"""
Integrazione con Apify (https://apify.com) per l'acquisizione di recensioni
pubblicate su Tripadvisor tramite servizi esterni di scraping.

Il client e' volutamente minimale e sincrono (usa `httpx`): avvia l'Apify Actor
di scraping Tripadvisor sull'URL della struttura fornita dall'utente, attende
il completamento della run entro un timeout configurabile e restituisce le
recensioni raccolte in un formato normalizzato, indipendente dal formato
proprietario dell'Actor scelto (cosi' l'Actor Apify puo' essere sostituito
senza impattare il resto del sistema: vedi `normalize_apify_item`).

Se `APIFY_API_TOKEN` non e' configurato, o la chiamata fallisce/va in timeout,
il chiamante (vedi `ingestion_service.py`) ricade automaticamente sul dataset
di esempio incluso, cosi' il sistema resta utilizzabile anche senza
credenziali o connettivita' verso servizi esterni.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

APIFY_API_BASE = "https://api.apify.com/v2"

# Formati di pagina Tripadvisor che contengono gli id -g/-d ma NON sono
# accettati dall'Actor di scraping (tipici di risultati di ricerca / link da
# Google): vanno riscritti nella forma canonica "<Tipo>_Review-g..-d..".
_TA_URL_RE = re.compile(
    r"(?P<base>https?://(?:www\.)?tripadvisor\.[a-z.]+)/"
    r"(?P<page>[A-Za-z_]+)-g(?P<geo>\d+)-d(?P<detail>\d+)-(?P<rest>.+)",
    re.IGNORECASE,
)


def canonicalize_tripadvisor_url(url: str) -> str:
    """Normalizza un URL Tripadvisor nella forma attesa dall'Actor.

    In particolare converte le pagine `HotelHighlight` (che l'Actor restituisce
    vuote) in `Hotel_Review`, mantenendo gli stessi id -g/-d. URL gia' corretti
    o non riconosciuti vengono restituiti invariati.
    """
    m = _TA_URL_RE.match(url.strip())
    if not m:
        return url.strip()

    page = m.group("page")
    if page.lower() == "hotelhighlight":
        page = "Hotel_Review"
    elif not page.lower().endswith("_review"):
        # es. "Tourism", "ShowUserReviews", ... -> best effort su Hotel_Review
        page = "Hotel_Review"

    rest = m.group("rest")
    if not re.match(r"Reviews[-.]", rest, re.IGNORECASE):
        rest = f"Reviews-{rest}"

    canonical = f"{m.group('base')}/{page}-g{m.group('geo')}-d{m.group('detail')}-{rest}"
    if canonical != url.strip():
        logger.info("URL Tripadvisor normalizzato: %s -> %s", url, canonical)
    return canonical


class ApifyUnavailableError(Exception):
    """Sollevata quando Apify non e' configurato o la run non va a buon fine."""


def _extract_author(item: dict[str, Any]) -> str:
    """L'Actor puo' restituire l'autore come stringa (`userName`/`author`) o come
    oggetto annidato (`user: {name: ...}`), oppure null se lo scraping dei dati
    del recensore e' disabilitato."""
    user = item.get("user")
    if isinstance(user, dict):
        name = user.get("name") or user.get("username")
        if name:
            return str(name)
    return item.get("userName") or item.get("author") or "Anonimo"


def normalize_apify_item(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Converte un item grezzo restituito dall'Apify Tripadvisor Actor
    (`maxcopell/tripadvisor-reviews`) nel formato interno usato dal sistema.
    Il mapping tollera alias di campi comuni per restare robusto a piccole
    variazioni tra build/actor diversi."""
    body = item.get("text") or item.get("reviewText") or item.get("review_text")
    if not body:
        return None

    # Il titolo della recensione e' spesso ricco di segnale (sentiment, aspetti):
    # lo si antepone al corpo per l'analisi NLP a valle.
    title = (item.get("title") or "").strip()
    text = f"{title}. {body}" if title and not body.startswith(title) else body

    rating = item.get("rating") or item.get("reviewRating") or item.get("bubbleRating")
    try:
        rating = float(rating)
    except (TypeError, ValueError):
        rating = 3.0
    # Alcuni actor esprimono il rating su scala 0-50 (bolle x10).
    if rating > 5:
        rating = rating / 10.0

    raw_date = item.get("publishedDate") or item.get("date") or item.get("reviewDate")
    review_date = _parse_date(raw_date) or date.today()

    language = (
        item.get("lang")
        or item.get("originalLanguage")
        or item.get("language")
        or item.get("reviewLanguage")
        or "und"
    )

    return {
        "external_review_id": str(item.get("id") or item.get("reviewId") or item.get("url", ""))[:120],
        "author": _extract_author(item),
        "text": text,
        "rating": max(1.0, min(5.0, rating)),
        "language": str(language)[:10],
        "review_date": review_date.isoformat(),
    }


def _parse_date(raw: Any) -> Optional[date]:
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        try:
            return datetime.utcfromtimestamp(raw / 1000 if raw > 10**12 else raw).date()
        except (ValueError, OSError):
            return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%B %d, %Y"):
        try:
            return datetime.strptime(str(raw), fmt).date()
        except ValueError:
            continue
    return None


def fetch_tripadvisor_reviews(tripadvisor_url: str, max_reviews: int = 100) -> list[dict[str, Any]]:
    """Avvia l'Apify Actor configurato e restituisce le recensioni normalizzate.

    Solleva ApifyUnavailableError se il token non e' configurato o se la run
    Apify fallisce/va in timeout: il chiamante decide come gestire il fallback.
    """
    settings = get_settings()
    if not settings.apify_api_token:
        raise ApifyUnavailableError("APIFY_API_TOKEN non configurato: uso il dataset di fallback.")

    tripadvisor_url = canonicalize_tripadvisor_url(tripadvisor_url)

    # Nomi dei campi conformi all'input schema dell'Actor
    # `maxcopell/tripadvisor-reviews` (vedi console Apify -> Input).
    run_input = {
        "startUrls": [{"url": tripadvisor_url}],
        "maxItemsPerQuery": max_reviews,
        "reviewRatings": ["ALL_REVIEW_RATINGS"],
        "reviewsLanguages": ["ALL_REVIEW_LANGUAGES"],
        # Manteniamo la lingua originale delle recensioni (utile per l'analisi
        # multilingua di sentiment/aspetti) invece della traduzione automatica.
        "disableMachineTranslations": True,
        "scrapeReviewerInfo": False,
    }
    actor = settings.apify_tripadvisor_actor_id.replace("/", "~")
    # Endpoint sincrono: avvia la run, attende il completamento e restituisce
    # direttamente gli item del dataset in una sola chiamata (niente polling).
    sync_url = (
        f"{APIFY_API_BASE}/acts/{actor}/run-sync-get-dataset-items"
        f"?token={settings.apify_api_token}"
        f"&timeout={settings.apify_run_timeout_secs}"
        f"&limit={max_reviews}"
    )

    try:
        with httpx.Client(timeout=settings.apify_run_timeout_secs + 15) as client:
            resp = client.post(sync_url, json=run_input)
            resp.raise_for_status()
            raw_items = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Chiamata Apify fallita: %s", exc)
        raise ApifyUnavailableError(str(exc)) from exc

    if isinstance(raw_items, dict):  # risposta di errore Apify (es. actor non approvato)
        raise ApifyUnavailableError(str(raw_items.get("error", raw_items)))

    normalized = [normalize_apify_item(it) for it in raw_items]
    return [r for r in normalized if r is not None]
