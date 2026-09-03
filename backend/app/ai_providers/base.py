"""
Interfaccia astratta per i provider di AI/NLP.

Il sistema adotta un pattern "strategy/provider" pluggable: il resto del
codice (ingestion, router AI) dipende solo da questa interfaccia astratta e
non dal provider concreto. Questo permette di:

  * usare di default un provider che gira interamente in locale, senza chiavi
    API a pagamento (sentiment via Hugging Face `transformers`, generazione
    via un LLM instruct servito da Ollama);
  * passare in qualunque momento, cambiando solo la variabile d'ambiente
    AI_PROVIDER (vedi app/config.py), a un provider basato su API cloud
    (es. Claude o OpenAI), implementando la stessa interfaccia;
  * testare la logica applicativa con un MockAIProvider deterministico e
    velocissimo, senza scaricare modelli (vedi tests/).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.models.models import Review


class AIProvider(ABC):
    name: str = "base"
    model_label: str = "n/a"

    @abstractmethod
    def analyze_review(self, db: Session, review: Review) -> None:
        """Calcola sentiment (label + score) e aspetti menzionati per una
        recensione e persiste i risultati (Review.sentiment_*, AspectMention)."""

    def analyze_reviews(self, db: Session, reviews: list[Review]) -> None:
        """Come `analyze_review` ma per un blocco di recensioni. L'implementazione
        di default cicla; i provider possono sovrascriverla per elaborare in
        batch (es. una sola inferenza per tutte le recensioni)."""
        for review in reviews:
            self.analyze_review(db, review)

    @abstractmethod
    def generate_summary(self, db: Session, property_id: str) -> str:
        """Genera un report descrittivo in linguaggio naturale che sintetizza
        le recensioni di una struttura (sentiment generale, aspetti
        principali, andamento nel tempo)."""

    @abstractmethod
    def generate_comparison(self, db: Session, property_ids: list[str]) -> str:
        """Genera un'analisi comparativa tra piu' strutture simili,
        evidenziandone i principali fattori distintivi (reputazione, servizi,
        valutazioni)."""

    @abstractmethod
    def generate_suggestions(self, db: Session, property_id: str) -> str:
        """Sulla base delle criticita' emerse dalle recensioni, genera
        suggerimenti di interventi migliorativi, priorita' operative e
        strategie per aumentare soddisfazione e competitivita'."""
