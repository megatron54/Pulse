"""Traduce una serie cruda de `GarminClient.get_exercise_sets_raw`
(payload de `get_activity_exercise_sets`, camelCase) a los campos
normalizados de `models.schema.GarminExerciseSet`.

`weight` viene en gramos en la API de Garmin Connect (mismo patrón que
otros pesos de la API, ver conversión ya existente en
`services.body_measurement_service` para Feelfit) - se convierte a kg
aquí para que el resto del backend trabaje siempre en kg. `category`
puede venir vacío en series de tipo "REST"; se intenta también
`exercises[0].category` como respaldo, igual que hace la propia UI web
de Garmin Connect cuando el ejercicio detectado automáticamente no
coincide con `category`.
"""
from __future__ import annotations

from typing import Any

_GRAMOS_POR_KG = 1000.0


def map_raw_exercise_set(raw: dict[str, Any], numero_serie: int) -> dict[str, Any]:
    peso_g = raw.get("weight")
    categoria = raw.get("category")
    if not categoria:
        ejercicios = raw.get("exercises")
        if isinstance(ejercicios, list) and ejercicios:
            primero = ejercicios[0]
            if isinstance(primero, dict):
                categoria = primero.get("category")

    duracion = raw.get("duration")
    repeticiones = raw.get("repetitionCount")

    return {
        "numero_serie": numero_serie,
        "tipo_serie": raw.get("setType"),
        "repeticiones": round(repeticiones) if repeticiones is not None else None,
        "peso_kg": (peso_g / _GRAMOS_POR_KG) if peso_g is not None else None,
        "categoria_ejercicio": categoria,
        "duracion_seg": round(duracion) if duracion is not None else None,
        "raw_json": raw,
    }
