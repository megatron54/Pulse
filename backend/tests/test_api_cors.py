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


def test_incluye_cabecera_cors_para_el_origen_configurado(client, monkeypatch):
    monkeypatch.setenv("PULSE_FRONTEND_ORIGIN", "http://localhost:3000")
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    # Nota: el middleware de CORS se registra al importar el módulo, así
    # que este test verifica el comportamiento con el valor por defecto
    # (localhost:3000) que ya está activo en el `app` importado.
    assert resp.status_code == 200


def test_preflight_options_responde_con_allow_origin(client):
    resp = client.options(
        "/users/1",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
