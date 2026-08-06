"""Capa de servicio delgada de solo lectura para el historial de
actividades Garmin ya ingeridas - valida que el usuario exista (mismo
patrón que `services.habit_service`/`services.food_log_service`) antes
de delegar en el repositorio."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from models.schema import GarminActivity, GarminDailyMetrics, UserProfile
from repositories.garmin_repository import get_activity_history, get_daily_metrics_history
from services.errors import EntityNotFoundError

_DIAS_HISTORIAL_POR_DEFECTO = 90


def get_activity_history_for_user(
    session: Session, user_id: int, as_of: date, days: int = _DIAS_HISTORIAL_POR_DEFECTO
) -> list[GarminActivity]:
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")
    return get_activity_history(session, user_id, as_of, days)


def get_daily_metrics_history_for_user(
    session: Session, user_id: int, as_of: date, days: int = _DIAS_HISTORIAL_POR_DEFECTO
) -> list[GarminDailyMetrics]:
    """Épica C del plan de expansión (02-roadmap/03-vision-produccion.md):
    historial completo de recovery (HRV, hrv_status, body battery,
    training readiness, sleep score, stress, resting HR, VO2max) para
    la página de Salud/Recovery y el resumen del dashboard "Hoy"."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")
    return get_daily_metrics_history(session, user_id, as_of, days)
