"""Traduce una actividad cruda de `GarminClient.get_activities_raw`
(camelCase, forma de la API real de Garmin Connect) a los campos
normalizados de `models.schema.GarminActivity`.

Nombres de campo verificados contra el código fuente real de
python-garminconnect (`garminconnect/typed.py`, clase `Activity`,
clonado en recursos/repos/python-garminconnect/) - no inventados a
partir de suposiciones. Carrera trae `distance`/HR/training effect;
fuerza no trae distancia/velocidad útiles (ver 02-roadmap/
03-vision-produccion.md, punto 2 de investigación) - esos campos
quedan en `None`, nunca en `0` ("unknown is not zero").
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

_TIPO_DESCONOCIDO = "desconocido"


class InvalidActivityError(Exception):
    """La actividad cruda no trae los campos mínimos indispensables
    (id y fecha) para poder persistirla de forma útil."""


def _parse_fecha(start_time_local: str, activity_id: Any) -> date:
    """`startTimeLocal` viene como "YYYY-MM-DD HH:MM:SS" (hora local del
    dispositivo, ya sin zona horaria - es la que Garmin usa para agrupar
    actividades por "día" en su propia UI, así que replicamos ese
    criterio en vez de convertir a UTC)."""
    try:
        return datetime.strptime(start_time_local, "%Y-%m-%d %H:%M:%S").date()
    except ValueError as exc:
        # Si el formato cambiara o llegara corrupto, esto debe contar
        # como UNA actividad inválida (igual que activity_id/
        # startTimeLocal ausentes), nunca como un ValueError crudo que
        # tumbaría el lote entero en sync_activities (que solo captura
        # InvalidActivityError, ver hallazgo LOW de code-review).
        raise InvalidActivityError(
            f"La actividad {activity_id} tiene 'startTimeLocal' con formato "
            f"inesperado: {start_time_local!r}"
        ) from exc


def map_raw_activity(raw: dict[str, Any]) -> dict[str, Any]:
    activity_id = raw.get("activityId")
    start_time_local = raw.get("startTimeLocal")
    if activity_id is None:
        raise InvalidActivityError("La actividad no trae 'activityId'")
    if not start_time_local:
        raise InvalidActivityError(
            f"La actividad {activity_id} no trae 'startTimeLocal'"
        )

    tipo = _TIPO_DESCONOCIDO
    activity_type = raw.get("activityType")
    if isinstance(activity_type, dict) and activity_type.get("typeKey"):
        tipo = activity_type["typeKey"]

    duracion = raw.get("duration")
    distancia = raw.get("distance")
    hr_avg = raw.get("averageHR")
    hr_max = raw.get("maxHR")
    training_effect = raw.get("aerobicTrainingEffect")

    return {
        "activity_id": str(activity_id),
        "fecha": _parse_fecha(start_time_local, activity_id),
        "tipo": tipo,
        "duracion_seg": round(duracion) if duracion is not None else None,
        "distancia_m": float(distancia) if distancia is not None else None,
        "hr_avg": round(hr_avg) if hr_avg is not None else None,
        "hr_max": round(hr_max) if hr_max is not None else None,
        "training_effect": float(training_effect) if training_effect is not None else None,
        "raw_json": raw,
    }
