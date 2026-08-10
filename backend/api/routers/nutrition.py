from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import (
    ActiveNutritionPlanOut,
    NutritionPhaseRecommendationOut,
    NutritionPlanOut,
    NutritionPlanRequest,
    NutritionTargetOut,
    NutritionTargetRequest,
)
from services.nutrition_plan_recommendation_service import recommend_next_phase
from services.nutrition_plan_service import create_nutrition_plan, get_active_nutrition_plan
from services.nutrition_service import compute_daily_nutrition_target

router = APIRouter(
    prefix="/users/{user_id}/nutrition",
    tags=["nutrition"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/daily-target", response_model=NutritionTargetOut)
def get_daily_nutrition_target(
    user_id: int, payload: NutritionTargetRequest, db: Session = Depends(get_db)
) -> NutritionTargetOut:
    resultado = compute_daily_nutrition_target(
        db, user_id=user_id, target_date=payload.target_date, factor_actividad=payload.factor_actividad
    )
    return NutritionTargetOut(
        kcal_objetivo=resultado.macros.kcal_objetivo,
        proteina_g=resultado.macros.proteina_g,
        carbohidratos_g=resultado.macros.carbohidratos_g,
        grasa_g=resultado.macros.grasa_g,
        fase_aplicada=resultado.fase_aplicada.value,
        deficit_pausado_por_guardrail=resultado.deficit_pausado_por_guardrail,
    )


@router.post("/plans", response_model=NutritionPlanOut, status_code=201)
def crear_plan_nutricional(
    user_id: int, payload: NutritionPlanRequest, db: Session = Depends(get_db)
) -> NutritionPlanOut:
    """Alta de un plan de fase de peso con duración determinada -
    petición explícita del usuario: "planes de deficit, superhabit y
    mantenimiento dedicados, con duración determinada, como tu
    nutricionista personal". Desactiva cualquier plan previo del
    usuario (nunca dos planes activos a la vez)."""
    plan = create_nutrition_plan(
        db,
        user_id=user_id,
        fase=payload.fase,
        semanas_duracion=payload.semanas_duracion,
        fecha_inicio=payload.fecha_inicio,
        motivo=payload.motivo,
    )
    return NutritionPlanOut.model_validate(plan, from_attributes=True)


@router.get("/plans/active")
def get_plan_nutricional_activo(
    user_id: int, as_of: date | None = Query(default=None), db: Session = Depends(get_db)
) -> ActiveNutritionPlanOut | None:
    """`null` si no hay ningún plan activo - "unknown is not zero"."""
    resultado = get_active_nutrition_plan(db, user_id, as_of=as_of or date.today())
    if resultado is None:
        return None
    return ActiveNutritionPlanOut(
        plan=NutritionPlanOut.model_validate(resultado.plan, from_attributes=True),
        fecha_fin=resultado.fecha_fin,
        dias_restantes=resultado.dias_restantes,
        expirado=resultado.expirado,
    )


@router.get("/plans/recommendation", response_model=NutritionPhaseRecommendationOut)
def get_recomendacion_fase(
    user_id: int, as_of: date | None = Query(default=None), db: Session = Depends(get_db)
) -> NutritionPhaseRecommendationOut:
    """Recomienda la siguiente fase (NUNCA la aplica automáticamente -
    decisión explícita del usuario: "recomienda, tú confirmas"). El
    frontend debe usar esto para prellenar el formulario de
    `POST /plans`, no para crear el plan directamente."""
    recomendacion = recommend_next_phase(db, user_id, as_of=as_of or date.today())
    return NutritionPhaseRecommendationOut(
        fase_recomendada=recomendacion.fase_recomendada,
        accion=recomendacion.accion,
        motivo=recomendacion.motivo,
        semanas_sugeridas=recomendacion.semanas_sugeridas,
    )
