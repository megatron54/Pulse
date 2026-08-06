"""Historial de actividades y de métricas diarias de recovery de Garmin
(Épica 2 y Épica C de 02-roadmap/03-vision-produccion.md) - solo
LECTURA de lo ya ingerido por el scheduler nocturno
(`services.scheduler_service`). No hay endpoint de sync manual todavía:
sin credenciales reales (Fase H bloqueada), no hay nada que disparar
desde la API - cuando exista, este router es el lugar natural para
añadirlo."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import GarminActivityOut, GarminDailyMetricsOut
from services.garmin_query_service import (
    CategoriaDeporte,
    get_activity_history_for_user,
    get_daily_metrics_history_for_user,
)

router = APIRouter(
    prefix="/users/{user_id}/garmin",
    tags=["garmin"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/activities", response_model=list[GarminActivityOut])
def get_activities(
    user_id: int,
    days: int = Query(default=90, ge=1, le=365),
    as_of: date | None = Query(default=None),
    categoria: CategoriaDeporte | None = Query(
        default=None,
        description="Filtra por categoría de deporte (running/ciclismo/gimnasio) - agrupa varios typeKey reales de Garmin.",
    ),
    db: Session = Depends(get_db),
) -> list[GarminActivityOut]:
    actividades = get_activity_history_for_user(
        db, user_id, as_of=as_of or date.today(), days=days, categoria=categoria
    )
    return [GarminActivityOut.model_validate(a, from_attributes=True) for a in actividades]


@router.get("/health-history", response_model=list[GarminDailyMetricsOut])
def get_health_history(
    user_id: int,
    days: int = Query(default=90, ge=1, le=365),
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[GarminDailyMetricsOut]:
    """Historial completo de recovery (HRV, hrv_status, body battery,
    training readiness, sleep score, stress, resting HR, VO2max) - más
    reciente primero. Alimenta la página de Salud/Recovery y el
    resumen del dashboard "Hoy" (Épica C/E/J del plan de expansión)."""
    metricas = get_daily_metrics_history_for_user(
        db, user_id, as_of=as_of or date.today(), days=days
    )
    return [GarminDailyMetricsOut.model_validate(m, from_attributes=True) for m in metricas]
