"""Tests para services.feelfit_onboarding_service - TDD."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, FeelfitCredentials, UserProfile
from services.errors import EntityNotFoundError
from services.feelfit_onboarding_service import connect_feelfit_account


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


class _FakeFeelfitClient:
    def __init__(self, *, token_store_dir, email=None, password=None):
        self.token_store_dir = token_store_dir
        self.email = email
        self.password = password
        self.login_called = False

    def login(self):
        self.login_called = True

    def get_measurements_raw(self, last_updated_at=0):
        return {"measurements": [{"time_stamp": 1723300000, "weight": 74.1}]}


class TestConnectFeelfitAccount:
    def test_crea_credenciales_y_sincroniza_el_historico(self, session, usuario):
        insertadas = connect_feelfit_account(
            session,
            user_id=usuario.id,
            email="a@b.com",
            password="secreto",
            token_store_dir="/tmp/feelfit-test",
            client_factory=_FakeFeelfitClient,
        )

        assert insertadas == 1
        cred = session.query(FeelfitCredentials).filter_by(user_id=usuario.id).one()
        assert cred.activo is True
        assert cred.token_store_dir == "/tmp/feelfit-test"

    def test_reconectar_reactiva_credenciales_existentes_sin_duplicarlas(self, session, usuario):
        connect_feelfit_account(
            session,
            user_id=usuario.id,
            email="a@b.com",
            password="secreto",
            token_store_dir="/tmp/feelfit-viejo",
            client_factory=_FakeFeelfitClient,
        )
        connect_feelfit_account(
            session,
            user_id=usuario.id,
            email="a@b.com",
            password="secreto2",
            token_store_dir="/tmp/feelfit-nuevo",
            client_factory=_FakeFeelfitClient,
        )

        credenciales = session.query(FeelfitCredentials).filter_by(user_id=usuario.id).all()
        assert len(credenciales) == 1
        assert credenciales[0].token_store_dir == "/tmp/feelfit-nuevo"

    def test_usuario_inexistente_lanza_entity_not_found_sin_crear_credenciales(self, session):
        with pytest.raises(EntityNotFoundError):
            connect_feelfit_account(
                session,
                user_id=99999,
                email="a@b.com",
                password="secreto",
                token_store_dir="/tmp/feelfit-test",
                client_factory=_FakeFeelfitClient,
            )
        assert session.query(FeelfitCredentials).count() == 0

    def test_login_fallido_no_crea_credenciales(self, session, usuario):
        class _FakeClienteQueFalla(_FakeFeelfitClient):
            def login(self):
                raise RuntimeError("credenciales inválidas")

        with pytest.raises(RuntimeError):
            connect_feelfit_account(
                session,
                user_id=usuario.id,
                email="a@b.com",
                password="mala",
                token_store_dir="/tmp/feelfit-test",
                client_factory=_FakeClienteQueFalla,
            )
        assert session.query(FeelfitCredentials).count() == 0
