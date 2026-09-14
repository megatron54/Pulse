"""Proxy fino de la API sobre el catálogo de ejercicios de wger
(`wger_client/`, construido en la Fase E del plan autónomo pero nunca
conectado a ningún endpoint hasta ahora - ver 02-roadmap/
03-vision-produccion.md, "selector de ejercicios de wger").

A diferencia del resto de routers, este NO toca la base de datos de
Pulse - es una traducción de errores de `wger_client` (que ya aplana y
valida el payload de wger) a códigos HTTP, nada más. `language` por
defecto es 2 (inglés), el mismo id que usa `wger_client.client` en sus
docstrings - ver `/api/v2/language/` en la instancia real de wger para
el mapeo completo si se necesita otro idioma.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_wger_client, verify_api_key
from api.schemas import EquipmentOut, ExerciseCategoryOut, ExerciseOut
from wger_client.client import WgerAuthError, WgerClient, WgerRequestError

router = APIRouter(
    prefix="/exercises",
    tags=["exercises"],
    dependencies=[Depends(verify_api_key)],
)

logger = logging.getLogger(__name__)

_LANGUAGE_POR_DEFECTO = 2

# El `detail` que ve el usuario. Antes era `str(exc)`, y la auditoría del
# frontend lo encontró escrito tal cual en la pantalla de Entrenamiento:
# "Fallo de conexión con wger: [Errno 111] Connection refused". Eso es
# un mensaje para los logs, no para una persona: nombra una dependencia
# interna que el usuario no conoce (y que pidió no ver) y añade un errno
# de sistema. El texto real sigue existiendo, en el log del servidor.
_DETALLE_CATALOGO = (
    "El catálogo de ejercicios no está disponible ahora mismo. "
    "Vuelve a intentarlo en un rato."
)


# Las dos únicas excepciones que `WgerClient` lanza (ver
# wger_client/client.py). Se capturan por nombre y no con un
# `except Exception`: así un fallo inesperado del proxy (p. ej. un
# `AttributeError` porque wger cambió la forma de su respuesta) sale
# como 500 y se ve en el monitor, en vez de disfrazarse de "wger está
# caído" y quedar indistinguible de una caída real.
_ERRORES_WGER = (WgerAuthError, WgerRequestError)


def _error_catalogo(exc: Exception, operacion: str) -> HTTPException:
    logger.warning("Fallo del catálogo de ejercicios (%s): %s", operacion, exc)
    return HTTPException(status_code=502, detail=_DETALLE_CATALOGO)


@router.get("/categories", response_model=list[ExerciseCategoryOut])
def get_exercise_categories(wger: WgerClient = Depends(get_wger_client)) -> list[dict]:
    try:
        return wger.get_exercise_categories()
    except _ERRORES_WGER as exc:
        raise _error_catalogo(exc, "categories") from exc


@router.get("/equipment", response_model=list[EquipmentOut])
def get_equipment(wger: WgerClient = Depends(get_wger_client)) -> list[dict]:
    try:
        return wger.get_equipment()
    except _ERRORES_WGER as exc:
        raise _error_catalogo(exc, "equipment") from exc


@router.get("/search", response_model=list[ExerciseOut])
def search_exercises(
    category_id: int,
    language: int = Query(default=_LANGUAGE_POR_DEFECTO),
    limit: int = Query(default=50, ge=1, le=200),
    wger: WgerClient = Depends(get_wger_client),
) -> list[dict]:
    try:
        return wger.search_exercises(category_id=category_id, language=language, limit=limit)
    except _ERRORES_WGER as exc:
        raise _error_catalogo(exc, "search") from exc
