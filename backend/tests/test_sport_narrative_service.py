"""Tests para coach.sport_narrative_service — TDD.

Épica G2 del plan de desarrollo (02-roadmap/04-plan-desarrollo-siguiente-fase.md,
Fase 1, punto 1): slot de coach por deporte. La "decisión" que se
explica aquí no viene de la Capa 1 (no existe un semáforo de carga por
deporte todavía) sino de una comparación aritmética simple y auditable
sobre `WeeklyVolume` ya agregado por `garmin_query_service` - sigue el
mismo contrato que `health_narrative_service`: nunca inventa una
tendencia sin datos suficientes ("unknown is not zero").
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from coach.sport_narrative_service import generate_sport_narrative_for_user
from models.schema import Base, GarminActivity, UserProfile
from services.errors import EntityNotFoundError
from services.garmin_query_service import CategoriaDeporte


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


def _lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _add_actividad(session, user_id, fecha, activity_id, tipo="running", distancia_m=5000.0):
    session.add(
        GarminActivity(
            user_id=user_id,
            activity_id=activity_id,
            fecha=fecha,
            tipo=tipo,
            distancia_m=distancia_m,
            duracion_seg=1800,
        )
    )


class TestGenerateSportNarrativeForUser:
    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        with pytest.raises(EntityNotFoundError):
            generate_sport_narrative_for_user(
                session,
                user_id=99999,
                categoria=CategoriaDeporte.RUNNING,
                as_of=date(2026, 9, 7),
                gemini_client=None,
            )

    def test_sin_ninguna_actividad_devuelve_none(self, session, usuario):
        resultado = generate_sport_narrative_for_user(
            session,
            user_id=usuario.id,
            categoria=CategoriaDeporte.RUNNING,
            as_of=date(2026, 9, 7),
            gemini_client=None,
        )
        assert resultado is None

    def test_carga_en_aumento_frente_a_las_semanas_previas(self, session, usuario):
        as_of = date(2026, 9, 9)  # miércoles, misma semana ISO que el lunes de abajo
        lunes_actual = _lunes(as_of)
        # 4 semanas previas con 1 sesión cada una, semana actual con 3.
        for i in range(1, 5):
            semana = lunes_actual - timedelta(weeks=i)
            _add_actividad(session, usuario.id, semana, activity_id=f"prev-{i}")
        for i in range(3):
            _add_actividad(
                session, usuario.id, lunes_actual + timedelta(days=i), activity_id=f"cur-{i}"
            )
        session.commit()

        resultado = generate_sport_narrative_for_user(
            session,
            user_id=usuario.id,
            categoria=CategoriaDeporte.RUNNING,
            as_of=as_of,
            gemini_client=None,
        )

        assert resultado is not None
        assert resultado.source == "template"
        assert "aumento" in resultado.text.lower()
        assert "3" in resultado.text

    def test_carga_estable(self, session, usuario):
        as_of = date(2026, 9, 7)
        lunes_actual = _lunes(as_of)
        for i in range(1, 5):
            semana = lunes_actual - timedelta(weeks=i)
            _add_actividad(session, usuario.id, semana, activity_id=f"prev-{i}")
        _add_actividad(session, usuario.id, lunes_actual, activity_id="cur-0")
        session.commit()

        resultado = generate_sport_narrative_for_user(
            session,
            user_id=usuario.id,
            categoria=CategoriaDeporte.RUNNING,
            as_of=as_of,
            gemini_client=None,
        )

        assert resultado is not None
        assert "estable" in resultado.text.lower()

    def test_categoria_distinta_no_mezcla_datos(self, session, usuario):
        as_of = date(2026, 9, 7)
        lunes_actual = _lunes(as_of)
        # Solo actividades de ciclismo - running debe seguir sin datos.
        _add_actividad(
            session, usuario.id, lunes_actual, activity_id="c-0", tipo="cycling",
            distancia_m=20000.0,
        )
        session.commit()

        resultado = generate_sport_narrative_for_user(
            session,
            user_id=usuario.id,
            categoria=CategoriaDeporte.RUNNING,
            as_of=as_of,
            gemini_client=None,
        )
        assert resultado is None
