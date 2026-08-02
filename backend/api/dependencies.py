"""Dependencias de FastAPI: sesión de BD por request y verificación de
API key (auth v1 mínima para mono-usuario, ver docs/02-roadmap/
02-plan-autonomo.md, Fase D)."""
from __future__ import annotations

import os
import secrets
from typing import Generator

from fastapi import Header, HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from models.database import create_pulse_engine

_engine: Engine | None = None


def get_engine() -> Engine:
    """Engine único reutilizado entre requests (patrón estándar de
    SQLAlchemy: el Engine gestiona su propio pool de conexiones)."""
    global _engine
    if _engine is None:
        _engine = create_pulse_engine()
    return _engine


def get_db() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Fail-closed: fuera de `PULSE_ENV=dev` (o si no se define, se
    asume dev para no romper el flujo local), exigir `PULSE_API_KEY`
    configurada es obligatorio - un despliegue en el que se olvidó la
    env var debe fallar ruidosamente (500), nunca quedar abierto en
    silencio. En `dev` explícito sin key configurada, la verificación se
    omite para no bloquear el desarrollo local.
    """
    entorno = os.environ.get("PULSE_ENV", "dev")
    api_key_esperada = os.environ.get("PULSE_API_KEY")

    if entorno != "dev" and not api_key_esperada:
        raise HTTPException(
            status_code=500,
            detail="PULSE_API_KEY no configurada fuera de PULSE_ENV=dev",
        )
    if api_key_esperada and not secrets.compare_digest(x_api_key or "", api_key_esperada):
        raise HTTPException(status_code=401, detail="API key inválida o ausente")
