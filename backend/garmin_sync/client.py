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


def _sanitizar_mensaje(mensaje: str, password: str | None) -> str:
    """Defensa en profundidad (LOW-1 de la revisión de seguridad del
    emparejamiento de Fase H): `python-garminconnect`/`garth` no
    incluyen la contraseña en sus mensajes de error observados, pero
    este código no debe depender para siempre de ese comportamiento de
    una librería externa. Si la contraseña apareciera como substring en
    el mensaje de error por cualquier motivo, se enmascara antes de que
    la excepción se propague/imprima en pantalla (ver scripts/
    garmin_pair.py)."""
    if password:
        mensaje = mensaje.replace(password, "***")
    return mensaje


def _extraer_hrv(payload: Any) -> float | None:
    if not payload:
        return None
    try:
        return payload["hrvSummary"]["lastNightAvg"]
    except (KeyError, TypeError):
        return None


def _extraer_hrv_status(payload: Any) -> str | None:
    """Estado cualitativo de HRV que Garmin ya calcula
    ("BALANCED"/"UNBALANCED"/"LOW"/"NONE"...) - se persiste tal cual
    viene (sin normalizar a un vocabulario propio, a diferencia de
    training_readiness) porque hoy no hay ningún motor de reglas que
    dependa de un valor concreto de este campo - es solo informativo
    para el histórico/dashboard (Épica A del plan de expansión,
    02-roadmap/03-vision-produccion.md)."""
    if not payload:
        return None
    try:
        return payload["hrvSummary"]["status"]
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


def _extraer_stress_avg(payload: Any) -> int | None:
    """`get_stress_data` (forma confirmada contra una cuenta real, ver
    02-roadmap/03-vision-produccion.md Épica A - no está tipada en
    python-garminconnect/typed.py, así que no se asumió sin verificar).
    Garmin usa -1/-2 como valores centinela dentro de la serie intradía
    (`stressValuesArray`) para "sin datos suficientes ese minuto", pero
    `avgStressLevel` en sí puede venir como -1 si no hay NINGÚN dato de
    estrés ese día entero - se trata igual que ausencia (None), nunca
    se muestra un estrés negativo como si fuera un valor real."""
    if not payload:
        return None
    try:
        valor = payload["avgStressLevel"]
    except (KeyError, TypeError):
        return None
    if not isinstance(valor, (int, float)) or valor < 0:
        return None
    return int(valor)


def _extraer_resting_hr(payload: Any) -> int | None:
    """`get_rhr_day` (forma confirmada contra una cuenta real): la lista
    bajo `WELLNESS_RESTING_HEART_RATE` puede venir vacía si el
    dispositivo aún no ha calculado el dato ese día.

    No se pudo confirmar contra un payload real si Garmin usa aquí el
    mismo centinela negativo que en `get_stress_data` (la cuenta de
    verificación de esta sesión siempre trajo un valor válido) - por
    analogía y prudencia se descarta igualmente cualquier valor ≤0,
    ya que un pulso en reposo real nunca puede ser cero o negativo."""
    if not payload:
        return None
    try:
        serie = payload["allMetrics"]["metricsMap"]["WELLNESS_RESTING_HEART_RATE"]
        valor = serie[0]["value"]
    except (KeyError, TypeError, IndexError):
        return None
    if not isinstance(valor, (int, float)) or valor <= 0:
        return None
    return valor


def _extraer_vo2max(payload: Any) -> float | None:
    """`get_max_metrics` - NOTA DE INCERTIDUMBRE EXPLÍCITA: contra la
    cuenta real usada para verificar esta sesión (Forerunner 165), este
    endpoint devuelve una lista VACÍA (el dispositivo/cuenta aún no
    tiene un VO2max calculado) - no se pudo confirmar la forma real de
    un elemento no vacío contra datos reales, y `typed.py` de
    python-garminconnect tampoco cubre este endpoint. La ruta de campo
    de abajo (`generic.vo2MaxPreciseValue`) es la documentada de forma
    consistente por la comunidad de integraciones de terceros
    (garmin-grafana y proyectos similares, ver 00-research/
    04-reutilizacion-open-source.md) pero DEBE revalidarse contra un
    payload real en cuanto exista una cuenta/dispositivo con VO2max
    disponible - "unknown is not zero": ante cualquier forma inesperada
    se devuelve None, nunca se inventa un número."""
    if not payload:
        return None
    try:
        return payload[0]["generic"]["vo2MaxPreciseValue"]
    except (KeyError, TypeError, IndexError):
        return None


def _extraer_serie(
    payload: Any, clave_array: str, *, descartar_negativos: bool = False
) -> list[tuple[int, float]]:
    """Extrae una serie `[timestamp_ms, valor]` de un payload dict de
    Garmin (`heartRateValues`/`stressValuesArray`) a una lista de
    tuplas `(timestamp_ms, valor)`. `descartar_negativos` filtra los
    centinelas negativos que Garmin usa en `stressValuesArray` para
    "sin datos suficientes ese minuto" ("unknown is not zero": un
    hueco en la serie es honesto, un -1/-2 mostrado como valor real
    no lo es). Cualquier forma inesperada da lista vacía, nunca
    lanza."""
    if not payload:
        return []
    try:
        puntos = payload.get(clave_array) or []
        resultado = []
        for punto in puntos:
            timestamp_ms, valor = punto[0], punto[1]
            if valor is None:
                continue
            if descartar_negativos and valor < 0:
                continue
            resultado.append((timestamp_ms, valor))
        return resultado
    except (AttributeError, TypeError, IndexError):
        return []


def _extraer_serie_body_battery(payload: Any) -> list[tuple[int, float]]:
    """`get_body_battery(date)` devuelve una LISTA (no un dict) de un
    elemento por día - forma real verificada contra una cuenta Garmin
    real, distinta de `get_heart_rates`/`get_stress_data`."""
    if not payload:
        return []
    try:
        return _extraer_serie(payload[0], "bodyBatteryValuesArray")
    except (KeyError, TypeError, IndexError):
        return []


class GarminClient:
    """Wrapper fino sobre `garminconnect.Garmin` con la política de
    autenticación y extracción de datos descrita en el docstring del
    módulo. Las funciones `_extraer_*` de HRV/training readiness/body
    battery/sleep están verificadas contra la forma pública documentada
    de python-garminconnect; `stress_avg`, `resting_hr` y `hrv_status`
    se verificaron además contra el JSON crudo real de una cuenta
    Garmin real en la sesión que añadió estos campos (Épica A,
    02-roadmap/03-vision-produccion.md). `vo2max` sigue siendo la
    excepción: no se pudo confirmar su forma contra un payload real no
    vacío (ver nota de incertidumbre en `_extraer_vo2max`) - revalidar
    en cuanto exista una cuenta/dispositivo con VO2max calculado."""

    def __init__(
        self,
        token_store_dir: str,
        email: str | None = None,
        password: str | None = None,
        api_factory: Callable[..., Any] | None = None,
        mfa_code_prompt: Callable[[], str] | None = None,
    ) -> None:
        self._token_store_dir = token_store_dir
        self._email = email
        self._password = password
        self._api_factory = api_factory or _default_api_factory()
        self._mfa_code_prompt = mfa_code_prompt
        self._api: Any = None
        # Caché por-fecha de `get_body_battery`/`get_stress_data`
        # (hallazgo de code-review): `get_daily_recovery_raw` y
        # `get_intraday_series_raw` piden estas DOS llamadas para el
        # MISMO día (el payload trae tanto el agregado como el array
        # intradía) - sin esta caché, una misma pasada del scheduler
        # duplicaba 2 de las 3 llamadas nuevas de intradía, aumentando
        # innecesariamente el volumen de peticiones contra la API no
        # oficial de Garmin (riesgo de rate-limit ya documentado en
        # este módulo). Vive en la instancia porque el mismo
        # `GarminClient` (misma sesión logueada) se reutiliza para
        # ambas llamadas dentro de una pasada de sync.
        self._cache_body_battery: dict[str, Any] = {}
        self._cache_stress: dict[str, Any] = {}

    def login(self) -> None:
        """Un único intento de login, reutilizando el token cacheado.
        Nunca reintenta internamente: si falla, la capa llamante decide
        (backoff, esperar al día siguiente, alertar al usuario).

        `mfa_code_prompt`, si se proporciona, se pasa como `prompt_mfa`
        a la factory de `garminconnect.Garmin` - necesario para
        emparejar cuentas reales con verificación en dos pasos (Fase H)
        en una sola llamada, en vez de fallar sin más explicación."""
        kwargs_factory = {}
        if self._mfa_code_prompt is not None:
            kwargs_factory["prompt_mfa"] = self._mfa_code_prompt
        api = self._api_factory(self._email, self._password, **kwargs_factory)
        try:
            api.login(self._token_store_dir)
        except Exception as exc:
            mensaje = _sanitizar_mensaje(str(exc), self._password)
            if _es_error_de_rate_limit(exc):
                raise GarminRateLimitedError(mensaje) from exc
            raise GarminAuthError(mensaje) from exc
        self._api = api

    def get_daily_recovery_raw(self, date_str: str) -> dict[str, Any]:
        """Obtiene y normaliza los campos de recuperación del día, más
        el payload crudo completo bajo `raw_json` para auditoría y
        posible reprocesado si cambia la lógica de negocio.

        `date_str` debe tener formato ISO YYYY-MM-DD; se valida aquí
        para dar un error claro en vez de un InsufficientDataError
        engañoso más abajo si el formato fuera inválido.

        Épica A del plan de expansión (02-roadmap/03-vision-produccion.md):
        además de los 4 campos originales (hrv, training_readiness,
        body_battery, sleep), ahora también se piden hrv_status, stress
        medio, resting HR y VO2max - las columnas ya existían en
        `GarminDailyMetrics` desde el principio pero nunca se
        rellenaban porque este cliente nunca las pedía. Mismo principio
        que el resto de este método: una llamada por campo, un fallo
        puntual nunca tumba a las demás.
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
        raw_body_battery = self._get_body_battery_raw_cacheado(date_str)
        raw_sleep = self._llamada_segura(self._api.get_sleep_data, date_str)
        raw_stress = self._get_stress_raw_cacheado(date_str)
        raw_rhr = self._llamada_segura(self._api.get_rhr_day, date_str)
        raw_max_metrics = self._llamada_segura(self._api.get_max_metrics, date_str)

        return {
            "hrv_today": _extraer_hrv(raw_hrv),
            "hrv_status": _extraer_hrv_status(raw_hrv),
            "training_readiness": _extraer_training_readiness(raw_readiness),
            "body_battery_am": _extraer_body_battery(raw_body_battery),
            "sleep_score": _extraer_sleep_score(raw_sleep),
            "stress_avg": _extraer_stress_avg(raw_stress),
            "resting_hr": _extraer_resting_hr(raw_rhr),
            "vo2max": _extraer_vo2max(raw_max_metrics),
            "raw_json": {
                "hrv": raw_hrv,
                "training_readiness": raw_readiness,
                "body_battery": raw_body_battery,
                "sleep": raw_sleep,
                "stress": raw_stress,
                "rhr": raw_rhr,
                "max_metrics": raw_max_metrics,
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

    def _get_body_battery_raw_cacheado(self, date_str: str) -> Any:
        """Ver comentario de `_cache_body_battery` en `__init__`: evita
        una segunda llamada de red idéntica cuando `get_daily_recovery_raw`
        y `get_intraday_series_raw` piden el mismo día."""
        if date_str not in self._cache_body_battery:
            self._cache_body_battery[date_str] = self._llamada_segura(
                self._api.get_body_battery, date_str
            )
        return self._cache_body_battery[date_str]

    def _get_stress_raw_cacheado(self, date_str: str) -> Any:
        if date_str not in self._cache_stress:
            self._cache_stress[date_str] = self._llamada_segura(self._api.get_stress_data, date_str)
        return self._cache_stress[date_str]

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

    def get_user_profile_raw(self) -> dict[str, Any]:
        """Perfil básico del usuario (nombre, altura, peso, fecha de
        nacimiento, sexo) - Épica de conexión Garmin desde la propia app
        (petición explícita del usuario: "sin cuenta local, que al
        conectar Garmin se saquen esos datos de ahí" en vez de un
        formulario manual de onboarding).

        Verificado contra el JSON real de una cuenta Garmin real (no solo
        contra la firma pública de la librería): `get_user_profile()`
        expone estos campos bajo `userData`, en gramos/cm/ISO-date;
        `get_full_name()` es una llamada aparte para el nombre a mostrar.
        Gramos -> kg dividiendo entre 1000 (mismo criterio que el resto
        de la app, que trabaja en kg).

        "unknown is not zero": cualquier campo ausente o `None` en el
        payload de Garmin se propaga como `None`, nunca como un 0/fecha
        inventada - la capa llamante (onboarding) decide qué hacer con
        un perfil incompleto (pedir el campo que falte, nunca los que sí
        vinieron)."""
        if self._api is None:
            raise RuntimeError("login() debe llamarse antes de sincronizar datos")

        nombre = self._api.get_full_name()
        datos = (self._api.get_user_profile() or {}).get("userData") or {}

        genero = datos.get("gender")
        sexo = {"MALE": "M", "FEMALE": "F"}.get(genero) if genero else None
        peso_g = datos.get("weight")

        return {
            "nombre": nombre,
            "sexo": sexo,
            "altura_cm": datos.get("height"),
            "peso_kg": (peso_g / 1000) if peso_g is not None else None,
            "fecha_nacimiento": datos.get("birthDate"),
        }

    def get_intraday_series_raw(self, date_str: str) -> dict[str, list[tuple[int, float]]]:
        """Serie minuto a minuto de ritmo cardíaco, body battery y estrés
        de `date_str` - petición explícita del usuario: "el ritmo
        cardiaco, body battery, etc son valores que cambian cada
        minuto, quiero todo ese histórico, no me vale que cojas la
        media del día". Complementa a `get_daily_recovery_raw`, que
        solo persiste un valor agregado por día.

        Cada métrica es una llamada independiente y se degrada por
        separado (mismo principio que `get_daily_recovery_raw`): un
        fallo puntual en una métrica no debe impedir obtener las demás.

        Formas verificadas contra el JSON real de una cuenta Garmin
        real:
        - `get_heart_rates(date)` -> dict con `heartRateValues`:
          lista de `[timestamp_ms, bpm]`.
        - `get_body_battery(date)` -> LISTA (no dict) de un elemento
          por día, con `bodyBatteryValuesArray`: lista de
          `[timestamp_ms, nivel]`.
        - `get_stress_data(date)` -> dict con `stressValuesArray`:
          lista de `[timestamp_ms, nivel]`, con -1/-2 como centinela de
          "sin datos suficientes ese minuto" - estos puntos se
          DESCARTAN aquí ("unknown is not zero": un hueco en la serie
          es honesto, un -1 mostrado como estrés real no lo es).

        `body_battery`/`stress` usan la caché por-fecha de
        `_get_body_battery_raw_cacheado`/`_get_stress_raw_cacheado`
        (hallazgo de code-review): si `get_daily_recovery_raw` ya pidió
        el mismo día en esta misma sesión, se reutiliza el payload en
        vez de repetir la llamada de red - reduce el riesgo de
        rate-limit sin perder ningún dato (el payload ya trae el array
        intradía completo)."""
        if self._api is None:
            raise RuntimeError("login() debe llamarse antes de sincronizar datos")
        try:
            date.fromisoformat(date_str)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"date_str debe tener formato ISO YYYY-MM-DD, recibido: {date_str!r}"
            ) from exc

        raw_hr = self._llamada_segura(self._api.get_heart_rates, date_str)
        raw_body_battery = self._get_body_battery_raw_cacheado(date_str)
        raw_stress = self._get_stress_raw_cacheado(date_str)

        return {
            "heart_rate": _extraer_serie(raw_hr, "heartRateValues"),
            "body_battery": _extraer_serie_body_battery(raw_body_battery),
            "stress": _extraer_serie(raw_stress, "stressValuesArray", descartar_negativos=True),
        }
