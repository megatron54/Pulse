"""TDD - repositories.garmin_intraday_repository: ingesta idempotente
de la serie minuto a minuto (petición explícita del usuario: histórico
completo de HR/body battery/estrés, no solo la media del día)."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminIntradayMetric, UserProfile
from repositories.garmin_intraday_repository import (
    get_intraday_history,
    save_intraday_points,
)

_FECHA = date(2026, 8, 8)


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


class TestSaveIntradayPoints:
    def test_inserta_los_puntos_nuevos(self, session, usuario):
        puntos = [(1786226400000, 107.0), (1786226520000, 103.0)]

        insertados = save_intraday_points(session, usuario.id, "heart_rate", _FECHA, puntos)

        assert insertados == 2
        assert session.query(GarminIntradayMetric).count() == 2

    def test_resincronizar_el_mismo_dia_no_duplica_puntos(self, session, usuario):
        puntos = [(1786226400000, 107.0), (1786226520000, 103.0)]
        save_intraday_points(session, usuario.id, "heart_rate", _FECHA, puntos)

        # Resincroniza el mismo rango + 1 punto nuevo real.
        puntos_2 = puntos + [(1786226640000, 101.0)]
        insertados_2 = save_intraday_points(session, usuario.id, "heart_rate", _FECHA, puntos_2)

        assert insertados_2 == 1  # solo el punto nuevo
        assert session.query(GarminIntradayMetric).count() == 3

    def test_lista_vacia_no_falla(self, session, usuario):
        assert save_intraday_points(session, usuario.id, "heart_rate", _FECHA, []) == 0

    def test_usa_la_fecha_pedida_explicitamente_no_la_derivada_del_timestamp_utc(
        self, session, usuario
    ):
        # Hallazgo de code-review: antes se derivaba `fecha` del
        # timestamp UTC de cada punto, lo que desplazaba los puntos de
        # madrugada (23:00-01:00 hora local) al día UTC equivocado.
        # Ahora `fecha` es un parámetro explícito - el mismo día
        # calendario que se le pidió a Garmin - así que un punto cuyo
        # timestamp UTC cae en OTRO día sigue quedando bajo la fecha
        # pedida.
        timestamp_ms_de_otro_dia_utc = 1786312800000  # +1 día respecto a _FECHA
        save_intraday_points(
            session, usuario.id, "heart_rate", _FECHA, [(timestamp_ms_de_otro_dia_utc, 90.0)]
        )
        fila = session.query(GarminIntradayMetric).one()
        assert fila.fecha == _FECHA

    def test_persiste_el_timestamp_utc_exacto_del_punto(self, session, usuario):
        save_intraday_points(session, usuario.id, "heart_rate", _FECHA, [(1786226400000, 107.0)])
        fila = session.query(GarminIntradayMetric).one()
        esperado = datetime.fromtimestamp(1786226400000 / 1000, tz=timezone.utc).replace(tzinfo=None)
        assert fila.timestamp_utc == esperado


class TestGetIntradayHistory:
    def test_devuelve_los_puntos_del_dia_pedido_ordenados(self, session, usuario):
        save_intraday_points(
            session,
            usuario.id,
            "heart_rate",
            _FECHA,
            [(1786226520000, 103.0), (1786226400000, 107.0)],  # desordenados a propósito
        )

        historia = get_intraday_history(session, usuario.id, "heart_rate", _FECHA)

        assert [p.valor for p in historia] == [107.0, 103.0]

    def test_no_devuelve_puntos_de_otra_metrica_ni_otro_dia(self, session, usuario):
        save_intraday_points(session, usuario.id, "heart_rate", _FECHA, [(1786226400000, 107.0)])
        save_intraday_points(session, usuario.id, "body_battery", _FECHA, [(1786226400000, 50.0)])
        save_intraday_points(
            session, usuario.id, "heart_rate", date(2026, 8, 9), [(1786312800000, 90.0)]
        )

        historia = get_intraday_history(session, usuario.id, "heart_rate", _FECHA)

        assert len(historia) == 1
        assert historia[0].valor == 107.0

    def test_dia_sin_datos_devuelve_lista_vacia(self, session, usuario):
        assert get_intraday_history(session, usuario.id, "heart_rate", _FECHA) == []
