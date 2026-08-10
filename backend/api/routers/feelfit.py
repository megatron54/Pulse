"""Conexión de la báscula Feelfit para un usuario YA EXISTENTE (a
diferencia de Garmin, que da de alta al usuario desde cero - ver
services.feelfit_onboarding_service para el porqué)."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import FeelfitConnectOut, FeelfitConnectRequest
from feelfit_client.client import FeelfitAuthError
from services.errors import EntityNotFoundError
from services.feelfit_onboarding_service import connect_feelfit_account

router = APIRouter(
    prefix="/users/{user_id}/feelfit-connect",
    tags=["feelfit"],
    dependencies=[Depends(verify_api_key)],
)


def _directorio_tokens_por_defecto() -> Path:
    # Mismo criterio que PULSE_GARMIN_TOKENS_DIR en api.routers.users -
    # un solo lugar de verdad para dónde vive el token cacheado.
    return Path(os.environ.get("PULSE_FEELFIT_TOKENS_DIR", str(Path.home() / ".feelfit")))


@router.post("", response_model=FeelfitConnectOut, status_code=201)
def feelfit_connect(
    user_id: int, payload: FeelfitConnectRequest, db: Session = Depends(get_db)
) -> FeelfitConnectOut:
    """Conecta la cuenta de Feelfit de `user_id` y sincroniza todo el
    histórico de mediciones disponible. `email`/`password` viajan solo
    en esta petición HTTPS, nunca se persisten."""
    token_store_dir = str(_directorio_tokens_por_defecto() / f"user-{user_id}")
    try:
        mediciones_importadas = connect_feelfit_account(
            db,
            user_id=user_id,
            email=payload.email,
            password=payload.password,
            token_store_dir=token_store_dir,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeelfitAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail="No se pudo iniciar sesión en Feelfit - revisa tu email y contraseña.",
        ) from exc

    return FeelfitConnectOut(mediciones_importadas=mediciones_importadas)
