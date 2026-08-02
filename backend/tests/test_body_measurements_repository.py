"""Tests para repositories.body_measurements_repository — TDD."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, BodyMeasurements, UserProfile
from repositories.body_measurements_repository import get_latest_weight_kg


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


class TestGetLatestWeightKg:
    def test_devuelve_el_peso_mas_reciente(self, session, usuario):
        session.add_all(
            [
                BodyMeasurements(user_id=usuario.id, fecha=date(2026, 8, 1), peso_kg=81.0),
                BodyMeasurements(user_id=usuario.id, fecha=date(2026, 8, 5), peso_kg=80.0),
            ]
        )
        session.commit()
        assert get_latest_weight_kg(session, usuario.id) == 80.0

    def test_devuelve_none_sin_mediciones(self, session, usuario):
        assert get_latest_weight_kg(session, usuario.id) is None

    def test_desempata_por_created_at_si_misma_fecha(self, session, usuario):
        fecha = date(2026, 8, 1)
        session.add(BodyMeasurements(user_id=usuario.id, fecha=fecha, peso_kg=81.0))
        session.commit()
        session.add(BodyMeasurements(user_id=usuario.id, fecha=fecha, peso_kg=79.5))
        session.commit()
        assert get_latest_weight_kg(session, usuario.id) == 79.5
