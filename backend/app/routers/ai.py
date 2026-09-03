"""
Endpoint per le funzionalita' di AI generativa: sintesi/report descrittivi,
analisi competitiva tra strutture simili e suggerimenti di interventi
migliorativi basati sulle criticita' emerse dalle recensioni. Ogni report
generato viene anche persistito in `analysis_reports` per tenerne uno storico.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import AnalysisReport, Property, ReportType
from app.schemas.schemas import (
    AnalysisReportOut,
    ComparisonRequest,
    SuggestionsRequest,
    SummaryRequest,
)
from app.services.nlp_service import get_ai_provider

router = APIRouter(prefix="/ai", tags=["ai-insights"])


def _check_properties_exist(db: Session, property_ids: list[str]) -> None:
    for pid in property_ids:
        if db.get(Property, pid) is None:
            raise HTTPException(status_code=404, detail=f"Struttura {pid} non trovata")


@router.post("/summary", response_model=AnalysisReportOut)
def generate_summary(payload: SummaryRequest, db: Session = Depends(get_db)):
    _check_properties_exist(db, [payload.property_id])
    provider = get_ai_provider()
    content = provider.generate_summary(db, payload.property_id)

    report = AnalysisReport(
        report_type=ReportType.summary,
        property_ids=[payload.property_id],
        content=content,
        ai_provider=provider.name,
        ai_model=provider.model_label,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/comparison", response_model=AnalysisReportOut)
def generate_comparison(payload: ComparisonRequest, db: Session = Depends(get_db)):
    _check_properties_exist(db, payload.property_ids)
    provider = get_ai_provider()
    content = provider.generate_comparison(db, payload.property_ids)

    report = AnalysisReport(
        report_type=ReportType.competitive_comparison,
        property_ids=payload.property_ids,
        content=content,
        ai_provider=provider.name,
        ai_model=provider.model_label,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/suggestions", response_model=AnalysisReportOut)
def generate_suggestions(payload: SuggestionsRequest, db: Session = Depends(get_db)):
    _check_properties_exist(db, [payload.property_id])
    provider = get_ai_provider()
    content = provider.generate_suggestions(db, payload.property_id)

    report = AnalysisReport(
        report_type=ReportType.improvement_suggestions,
        property_ids=[payload.property_id],
        content=content,
        ai_provider=provider.name,
        ai_model=provider.model_label,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/reports", response_model=list[AnalysisReportOut])
def list_reports(
    db: Session = Depends(get_db),
    limit: int = 50,
    property_id: str | None = None,
    report_type: ReportType | None = None,
):
    """Report AI generati in precedenza, dal piu' recente. Filtrabili per
    struttura e per tipo: il Front-End li usa per ripresentare l'ultimo report
    salvato senza doverlo rigenerare a ogni apertura della pagina."""
    from sqlalchemy import select

    stmt = select(AnalysisReport).order_by(AnalysisReport.generated_at.desc())
    if report_type is not None:
        stmt = stmt.where(AnalysisReport.report_type == report_type)
    rows = list(db.execute(stmt.limit(200)).scalars())
    if property_id is not None:
        rows = [r for r in rows if property_id in (r.property_ids or [])]
    return rows[:limit]
