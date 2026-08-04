"""Diario de comidas real del usuario, vía SU PROPIO wger (petición
explícita del usuario, ver 02-roadmap/03-vision-produccion.md, épica de
food log). El diario en sí vive en wger - Pulse solo guarda la
referencia al token del usuario (nunca su contraseña, ver docstring de
`models.schema.WgerCredentials` para la deuda de cifrado en reposo
documentada explícitamente) y orquesta las llamadas.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_db, get_wger_client, verify_api_key
from api.schemas import (
    DailyFoodLogOut,
    FoodLogEntryRequest,
    IngredientOut,
    WgerTokenRequest,
)
from services.errors import EntityNotFoundError
from services.food_log_service import get_daily_food_log, log_food_entry
from services.food_log_service import save_wger_token as save_wger_token_service
from sqlalchemy.orm import Session
from wger_client.client import WgerAuthError, WgerClient

router = APIRouter(
    prefix="/users/{user_id}/nutrition",
    tags=["food-log"],
    dependencies=[Depends(verify_api_key)],
)

_LANGUAGE_POR_DEFECTO = 2


@router.post("/wger-token", status_code=204)
def save_wger_token(
    user_id: int, payload: WgerTokenRequest, db: Session = Depends(get_db)
) -> None:
    """Guarda el token permanente que el usuario generó él mismo desde
    la página "API key" de su wger (ver la guía oficial de wger citada
    en 02-roadmap/03-vision-produccion.md) - Pulse nunca ve ni pide su
    contraseña. Nunca se devuelve el token en ninguna respuesta (ver
    `WgerTokenRequest`, que solo se usa como schema de entrada, jamás de
    salida)."""
    save_wger_token_service(db, user_id, payload.token)


@router.get("/ingredients/search", response_model=list[IngredientOut])
def search_ingredients(
    query: str,
    language: int = Query(default=_LANGUAGE_POR_DEFECTO),
    limit: int = Query(default=20, ge=1, le=100),
    wger: WgerClient = Depends(get_wger_client),
) -> list[dict]:
    """Búsqueda de ingredientes de solo lectura (público, sin token) -
    mismo patrón que `/exercises/search`."""
    try:
        return wger.search_ingredients(query=query, language=language, limit=limit)
    except Exception as exc:  # noqa: BLE001 - fallo del proxy hacia wger, no del cliente de Pulse
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/food-log", status_code=201)
def create_food_log_entry(
    user_id: int,
    payload: FoodLogEntryRequest,
    db: Session = Depends(get_db),
    wger: WgerClient = Depends(get_wger_client),
) -> None:
    try:
        log_food_entry(
            db,
            user_id,
            ingredient_id=payload.ingredient_id,
            amount_grams=payload.amount_grams,
            wger=wger,
        )
    except EntityNotFoundError:
        # No convertir aquí: dejar que el handler global de
        # api/main.py (@app.exception_handler(EntityNotFoundError)) la
        # mapee a 404, igual que el resto de routers de la API - el
        # `except Exception` de abajo NO debe capturarla (hereda de
        # ValueError -> Exception), o el 404 se convertiría en un 502
        # incorrecto.
        raise
    except WgerAuthError as exc:
        # Distinto de un fallo genérico de wger (502): el token del
        # usuario ya no es válido, algo que el propio usuario puede
        # arreglar (regenerar el token), no un problema de wger caído.
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - fallo del proxy hacia wger, no del cliente de Pulse
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/food-log", response_model=DailyFoodLogOut)
def get_food_log(
    user_id: int,
    target_date: date = Query(alias="date"),
    db: Session = Depends(get_db),
    wger: WgerClient = Depends(get_wger_client),
) -> DailyFoodLogOut:
    try:
        resultado = get_daily_food_log(db, user_id, target_date=target_date, wger=wger)
    except EntityNotFoundError:
        raise
    except WgerAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - fallo del proxy hacia wger, no del cliente de Pulse
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return DailyFoodLogOut.model_validate(resultado, from_attributes=True)
