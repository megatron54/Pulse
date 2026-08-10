"""Tests de integración de POST /users/{id}/feelfit-connect - TDD.
Petición explícita del usuario: conectar báscula Feelfit (confirmado
Android, sin vía oficial viable) - login se aísla mediante monkeypatch
de `connect_feelfit_account`, sin red real."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import api.routers.feelfit as feelfit_router
from api.dependencies import get_db
from api.main import app
from feelfit_client.client import FeelfitAuthError
from models.schema import Base
from services.errors import EntityNotFoundError


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
        },
    )
    return resp.json()["id"]


class TestFeelfitConnect:
    def test_conecta_y_devuelve_el_numero_de_mediciones_importadas(self, client, monkeypatch):
        test_client, _ = client
        user_id = _crear_usuario(test_client)

        monkeypatch.setattr(
            feelfit_router, "connect_feelfit_account", lambda *a, **k: 12
        )

        resp = test_client.post(
            f"/users/{user_id}/feelfit-connect",
            json={"email": "a@b.com", "password": "secreto"},
        )

        assert resp.status_code == 201
        assert resp.json() == {"mediciones_importadas": 12}

    def test_usuario_inexistente_devuelve_404(self, client, monkeypatch):
        test_client, _ = client

        def _lanza_not_found(*a, **k):
            raise EntityNotFoundError("no existe")

        monkeypatch.setattr(feelfit_router, "connect_feelfit_account", _lanza_not_found)

        resp = test_client.post(
            "/users/99999/feelfit-connect",
            json={"email": "a@b.com", "password": "secreto"},
        )

        assert resp.status_code == 404

    def test_credenciales_invalidas_devuelve_401(self, client, monkeypatch):
        test_client, _ = client
        user_id = _crear_usuario(test_client)

        def _lanza_auth_error(*a, **k):
            raise FeelfitAuthError("credenciales inválidas")

        monkeypatch.setattr(feelfit_router, "connect_feelfit_account", _lanza_auth_error)

        resp = test_client.post(
            f"/users/{user_id}/feelfit-connect",
            json={"email": "a@b.com", "password": "mala"},
        )

        assert resp.status_code == 401
