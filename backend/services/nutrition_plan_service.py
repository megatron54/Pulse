"""Planes de fase de peso (déficit/superávit/mantenimiento) con
DURACIÓN determinada - petición explícita del usuario: "planes de
deficit, superhabit y mantenimiento dedicados, con duración
determinada, como tu nutricionista personal".

Sustituye el uso de `UserProfile.fase_peso_actual` como campo estático
sin fecha por un historial real de planes (append-only, solo uno
activo a la vez). `UserProfile.fase_peso_actual` se mantiene en
sincronía al crear un plan - así `services.nutrition_service.
compute_daily_nutrition_target` (que lee ese campo) no necesita ningún
cambio para respetar el plan activo."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.schema import NutritionPlan, UserProfile
from services.errors import EntityNotFoundError


def create_nutrition_plan(
    session: Session,
    *,
    user_id: int,
    fase: str,
    semanas_duracion: int,
    fecha_inicio: date,
    motivo: str | None = None,
) -> NutritionPlan:
    """Crea un plan nuevo y lo activa, desactivando cualquier plan
    previo del usuario (nunca dos planes activos a la vez)."""
    usuario = session.get(UserProfile, user_id)
    if usuario is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")
    if semanas_duracion <= 0:
        raise ValueError("semanas_duracion debe ser un entero positivo")

    session.execute(
        NutritionPlan.__table__.update()
        .where(NutritionPlan.user_id == user_id, NutritionPlan.activo.is_(True))
        .values(activo=False)
    )

    plan = NutritionPlan(
        user_id=user_id,
        fase=fase,
        semanas_duracion=semanas_duracion,
        fecha_inicio=fecha_inicio,
        motivo=motivo,
        activo=True,
    )
    session.add(plan)

    # Mantiene UserProfile.fase_peso_actual en sincronía - ver docstring
    # del módulo.
    usuario.fase_peso_actual = fase

    session.commit()
    session.refresh(plan)
    return plan


@dataclass(frozen=True)
class ActiveNutritionPlan:
    plan: NutritionPlan
    fecha_fin: date
    dias_restantes: int
    expirado: bool


def get_active_nutrition_plan(
    session: Session, user_id: int, as_of: date
) -> ActiveNutritionPlan | None:
    """Plan activo del usuario, con `fecha_fin`/`dias_restantes`/
    `expirado` ya calculados (nunca almacenados, ver docstring de
    `NutritionPlan`) - `None` si no hay ningún plan activo ("unknown is
    not zero": la ausencia de plan es un estado real, no se inventa
    uno por defecto)."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    plan = session.execute(
        select(NutritionPlan).where(
            NutritionPlan.user_id == user_id, NutritionPlan.activo.is_(True)
        )
    ).scalar_one_or_none()
    if plan is None:
        return None

    fecha_fin = plan.fecha_inicio + timedelta(weeks=plan.semanas_duracion)
    dias_restantes = max(0, (fecha_fin - as_of).days)
    expirado = as_of >= fecha_fin

    return ActiveNutritionPlan(
        plan=plan, fecha_fin=fecha_fin, dias_restantes=dias_restantes, expirado=expirado
    )
