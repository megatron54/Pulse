"""Capa de servicio delgada de solo lectura para el historial de
actividades Garmin ya ingeridas - valida que el usuario exista (mismo
patrón que `services.habit_service`/`services.food_log_service`) antes
de delegar en el repositorio."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from sqlalchemy.orm import Session

from models.schema import GarminActivity, GarminDailyMetrics, UserProfile
from repositories.garmin_repository import get_activity_history, get_daily_metrics_history
from services.errors import EntityNotFoundError

_DIAS_HISTORIAL_POR_DEFECTO = 90
_SEMANAS_VOLUMEN_POR_DEFECTO = 12


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


@dataclass(frozen=True)
class WeeklyVolume:
    """Épica 10 del plan de expansión: un punto de la gráfica de
    volumen semanal. `distancia_total_m`/`duracion_total_seg` son
    `None` cuando ninguna actividad de esa semana trae ese campo
    (ej. gimnasio no trae distancia útil, ver punto 2 del doc vivo) -
    "unknown is not zero", nunca se suma como si fuera 0. `num_sesiones`
    en cambio SÍ es un conteo real, siempre entero (0 si no hubo
    ninguna actividad esa semana - una semana real sin entrenar no es
    lo mismo que una semana fuera de la ventana solicitada)."""

    semana_inicio: date  # lunes de esa semana ISO
    distancia_total_m: float | None
    duracion_total_seg: int | None
    num_sesiones: int


def get_weekly_volume_for_user(
    session: Session,
    user_id: int,
    as_of: date,
    categoria: CategoriaDeporte,
    weeks: int = _SEMANAS_VOLUMEN_POR_DEFECTO,
) -> list[WeeklyVolume]:
    """Agrega el historial de actividades de una categoría de deporte
    (Épica D) en `weeks` semanas ISO (lunes-domingo), para las gráficas
    de volumen por deporte del backlog MUST-HAVE (Épica 10 del plan de
    expansión). Devuelve SIEMPRE `weeks` puntos, en orden cronológico
    ascendente, con las semanas sin ninguna actividad incluidas
    explícitamente en 0 sesiones - la API nunca oculta un hueco real de
    entrenamiento aunque el frontend de hoy (WeeklyVolumeChart) decida
    graficar solo las semanas con dato, igual que WeightTrendCard/
    ReadinessTrendCard: quien consuma este endpoint para otro fin
    (ej. una tabla, o un futuro gráfico con eje temporal real) tiene el
    0 explícito disponible sin tener que volver a llamar al backend."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    lunes_semana_actual = as_of - timedelta(days=as_of.weekday())
    primera_semana_inicio = lunes_semana_actual - timedelta(weeks=weeks - 1)
    dias_totales = (as_of - primera_semana_inicio).days + 1

    actividades = get_activity_history_for_user(
        session, user_id, as_of=as_of, days=dias_totales, categoria=categoria
    )

    actividades_por_semana: dict[date, list[GarminActivity]] = {
        primera_semana_inicio + timedelta(weeks=i): [] for i in range(weeks)
    }
    for actividad in actividades:
        semana_inicio = actividad.fecha - timedelta(days=actividad.fecha.weekday())
        if semana_inicio in actividades_por_semana:
            actividades_por_semana[semana_inicio].append(actividad)

    resultado: list[WeeklyVolume] = []
    for semana_inicio in sorted(actividades_por_semana):
        acts = actividades_por_semana[semana_inicio]
        distancias = [a.distancia_m for a in acts if a.distancia_m is not None]
        duraciones = [a.duracion_seg for a in acts if a.duracion_seg is not None]
        resultado.append(
            WeeklyVolume(
                semana_inicio=semana_inicio,
                distancia_total_m=sum(distancias) if distancias else None,
                duracion_total_seg=sum(duraciones) if duraciones else None,
                num_sesiones=len(acts),
            )
        )
    return resultado
