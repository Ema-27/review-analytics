"""
Calcolo delle statistiche aggregate su recensioni/strutture: trend delle
valutazioni, distribuzione del sentiment, aspetti piu' menzionati e relativo
sentiment prevalente. Queste funzioni sono il punto di raccolta unico usato
sia dagli endpoint di analytics (grafici/indicatori nel Front-End) sia dai
provider AI (per costruire prompt/contesto informati sui dati reali quando
generano sintesi, confronti e suggerimenti) -- evitando duplicazione di
logica tra le due parti del sistema.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import AspectMention, Property, Review, SentimentLabel

SENTIMENT_TO_SCORE = {
    SentimentLabel.very_negative: -1.0,
    SentimentLabel.negative: -0.5,
    SentimentLabel.neutral: 0.0,
    SentimentLabel.positive: 0.5,
    SentimentLabel.very_positive: 1.0,
}


def get_property_stats(db: Session, property_id: str, months: int = 12) -> dict[str, Any]:
    prop = db.get(Property, property_id)
    if prop is None:
        raise ValueError(f"Property {property_id} non trovata")

    reviews: list[Review] = list(
        db.execute(select(Review).where(Review.property_id == property_id)).scalars()
    )

    review_count = len(reviews)
    average_rating = round(sum(r.rating for r in reviews) / review_count, 2) if review_count else 0.0

    # --- trend mensile ---
    monthly: dict[str, list[float]] = defaultdict(list)
    for r in reviews:
        key = r.review_date.strftime("%Y-%m")
        monthly[key].append(r.rating)
    rating_trend = [
        {"period": k, "average_rating": round(sum(v) / len(v), 2), "review_count": len(v)}
        for k, v in sorted(monthly.items())
    ]

    # --- distribuzione sentiment ---
    sentiment_counter = Counter(r.sentiment_label for r in reviews if r.sentiment_label)
    total_analyzed = sum(sentiment_counter.values()) or 1
    sentiment_breakdown = [
        {
            "label": label.value,
            "count": count,
            "percentage": round(100 * count / total_analyzed, 1),
        }
        for label, count in sentiment_counter.items()
    ]

    # --- aspetti (piu' apprezzati / criticati) ---
    review_ids = [r.id for r in reviews]
    aspects: list[AspectMention] = []
    if review_ids:
        aspects = list(
            db.execute(select(AspectMention).where(AspectMention.review_id.in_(review_ids))).scalars()
        )
    aspect_stats: dict[str, Counter] = defaultdict(Counter)
    for a in aspects:
        aspect_stats[a.aspect][a.sentiment_label] += 1

    top_aspects = []
    for aspect, counter in aspect_stats.items():
        mentions = sum(counter.values())
        positive = counter.get(SentimentLabel.positive, 0) + counter.get(SentimentLabel.very_positive, 0)
        negative = counter.get(SentimentLabel.negative, 0) + counter.get(SentimentLabel.very_negative, 0)
        neutral = mentions - positive - negative
        net_sentiment = round((positive - negative) / mentions, 2) if mentions else 0.0
        top_aspects.append(
            {
                "aspect": aspect,
                "mentions": mentions,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "net_sentiment": net_sentiment,
            }
        )
    top_aspects.sort(key=lambda a: a["mentions"], reverse=True)

    positive_snippets = [r.text for r in reviews if r.sentiment_score and r.sentiment_score > 0.4][:5]
    negative_snippets = [r.text for r in reviews if r.sentiment_score and r.sentiment_score < -0.2][:5]

    return {
        "property": prop,
        "review_count": review_count,
        "average_rating": average_rating,
        "rating_trend": rating_trend,
        "sentiment_breakdown": sentiment_breakdown,
        "top_aspects": top_aspects,
        "positive_snippets": positive_snippets,
        "negative_snippets": negative_snippets,
    }


def get_comparison_stats(db: Session, property_ids: list[str]) -> list[dict[str, Any]]:
    return [get_property_stats(db, pid) for pid in property_ids]


def rank_distinguishing_aspects(stats_list: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Per un confronto competitivo: individua, per ciascuna struttura, gli
    aspetti in cui si distingue (in positivo o in negativo) rispetto alle
    altre in confronto, sulla base del net_sentiment per aspetto condiviso."""
    by_property: dict[str, list[dict[str, Any]]] = {}
    aspect_by_property: dict[str, dict[str, float]] = {}

    for stats in stats_list:
        pid = stats["property"].id
        aspect_by_property[pid] = {a["aspect"]: a["net_sentiment"] for a in stats["top_aspects"]}

    for stats in stats_list:
        pid = stats["property"].id
        own = aspect_by_property[pid]
        distinguishing = []
        for aspect, score in own.items():
            others_scores = [
                aspect_by_property[other_pid][aspect]
                for other_pid in aspect_by_property
                if other_pid != pid and aspect in aspect_by_property[other_pid]
            ]
            if not others_scores:
                continue
            avg_others = sum(others_scores) / len(others_scores)
            delta = round(score - avg_others, 2)
            if abs(delta) >= 0.15:
                distinguishing.append({"aspect": aspect, "delta_vs_others": delta, "own_score": score})
        distinguishing.sort(key=lambda d: abs(d["delta_vs_others"]), reverse=True)
        by_property[pid] = distinguishing[:5]

    return by_property
