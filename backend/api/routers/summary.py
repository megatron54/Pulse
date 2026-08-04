"""Resumen periódico (semanal/mensual) de tendencias - Épica MUST-HAVE
#4 de 02-roadmap/03-vision-produccion.md."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import PeriodicSummaryOut
from services.periodic_summary_service import compute_periodic_summary

router = APIRouter(
    prefix="/users/{user_id}",
    tags=["summary"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/summary", response_model=PeriodicSummaryOut)
def get_periodic_summary(
    user_id: int,
    as_of: date | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
) -> PeriodicSummaryOut:
    resultado = compute_periodic_summary(db, user_id, as_of=as_of or date.today(), days=days)
    return PeriodicSummaryOut.model_validate(resultado, from_attributes=True)
