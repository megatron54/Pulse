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
from sqlalchemy.orm import Session

from models.schema import GarminDailyMetrics

_DIAS_BASELINE = 28
_DIAS_TENDENCIA = 7


def save_daily_metrics(
    session: Session, user_id: int, fecha: date, raw: dict[str, Any]
) -> GarminDailyMetrics:
    """Persiste una fila append-only con los campos normalizados del
    payload de garmin_sync.client.get_daily_recovery_raw. Nunca
    sobreescribe una sincronización previa del mismo día."""
    fila = GarminDailyMetrics(
        user_id=user_id,
        fecha=fecha,
        hrv_value=raw.get("hrv_today"),
        training_readiness=raw.get("training_readiness"),
        body_battery_am=raw.get("body_battery_am"),
        sleep_score=raw.get("sleep_score"),
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
