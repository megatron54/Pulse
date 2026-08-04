"""Tests de integración del router de resumen periódico — TDD."""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from models.schema import Base, ReadinessLog


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


class TestGetPeriodicSummary:
    def test_devuelve_el_resumen_sin_fabricar_datos(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(
            f"/users/{usuario['id']}/summary", params={"as_of": "2026-08-20", "days": 7}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dias_con_checkin_readiness"] == 0
        assert body["distribucion_readiness"] == {"green": 0, "yellow": 0, "red": 0}
        assert body["peso_delta_kg"] is None
        assert body["actividades_totales"] == 0

    def test_incluye_la_distribucion_real_de_readiness(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        with Session(engine) as session:
            session.add(
                ReadinessLog(user_id=usuario["id"], fecha=date(2026, 8, 20), resultado="green")
            )
            session.commit()

        resp = c.get(
            f"/users/{usuario['id']}/summary", params={"as_of": "2026-08-20", "days": 7}
        )
        assert resp.json()["distribucion_readiness"]["green"] == 1

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/summary", params={"as_of": "2026-08-20"})
        assert resp.status_code == 404

    def test_dias_por_defecto_es_7(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/summary")
        assert resp.status_code == 200
