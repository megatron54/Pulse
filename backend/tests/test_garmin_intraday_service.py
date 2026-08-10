from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminIntradayMetric, UserProfile
from services.garmin_intraday_service import sync_intraday_metrics


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


class TestSyncIntradayMetrics:
    def test_persiste_las_tres_metricas_y_reporta_el_conteo(self, session, usuario):
        client = MagicMock()
        client.get_intraday_series_raw.return_value = {
            "heart_rate": [(1786226400000, 107.0), (1786226520000, 103.0)],
            "body_battery": [(1786226400000, 50.0)],
            "stress": [],
        }

        resultado = sync_intraday_metrics(session, usuario.id, client, date(2026, 8, 8))

        client.get_intraday_series_raw.assert_called_once_with("2026-08-08")
        assert resultado.puntos_nuevos_por_metrica == {
            "heart_rate": 2,
            "body_battery": 1,
            "stress": 0,
        }
        assert resultado.total_puntos_nuevos == 3
        assert session.query(GarminIntradayMetric).count() == 3

    def test_resincronizar_no_duplica_puntos(self, session, usuario):
        client = MagicMock()
        client.get_intraday_series_raw.return_value = {
            "heart_rate": [(1786226400000, 107.0)],
            "body_battery": [],
            "stress": [],
        }
        sync_intraday_metrics(session, usuario.id, client, date(2026, 8, 8))

        resultado_2 = sync_intraday_metrics(session, usuario.id, client, date(2026, 8, 8))

        assert resultado_2.total_puntos_nuevos == 0
        assert session.query(GarminIntradayMetric).count() == 1
