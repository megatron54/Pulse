"""Emparejamiento inicial de una cuenta Garmin real (Fase H).

El login con email/contraseña ocurre AQUÍ, una sola vez, para generar
el token OAuth que `python-garminconnect` cachea en `token_store_dir` -
ni el email ni la contraseña se persisten jamás en la base de datos de
Pulse (ver docstring de `models.schema.GarminCredentials`); Pulse solo
guarda la ruta al directorio del token cacheado. Después de este
emparejamiento, el scheduler nocturno (`services.scheduler_service`)
reutiliza siempre ese token, nunca vuelve a pedir la contraseña.

Esta función es la parte TESTEABLE del flujo de emparejamiento (login +
persistencia, con un `api_factory` inyectable como el resto de
`garmin_sync`). La parte interactiva (pedir email/password por
terminal sin que se guarden en ningún log ni historial de chat) vive
en `scripts/garmin_pair.py`, deliberadamente FUERA de esta capa - un
script de un solo uso, ejecutado a mano por el usuario en su propia
terminal, nunca vía la API/web de Pulse ni vía un agente de IA (mismo
criterio de seguridad documentado en el docstring del modelo)."""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from garmin_sync.client import GarminClient
from models.schema import GarminCredentials, UserProfile
from repositories.garmin_credentials_repository import upsert_garmin_credentials
from services.errors import EntityNotFoundError


def pair_garmin_account(
    session: Session,
    user_id: int,
    email: str,
    password: str,
    token_store_dir: str,
    api_factory: Callable[..., Any] | None = None,
    mfa_code_prompt: Callable[[], str] | None = None,
) -> GarminCredentials:
    """Intenta el login UNA vez (política ya establecida en
    `GarminClient.login`: nunca reintentar agresivamente) y solo si
    tiene éxito persiste la referencia al token cacheado. Un fallo de
    login (credenciales incorrectas, rate-limit, MFA pendiente) se
    propaga tal cual - `email`/`password` nunca llegan a la base de
    datos en ningún caso, con éxito o sin él.

    `mfa_code_prompt` se reenvía tal cual a `GarminClient` - necesario
    para cuentas reales con verificación en dos pasos (ver
    scripts/garmin_pair.py, que pasa un callback que pide el código por
    terminal)."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    client = GarminClient(
        token_store_dir=token_store_dir,
        email=email,
        password=password,
        api_factory=api_factory,
        mfa_code_prompt=mfa_code_prompt,
    )
    client.login()

    return upsert_garmin_credentials(session, user_id, token_store_dir)
