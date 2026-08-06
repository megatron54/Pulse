from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import DailySessionOut, DailySessionRequest, TrainingLoadOut
from coach.gemini_client import build_gemini_client_if_configured
from coach.narrative_service import generate_session_narrative
from engine.periodization import SessionType
from repositories.readiness_log_repository import get_latest_readiness_level
from services.session_service import compute_daily_session
from services.training_load_service import compute_training_load

router = APIRouter(
    prefix="/users/{user_id}/session",
    tags=["session"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/daily", response_model=DailySessionOut)
def get_daily_session(
    user_id: int, payload: DailySessionRequest, db: Session = Depends(get_db)
) -> DailySessionOut:
    recomendacion = compute_daily_session(
        db,
        user_id=user_id,
        target_date=payload.target_date,
        planned_session=SessionType(payload.planned_session) if payload.planned_session else None,
        acwr_history=payload.acwr_history,
        days_to_competition=payload.days_to_competition,
    )

    # Reutiliza el mismo repositorio que usó compute_daily_session
    # internamente (centralizado en repositories.readiness_log_repository)
    # en vez de una query ad-hoc duplicada en el router.
    readiness = get_latest_readiness_level(db, user_id, payload.target_date)
    if readiness is None:
        # No debería ocurrir: compute_daily_session ya exige que exista.
        # Defensivo ante futuros refactors, en vez de un AttributeError.
        raise ValueError(
            f"No hay readiness calculado para user_id={user_id} en {payload.target_date}"
        )

    narrativa = generate_session_narrative(
        recomendacion, readiness=readiness, gemini_client=build_gemini_client_if_configured()
    )

    return DailySessionOut(
        session_type=recomendacion.session_type.value,
        volume_pct=recomendacion.volume_pct,
        intensity_rpe_cap=recomendacion.intensity_rpe_cap,
        narrative_text=narrativa.text,
        narrative_source=narrativa.source,
    )


@router.get("/training-load", response_model=TrainingLoadOut)
def get_training_load(
    user_id: int,
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TrainingLoadOut:
    """ACWR real calculado a partir del historial de `volume_pct` ya
    decidido día a día (ver services.training_load_service) - no el
    número manual que el usuario escribe en el check-in. `as_of` por
    defecto es la fecha del SERVIDOR (mismo matiz que el resto de
    endpoints de historial - los clientes deben enviarlo explícito si
    necesitan la fecha local del usuario)."""
    resultado = compute_training_load(db, user_id, as_of=as_of or date.today())
    return TrainingLoadOut.model_validate(resultado, from_attributes=True)
