"""Tests para services.scheduler_service.run_daily_activity_sync_for_all_users
— TDD.

Función separada de `run_daily_sync_for_all_users` (que sincroniza
recovery) a propósito: son dos preocupaciones independientes con su
propia cadencia razonable (recovery es diario y de 1 solo día;
actividades puede mirar una ventana de varios días para no perder
actividades que Garmin tarda en consolidar), y mezclarlas habría
arriesgado la suite ya extensa de tests de recovery sync. Mismo
principio de aislamiento por usuario que esa función."""
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import AuditLog, Base, GarminActivity, GarminCredentials, UserProfile
from services.scheduler_service import run_daily_activity_sync_for_all_users


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
    session.add(
        GarminCredentials(user_id=u.id, token_store_dir=f"/tokens/{u.id}", activo=activo)
    )
    session.commit()
    return u


def _fake_api_factory(actividades=None):
    fake_api = MagicMock()
    fake_api.get_activities_by_date.return_value = actividades or []
    return lambda *a, **k: fake_api


_ACTIVIDAD_EJEMPLO = {
    "activityId": 1,
    "startTimeLocal": "2026-08-01 07:00:00",
    "activityType": {"typeKey": "running"},
    "duration": 1800.0,
}


class TestRunDailyActivitySyncForAllUsers:
    def test_sincroniza_actividades_de_todos_los_usuarios_con_credenciales_activas(
        self, session
    ):
        u1 = _crear_usuario_con_credenciales(session, nombre="U1")
        u2 = _crear_usuario_con_credenciales(session, nombre="U2")

        resultado = run_daily_activity_sync_for_all_users(
            session,
            end_date=date(2026, 8, 4),
            api_factory=_fake_api_factory([_ACTIVIDAD_EJEMPLO]),
        )

        assert resultado.exitosos == 2
        assert resultado.fallidos == 0
        assert session.query(GarminActivity).filter_by(user_id=u1.id).count() == 1
        assert session.query(GarminActivity).filter_by(user_id=u2.id).count() == 1

    def test_ignora_usuarios_con_credenciales_inactivas(self, session):
        _crear_usuario_con_credenciales(session, nombre="Activo", activo=True)
        _crear_usuario_con_credenciales(session, nombre="Inactivo", activo=False)

        resultado = run_daily_activity_sync_for_all_users(
            session, end_date=date(2026, 8, 4), api_factory=_fake_api_factory()
        )
        assert resultado.exitosos == 1
        assert resultado.omitidos == 1

    def test_un_fallo_de_login_no_impide_sincronizar_a_los_demas(self, session):
        u_falla = _crear_usuario_con_credenciales(session, nombre="Falla")
        u_ok = _crear_usuario_con_credenciales(session, nombre="OK")

        llamadas = {"n": 0}

        def api_factory_con_fallo(*args, **kwargs):
            llamadas["n"] += 1
            if llamadas["n"] == 1:
                fake_api = MagicMock()
                fake_api.login.side_effect = Exception("token caducado")
                return fake_api
            return _fake_api_factory([_ACTIVIDAD_EJEMPLO])(*args, **kwargs)

        resultado = run_daily_activity_sync_for_all_users(
            session, end_date=date(2026, 8, 4), api_factory=api_factory_con_fallo
        )
        assert resultado.exitosos == 1
        assert resultado.fallidos == 1
        assert session.query(GarminActivity).count() == 1

    def test_registra_auditoria_por_fallo(self, session):
        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("boom")
        _crear_usuario_con_credenciales(session, nombre="Falla")

        run_daily_activity_sync_for_all_users(
            session, end_date=date(2026, 8, 4), api_factory=lambda *a, **k: fake_api
        )
        auditoria = session.query(AuditLog).filter_by(modulo="scheduler_activities").one()
        assert auditoria.output == "error"

    def test_fallo_al_auditar_no_aborta_el_resto_del_batch(self, session, monkeypatch):
        # Misma salvaguarda que run_daily_sync_for_all_users (HIGH-2 de
        # code-review original): si escribir el propio AuditLog de un
        # fallo lanzara una excepción, el resto del batch debe seguir.
        u_falla = _crear_usuario_con_credenciales(session, nombre="Falla")
        u_ok = _crear_usuario_con_credenciales(session, nombre="OK")

        llamadas = {"n": 0}
        original_add = session.add

        def add_que_falla_una_vez(instancia):
            if isinstance(instancia, AuditLog) and llamadas["n"] == 0:
                llamadas["n"] += 1
                raise Exception("fallo simulado escribiendo auditoría")
            original_add(instancia)

        monkeypatch.setattr(session, "add", add_que_falla_una_vez)

        llamadas_api = {"n": 0}

        def api_factory(*args, **kwargs):
            llamadas_api["n"] += 1
            if llamadas_api["n"] == 1:
                fake_api = MagicMock()
                fake_api.login.side_effect = Exception("boom")
                return fake_api
            return _fake_api_factory([_ACTIVIDAD_EJEMPLO])(*args, **kwargs)

        resultado = run_daily_activity_sync_for_all_users(
            session, end_date=date(2026, 8, 4), api_factory=api_factory
        )
        assert resultado.fallidos == 1
        assert resultado.exitosos == 1
        assert session.query(GarminActivity).filter_by(user_id=u_ok.id).count() == 1
