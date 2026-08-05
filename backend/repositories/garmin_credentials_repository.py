"""Repositorio de `GarminCredentials` - ver el docstring del modelo
(models/schema.py) para el razonamiento completo: esta tabla SOLO
guarda una referencia al directorio donde `python-garminconnect` cachea
el token OAuth ya autenticado, nunca la contraseña del usuario."""
from __future__ import annotations

from sqlalchemy.orm import Session

from models.schema import GarminCredentials


def upsert_garmin_credentials(
    session: Session, user_id: int, token_store_dir: str
) -> GarminCredentials:
    """Crea las credenciales si no existen, o actualiza el
    `token_store_dir` y reactiva (`activo=True`) si ya existían -
    permite re-emparejar sin duplicar fila (hay un `unique=True` en
    `user_id`, así que un segundo INSERT lanzaría IntegrityError)."""
    cred = session.query(GarminCredentials).filter_by(user_id=user_id).first()
    if cred is None:
        cred = GarminCredentials(user_id=user_id, token_store_dir=token_store_dir)
        session.add(cred)
    else:
        cred.token_store_dir = token_store_dir
        cred.activo = True
    session.commit()
    session.refresh(cred)
    return cred
