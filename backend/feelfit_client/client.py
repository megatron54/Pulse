"""Cliente para la API no oficial de Feelfit (báscula Qingniu/Yolanda) -
petición explícita del usuario: "investigar conexión custom con báscula
FeelFit" tras confirmar que su teléfono es Android (Health Connect está
"esencialmente ausente" en esta categoría de básculas, y el path de
Feelfit en Android es Google Fit o nada - ninguna vía oficial sirve).

Contrato HTTP verificado contra el código fuente REAL de dos
implementaciones independientes y en uso (ambas MIT):
- github.com/Sanji78/feelfit (integración de Home Assistant)
- github.com/tecnologicachile/mcp-feelfit (servidor MCP)
Ambas coinciden en el endpoint base, el payload de login (RSA + email),
y los nombres de campo de cada medición (`time_stamp`, `weight`,
`bodyfat`, etc.) - no es una suposición sobre una API no documentada,
es un contrato ya verificado por terceros contra cuentas reales.

Sigue el MISMO criterio de seguridad que `garmin_sync.client`: la
contraseña vive solo en memoria durante `login()`, nunca se persiste.
A diferencia de Garmin (donde `python-garminconnect`/garth cachea una
sesión de larga duración en disco de forma transparente), aquí el
propio contrato de la API expone `remaining_time` en la respuesta de
login (~180 días según ambas implementaciones de referencia) - se
persiste ese token + su expiración en `token_store_dir/session.json`,
nunca la contraseña."""
from __future__ import annotations

import base64
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

_API_BASE = "https://feelfit.qnclouds.com/api/v4"
_PATH_LOGIN = "/users/sign_in"
_PATH_MEASUREMENTS = "/measurements/list_measurement"

# Clave pública RSA embebida en la app Android de Feelfit - idéntica en
# ambas implementaciones de referencia (Sanji78/feelfit y
# tecnologicachile/mcp-feelfit), no es un secreto de Pulse.
_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+25I2upukpfQ7rIaaTZtVE744
u2zV+HaagrUhDOTq8fMVf9yFQvEZh2/HKxFudUxP0dXUa8F6X4XmWumHdQnum3zm
Jr04fz2b2WCcN0ta/rbF2nYAnMVAk2OJVZAMudOiMWhcxV1nNJiKgTNNr13de0EQ
IiOL2CUBzu+HmIfUbQIDAQAB
-----END PUBLIC KEY-----"""

_DEFAULT_PARAMS = {
    "app_revision": "4.16.0",
    "html_version": "14.16.0",
    "cellphone_type": "samsung SM-T510",
    "system_type": "11_30",
    "zone": "Europe/Madrid",
    "area_code": "ES",
    "locale": "es",
    "app_id": "Feelfit",
    "platform": "android",
}

_COMMON_HEADERS = {
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "Host": "feelfit.qnclouds.com",
    "User-Agent": "okhttp/4.9.1",
}

# Margen de seguridad antes de la expiración real para forzar un
# relogin preventivo en vez de arriesgarse a un 401 a mitad de sync.
_MARGEN_EXPIRACION_SEGUNDOS = 3600


class FeelfitAuthError(Exception):
    """Login fallido, credenciales inválidas, o token expirado sin
    password disponible para relogear (caso del scheduler nocturno,
    que solo tiene `token_store_dir`)."""


def _encrypt_password(password: str) -> str:
    rsa_key = RSA.import_key(_PUBLIC_KEY)
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted = cipher.encrypt(password.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def normalize_measurement(raw: dict[str, Any]) -> dict[str, Any]:
    """Normaliza una medición cruda de Feelfit a los campos que
    persiste `services.feelfit_sync_service`.

    "unknown is not zero": cualquier campo ausente se propaga como
    `None`, nunca como 0/0.0 - un `bodyfat_pct` faltante NUNCA debe
    guardarse como "0% de grasa corporal".

    `fuente_externa_id` usa `time_stamp` como clave de idempotencia
    (ver `BodyMeasurements.fuente_externa_id`): ninguna de las dos
    implementaciones de referencia expone un ID de medición propio en
    la lista (`list_measurement` solo devuelve `last_measurement_id`
    agregado a nivel de respuesta, no por item) - un timestamp de
    báscula es, en la práctica, único por medición real."""
    time_stamp = raw.get("time_stamp")
    return {
        "timestamp_epoch": time_stamp,
        "fuente_externa_id": str(time_stamp) if time_stamp is not None else None,
        "peso_kg": raw.get("weight"),
        "bodyfat_pct": raw.get("bodyfat"),
        "bmi": raw.get("bmi"),
        "muscle_kg": raw.get("muscle"),
        "bone_kg": raw.get("bone"),
        "water_pct": raw.get("water"),
    }


class FeelfitClient:
    """Cliente para una cuenta de Feelfit. `http_post`/`http_get` son
    inyectables (mismo patrón que `api_factory` en `GarminClient`) para
    poder testear sin red real."""

    def __init__(
        self,
        token_store_dir: str,
        email: str | None = None,
        password: str | None = None,
        http_post: Callable[..., Any] | None = None,
        http_get: Callable[..., Any] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._token_store_dir = token_store_dir
        self._email = email
        self._password = password
        self._http_post = http_post or requests.post
        self._http_get = http_get or requests.get
        self._clock = clock or time.time
        self._token: str | None = None
        self._user_id: str | None = None

    @property
    def _cache_path(self) -> Path:
        return Path(self._token_store_dir) / "session.json"

    def _cargar_token_cacheado(self) -> dict[str, Any] | None:
        if not self._cache_path.exists():
            return None
        try:
            return json.loads(self._cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _persistir_token(self, token: str, user_id: str, expires_at: float) -> None:
        Path(self._token_store_dir).mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps({"token": token, "user_id": user_id, "expires_at": expires_at})
        )

    def login(self) -> None:
        """Un único intento de login real (nunca reintenta a
        ciegas - mismo criterio que `GarminClient.login`), reutilizando
        el token cacheado en disco si sigue vigente.

        Si el token cacheado expiró y no hay `email`/`password`
        disponibles (caso del scheduler, que solo pasa
        `token_store_dir`), lanza `FeelfitAuthError` explícito en vez
        de intentar un login con credenciales `None` - el usuario debe
        reconectar su cuenta manualmente (POST /feelfit-connect)."""
        cache = self._cargar_token_cacheado()
        if cache and cache.get("expires_at", 0) > self._clock() + _MARGEN_EXPIRACION_SEGUNDOS:
            self._token = cache["token"]
            self._user_id = cache["user_id"]
            return

        if not self._email or not self._password:
            raise FeelfitAuthError(
                "Token cacheado ausente o expirado y no hay credenciales para relogear. "
                "El usuario debe reconectar su cuenta Feelfit."
            )

        encrypted_pw = _encrypt_password(self._password)
        headers = {**_COMMON_HEADERS, "Authorization": "Bearer", "Content-Type": "application/json;charset=UTF-8"}
        resp = self._http_post(
            f"{_API_BASE}{_PATH_LOGIN}?{_query_string(_DEFAULT_PARAMS)}",
            headers=headers,
            json={"email": self._email, "password": encrypted_pw},
            timeout=15,
        )
        if resp.status_code != 200:
            raise FeelfitAuthError(f"Login Feelfit falló con HTTP {resp.status_code}")

        resultado = resp.json()
        if str(resultado.get("code")) not in ("200", "0"):
            raise FeelfitAuthError(f"Login Feelfit rechazado: {resultado.get('msg', resultado)}")

        data = resultado.get("data") or {}
        token_info = data.get("token_info") or {}
        token = token_info.get("token")
        user_info = data.get("user_info") or {}
        user_id = str(user_info.get("user_id")) if user_info.get("user_id") is not None else None
        if not token or not user_id:
            raise FeelfitAuthError("Login Feelfit devolvió una respuesta sin token o user_id")

        remaining = float(token_info.get("remaining_time") or 0)
        expires_at = self._clock() + remaining
        self._persistir_token(token, user_id, expires_at)
        self._token = token
        self._user_id = user_id

    def get_measurements_raw(self, last_updated_at: int = 0) -> dict[str, Any]:
        """Devuelve el payload crudo de `/measurements/list_measurement`
        (lista bajo `measurements`, sin normalizar) - la normalización a
        los campos internos de Pulse vive en `normalize_measurement`,
        deliberadamente separada para poder reprocesar sin volver a
        golpear la API si cambia la lógica de negocio (mismo criterio
        que `raw_json` en las tablas de ingesta de Garmin)."""
        if not self._token or not self._user_id:
            raise FeelfitAuthError("login() debe llamarse antes de pedir mediciones")

        params = {
            **_DEFAULT_PARAMS,
            "user_id": self._user_id,
            "last_updated_at": str(last_updated_at),
            "last_measurement_id": "0",
        }
        headers = {**_COMMON_HEADERS, "Authorization": f"Bearer {self._token}"}
        resp = self._http_get(f"{_API_BASE}{_PATH_MEASUREMENTS}", headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            raise FeelfitAuthError(f"GET measurements falló con HTTP {resp.status_code}")
        resultado = resp.json()
        if isinstance(resultado, dict) and "data" in resultado:
            return resultado.get("data") or {}
        return resultado


def _query_string(params: dict[str, str]) -> str:
    return urllib.parse.urlencode(params)
