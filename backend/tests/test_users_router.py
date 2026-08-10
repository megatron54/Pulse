"""Tests de integración del router de usuarios, incluyendo el alta vía
conexión Garmin (services.garmin_onboarding_service) - TDD."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from garmin_sync.client import GarminAuthError, GarminRateLimitedError
from models.schema import Base, GarminCredentials, UserProfile
from services.garmin_onboarding_service import GarminPerfilIncompletoError


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


class TestGarminConnect:
    def test_crea_el_usuario_con_los_datos_de_garmin(self, client):
        c, engine = client
        with Session(engine) as session:
            usuario_creado = UserProfile(
                nombre="Miguel", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28), sexo="M"
            )
            session.add(usuario_creado)
            session.commit()
            session.refresh(usuario_creado)

        with patch(
            "api.routers.users.connect_new_user_via_garmin", return_value=usuario_creado
        ) as mock_connect:
            resp = c.post(
                "/users/garmin-connect", json={"email": "miguel@example.com", "password": "hunter2"}
            )

        assert resp.status_code == 201
        assert resp.json()["nombre"] == "Miguel"
        # email/password se pasan a la capa de servicio, nunca se
        # devuelven en la respuesta.
        assert "password" not in resp.text
        assert mock_connect.call_args.kwargs["email"] == "miguel@example.com"
        assert mock_connect.call_args.kwargs["password"] == "hunter2"

    def test_perfil_incompleto_devuelve_422_con_los_campos_faltantes(self, client):
        c, _ = client
        with patch(
            "api.routers.users.connect_new_user_via_garmin",
            side_effect=GarminPerfilIncompletoError(["sexo", "altura_cm"]),
        ):
            resp = c.post(
                "/users/garmin-connect", json={"email": "miguel@example.com", "password": "hunter2"}
            )

        assert resp.status_code == 422
        assert set(resp.json()["detail"]["campos_faltantes"]) == {"sexo", "altura_cm"}

    def test_overrides_se_pasan_solo_si_estan_presentes(self, client):
        c, engine = client
        with Session(engine) as session:
            usuario_creado = UserProfile(
                nombre="Miguel", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28), sexo="M"
            )
            session.add(usuario_creado)
            session.commit()
            session.refresh(usuario_creado)

        with patch(
            "api.routers.users.connect_new_user_via_garmin", return_value=usuario_creado
        ) as mock_connect:
            c.post(
                "/users/garmin-connect",
                json={"email": "a@b.com", "password": "x", "sexo": "M"},
            )

        assert mock_connect.call_args.kwargs["overrides"] == {"sexo": "M"}

    def test_credenciales_invalidas_devuelve_401(self, client):
        c, _ = client
        with patch(
            "api.routers.users.connect_new_user_via_garmin",
            side_effect=GarminAuthError("401 no autorizado"),
        ):
            resp = c.post(
                "/users/garmin-connect", json={"email": "a@b.com", "password": "incorrecta"}
            )

        assert resp.status_code == 401
        # El mensaje nunca expone el detalle crudo de garminconnect.
        assert "incorrecta" not in resp.text

    def test_rate_limit_devuelve_429(self, client):
        c, _ = client
        with patch(
            "api.routers.users.connect_new_user_via_garmin",
            side_effect=GarminRateLimitedError("429 too many requests"),
        ):
            resp = c.post("/users/garmin-connect", json={"email": "a@b.com", "password": "x"})

        assert resp.status_code == 429

    def test_no_hay_credenciales_garmin_expuestas_en_ninguna_respuesta(self, client):
        c, engine = client
        with Session(engine) as session:
            usuario_creado = UserProfile(
                nombre="Miguel", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28), sexo="M"
            )
            session.add(usuario_creado)
            session.add(
                GarminCredentials(user_id=usuario_creado.id or 1, token_store_dir="/tmp/x", activo=True)
            )
            session.commit()
            session.refresh(usuario_creado)

        with patch("api.routers.users.connect_new_user_via_garmin", return_value=usuario_creado):
            resp = c.post(
                "/users/garmin-connect", json={"email": "a@b.com", "password": "super-secreto"}
            )

        assert "token_store_dir" not in resp.text
        assert "super-secreto" not in resp.text
