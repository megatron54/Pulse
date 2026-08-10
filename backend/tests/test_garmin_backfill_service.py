"""Backfill histórico tras conectar Garmin por primera vez (petición
explícita del usuario: "debería extraerse todo el histórico de Garmin,
no solo lo de los últimos 5 min"). TDD - ver
services.garmin_backfill_service."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminActivity, ReadinessLog, UserProfile
from services.garmin_backfill_service import backfill_full_history


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def usuario(session):
    u = UserProfile(nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M")
    session.add(u)
    session.commit()
    return u


class TestBackfillFullHistory:
    def test_ingiere_actividades_del_rango_completo_en_una_sola_llamada(self, session, usuario):
        # Las actividades SÍ soportan pedir un rango amplio en una sola
        # llamada (a diferencia de la recuperación diaria) - no hay
        # motivo para trocear esa llamada día a día.
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {
                "activityId": 1,
                "startTimeLocal": "2024-01-15 07:00:00",
                "activityType": {"typeKey": "running"},
                "duration": 1800.0,
            }
        ]
        client.get_daily_recovery_raw.return_value = {
            "hrv_today": None,
            "hrv_status": None,
            "training_readiness": None,
            "body_battery_am": None,
            "sleep_score": None,
            "stress_avg": None,
            "resting_hr": None,
            "vo2max": None,
            "raw_json": {},
        }

        resultado = backfill_full_history(
            session,
            user_id=usuario.id,
            garmin_client=client,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
        )

        client.get_activities_raw.assert_called_once_with("2024-01-01", "2024-01-03")
        assert session.query(GarminActivity).count() == 1
        assert resultado.actividades_ingresadas == 1

    def test_recorre_dia_a_dia_para_recovery_y_aisla_fallos_individuales(self, session, usuario):
        client = MagicMock()
        client.get_activities_raw.return_value = []

        payload_ok = {
            "hrv_today": 65.0,
            "hrv_status": "BALANCED",
            "training_readiness": "high",
            "body_battery_am": 80,
            "sleep_score": 85,
            "stress_avg": 20,
            "resting_hr": 50,
            "vo2max": None,
            "raw_json": {},
        }

        def _recovery_side_effect(fecha_str):
            if fecha_str == "2024-01-02":
                raise Exception("fallo puntual simulado de Garmin")
            return payload_ok

        client.get_daily_recovery_raw.side_effect = _recovery_side_effect

        resultado = backfill_full_history(
            session,
            user_id=usuario.id,
            garmin_client=client,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
        )

        # 2 días exitosos (01 y 03), 1 fallido (02) - el fallo puntual
        # NO detiene el resto del backfill (mismo principio de
        # aislamiento que services.scheduler_service).
        assert resultado.dias_recovery_exitosos == 2
        assert resultado.dias_recovery_fallidos == 1
        assert session.query(ReadinessLog).count() == 2

    def test_un_dia_exitoso_persiste_de_verdad_pese_a_un_fallo_posterior(self, session, usuario):
        # Hallazgo de code-review (MEDIO): sin un commit por día
        # exitoso, el rollback() de un día fallido POSTERIOR revertiría
        # también los días anteriores todavía no commiteados en la
        # misma transacción - el contador mentiría respecto a lo
        # realmente persistido. Aquí el día 1 tiene éxito y el día 2
        # falla; se verifica releyendo la BD (no solo el contador) que
        # el ReadinessLog del día 1 sigue ahí.
        client = MagicMock()
        client.get_activities_raw.return_value = []
        payload_ok = {
            "hrv_today": 65.0,
            "hrv_status": "BALANCED",
            "training_readiness": "high",
            "body_battery_am": 80,
            "sleep_score": 85,
            "stress_avg": 20,
            "resting_hr": 50,
            "vo2max": None,
            "raw_json": {},
        }

        def _recovery_side_effect(fecha_str):
            if fecha_str == "2024-01-02":
                raise Exception("fallo puntual simulado de Garmin")
            return payload_ok

        client.get_daily_recovery_raw.side_effect = _recovery_side_effect

        backfill_full_history(
            session,
            user_id=usuario.id,
            garmin_client=client,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )

        logs_persistidos = session.query(ReadinessLog).filter_by(user_id=usuario.id).all()
        assert len(logs_persistidos) == 1
        assert logs_persistidos[0].fecha == date(2024, 1, 1)

    def test_rango_vacio_de_datos_no_rompe_el_backfill_y_lo_reporta_honestamente(self, session, usuario):
        # "unknown is not zero": sin ningún campo crítico ese día
        # (cuenta recién emparejada, Garmin aún sin consolidar), el día
        # se cuenta como fallido - nunca se inventa un ReadinessLog.
        client = MagicMock()
        client.get_activities_raw.return_value = []
        client.get_daily_recovery_raw.return_value = {
            "hrv_today": None,
            "hrv_status": None,
            "training_readiness": None,
            "body_battery_am": None,
            "sleep_score": None,
            "stress_avg": None,
            "resting_hr": None,
            "vo2max": None,
            "raw_json": {},
        }

        resultado = backfill_full_history(
            session,
            user_id=usuario.id,
            garmin_client=client,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
        )

        assert resultado.actividades_ingresadas == 0
        assert resultado.dias_recovery_exitosos == 0
        assert resultado.dias_recovery_fallidos == 1

    def test_fallo_de_actividades_no_impide_el_backfill_de_recovery(self, session, usuario):
        # Aislamiento entre las dos preocupaciones (actividades vs.
        # recovery), igual que ya hacen las dos funciones separadas de
        # services.scheduler_service.
        client = MagicMock()
        client.get_activities_raw.side_effect = Exception("fallo de actividades")
        client.get_daily_recovery_raw.return_value = {
            "hrv_today": 65.0,
            "hrv_status": None,
            "training_readiness": None,
            "body_battery_am": 80,
            "sleep_score": 85,
            "stress_avg": None,
            "resting_hr": None,
            "vo2max": None,
            "raw_json": {},
        }

        resultado = backfill_full_history(
            session,
            user_id=usuario.id,
            garmin_client=client,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
        )

        assert resultado.actividades_fallo is True
        assert resultado.dias_recovery_exitosos == 1

