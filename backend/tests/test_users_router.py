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
from models.schema import (
    Base,
    BodyMeasurements,
    FeelfitCredentials,
    GarminCredentials,
    GarminDailyMetrics,
    UserProfile,
)
from services.garmin_onboarding_service import ConexionGarminResultado, GarminPerfilIncompletoError


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

        with (
            patch(
                "api.routers.users.connect_or_reconnect_via_garmin",
                return_value=ConexionGarminResultado(
                    usuario=usuario_creado, es_nuevo=True, token_store_dir="/tmp/x"
                ),
            ) as mock_connect,
            patch("api.routers.users._ejecutar_backfill_en_background"),
        ):
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

    def test_dispara_el_backfill_como_tarea_en_background_no_bloqueante(self, client):
        # Hallazgo de code-review, CRÍTICO: antes de este fix, el
        # backfill de 90 días corría DENTRO de esta misma petición HTTP
        # (~900 llamadas secuenciales a Garmin) - causa real del
        # "iniciando sesión" colgado varios minutos y del rate-limit.
        # La respuesta debe volver en cuanto el usuario existe, con el
        # backfill programado como tarea en background aparte.
        c, engine = client
        with Session(engine) as session:
            usuario_creado = UserProfile(
                nombre="Miguel", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28), sexo="M"
            )
            session.add(usuario_creado)
            session.commit()
            session.refresh(usuario_creado)

        with (
            patch(
                "api.routers.users.connect_or_reconnect_via_garmin",
                return_value=ConexionGarminResultado(
                    usuario=usuario_creado, es_nuevo=True, token_store_dir="/tmp/x"
                ),
            ),
            patch("api.routers.users._ejecutar_backfill_en_background") as mock_backfill,
        ):
            resp = c.post(
                "/users/garmin-connect", json={"email": "miguel@example.com", "password": "hunter2"}
            )

        assert resp.status_code == 201
        mock_backfill.assert_called_once()
        assert mock_backfill.call_args.args[0] == usuario_creado.id

    def test_perfil_incompleto_devuelve_422_con_los_campos_faltantes(self, client):
        c, _ = client
        with patch(
            "api.routers.users.connect_or_reconnect_via_garmin",
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

        with (
            patch(
                "api.routers.users.connect_or_reconnect_via_garmin",
                return_value=ConexionGarminResultado(
                    usuario=usuario_creado, es_nuevo=True, token_store_dir="/tmp/x"
                ),
            ) as mock_connect,
            patch("api.routers.users._ejecutar_backfill_en_background"),
        ):
            c.post(
                "/users/garmin-connect",
                json={"email": "a@b.com", "password": "x", "sexo": "M"},
            )

        assert mock_connect.call_args.kwargs["overrides"] == {"sexo": "M"}

    def test_credenciales_invalidas_devuelve_401(self, client):
        c, _ = client
        with patch(
            "api.routers.users.connect_or_reconnect_via_garmin",
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
            "api.routers.users.connect_or_reconnect_via_garmin",
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

        with (
            patch(
                "api.routers.users.connect_or_reconnect_via_garmin",
                return_value=ConexionGarminResultado(
                    usuario=usuario_creado, es_nuevo=True, token_store_dir="/tmp/x"
                ),
            ),
            patch("api.routers.users._ejecutar_backfill_en_background"),
        ):
            resp = c.post(
                "/users/garmin-connect", json={"email": "a@b.com", "password": "super-secreto"}
            )

        assert "token_store_dir" not in resp.text
        assert "super-secreto" not in resp.text


class TestGetConnections:
    """GET /users/{id}/connections - lo que alimenta la página de Perfil."""

    def _crear_usuario(self, engine) -> int:
        with Session(engine) as session:
            usuario = UserProfile(
                nombre="Miguel", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28), sexo="M"
            )
            session.add(usuario)
            session.commit()
            return usuario.id

    def test_sin_credenciales_reporta_todo_desconectado(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)

        resp = c.get(f"/users/{user_id}/connections")

        assert resp.status_code == 200
        datos = resp.json()
        assert datos["garmin"] == {
            "conectado": False,
            "email": None,
            "historial_desde": None,
            "dias_de_historial": None,
        }
        assert datos["feelfit"]["conectado"] is False
        assert datos["feelfit"]["mediciones_importadas"] == 0

    def test_reporta_email_historial_y_dias_sincronizados_de_garmin(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)
        with Session(engine) as session:
            session.add(
                GarminCredentials(
                    user_id=user_id,
                    token_store_dir="/tmp/x",
                    garmin_email="miguel@example.com",
                    historial_sincronizado_desde=date(2026, 6, 1),
                    activo=True,
                )
            )
            session.add_all(
                [
                    GarminDailyMetrics(user_id=user_id, fecha=date(2026, 9, 11)),
                    GarminDailyMetrics(user_id=user_id, fecha=date(2026, 9, 12)),
                ]
            )
            session.commit()

        datos = c.get(f"/users/{user_id}/connections").json()

        assert datos["garmin"] == {
            "conectado": True,
            "email": "miguel@example.com",
            "historial_desde": "2026-06-01",
            "dias_de_historial": 2,
        }

    def test_credenciales_inactivas_cuentan_como_no_conectado(self, client):
        """`activo=False` es la marca que deja el scheduler cuando el
        token deja de funcionar: mostrarlo como conectado sería falsa
        precisión y el usuario nunca sabría que debe reconectar."""
        c, engine = client
        user_id = self._crear_usuario(engine)
        with Session(engine) as session:
            session.add(
                GarminCredentials(user_id=user_id, token_store_dir="/tmp/x", activo=False)
            )
            session.add(FeelfitCredentials(user_id=user_id, token_store_dir="/tmp/f", activo=False))
            session.commit()

        datos = c.get(f"/users/{user_id}/connections").json()

        assert datos["garmin"]["conectado"] is False
        assert datos["feelfit"]["conectado"] is False

    def test_solo_cuenta_como_feelfit_las_mediciones_de_la_bascula(self, client):
        """Las mediciones manuales no son datos importados de Feelfit:
        contarlas atribuiría a la integración algo que el usuario metió
        a mano."""
        c, engine = client
        user_id = self._crear_usuario(engine)
        with Session(engine) as session:
            session.add(FeelfitCredentials(user_id=user_id, token_store_dir="/tmp/f", activo=True))
            session.add_all(
                [
                    BodyMeasurements(
                        user_id=user_id,
                        fecha=date(2026, 9, 10),
                        peso_kg=74.0,
                        metodo="feelfit_bioimpedance",
                        fuente_externa_id="m-1",
                    ),
                    BodyMeasurements(
                        user_id=user_id, fecha=date(2026, 9, 11), peso_kg=74.2, metodo="manual"
                    ),
                ]
            )
            session.commit()

        datos = c.get(f"/users/{user_id}/connections").json()

        assert datos["feelfit"]["conectado"] is True
        assert datos["feelfit"]["mediciones_importadas"] == 1

    def test_nunca_expone_el_token_store_dir(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)
        with Session(engine) as session:
            session.add(
                GarminCredentials(
                    user_id=user_id, token_store_dir="/secreto/tokens/garmin", activo=True
                )
            )
            session.commit()

        resp = c.get(f"/users/{user_id}/connections")

        assert "token_store_dir" not in resp.text
        assert "/secreto/tokens" not in resp.text

    def test_404_si_el_usuario_no_existe(self, client):
        c, _ = client

        assert c.get("/users/9999/connections").status_code == 404


class TestUpdateUser:
    """PATCH /users/{id} - edición del propio perfil desde Perfil."""

    def _crear_usuario(self, engine) -> int:
        with Session(engine) as session:
            usuario = UserProfile(
                nombre="Miguel",
                altura_cm=176.0,
                fecha_nacimiento=date(2002, 11, 28),
                sexo="M",
                fase_peso_actual="maintenance",
            )
            session.add(usuario)
            session.commit()
            return usuario.id

    def test_actualiza_solo_los_campos_enviados(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)

        resp = c.patch(f"/users/{user_id}", json={"fase_peso_actual": "cut"})

        assert resp.status_code == 200
        datos = resp.json()
        assert datos["fase_peso_actual"] == "cut"
        # Lo no enviado se queda como estaba (no se pisa con defaults).
        assert datos["nombre"] == "Miguel"
        assert datos["altura_cm"] == 176.0
        assert datos["fecha_nacimiento"] == "2002-11-28"

    def test_persiste_el_cambio(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)

        c.patch(f"/users/{user_id}", json={"nombre": "Miguel Serra", "altura_cm": 177.5})

        with Session(engine) as session:
            usuario = session.get(UserProfile, user_id)
            assert usuario.nombre == "Miguel Serra"
            assert usuario.altura_cm == 177.5

    def test_rechaza_una_altura_imposible(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)

        assert c.patch(f"/users/{user_id}", json={"altura_cm": 0}).status_code == 422
        assert c.patch(f"/users/{user_id}", json={"altura_cm": -5}).status_code == 422

    def test_rechaza_una_fase_de_peso_inexistente(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)

        assert c.patch(f"/users/{user_id}", json={"fase_peso_actual": "bulking"}).status_code == 422

    def test_rechaza_un_campo_desconocido(self, client):
        """Un nombre de campo mal escrito debe fallar, no aceptarse y no
        cambiar nada (el cliente creería que guardó)."""
        c, engine = client
        user_id = self._crear_usuario(engine)

        assert c.patch(f"/users/{user_id}", json={"altura": 180}).status_code == 422

    def test_un_patch_vacio_es_400(self, client):
        c, engine = client
        user_id = self._crear_usuario(engine)

        assert c.patch(f"/users/{user_id}", json={}).status_code == 400

    def test_404_si_el_usuario_no_existe(self, client):
        c, _ = client

        assert c.patch("/users/9999", json={"nombre": "X"}).status_code == 404
