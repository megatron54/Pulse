"""TDD - services.nutrition_plan_recommendation_service: recomienda
(nunca aplica automáticamente) la siguiente fase - decisión explícita
del usuario: "recomienda, tú confirmas"."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminDailyMetrics, ReadinessLog, UserProfile
from services.nutrition_plan_recommendation_service import recommend_next_phase
from services.nutrition_plan_service import create_nutrition_plan


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


class TestRecommendNextPhase:
    def test_sin_ningun_plan_recomienda_mantenimiento(self, session, usuario):
        rec = recommend_next_phase(session, usuario.id, as_of=date(2026, 8, 10))

        assert rec.fase_recomendada == "maintenance"
        assert rec.accion == "nuevo_plan_sugerido"
        assert "sin plan activo" in rec.motivo.lower()

    def test_plan_activo_sano_y_vigente_no_sugiere_cambios(self, session, usuario):
        create_nutrition_plan(
            session, user_id=usuario.id, fase="cut", semanas_duracion=8, fecha_inicio=date(2026, 8, 1)
        )

        rec = recommend_next_phase(session, usuario.id, as_of=date(2026, 8, 10))

        assert rec.accion == "sin_cambios"
        assert rec.fase_recomendada == "cut"

    def test_plan_de_cut_expirado_recomienda_mantenimiento_como_pausa_obligatoria(
        self, session, usuario
    ):
        create_nutrition_plan(
            session, user_id=usuario.id, fase="cut", semanas_duracion=8, fecha_inicio=date(2026, 6, 1)
        )

        rec = recommend_next_phase(session, usuario.id, as_of=date(2026, 8, 10))

        assert rec.accion == "nuevo_plan_sugerido"
        assert rec.fase_recomendada == "maintenance"
        assert "8 semanas" in rec.motivo or "cut" in rec.motivo.lower()
        assert rec.semanas_sugeridas is not None and rec.semanas_sugeridas >= 2

    def test_plan_de_mantenimiento_expirado_no_es_urgente(self, session, usuario):
        create_nutrition_plan(
            session,
            user_id=usuario.id,
            fase="maintenance",
            semanas_duracion=4,
            fecha_inicio=date(2026, 6, 1),
        )

        rec = recommend_next_phase(session, usuario.id, as_of=date(2026, 8, 10))

        assert rec.accion == "sin_cambios"
        assert rec.fase_recomendada == "maintenance"

    def test_cut_con_readiness_red_sostenido_recomienda_pausar_pese_a_que_el_plan_siga_vigente(
        self, session, usuario
    ):
        create_nutrition_plan(
            session, user_id=usuario.id, fase="cut", semanas_duracion=8, fecha_inicio=date(2026, 8, 1)
        )
        for i in range(3):
            session.add(
                ReadinessLog(
                    user_id=usuario.id,
                    fecha=date(2026, 8, 7 + i),
                    resultado="red",
                    joint_pain_flag=False,
                )
            )
        session.commit()

        rec = recommend_next_phase(session, usuario.id, as_of=date(2026, 8, 10))

        assert rec.accion == "nuevo_plan_sugerido"
        assert rec.fase_recomendada == "maintenance"
        assert "recovery" in rec.motivo.lower() or "readiness" in rec.motivo.lower()

    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        from services.errors import EntityNotFoundError

        with pytest.raises(EntityNotFoundError):
            recommend_next_phase(session, 99999, as_of=date(2026, 8, 10))
