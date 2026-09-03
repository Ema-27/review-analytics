"""
Provider AI interamente in-process: esegue tutto in locale (nessuna chiave API
esterna richiesta) usando modelli open-source Hugging Face, senza dipendere da
servizi cloud a pagamento. E' la variante piu' leggera (nessun container
extra); la generazione testuale usa pero' `google/flan-t5-base`, con qualita'
in italiano scarsa. Il provider di default e' `OllamaProvider`, che ne eredita
sentiment/aspetti ma sposta la generazione su un LLM instruct piu' capace.

Modelli usati (scaricati automaticamente al primo utilizzo e messi in cache
nel volume Docker `model_cache`, vedi docker-compose.yml):

  * Sentiment (multilingue IT/EN/FR/DE/ES):
    nlptown/bert-base-multilingual-uncased-sentiment
    -> classificazione a 5 classi (1-5 stelle), qui mappata su
       SentimentLabel a 5 livelli e su uno score continuo [-1, +1].

  * Estrazione aspetti: lessico multilingue (aspect_lexicon.py) + sentiment
    a livello di frase riusando la stessa pipeline di sentiment.

  * Generazione testo (sintesi, confronto competitivo, suggerimenti):
    google/flan-t5-base, modello instruction-tuned leggero, eseguibile su CPU.
    I prompt sono costruiti iniettando i fatti/numeri reali calcolati da
    stats_service (vedi narrative_templates.build_*_facts) per ridurre il
    rischio di "allucinazioni" e mantenere il testo generato ancorato ai dati.

Il caricamento dei modelli e' lazy (avviene alla prima chiamata effettiva, non
all'avvio dell'app) e i modelli vengono tenuti in cache di processo, per non
rallentare l'avvio del container e non pagare il costo di download/caricamento
a ogni richiesta.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.ai_providers.aspect_lexicon import extract_aspects_from_text
from app.ai_providers.base import AIProvider
from app.ai_providers.narrative_templates import (
    build_comparison_facts,
    build_comparison_fallback_text,
    build_summary_facts,
    build_summary_fallback_text,
    build_suggestions_fallback_text,
    is_low_quality_generation,
)
from app.config import get_settings
from app.models.models import AspectMention, Review, SentimentLabel
from app.services import stats_service

logger = logging.getLogger(__name__)

# Mappa le 5 classi del modello nlptown (stringhe tipo "1 star" .. "5 stars")
# sulle 5 etichette del dominio applicativo e su uno score continuo.
_STARS_TO_LABEL = {
    1: (SentimentLabel.very_negative, -1.0),
    2: (SentimentLabel.negative, -0.5),
    3: (SentimentLabel.neutral, 0.0),
    4: (SentimentLabel.positive, 0.5),
    5: (SentimentLabel.very_positive, 1.0),
}


class HuggingFaceLocalProvider(AIProvider):
    name = "huggingface_local"

    def __init__(self) -> None:
        settings = get_settings()
        self.model_label = f"{settings.hf_sentiment_model} + {settings.hf_generation_model}"
        self._sentiment_pipeline = None
        self._generation_pipeline = None
        self._settings = settings
        # Il caricamento lazy dei modelli puo' essere innescato da piu' richieste
        # HTTP contemporanee (gli endpoint sincroni di FastAPI girano in un
        # threadpool): un lock evita di caricare due volte lo stesso modello.
        self._load_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------
    @property
    def sentiment_pipeline(self):
        if self._sentiment_pipeline is None:
            with self._load_lock:
                if self._sentiment_pipeline is None:
                    from transformers import pipeline

                    logger.info(
                        "Caricamento modello sentiment: %s", self._settings.hf_sentiment_model
                    )
                    self._sentiment_pipeline = pipeline(
                        "sentiment-analysis",
                        model=self._settings.hf_sentiment_model,
                        tokenizer=self._settings.hf_sentiment_model,
                        device=-1 if self._settings.hf_device == "cpu" else 0,
                    )
        return self._sentiment_pipeline

    @property
    def generation_pipeline(self):
        if self._generation_pipeline is None:
            with self._load_lock:
                if self._generation_pipeline is None:
                    from transformers import pipeline

                    logger.info(
                        "Caricamento modello generativo: %s", self._settings.hf_generation_model
                    )
                    self._generation_pipeline = pipeline(
                        "text2text-generation",
                        model=self._settings.hf_generation_model,
                        tokenizer=self._settings.hf_generation_model,
                        device=-1 if self._settings.hf_device == "cpu" else 0,
                    )
        return self._generation_pipeline

    # ------------------------------------------------------------------
    # Sentiment + aspect extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _result_to_label(result: dict) -> tuple[SentimentLabel, float]:
        try:
            stars = int(result["label"][0])  # es. "5 stars" -> 5
        except (KeyError, ValueError, TypeError):
            return SentimentLabel.neutral, 0.0
        return _STARS_TO_LABEL.get(stars, (SentimentLabel.neutral, 0.0))

    def _classify_many(self, texts: list[str]) -> list[tuple[SentimentLabel, float]]:
        """Classifica una lista di testi in un'unica passata batch: molto piu'
        veloce su CPU rispetto a una chiamata per testo."""
        if not texts:
            return []
        try:
            results = self.sentiment_pipeline(
                [t[:512] for t in texts], batch_size=16, truncation=True
            )
            return [self._result_to_label(r) for r in results]
        except Exception:  # pragma: no cover - difensivo
            logger.exception("Errore classificazione sentiment batch, uso fallback neutro")
            return [(SentimentLabel.neutral, 0.0)] * len(texts)

    def _classify_sentiment(self, text: str) -> tuple[SentimentLabel, float]:
        return self._classify_many([text])[0]

    def analyze_review(self, db: Session, review: Review) -> None:
        self.analyze_reviews(db, [review])

    def analyze_reviews(self, db: Session, reviews: list[Review]) -> None:
        """Analisi in blocco: un batch per il sentiment delle recensioni, uno
        per tutte le frasi-aspetto raccolte, invece di N chiamate separate."""
        if not reviews:
            return

        now = datetime.utcnow()
        for review, (label, score) in zip(reviews, self._classify_many([r.text for r in reviews])):
            review.sentiment_label = label
            review.sentiment_score = score
            review.analyzed_at = now

        # Estrazione aspetti (regex, economica) + un solo batch di sentiment
        # sulle frasi in cui gli aspetti compaiono.
        pending: list[tuple[Review, str, str]] = []
        for review in reviews:
            for aspect, sentence in extract_aspects_from_text(review.text).items():
                pending.append((review, aspect, sentence))

        if pending:
            labels = self._classify_many([s for _, _, s in pending])
            for (review, aspect, sentence), (sent_label, _) in zip(pending, labels):
                db.add(
                    AspectMention(
                        review_id=review.id,
                        aspect=aspect,
                        sentiment_label=sent_label,
                        snippet=sentence[:500],
                    )
                )
        db.flush()

    # ------------------------------------------------------------------
    # Generazione testo (con fallback template se il modello fallisce)
    # ------------------------------------------------------------------
    def _generate(self, prompt: str, max_new_tokens: int = 200) -> Optional[str]:
        try:
            out = self.generation_pipeline(
                prompt, max_new_tokens=max_new_tokens, do_sample=False, num_beams=4
            )[0]["generated_text"].strip()
            return out or None
        except Exception:  # pragma: no cover - difensivo
            logger.exception("Generazione testo fallita, uso narrativa basata su template")
            return None

    def generate_summary(self, db: Session, property_id: str) -> str:
        stats = stats_service.get_property_stats(db, property_id)
        facts = build_summary_facts(stats)
        prompt = (
            "Sei un analista di customer experience nel turismo. Sulla base dei seguenti dati "
            "reali, scrivi in italiano un breve report descrittivo (4-6 frasi) sull'andamento "
            "della soddisfazione degli utenti, citando gli aspetti piu' apprezzati e criticati.\n\n"
            f"DATI:\n{facts}\n\nREPORT:"
        )
        generated = self._generate(prompt, max_new_tokens=220)
        if not is_low_quality_generation(generated, prompt):
            return generated
        return build_summary_fallback_text(stats)

    def generate_comparison(self, db: Session, property_ids: list[str]) -> str:
        stats_list = stats_service.get_comparison_stats(db, property_ids)
        distinguishing = stats_service.rank_distinguishing_aspects(stats_list)
        facts = build_comparison_facts(stats_list, distinguishing)
        prompt = (
            "Sei un analista competitivo nel settore turistico. Confronta le seguenti strutture "
            "simili sulla base dei dati reali forniti, evidenziando in italiano i principali "
            "fattori distintivi tra loro (reputazione, servizi, valutazioni).\n\n"
            f"DATI:\n{facts}\n\nCONFRONTO:"
        )
        generated = self._generate(prompt, max_new_tokens=260)
        if not is_low_quality_generation(generated, prompt):
            return generated
        return build_comparison_fallback_text(stats_list, distinguishing)

    def generate_suggestions(self, db: Session, property_id: str) -> str:
        stats = stats_service.get_property_stats(db, property_id)
        top_neg = [a for a in stats["top_aspects"] if a["net_sentiment"] < 0][:4]

        # Nessuna criticita' reale: chiedere al modello "3-4 interventi" lo porta
        # a inventare consigli generici e ripetitivi. Meglio il testo dai dati.
        if not top_neg:
            return build_suggestions_fallback_text(stats)

        neg_txt = ", ".join(f"{a['aspect']} ({a['negative']} menzioni negative)" for a in top_neg)
        prompt = (
            "Sei un consulente di hospitality management. Sulla base delle criticita' emerse "
            "dalle recensioni elencate di seguito, proponi in italiano 3-4 interventi migliorativi "
            "concreti e prioritari per aumentare la soddisfazione degli utenti e la competitivita' "
            "della struttura. Ogni intervento deve essere distinto dagli altri, non ripetere lo "
            "stesso concetto.\n\n"
            f"Struttura: {stats['property'].name}\nCriticita' principali: {neg_txt}\n\n"
            "SUGGERIMENTI:"
        )
        generated = self._generate(prompt, max_new_tokens=260)
        if not is_low_quality_generation(generated, prompt):
            return generated
        return build_suggestions_fallback_text(stats)
