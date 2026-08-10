"""Cliente HTTP fino sobre la API REST pública de wger (Fase E del plan
autónomo, docs/02-roadmap/02-plan-autonomo.md).

Decisión de arquitectura (registrada en el roadmap): Pulse consume wger
vía su API REST, NUNCA accediendo directamente a su base de datos —
mantiene la separación de esquemas ya decidida en la Fase 0 (Postgres
propio de Pulse en el puerto 5433, completamente aparte del Postgres
interno de wger).

Mismo patrón de inyección de dependencias que `garmin_sync.client`: el
cliente HTTP (`httpx.Client` o compatible - solo necesita `.get(url,
params=...)` que devuelva algo con `.status_code`/`.json()`) se inyecta
vía el parámetro `http_client`, para que los tests no necesiten red real
ni una instancia de wger corriendo.

Verificado a mano contra una instancia real de wger en `localhost`
(contenedor `wger-docker-web-1`) antes de escribir este módulo:
- El catálogo de ejercicios (`/api/v2/exercisecategory/`, `/equipment/`,
  `/exerciseinfo/`) es de LECTURA PÚBLICA, sin necesitar token.
- Los endpoints de datos por usuario (`/weightentry/`, `/nutritionplan/`,
  etc.) SÍ devuelven 403 sin autenticación - quedan fuera del alcance de
  esta primera versión del cliente (no hay flujo de login/token de wger
  todavía; se añadirá cuando Pulse necesite escribir datos en wger en
  vez de solo leer su catálogo de ejercicios).
- El payload de `/exerciseinfo/` es profundamente anidado y con
  traducciones por idioma; este cliente lo aplana a los pocos campos
  que el resto de Pulse necesita (mismo principio de traducción
  explícita que `garmin_sync.mapper` aplica al payload de Garmin) en
  vez de dejar que ese detalle de wger se filtre al resto del sistema.
"""
from __future__ import annotations

from typing import Any

import httpx

_LIMITE_POR_DEFECTO = 50
_MARCADOR_SIN_TRADUCCION = "[sin traducción - id {id}]"


class WgerAuthError(Exception):
    """La API de wger respondió 401/403 (falta autenticación o el
    recurso pedido no es de lectura pública)."""


class WgerRequestError(Exception):
    """Cualquier otro fallo de la petición: error 5xx, timeout, fallo de
    conexión, etc. No distingue más finamente porque, a diferencia de
    Garmin, wger corre en la propia infraestructura local del usuario -
    no hay política de rate-limit de un tercero que respetar aquí."""


class WgerClient:
    """Cliente de solo lectura sobre el catálogo público de ejercicios
    de wger. `base_url` debe ser la raíz del servidor wger (p.ej.
    `http://localhost`, sin `/api/v2` - este cliente añade esa parte)."""

    def __init__(self, base_url: str, http_client: httpx.Client | None = None) -> None:
        """`base_url` se asume de confianza (siempre configurado por el
        propio operador de Pulse, nunca derivado de input de un
        usuario) - no se valida esquema ni host. Si en el futuro
        `base_url` pudiera venir de una fuente no confiable, habría que
        añadir un allow-list de esquema (`http`/`https`) y host antes de
        usarlo, para evitar un vector tipo SSRF.

        Nota de diseño: a diferencia de `garmin_sync.client.GarminClient`
        (que inyecta un `api_factory` *callable*, perezoso, para evitar
        importar `garminconnect` en los tests), aquí se inyecta una
        *instancia* ya construida de `httpx.Client`. Es una idiom de DI
        distinta y deliberada: `httpx` ya es una dependencia dura de
        Pulse (usada por FastAPI/tests de la API), así que no hay nada
        que evitar importar."""
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client()

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/api/v2{path}"
        try:
            response = self._http.get(url, params={**params, "format": "json"})
        except httpx.HTTPError as exc:
            raise WgerRequestError(f"Fallo de conexión con wger: {exc}") from exc

        if response.status_code in (401, 403):
            raise WgerAuthError(
                f"wger rechazó la petición a {path} (status {response.status_code})"
            )
        if response.status_code >= 400:
            raise WgerRequestError(
                f"wger devolvió un error en {path} (status {response.status_code})"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise WgerRequestError(
                f"wger devolvió un cuerpo no-JSON en {path}: {exc}"
            ) from exc

    def _get_results(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Como `_get`, pero además garantiza que el contrato de error de
        esta clase (solo `WgerAuthError`/`WgerRequestError` escapan de
        aquí) se sostiene incluso si wger devolviera un 200 con una
        forma inesperada (sin la clave "results" de la paginación DRF
        estándar).

        Nota de alcance deliberado: solo se lee la primera página de
        resultados (no se sigue `next`). Para las categorías y el
        equipamiento esto cubre hoy el catálogo completo (~10 filas cada
        uno, muy por debajo del tamaño de página por defecto de wger).
        Para `search_exercises` se mitiga pasando un `limit` explícito
        más alto, pero una categoría con más ejercicios que ese límite
        se truncaría en silencio. Aceptable para el alcance de Fase E
        (cliente de solo lectura del catálogo); si el catálogo de wger
        creciera lo suficiente, habría que añadir seguimiento de `next`."""
        payload = self._get(path, params)
        if "results" not in payload:
            raise WgerRequestError(
                f"Respuesta inesperada de wger en {path}: falta la clave 'results'"
            )
        return payload["results"]

    def get_exercise_categories(self) -> list[dict[str, Any]]:
        """Devuelve `[{"id": ..., "name": ...}, ...]` tal cual las
        entrega wger - este payload ya es plano, no necesita traducción."""
        return self._get_results("/exercisecategory/", {})

    def get_equipment(self) -> list[dict[str, Any]]:
        """Devuelve `[{"id": ..., "name": ...}, ...]`."""
        return self._get_results("/equipment/", {})

    def search_exercises(
        self,
        category_id: int,
        language: int,
        limit: int = _LIMITE_POR_DEFECTO,
    ) -> list[dict[str, Any]]:
        """Busca ejercicios de una categoría, aplanados a los campos que
        el resto de Pulse necesita: `id`, `nombre` (traducido al idioma
        pedido), `categoria`, `equipamiento`.

        `language` sigue el id numérico de idioma de wger (2 = inglés,
        1 = alemán, etc. - ver `/api/v2/language/` en la instancia real
        para el mapeo completo; no se resuelve aquí a propósito, porque
        wger es la única fuente de verdad de esa tabla).

        Si un ejercicio individual del resultado viene con una forma
        inesperada (falta `id` o `category`), ese ejercicio se omite en
        vez de tumbar la búsqueda entera - mismo principio de
        aislamiento por-item que `garmin_sync.client._llamada_segura`
        aplica campo a campo."""
        resultados = self._get_results(
            "/exerciseinfo/",
            {"category": category_id, "language": language, "limit": limit},
        )
        ejercicios = []
        for ejercicio in resultados:
            aplanado = self._aplanar_ejercicio(ejercicio, language)
            if aplanado is not None:
                ejercicios.append(aplanado)
        return ejercicios

    @staticmethod
    def _aplanar_ejercicio(
        ejercicio: dict[str, Any], language: int
    ) -> dict[str, Any] | None:
        try:
            ejercicio_id = ejercicio["id"]
            categoria_nombre = ejercicio["category"]["name"]
        except (KeyError, TypeError):
            return None

        nombre = next(
            (
                traduccion["name"]
                for traduccion in ejercicio.get("translations", [])
                if traduccion.get("language") == language
            ),
            None,
        )
        if nombre is None:
            # Principio "unknown is not zero": nunca una cadena vacía
            # que pueda confundirse con un ejercicio real sin nombre.
            nombre = _MARCADOR_SIN_TRADUCCION.format(id=ejercicio_id)

        return {
            "id": ejercicio_id,
            "nombre": nombre,
            "categoria": categoria_nombre,
            "equipamiento": [e["name"] for e in ejercicio.get("equipment", [])],
        }
