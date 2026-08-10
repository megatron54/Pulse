"""Orquesta la ingesta de la serie minuto a minuto de Garmin (petición
explícita del usuario: histórico completo de HR/body battery/estrés,
no solo la media del día) - pide el rango crudo al cliente, y lo
persiste de forma idempotente vía `garmin_intraday_repository`.

Aislamiento por métrica (mismo principio que el resto del pipeline de
Garmin): un fallo en una métrica nunca debe impedir ingerir las demás
- ya lo garantiza `GarminClient.get_intraday_series_raw` devolviendo
lista vacía por metrica fallida, así que aquí solo queda persistir."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from repositories.garmin_intraday_repository import save_intraday_points

_METRICAS = ("heart_rate", "body_battery", "stress")


@dataclass(frozen=True)
class IntradaySyncResult:
    puntos_nuevos_por_metrica: dict[str, int]

    @property
    def total_puntos_nuevos(self) -> int:
        return sum(self.puntos_nuevos_por_metrica.values())


def sync_intraday_metrics(
    session: Session, user_id: int, garmin_client: Any, target_date: date
) -> IntradaySyncResult:
    serie = garmin_client.get_intraday_series_raw(target_date.isoformat())

    puntos_nuevos_por_metrica = {
        metrica: save_intraday_points(session, user_id, metrica, target_date, serie.get(metrica, []))
        for metrica in _METRICAS
    }
    return IntradaySyncResult(puntos_nuevos_por_metrica=puntos_nuevos_por_metrica)
