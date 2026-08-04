"""Tests de integración del router de ejercicios (catálogo de wger) —
TDD. A diferencia del resto de la API, este router no toca la base de
datos de Pulse en absoluto - es un proxy fino sobre wger_client, así
que los tests inyectan un WgerClient doble en vez de crear un usuario/
engine SQLite."""
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_wger_client
from api.main import app
from wger_client.client import WgerAuthError, WgerRequestError


class _WgerClientDoble:
    def __init__(self):
        self.categorias = [{"id": 10, "name": "Abs"}, {"id": 9, "name": "Legs"}]
        self.equipamiento = [{"id": 1, "name": "Barbell"}]
        self.ejercicios = [
            {"id": 9, "nombre": "Squat", "categoria": "Legs", "equipamiento": ["Barbell"]}
        ]
        self.excepcion_a_lanzar: Exception | None = None

    def get_exercise_categories(self):
        if self.excepcion_a_lanzar:
            raise self.excepcion_a_lanzar
        return self.categorias

    def get_equipment(self):
        if self.excepcion_a_lanzar:
            raise self.excepcion_a_lanzar
        return self.equipamiento

    def search_exercises(self, category_id, language, limit=50):
        if self.excepcion_a_lanzar:
            raise self.excepcion_a_lanzar
        return self.ejercicios


@pytest.fixture()
def wger_doble():
    return _WgerClientDoble()


@pytest.fixture()
def client(wger_doble):
    app.dependency_overrides[get_wger_client] = lambda: wger_doble
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetExerciseCategories:
    def test_devuelve_las_categorias_del_doble(self, client):
        resp = client.get("/exercises/categories")
        assert resp.status_code == 200
        assert resp.json() == [{"id": 10, "name": "Abs"}, {"id": 9, "name": "Legs"}]

    def test_error_de_conexion_con_wger_da_502(self, client, wger_doble):
        wger_doble.excepcion_a_lanzar = WgerRequestError("wger caído")
        resp = client.get("/exercises/categories")
        assert resp.status_code == 502

    def test_error_de_auth_con_wger_da_502(self, client, wger_doble):
        # WgerAuthError también se mapea a 502: es un fallo del proxy
        # hacia wger, no un fallo de autenticación del propio cliente
        # de Pulse contra su API (eso lo gestiona verify_api_key aparte).
        wger_doble.excepcion_a_lanzar = WgerAuthError("wger rechazó la petición")
        resp = client.get("/exercises/categories")
        assert resp.status_code == 502


class TestGetEquipment:
    def test_devuelve_el_equipamiento_del_doble(self, client):
        resp = client.get("/exercises/equipment")
        assert resp.status_code == 200
        assert resp.json() == [{"id": 1, "name": "Barbell"}]

    def test_error_de_wger_da_502(self, client, wger_doble):
        wger_doble.excepcion_a_lanzar = WgerRequestError("wger caído")
        resp = client.get("/exercises/equipment")
        assert resp.status_code == 502


class TestSearchExercises:
    def test_devuelve_ejercicios_aplanados(self, client):
        resp = client.get("/exercises/search", params={"category_id": 9, "language": 2})
        assert resp.status_code == 200
        assert resp.json() == [
            {"id": 9, "nombre": "Squat", "categoria": "Legs", "equipamiento": ["Barbell"]}
        ]

    def test_categoria_sin_ejercicios_devuelve_lista_vacia_no_un_error(self, client, wger_doble):
        # Load-bearing assumption del diseño de errores (code-review):
        # un category_id inexistente/sin resultados en wger es un
        # filtro DRF vacío (200 con results:[]), nunca un error - por
        # eso este router no distingue "categoría no encontrada" de
        # "categoría vacía", ambas devuelven [] con 200.
        wger_doble.ejercicios = []
        resp = client.get("/exercises/search", params={"category_id": 9999, "language": 2})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_error_de_wger_da_502(self, client, wger_doble):
        wger_doble.excepcion_a_lanzar = WgerRequestError("wger caído")
        resp = client.get("/exercises/search", params={"category_id": 9, "language": 2})
        assert resp.status_code == 502

    def test_category_id_es_obligatorio(self, client):
        resp = client.get("/exercises/search", params={"language": 2})
        assert resp.status_code == 422

    def test_language_por_defecto_es_ingles(self, client, wger_doble, monkeypatch):
        capturado = {}

        def search_exercises_espia(category_id, language, limit=50):
            capturado["language"] = language
            return wger_doble.ejercicios

        monkeypatch.setattr(wger_doble, "search_exercises", search_exercises_espia)
        resp = client.get("/exercises/search", params={"category_id": 9})
        assert resp.status_code == 200
        assert capturado["language"] == 2
