"""Test de regresión para CORS (Fase B): sin esto, el frontend (Next.js,
otro origen) no puede llamar a la API desde el navegador - fallo real
encontrado al probar el flujo end-to-end con Playwright durante el
desarrollo de la Fase B (ver docs/02-roadmap/02-plan-autonomo.md)."""
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
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_preflight_options_responde_con_allow_origin_permitido(client):
    resp = client.options(
        "/users/1",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_preflight_options_no_incluye_allow_origin_para_origen_no_permitido(client):
    # Prueba negativa real: un origen distinto al configurado NO debe
    # recibir la cabecera - es lo que demuestra que la restricción de
    # CORS funciona, no solo que el origen bueno pasa.
    resp = client.options(
        "/users/1",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"
    assert "access-control-allow-origin" not in resp.headers


def test_get_health_incluye_cabecera_cors_para_origen_permitido(client):
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
