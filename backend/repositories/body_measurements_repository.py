"""Repositorio de mediciones corporales."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.schema import BodyMeasurements


def get_latest_weight_kg(session: Session, user_id: int) -> float | None:
    """Peso más reciente registrado (por fecha, desempatando por
    created_at si hay múltiples filas el mismo día - coherente con el
    principio append-only: la última sincronización/entrada manual
    gana)."""
    stmt = (
        select(BodyMeasurements.peso_kg)
        .where(BodyMeasurements.user_id == user_id)
        .order_by(
            BodyMeasurements.fecha.desc(),
            BodyMeasurements.created_at.desc(),
            # created_at tiene resolución de segundo: dos filas insertadas
            # en el mismo segundo (sync batch, doble entrada rápida) dejan
            # el desempate anterior indefinido. El id autoincremental es
            # monótono y garantiza "la última fila insertada gana".
            BodyMeasurements.id.desc(),
        )
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def get_weight_history(
    session: Session, user_id: int, as_of: date, days: int
) -> list[BodyMeasurements]:
    """Mediciones de los últimos `days` días (incluyendo `as_of`), en
    orden cronológico ascendente - para dashboards de tendencia (Fase I).

    Nota de diseño: a diferencia de `get_latest_weight_kg` (que aplica
    "la última fila del día gana"), esta función devuelve TODAS las
    filas de cada día sin agregar - útil para auditar re-sincronizaciones,
    pero un dashboard que solo quiera un punto por día debe agregar él
    mismo (quedarse con la última fila de cada `fecha`). Desempate
    intra-día por `id` (monótono), igual que el resto del repositorio.
    """
    fecha_inicio = as_of - timedelta(days=days)
    stmt = (
        select(BodyMeasurements)
        .where(BodyMeasurements.user_id == user_id)
        .where(BodyMeasurements.fecha >= fecha_inicio)
        .where(BodyMeasurements.fecha <= as_of)
        .order_by(BodyMeasurements.fecha.asc(), BodyMeasurements.id.asc())
    )
    return list(session.execute(stmt).scalars().all())
