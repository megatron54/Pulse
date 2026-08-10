"""Recomienda (NUNCA aplica automáticamente) la siguiente fase de peso
- decisión explícita del usuario: "recomienda, tú confirmas", mismo
principio que el resto de Pulse (el motor de reglas nunca actúa de
forma autónoma sin que el usuario lo vea/apruebe primero).

Reglas deterministas, en orden de prioridad (gana la primera que
aplique):
1. Guardrail de seguridad activo (mismo criterio que
   `engine.guardrails.should_pause_calorie_deficit`/
   `should_pause_calorie_deficit_for_poor_sleep`, ya usado en el
   cálculo diario de macros) - si el plan activo es CUT y la
   recuperación está mal, se recomienda pausar a mantenimiento AHORA,
   sin esperar a que el plan expire por duración.
2. Sin plan activo - mantenimiento es el punto de partida seguro
   (nunca se asume que el usuario quiere déficit/superávit sin que él
   lo elija explícitamente).
3. Plan expirado (hoy >= fecha_fin) y no es ya mantenimiento - se
   recomienda una fase de mantenimiento ("diet/surplus break"),
   práctica estándar tras un período prolongado de déficit/superávit,
   con duración sugerida = mitad de la fase anterior (mínimo 2,
   máximo 4 semanas).
4. Plan expirado y ya es mantenimiento - no es urgente, se informa
   pero no se sugiere un cambio forzado.
5. Plan vigente y sin guardrail activo - sin cambios, se informa
   cuánto queda."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from engine.guardrails import (
    should_pause_calorie_deficit,
    should_pause_calorie_deficit_for_poor_sleep,
)
from engine.nutrition import WeightPhase
from models.schema import UserProfile
from repositories.garmin_repository import get_daily_metrics_history
from repositories.readiness_log_repository import get_recent_readiness_levels
from services.errors import EntityNotFoundError
from services.nutrition_plan_service import get_active_nutrition_plan

_DIAS_HISTORIAL_GUARDRAIL = 3
_SEMANAS_MANTENIMIENTO_MIN = 2
_SEMANAS_MANTENIMIENTO_MAX = 4


@dataclass(frozen=True)
class NutritionPhaseRecommendation:
    fase_recomendada: str
    accion: str  # "sin_cambios" | "nuevo_plan_sugerido"
    motivo: str
    semanas_sugeridas: int | None = None


def recommend_next_phase(
    session: Session, user_id: int, as_of: date
) -> NutritionPhaseRecommendation:
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    activo = get_active_nutrition_plan(session, user_id, as_of=as_of)

    if activo is not None and activo.plan.fase == "cut":
        motivo_guardrail = _guardrail_disparado(session, user_id, as_of)
        if motivo_guardrail is not None:
            return NutritionPhaseRecommendation(
                fase_recomendada="maintenance",
                accion="nuevo_plan_sugerido",
                motivo=motivo_guardrail,
                semanas_sugeridas=_SEMANAS_MANTENIMIENTO_MIN,
            )

    if activo is None:
        return NutritionPhaseRecommendation(
            fase_recomendada="maintenance",
            accion="nuevo_plan_sugerido",
            motivo="Sin plan activo - mantenimiento es el punto de partida seguro.",
            semanas_sugeridas=4,
        )

    if activo.expirado:
        if activo.plan.fase == "maintenance":
            return NutritionPhaseRecommendation(
                fase_recomendada="maintenance",
                accion="sin_cambios",
                motivo="Tu fase de mantenimiento ha terminado - puedes renovarla o elegir una fase nueva.",
            )
        semanas_sugeridas = max(
            _SEMANAS_MANTENIMIENTO_MIN,
            min(_SEMANAS_MANTENIMIENTO_MAX, activo.plan.semanas_duracion // 2),
        )
        return NutritionPhaseRecommendation(
            fase_recomendada="maintenance",
            accion="nuevo_plan_sugerido",
            motivo=(
                f"Tras {activo.plan.semanas_duracion} semanas en {activo.plan.fase}, se recomienda "
                "una fase de mantenimiento antes de continuar."
            ),
            semanas_sugeridas=semanas_sugeridas,
        )

    return NutritionPhaseRecommendation(
        fase_recomendada=activo.plan.fase,
        accion="sin_cambios",
        motivo=f"Tu plan de {activo.plan.fase} sigue en curso - {activo.dias_restantes} días restantes.",
    )


def _guardrail_disparado(session: Session, user_id: int, as_of: date) -> str | None:
    """Reutiliza el mismo criterio ya activo en el cálculo diario de
    macros (`services.nutrition_service`) - si dispararía ahí, se
    recomienda aquí ANTES de que el plan expire por duración."""
    historial_readiness = get_recent_readiness_levels(
        session, user_id, as_of, n=_DIAS_HISTORIAL_GUARDRAIL
    )
    if historial_readiness and should_pause_calorie_deficit(
        weight_phase=WeightPhase.CUT, readiness_history=historial_readiness
    ):
        return (
            f"Tu recovery ha estado en zona roja los últimos {_DIAS_HISTORIAL_GUARDRAIL} días - "
            "se recomienda pausar el déficit."
        )

    metricas_recientes = get_daily_metrics_history(
        session, user_id, as_of=as_of, days=_DIAS_HISTORIAL_GUARDRAIL
    )
    sleep_scores = [m.sleep_score for m in reversed(metricas_recientes)]
    if sleep_scores and should_pause_calorie_deficit_for_poor_sleep(
        weight_phase=WeightPhase.CUT, sleep_scores=sleep_scores
    ):
        return (
            f"Tu sueño ha estado por debajo de lo saludable los últimos "
            f"{_DIAS_HISTORIAL_GUARDRAIL} días - se recomienda pausar el déficit."
        )

    return None
