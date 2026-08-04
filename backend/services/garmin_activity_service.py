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
from repositories.garmin_repository import save_activity_if_new


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
        else:
            omitidas += 1

    return ActivitySyncResult(ingresadas=ingresadas, omitidas=omitidas, invalidas=invalidas)
