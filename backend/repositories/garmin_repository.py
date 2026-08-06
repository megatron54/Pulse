"""Repositorio de datos Garmin: persistencia + señales derivadas de
historial (baseline y tendencia de HRV) que engine.periodization
necesita pero que Garmin no entrega ya calculadas para un solo día.

Principio "usar tendencia vs. baseline personal, no el dato de un solo
día" (ver 00-research/06-periodizacion-ciencia-deportiva.md).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.schema import GarminActivity, GarminDailyMetrics

_DIAS_BASELINE = 28
_DIAS_TENDENCIA = 7
_DIAS_HISTORIAL_ACTIVIDADES_POR_DEFECTO = 90


def save_daily_metrics(
    session: Session, user_id: int, fecha: date, raw: dict[str, Any]
) -> GarminDailyMetrics:
    """Persiste una fila append-only con los campos normalizados del
    payload de garmin_sync.client.get_daily_recovery_raw. Nunca
    sobreescribe una sincronización previa del mismo día.

    Épica A del plan de expansión (02-roadmap/03-vision-produccion.md):
    hrv_status/vo2max/stress_avg/resting_hr existían como columnas
    desde el modelo original pero nunca se rellenaban porque el
    cliente nunca los pedía - `.get(...)` con default None mantiene el
    comportamiento "unknown is not zero" para raws antiguos/parciales
    que todavía no traigan estas claves."""
    fila = GarminDailyMetrics(
        user_id=user_id,
        fecha=fecha,
        hrv_value=raw.get("hrv_today"),
        hrv_status=raw.get("hrv_status"),
        training_readiness=raw.get("training_readiness"),
        body_battery_am=raw.get("body_battery_am"),
        sleep_score=raw.get("sleep_score"),
        stress_avg=raw.get("stress_avg"),
        resting_hr=raw.get("resting_hr"),
        vo2max=raw.get("vo2max"),
    )
    session.add(fila)
    session.commit()
    session.refresh(fila)
    return fila


def get_hrv_baseline_28d(session: Session, user_id: int, as_of: date) -> float | None:
    """Media de HRV de los 28 días anteriores a `as_of` (sin incluir
    `as_of`). Devuelve None si no hay ningún dato de HRV en la ventana
    (principio "unknown is not zero" - no se inventa una baseline de 0)."""
    return _media_hrv_en_ventana(session, user_id, as_of, _DIAS_BASELINE)


def get_hrv_trend_7d(session: Session, user_id: int, as_of: date) -> float | None:
    """Pendiente relativa simple de HRV en los últimos 7 días: compara la
    media de la primera mitad de la ventana contra la segunda mitad, y
    expresa el cambio como fracción de la media de la ventana completa.
    Un valor positivo indica HRV subiendo, negativo indica HRV bajando -
    coherente con el signo esperado por engine.periodization
    (`hrv_trend_7d < -0.10` dispara un red flag)."""
    fecha_inicio = as_of - timedelta(days=_DIAS_TENDENCIA)
    valores = _valores_hrv_en_rango(session, user_id, fecha_inicio, as_of)
    if len(valores) < 2:
        return None

    mitad = len(valores) // 2
    primera_mitad = valores[:mitad] if mitad > 0 else valores[:1]
    segunda_mitad = valores[mitad:]
    media_total = sum(valores) / len(valores)
    if media_total == 0:
        return None

    cambio = (sum(segunda_mitad) / len(segunda_mitad)) - (
        sum(primera_mitad) / len(primera_mitad)
    )
    return cambio / media_total


def _media_hrv_en_ventana(
    session: Session, user_id: int, as_of: date, dias: int
) -> float | None:
    fecha_inicio = as_of - timedelta(days=dias)
    valores = _valores_hrv_en_rango(session, user_id, fecha_inicio, as_of)
    if not valores:
        return None
    return sum(valores) / len(valores)


def _valores_hrv_en_rango(
    session: Session, user_id: int, fecha_inicio: date, fecha_fin_exclusiva: date
) -> list[float]:
    stmt = (
        select(GarminDailyMetrics.fecha, GarminDailyMetrics.hrv_value)
        .where(GarminDailyMetrics.user_id == user_id)
        .where(GarminDailyMetrics.fecha >= fecha_inicio)
        .where(GarminDailyMetrics.fecha < fecha_fin_exclusiva)
        .where(GarminDailyMetrics.hrv_value.is_not(None))
        .order_by(GarminDailyMetrics.fecha.asc())
    )
    filas = session.execute(stmt).all()
    return [hrv for _fecha, hrv in filas]


def save_activity_if_new(session: Session, user_id: int, actividad: dict[str, Any]) -> bool:
    """Persiste una actividad de `garmin_sync.activity_mapper.
    map_raw_activity` si no existe ya una fila para (user_id,
    activity_id) - idempotente por diseño: resincronizar el mismo rango
    de fechas (p.ej. tras un fallo parcial de red a mitad de sync, ver
    docstring de `services.garmin_activity_service.sync_activities`)
    nunca debe duplicar actividades. Devuelve True si se insertó una
    fila nueva, False si ya existía (para que la capa de servicio pueda
    reportar cuántas eran realmente nuevas).

    El check-then-insert de abajo es solo una optimización para el caso
    común (evita el roundtrip de un INSERT fallido en el 99% de los
    casos donde de verdad es nueva); la garantía real de no-duplicado la
    da el `UniqueConstraint(user_id, activity_id)` del modelo - si dos
    sincronizaciones corrieran en paralelo y ambas pasaran el check
    (carrera), el `IntegrityError` del segundo INSERT se captura aquí y
    se trata igual que "ya existía", nunca se propaga como un 500."""
    ya_existe = (
        session.query(GarminActivity)
        .filter_by(user_id=user_id, activity_id=actividad["activity_id"])
        .first()
        is not None
    )
    if ya_existe:
        return False

    session.add(GarminActivity(user_id=user_id, **actividad))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return False
    return True


def get_activity_history(
    session: Session, user_id: int, as_of: date, days: int = _DIAS_HISTORIAL_ACTIVIDADES_POR_DEFECTO
) -> list[GarminActivity]:
    """Actividades del usuario en `[as_of-days+1, as_of]`, más recientes
    primero - para el listado de la página Garmin del frontend."""
    fecha_inicio = as_of - timedelta(days=days - 1)
    stmt = (
        select(GarminActivity)
        .where(GarminActivity.user_id == user_id)
        .where(GarminActivity.fecha >= fecha_inicio)
        .where(GarminActivity.fecha <= as_of)
        .order_by(GarminActivity.fecha.desc())
    )
    return list(session.execute(stmt).scalars().all())
