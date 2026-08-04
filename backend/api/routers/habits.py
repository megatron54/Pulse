"""Diario de hábitos + correlación con recovery (Épica MUST-HAVE #3 de
02-roadmap/03-vision-produccion.md, análogo al "Journal" de WHOOP)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import Habito, HabitCorrelationOut, SetHabitsRequest
from services.habit_correlation_service import compute_habit_correlation
from services.habit_service import set_habits as set_habits_service

router = APIRouter(
    prefix="/users/{user_id}/habits",
    tags=["habits"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", status_code=204)
def set_habits(
    user_id: int,
    payload: SetHabitsRequest,
    target_date: date = Query(alias="date"),
    db: Session = Depends(get_db),
) -> None:
    """Guarda el check-in de hábitos completo de `target_date`
    (reemplaza cualquier registro previo de ese día, ver docstring de
    `set_habits_for_date`)."""
    set_habits_service(db, user_id, target_date, list(payload.habitos))


@router.get("/correlation", response_model=HabitCorrelationOut)
def get_habit_correlation(
    user_id: int,
    habito: Habito,
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HabitCorrelationOut:
    # as_of por defecto es la fecha del SERVIDOR, no la del usuario -
    # mismo patrón/advertencia que readiness.py y body_composition.py:
    # los clientes deben enviarlo explícito (el frontend ya lo hace vía
    # `todayLocalDate()`, ver lib/api.ts).
    resultado = compute_habit_correlation(db, user_id, habito, as_of=as_of or date.today())
    return HabitCorrelationOut.model_validate(resultado, from_attributes=True)
