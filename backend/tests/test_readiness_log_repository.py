"""Tests para repositories.readiness_log_repository — TDD."""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from engine.periodization import ReadinessLevel
from models.schema import Base, ReadinessLog, UserProfile
from repositories.readiness_log_repository import get_recent_readiness_levels


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


class TestGetRecentReadinessLevels:
    def test_devuelve_los_ultimos_n_en_orden_cronologico(self, session, usuario):
        hoy = date(2026, 8, 10)
        for i, resultado in enumerate(["green", "yellow", "red"]):
            session.add(
                ReadinessLog(
                    user_id=usuario.id,
                    fecha=hoy - timedelta(days=3 - i),
                    resultado=resultado,
                )
            )
        session.commit()

        niveles = get_recent_readiness_levels(session, usuario.id, hoy, n=3)
        assert niveles == [
            ReadinessLevel.GREEN,
            ReadinessLevel.YELLOW,
            ReadinessLevel.RED,
        ]

    def test_devuelve_lista_vacia_sin_historial(self, session, usuario):
        assert get_recent_readiness_levels(session, usuario.id, date(2026, 8, 10), n=3) == []

    def test_no_incluye_el_dia_de_hoy(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="red"))
        session.commit()
        assert get_recent_readiness_levels(session, usuario.id, hoy, n=3) == []
