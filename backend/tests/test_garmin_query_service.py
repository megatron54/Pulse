"""Tests dedicados del servicio de consulta Garmin - en particular del
mapeo CategoriaDeporte -> typeKey reales de Garmin (Épica D/G del plan
de expansión, 02-roadmap/03-vision-produccion.md), para que una edición
accidental de la lista no pase desapercibida (antes solo se cubría
indirectamente vía test_garmin_router.py)."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminActivity, UserProfile
from repositories.garmin_repository import save_activity_if_new
from services.garmin_query_service import CategoriaDeporte, get_activity_history_for_user


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


def _actividad(activity_id: str, tipo: str) -> dict:
    return {
        "activity_id": activity_id,
        "fecha": date(2026, 8, 1),
        "tipo": tipo,
        "duracion_seg": 1800,
        "distancia_m": 5000.0,
        "hr_avg": 150,
        "hr_max": 172,
        "training_effect": 3.2,
        "raw_json": {},
    }


class TestCategoriaDeporteAgrupaVariantesDeTypeKey:
    """Cada categoría debe agrupar TODAS las variantes documentadas de
    typeKey - no solo el valor "canónico" (ej. "running")."""

    @pytest.mark.parametrize(
        "tipo_garmin",
        ["running", "trail_running", "treadmill_running", "track_running", "street_running"],
    )
    def test_running_agrupa_sus_variantes(self, session, usuario, tipo_garmin):
        save_activity_if_new(session, usuario.id, _actividad("1", tipo_garmin))
        historial = get_activity_history_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING
        )
        assert len(historial) == 1

    @pytest.mark.parametrize(
        "tipo_garmin",
        ["cycling", "road_biking", "mountain_biking", "indoor_cycling", "gravel_cycling", "virtual_ride"],
    )
    def test_ciclismo_agrupa_sus_variantes(self, session, usuario, tipo_garmin):
        save_activity_if_new(session, usuario.id, _actividad("1", tipo_garmin))
        historial = get_activity_history_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.CICLISMO
        )
        assert len(historial) == 1

    @pytest.mark.parametrize(
        "tipo_garmin", ["strength_training", "indoor_cardio", "fitness_equipment"]
    )
    def test_gimnasio_agrupa_sus_variantes(self, session, usuario, tipo_garmin):
        save_activity_if_new(session, usuario.id, _actividad("1", tipo_garmin))
        historial = get_activity_history_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.GIMNASIO
        )
        assert len(historial) == 1

    def test_una_categoria_nunca_incluye_actividades_de_otra(self, session, usuario):
        save_activity_if_new(session, usuario.id, _actividad("1", "running"))
        save_activity_if_new(session, usuario.id, _actividad("2", "road_biking"))
        save_activity_if_new(session, usuario.id, _actividad("3", "strength_training"))

        running = get_activity_history_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING
        )
        assert [a.activity_id for a in running] == ["1"]

    def test_sin_categoria_devuelve_todas_las_actividades(self, session, usuario):
        save_activity_if_new(session, usuario.id, _actividad("1", "running"))
        save_activity_if_new(session, usuario.id, _actividad("2", "road_biking"))

        todas = get_activity_history_for_user(session, usuario.id, as_of=date(2026, 8, 10))
        assert len(todas) == 2
