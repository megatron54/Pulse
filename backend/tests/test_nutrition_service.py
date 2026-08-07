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
from models.schema import AuditLog, Base, BodyMeasurements, GarminDailyMetrics, ReadinessLog, UserProfile
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

    def test_cut_con_sleep_score_bajo_sostenido_pausa_el_deficit(self, session):
        # Épica I del plan de expansión: extensión conservadora del
        # guardrail existente usando sleep_score crudo (umbral <60,
        # 3 noches consecutivas, confirmado explícitamente por el
        # usuario tras revisar 00-research/08-nutricion-recovery-ciencia.md).
        usuario = _crear_usuario(session, fase_peso="cut")
        hoy = date(2026, 8, 10)
        for i in range(0, 3):
            session.add(
                GarminDailyMetrics(
                    user_id=usuario.id, fecha=hoy - timedelta(days=i), sleep_score=50
                )
            )
        session.commit()

        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=hoy, factor_actividad=1.55
        )
        assert resultado.fase_aplicada == WeightPhase.MAINTENANCE
        assert resultado.deficit_pausado_por_guardrail is True

    def test_cut_con_sleep_score_bajo_solo_dos_noches_no_pausa(self, session):
        usuario = _crear_usuario(session, fase_peso="cut")
        hoy = date(2026, 8, 10)
        for i in range(0, 2):
            session.add(
                GarminDailyMetrics(
                    user_id=usuario.id, fecha=hoy - timedelta(days=i), sleep_score=50
                )
            )
        session.commit()

        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=hoy, factor_actividad=1.55
        )
        assert resultado.fase_aplicada == WeightPhase.CUT
        assert resultado.deficit_pausado_por_guardrail is False

    def test_dias_sin_sleep_score_sincronizado_no_disparan_la_pausa(self, session):
        # "unknown is not zero": sin GarminDailyMetrics para esos días,
        # nunca se debe pausar el déficit por una ausencia de dato.
        usuario = _crear_usuario(session, fase_peso="cut")
        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=date(2026, 8, 10), factor_actividad=1.55
        )
        assert resultado.deficit_pausado_por_guardrail is False

    def test_dia_sincronizado_sin_sleep_score_calculado_no_dispara_la_pausa(self, session):
        # Distinto del caso anterior: aquí SÍ hay fila de
        # GarminDailyMetrics para los 3 días, pero uno de ellos no trae
        # sleep_score (None real en la fila, no ausencia de fila) - el
        # guardrail debe seguir sin pausar (racha rota, no 2 malas + 1
        # ausente contando como mala).
        usuario = _crear_usuario(session, fase_peso="cut")
        hoy = date(2026, 8, 10)
        session.add(GarminDailyMetrics(user_id=usuario.id, fecha=hoy, sleep_score=50))
        session.add(
            GarminDailyMetrics(user_id=usuario.id, fecha=hoy - timedelta(days=1), sleep_score=None)
        )
        session.add(
            GarminDailyMetrics(user_id=usuario.id, fecha=hoy - timedelta(days=2), sleep_score=50)
        )
        session.commit()

        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=hoy, factor_actividad=1.55
        )
        assert resultado.deficit_pausado_por_guardrail is False

    def test_readiness_bueno_no_impide_que_el_sueno_pausado_dispare_la_pausa(self, session):
        # Ejercita de verdad la rama `else` de compute_daily_nutrition_target
        # (readiness presente pero NO dispara la guardrail, distinto de
        # "sin ningún ReadinessLog") - antes solo se probaba el caso sin
        # historial de readiness en absoluto.
        usuario = _crear_usuario(session, fase_peso="cut")
        hoy = date(2026, 8, 10)
        for i in range(1, 4):
            session.add(
                ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=i), resultado="green")
            )
        for i in range(0, 3):
            session.add(
                GarminDailyMetrics(
                    user_id=usuario.id, fecha=hoy - timedelta(days=i), sleep_score=50
                )
            )
        session.commit()

        resultado = compute_daily_nutrition_target(
            session, usuario.id, target_date=hoy, factor_actividad=1.55
        )
        assert resultado.fase_aplicada == WeightPhase.MAINTENANCE
        assert resultado.deficit_pausado_por_guardrail is True

        auditoria = (
            session.query(AuditLog)
            .filter_by(user_id=usuario.id, modulo="nutrition")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert auditoria.regla_disparada == "should_pause_calorie_deficit_for_poor_sleep"

    def test_readiness_red_sostenido_tiene_prioridad_y_queda_registrado_en_auditoria(self, session):
        usuario = _crear_usuario(session, fase_peso="cut")
        hoy = date(2026, 8, 10)
        for i in range(1, 4):
            session.add(
                ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=i), resultado="red")
            )
        session.commit()

        compute_daily_nutrition_target(session, usuario.id, target_date=hoy, factor_actividad=1.55)

        auditoria = (
            session.query(AuditLog)
            .filter_by(user_id=usuario.id, modulo="nutrition")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert auditoria.regla_disparada == "should_pause_calorie_deficit"
