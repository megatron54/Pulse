"""Repositorio de plan semanal (TrainingBlock + WeeklySchedule).

Deriva automáticamente qué SessionType tocaría un día concreto, para no
depender de que `planned_session` se pase siempre a mano a
services.session_service.compute_daily_session (ver docs/02-roadmap/
02-plan-autonomo.md, Fase F).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm import Session

from engine.periodization import SessionType
from models.schema import TrainingBlock, WeeklySchedule
# Único import de `services` desde un repositorio, y a propósito:
# `services.errors` es el módulo de excepciones de DOMINIO compartidas
# (lo dice su docstring), no lógica de servicio. La alternativa era
# seguir lanzando un `ValueError` genérico y traducirlo en
# session_service, que obligaba a tratar cualquier ValueError de esta
# función como "planes solapados" y perdía la precisión del motivo.
from services.errors import OverlappingTrainingBlocksError

_DIAS_SEMANA_ISO = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def get_planned_session_for_date(
    session: Session, user_id: int, target_date: date
) -> SessionType | None:
    """Busca el TrainingBlock del usuario cuyo rango [fecha_inicio,
    fecha_fin] cubre `target_date`, y dentro de él la entrada de
    WeeklySchedule para el día de la semana correspondiente.

    Devuelve None si no hay bloque activo para esa fecha, o si el bloque
    activo no tiene una entrada de schedule para ese día de la semana
    (principio "unknown is not zero": no se inventa una sesión por
    defecto, la capa llamante decide qué hacer ante la ausencia).

    Lanza ValueError explícito (nunca deja escapar la excepción cruda de
    SQLAlchemy, que no está mapeada a ningún código HTTP en la API) si
    el usuario tiene DOS o más TrainingBlock activos con rangos de
    fechas solapados para `target_date` - un estado de datos corrupto
    que no se puede ni debe desambiguar en silencio.
    """
    dia_semana = _DIAS_SEMANA_ISO[target_date.weekday()]

    stmt = (
        select(WeeklySchedule.session_type)
        .join(TrainingBlock, TrainingBlock.id == WeeklySchedule.training_block_id)
        .where(TrainingBlock.user_id == user_id)
        .where(TrainingBlock.fecha_inicio <= target_date)
        .where(TrainingBlock.fecha_fin >= target_date)
        .where(WeeklySchedule.dia_semana == dia_semana)
    )
    try:
        resultado = session.execute(stmt).scalar_one_or_none()
    except MultipleResultsFound as exc:
        # El texto es de INTERFAZ, no de log (doctrina 8: el `detail` de
        # un error HTTP lo lee una persona). La versión anterior decía
        # "user_id=4 tiene múltiples TrainingBlock activos y solapados -
        # revisa/corrige los rangos de fechas de tus bloques de
        # periodización": un id interno y el nombre del modelo en
        # pantalla, y sin ninguna acción que el usuario pudiera tomar.
        raise OverlappingTrainingBlocksError(
            "Tienes dos planes de entrenamiento que se solapan en esta fecha, "
            "así que no se sabe cuál manda. Deja solo uno activo para poder "
            "ajustar la sesión de hoy."
        ) from exc
    return SessionType(resultado) if resultado is not None else None
