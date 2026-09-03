"""
Orchestrazione della pipeline di acquisizione recensioni.

Due modalita' d'uso:

1. `run_ingestion(db, request)` - flusso "on demand" invocato dall'endpoint
   POST /ingestion/run: tenta l'acquisizione via Apify/Tripadvisor se e' stato
   fornito un URL e un token Apify e' configurato; altrimenti (o in caso di
   errore) ricade sul dataset di esempio incluso nel repository, garantendo
   che il sistema sia sempre dimostrabile.

2. `seed_demo_dataset(db)` - popola il database con l'intero dataset di
   esempio (12 strutture, centinaia di recensioni multilingua) cosi' che la
   demo abbia da subito dati significativi su cui mostrare grafici, trend e
   report AI, senza dover attendere chiamate Apify durante la presentazione.

Ogni ingestion viene tracciata in tabella `ingestion_jobs` per audit, e le
nuove recensioni vengono immediatamente passate alla pipeline NLP
(app/services/nlp_service.py) per calcolare sentiment e aspetti.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    IngestionJob,
    Location,
    Property,
    PropertyType,
    Review,
    ReviewSource,
)
from app.schemas.schemas import IngestionRequest
from app.services import apify_service
from app.services.nlp_service import get_ai_provider

logger = logging.getLogger(__name__)

SAMPLE_DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_reviews.json"


def _load_sample_dataset() -> list[dict[str, Any]]:
    with SAMPLE_DATASET_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def get_or_create_location(db: Session, city: str, country: str, region: Optional[str] = None) -> Location:
    stmt = select(Location).where(Location.city == city, Location.country == country)
    loc = db.execute(stmt).scalar_one_or_none()
    if loc:
        return loc
    loc = Location(city=city, country=country, region=region)
    db.add(loc)
    db.flush()
    return loc


def get_or_create_property(
    db: Session,
    name: str,
    ptype: PropertyType,
    location: Location,
    category: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Property:
    stmt = select(Property).where(Property.name == name, Property.location_id == location.id)
    prop = db.execute(stmt).scalar_one_or_none()
    if prop:
        return prop
    prop = Property(
        name=name,
        type=ptype,
        location_id=location.id,
        category=category,
        source_url=source_url,
    )
    db.add(prop)
    db.flush()
    return prop


def _ingest_reviews(
    db: Session, prop: Property, raw_reviews: list[dict[str, Any]], source: ReviewSource
) -> int:
    """Inserisce le recensioni evitando duplicati (stesso property + external id)
    e le passa subito alla pipeline NLP per il calcolo di sentiment/aspetti."""
    existing_ids = {
        r[0]
        for r in db.execute(
            select(Review.external_review_id).where(Review.property_id == prop.id)
        ).all()
        if r[0]
    }

    new_reviews: list[Review] = []
    for raw in raw_reviews:
        ext_id = raw.get("external_review_id")
        if ext_id and ext_id in existing_ids:
            continue
        existing_ids.add(ext_id)  # evita duplicati anche dentro lo stesso batch

        review_date = raw["review_date"]
        if isinstance(review_date, str):
            review_date = date.fromisoformat(review_date)

        review = Review(
            property_id=prop.id,
            external_review_id=ext_id,
            source=source,
            author=raw.get("author"),
            text=raw["text"],
            rating=float(raw["rating"]),
            language=raw.get("language", "und"),
            review_date=review_date,
        )
        db.add(review)
        new_reviews.append(review)

    if not new_reviews:
        return 0

    db.flush()

    # Analisi NLP in blocco (sentiment + aspetti). Per volumi molto grandi in
    # produzione si delegherebbe a una coda asincrona (es. Celery); qui viene
    # eseguita in linea, ma in batch per non pagare una inferenza per volta.
    get_ai_provider().analyze_reviews(db, new_reviews)

    return len(new_reviews)


def run_ingestion(db: Session, request: IngestionRequest) -> IngestionJob:
    job = IngestionJob(
        source=ReviewSource.tripadvisor if request.tripadvisor_url else ReviewSource.sample_dataset,
        query_params=request.model_dump(mode="json"),
        status="running",
    )
    db.add(job)
    db.flush()

    try:
        raw_reviews, source = _resolve_reviews(request, job)
        job.source = source

        if not raw_reviews:
            # Nessuna recensione: NON si crea una struttura vuota e NON si
            # ricade su dati di un'altra struttura (comportamento fuorviante).
            job.records_ingested = 0
            job.status = "completed"
            if not job.error_message:
                job.error_message = (
                    f"Nessuna recensione acquisita per '{request.property_name}'. "
                    "Per una struttura non presente nel dataset di esempio servono "
                    "un APIFY_API_TOKEN valido e un URL Tripadvisor corretto."
                )
            return job

        location = get_or_create_location(db, request.city, request.country)
        prop = get_or_create_property(
            db,
            name=request.property_name,
            ptype=request.property_type,
            location=location,
            source_url=request.tripadvisor_url,
        )
        job.records_ingested = _ingest_reviews(db, prop, raw_reviews, source)
        job.status = "completed"
    except Exception as exc:  # pragma: no cover - percorso difensivo
        logger.exception("Ingestion fallita")
        job.status = "failed"
        job.error_message = str(exc)
        raise
    finally:
        job.finished_at = datetime.utcnow()
        db.commit()

    return job


def _resolve_reviews(
    request: IngestionRequest, job: IngestionJob
) -> tuple[list[dict[str, Any]], ReviewSource]:
    """Decide da dove prendere le recensioni per una ingestion mirata.

    Priorita': Apify (se e' stato fornito un URL Tripadvisor). Il dataset di
    esempio e' usato SOLO se il nome della struttura combacia con una voce del
    dataset: mai come sostituto silenzioso di dati reali di un'altra struttura.
    Se non si ottiene nulla, si annota il motivo in `job.error_message`.
    """
    if request.tripadvisor_url:
        try:
            reviews = apify_service.fetch_tripadvisor_reviews(
                request.tripadvisor_url, max_reviews=request.max_reviews
            )
            if reviews:
                return reviews, ReviewSource.tripadvisor
            job.error_message = (
                "L'acquisizione via Apify non ha restituito recensioni per l'URL "
                "fornito: verifica che l'URL sia la pagina Tripadvisor corretta "
                "della struttura e che l'Actor sia stato approvato."
            )
        except apify_service.ApifyUnavailableError as exc:
            logger.info("Apify non disponibile: %s", exc)
            job.error_message = f"Apify non disponibile: {exc}"
        # fallback ammesso solo per corrispondenza esatta di nome
        return _sample_reviews_by_name(request), ReviewSource.sample_dataset

    by_name = _sample_reviews_by_name(request)
    if not by_name:
        job.error_message = (
            f"'{request.property_name}' non e' presente nel dataset di esempio. "
            "Fornisci un URL Tripadvisor (con APIFY_API_TOKEN configurato) per "
            "acquisire recensioni reali."
        )
    return by_name, ReviewSource.sample_dataset


def _sample_reviews_by_name(request: IngestionRequest) -> list[dict[str, Any]]:
    """Recensioni del dataset di esempio per una struttura con nome combaciante
    (confronto case-insensitive); lista vuota se non c'e' corrispondenza."""
    name_lower = request.property_name.strip().lower()
    for entry in _load_sample_dataset():
        if entry["name"].strip().lower() == name_lower:
            return entry["reviews"]
    return []


def seed_demo_dataset(db: Session) -> dict[str, int]:
    """Popola il database con l'intero dataset di esempio incluso nel progetto,
    cosi' la demo ha immediatamente dati realistici multi-struttura e
    multi-lingua su cui mostrare dashboard, confronti e report AI."""
    dataset = _load_sample_dataset()
    properties_created = 0
    reviews_created = 0

    for entry in dataset:
        location = get_or_create_location(db, entry["city"], entry["country"])
        prop = get_or_create_property(
            db,
            name=entry["name"],
            ptype=PropertyType(entry["type"]),
            location=location,
            category=entry.get("category"),
        )
        properties_created += 1
        reviews_created += _ingest_reviews(db, prop, entry["reviews"], ReviewSource.sample_dataset)

    db.commit()
    return {"properties": properties_created, "reviews": reviews_created}
