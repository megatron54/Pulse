"""Tests del sync manual bajo demanda (services.garmin_manual_sync_service)
- TDD. Ver docstring del módulo para el razonamiento de por qué existe
separado del backfill histórico."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminCredentials, ReadinessLog, UserProfile
from services.garmin_manual_sync_service import GarminNoConectadoError, sync_today_for_user


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _usuario_con_garmin(session, token_store_dir="/data/garmin-tokens/pulse-user-1"):
    usuario = UserProfile(
        nombre="Miguel", sexo="M", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28)
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    session.add(GarminCredentials(user_id=usuario.id, token_store_dir=token_store_dir, activo=True))
    session.commit()
    return usuario


def _fake_api():
    fake_api = MagicMock()
    fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 65}}
    fake_api.get_training_readiness.return_value = None
    fake_api.get_body_battery.return_value = [{"charged": 80, "bodyBatteryValuesArray": []}]
    fake_api.get_sleep_data.return_value = {
        "dailySleepDTO": {"sleepScores": {"overall": {"value": 75}}}
    }
    fake_api.get_stress_data.return_value = None
    fake_api.get_rhr_day.return_value = None
    fake_api.get_max_metrics.return_value = None
    fake_api.get_heart_rates.return_value = None
    return fake_api


class TestSyncTodayForUser:
    def test_usuario_sin_credenciales_lanza_garmin_no_conectado(self, session):
        usuario = UserProfile(
            nombre="Miguel", sexo="M", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28)
        )
        session.add(usuario)
        session.commit()
        session.refresh(usuario)

        with pytest.raises(GarminNoConectadoError):
            sync_today_for_user(session, usuario.id)

    def test_usuario_con_credenciales_desactivadas_lanza_garmin_no_conectado(self, session):
        usuario = _usuario_con_garmin(session)
        cred = session.query(GarminCredentials).filter_by(user_id=usuario.id).one()
        cred.activo = False
        session.commit()

        with pytest.raises(GarminNoConectadoError):
            sync_today_for_user(session, usuario.id)

    def test_sincroniza_recovery_e_intradia_del_dia_pedido(self, session, monkeypatch):
        usuario = _usuario_con_garmin(session)
        fake_api = _fake_api()

        import garmin_sync.client as client_module

        monkeypatch.setattr(client_module, "_default_api_factory", lambda: lambda *a, **k: fake_api)

        resultado = sync_today_for_user(session, usuario.id, target_date=date(2026, 8, 10))

        fake_api.login.assert_called_once()
        fake_api.get_hrv_data.assert_called_once_with("2026-08-10")
        assert resultado.fecha == date(2026, 8, 10)
        assert session.query(ReadinessLog).filter_by(user_id=usuario.id).count() == 1

    def test_por_defecto_sincroniza_hoy(self, session, monkeypatch):
        usuario = _usuario_con_garmin(session)
        fake_api = _fake_api()

        import garmin_sync.client as client_module

        monkeypatch.setattr(client_module, "_default_api_factory", lambda: lambda *a, **k: fake_api)

        resultado = sync_today_for_user(session, usuario.id)

        assert resultado.fecha == date.today()
