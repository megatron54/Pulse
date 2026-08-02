"""Tests para repositories.training_block_repository — TDD.

Deriva `planned_session` automáticamente a partir del TrainingBlock
activo + su WeeklySchedule, en vez de recibirlo como parámetro manual
en cada llamada (ver docs/02-roadmap/02-plan-autonomo.md, Fase F).
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from engine.periodization import SessionType
from models.schema import Base, TrainingBlock, UserProfile, WeeklySchedule
from repositories.training_block_repository import get_planned_session_for_date


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


def _crear_bloque_con_schedule(session, user_id, fecha_inicio, fecha_fin, schedule: dict):
    bloque = TrainingBlock(
        user_id=user_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        objetivo_prioritario="strength",
    )
    session.add(bloque)
    session.commit()
    for dia, tipo in schedule.items():
        session.add(
            WeeklySchedule(training_block_id=bloque.id, dia_semana=dia, session_type=tipo)
        )
    session.commit()
    return bloque


class TestGetPlannedSessionForDate:
    def test_devuelve_el_session_type_del_dia_de_la_semana(self, session, usuario):
        # 2026-08-03 es lunes
        _crear_bloque_con_schedule(
            session,
            usuario.id,
            date(2026, 8, 1),
            date(2026, 9, 12),
            {"mon": "strength_heavy", "wed": "endurance_intervals"},
        )
        resultado = get_planned_session_for_date(session, usuario.id, date(2026, 8, 3))
        assert resultado == SessionType.STRENGTH_HEAVY

    def test_devuelve_otro_dia_de_la_misma_semana(self, session, usuario):
        # 2026-08-05 es miércoles
        _crear_bloque_con_schedule(
            session,
            usuario.id,
            date(2026, 8, 1),
            date(2026, 9, 12),
            {"mon": "strength_heavy", "wed": "endurance_intervals"},
        )
        resultado = get_planned_session_for_date(session, usuario.id, date(2026, 8, 5))
        assert resultado == SessionType.ENDURANCE_INTERVALS

    def test_devuelve_none_sin_bloque_activo(self, session, usuario):
        assert get_planned_session_for_date(session, usuario.id, date(2026, 8, 3)) is None

    def test_devuelve_none_fuera_del_rango_de_fechas_del_bloque(self, session, usuario):
        _crear_bloque_con_schedule(
            session,
            usuario.id,
            date(2026, 8, 1),
            date(2026, 8, 10),
            {"mon": "strength_heavy"},
        )
        # 2026-09-07 es lunes, pero fuera del rango del bloque (termina 8/10)
        assert get_planned_session_for_date(session, usuario.id, date(2026, 9, 7)) is None

    def test_devuelve_none_si_el_dia_no_tiene_entrada_en_el_schedule(self, session, usuario):
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"mon": "strength_heavy"}
        )
        # 2026-08-04 es martes, sin entrada en el schedule
        assert get_planned_session_for_date(session, usuario.id, date(2026, 8, 4)) is None

    def test_ignora_bloques_de_otro_usuario(self, session, usuario):
        otro = UserProfile(
            nombre="Otro", altura_cm=170.0, fecha_nacimiento=date(1990, 1, 1), sexo="F"
        )
        session.add(otro)
        session.commit()
        _crear_bloque_con_schedule(
            session, otro.id, date(2026, 8, 1), date(2026, 9, 12), {"mon": "strength_heavy"}
        )
        assert get_planned_session_for_date(session, usuario.id, date(2026, 8, 3)) is None

    def test_borde_exacto_fecha_inicio_del_bloque(self, session, usuario):
        # 2026-08-01 es sábado
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"sat": "endurance_long"}
        )
        resultado = get_planned_session_for_date(session, usuario.id, date(2026, 8, 1))
        assert resultado == SessionType.ENDURANCE_LONG

    def test_borde_exacto_fecha_fin_del_bloque(self, session, usuario):
        # 2026-09-12 es sábado
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"sat": "endurance_long"}
        )
        resultado = get_planned_session_for_date(session, usuario.id, date(2026, 9, 12))
        assert resultado == SessionType.ENDURANCE_LONG

    def test_dia_domingo_se_mapea_correctamente(self, session, usuario):
        # 2026-08-02 es domingo
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"sun": "active_recovery"}
        )
        resultado = get_planned_session_for_date(session, usuario.id, date(2026, 8, 2))
        assert resultado == SessionType.ACTIVE_RECOVERY

    def test_bloques_solapados_lanza_valueerror_explicito(self, session, usuario):
        # Estado de datos corrupto (no debería ocurrir en uso normal, pero
        # debe fallar de forma explícita/auditable, no silenciosa/ambigua,
        # y no debe dejar escapar la excepción cruda de SQLAlchemy).
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"mon": "strength_heavy"}
        )
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"mon": "endurance_long"}
        )
        with pytest.raises(ValueError):
            get_planned_session_for_date(session, usuario.id, date(2026, 8, 3))
