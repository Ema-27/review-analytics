"""Endpoint per la consultazione delle strutture turistiche censite nel sistema."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Location, Property, PropertyType, Review
from app.schemas.schemas import PropertyOut, PropertySummary

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertySummary])
def list_properties(
    db: Session = Depends(get_db),
    type: Optional[PropertyType] = Query(default=None),
    city: Optional[str] = Query(default=None),
):
    stmt = (
        select(
            Property,
            Location,
            func.count(Review.id).label("review_count"),
            func.avg(Review.rating).label("avg_rating"),
            func.avg(Review.sentiment_score).label("avg_sentiment"),
        )
        .join(Location, Property.location_id == Location.id)
        .outerjoin(Review, Review.property_id == Property.id)
        .group_by(Property.id, Location.id)
    )
    if type:
        stmt = stmt.where(Property.type == type)
    if city:
        stmt = stmt.where(Location.city.ilike(f"%{city}%"))

    rows = db.execute(stmt).all()
    return [
        PropertySummary(
            id=prop.id,
            name=prop.name,
            type=prop.type,
            city=loc.city,
            country=loc.country,
            review_count=review_count or 0,
            average_rating=round(avg_rating, 2) if avg_rating else None,
            average_sentiment=round(avg_sentiment, 2) if avg_sentiment else None,
        )
        for prop, loc, review_count, avg_rating, avg_sentiment in rows
    ]


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: str, db: Session = Depends(get_db)):
    prop = db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="Struttura non trovata")
    return prop
