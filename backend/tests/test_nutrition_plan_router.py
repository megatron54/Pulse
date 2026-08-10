"""Tests de integración de los endpoints de plan nutricional - TDD.
Petición explícita del usuario: "planes de deficit, superhabit y
mantenimiento dedicados, con duración determinada, como tu
nutricionista personal", decisión: "recomienda, tú confirmas"."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from models.schema import Base


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


class TestCrearPlanNutricional:
    def test_crea_el_plan(self, client):
        c, _ = client
        usuario = _crear_usuario(c)

        resp = c.post(
            f"/users/{usuario['id']}/nutrition/plans",
            json={"fase": "cut", "semanas_duracion": 8, "fecha_inicio": "2026-08-10"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["fase"] == "cut"
        assert body["activo"] is True

    def test_semanas_duracion_invalida_da_422(self, client):
        c, _ = client
        usuario = _crear_usuario(c)

        resp = c.post(
            f"/users/{usuario['id']}/nutrition/plans",
            json={"fase": "cut", "semanas_duracion": 0, "fecha_inicio": "2026-08-10"},
        )
        assert resp.status_code == 422

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.post(
            "/users/99999/nutrition/plans",
            json={"fase": "cut", "semanas_duracion": 8, "fecha_inicio": "2026-08-10"},
        )
        assert resp.status_code == 404


class TestGetPlanNutricionalActivo:
    def test_sin_plan_devuelve_null(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(f"/users/{usuario['id']}/nutrition/plans/active")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_con_plan_devuelve_fecha_fin_y_dias_restantes(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        c.post(
            f"/users/{usuario['id']}/nutrition/plans",
            json={"fase": "cut", "semanas_duracion": 8, "fecha_inicio": "2026-08-10"},
        )

        resp = c.get(f"/users/{usuario['id']}/nutrition/plans/active?as_of=2026-08-20")

        assert resp.status_code == 200
        body = resp.json()
        assert body["fecha_fin"] == "2026-10-05"
        assert body["dias_restantes"] > 0
        assert body["expirado"] is False


class TestGetRecomendacionFase:
    def test_sin_plan_recomienda_mantenimiento(self, client):
        c, _ = client
        usuario = _crear_usuario(c)

        resp = c.get(f"/users/{usuario['id']}/nutrition/plans/recommendation")

        assert resp.status_code == 200
        body = resp.json()
        assert body["fase_recomendada"] == "maintenance"
        assert body["accion"] == "nuevo_plan_sugerido"

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get("/users/99999/nutrition/plans/recommendation")
        assert resp.status_code == 404
