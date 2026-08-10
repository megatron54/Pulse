"""Capa de servicio delgada sobre `repositories.habit_log_repository`:
única responsabilidad añadida aquí es validar que el usuario exista
antes de escribir (mismo patrón que otros servicios que validan el
usuario antes de tocar el repositorio) - hallazgo de code-review: sin
esto, en Postgres real un `IntegrityError` de FK escaparía como 500
sin traducir en vez de un 404 limpio)."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from models.schema import UserProfile
from repositories.habit_log_repository import set_habits_for_date
from services.errors import EntityNotFoundError


def set_habits(session: Session, user_id: int, target_date: date, habitos: list[str]) -> None:
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")
    set_habits_for_date(session, user_id, target_date, habitos)
