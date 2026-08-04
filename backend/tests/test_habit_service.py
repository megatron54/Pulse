"""Tests para services.habit_service — TDD."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, HabitLog, UserProfile
from services.errors import EntityNotFoundError
from services.habit_service import set_habits


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


class TestSetHabits:
    def test_guarda_los_habitos_si_el_usuario_existe(self, session, usuario):
        set_habits(session, usuario.id, date(2026, 8, 4), ["alcohol"])
        filas = session.query(HabitLog).filter_by(user_id=usuario.id).all()
        assert {f.habito for f in filas} == {"alcohol"}

    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        with pytest.raises(EntityNotFoundError):
            set_habits(session, 99999, date(2026, 8, 4), ["alcohol"])
