"""
Provider AI deterministico e istantaneo, senza alcun modello ML: usato nei
test automatici (per non dipendere dal download di modelli multi-GB durante
la CI) e opzionalmente in demo rapide offline impostando AI_PROVIDER=mock.

La logica di sentiment e' una semplice euristica lessicale (parole positive/
negative note) sufficiente a validare il resto della pipeline (persistenza,
aggregazioni, API, frontend) in modo rapido e riproducibile.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.ai_providers.aspect_lexicon import extract_aspects_from_text
from app.ai_providers.base import AIProvider
from app.ai_providers.narrative_templates import (
    build_comparison_fallback_text,
    build_summary_fallback_text,
    build_suggestions_fallback_text,
)
from app.models.models import AspectMention, Review, SentimentLabel
from app.services import stats_service

_POSITIVE_WORDS = {
    "fantastic", "excellent", "eccellente", "fantastica", "consigliatissimo",
    "impeccabile", "great", "ottimo", "ottima", "highly", "flawless",
}
_NEGATIVE_WORDS = {
    "deluso", "delude", "scadente", "disappointing", "poor", "decu",
    "decevoir", "decepciono", "desiderare", "desire",
}


class MockAIProvider(AIProvider):
    name = "mock"
    model_label = "lexicon-heuristic (test/demo)"

    def _classify(self, text: str) -> tuple[SentimentLabel, float]:
        lowered = text.lower()
        pos = sum(1 for w in _POSITIVE_WORDS if w in lowered)
        neg = sum(1 for w in _NEGATIVE_WORDS if w in lowered)
        if pos > neg:
            return (SentimentLabel.very_positive, 1.0) if pos >= 2 else (SentimentLabel.positive, 0.5)
        if neg > pos:
            return (SentimentLabel.very_negative, -1.0) if neg >= 2 else (SentimentLabel.negative, -0.5)
        return SentimentLabel.neutral, 0.0

    def analyze_review(self, db: Session, review: Review) -> None:
        label, score = self._classify(review.text)
        review.sentiment_label = label
        review.sentiment_score = score
        review.analyzed_at = datetime.utcnow()

        for aspect, sentence in extract_aspects_from_text(review.text).items():
            sent_label, _ = self._classify(sentence)
            db.add(
                AspectMention(
                    review_id=review.id, aspect=aspect, sentiment_label=sent_label, snippet=sentence[:500]
                )
            )
        db.flush()

    def generate_summary(self, db: Session, property_id: str) -> str:
        stats = stats_service.get_property_stats(db, property_id)
        return build_summary_fallback_text(stats)

    def generate_comparison(self, db: Session, property_ids: list[str]) -> str:
        stats_list = stats_service.get_comparison_stats(db, property_ids)
        distinguishing = stats_service.rank_distinguishing_aspects(stats_list)
        return build_comparison_fallback_text(stats_list, distinguishing)

    def generate_suggestions(self, db: Session, property_id: str) -> str:
        stats = stats_service.get_property_stats(db, property_id)
        return build_suggestions_fallback_text(stats)
