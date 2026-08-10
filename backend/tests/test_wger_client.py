"""Tests para wger_client.client — TDD.

Fase E del plan autónomo: cliente HTTP fino sobre la API REST pública
de wger (ya expuesta por el contenedor `web`, ver
infra/wger-docker/README o docker-compose), en vez de tocar su base de
datos directamente (misma separación de esquemas decidida en la Fase 0).

Mismo patrón de inyección de dependencias que garmin_sync.client: el
cliente HTTP (`httpx.Client`) se inyecta vía `http_client_factory`, para
poder testear sin red real ni un wger corriendo. Verificado a mano
contra una instancia real de wger en localhost antes de escribir estos
tests (ver docstring del módulo de producción para las respuestas
reales observadas).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from wger_client.client import WgerAuthError, WgerClient, WgerRequestError


def _fake_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


class TestGetExerciseCategories:
    def test_devuelve_la_lista_de_categorias(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "count": 2,
                "next": None,
                "results": [{"id": 10, "name": "Abs"}, {"id": 9, "name": "Legs"}],
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        categorias = client.get_exercise_categories()

        assert categorias == [{"id": 10, "name": "Abs"}, {"id": 9, "name": "Legs"}]
        fake_http.get.assert_called_once_with(
            "http://localhost/api/v2/exercisecategory/", params={"format": "json"}
        )

    def test_error_5xx_se_traduce_a_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(503)
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_exercise_categories()

    def test_error_401_se_traduce_a_wgerautherror(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(401)
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerAuthError):
            client.get_exercise_categories()


class TestGetEquipment:
    def test_devuelve_la_lista_de_equipamiento(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200, {"count": 1, "next": None, "results": [{"id": 1, "name": "Barbell"}]}
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        equipamiento = client.get_equipment()

        assert equipamiento == [{"id": 1, "name": "Barbell"}]


class TestSearchExercises:
    def test_normaliza_los_campos_relevantes_del_payload_real_de_exerciseinfo(self):
        """El payload real de /exerciseinfo/ es profundamente anidado
        (category, equipment, translations por idioma...). Este cliente
        NUNCA debe exponer ese JSON crudo al resto de Pulse: lo aplana a
        los campos que session_service podría necesitar, mismo
        principio de traducción explícita que garmin_sync.mapper."""
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "count": 1,
                "next": None,
                "results": [
                    {
                        "id": 9,
                        "category": {"id": 10, "name": "Abs"},
                        "equipment": [{"id": 10, "name": "Kettlebell"}],
                        "muscles": [],
                        "translations": [
                            {"language": 2, "name": "2 Handed Kettlebell Swing"},
                            {"language": 1, "name": "KB Schwung"},
                        ],
                    }
                ],
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        ejercicios = client.search_exercises(category_id=10, language=2)

        assert ejercicios == [
            {
                "id": 9,
                "nombre": "2 Handed Kettlebell Swing",
                "categoria": "Abs",
                "equipamiento": ["Kettlebell"],
            }
        ]

    def test_pasa_category_id_y_language_como_query_params(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200, {"count": 0, "next": None, "results": []}
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        client.search_exercises(category_id=10, language=2)

        fake_http.get.assert_called_once_with(
            "http://localhost/api/v2/exerciseinfo/",
            params={"format": "json", "category": 10, "language": 2, "limit": 50},
        )

    def test_sin_traduccion_para_el_idioma_pedido_usa_id_como_nombre_de_respaldo(self):
        """Principio "unknown is not zero": si no hay traducción para el
        idioma solicitado, no se debe romper ni inventar un nombre -
        se usa un marcador explícito con el id, nunca una cadena vacía
        que pueda confundirse con un ejercicio real sin nombre."""
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "count": 1,
                "next": None,
                "results": [
                    {
                        "id": 42,
                        "category": {"id": 9, "name": "Legs"},
                        "equipment": [],
                        "translations": [{"language": 1, "name": "Kniebeuge"}],
                    }
                ],
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        ejercicios = client.search_exercises(category_id=9, language=2)

        assert ejercicios[0]["nombre"] == "[sin traducción - id 42]"

    def test_error_de_conexion_se_traduce_a_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.get.side_effect = httpx.ConnectError("no se pudo conectar")
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.search_exercises(category_id=10, language=2)

    def test_ejercicio_sin_id_ni_categoria_se_omite_sin_tumbar_la_busqueda(self):
        """Regresión de code-review (MEDIUM): un ejercicio malformado en
        el resultado no debe tumbar toda la búsqueda - se omite y el
        resto se devuelve normalmente."""
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "count": 2,
                "next": None,
                "results": [
                    {"translations": []},  # sin id ni category -> se omite
                    {
                        "id": 7,
                        "category": {"id": 9, "name": "Legs"},
                        "equipment": [],
                        "translations": [{"language": 2, "name": "Squat"}],
                    },
                ],
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        ejercicios = client.search_exercises(category_id=9, language=2)

        assert len(ejercicios) == 1
        assert ejercicios[0]["nombre"] == "Squat"


class TestContratoDeErroresDeLaEnvoltura:
    """El contrato de esta clase es que SOLO WgerAuthError/WgerRequestError
    escapan al llamante, nunca un KeyError/ValueError crudo de un
    payload con forma inesperada (regresión de code-review, MEDIUM)."""

    def test_respuesta_200_sin_clave_results_se_traduce_a_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(200, {"detail": "algo distinto"})
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_exercise_categories()

    def test_cuerpo_no_json_se_traduce_a_wgerrequesterror(self):
        fake_http = MagicMock()
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.side_effect = ValueError("no es JSON válido")
        fake_http.get.return_value = resp
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_exercise_categories()

