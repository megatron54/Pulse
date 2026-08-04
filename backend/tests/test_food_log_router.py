"""Tests de integración del router de food-log — TDD. Mezcla base de
datos SQLite real (para WgerCredentials, patrón estándar de la API) con
un WgerClient doble inyectado vía dependency_overrides (patrón ya
establecido en test_exercises_router.py)."""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db, get_wger_client
from api.main import app
from models.schema import Base


class _WgerClientDoble:
    def __init__(self):
        self.ingredientes_busqueda = [
            {"id": 2, "nombre": "Pollo", "kcal_100g": 165.0, "proteina_100g_g": 31.0,
             "carbohidratos_100g_g": 0.0, "grasa_100g_g": 3.6}
        ]
        self.diario = []
        self.ingredientes = {
            2: {"id": 2, "nombre": "Pollo", "kcal_100g": 165.0, "proteina_100g_g": 31.0,
                "carbohidratos_100g_g": 0.0, "grasa_100g_g": 3.6}
        }
        self.excepcion_a_lanzar: Exception | None = None

    def search_ingredients(self, query, language, limit=20):
        if self.excepcion_a_lanzar:
            raise self.excepcion_a_lanzar
        return self.ingredientes_busqueda

    def log_food_diary_entry(self, token, ingredient_id, amount_grams, target_datetime=None):
        if self.excepcion_a_lanzar:
            raise self.excepcion_a_lanzar
        self.diario.append({"ingredient": ingredient_id, "amount": str(amount_grams)})
        return {"id": "uuid-1", "ingredient": ingredient_id, "amount": str(amount_grams)}

    def get_food_diary(self, token, target_date):
        if self.excepcion_a_lanzar:
            raise self.excepcion_a_lanzar
        return self.diario

    def get_ingredient(self, ingredient_id):
        return self.ingredientes[ingredient_id]


@pytest.fixture()
def wger_doble():
    return _WgerClientDoble()


@pytest.fixture()
def client(wger_doble):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_wger_client] = lambda: wger_doble
    yield TestClient(app)
    app.dependency_overrides.clear()


def _crear_usuario(client):
    resp = client.post(
        "/users",
        json={
            "nombre": "Test",
            "altura_cm": 180,
            "fecha_nacimiento": "1995-01-01",
            "sexo": "M",
            "fase_peso_actual": "maintenance",
        },
    )
    return resp.json()


class TestSaveWgerToken:
    def test_guarda_el_token_y_no_lo_devuelve_en_la_respuesta(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-secreto"}
        )
        assert resp.status_code == 204
        assert resp.text == ""

    def test_usuario_inexistente_da_404(self, client):
        # MEDIUM-2 de code-review: sin esta validación, en Postgres real
        # esto habría escapado como un 500 (IntegrityError de FK) en vez
        # de un 404 limpio.
        resp = client.post("/users/9999/nutrition/wger-token", json={"token": "tok"})
        assert resp.status_code == 404


class TestSearchIngredients:
    def test_busca_ingredientes_sin_necesitar_token(self, client):
        resp = client.get("/users/1/nutrition/ingredients/search", params={"query": "pollo"})
        assert resp.status_code == 200
        assert resp.json()[0]["nombre"] == "Pollo"


class TestCreateFoodLogEntry:
    def test_registra_la_comida_tras_guardar_el_token(self, client):
        usuario = _crear_usuario(client)
        client.post(f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-abc"})
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 150},
        )
        assert resp.status_code == 201

    def test_sin_token_configurado_da_404(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 150},
        )
        assert resp.status_code == 404

    def test_usuario_inexistente_da_404(self, client):
        resp = client.post(
            "/users/9999/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 150},
        )
        assert resp.status_code == 404

    def test_fallo_de_wger_da_502(self, client, wger_doble):
        from wger_client.client import WgerRequestError

        usuario = _crear_usuario(client)
        client.post(f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-abc"})
        wger_doble.excepcion_a_lanzar = WgerRequestError("wger caído")
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 150},
        )
        assert resp.status_code == 502

    def test_token_invalido_da_401_no_502(self, client, wger_doble):
        from wger_client.client import WgerAuthError

        usuario = _crear_usuario(client)
        client.post(f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-caducado"})
        wger_doble.excepcion_a_lanzar = WgerAuthError("token inválido")
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 150},
        )
        assert resp.status_code == 401

    def test_amount_grams_mayor_que_9999_da_422(self, client):
        # Q3 de code-review: 9999g es el máximo real que admite el
        # formato `decimal` de wger (^-?\d{0,4}...) - por encima de eso
        # debe rechazarse en el borde (422), no llegar a wger y volver
        # como un 502 confuso.
        usuario = _crear_usuario(client)
        client.post(f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-abc"})
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 10000},
        )
        assert resp.status_code == 422

    def test_amount_grams_cero_o_negativo_da_422(self, client):
        usuario = _crear_usuario(client)
        client.post(f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-abc"})
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 0},
        )
        assert resp.status_code == 422


class TestGetFoodLog:
    def test_devuelve_el_diario_del_dia_con_totales(self, client, wger_doble):
        usuario = _crear_usuario(client)
        client.post(f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-abc"})
        client.post(
            f"/users/{usuario['id']}/nutrition/food-log",
            json={"ingredient_id": 2, "amount_grams": 150},
        )

        resp = client.get(
            f"/users/{usuario['id']}/nutrition/food-log", params={"date": "2026-08-04"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["kcal_total"] == pytest.approx(247.5)
        assert len(body["entradas"]) == 1
        assert body["entradas"][0]["nombre"] == "Pollo"

    def test_sin_token_configurado_da_404(self, client):
        usuario = _crear_usuario(client)
        resp = client.get(
            f"/users/{usuario['id']}/nutrition/food-log", params={"date": "2026-08-04"}
        )
        assert resp.status_code == 404

    def test_token_invalido_da_401_no_502(self, client, wger_doble):
        from wger_client.client import WgerAuthError

        usuario = _crear_usuario(client)
        client.post(f"/users/{usuario['id']}/nutrition/wger-token", json={"token": "tok-caducado"})
        wger_doble.excepcion_a_lanzar = WgerAuthError("token inválido")
        resp = client.get(
            f"/users/{usuario['id']}/nutrition/food-log", params={"date": "2026-08-04"}
        )
        assert resp.status_code == 401
