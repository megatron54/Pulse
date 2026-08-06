"""Tests para services.scheduler_service — TDD.

Fase C del plan autónomo (docs/02-roadmap/02-plan-autonomo.md): la
infraestructura de sincronización diaria masiva para TODOS los usuarios
con GarminCredentials activas. Sin credenciales reales todavía (Fase H
bloqueada), pero el código y sus tests quedan listos.

Principio clave: un fallo sincronizando UN usuario (rate-limit, token
caducado, InsufficientDataError puntual) NUNCA debe impedir que se
sincronicen los demás - mismo principio de aislamiento por-campo que ya
usa garmin_sync.client._llamada_segura.
"""
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from garmin_sync.client import GarminAuthError
from garmin_sync.mapper import InsufficientDataError
from models.schema import (
    AuditLog,
    Base,
    GarminCredentials,
    GarminDailyMetrics,
    ReadinessLog,
    UserProfile,
)
from services.scheduler_service import run_daily_sync_for_all_users


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


def _fake_api_factory(hrv=65.0, readiness="high", body_battery=80, sleep=85):
    fake_api = MagicMock()
    fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": hrv}}
    fake_api.get_training_readiness.return_value = [{"level": readiness.upper()}]
    fake_api.get_body_battery.return_value = [{"charged": body_battery, "drained": 10}]
    fake_api.get_sleep_data.return_value = {
        "dailySleepDTO": {"sleepScores": {"overall": {"value": sleep}}}
    }
    # Épica A (02-roadmap/03-vision-produccion.md) - ver mismo comentario
    # en test_readiness_service.py: sin esto, un MagicMock sin configurar
    # rompe los extractores nuevos de garmin_sync.client.
    fake_api.get_stress_data.return_value = {}
    fake_api.get_rhr_day.return_value = {}
    fake_api.get_max_metrics.return_value = []
    return lambda *a, **k: fake_api


class TestRunDailySyncForAllUsers:
    def test_sincroniza_a_todos_los_usuarios_con_credenciales_activas(self, session):
        u1 = _crear_usuario_con_credenciales(session, nombre="U1")
        u2 = _crear_usuario_con_credenciales(session, nombre="U2")

        resultado = run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=_fake_api_factory()
        )

        assert resultado.exitosos == 2
        assert resultado.fallidos == 0
        assert session.query(ReadinessLog).filter_by(user_id=u1.id).count() == 1
        assert session.query(ReadinessLog).filter_by(user_id=u2.id).count() == 1

    def test_ignora_usuarios_con_credenciales_inactivas(self, session):
        _crear_usuario_con_credenciales(session, nombre="Activo", activo=True)
        _crear_usuario_con_credenciales(session, nombre="Inactivo", activo=False)

        resultado = run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=_fake_api_factory()
        )
        assert resultado.exitosos == 1
        assert resultado.omitidos == 1

    def test_sin_usuarios_con_credenciales_no_falla(self, session):
        resultado = run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=_fake_api_factory()
        )
        assert resultado.exitosos == 0
        assert resultado.fallidos == 0

    def test_un_fallo_no_impide_sincronizar_a_los_demas(self, session):
        u_falla = _crear_usuario_con_credenciales(session, nombre="Falla")
        u_ok = _crear_usuario_con_credenciales(session, nombre="OK")

        llamadas = {"n": 0}

        def api_factory_con_fallo(*args, **kwargs):
            llamadas["n"] += 1
            if llamadas["n"] == 1:
                fake_api = MagicMock()
                fake_api.login.side_effect = Exception("token caducado")
                return fake_api
            return _fake_api_factory()(*args, **kwargs)

        resultado = run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=api_factory_con_fallo
        )
        assert resultado.exitosos == 1
        assert resultado.fallidos == 1
        # El usuario que sí funcionó debe tener su ReadinessLog igualmente.
        assert session.query(ReadinessLog).count() == 1

    def test_registra_auditoria_por_fallo(self, session):
        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("boom")
        _crear_usuario_con_credenciales(session, nombre="Falla")

        run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=lambda *a, **k: fake_api
        )
        auditoria = session.query(AuditLog).filter_by(modulo="scheduler").one()
        assert auditoria.output == "error"

    def test_exito_previo_sobrevive_al_rollback_de_un_fallo_posterior(self, session):
        """Regresión del hallazgo HIGH/MED-1 de code-review: procesar un
        usuario OK primero y uno que falla después no debe perder el
        ReadinessLog ya comprometido del primero al hacer rollback()
        para el segundo, porque cada iteración exitosa hace su propio
        commit interno (sync_and_compute_readiness) antes de que
        empiece la siguiente iteración."""
        u_ok = _crear_usuario_con_credenciales(session, nombre="OK")
        u_falla = _crear_usuario_con_credenciales(session, nombre="Falla")

        llamadas = {"n": 0}

        def api_factory(*args, **kwargs):
            llamadas["n"] += 1
            if llamadas["n"] == 1:
                return _fake_api_factory()(*args, **kwargs)
            fake_api = MagicMock()
            fake_api.login.side_effect = Exception("token caducado")
            return fake_api

        resultado = run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=api_factory
        )
        assert resultado.exitosos == 1
        assert resultado.fallidos == 1
        assert session.query(ReadinessLog).filter_by(user_id=u_ok.id).count() == 1
        assert session.query(ReadinessLog).filter_by(user_id=u_falla.id).count() == 0

    def test_insufficient_data_error_persiste_metrics_crudas_pero_cuenta_como_fallo(
        self, session
    ):
        """El dato crudo de Garmin se persiste aunque falte un campo
        crítico (principio "no perder el dato aunque falte un campo
        puntual", ver docstring de readiness_service). El usuario se
        sigue contando como fallido porque no hubo ReadinessLog."""
        u = _crear_usuario_con_credenciales(session, nombre="DatoParcial")

        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {}  # sin lastNightAvg -> hrv_today=None
        fake_api.get_training_readiness.return_value = [{"level": "HIGH"}]
        fake_api.get_body_battery.return_value = [{"charged": 80, "drained": 10}]
        fake_api.get_sleep_data.return_value = {
            "dailySleepDTO": {"sleepScores": {"overall": {"value": 85}}}
        }
        fake_api.get_stress_data.return_value = {}
        fake_api.get_rhr_day.return_value = {}
        fake_api.get_max_metrics.return_value = []

        resultado = run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=lambda *a, **k: fake_api
        )
        assert resultado.fallidos == 1
        assert session.query(GarminDailyMetrics).filter_by(user_id=u.id).count() == 1
        assert session.query(ReadinessLog).filter_by(user_id=u.id).count() == 0

    def test_fallo_al_auditar_no_aborta_el_resto_del_batch(self, session, monkeypatch):
        """HIGH-2 de code-review: si escribir el propio AuditLog de un
        fallo lanzara una excepción (p.ej. FK inválida), el resto de
        usuarios del batch deben seguir procesándose igualmente."""
        u_falla = _crear_usuario_con_credenciales(session, nombre="Falla")
        u_ok = _crear_usuario_con_credenciales(session, nombre="OK")

        import services.scheduler_service as scheduler_service_module

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
            return _fake_api_factory()(*args, **kwargs)

        resultado = run_daily_sync_for_all_users(
            session, target_date=date(2026, 8, 2), api_factory=api_factory
        )
        assert resultado.fallidos == 1
        assert resultado.exitosos == 1
        assert session.query(ReadinessLog).filter_by(user_id=u_ok.id).count() == 1
