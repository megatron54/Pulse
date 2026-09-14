"""Tests de integración del router de Garmin (solo lectura del
historial de actividades ya ingeridas - la sincronización real corre
en el scheduler nocturno, ver services.scheduler_service) — TDD."""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from models.schema import (
    Base,
    GarminActivity,
    GarminDailyMetrics,
    GarminExerciseSet,
    GarminIntradayMetric,
    ReadinessLog,
)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), engine
    app.dependency_overrides.clear()


def _crear_usuario(client):
    resp = client.post(
        "/users",
        json={
            "nombre": "Test",
            "altura_cm": 180,
            "fecha_nacimiento": "1995-01-01",
            "sexo": "M",
            "fase_peso_actual": "maintenance",
        },
    )
    return resp.json()


class TestGetActivityHistory:
    def test_devuelve_las_actividades_ingeridas_del_usuario(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                GarminActivity(
                    user_id=usuario["id"],
                    activity_id="1",
                    fecha=date(2026, 8, 1),
                    tipo="running",
                    duracion_seg=1800,
                    distancia_m=5000.0,
                    hr_avg=150,
                    hr_max=172,
                    training_effect=3.2,
                )
            )
            session.commit()

        resp = c.get(f"/users/{usuario['id']}/garmin/activities")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["tipo"] == "running"
        assert body[0]["distancia_m"] == 5000.0

    def test_usuario_sin_actividades_devuelve_lista_vacia(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/activities")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/garmin/activities")
        assert resp.status_code == 404

    def test_filtra_por_categoria_de_deporte(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                GarminActivity(
                    user_id=usuario["id"],
                    activity_id="1",
                    fecha=date(2026, 8, 1),
                    tipo="running",
                    duracion_seg=1800,
                    distancia_m=5000.0,
                    hr_avg=150,
                    hr_max=172,
                    training_effect=3.2,
                )
            )
            session.add(
                GarminActivity(
                    user_id=usuario["id"],
                    activity_id="2",
                    fecha=date(2026, 8, 2),
                    tipo="road_biking",
                    duracion_seg=3600,
                    distancia_m=20000.0,
                    hr_avg=140,
                    hr_max=160,
                    training_effect=2.8,
                )
            )
            session.commit()

        resp = c.get(f"/users/{usuario['id']}/garmin/activities?categoria=ciclismo")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["tipo"] == "road_biking"

    def test_categoria_invalida_da_422(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/activities?categoria=natacion")
        assert resp.status_code == 422


class TestGetHealthHistory:
    """Épica C del plan de expansión (02-roadmap/03-vision-produccion.md)."""

    def test_devuelve_el_historial_de_metricas_diarias_del_usuario(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                GarminDailyMetrics(
                    user_id=usuario["id"],
                    fecha=date(2026, 8, 6),
                    hrv_value=49.0,
                    hrv_status="NONE",
                    body_battery_am=77,
                    training_readiness="high",
                    sleep_score=82,
                    stress_avg=10,
                    resting_hr=54,
                    vo2max=None,
                )
            )
            session.commit()

        resp = c.get(f"/users/{usuario['id']}/garmin/health-history")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["hrv_value"] == 49.0
        assert body[0]["hrv_status"] == "NONE"
        assert body[0]["stress_avg"] == 10
        assert body[0]["resting_hr"] == 54
        assert body[0]["vo2max"] is None

    def test_usuario_sin_historial_devuelve_lista_vacia(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/health-history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/garmin/health-history")
        assert resp.status_code == 404

    def test_respeta_el_parametro_days(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                GarminDailyMetrics(user_id=usuario["id"], fecha=date(2026, 1, 1), hrv_value=40.0)
            )
            session.add(
                GarminDailyMetrics(user_id=usuario["id"], fecha=date(2026, 8, 6), hrv_value=50.0)
            )
            session.commit()

        resp = c.get(f"/users/{usuario['id']}/garmin/health-history?days=7&as_of=2026-08-06")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["hrv_value"] == 50.0


class TestGetHealthNarrative:
    """Épica H del plan de expansión (02-roadmap/03-vision-produccion.md)."""

    def test_sin_readiness_calculado_devuelve_text_y_source_none(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/health-narrative?fecha=2026-08-06")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"text": None, "source": None}

    def test_con_readiness_calculado_devuelve_una_narrativa_real(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                ReadinessLog(user_id=usuario["id"], fecha=date(2026, 8, 6), resultado="green")
            )
            session.add(
                GarminDailyMetrics(
                    user_id=usuario["id"],
                    fecha=date(2026, 8, 6),
                    hrv_value=60.0,
                    sleep_score=82,
                )
            )
            session.commit()

        resp = c.get(f"/users/{usuario['id']}/garmin/health-narrative?fecha=2026-08-06")
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] is not None
        assert body["source"] == "template"
        assert "60" in body["text"]

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/garmin/health-narrative")
        assert resp.status_code == 404


class TestGetWeeklyVolume:
    """Épica 10 del plan de expansión (02-roadmap/03-vision-produccion.md)."""

    def test_devuelve_el_volumen_semanal_agregado(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                GarminActivity(
                    user_id=usuario["id"],
                    activity_id="1",
                    fecha=date(2026, 8, 3),
                    tipo="running",
                    duracion_seg=1800,
                    distancia_m=5000.0,
                    hr_avg=150,
                    hr_max=172,
                    training_effect=3.2,
                )
            )
            session.commit()

        resp = c.get(
            f"/users/{usuario['id']}/garmin/activities/volume?categoria=running&weeks=4&as_of=2026-08-10"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 4
        semana_con_datos = [s for s in body if s["num_sesiones"] > 0]
        assert len(semana_con_datos) == 1
        assert semana_con_datos[0]["distancia_total_m"] == 5000.0

    def test_categoria_es_obligatoria(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/activities/volume?weeks=4")
        assert resp.status_code == 422

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/garmin/activities/volume?categoria=running")
        assert resp.status_code == 404


class TestGetSportNarrative:
    """Épica G2 del plan de desarrollo (04-plan-desarrollo-siguiente-fase.md,
    Fase 1)."""

    def test_sin_actividades_devuelve_text_y_source_none(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(
            f"/users/{usuario['id']}/garmin/activities/narrative?categoria=running&as_of=2026-09-09"
        )
        assert resp.status_code == 200
        assert resp.json() == {"text": None, "source": None}

    def test_con_actividades_devuelve_una_narrativa_real(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                GarminActivity(
                    user_id=usuario["id"],
                    activity_id="1",
                    fecha=date(2026, 9, 9),
                    tipo="running",
                    duracion_seg=1800,
                    distancia_m=5000.0,
                )
            )
            session.commit()

        resp = c.get(
            f"/users/{usuario['id']}/garmin/activities/narrative?categoria=running&as_of=2026-09-09"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] is not None
        assert body["source"] == "template"

    def test_categoria_es_obligatoria(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/activities/narrative")
        assert resp.status_code == 422

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/garmin/activities/narrative?categoria=running")
        assert resp.status_code == 404


class TestGetExerciseSets:
    """Épica G del plan de desarrollo (Fase 1, punto 2)."""

    def test_devuelve_las_series_de_una_actividad_de_gimnasio(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                GarminExerciseSet(
                    user_id=usuario["id"],
                    activity_id="1",
                    numero_serie=0,
                    tipo_serie="ACTIVE",
                    repeticiones=10,
                    peso_kg=60.0,
                    categoria_ejercicio="BENCH_PRESS",
                    duracion_seg=45,
                )
            )
            session.commit()

        resp = c.get(f"/users/{usuario['id']}/garmin/activities/1/exercise-sets")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["categoria_ejercicio"] == "BENCH_PRESS"
        assert body[0]["peso_kg"] == 60.0

    def test_actividad_sin_series_devuelve_lista_vacia(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/activities/999/exercise-sets")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/garmin/activities/1/exercise-sets")
        assert resp.status_code == 404


class TestGetIntradayHistory:
    """Petición explícita del usuario: "el ritmo cardiaco, body
    battery, etc son valores que cambian cada minuto, quiero todo ese
    histórico"."""

    def test_devuelve_la_serie_del_dia_pedido(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add_all(
                [
                    GarminIntradayMetric(
                        user_id=usuario["id"],
                        metrica="heart_rate",
                        fecha=date(2026, 8, 9),
                        timestamp_utc=datetime(2026, 8, 9, 6, 0, 0),
                        valor=60.0,
                    ),
                    GarminIntradayMetric(
                        user_id=usuario["id"],
                        metrica="heart_rate",
                        fecha=date(2026, 8, 9),
                        timestamp_utc=datetime(2026, 8, 9, 6, 2, 0),
                        valor=62.0,
                    ),
                ]
            )
            session.commit()

        resp = c.get(
            f"/users/{usuario['id']}/garmin/intraday?metrica=heart_rate&fecha=2026-08-09"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["valor"] == 60.0

    def test_dia_sin_datos_devuelve_lista_vacia(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(
            f"/users/{usuario['id']}/garmin/intraday?metrica=heart_rate&fecha=2026-08-09"
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_metrica_invalida_da_422(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/garmin/intraday?metrica=no-existe")
        assert resp.status_code == 422

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/garmin/intraday?metrica=heart_rate")
        assert resp.status_code == 404


class TestSyncNow:
    """Botón "actualizar ahora" del frontend (hallazgo de code-review:
    antes no existía ningún endpoint de sync manual) - ver
    services.garmin_manual_sync_service."""

    def test_sincroniza_hoy_por_defecto_y_devuelve_el_resultado(self, client):
        c, _ = client
        usuario = _crear_usuario(c)

        from unittest.mock import patch

        from services.garmin_manual_sync_service import ManualSyncResult

        resultado = ManualSyncResult(
            fecha=date(2026, 8, 10), puntos_intradia_nuevos=42, actividades_nuevas=1
        )
        with patch(
            "api.routers.garmin.sync_today_for_user", return_value=resultado
        ) as mock_sync:
            resp = c.post(f"/users/{usuario['id']}/garmin/sync")

        assert resp.status_code == 200
        assert resp.json() == {
            "fecha": "2026-08-10",
            "puntos_intradia_nuevos": 42,
            "actividades_nuevas": 1,
        }
        assert mock_sync.call_args.kwargs["target_date"] is None

    def test_usuario_sin_garmin_conectado_da_404(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.post(f"/users/{usuario['id']}/garmin/sync")
        assert resp.status_code == 404

    def test_rate_limit_devuelve_429(self, client):
        c, _ = client
        usuario = _crear_usuario(c)

        from unittest.mock import patch

        from garmin_sync.client import GarminRateLimitedError

        with patch(
            "api.routers.garmin.sync_today_for_user",
            side_effect=GarminRateLimitedError("429 too many requests"),
        ):
            resp = c.post(f"/users/{usuario['id']}/garmin/sync")

        assert resp.status_code == 429

    def test_login_invalido_devuelve_401(self, client):
        c, _ = client
        usuario = _crear_usuario(c)

        from unittest.mock import patch

        from garmin_sync.client import GarminAuthError

        with patch(
            "api.routers.garmin.sync_today_for_user",
            side_effect=GarminAuthError("401 no autorizado"),
        ):
            resp = c.post(f"/users/{usuario['id']}/garmin/sync")

        assert resp.status_code == 401
