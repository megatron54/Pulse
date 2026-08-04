"""Cliente de sincronización con Garmin Connect.

No es Capa 1 (motor de reglas): es la capa de INGESTA DE DATOS de la
arquitectura (docs/01-arquitectura/01-arquitectura-general.md). Aun así
sigue el mismo estándar de robustez: sin llamadas mágicas, con manejo de
errores explícito y testeable sin red real (la librería `garminconnect`
se inyecta vía `api_factory`, sustituible por un doble de prueba).

Política de autenticación (ver docs/00-research/03-garmin-integracion.md):
- Reutilizar SIEMPRE el token cacheado (`token_store_dir`); un solo
  intento de login, NUNCA un bucle de reintento agresivo — es la causa
  raíz documentada de bloqueos de cuenta de 48-72h en el foro de Garmin.
- Distinguir explícitamente errores de rate-limit (429) de otros fallos
  de autenticación, para que la capa de sincronización pueda aplicar
  backoff exponencial en vez de reintentar de inmediato.
- Cada campo de recuperación (HRV, sleep, body battery, training
  readiness) se obtiene con su propia llamada: Garmin entrega payloads
  independientes por tipo de dato, y un fallo puntual en uno no debe
  impedir obtener el resto (principio "unknown is not zero": se marca
  ese campo como None, nunca se inventa un valor).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable

_RATE_LIMIT_MARCADORES = ("429", "403", "too many requests", "rate limit")


class GarminAuthError(Exception):
    """Fallo de autenticación no relacionado con rate-limiting."""


class GarminRateLimitedError(Exception):
    """Garmin ha aplicado rate-limiting o un bloqueo Cloudflare a la
    cuenta (429/403 o equivalente).

    La capa llamante NO debe reintentar el login inmediatamente: debe
    aplicar backoff exponencial o esperar a la siguiente ventana diaria.

    Nota de deuda técnica: la detección hoy es por substring del mensaje
    de error, no por tipo/status_code de excepción. Si en el futuro se
    observan falsos positivos/negativos, migrar a detectar la excepción
    tipada de `python-garminconnect` (ej. GarminConnectTooManyRequestsError)
    y el `status_code` HTTP como señal primaria, dejando el string como
    fallback únicamente.
    """


def _default_api_factory():
    """Factory por defecto: importa garminconnect de forma perezosa para
    que los tests puedan sustituirla sin necesitar la dependencia
    instalada ni credenciales reales."""
    import garminconnect

    return garminconnect.Garmin


def _es_error_de_rate_limit(exc: Exception) -> bool:
    mensaje = str(exc).lower()
    return any(marcador in mensaje for marcador in _RATE_LIMIT_MARCADORES)


def _extraer_hrv(payload: Any) -> float | None:
    if not payload:
        return None
    try:
        return payload["hrvSummary"]["lastNightAvg"]
    except (KeyError, TypeError):
        return None


def _extraer_training_readiness(payload: Any) -> str | None:
    """Normaliza el nivel de Garmin ("HIGH"/"MODERATE"/"LOW"/"LOW_LOW"...)
    al vocabulario esperado por engine.periodization.RecoveryContext
    ("high"/"moderate"/"low"/"very_low")."""
    if not payload:
        return None
    try:
        nivel_garmin = payload[0]["level"]
    except (KeyError, TypeError, IndexError):
        return None
    if not nivel_garmin:
        return None
    return _NIVELES_TRAINING_READINESS.get(nivel_garmin.upper())


_NIVELES_TRAINING_READINESS = {
    "HIGH": "high",
    "MODERATE": "moderate",
    "LOW": "low",
    "LOW_LOW": "very_low",
    "VERY_LOW": "very_low",
}


def _extraer_body_battery(payload: Any) -> int | None:
    if not payload:
        return None
    try:
        return payload[0]["charged"]
    except (KeyError, TypeError, IndexError):
        return None


def _extraer_sleep_score(payload: Any) -> int | None:
    if not payload:
        return None
    try:
        return payload["dailySleepDTO"]["sleepScores"]["overall"]["value"]
    except (KeyError, TypeError):
        return None


class GarminClient:
    """Wrapper fino sobre `garminconnect.Garmin` con la política de
    autenticación y extracción de datos descrita en el docstring del
    módulo. NOTA: las funciones `_extraer_*` asumen la forma del JSON de
    la API pública de garminconnect documentada en su demo; conviene
    verificarlas/ajustarlas contra una cuenta real en la primera
    sincronización end-to-end (Fase 0 del roadmap)."""

    def __init__(
        self,
        token_store_dir: str,
        email: str | None = None,
        password: str | None = None,
        api_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._token_store_dir = token_store_dir
        self._email = email
        self._password = password
        self._api_factory = api_factory or _default_api_factory()
        self._api: Any = None

    def login(self) -> None:
        """Un único intento de login, reutilizando el token cacheado.
        Nunca reintenta internamente: si falla, la capa llamante decide
        (backoff, esperar al día siguiente, alertar al usuario)."""
        api = self._api_factory(self._email, self._password)
        try:
            api.login(self._token_store_dir)
        except Exception as exc:
            if _es_error_de_rate_limit(exc):
                raise GarminRateLimitedError(str(exc)) from exc
            raise GarminAuthError(str(exc)) from exc
        self._api = api

    def get_daily_recovery_raw(self, date_str: str) -> dict[str, Any]:
        """Obtiene y normaliza los 4 campos de recuperación del día,
        más el payload crudo completo bajo `raw_json` para auditoría y
        posible reprocesado si cambia la lógica de negocio.

        `date_str` debe tener formato ISO YYYY-MM-DD; se valida aquí
        para dar un error claro en vez de un InsufficientDataError
        engañoso más abajo si el formato fuera inválido.
        """
        if self._api is None:
            raise RuntimeError("login() debe llamarse antes de sincronizar datos")
        try:
            date.fromisoformat(date_str)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"date_str debe tener formato ISO YYYY-MM-DD, recibido: {date_str!r}"
            ) from exc

        raw_hrv = self._llamada_segura(self._api.get_hrv_data, date_str)
        raw_readiness = self._llamada_segura(
            self._api.get_training_readiness, date_str
        )
        raw_body_battery = self._llamada_segura(self._api.get_body_battery, date_str)
        raw_sleep = self._llamada_segura(self._api.get_sleep_data, date_str)

        return {
            "hrv_today": _extraer_hrv(raw_hrv),
            "training_readiness": _extraer_training_readiness(raw_readiness),
            "body_battery_am": _extraer_body_battery(raw_body_battery),
            "sleep_score": _extraer_sleep_score(raw_sleep),
            "raw_json": {
                "hrv": raw_hrv,
                "training_readiness": raw_readiness,
                "body_battery": raw_body_battery,
                "sleep": raw_sleep,
            },
        }

    @staticmethod
    def _llamada_segura(metodo: Callable[[str], Any], date_str: str) -> Any:
        """Ejecuta una llamada individual a la API; un fallo aquí no debe
        impedir obtener el resto de campos de recuperación del día."""
        try:
            return metodo(date_str)
        except Exception:
            return None

    def get_activities_raw(self, start_date_str: str, end_date_str: str) -> list[dict[str, Any]]:
        """Lista cruda de actividades (carrera/ciclismo/fuerza/...) en el
        rango `[start_date_str, end_date_str]`, tal cual las entrega
        `get_activities_by_date` de python-garminconnect - sin normalizar
        (eso es responsabilidad de `garmin_sync.activity_mapper`, para
        mantener este cliente como un wrapper fino sobre la API externa,
        igual que `get_daily_recovery_raw`).

        A diferencia de la recuperación diaria (4 llamadas independientes
        que se degradan campo a campo), aquí solo hay una llamada: si
        falla, se propaga tal cual - no hay nada parcial que rescatar.
        Un payload `None`/ausente se normaliza a lista vacía (`unknown is
        not zero` en su variante de colección: sin actividades ese rango
        no es un error)."""
        if self._api is None:
            raise RuntimeError("login() debe llamarse antes de sincronizar datos")
        for date_str in (start_date_str, end_date_str):
            try:
                date.fromisoformat(date_str)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"las fechas deben tener formato ISO YYYY-MM-DD, recibido: {date_str!r}"
                ) from exc

        actividades = self._api.get_activities_by_date(start_date_str, end_date_str)
        return actividades or []
