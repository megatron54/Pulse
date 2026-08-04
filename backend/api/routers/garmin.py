"""Historial de actividades Garmin (Épica 2 de 02-roadmap/
03-vision-produccion.md) - solo LECTURA de lo ya ingerido por el
scheduler nocturno (`services.scheduler_service.
run_daily_activity_sync_for_all_users`). No hay endpoint de sync manual
todavía: sin credenciales reales (Fase H bloqueada), no hay nada que
disparar desde la API - cuando exista, este router es el lugar natural
para añadirlo."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import GarminActivityOut
from services.garmin_query_service import get_activity_history_for_user

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
    db: Session = Depends(get_db),
) -> list[GarminActivityOut]:
    actividades = get_activity_history_for_user(
        db, user_id, as_of=as_of or date.today(), days=days
    )
    return [GarminActivityOut.model_validate(a, from_attributes=True) for a in actividades]
