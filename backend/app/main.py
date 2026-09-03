"""
Entry point dell'applicazione FastAPI "TourInsight".

Applicazione cloud per la raccolta, gestione e analisi di recensioni relative
a strutture e servizi turistici (hotel, ristoranti, attrazioni), con
integrazione di tecniche di NLP e AI generativa per sentiment analysis,
sintesi, confronto competitivo e suggerimenti di miglioramento.
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import ai, analytics, ingestion, properties, reviews

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


def _warm_up_models() -> None:
    """Pre-carica il modello di sentiment in un thread di sfondo, cosi' la prima
    acquisizione non paga il costo di caricamento (~15-25 s su CPU)."""
    if settings.ai_provider == "mock":
        return
    try:
        from app.services.nlp_service import get_ai_provider

        provider = get_ai_provider()
        if hasattr(provider, "_classify_many"):
            provider._classify_many(["ok"])
            logger.info("Modello sentiment pre-caricato.")
        if hasattr(provider, "warm_up"):
            provider.warm_up()
    except Exception:  # pragma: no cover - warmup best-effort
        logger.warning("Pre-caricamento modelli non riuscito (verranno caricati al primo uso).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    threading.Thread(target=_warm_up_models, daemon=True).start()
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "API per la raccolta, gestione e analisi di recensioni di strutture "
        "e servizi turistici (hotel, ristoranti, attrazioni)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router, prefix=settings.api_v1_prefix)
app.include_router(reviews.router, prefix=settings.api_v1_prefix)
app.include_router(analytics.router, prefix=settings.api_v1_prefix)
app.include_router(ai.router, prefix=settings.api_v1_prefix)
app.include_router(ingestion.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "message": "TourInsight API - vedi /docs per la documentazione interattiva (Swagger UI).",
    }
