"""Repositorio de historial de readiness — usado por engine.guardrails
para detectar rachas de RED sostenido (ver should_pause_calorie_deficit
en 00-research/06-periodizacion-ciencia-deportiva.md)."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.periodization import ReadinessLevel
from models.schema import ReadinessLog


def get_latest_readiness_level(
    session: Session, user_id: int, target_date: date
) -> ReadinessLevel | None:
    """El resultado de readiness más reciente para `user_id` en
    `target_date` (append-only: puede haber varias filas si se
    re-ejecutó el check-in ese día - se usa siempre la última, mismo
    criterio que `services.session_service` y `services.readiness_service`).
    Devuelve None si no hay ningún ReadinessLog para ese día.

    Centraliza esta consulta para que tanto `services.session_service`
    como la capa HTTP (api/routers/session.py) usen exactamente la misma
    lógica, evitando que dos queries independientes puedan divergir.
    """
    log = (
        session.query(ReadinessLog)
        .filter_by(user_id=user_id, fecha=target_date)
        .order_by(ReadinessLog.created_at.desc(), ReadinessLog.id.desc())
        .first()
    )
    return ReadinessLevel(log.resultado) if log is not None else None


def get_recent_readiness_levels(
    session: Session, user_id: int, as_of: date, n: int
) -> list[ReadinessLevel]:
    """Últimos `n` resultados de readiness ANTERIORES a `as_of` (no
    incluye el día actual, que aún no se ha calculado en el momento en
    que se consulta este historial), en orden cronológico ascendente -
    el formato que espera engine.guardrails.should_pause_calorie_deficit."""
    fecha_inicio = as_of - timedelta(days=n)
    stmt = (
        select(ReadinessLog.resultado)
        .where(ReadinessLog.user_id == user_id)
        .where(ReadinessLog.fecha >= fecha_inicio)
        .where(ReadinessLog.fecha < as_of)
        .order_by(ReadinessLog.fecha.asc())
    )
    filas = session.execute(stmt).scalars().all()
    return [ReadinessLevel(valor) for valor in filas]


def get_readiness_history(
    session: Session, user_id: int, as_of: date, days: int
) -> list[ReadinessLog]:
    """Historial de ReadinessLog de los últimos `days` días, INCLUYENDO
    `as_of` - para dashboards de tendencia (Fase I). A diferencia de
    `get_recent_readiness_levels` (usado por guardrails, que excluye
    el día actual a propósito porque ese aún se está calculando en el
    momento de la consulta), aquí sí interesa el dato de hoy si ya existe.
    """
    fecha_inicio = as_of - timedelta(days=days)
    stmt = (
        select(ReadinessLog)
        .where(ReadinessLog.user_id == user_id)
        .where(ReadinessLog.fecha >= fecha_inicio)
        .where(ReadinessLog.fecha <= as_of)
        .order_by(ReadinessLog.fecha.asc(), ReadinessLog.id.asc())
    )
    return list(session.execute(stmt).scalars().all())
