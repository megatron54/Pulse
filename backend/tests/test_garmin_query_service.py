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
from services.garmin_query_service import (
    CategoriaDeporte,
    get_activity_history_for_user,
    get_weekly_volume_for_user,
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


def _actividad(
    activity_id: str,
    tipo: str,
    fecha: date = date(2026, 8, 1),
    duracion_seg: int | None = 1800,
    distancia_m: float | None = 5000.0,
) -> dict:
    return {
        "activity_id": activity_id,
        "fecha": fecha,
        "tipo": tipo,
        "duracion_seg": duracion_seg,
        "distancia_m": distancia_m,
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


class TestGetWeeklyVolumeForUser:
    """Épica 10 del plan de expansión (02-roadmap/03-vision-produccion.md):
    gráficas de volumen por deporte - agrega distancia/duración/número
    de sesiones por semana (lunes-domingo), reutilizando el historial
    de actividades ya filtrado por categoría (Épica D)."""

    def test_agrupa_dos_actividades_de_la_misma_semana(self, session, usuario):
        # Lunes 2026-08-03 y jueves 2026-08-06 caen en la misma semana ISO.
        save_activity_if_new(
            session,
            usuario.id,
            _actividad("1", "running", fecha=date(2026, 8, 3), distancia_m=5000.0, duracion_seg=1800),
        )
        save_activity_if_new(
            session,
            usuario.id,
            _actividad("2", "running", fecha=date(2026, 8, 6), distancia_m=3000.0, duracion_seg=1200),
        )

        semanas = get_weekly_volume_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING, weeks=4
        )

        semana_con_datos = [s for s in semanas if s.num_sesiones > 0]
        assert len(semana_con_datos) == 1
        assert semana_con_datos[0].semana_inicio == date(2026, 8, 3)
        assert semana_con_datos[0].distancia_total_m == 8000.0
        assert semana_con_datos[0].duracion_total_seg == 3000
        assert semana_con_datos[0].num_sesiones == 2

    def test_separa_actividades_de_semanas_distintas(self, session, usuario):
        save_activity_if_new(
            session, usuario.id, _actividad("1", "running", fecha=date(2026, 7, 27))
        )
        save_activity_if_new(
            session, usuario.id, _actividad("2", "running", fecha=date(2026, 8, 3))
        )

        semanas = get_weekly_volume_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING, weeks=4
        )

        semanas_con_datos = {s.semana_inicio: s.num_sesiones for s in semanas if s.num_sesiones > 0}
        assert semanas_con_datos == {date(2026, 7, 27): 1, date(2026, 8, 3): 1}

    def test_incluye_semanas_vacias_en_la_ventana_con_ceros(self, session, usuario):
        # "unknown is not zero" en su forma de serie temporal: una
        # semana sin actividades debe aparecer con 0 sesiones, no
        # simplemente ausente de la lista - para que un gráfico de
        # tendencia no interprete el hueco como "sin datos" y una
        # semana real con 0 como si fueran lo mismo que fuera de rango.
        semanas = get_weekly_volume_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING, weeks=4
        )
        assert len(semanas) == 4
        assert all(s.num_sesiones == 0 for s in semanas)
        assert all(s.distancia_total_m is None for s in semanas)

    def test_ignora_actividades_de_otra_categoria(self, session, usuario):
        save_activity_if_new(
            session, usuario.id, _actividad("1", "road_biking", fecha=date(2026, 8, 3))
        )

        semanas = get_weekly_volume_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING, weeks=4
        )
        assert all(s.num_sesiones == 0 for s in semanas)

    def test_semanas_ordenadas_cronologicamente_ascendente(self, session, usuario):
        semanas = get_weekly_volume_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING, weeks=4
        )
        inicios = [s.semana_inicio for s in semanas]
        assert inicios == sorted(inicios)

    def test_actividad_sin_distancia_no_rompe_la_suma_pero_cuenta_la_sesion(self, session, usuario):
        # Gimnasio no trae distancia útil (ver punto 2 del doc vivo) -
        # una sesión sin distancia debe seguir contando para
        # num_sesiones/duracion, sin que None rompa la suma.
        save_activity_if_new(
            session,
            usuario.id,
            _actividad(
                "1", "strength_training", fecha=date(2026, 8, 3), distancia_m=None, duracion_seg=2400
            ),
        )

        semanas = get_weekly_volume_for_user(
            session, usuario.id, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.GIMNASIO, weeks=4
        )

        semana_con_datos = [s for s in semanas if s.num_sesiones > 0][0]
        assert semana_con_datos.num_sesiones == 1
        assert semana_con_datos.duracion_total_seg == 2400
        assert semana_con_datos.distancia_total_m is None

    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        from services.errors import EntityNotFoundError

        with pytest.raises(EntityNotFoundError):
            get_weekly_volume_for_user(
                session, 99999, as_of=date(2026, 8, 10), categoria=CategoriaDeporte.RUNNING, weeks=4
            )
