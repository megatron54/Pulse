from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import GarminConnectRequest, UserCreateRequest, UserOut
from garmin_sync.client import GarminAuthError, GarminRateLimitedError
from models.schema import UserProfile
from services.garmin_onboarding_service import (
    GarminPerfilIncompletoError,
    connect_new_user_via_garmin,
)

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(verify_api_key)])


def _directorio_tokens_por_defecto() -> Path:
    # Mismo criterio que scripts/garmin_pair.py (PULSE_GARMIN_TOKENS_DIR,
    # con fallback a ~/.garminconnect) - un solo lugar de verdad para
    # dónde vive el token cacheado de cada usuario.
    return Path(os.environ.get("PULSE_GARMIN_TOKENS_DIR", str(Path.home() / ".garminconnect")))


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserProfile:
    usuario = UserProfile(**payload.model_dump())
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/garmin-connect", response_model=UserOut, status_code=201)
def garmin_connect(payload: GarminConnectRequest, db: Session = Depends(get_db)) -> UserProfile:
    """Alta de un usuario nuevo conectando su cuenta de Garmin - sustituye
    al formulario manual de onboarding (petición explícita del usuario:
    "sin cuenta local, que al conectar Garmin se saquen esos datos de
    ahí"). `email`/`password` viajan solo en esta petición HTTPS, nunca
    se persisten (ver `GarminConnectRequest`/`connect_new_user_via_garmin`).

    El directorio de tokens usa un UUID en vez de un id de usuario (que
    todavía no existe en este punto) - no tiene que coincidir con
    ninguna convención de nombre, solo ser único y estable para que
    `python-garminconnect` cachee la sesión ahí.

    Limitación conocida (no soportada todavía): cuentas de Garmin con
    verificación en dos pasos (MFA) fallarán aquí con un 401 genérico -
    a diferencia de `services.garmin_pairing_service` (emparejamiento
    de una cuenta YA existente), este endpoint no pasa `mfa_code_prompt`
    porque una petición HTTP única no puede pedir el código interactivo
    a mitad de un login. Si se necesita soportar MFA en este flujo, hace
    falta un segundo endpoint que reciba el código tras un primer 401
    específico de MFA.
    """
    token_store_dir = str(_directorio_tokens_por_defecto() / f"pulse-connect-{uuid.uuid4().hex}")
    overrides = {
        campo: valor
        for campo, valor in (
            ("nombre", payload.nombre),
            ("altura_cm", payload.altura_cm),
            ("fecha_nacimiento", payload.fecha_nacimiento),
            ("sexo", payload.sexo),
        )
        if valor is not None
    }
    try:
        return connect_new_user_via_garmin(
            db,
            email=payload.email,
            password=payload.password,
            token_store_dir=token_store_dir,
            overrides=overrides,
        )
    except GarminPerfilIncompletoError as exc:
        raise HTTPException(
            status_code=422,
            detail={"campos_faltantes": exc.campos_faltantes},
        ) from exc
    except GarminRateLimitedError as exc:
        raise HTTPException(
            status_code=429,
            detail="Garmin ha aplicado rate-limiting a esta cuenta. Espera unos minutos antes de reintentar.",
        ) from exc
    except GarminAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail="No se pudo iniciar sesión en Garmin Connect - revisa tu email y contraseña.",
        ) from exc


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserProfile:
    usuario = db.get(UserProfile, user_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail=f"No existe usuario con id={user_id}")
    return usuario
