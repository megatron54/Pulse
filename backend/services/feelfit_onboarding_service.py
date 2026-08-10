"""Conecta la báscula Feelfit de un usuario YA EXISTENTE (a diferencia
de Garmin, que crea el usuario desde cero - Feelfit solo aporta peso/
composición corporal, no basta para dar de alta un perfil completo).

Misma política de contraseña que `garmin_onboarding_service`: vive solo
en memoria durante esta llamada, nunca se persiste - solo el
`token_store_dir` resultante se guarda en `FeelfitCredentials`."""
from __future__ import annotations

from typing import Callable

from sqlalchemy.orm import Session

from feelfit_client.client import FeelfitClient
from models.schema import FeelfitCredentials, UserProfile
from services.errors import EntityNotFoundError
from services.feelfit_sync_service import sync_feelfit_measurements


def connect_feelfit_account(
    session: Session,
    *,
    user_id: int,
    email: str,
    password: str,
    token_store_dir: str,
    client_factory: Callable[..., FeelfitClient] | None = None,
) -> int:
    """Inicia sesión en Feelfit, crea/reactiva `FeelfitCredentials` para
    `user_id`, y sincroniza TODO el histórico de mediciones disponible
    (`last_updated_at=0` - a diferencia del backfill de Garmin, la API
    de Feelfit no tiene el mismo riesgo documentado de rate-limit por
    volumen, así que no hace falta acotar una ventana de días).

    Devuelve el número de mediciones nuevas insertadas. Lanza
    `EntityNotFoundError` si `user_id` no existe, o
    `FeelfitAuthError` (propagada desde `FeelfitClient.login`) si el
    login falla - en ambos casos no se crea/toca ninguna credencial."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    factory = client_factory or FeelfitClient
    client = factory(token_store_dir=token_store_dir, email=email, password=password)
    client.login()

    credencial = session.query(FeelfitCredentials).filter_by(user_id=user_id).one_or_none()
    if credencial is None:
        session.add(
            FeelfitCredentials(user_id=user_id, token_store_dir=token_store_dir, activo=True)
        )
    else:
        credencial.token_store_dir = token_store_dir
        credencial.activo = True
    session.commit()

    return sync_feelfit_measurements(session, user_id, client, last_updated_at=0)
