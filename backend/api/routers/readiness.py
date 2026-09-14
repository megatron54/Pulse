from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import ManualReadinessRequest, ReadinessOut, SignalOut
from engine.periodization import RecoveryContext, assess_signals_from_values
from models.schema import ReadinessLog
from repositories.readiness_log_repository import get_readiness_history
from services.readiness_service import record_manual_readiness


def _a_readiness_out(log: ReadinessLog) -> ReadinessOut:
    """Añade a la fila guardada el desglose por señal.

    Se calcula al leer, no se guarda: las señales son una relectura de
    los mismos campos con los umbrales del motor, así que persistirlas
    sería duplicar el dato y arriesgarse a que un día dejaran de
    coincidir con las reglas vigentes. Y se calcula con
    `assess_signals_from_values` (no con un `RecoveryContext`) porque la
    fila guarda el delta de VFC ya calculado, no la VFC de hoy ni la
    baseline: reconstruir un contexto completo obligaría a inventarse
    esos dos números.

    Las filas anteriores a la columna `hrv_trend_7d` la traen a `None`,
    y eso llega a la interfaz como "sin dato" - no como una tendencia
    plana, que es lo que se leería un 0.
    """
    senales = assess_signals_from_values(
        hrv_delta_pct=log.hrv_delta_pct,
        hrv_trend_7d=log.hrv_trend_7d,
        training_readiness=log.training_readiness,
        body_battery_am=log.body_battery_am,
        acwr=log.acwr,
        sleep_score=log.sleep_score,
        joint_pain_flag=log.joint_pain_flag,
    )
    return ReadinessOut(
        id=log.id,
        fecha=log.fecha,
        resultado=log.resultado,
        hrv_delta_pct=log.hrv_delta_pct,
        hrv_trend_7d=log.hrv_trend_7d,
        training_readiness=log.training_readiness,
        body_battery_am=log.body_battery_am,
        sleep_score=log.sleep_score,
        acwr=log.acwr,
        joint_pain_flag=log.joint_pain_flag,
        senales=[
            SignalOut(
                senal=s.senal,
                estado=s.estado.value,
                valor=s.valor,
                umbral_rojo=s.umbral_rojo,
                umbral_amarillo=s.umbral_amarillo,
                peor_hacia=s.peor_hacia,
            )
            for s in senales
        ],
    )


router = APIRouter(
    prefix="/users/{user_id}/readiness",
    tags=["readiness"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/manual-checkin", response_model=ReadinessOut, status_code=201)
def manual_readiness_checkin(
    user_id: int, payload: ManualReadinessRequest, db: Session = Depends(get_db)
) -> ReadinessOut:
    """Check-in manual de recuperación (sin Garmin). Ver Fase H del plan
    autónomo: la sincronización real con Garmin sigue bloqueada por
    falta de credenciales; este endpoint permite usar el motor de
    reglas completo (readiness + sesión + nutrición) mientras tanto."""
    ctx = RecoveryContext(
        hrv_today=payload.hrv_today,
        hrv_baseline_28d=payload.hrv_baseline_28d,
        hrv_trend_7d=payload.hrv_trend_7d,
        body_battery_am=payload.body_battery_am,
        training_readiness=payload.training_readiness,
        sleep_score=payload.sleep_score,
        acwr=payload.acwr,
        joint_pain_flag=payload.joint_pain_flag,
    )
    log = record_manual_readiness(
        db, user_id=user_id, target_date=payload.target_date, ctx=ctx
    )
    return _a_readiness_out(log)


@router.get("/history", response_model=list[ReadinessOut])
def get_readiness_history_endpoint(
    user_id: int,
    days: int = Query(default=30, ge=1, le=365),
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ReadinessOut]:
    """Historial de readiness para dashboards de tendencia (Fase I).

    Mismo matiz que en body_composition.get_body_measurement_history:
    `as_of` por defecto es fecha del SERVIDOR, no la fecha local del
    usuario - los clientes deben enviarlo explícito."""
    return [
        _a_readiness_out(log)
        for log in get_readiness_history(db, user_id, as_of=as_of or date.today(), days=days)
    ]
