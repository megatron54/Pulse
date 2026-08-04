"""Repositorio de credenciales de wger del usuario (token permanente de
su propia API, ver docstring de `models.schema.WgerCredentials` para el
razonamiento de seguridad y la deuda pendiente de cifrado en reposo)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from models.schema import WgerCredentials


def save_token(session: Session, user_id: int, token: str) -> None:
    """Crea o actualiza el token del usuario - a diferencia de
    `GarminCredentials` (una fila por usuario que nunca se sobrescribe
    tras crearse), aquí SÍ tiene sentido sobrescribir: un usuario puede
    regenerar su token en wger (p.ej. tras sospechar que se filtró) y
    Pulse debe usar siempre el más reciente, nunca acumular tokens
    caducados en la tabla."""
    existente = session.query(WgerCredentials).filter_by(user_id=user_id).first()
    if existente is not None:
        existente.token = token
        existente.activo = True
    else:
        session.add(WgerCredentials(user_id=user_id, token=token))
    session.commit()


def get_active_token(session: Session, user_id: int) -> str | None:
    cred = (
        session.query(WgerCredentials)
        .filter_by(user_id=user_id, activo=True)
        .first()
    )
    return cred.token if cred is not None else None
