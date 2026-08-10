"""Tests para services.scheduler_service.run_daily_feelfit_sync_for_all_users
- TDD. Mismo principio de aislamiento por usuario que los jobs de
Garmin: un fallo de login/token expirado en UNA cuenta Feelfit nunca
debe impedir sincronizar las demás."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from feelfit_client.client import FeelfitAuthError
from models.schema import AuditLog, Base, BodyMeasurements, FeelfitCredentials, UserProfile
from services.scheduler_service import run_daily_feelfit_sync_for_all_users


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _crear_usuario_con_credenciales(session, nombre="Test", activo=True):
    u = UserProfile(nombre=nombre, altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M")
    session.add(u)
    session.commit()
    session.add(FeelfitCredentials(user_id=u.id, token_store_dir=f"/tmp/{nombre}", activo=activo))
    session.commit()
    return u


class _FakeClienteExitoso:
    def __init__(self, token_store_dir):
        self.token_store_dir = token_store_dir

    def login(self):
        pass

    def get_measurements_raw(self, last_updated_at=0):
        return {"measurements": [{"time_stamp": 1723300000, "weight": 74.1}]}


class _FakeClienteQueFallaLogin:
    def __init__(self, token_store_dir):
        pass

    def login(self):
        raise FeelfitAuthError("token expirado, sin password para relogear")


class TestRunDailyFeelfitSyncForAllUsers:
    def test_sincroniza_todos_los_usuarios_con_credenciales_activas(self, session):
        _crear_usuario_con_credenciales(session, "Ana")
        _crear_usuario_con_credenciales(session, "Bob")

        resultado = run_daily_feelfit_sync_for_all_users(
            session, client_factory=_FakeClienteExitoso
        )

        assert resultado.exitosos == 2
        assert resultado.fallidos == 0
        assert session.query(BodyMeasurements).count() == 2

    def test_omite_credenciales_inactivas(self, session):
        _crear_usuario_con_credenciales(session, "Activo", activo=True)
        _crear_usuario_con_credenciales(session, "Inactivo", activo=False)

        resultado = run_daily_feelfit_sync_for_all_users(
            session, client_factory=_FakeClienteExitoso
        )

        assert resultado.exitosos == 1
        assert resultado.omitidos == 1

    def test_un_fallo_de_login_no_impide_sincronizar_a_los_demas(self, session):
        _crear_usuario_con_credenciales(session, "FallaLogin")
        _crear_usuario_con_credenciales(session, "OK")

        llamadas = {"n": 0}

        def factory(token_store_dir):
            llamadas["n"] += 1
            if llamadas["n"] == 1:
                return _FakeClienteQueFallaLogin(token_store_dir)
            return _FakeClienteExitoso(token_store_dir)

        resultado = run_daily_feelfit_sync_for_all_users(session, client_factory=factory)

        assert resultado.exitosos == 1
        assert resultado.fallidos == 1
        assert (
            session.query(AuditLog).filter_by(regla_disparada="sync_feelfit_fallido").count() == 1
        )
