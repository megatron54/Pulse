"""Endpoint para crear TrainingBlock + WeeklySchedule.

Sin esto, la auto-derivación de `planned_session` (Fase F) no es
alcanzable desde el frontend/API - solo existía a nivel de servicio y
repositorio, probada por tests directos pero sin forma de que un
usuario real la activara. Este router cierra ese hueco.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import TrainingBlockCreateRequest, TrainingBlockOut
from models.schema import TrainingBlock, UserProfile, WeeklySchedule
from services.errors import EntityNotFoundError

router = APIRouter(
    prefix="/users/{user_id}/training-blocks",
    tags=["training-blocks"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=TrainingBlockOut, status_code=201)
def create_training_block(
    user_id: int, payload: TrainingBlockCreateRequest, db: Session = Depends(get_db)
) -> TrainingBlock:
    """Crea un TrainingBlock con su WeeklySchedule (mapa día->sesión).

    No valida solapamiento con otros bloques del usuario en escritura
    (deuda documentada: la detección real ocurre en lectura, ver
    repositories.training_block_repository.get_planned_session_for_date,
    que falla explícitamente ante bloques solapados en vez de
    desambiguar en silencio)."""
    if db.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    bloque = TrainingBlock(
        user_id=user_id,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        objetivo_prioritario=payload.objetivo_prioritario,
        objetivos_mantenimiento=payload.objetivos_mantenimiento,
    )
    db.add(bloque)
    db.commit()
    db.refresh(bloque)

    for dia, tipo in payload.weekly_schedule.items():
        db.add(WeeklySchedule(training_block_id=bloque.id, dia_semana=dia, session_type=tipo))
    db.commit()

    return bloque
