"""Endpoints de TrainingBlock + WeeklySchedule (crear, listar, borrar).

Sin esto, la auto-derivación de `planned_session` (Fase F) no es
alcanzable desde el frontend/API - solo existía a nivel de servicio y
repositorio, probada por tests directos pero sin forma de que un
usuario real la activara. Este router cierra ese hueco.

Listar y borrar existen por un motivo concreto, no por simetría CRUD:
`get_planned_session_for_date` falla a propósito cuando dos bloques
cubren la misma fecha, y le pide al usuario que deje solo uno activo.
Sin un listado y un borrado, ese mensaje le pedía algo que la aplicación
no le dejaba hacer: el único camino era entrar a la base de datos a
mano. Borra él, no nosotros: elegir en su nombre cuál de los dos planes
sobra tiraría semanas de planificación sin preguntar.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, select
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


@router.get("", response_model=list[TrainingBlockOut])
def list_training_blocks(user_id: int, db: Session = Depends(get_db)) -> list[TrainingBlock]:
    """Todos los bloques del usuario, del más reciente al más antiguo.

    Devuelve también los ya terminados: son el historial de lo que ha
    entrenado, y sin ellos la pantalla no puede distinguir "no tengo
    plan" de "mi plan acabó la semana pasada", que se resuelven de forma
    distinta.
    """
    if db.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    stmt = (
        select(TrainingBlock)
        .where(TrainingBlock.user_id == user_id)
        .order_by(TrainingBlock.fecha_inicio.desc(), TrainingBlock.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.delete("/{block_id}", status_code=204)
def delete_training_block(user_id: int, block_id: int, db: Session = Depends(get_db)) -> Response:
    """Borra un bloque y su plan semanal.

    Filtra por `user_id` además de por `block_id`: sin ese filtro, el id
    de otro usuario en la URL borraría un plan ajeno.

    Borra a mano las filas de `WeeklySchedule`: la FK no declara
    `ondelete="CASCADE"`, así que dejarlas sería dejar un plan semanal
    apuntando a un bloque inexistente.
    """
    bloque = db.execute(
        select(TrainingBlock)
        .where(TrainingBlock.id == block_id)
        .where(TrainingBlock.user_id == user_id)
    ).scalar_one_or_none()
    if bloque is None:
        raise EntityNotFoundError(f"No existe TrainingBlock id={block_id} para user_id={user_id}")

    db.execute(delete(WeeklySchedule).where(WeeklySchedule.training_block_id == block_id))
    db.delete(bloque)
    db.commit()
    return Response(status_code=204)
