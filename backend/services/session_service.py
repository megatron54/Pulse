"""Orquesta la decisión de sesión de entrenamiento del día.

Conecta: ReadinessLog (ya persistido por services.readiness_service para
`target_date`) -> repositories.training_block_repository (deriva
`planned_session` del bloque/plan semanal activo, si `planned_session`
no se pasa explícito) -> engine.guardrails (deload forzado por ACWR
sostenido, descanso forzado pre-competición) ->
engine.periodization.decide_session (regla normal RED/YELLOW/GREEN) ->
AuditLog.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from engine.guardrails import should_force_deload, should_force_full_rest_pre_competition
from engine.periodization import (
    SessionRecommendation,
    SessionType,
    decide_session,
)
from models.schema import AuditLog, UserProfile
from repositories.readiness_log_repository import get_latest_readiness_level
from repositories.training_block_repository import get_planned_session_for_date
from services.errors import EntityNotFoundError


def compute_daily_session(
    session: Session,
    user_id: int,
    target_date: date,
    planned_session: SessionType | None = None,
    acwr_history: list[float] | None = None,
    days_to_competition: int | None = None,
) -> SessionRecommendation:
    """Decide la sesión final del día, aplicando primero los guardrails
    de última instancia (deload por ACWR sostenido, descanso pre-
    competición) y, si ninguno se dispara, la regla normal de
    `decide_session` según el readiness ya calculado.

    `planned_session` es opcional (Fase F del plan autónomo, ver
    docs/02-roadmap/02-plan-autonomo.md): si no se proporciona, se
    deriva automáticamente del TrainingBlock/WeeklySchedule activo para
    `target_date` vía `repositories.training_block_repository`. Se
    mantiene como parámetro explícito para permitir overrides manuales
    (ej. un cambio de plan puntual) sin tener que tocar el bloque
    persistido.

    Orden de prioridad entre guardrails (decisión consciente, no
    incidental): `should_force_deload` se evalúa primero porque ACWR
    sostenido >1.5 es una señal de sobrecarga de ENTRENAMIENTO acumulada
    en el tiempo (días), mientras que la proximidad de competición es un
    factor de CALENDARIO puntual. En el caso límite en que ambos
    guardrails se disparan a la vez, ambos resultados son de volumen 0
    (ACTIVE_RECOVERY vs REST) - ninguno permite entrenar con intensidad,
    por lo que el orden no compromete la seguridad del usuario en
    ningún escenario, solo determina el tipo exacto de descanso.

    Lanza ValueError si `user_id` no existe, si no hay un ReadinessLog
    para `target_date` (debe ejecutarse
    `services.readiness_service.sync_and_compute_readiness` antes, para
    ese mismo día), o si `planned_session` no se proporciona y tampoco
    hay ningún plan semanal activo del que derivarlo.
    """
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    readiness = get_latest_readiness_level(session, user_id, target_date)
    if readiness is None:
        raise ValueError(
            f"No hay readiness calculado para user_id={user_id} en {target_date}: "
            "ejecutar sync_and_compute_readiness primero"
        )

    if planned_session is None:
        planned_session = get_planned_session_for_date(session, user_id, target_date)
        if planned_session is None:
            raise ValueError(
                f"No se proporcionó planned_session y no hay plan semanal activo "
                f"para user_id={user_id} en {target_date}: crea un TrainingBlock con "
                "WeeklySchedule, o pasa planned_session explícitamente."
            )

    regla_disparada = "decide_session"

    if acwr_history and should_force_deload(acwr_history):
        recomendacion = SessionRecommendation(
            session_type=SessionType.ACTIVE_RECOVERY, volume_pct=0
        )
        regla_disparada = "should_force_deload"
    elif should_force_full_rest_pre_competition(days_to_competition, readiness):
        recomendacion = SessionRecommendation(session_type=SessionType.REST, volume_pct=0)
        regla_disparada = "should_force_full_rest_pre_competition"
    else:
        recomendacion = decide_session(planned_session=planned_session, readiness=readiness)

    session.add(
        AuditLog(
            user_id=user_id,
            modulo="session_decision",
            inputs_json={
                "planned_session": planned_session.value,
                "readiness": readiness.value,
                "acwr_history": acwr_history,
                "days_to_competition": days_to_competition,
            },
            regla_disparada=regla_disparada,
            output=recomendacion.session_type.value,
            decision_final=(
                f"{recomendacion.session_type.value}@{recomendacion.volume_pct}%"
                + (
                    f";rpe_cap={recomendacion.intensity_rpe_cap}"
                    if recomendacion.intensity_rpe_cap is not None
                    else ""
                )
            ),
        )
    )
    session.commit()

    return recomendacion
