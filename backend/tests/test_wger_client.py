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

from wger_client.client import WgerAuthError, WgerClient, WgerRequestError, _formatear_decimal


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


class TestSearchIngredients:
    def test_aplana_los_campos_de_macros_y_los_convierte_a_numero(self):
        # Hallazgo real de investigación (02-roadmap/03-vision-produccion.md,
        # verificado contra wger.de): los campos numéricos de nutrientes
        # vienen como STRINGS ("protein": "6.100") - hay que castear antes
        # de cualquier aritmética, si no, concatenación silenciosa.
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "count": 1,
                "next": None,
                "results": [
                    {
                        "id": 2751119,
                        "name": "Plant Based Caesar Dressing",
                        "energy": 367,
                        "protein": "0.667",
                        "carbohydrates": "3.330",
                        "fat": "40.000",
                        "fiber": "0.000",
                    }
                ],
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        resultado = client.search_ingredients(query="caesar", language=2)

        assert resultado == [
            {
                "id": 2751119,
                "nombre": "Plant Based Caesar Dressing",
                "kcal_100g": 367.0,
                "proteina_100g_g": 0.667,
                "carbohidratos_100g_g": 3.33,
                "grasa_100g_g": 40.0,
            }
        ]

    def test_omite_un_ingrediente_con_campos_de_macros_ausentes_o_no_numericos(self):
        # Principio "unknown is not zero": OFF tiene datos dispersos
        # (fiber/is_vegan suelen ser null, según la investigación) - un
        # ingrediente sin energy/protein/carbohydrates/fat utilizables
        # se omite en vez de fabricar un 0 que se confundiría con un
        # alimento real sin calorías.
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "count": 2,
                "next": None,
                "results": [
                    {"id": 1, "name": "Sin protein", "energy": 100, "carbohydrates": "1", "fat": "1"},
                    {
                        "id": 2,
                        "name": "Completo",
                        "energy": 100,
                        "protein": "1",
                        "carbohydrates": "1",
                        "fat": "1",
                    },
                ],
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        resultado = client.search_ingredients(query="x", language=2)

        assert len(resultado) == 1
        assert resultado[0]["id"] == 2

    def test_pasa_search_y_language_como_query_params(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200, {"count": 0, "next": None, "results": []}
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        client.search_ingredients(query="pollo", language=2, limit=10)

        fake_http.get.assert_called_once_with(
            "http://localhost/api/v2/ingredientinfo/",
            params={"format": "json", "search": "pollo", "language": 2, "limit": 10},
        )


class TestGetIngredient:
    def test_devuelve_el_ingrediente_aplanado_por_id(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "id": 2751119,
                "name": "Plant Based Caesar Dressing",
                "energy": 367,
                "protein": "0.667",
                "carbohydrates": "3.330",
                "fat": "40.000",
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        resultado = client.get_ingredient(ingredient_id=2751119)

        assert resultado == {
            "id": 2751119,
            "nombre": "Plant Based Caesar Dressing",
            "kcal_100g": 367.0,
            "proteina_100g_g": 0.667,
            "carbohidratos_100g_g": 3.33,
            "grasa_100g_g": 40.0,
        }
        fake_http.get.assert_called_once_with(
            "http://localhost/api/v2/ingredientinfo/2751119/", params={"format": "json"}
        )

    def test_ingrediente_con_macros_ausentes_da_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(200, {"id": 1, "name": "Incompleto"})
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_ingredient(ingredient_id=1)


class TestFoodDiary:
    def test_log_food_diary_entry_envia_authorization_token(self):
        fake_http = MagicMock()
        fake_http.post.return_value = _fake_response(
            201, {"id": "uuid-1", "ingredient": 42, "amount": "150.00"}
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        client.log_food_diary_entry(token="tok-abc", ingredient_id=42, amount_grams=150)

        _url, kwargs = fake_http.post.call_args
        assert kwargs["headers"]["Authorization"] == "Token tok-abc"
        assert kwargs["json"]["ingredient"] == 42
        assert kwargs["json"]["amount"] == "150"

    def test_log_food_diary_entry_token_invalido_da_wgerautherror(self):
        fake_http = MagicMock()
        fake_http.post.return_value = _fake_response(401, {"detail": "no autorizado"})
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerAuthError):
            client.log_food_diary_entry(token="malo", ingredient_id=1, amount_grams=100)

    def test_get_food_diary_filtra_por_fecha_y_pasa_el_token(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(
            200,
            {
                "count": 1,
                "next": None,
                "results": [{"id": "uuid-1", "ingredient": 42, "amount": "150.00"}],
            },
        )
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        resultado = client.get_food_diary(token="tok-abc", target_date="2026-08-04")

        assert resultado == [{"id": "uuid-1", "ingredient": 42, "amount": "150.00"}]
        _url, kwargs = fake_http.get.call_args
        assert kwargs["headers"]["Authorization"] == "Token tok-abc"
        assert kwargs["params"]["datetime__date"] == "2026-08-04"

    def test_log_food_diary_entry_incluye_datetime_si_se_pasa_explicito(self):
        fake_http = MagicMock()
        fake_http.post.return_value = _fake_response(201, {"id": "uuid-1"})
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        client.log_food_diary_entry(
            token="tok", ingredient_id=1, amount_grams=100, target_datetime="2026-08-04T08:00:00"
        )

        _url, kwargs = fake_http.post.call_args
        assert kwargs["json"]["datetime"] == "2026-08-04T08:00:00"

    def test_log_food_diary_entry_error_de_conexion_da_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.post.side_effect = httpx.ConnectError("sin red")
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.log_food_diary_entry(token="tok", ingredient_id=1, amount_grams=100)

    def test_log_food_diary_entry_error_5xx_da_wgerrequesterror(self):
        fake_http = MagicMock()
        resp = _fake_response(500, {})
        resp.text = "internal error"
        fake_http.post.return_value = resp
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.log_food_diary_entry(token="tok", ingredient_id=1, amount_grams=100)

    def test_get_food_diary_error_de_conexion_da_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.get.side_effect = httpx.ConnectError("sin red")
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_food_diary(token="tok", target_date="2026-08-04")

    def test_get_food_diary_error_401_da_wgerautherror(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(401, {})
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerAuthError):
            client.get_food_diary(token="tok-caducado", target_date="2026-08-04")

    def test_get_food_diary_error_5xx_da_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(500, {})
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_food_diary(token="tok", target_date="2026-08-04")

    def test_get_food_diary_cuerpo_no_json_da_wgerrequesterror(self):
        fake_http = MagicMock()
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.side_effect = ValueError("no es JSON")
        fake_http.get.return_value = resp
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_food_diary(token="tok", target_date="2026-08-04")

    def test_get_food_diary_sin_clave_results_da_wgerrequesterror(self):
        fake_http = MagicMock()
        fake_http.get.return_value = _fake_response(200, {"detail": "forma inesperada"})
        client = WgerClient(base_url="http://localhost", http_client=fake_http)

        with pytest.raises(WgerRequestError):
            client.get_food_diary(token="tok", target_date="2026-08-04")


class TestFormatearDecimal:
    def test_entero_no_lleva_decimales(self):
        assert _formatear_decimal(150) == "150"

    def test_decimal_se_trunca_a_dos_cifras_sin_ceros_sobrantes(self):
        assert _formatear_decimal(150.5) == "150.5"
        assert _formatear_decimal(150.25) == "150.25"
