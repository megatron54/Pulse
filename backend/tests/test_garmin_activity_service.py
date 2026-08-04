"""Tests para services.garmin_activity_service — TDD."""
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminActivity, UserProfile
from services.garmin_activity_service import sync_activities


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


class TestSyncActivities:
    def test_ingiere_actividades_nuevas_y_reporta_el_conteo(self, session, usuario):
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {
                "activityId": 1,
                "startTimeLocal": "2026-08-01 07:00:00",
                "activityType": {"typeKey": "running"},
                "duration": 1800.0,
            },
            {
                "activityId": 2,
                "startTimeLocal": "2026-08-02 07:00:00",
                "activityType": {"typeKey": "cycling"},
                "duration": 3600.0,
            },
        ]

        resultado = sync_activities(
            session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4)
        )

        assert resultado.ingresadas == 2
        assert resultado.omitidas == 0
        assert session.query(GarminActivity).filter_by(user_id=usuario.id).count() == 2
        client.get_activities_raw.assert_called_once_with("2026-08-01", "2026-08-04")

    def test_reprocesar_el_mismo_rango_no_duplica_y_lo_reporta_como_omitido(
        self, session, usuario
    ):
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {
                "activityId": 1,
                "startTimeLocal": "2026-08-01 07:00:00",
                "activityType": {"typeKey": "running"},
                "duration": 1800.0,
            }
        ]

        sync_activities(session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4))
        resultado = sync_activities(
            session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4)
        )

        assert resultado.ingresadas == 0
        assert resultado.omitidas == 1
        assert session.query(GarminActivity).filter_by(user_id=usuario.id).count() == 1

    def test_una_actividad_invalida_no_tumba_al_resto_del_lote(self, session, usuario):
        # Aislamiento por actividad, mismo principio que
        # scheduler_service aplica por usuario y garmin_sync.client
        # aplica por campo de recuperación.
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {"startTimeLocal": "2026-08-01 07:00:00"},  # sin activityId: inválida
            {
                "activityId": 2,
                "startTimeLocal": "2026-08-02 07:00:00",
                "activityType": {"typeKey": "cycling"},
            },
        ]

        resultado = sync_activities(
            session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4)
        )

        assert resultado.ingresadas == 1
        assert resultado.invalidas == 1
        assert session.query(GarminActivity).filter_by(user_id=usuario.id).count() == 1
