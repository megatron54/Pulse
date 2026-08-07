"""Tests de integración del router de Garmin (solo lectura del
historial de actividades ya ingeridas - la sincronización real corre
en el scheduler nocturno, ver services.scheduler_service) — TDD."""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from models.schema import Base, GarminActivity, GarminDailyMetrics, ReadinessLog


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
