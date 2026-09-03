"""
Modelli ORM (SQLAlchemy 2.0 typed style) per il dominio dell'applicazione:

Location        -> localita' turistica (citta'/paese) in cui si trovano le strutture
Property        -> struttura/servizio turistico (hotel, ristorante, attrazione)
Review          -> singola recensione raccolta (testo, valutazione, data, lingua, ...)
AspectMention    -> aspetto specifico menzionato in una recensione (es. "colazione",
                    "pulizia", "personale") con relativo sentiment, usato per capire
                    quali aspetti sono piu' apprezzati o criticati
AnalysisReport   -> output testuale generato dall'AI generativa (sintesi, report
                    descrittivo, confronto competitivo, suggerimenti di miglioramento)
IngestionJob     -> traccia delle esecuzioni della pipeline di acquisizione dati
                    (Apify o dataset di fallback), utile per audit e per la demo
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# JSON generico (anziche' JSONB specifico di PostgreSQL) cosi' lo stesso
# modello funziona sia su PostgreSQL (usato in Docker/produzione) sia su
# SQLite in-memory (usato nei test unitari, vedi backend/tests/conftest.py),
# senza dover duplicare i modelli o mockare il layer ORM nei test.
JSONType = JSON

from app.database import Base


class PropertyType(str, enum.Enum):
    hotel = "hotel"
    restaurant = "restaurant"
    attraction = "attraction"


class ReviewSource(str, enum.Enum):
    tripadvisor = "tripadvisor"
    google = "google"
    sample_dataset = "sample_dataset"
    manual = "manual"


class SentimentLabel(str, enum.Enum):
    very_negative = "very_negative"
    negative = "negative"
    neutral = "neutral"
    positive = "positive"
    very_positive = "very_positive"


class ReportType(str, enum.Enum):
    summary = "summary"
    competitive_comparison = "competitive_comparison"
    improvement_suggestions = "improvement_suggestions"


def _uuid() -> str:
    return str(uuid.uuid4())


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("city", "country", name="uq_location_city_country"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(120), nullable=False)

    properties: Mapped[list["Property"]] = relationship(back_populates="location")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[PropertyType] = mapped_column(Enum(PropertyType), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    external_source: Mapped[Optional[str]] = mapped_column(String(50))
    external_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    category: Mapped[Optional[str]] = mapped_column(String(120))  # es. cucina, stelle hotel
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    location: Mapped["Location"] = relationship(back_populates="properties")
    reviews: Mapped[list["Review"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("property_id", "external_review_id", name="uq_review_property_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    property_id: Mapped[str] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    external_review_id: Mapped[Optional[str]] = mapped_column(String(120))
    source: Mapped[ReviewSource] = mapped_column(Enum(ReviewSource), nullable=False)

    author: Mapped[Optional[str]] = mapped_column(String(150))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)  # 1.0 - 5.0
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="und")
    review_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Campi valorizzati dalla pipeline NLP (app/services/nlp_service.py)
    sentiment_label: Mapped[Optional[SentimentLabel]] = mapped_column(Enum(SentimentLabel))
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)  # -1.0 .. +1.0
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    property: Mapped["Property"] = relationship(back_populates="reviews")
    aspects: Mapped[list["AspectMention"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class AspectMention(Base):
    """Aspetto (es. 'colazione', 'staff', 'pulizia', 'prezzo') estratto da una
    recensione con il relativo sentiment locale: e' la base con cui il sistema
    individua gli aspetti piu' apprezzati o criticati di una struttura."""

    __tablename__ = "aspect_mentions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"), nullable=False, index=True)
    aspect: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    sentiment_label: Mapped[SentimentLabel] = mapped_column(Enum(SentimentLabel), nullable=False)
    snippet: Mapped[Optional[str]] = mapped_column(Text)

    review: Mapped["Review"] = relationship(back_populates="aspects")


class AnalysisReport(Base):
    """Output testuale prodotto dall'AI generativa: sintesi di una struttura,
    confronto competitivo tra piu' strutture o suggerimenti di miglioramento.
    property_ids contiene l'elenco delle strutture coinvolte (1 per un summary,
    N per un confronto competitivo)."""

    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False, index=True)
    property_ids: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_snapshot: Mapped[Optional[dict]] = mapped_column(JSONType)
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(150), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[ReviewSource] = mapped_column(Enum(ReviewSource), nullable=False)
    query_params: Mapped[Optional[dict]] = mapped_column(JSONType)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    records_ingested: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
