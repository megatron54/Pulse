"""Tests para repositories.wger_credentials_repository — TDD."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, UserProfile, WgerCredentials
from repositories.wger_credentials_repository import get_active_token, save_token


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


class TestSaveToken:
    def test_crea_credenciales_nuevas_si_no_existian(self, session, usuario):
        save_token(session, usuario.id, "token-abc")
        fila = session.query(WgerCredentials).filter_by(user_id=usuario.id).one()
        assert fila.token == "token-abc"
        assert fila.activo is True

    def test_sobrescribe_el_token_si_ya_existian_credenciales(self, session, usuario):
        save_token(session, usuario.id, "token-viejo")
        save_token(session, usuario.id, "token-nuevo")
        filas = session.query(WgerCredentials).filter_by(user_id=usuario.id).all()
        assert len(filas) == 1
        assert filas[0].token == "token-nuevo"


class TestGetActiveToken:
    def test_devuelve_none_si_no_hay_credenciales(self, session, usuario):
        assert get_active_token(session, usuario.id) is None

    def test_devuelve_el_token_si_esta_activo(self, session, usuario):
        save_token(session, usuario.id, "token-abc")
        assert get_active_token(session, usuario.id) == "token-abc"

    def test_devuelve_none_si_las_credenciales_estan_inactivas(self, session, usuario):
        save_token(session, usuario.id, "token-abc")
        cred = session.query(WgerCredentials).filter_by(user_id=usuario.id).one()
        cred.activo = False
        session.commit()
        assert get_active_token(session, usuario.id) is None
