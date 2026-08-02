from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import BodyMeasurementCreateRequest, BodyMeasurementOut
from models.schema import BodyMeasurements
from services.body_composition_service import record_body_measurement

router = APIRouter(
    prefix="/users/{user_id}/body-measurements",
    tags=["body-composition"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=BodyMeasurementOut, status_code=201)
def create_body_measurement(
    user_id: int, payload: BodyMeasurementCreateRequest, db: Session = Depends(get_db)
) -> BodyMeasurements:
    return record_body_measurement(
        db,
        user_id=user_id,
        target_date=payload.target_date,
        peso_kg=payload.peso_kg,
        cuello_cm=payload.cuello_cm,
        cintura_cm=payload.cintura_cm,
        cadera_cm=payload.cadera_cm,
    )
