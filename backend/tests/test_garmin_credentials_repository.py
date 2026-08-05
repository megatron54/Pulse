"""Tests para repositories.garmin_credentials_repository — TDD."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminCredentials, UserProfile
from repositories.garmin_credentials_repository import upsert_garmin_credentials


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


class TestUpsertGarminCredentials:
    def test_crea_credenciales_nuevas_activas(self, session, usuario):
        cred = upsert_garmin_credentials(session, usuario.id, "/tokens/1")
        assert cred.user_id == usuario.id
        assert cred.token_store_dir == "/tokens/1"
        assert cred.activo is True

    def test_reemparejar_actualiza_el_directorio_y_reactiva(self, session, usuario):
        session.add(
            GarminCredentials(user_id=usuario.id, token_store_dir="/tokens/viejo", activo=False)
        )
        session.commit()

        cred = upsert_garmin_credentials(session, usuario.id, "/tokens/nuevo")

        assert cred.token_store_dir == "/tokens/nuevo"
        assert cred.activo is True
        assert session.query(GarminCredentials).filter_by(user_id=usuario.id).count() == 1

    def test_no_persiste_ningun_campo_de_password(self, session, usuario):
        columnas = set(GarminCredentials.__table__.columns.keys())
        assert "password" not in columnas
        assert "email" not in columnas
