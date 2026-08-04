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
from models.schema import Base, GarminActivity


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
