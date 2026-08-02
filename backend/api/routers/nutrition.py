from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import NutritionTargetOut, NutritionTargetRequest
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
