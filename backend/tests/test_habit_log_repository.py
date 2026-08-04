"""Tests para repositories.habit_log_repository — TDD."""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, HabitCheckin, HabitLog, UserProfile
from repositories.habit_log_repository import (
    get_dates_with_any_checkin,
    get_dates_with_habit,
    get_dates_without_habit_in_window,
    set_habits_for_date,
)


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


class TestSetHabitsForDate:
    def test_crea_una_fila_por_cada_habito_marcado(self, session, usuario):
        hoy = date(2026, 8, 4)
        set_habits_for_date(session, usuario.id, hoy, ["alcohol", "estres_alto"])
        filas = session.query(HabitLog).filter_by(user_id=usuario.id, fecha=hoy).all()
        assert {f.habito for f in filas} == {"alcohol", "estres_alto"}

    def test_reemplaza_los_habitos_del_dia_si_se_vuelve_a_llamar(self, session, usuario):
        hoy = date(2026, 8, 4)
        set_habits_for_date(session, usuario.id, hoy, ["alcohol"])
        set_habits_for_date(session, usuario.id, hoy, ["siesta"])
        filas = session.query(HabitLog).filter_by(user_id=usuario.id, fecha=hoy).all()
        assert {f.habito for f in filas} == {"siesta"}

    def test_lista_vacia_borra_los_habitos_del_dia(self, session, usuario):
        hoy = date(2026, 8, 4)
        set_habits_for_date(session, usuario.id, hoy, ["alcohol"])
        set_habits_for_date(session, usuario.id, hoy, [])
        assert session.query(HabitLog).filter_by(user_id=usuario.id, fecha=hoy).count() == 0

    def test_no_afecta_los_habitos_de_otros_dias(self, session, usuario):
        set_habits_for_date(session, usuario.id, date(2026, 8, 3), ["alcohol"])
        set_habits_for_date(session, usuario.id, date(2026, 8, 4), ["siesta"])
        assert session.query(HabitLog).filter_by(user_id=usuario.id, fecha=date(2026, 8, 3)).count() == 1

    def test_registra_siempre_un_checkin_aunque_la_lista_este_vacia(self, session, usuario):
        # Hallazgo CRITICAL de code-review: sin esta fila, "hoy no pasó
        # nada" es indistinguible de "nunca hice check-in hoy".
        hoy = date(2026, 8, 4)
        set_habits_for_date(session, usuario.id, hoy, [])
        assert session.query(HabitCheckin).filter_by(user_id=usuario.id, fecha=hoy).count() == 1

    def test_reenviar_el_mismo_dia_no_duplica_la_fila_de_checkin(self, session, usuario):
        hoy = date(2026, 8, 4)
        set_habits_for_date(session, usuario.id, hoy, ["alcohol"])
        set_habits_for_date(session, usuario.id, hoy, ["siesta"])
        assert session.query(HabitCheckin).filter_by(user_id=usuario.id, fecha=hoy).count() == 1

    def test_dedupe_de_habitos_repetidos_en_el_mismo_payload(self, session, usuario):
        hoy = date(2026, 8, 4)
        set_habits_for_date(session, usuario.id, hoy, ["alcohol", "alcohol"])
        assert session.query(HabitLog).filter_by(user_id=usuario.id, fecha=hoy).count() == 1


class TestGetDatesWithHabit:
    def test_devuelve_las_fechas_en_las_que_se_registro_el_habito(self, session, usuario):
        set_habits_for_date(session, usuario.id, date(2026, 8, 1), ["alcohol"])
        set_habits_for_date(session, usuario.id, date(2026, 8, 2), ["siesta"])
        set_habits_for_date(session, usuario.id, date(2026, 8, 3), ["alcohol", "siesta"])

        fechas = get_dates_with_habit(
            session, usuario.id, "alcohol", as_of=date(2026, 8, 10), days=90
        )
        assert fechas == {date(2026, 8, 1), date(2026, 8, 3)}

    def test_respeta_la_ventana_de_dias(self, session, usuario):
        set_habits_for_date(session, usuario.id, date(2026, 1, 1), ["alcohol"])
        fechas = get_dates_with_habit(
            session, usuario.id, "alcohol", as_of=date(2026, 8, 10), days=90
        )
        assert fechas == set()


class TestGetDatesWithAnyCheckin:
    def test_devuelve_los_dias_en_los_que_hubo_checkin_de_habitos(self, session, usuario):
        set_habits_for_date(session, usuario.id, date(2026, 8, 8), ["alcohol"])
        set_habits_for_date(session, usuario.id, date(2026, 8, 9), [])  # "no pasó nada", explícito

        checkins = get_dates_with_any_checkin(
            session, usuario.id, as_of=date(2026, 8, 10), days=5
        )
        assert checkins == {date(2026, 8, 8), date(2026, 8, 9)}


class TestGetDatesWithoutHabitInWindow:
    def test_solo_incluye_dias_con_checkin_explicito_no_todo_el_calendario(self, session, usuario):
        # Hallazgo CRITICAL de code-review: un día en el que el usuario
        # nunca abrió la app NO debe contar como "no tuvo el hábito".
        # Ventana de 5 días: 6,7,8,9,10 de agosto. Solo el 8 y el 9
        # tienen checkin (el 8 con alcohol, el 9 explícitamente vacío);
        # 6, 7 y 10 son días sin ningún dato.
        set_habits_for_date(session, usuario.id, date(2026, 8, 8), ["alcohol"])
        set_habits_for_date(session, usuario.id, date(2026, 8, 9), [])

        sin_habito = get_dates_without_habit_in_window(
            session, usuario.id, "alcohol", as_of=date(2026, 8, 10), days=5
        )
        assert sin_habito == {date(2026, 8, 9)}
