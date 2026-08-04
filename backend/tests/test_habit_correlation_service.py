"""Tests para services.habit_correlation_service — TDD.

Fase MUST-HAVE #3 del backlog priorizado (auditoría de competidores,
02-roadmap/03-vision-produccion.md): diario de hábitos correlacionado
con recovery, análogo al "Journal" de WHOOP. Se correlaciona el hábito
del día N con el readiness del día N+1 (un hábito de hoy - alcohol,
dormir poco - afecta la recuperación de MAÑANA, no la de hoy mismo).

Umbral de confianza tomado de la investigación real sobre WHOOP Journal
citada en 02-roadmap/03-vision-produccion.md: "5+5 muestras" mínimo.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, ReadinessLog, UserProfile
from repositories.habit_log_repository import set_habits_for_date
from services.errors import EntityNotFoundError
from services.habit_correlation_service import compute_habit_correlation


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


def _sembrar_readiness(session, user_id, fecha, resultado):
    session.add(ReadinessLog(user_id=user_id, fecha=fecha, resultado=resultado))
    session.commit()


class TestComputeHabitCorrelation:
    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        with pytest.raises(EntityNotFoundError):
            compute_habit_correlation(
                session, user_id=99999, habito="alcohol", as_of=date(2026, 8, 10)
            )

    def test_sin_muestras_suficientes_marca_datos_insuficientes(self, session, usuario):
        resultado = compute_habit_correlation(
            session, usuario.id, habito="alcohol", as_of=date(2026, 8, 10)
        )
        assert resultado.datos_suficientes is False
        assert resultado.pct_red_con_habito is None

    def test_calcula_pct_red_del_dia_siguiente_para_cada_grupo(self, session, usuario):
        hoy = date(2026, 8, 20)
        # 6 días CON alcohol, el día siguiente a cada uno es RED en 4 de 6.
        dias_con_habito = [hoy - timedelta(days=d) for d in range(1, 13, 2)]  # 6 días
        for i, dia in enumerate(dias_con_habito):
            set_habits_for_date(session, usuario.id, dia, ["alcohol"])
            resultado_siguiente = "red" if i < 4 else "green"
            _sembrar_readiness(session, usuario.id, dia + timedelta(days=1), resultado_siguiente)

        # 6 días SIN alcohol (pero CON checkin explícito - condición
        # necesaria tras el fix del hallazgo CRITICAL: un día sin
        # checkin no cuenta como grupo de control), el día siguiente es
        # RED solo en 1 de 6.
        dias_sin_habito = [hoy - timedelta(days=d) for d in range(2, 14, 2)]  # 6 días
        for i, dia in enumerate(dias_sin_habito):
            set_habits_for_date(session, usuario.id, dia, [])
            resultado_siguiente = "red" if i < 1 else "green"
            _sembrar_readiness(session, usuario.id, dia + timedelta(days=1), resultado_siguiente)

        resultado = compute_habit_correlation(
            session, usuario.id, habito="alcohol", as_of=hoy, window_days=90
        )

        assert resultado.datos_suficientes is True
        assert resultado.pct_red_con_habito == pytest.approx(4 / 6)
        assert resultado.pct_red_sin_habito == pytest.approx(1 / 6)
        assert resultado.dias_con_habito_con_dato == 6
        assert resultado.dias_sin_habito_con_dato == 6

    def test_ignora_dias_sin_readiness_calculado_al_dia_siguiente(self, session, usuario):
        # "unknown is not zero": un día con hábito pero SIN readiness
        # calculado el día después no debe contar ni como red ni como
        # no-red - simplemente se excluye de la muestra.
        hoy = date(2026, 8, 20)
        dia_con_dato = hoy - timedelta(days=1)
        dia_sin_dato = hoy - timedelta(days=3)
        set_habits_for_date(session, usuario.id, dia_con_dato, ["alcohol"])
        set_habits_for_date(session, usuario.id, dia_sin_dato, ["alcohol"])
        _sembrar_readiness(session, usuario.id, dia_con_dato + timedelta(days=1), "red")
        # dia_sin_dato + 1 día: sin ReadinessLog en absoluto.

        resultado = compute_habit_correlation(
            session, usuario.id, habito="alcohol", as_of=hoy, window_days=90
        )
        assert resultado.dias_con_habito_con_dato == 1

    def test_un_dia_sin_checkin_nunca_cuenta_como_grupo_de_control(self, session, usuario):
        # Regresión directa del hallazgo CRITICAL de code-review: un día
        # en el que el usuario nunca hizo check-in de hábitos (pero sí
        # tiene readiness calculado al día siguiente, por ejemplo porque
        # hace el check-in de recovery a diario y el de hábitos no)
        # NO debe entrar en pct_red_sin_habito.
        hoy = date(2026, 8, 20)
        dia_sin_checkin = hoy - timedelta(days=5)
        # Nunca se llama a set_habits_for_date para este día - por lo
        # tanto no hay fila en HabitCheckin.
        _sembrar_readiness(session, usuario.id, dia_sin_checkin + timedelta(days=1), "red")

        resultado = compute_habit_correlation(
            session, usuario.id, habito="alcohol", as_of=hoy, window_days=90
        )
        assert resultado.dias_sin_habito_con_dato == 0
