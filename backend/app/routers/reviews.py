"""Endpoint per la consultazione (e l'inserimento manuale) delle recensioni."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Property, Review
from app.schemas.schemas import AspectMentionOut, ReviewCreate, ReviewOut
from app.services.nlp_service import get_ai_provider

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewOut])
def list_reviews(
    db: Session = Depends(get_db),
    property_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Review).order_by(Review.review_date.desc()).offset(offset).limit(limit)
    if property_id:
        stmt = stmt.where(Review.property_id == property_id)
    return list(db.execute(stmt).scalars())


@router.get("/{review_id}/aspects", response_model=list[AspectMentionOut])
def get_review_aspects(review_id: str, db: Session = Depends(get_db)):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    return review.aspects


@router.post("", response_model=ReviewOut, status_code=201)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    """Inserimento manuale di una recensione (utile per demo/test o per
    integrare fonti diverse da Apify). La recensione viene analizzata subito
    dal provider AI attivo (sentiment + aspetti)."""
    prop = db.get(Property, payload.property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="Struttura non trovata")

    review = Review(**payload.model_dump())
    db.add(review)
    db.flush()

    get_ai_provider().analyze_review(db, review)

    db.commit()
    db.refresh(review)
    return review
