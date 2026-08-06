"""Capa de servicio delgada de solo lectura para el historial de
actividades Garmin ya ingeridas - valida que el usuario exista (mismo
patrón que `services.habit_service`/`services.food_log_service`) antes
de delegar en el repositorio."""
from __future__ import annotations

from datetime import date
from enum import Enum

from sqlalchemy.orm import Session

from models.schema import GarminActivity, GarminDailyMetrics, UserProfile
from repositories.garmin_repository import get_activity_history, get_daily_metrics_history
from services.errors import EntityNotFoundError

_DIAS_HISTORIAL_POR_DEFECTO = 90


class CategoriaDeporte(str, Enum):
    """Épica D/G del plan de expansión (02-roadmap/03-vision-produccion.md):
    agrupa varios `typeKey` reales de Garmin bajo una categoría de
    página. **Sin verificar contra un payload real todavía** (el
    usuario aún no ha registrado ninguna actividad de estos tipos en
    su cuenta emparejada - `garmin_activity` está vacía a fecha de
    esta épica) - la lista de `typeKey` viene de la investigación ya
    documentada en el punto 2 del doc vivo (running/cycling/
    strength_training) más variantes de sentido común de la propia
    taxonomía pública de Garmin Connect. Revisar/ampliar esta lista en
    cuanto existan actividades reales de cada tipo para confirmar los
    `typeKey` exactos que usa el dispositivo del usuario."""

    RUNNING = "running"
    CICLISMO = "ciclismo"
    GIMNASIO = "gimnasio"


_TIPOS_GARMIN_POR_CATEGORIA: dict[CategoriaDeporte, list[str]] = {
    CategoriaDeporte.RUNNING: [
        "running",
        "trail_running",
        "treadmill_running",
        "track_running",
        "street_running",
    ],
    CategoriaDeporte.CICLISMO: [
        "cycling",
        "road_biking",
        "mountain_biking",
        "indoor_cycling",
        "gravel_cycling",
        "virtual_ride",
    ],
    CategoriaDeporte.GIMNASIO: [
        "strength_training",
        "indoor_cardio",
        "fitness_equipment",
    ],
}


def get_activity_history_for_user(
    session: Session,
    user_id: int,
    as_of: date,
    days: int = _DIAS_HISTORIAL_POR_DEFECTO,
    categoria: CategoriaDeporte | None = None,
) -> list[GarminActivity]:
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")
    tipos = _TIPOS_GARMIN_POR_CATEGORIA[categoria] if categoria is not None else None
    return get_activity_history(session, user_id, as_of, days, tipos=tipos)


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
