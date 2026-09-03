"""
Endpoint di analisi statistica: alimentano i grafici interattivi e gli
indicatori del Front-End (andamento valutazioni, distribuzione sentiment,
aspetti piu' apprezzati/criticati).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import PropertyAnalytics
from app.services import stats_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/properties/{property_id}", response_model=PropertyAnalytics)
def property_analytics(property_id: str, db: Session = Depends(get_db)):
    try:
        stats = stats_service.get_property_stats(db, property_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return PropertyAnalytics(
        property_id=stats["property"].id,
        property_name=stats["property"].name,
        review_count=stats["review_count"],
        average_rating=stats["average_rating"],
        rating_trend=stats["rating_trend"],
        sentiment_breakdown=stats["sentiment_breakdown"],
        top_aspects=stats["top_aspects"],
    )
