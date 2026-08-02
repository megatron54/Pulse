"""Orquesta el cálculo del objetivo nutricional diario.

Conecta: UserProfile + BodyMeasurements (repository) -> engine.nutrition
(Capa 1, TDEE/macros) -> engine.guardrails.should_pause_calorie_deficit
(Capa 1, usando historial de ReadinessLog vía repository) -> AuditLog.

Ninguna lógica de decisión vive aquí: solo se combina el peso más
reciente y la fase de peso del perfil, se le pasa al motor de reglas, y
se aplica el guardrail de pausa de déficit si corresponde - sin mutar el
estado almacenado del usuario (la pausa es de UN día, no un cambio de
fase permanente, ver docstring de engine.guardrails.should_pause_calorie_deficit).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from engine.guardrails import should_pause_calorie_deficit
from engine.nutrition import MacroTargets, UserBiometrics, WeightPhase, calculate_macros, calculate_tdee
from models.schema import AuditLog, UserProfile
from repositories.body_measurements_repository import get_latest_weight_kg
from repositories.readiness_log_repository import get_recent_readiness_levels

_DIAS_HISTORIAL_GUARDRAIL_CUT = 3


@dataclass(frozen=True)
class DailyNutritionResult:
    macros: MacroTargets
    fase_aplicada: WeightPhase
    deficit_pausado_por_guardrail: bool


def compute_daily_nutrition_target(
    session: Session, user_id: int, target_date: date, factor_actividad: float
) -> DailyNutritionResult:
    """Calcula el objetivo de macros del día para `user_id`.

    Lanza ValueError si no hay ninguna medición de peso registrada
    todavía (no se puede calcular TDEE sin peso - "unknown is not zero").
    """
    usuario = session.get(UserProfile, user_id)
    if usuario is None:
        raise ValueError(f"No existe UserProfile con id={user_id}")

    peso_kg = get_latest_weight_kg(session, user_id)
    if peso_kg is None:
        raise ValueError(
            "No hay ninguna medición de peso registrada: no se puede calcular TDEE"
        )

    edad = _calcular_edad(usuario.fecha_nacimiento, target_date)
    bio = UserBiometrics(
        peso_kg=peso_kg,
        altura_cm=usuario.altura_cm,
        edad=edad,
        sexo=usuario.sexo,
    )
    tdee = calculate_tdee(bio, factor_actividad=factor_actividad)

    fase_perfil = WeightPhase(usuario.fase_peso_actual)
    fase_aplicada = fase_perfil
    deficit_pausado = False

    if fase_perfil == WeightPhase.CUT:
        historial = get_recent_readiness_levels(
            session, user_id, target_date, n=_DIAS_HISTORIAL_GUARDRAIL_CUT
        )
        if historial and should_pause_calorie_deficit(
            weight_phase=fase_perfil, readiness_history=historial
        ):
            fase_aplicada = WeightPhase.MAINTENANCE
            deficit_pausado = True

    macros = calculate_macros(peso_kg=peso_kg, tdee=tdee, fase=fase_aplicada)

    session.add(
        AuditLog(
            user_id=user_id,
            modulo="nutrition",
            inputs_json={
                "peso_kg": peso_kg,
                "tdee": tdee,
                "fase_perfil": fase_perfil.value,
                "factor_actividad": factor_actividad,
            },
            regla_disparada=(
                "should_pause_calorie_deficit" if deficit_pausado else "calculate_macros"
            ),
            output=fase_aplicada.value,
            decision_final=(
                f"kcal_objetivo={macros.kcal_objetivo:.0f};"
                f"proteina_g={macros.proteina_g:.0f}"
            ),
        )
    )
    session.commit()

    return DailyNutritionResult(
        macros=macros, fase_aplicada=fase_aplicada, deficit_pausado_por_guardrail=deficit_pausado
    )


def _calcular_edad(fecha_nacimiento: date, as_of: date) -> int:
    edad = as_of.year - fecha_nacimiento.year
    if (as_of.month, as_of.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad
