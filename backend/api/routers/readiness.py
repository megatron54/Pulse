from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import ManualReadinessRequest, ReadinessOut
from engine.periodization import RecoveryContext
from models.schema import ReadinessLog
from services.readiness_service import record_manual_readiness

router = APIRouter(
    prefix="/users/{user_id}/readiness",
    tags=["readiness"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/manual-checkin", response_model=ReadinessOut, status_code=201)
def manual_readiness_checkin(
    user_id: int, payload: ManualReadinessRequest, db: Session = Depends(get_db)
) -> ReadinessLog:
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
    return record_manual_readiness(db, user_id=user_id, target_date=payload.target_date, ctx=ctx)
