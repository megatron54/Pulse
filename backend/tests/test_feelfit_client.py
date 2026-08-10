"""Tests para feelfit_client.client - TDD, escritos antes que la
implementación.

Sin red real ni credenciales: `http_post`/`http_get` se inyectan como
callables reemplazables (misma filosofía que `api_factory` en
`garmin_sync.client`), sustituidos aquí por dobles de prueba. El
contrato HTTP (endpoints, forma del payload de login, cabeceras) está
verificado contra el código fuente real de DOS implementaciones
independientes de la API no oficial de Feelfit
(github.com/Sanji78/feelfit y github.com/tecnologicachile/mcp-feelfit,
ambas MIT, ambas en uso real) - no es una suposición.

`fecha`/`peso_kg` de cada medición SÍ están verificados contra ambas
fuentes (`time_stamp`, `weight`). El resto de campos opcionales
(bodyfat, muscle, etc.) también, pero "unknown is not zero": si algún
campo faltara en un payload real no contemplado aquí, se propaga como
`None`, nunca como 0."""
from __future__ import annotations

import json

import pytest

from feelfit_client.client import (
    FeelfitAuthError,
    FeelfitClient,
    normalize_measurement,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _login_ok_payload(token="tok-abc", remaining_time=180 * 24 * 3600, user_id="12345"):
    return {
        "code": "200",
        "data": {
            "token_info": {"token": token, "remaining_time": remaining_time},
            "user_info": {"user_id": user_id, "account_name": "Miguel"},
        },
    }


class TestLogin:
    def test_login_exitoso_persiste_token_en_disco_y_lo_usa(self, tmp_path):
        llamadas_post = []

        def fake_post(url, headers=None, json=None, timeout=None):
            llamadas_post.append((url, json))
            return _FakeResponse(200, _login_ok_payload())

        client = FeelfitClient(
            token_store_dir=str(tmp_path),
            email="user@example.com",
            password="secreto123",
            http_post=fake_post,
            http_get=lambda *a, **k: _FakeResponse(200, {"data": {}}),
        )
        client.login()

        assert len(llamadas_post) == 1
        assert "/users/sign_in" in llamadas_post[0][0]
        # La contraseña NUNCA viaja en claro en el payload (mismo
        # criterio de seguridad que Garmin) - se cifra con RSA antes.
        assert llamadas_post[0][1]["password"] != "secreto123"
        assert client._token == "tok-abc"
        assert client._user_id == "12345"

        # Persistida en disco para reutilizarse sin password (scheduler).
        cache_path = tmp_path / "session.json"
        assert cache_path.exists()
        cache = json.loads(cache_path.read_text())
        assert cache["token"] == "tok-abc"
        assert cache["user_id"] == "12345"

    def test_login_reutiliza_token_cacheado_sin_llamar_a_la_red(self, tmp_path):
        (tmp_path / "session.json").write_text(
            json.dumps({"token": "tok-cacheado", "user_id": "999", "expires_at": 9999999999.0})
        )
        llamadas_post = []

        client = FeelfitClient(
            token_store_dir=str(tmp_path),
            http_post=lambda *a, **k: llamadas_post.append(1) or _FakeResponse(200, {}),
            http_get=lambda *a, **k: _FakeResponse(200, {"data": {}}),
            clock=lambda: 1000.0,
        )
        client.login()

        assert llamadas_post == []
        assert client._token == "tok-cacheado"
        assert client._user_id == "999"

    def test_token_cacheado_expirado_fuerza_relogin(self, tmp_path):
        (tmp_path / "session.json").write_text(
            json.dumps({"token": "tok-viejo", "user_id": "999", "expires_at": 500.0})
        )
        llamadas_post = []

        def fake_post(url, headers=None, json=None, timeout=None):
            llamadas_post.append(url)
            return _FakeResponse(200, _login_ok_payload(token="tok-nuevo"))

        client = FeelfitClient(
            token_store_dir=str(tmp_path),
            email="user@example.com",
            password="secreto123",
            http_post=fake_post,
            http_get=lambda *a, **k: _FakeResponse(200, {"data": {}}),
            clock=lambda: 1000.0,
        )
        client.login()

        assert len(llamadas_post) == 1
        assert client._token == "tok-nuevo"

    def test_token_expirado_sin_password_lanza_auth_error_claro(self, tmp_path):
        # Caso real del scheduler nocturno: solo tiene token_store_dir,
        # sin email/password. Si el token cacheado expiró, no puede
        # relogear solo - debe fallar con un mensaje claro (nunca
        # intentar login con password=None silenciosamente).
        (tmp_path / "session.json").write_text(
            json.dumps({"token": "tok-viejo", "user_id": "999", "expires_at": 500.0})
        )
        client = FeelfitClient(token_store_dir=str(tmp_path), clock=lambda: 1000.0)

        with pytest.raises(FeelfitAuthError):
            client.login()

    def test_login_con_credenciales_invalidas_lanza_feelfit_auth_error(self, tmp_path):
        def fake_post(url, headers=None, json=None, timeout=None):
            return _FakeResponse(200, {"code": "400", "msg": "credenciales inválidas"})

        client = FeelfitClient(
            token_store_dir=str(tmp_path),
            email="user@example.com",
            password="mala",
            http_post=fake_post,
            http_get=lambda *a, **k: _FakeResponse(200, {}),
        )
        with pytest.raises(FeelfitAuthError):
            client.login()

    def test_login_con_error_http_lanza_feelfit_auth_error(self, tmp_path):
        def fake_post(url, headers=None, json=None, timeout=None):
            return _FakeResponse(401, {"msg": "unauthorized"})

        client = FeelfitClient(
            token_store_dir=str(tmp_path),
            email="user@example.com",
            password="x",
            http_post=fake_post,
            http_get=lambda *a, **k: _FakeResponse(200, {}),
        )
        with pytest.raises(FeelfitAuthError):
            client.login()


class TestGetMeasurementsRaw:
    def test_devuelve_la_lista_cruda_de_mediciones(self, tmp_path):
        def fake_post(url, headers=None, json=None, timeout=None):
            return _FakeResponse(200, _login_ok_payload())

        capturado = {}

        def fake_get(url, headers=None, params=None, timeout=None):
            capturado["url"] = url
            capturado["params"] = params
            return _FakeResponse(
                200,
                {
                    "data": {
                        "measurements": [
                            {"time_stamp": 1723300000, "weight": 74.1, "bodyfat": 19.4},
                        ],
                        "last_updated_at": 1723300000,
                    }
                },
            )

        client = FeelfitClient(
            token_store_dir=str(tmp_path),
            email="user@example.com",
            password="x",
            http_post=fake_post,
            http_get=fake_get,
        )
        client.login()
        resultado = client.get_measurements_raw()

        assert capturado["params"]["user_id"] == "12345"
        assert len(resultado["measurements"]) == 1
        assert resultado["measurements"][0]["weight"] == 74.1

    def test_no_autenticado_lanza_error_claro(self, tmp_path):
        client = FeelfitClient(token_store_dir=str(tmp_path))
        with pytest.raises(FeelfitAuthError):
            client.get_measurements_raw()


class TestNormalizeMeasurement:
    def test_mapea_los_campos_verificados_contra_las_dos_implementaciones_reales(self):
        raw = {
            "time_stamp": 1723300000,
            "weight": 74.1,
            "bodyfat": 19.4,
            "bmi": 23.1,
            "muscle": 55.2,
            "bone": 3.1,
            "water": 58.0,
        }
        resultado = normalize_measurement(raw)

        assert resultado["timestamp_epoch"] == 1723300000
        assert resultado["peso_kg"] == 74.1
        assert resultado["bodyfat_pct"] == 19.4
        assert resultado["fuente_externa_id"] == "1723300000"

    def test_campos_ausentes_se_propagan_como_none_nunca_como_cero(self):
        # "unknown is not zero": un payload real que no traiga bodyfat
        # (báscula sin bioimpedancia, o campo distinto al esperado) NO
        # debe registrarse como 0.0% de grasa.
        raw = {"time_stamp": 1723300000, "weight": 74.1}
        resultado = normalize_measurement(raw)

        assert resultado["bodyfat_pct"] is None

    def test_sin_time_stamp_no_hay_fuente_externa_id(self):
        resultado = normalize_measurement({"weight": 74.1})
        assert resultado["fuente_externa_id"] is None
        assert resultado["timestamp_epoch"] is None
