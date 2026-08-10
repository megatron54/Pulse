"""Tests para las funciones de historial usadas por los dashboards de
tendencia (Fase I del plan autónomo)."""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, BodyMeasurements, ReadinessLog, UserProfile
from repositories.body_measurements_repository import get_weight_history
from repositories.readiness_log_repository import get_readiness_history


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


class TestGetWeightHistory:
    def test_devuelve_en_orden_cronologico_ascendente(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add_all(
            [
                BodyMeasurements(user_id=usuario.id, fecha=hoy - timedelta(days=2), peso_kg=81.0),
                BodyMeasurements(user_id=usuario.id, fecha=hoy - timedelta(days=5), peso_kg=82.0),
                BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=80.0),
            ]
        )
        session.commit()
        historial = get_weight_history(session, usuario.id, as_of=hoy, days=30)
        assert [m.peso_kg for m in historial] == [82.0, 81.0, 80.0]

    def test_excluye_datos_fuera_de_la_ventana(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add_all(
            [
                BodyMeasurements(user_id=usuario.id, fecha=hoy - timedelta(days=100), peso_kg=90.0),
                BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=80.0),
            ]
        )
        session.commit()
        historial = get_weight_history(session, usuario.id, as_of=hoy, days=30)
        assert len(historial) == 1
        assert historial[0].peso_kg == 80.0

    def test_lista_vacia_sin_historial(self, session, usuario):
        assert get_weight_history(session, usuario.id, as_of=date(2026, 8, 10), days=30) == []

    def test_ignora_mediciones_de_otro_usuario(self, session, usuario):
        otro = UserProfile(
            nombre="Otro", altura_cm=170.0, fecha_nacimiento=date(1990, 1, 1), sexo="F"
        )
        session.add(otro)
        session.commit()
        session.add(BodyMeasurements(user_id=otro.id, fecha=date(2026, 8, 10), peso_kg=60.0))
        session.commit()
        assert get_weight_history(session, usuario.id, as_of=date(2026, 8, 10), days=30) == []

    def test_desempata_por_id_entre_filas_del_mismo_dia(self, session, usuario):
        # Varias re-sincronizaciones el mismo día: el orden debe reflejar
        # el orden de inserción (id monótono), no quedar indefinido.
        hoy = date(2026, 8, 10)
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=81.0))
        session.commit()
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=80.5))
        session.commit()
        historial = get_weight_history(session, usuario.id, as_of=hoy, days=30)
        assert [m.peso_kg for m in historial] == [81.0, 80.5]

    def test_borde_de_la_ventana_exacto_29_dias_dentro_30_fuera(self, session, usuario):
        # Off-by-one corregido (hallazgo #10 del doc vivo,
        # 02-roadmap/03-vision-produccion.md): con days=30, la ventana
        # es [as_of-29, as_of] - 30 días EXACTOS, no 31. La fila de
        # hace 30 días queda fuera; la de hace 29 días queda dentro.
        hoy = date(2026, 8, 10)
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy - timedelta(days=29), peso_kg=85.0))
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy - timedelta(days=30), peso_kg=999.0))
        session.commit()
        historial = get_weight_history(session, usuario.id, as_of=hoy, days=30)
        assert len(historial) == 1
        assert historial[0].peso_kg == 85.0


class TestGetReadinessHistory:
    def test_devuelve_en_orden_cronologico_ascendente(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add_all(
            [
                ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=2), resultado="yellow"),
                ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=5), resultado="green"),
                ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="red"),
            ]
        )
        session.commit()
        historial = get_readiness_history(session, usuario.id, as_of=hoy, days=30)
        assert [r.resultado for r in historial] == ["green", "yellow", "red"]

    def test_incluye_el_dia_de_hoy_a_diferencia_de_get_recent_readiness_levels(
        self, session, usuario
    ):
        # A diferencia de get_recent_readiness_levels (usado por
        # guardrails, que excluye hoy por diseño), el historial para
        # dashboards SÍ debe incluir el dato de hoy si existe.
        hoy = date(2026, 8, 10)
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="green"))
        session.commit()
        historial = get_readiness_history(session, usuario.id, as_of=hoy, days=30)
        assert len(historial) == 1

    def test_lista_vacia_sin_historial(self, session, usuario):
        assert get_readiness_history(session, usuario.id, as_of=date(2026, 8, 10), days=30) == []

    def test_borde_de_la_ventana_exacto_29_dias_dentro_30_fuera(self, session, usuario):
        # Off-by-one corregido (hallazgo #10 del doc vivo): con days=30,
        # la ventana es [as_of-29, as_of] - 30 días exactos.
        hoy = date(2026, 8, 10)
        session.add(
            ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=29), resultado="green")
        )
        session.add(
            ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=30), resultado="red")
        )
        session.commit()
        historial = get_readiness_history(session, usuario.id, as_of=hoy, days=30)
        assert [r.resultado for r in historial] == ["green"]
