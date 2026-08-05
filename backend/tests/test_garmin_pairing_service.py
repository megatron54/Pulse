"""Tests para services.garmin_pairing_service — TDD.

Cubre la lógica testeable del emparejamiento inicial de una cuenta
Garmin real (Fase H, desbloqueada por el usuario con su cuenta real):
login con email/password UNA sola vez (nunca se persisten), y
persistencia de la referencia al token cacheado. La parte interactiva
(pedir email/password por terminal) vive en scripts/garmin_pair.py y
NO se testea aquí a propósito - ver ese script para el razonamiento de
por qué el I/O interactivo queda fuera del alcance de TDD."""
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from garmin_sync.client import GarminAuthError
from models.schema import Base, GarminCredentials, UserProfile
from services.garmin_pairing_service import pair_garmin_account


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def usuario(session):
    u = UserProfile(nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M")
    session.add(u)
    session.commit()
    return u


def _fake_api_factory(fake_api):
    return lambda *a, **k: fake_api


class TestPairGarminAccount:
    def test_login_exitoso_persiste_las_credenciales(self, session, usuario):
        fake_api = MagicMock()

        pair_garmin_account(
            session,
            user_id=usuario.id,
            email="atleta@example.com",
            password="correcto-caballo-bateria-grapa",
            token_store_dir="/tokens/1",
            api_factory=_fake_api_factory(fake_api),
        )

        fake_api.login.assert_called_once_with("/tokens/1")
        cred = session.query(GarminCredentials).filter_by(user_id=usuario.id).one()
        assert cred.token_store_dir == "/tokens/1"
        assert cred.activo is True

    def test_login_fallido_no_persiste_nada_y_propaga_el_error(self, session, usuario):
        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("credenciales incorrectas")

        with pytest.raises(GarminAuthError):
            pair_garmin_account(
                session,
                user_id=usuario.id,
                email="atleta@example.com",
                password="incorrecta",
                token_store_dir="/tokens/1",
                api_factory=_fake_api_factory(fake_api),
            )

        assert session.query(GarminCredentials).count() == 0

    def test_usuario_inexistente_lanza_entity_not_found_sin_intentar_login(self, session):
        from services.errors import EntityNotFoundError

        fake_api = MagicMock()
        with pytest.raises(EntityNotFoundError):
            pair_garmin_account(
                session,
                user_id=99999,
                email="atleta@example.com",
                password="x",
                token_store_dir="/tokens/1",
                api_factory=_fake_api_factory(fake_api),
            )
        fake_api.login.assert_not_called()

    def test_reenvia_el_prompt_mfa_al_garmin_client(self, session, usuario):
        # LOW-2 de code-review: cuentas reales con verificación en dos
        # pasos necesitan este callback para completar el login.
        fake_api = MagicMock()
        llamadas: dict = {}

        def api_factory(*args, **kwargs):
            llamadas["kwargs"] = kwargs
            return fake_api

        prompt = lambda: "123456"  # noqa: E731 - callback trivial de test

        pair_garmin_account(
            session,
            user_id=usuario.id,
            email="atleta@example.com",
            password="x",
            token_store_dir="/tokens/1",
            api_factory=api_factory,
            mfa_code_prompt=prompt,
        )

        assert llamadas["kwargs"].get("prompt_mfa") is prompt
