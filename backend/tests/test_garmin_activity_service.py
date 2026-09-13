"""Tests para services.garmin_activity_service — TDD."""
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminActivity, GarminExerciseSet, UserProfile
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


class TestSyncExerciseSetsDeGimnasio:
    """Épica G del plan de desarrollo (Fase 1, punto 2): una actividad
    NUEVA de gimnasio dispara la ingesta de sus series; solo se pide
    detalle para actividades nuevas (nunca releer detalle de
    actividades ya vistas, ver nota de riesgo de bloqueo de cuenta)."""

    def test_actividad_nueva_de_gimnasio_ingiere_sus_series(self, session, usuario):
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {
                "activityId": 1,
                "startTimeLocal": "2026-08-01 07:00:00",
                "activityType": {"typeKey": "strength_training"},
            }
        ]
        client.get_exercise_sets_raw.return_value = [
            {"setType": "ACTIVE", "repetitionCount": 10, "weight": 60000, "category": "BENCH_PRESS"},
            {"setType": "REST", "duration": 60},
        ]

        sync_activities(session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4))

        client.get_exercise_sets_raw.assert_called_once_with("1")
        series = session.query(GarminExerciseSet).filter_by(user_id=usuario.id).order_by(
            GarminExerciseSet.numero_serie
        ).all()
        assert len(series) == 2
        assert series[0].categoria_ejercicio == "BENCH_PRESS"
        assert series[0].peso_kg == 60.0
        assert series[1].tipo_serie == "REST"

    def test_actividad_de_running_no_pide_series(self, session, usuario):
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {
                "activityId": 1,
                "startTimeLocal": "2026-08-01 07:00:00",
                "activityType": {"typeKey": "running"},
            }
        ]

        sync_activities(session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4))

        client.get_exercise_sets_raw.assert_not_called()

    def test_actividad_de_gimnasio_sin_series_no_persiste_nada(self, session, usuario):
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {
                "activityId": 1,
                "startTimeLocal": "2026-08-01 07:00:00",
                "activityType": {"typeKey": "strength_training"},
            }
        ]
        client.get_exercise_sets_raw.return_value = []

        sync_activities(session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4))

        assert session.query(GarminExerciseSet).count() == 0

    def test_reprocesar_el_mismo_rango_no_vuelve_a_pedir_series_de_una_actividad_ya_vista(
        self, session, usuario
    ):
        client = MagicMock()
        client.get_activities_raw.return_value = [
            {
                "activityId": 1,
                "startTimeLocal": "2026-08-01 07:00:00",
                "activityType": {"typeKey": "strength_training"},
            }
        ]
        client.get_exercise_sets_raw.return_value = [{"setType": "ACTIVE", "repetitionCount": 5}]

        sync_activities(session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4))
        sync_activities(session, usuario.id, client, date(2026, 8, 1), date(2026, 8, 4))

        client.get_exercise_sets_raw.assert_called_once_with("1")
