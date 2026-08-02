"""Tests para services.nutrition_service — TDD.

Conecta: UserProfile + BodyMeasurements (repository) -> engine.nutrition
(Capa 1) -> engine.guardrails.should_pause_calorie_deficit (usando
historial de ReadinessLog vía repository) -> AuditLog.

Guardrail 2 (ver 00-research/06-periodizacion-ciencia-deportiva.md):
CUT + RED sostenido >=3 días -> pausar el déficit (usar MAINTENANCE en
su lugar), SIN mutar el UserProfile.fase_peso_actual almacenado - es una
pausa de UN DÍA, no un cambio de fase permanente.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from engine.nutrition import WeightPhase
from models.schema import AuditLog, Base, BodyMeasurements, ReadinessLog, UserProfile
from services.nutrition_service import compute_daily_nutrition_target


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _crear_usuario(session, fase_peso="maintenance"):
    u = UserProfile(
        nombre="Test",
        altura_cm=180.0,
        fecha_nacimiento=date(1996, 8, 2),  # 30 años el 2026-08-02
        sexo="M",
        fase_peso_actual=fase_peso,
    )
    session.add(u)
    session.commit()
    session.add(BodyMeasurements(user_id=u.id, fecha=date(2026, 7, 1), peso_kg=80.0))
    session.commit()
    return u


class TestComputeDailyNutritionTarget:
    def test_calcula_macros_con_el_peso_mas_reciente_y_fase_del_perfil(self, session):
        usuario = _crear_usuario(session, fase_peso="maintenance")
        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=date(2026, 8, 2), factor_actividad=1.55
        )
        assert resultado.macros.kcal_objetivo > 0
        assert resultado.fase_aplicada == WeightPhase.MAINTENANCE
        assert resultado.deficit_pausado_por_guardrail is False

    def test_rechaza_si_no_hay_peso_registrado(self, session):
        usuario = UserProfile(
            nombre="SinPeso", altura_cm=180.0, fecha_nacimiento=date(1996, 8, 2), sexo="M"
        )
        session.add(usuario)
        session.commit()
        with pytest.raises(ValueError):
            compute_daily_nutrition_target(
                session, usuario.id, target_date=date(2026, 8, 2), factor_actividad=1.55
            )

    def test_cut_con_red_sostenido_pausa_el_deficit(self, session):
        usuario = _crear_usuario(session, fase_peso="cut")
        hoy = date(2026, 8, 10)
        for i in range(1, 4):
            session.add(
                ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=i), resultado="red")
            )
        session.commit()

        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=hoy, factor_actividad=1.55
        )
        assert resultado.fase_aplicada == WeightPhase.MAINTENANCE
        assert resultado.deficit_pausado_por_guardrail is True
        # Comparación real: MAINTENANCE debe dar más kcal que CUT habría
        # dado con los mismos peso/TDEE, no solo "kcal > 0".
        kcal_cut_habria_dado = compute_daily_nutrition_target(
            session, usuario.id, target_date=date(2026, 8, 2), factor_actividad=1.55
        ).macros.kcal_objetivo
        assert resultado.macros.kcal_objetivo > kcal_cut_habria_dado

    def test_cut_sin_red_sostenido_mantiene_el_deficit(self, session):
        usuario = _crear_usuario(session, fase_peso="cut")
        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=date(2026, 8, 2), factor_actividad=1.55
        )
        assert resultado.fase_aplicada == WeightPhase.CUT
        assert resultado.deficit_pausado_por_guardrail is False

    def test_no_muta_la_fase_de_peso_almacenada_en_el_perfil(self, session):
        usuario = _crear_usuario(session, fase_peso="cut")
        hoy = date(2026, 8, 10)
        for i in range(1, 4):
            session.add(
                ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=i), resultado="red")
            )
        session.commit()

        compute_daily_nutrition_target(session, usuario.id, target_date=hoy, factor_actividad=1.55)
        session.refresh(usuario)
        assert usuario.fase_peso_actual == "cut"  # la pausa es de UN día, no permanente

    def test_registra_auditoria_de_la_decision(self, session):
        usuario = _crear_usuario(session, fase_peso="maintenance")
        compute_daily_nutrition_target(
            session, usuario.id, target_date=date(2026, 8, 2), factor_actividad=1.55
        )
        auditoria = session.query(AuditLog).filter_by(user_id=usuario.id, modulo="nutrition").one()
        assert "kcal_objetivo" in auditoria.decision_final
