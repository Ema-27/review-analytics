"""Schemi Pydantic per validazione input/output delle API REST."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import PropertyType, ReportType, ReviewSource, SentimentLabel


# ---------- Location ----------
class LocationBase(BaseModel):
    city: str
    region: Optional[str] = None
    country: str


class LocationCreate(LocationBase):
    pass


class LocationOut(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ---------- Property ----------
class PropertyBase(BaseModel):
    name: str
    type: PropertyType
    category: Optional[str] = None
    source_url: Optional[str] = None


class PropertyCreate(PropertyBase):
    location: LocationCreate


class PropertyOut(PropertyBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    location: LocationOut
    created_at: datetime


class PropertySummary(BaseModel):
    """Vista aggregata usata nelle liste/dashboard: evita N+1 query pesanti."""

    id: str
    name: str
    type: PropertyType
    city: str
    country: str
    review_count: int
    average_rating: Optional[float] = None
    average_sentiment: Optional[float] = None


# ---------- Review ----------
class ReviewBase(BaseModel):
    author: Optional[str] = None
    text: str
    rating: float = Field(ge=1.0, le=5.0)
    language: str = "und"
    review_date: date
    source: ReviewSource = ReviewSource.manual
    external_review_id: Optional[str] = None


class ReviewCreate(ReviewBase):
    property_id: str


class ReviewOut(ReviewBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    property_id: str
    sentiment_label: Optional[SentimentLabel] = None
    sentiment_score: Optional[float] = None
    created_at: datetime


# ---------- Aspetti ----------
class AspectMentionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    aspect: str
    sentiment_label: SentimentLabel
    snippet: Optional[str] = None


class AspectAggregateOut(BaseModel):
    """Aggregato per la UI: quanto spesso un aspetto compare e con quale sentiment
    prevalente, cio' che alimenta 'aspetti piu' apprezzati/criticati'."""

    aspect: str
    mentions: int
    positive: int
    negative: int
    neutral: int
    net_sentiment: float  # (positive - negative) / mentions


# ---------- Analytics ----------
class RatingTrendPoint(BaseModel):
    period: str  # es. "2026-01"
    average_rating: float
    review_count: int


class SentimentBreakdown(BaseModel):
    label: SentimentLabel
    count: int
    percentage: float


class PropertyAnalytics(BaseModel):
    property_id: str
    property_name: str
    review_count: int
    average_rating: float
    rating_trend: list[RatingTrendPoint]
    sentiment_breakdown: list[SentimentBreakdown]
    top_aspects: list[AspectAggregateOut]


# ---------- AI reports ----------
class AnalysisReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    report_type: ReportType
    property_ids: list[str]
    content: str
    ai_provider: str
    ai_model: str
    generated_at: datetime


class SummaryRequest(BaseModel):
    property_id: str
    max_reviews: int = Field(default=200, le=1000)


class ComparisonRequest(BaseModel):
    property_ids: list[str] = Field(min_length=2, max_length=6)


class SuggestionsRequest(BaseModel):
    property_id: str


# ---------- Ingestion ----------
class IngestionRequest(BaseModel):
    property_name: str
    property_type: PropertyType
    city: str
    country: str
    tripadvisor_url: Optional[str] = Field(
        default=None,
        description="URL della pagina Tripadvisor della struttura. Se assente o se "
        "Apify non e' configurato, viene usato il dataset di esempio.",
    )
    max_reviews: int = Field(default=100, le=500)


class IngestionJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source: ReviewSource
    status: str
    records_ingested: int
    error_message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
