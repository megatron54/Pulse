"""Historial de actividades y de métricas diarias de recovery de Garmin
(Épica 2 y Épica C de 02-roadmap/03-vision-produccion.md) - solo
LECTURA de lo ya ingerido por el scheduler nocturno
(`services.scheduler_service`). No hay endpoint de sync manual todavía:
sin credenciales reales (Fase H bloqueada), no hay nada que disparar
desde la API - cuando exista, este router es el lugar natural para
añadirlo."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import (
    GarminActivityOut,
    GarminDailyMetricsOut,
    GarminIntradayPointOut,
    HealthNarrativeOut,
    WeeklyVolumeOut,
)
from coach.gemini_client import build_gemini_client_if_configured
from coach.health_narrative_service import generate_health_narrative_for_user
from services.garmin_query_service import (
    CategoriaDeporte,
    get_activity_history_for_user,
    get_daily_metrics_history_for_user,
    get_intraday_history_for_user,
    get_weekly_volume_for_user,
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


@router.get("/health-narrative", response_model=HealthNarrativeOut)
def get_health_narrative(
    user_id: int,
    fecha: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HealthNarrativeOut:
    """Explicación conversacional (Capa 3, Épica H) del estado de
    recovery ya decidido para `fecha` (por defecto hoy). `text`/`source`
    vienen `None` si todavía no existe ningún ReadinessLog para ese
    día - nunca se inventa una explicación de una decisión que no se
    ha tomado."""
    resultado = generate_health_narrative_for_user(
        db,
        user_id,
        fecha=fecha or date.today(),
        gemini_client=build_gemini_client_if_configured(),
    )
    if resultado is None:
        return HealthNarrativeOut(text=None, source=None)
    return HealthNarrativeOut(text=resultado.text, source=resultado.source)


@router.get("/activities/volume", response_model=list[WeeklyVolumeOut])
def get_weekly_volume(
    user_id: int,
    categoria: CategoriaDeporte = Query(
        ...,
        description="Categoría de deporte (running/ciclismo/gimnasio) - obligatoria, a diferencia de /activities donde es opcional.",
    ),
    weeks: int = Query(default=12, ge=1, le=52),
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[WeeklyVolumeOut]:
    """Volumen semanal agregado (distancia, duración, número de
    sesiones) de una categoría de deporte - Épica 10 del plan de
    expansión (gráficas de volumen por deporte, backlog MUST-HAVE).
    Devuelve SIEMPRE `weeks` puntos en orden ascendente, incluyendo
    semanas sin actividad con 0 sesiones explícitas."""
    semanas = get_weekly_volume_for_user(
        db, user_id, as_of=as_of or date.today(), categoria=categoria, weeks=weeks
    )
    return [WeeklyVolumeOut.model_validate(s, from_attributes=True) for s in semanas]


@router.get("/intraday", response_model=list[GarminIntradayPointOut])
def get_intraday_history(
    user_id: int,
    metrica: Literal["heart_rate", "body_battery", "stress"] = Query(
        ..., description="Qué serie minuto a minuto consultar."
    ),
    fecha: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[GarminIntradayPointOut]:
    """Serie minuto a minuto de `metrica` para `fecha` (por defecto
    hoy) - petición explícita del usuario: "el ritmo cardiaco, body
    battery, etc son valores que cambian cada minuto, quiero todo ese
    histórico, no me vale que cojas la media del día". Complementa a
    `/health-history` (un solo valor agregado por día). Devuelve lista
    vacía si el scheduler todavía no ha sincronizado ese día - "unknown
    is not zero", nunca se interpola ni se rellena un hueco."""
    puntos = get_intraday_history_for_user(db, user_id, metrica, fecha or date.today())
    return [GarminIntradayPointOut.model_validate(p, from_attributes=True) for p in puntos]
