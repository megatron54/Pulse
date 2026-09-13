"""Orquesta la ingestión de actividades Garmin (Épica 2 de
02-roadmap/03-vision-produccion.md): pide el rango crudo al cliente,
mapea cada actividad, y la persiste de forma idempotente.

Buildable y testeable con un `GarminClient` doble (ver
tests/test_garmin_activity_service.py) sin credenciales reales - la
sincronización real queda bloqueada por la Fase H (sin cuenta Garmin de
prueba), pero el código queda listo para el día en que exista.

Aislamiento por actividad (mismo principio que
`services.scheduler_service.run_daily_sync_for_all_users` aplica por
usuario, y `garmin_sync.client._llamada_segura` por campo de
recuperación): una actividad individual mal formada (falta
`activityId`/`startTimeLocal`) nunca debe descartar el resto del lote -
se cuenta como inválida y se sigue con las demás."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from garmin_sync.activity_mapper import InvalidActivityError, map_raw_activity
from garmin_sync.exercise_set_mapper import map_raw_exercise_set
from repositories.garmin_repository import save_activity_if_new, save_exercise_sets_if_new
from services.garmin_query_service import CategoriaDeporte, tipos_garmin_de


@dataclass(frozen=True)
class ActivitySyncResult:
    ingresadas: int
    omitidas: int
    invalidas: int


def sync_activities(
    session: Session,
    user_id: int,
    garmin_client: Any,
    start_date: date,
    end_date: date,
) -> ActivitySyncResult:
    raw_activities = garmin_client.get_activities_raw(
        start_date.isoformat(), end_date.isoformat()
    )

    tipos_gimnasio = tipos_garmin_de(CategoriaDeporte.GIMNASIO)

    ingresadas = 0
    omitidas = 0
    invalidas = 0
    for raw in raw_activities:
        try:
            actividad = map_raw_activity(raw)
        except InvalidActivityError:
            invalidas += 1
            continue

        if save_activity_if_new(session, user_id, actividad):
            ingresadas += 1
            if actividad["tipo"] in tipos_gimnasio:
                _sync_exercise_sets(session, user_id, garmin_client, actividad["activity_id"])
        else:
            omitidas += 1

    return ActivitySyncResult(ingresadas=ingresadas, omitidas=omitidas, invalidas=invalidas)


def _sync_exercise_sets(
    session: Session, user_id: int, garmin_client: Any, activity_id: str
) -> None:
    """Serie de gimnasio de una actividad recién ingresada (Épica G,
    Fase 1 punto 2) - solo se pide detalle para actividades NUEVAS
    (nunca releer detalle de actividades ya vistas, ver nota de riesgo
    de bloqueo de cuenta del punto 2 de investigación). Un fallo aquí
    (actividad sin sets, o el propio `get_exercise_sets_raw` ya
    degradado a lista vacía) nunca debe descartar la actividad recién
    guardada - mismo aislamiento por actividad que el resto de este
    módulo."""
    raw_sets = garmin_client.get_exercise_sets_raw(activity_id)
    if not raw_sets:
        return
    sets = [map_raw_exercise_set(raw, numero_serie=i) for i, raw in enumerate(raw_sets)]
    save_exercise_sets_if_new(session, user_id, activity_id, sets)
