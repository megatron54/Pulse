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

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_wger_client, verify_api_key
from api.schemas import EquipmentOut, ExerciseCategoryOut, ExerciseOut
from wger_client.client import WgerClient

router = APIRouter(
    prefix="/exercises",
    tags=["exercises"],
    dependencies=[Depends(verify_api_key)],
)

_LANGUAGE_POR_DEFECTO = 2


@router.get("/categories", response_model=list[ExerciseCategoryOut])
def get_exercise_categories(wger: WgerClient = Depends(get_wger_client)) -> list[dict]:
    try:
        return wger.get_exercise_categories()
    except Exception as exc:  # noqa: BLE001 - WgerAuthError y WgerRequestError, ambos -> 502
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/equipment", response_model=list[EquipmentOut])
def get_equipment(wger: WgerClient = Depends(get_wger_client)) -> list[dict]:
    try:
        return wger.get_equipment()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/search", response_model=list[ExerciseOut])
def search_exercises(
    category_id: int,
    language: int = Query(default=_LANGUAGE_POR_DEFECTO),
    limit: int = Query(default=50, ge=1, le=200),
    wger: WgerClient = Depends(get_wger_client),
) -> list[dict]:
    try:
        return wger.search_exercises(category_id=category_id, language=language, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
