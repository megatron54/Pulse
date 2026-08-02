from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import DailySessionOut, DailySessionRequest
from coach.gemini_client import GeminiClient
from coach.narrative_service import generate_session_narrative
from engine.periodization import SessionType
from repositories.readiness_log_repository import get_latest_readiness_level
from services.session_service import compute_daily_session

router = APIRouter(
    prefix="/users/{user_id}/session",
    tags=["session"],
    dependencies=[Depends(verify_api_key)],
)


def _build_gemini_client_if_configured() -> GeminiClient | None:
    """La IA es opcional y no autoritativa (ver docs/00-research/
    07-arquitectura-coach-ia.md): si no hay GEMINI_API_KEY configurada,
    la Capa 3 usa su plantilla determinista de respaldo sin que el
    endpoint falle ni se degrade la decisión estructurada."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return GeminiClient(api_key=api_key)


@router.post("/daily", response_model=DailySessionOut)
def get_daily_session(
    user_id: int, payload: DailySessionRequest, db: Session = Depends(get_db)
) -> DailySessionOut:
    recomendacion = compute_daily_session(
        db,
        user_id=user_id,
        target_date=payload.target_date,
        planned_session=SessionType(payload.planned_session),
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
        recomendacion, readiness=readiness, gemini_client=_build_gemini_client_if_configured()
    )

    return DailySessionOut(
        session_type=recomendacion.session_type.value,
        volume_pct=recomendacion.volume_pct,
        intensity_rpe_cap=recomendacion.intensity_rpe_cap,
        narrative_text=narrativa.text,
        narrative_source=narrativa.source,
    )
