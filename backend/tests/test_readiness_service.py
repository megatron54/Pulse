"""Tests para services.readiness_service — TDD.

Orquesta el flujo completo del día: sync Garmin -> persistencia ->
cálculo de baseline/tendencia -> engine.periodization.compute_readiness
-> persistencia del resultado + auditoría. Es la primera pieza que
conecta las Capas 1 (motor de reglas), 2 (datos) e ingesta (Garmin) de
la arquitectura.

Sin red real: se reutiliza el patrón de api_factory inyectable de
garmin_sync.client, ya validado en test_garmin_client.py.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from engine.periodization import ReadinessLevel, RecoveryContext
from garmin_sync.client import GarminClient
from garmin_sync.mapper import InsufficientDataError
from models.schema import AuditLog, Base, GarminDailyMetrics, ReadinessLog, UserProfile
from services.readiness_service import record_manual_readiness, sync_and_compute_readiness


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


def _garmin_client_logueado(hrv=65.0, readiness="high", body_battery=80, sleep=85):
    fake_api = MagicMock()
    fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": hrv}}
    fake_api.get_training_readiness.return_value = [{"level": readiness.upper()}]
    fake_api.get_body_battery.return_value = [{"charged": body_battery, "drained": 10}]
    fake_api.get_sleep_data.return_value = {
        "dailySleepDTO": {"sleepScores": {"overall": {"value": sleep}}}
    }
    client = GarminClient(
        token_store_dir="C:/fake/.garminconnect",
        api_factory=lambda *a, **k: fake_api,
    )
    client.login()
    return client


class TestSyncAndComputeReadiness:
    def test_flujo_completo_sin_historial_previo_da_green_con_datos_perfectos(
        self, session, usuario
    ):
        client = _garmin_client_logueado()
        resultado = sync_and_compute_readiness(
            session=session,
            user_id=usuario.id,
            garmin_client=client,
            target_date=date(2026, 8, 2),
            acwr=1.0,
            joint_pain_flag=False,
        )
        assert resultado.resultado == ReadinessLevel.GREEN.value

    def test_persiste_garmin_daily_metrics(self, session, usuario):
        client = _garmin_client_logueado()
        sync_and_compute_readiness(
            session=session,
            user_id=usuario.id,
            garmin_client=client,
            target_date=date(2026, 8, 2),
            acwr=1.0,
            joint_pain_flag=False,
        )
        filas = session.query(GarminDailyMetrics).filter_by(user_id=usuario.id).all()
        assert len(filas) == 1
        assert filas[0].hrv_value == 65.0

    def test_persiste_readiness_log_con_los_campos_del_contexto(self, session, usuario):
        client = _garmin_client_logueado()
        resultado = sync_and_compute_readiness(
            session=session,
            user_id=usuario.id,
            garmin_client=client,
            target_date=date(2026, 8, 2),
            acwr=1.0,
            joint_pain_flag=False,
        )
        fila = session.query(ReadinessLog).filter_by(user_id=usuario.id).one()
        assert fila.id == resultado.id
        assert fila.acwr == 1.0
        assert fila.training_readiness == "high"

    def test_registra_auditoria_de_la_decision(self, session, usuario):
        client = _garmin_client_logueado()
        sync_and_compute_readiness(
            session=session,
            user_id=usuario.id,
            garmin_client=client,
            target_date=date(2026, 8, 2),
            acwr=1.0,
            joint_pain_flag=False,
        )
        auditoria = session.query(AuditLog).filter_by(user_id=usuario.id).one()
        assert auditoria.modulo == "periodization"
        assert auditoria.output == ReadinessLevel.GREEN.value

    def test_dolor_articular_fuerza_red_incluso_con_datos_perfectos(self, session, usuario):
        client = _garmin_client_logueado()
        resultado = sync_and_compute_readiness(
            session=session,
            user_id=usuario.id,
            garmin_client=client,
            target_date=date(2026, 8, 2),
            acwr=1.0,
            joint_pain_flag=True,
        )
        assert resultado.resultado == ReadinessLevel.RED.value

    def test_sin_historial_de_baseline_usa_hrv_de_hoy_como_neutral(self, session, usuario):
        # Fallback documentado: sin 28 días de historial, no hay señal de
        # desviación posible -> se asume neutral (delta=0), no se inventa
        # un "mal día" ni se bloquea el uso de la app desde el día 1.
        client = _garmin_client_logueado(hrv=65.0)
        resultado = sync_and_compute_readiness(
            session=session,
            user_id=usuario.id,
            garmin_client=client,
            target_date=date(2026, 8, 2),
            acwr=1.0,
            joint_pain_flag=False,
        )
        assert resultado.hrv_delta_pct == pytest.approx(0.0, abs=0.001)

    def test_usa_baseline_real_cuando_hay_historial_suficiente(self, session, usuario):
        hoy = date(2026, 8, 29)
        for i in range(1, 29):
            session.add(
                GarminDailyMetrics(user_id=usuario.id, fecha=hoy - timedelta(days=i), hrv_value=65.0)
            )
        session.commit()

        client = _garmin_client_logueado(hrv=50.0)  # -23% vs baseline 65 -> RED
        resultado = sync_and_compute_readiness(
            session=session,
            user_id=usuario.id,
            garmin_client=client,
            target_date=hoy,
            acwr=1.0,
            joint_pain_flag=False,
        )
        assert resultado.resultado == ReadinessLevel.RED.value

    def test_datos_garmin_insuficientes_propaga_insufficient_data_error(self, session, usuario):
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {}  # sin lastNightAvg -> None
        fake_api.get_training_readiness.return_value = [{"level": "HIGH"}]
        fake_api.get_body_battery.return_value = [{"charged": 80}]
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 85}}}}
        client = GarminClient(
            token_store_dir="C:/fake", api_factory=lambda *a, **k: fake_api
        )
        client.login()

        with pytest.raises(InsufficientDataError):
            sync_and_compute_readiness(
                session=session,
                user_id=usuario.id,
                garmin_client=client,
                target_date=date(2026, 8, 2),
                acwr=1.0,
                joint_pain_flag=False,
            )
        # Aun así, la sincronización cruda debe haberse persistido (no se
        # pierde el dato de Garmin solo porque falte HRV ese día).
        filas = session.query(GarminDailyMetrics).filter_by(user_id=usuario.id).all()
        assert len(filas) == 1


class TestRecordManualReadiness:
    """Check-in manual: mismo motor de reglas y persistencia que
    sync_and_compute_readiness, pero sin depender de Garmin - útil
    mientras la sincronización real siga bloqueada (Fase H)."""

    def test_persiste_readiness_log_igual_que_la_via_garmin(self, session, usuario):
        ctx = RecoveryContext(
            hrv_today=65.0,
            hrv_baseline_28d=65.0,
            hrv_trend_7d=0.0,
            body_battery_am=80,
            training_readiness="high",
            sleep_score=85,
            acwr=1.0,
            joint_pain_flag=False,
        )
        log = record_manual_readiness(session, usuario.id, date(2026, 8, 2), ctx)
        assert log.resultado == ReadinessLevel.GREEN.value

        fila = session.query(ReadinessLog).filter_by(user_id=usuario.id).one()
        assert fila.id == log.id

    def test_no_toca_garmin_daily_metrics(self, session, usuario):
        # A diferencia de la vía Garmin, el check-in manual no sincroniza
        # ni persiste nada en GarminDailyMetrics.
        ctx = RecoveryContext(
            hrv_today=65.0,
            hrv_baseline_28d=65.0,
            hrv_trend_7d=0.0,
            body_battery_am=80,
            training_readiness="high",
            sleep_score=85,
            acwr=1.0,
            joint_pain_flag=False,
        )
        record_manual_readiness(session, usuario.id, date(2026, 8, 2), ctx)
        assert session.query(GarminDailyMetrics).filter_by(user_id=usuario.id).count() == 0

    def test_registra_auditoria(self, session, usuario):
        ctx = RecoveryContext(
            hrv_today=50.0,
            hrv_baseline_28d=65.0,
            hrv_trend_7d=0.0,
            body_battery_am=80,
            training_readiness="high",
            sleep_score=85,
            acwr=1.0,
            joint_pain_flag=False,
        )
        log = record_manual_readiness(session, usuario.id, date(2026, 8, 2), ctx)
        assert log.resultado == ReadinessLevel.RED.value
        auditoria = session.query(AuditLog).filter_by(user_id=usuario.id).one()
        assert auditoria.output == ReadinessLevel.RED.value
