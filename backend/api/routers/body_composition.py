from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import BodyMeasurementCreateRequest, BodyMeasurementOut
from models.schema import BodyMeasurements
from repositories.body_measurements_repository import get_weight_history
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


@router.get("/history", response_model=list[BodyMeasurementOut])
def get_body_measurement_history(
    user_id: int,
    # `le=3650` = 10 años, y no es un número arbitrario: el porqué (y por
    # qué no hace falta paginar con ese tope) está en el docstring. Quien
    # quiera subirlo tiene que volver a hacer esa cuenta.
    days: int = Query(default=90, ge=1, le=3650),
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[BodyMeasurements]:
    """Historial de peso/composición corporal para dashboards de
    tendencia (Fase I).

    El tope de `days` es de 10 años (antes eran 730 días): al importar
    una báscula Feelfit entran años de pesadas de golpe, y con el tope
    de 2 años el frontend recibía 65 de las 275 mediciones del usuario
    sin poder pedir el resto. Una fila por pesada hace que una década
    sean unos pocos miles de filas, así que no hace falta paginar; el
    tope sigue existiendo para que `days` no pueda pedir una ventana
    absurda por error.

    `as_of` por defecto es `date.today()` del
    SERVIDOR (no la fecha local del usuario) - el frontend ya usa
    `todayLocalDate()` (fecha local del navegador, ver frontend/src/lib/
    api.ts) precisamente porque `toISOString()`/UTC puede desfasar "hoy"
    un día cerca de medianoche. Los clientes DEBEN enviar `as_of`
    explícito con la fecha local del usuario; el default del servidor
    es solo un fallback de conveniencia, no una fuente de verdad de
    "hoy"."""
    return get_weight_history(db, user_id, as_of=as_of or date.today(), days=days)
