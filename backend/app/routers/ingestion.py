"""
Endpoint per l'acquisizione dei dati: avvio di una ingestion mirata (Apify/
Tripadvisor con fallback automatico al dataset di esempio) oppure seeding
completo del dataset dimostrativo incluso nel progetto.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import IngestionJobOut, IngestionRequest
from app.services import ingestion_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", response_model=IngestionJobOut)
def run_ingestion(payload: IngestionRequest, db: Session = Depends(get_db)):
    return ingestion_service.run_ingestion(db, payload)


@router.post("/seed-demo-data")
def seed_demo_data(db: Session = Depends(get_db)):
    """Popola il database con l'intero dataset di esempio (12 strutture in 4
    citta', centinaia di recensioni multilingua) cosi' l'applicazione ha
    subito dati significativi da mostrare durante la demo. Idempotente:
    rieseguendolo su un DB gia' popolato non crea duplicati."""
    return ingestion_service.seed_demo_dataset(db)
