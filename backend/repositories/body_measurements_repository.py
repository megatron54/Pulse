"""Repositorio de mediciones corporales."""
from __future__ import annotations

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
