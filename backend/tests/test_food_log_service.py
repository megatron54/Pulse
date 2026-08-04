"""Tests para services.food_log_service — TDD.

Orquesta: WgerCredentials (token del usuario) -> WgerClient (registro/
lectura del diario real en wger) -> resolución de macros por
ingrediente (una entrada del diario de wger solo trae `ingredient` +
`amount`, nunca kcal/proteína/carbohidratos/grasa directamente) ->
totales del día.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from models.schema import AuditLog, Base, UserProfile
from repositories.wger_credentials_repository import get_active_token, save_token
from services.errors import EntityNotFoundError
from services.food_log_service import get_daily_food_log, log_food_entry, save_wger_token
from wger_client.client import WgerAuthError, WgerRequestError


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def usuario(session):
    u = UserProfile(nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M")
    session.add(u)
    session.commit()
    return u


def _wger_doble():
    wger = MagicMock()
    wger.log_food_diary_entry.return_value = {"id": "uuid-1", "ingredient": 2, "amount": "150.00"}
    wger.get_food_diary.return_value = [
        {"id": "uuid-1", "ingredient": 2, "amount": "150.00"},
        {"id": "uuid-2", "ingredient": 3, "amount": "50.00"},
    ]
    wger.get_ingredient.side_effect = lambda ingredient_id: {
        2: {
            "id": 2,
            "nombre": "Pollo",
            "kcal_100g": 165.0,
            "proteina_100g_g": 31.0,
            "carbohidratos_100g_g": 0.0,
            "grasa_100g_g": 3.6,
        },
        3: {
            "id": 3,
            "nombre": "Arroz",
            "kcal_100g": 130.0,
            "proteina_100g_g": 2.7,
            "carbohidratos_100g_g": 28.0,
            "grasa_100g_g": 0.3,
        },
    }[ingredient_id]
    return wger


class TestSaveWgerTokenService:
    def test_guarda_el_token_si_el_usuario_existe(self, session, usuario):
        save_wger_token(session, usuario.id, "tok-abc")
        assert get_active_token(session, usuario.id) == "tok-abc"

    def test_usuario_inexistente_lanza_entitynotfounderror(self, session):
        with pytest.raises(EntityNotFoundError):
            save_wger_token(session, user_id=9999, token="tok-abc")

    def test_registra_en_auditlog_sin_incluir_el_valor_del_token(self, session, usuario):
        save_wger_token(session, usuario.id, "tok-secreto-no-debe-aparecer")

        auditoria = session.query(AuditLog).filter_by(modulo="wger_credentials").one()
        assert "tok-secreto-no-debe-aparecer" not in str(auditoria.inputs_json)
        assert "tok-secreto-no-debe-aparecer" not in auditoria.decision_final


class TestLogFoodEntry:
    def test_registra_la_entrada_usando_el_token_guardado(self, session, usuario):
        save_token(session, usuario.id, "tok-abc")
        wger = _wger_doble()

        log_food_entry(session, usuario.id, ingredient_id=2, amount_grams=150, wger=wger)

        wger.log_food_diary_entry.assert_called_once_with(
            token="tok-abc", ingredient_id=2, amount_grams=150
        )

    def test_sin_token_configurado_lanza_entitynotfounderror(self, session, usuario):
        wger = _wger_doble()
        with pytest.raises(EntityNotFoundError):
            log_food_entry(session, usuario.id, ingredient_id=2, amount_grams=150, wger=wger)

    def test_usuario_inexistente_lanza_entitynotfounderror(self, session):
        wger = _wger_doble()
        with pytest.raises(EntityNotFoundError):
            log_food_entry(session, user_id=9999, ingredient_id=2, amount_grams=150, wger=wger)


class TestGetDailyFoodLog:
    def test_calcula_los_totales_del_dia_resolviendo_cada_ingrediente(self, session, usuario):
        save_token(session, usuario.id, "tok-abc")
        wger = _wger_doble()

        resultado = get_daily_food_log(session, usuario.id, target_date=date(2026, 8, 4), wger=wger)

        # Pollo: 150g de 165kcal/100g = 247.5 kcal, 46.5g proteína
        # Arroz: 50g de 130kcal/100g = 65 kcal, 14g carbohidratos, 1.35g proteína
        assert resultado.kcal_total == pytest.approx(312.5)
        assert resultado.proteina_g_total == pytest.approx(46.5 + 1.35)
        assert resultado.carbohidratos_g_total == pytest.approx(14.0)
        assert len(resultado.entradas) == 2
        assert resultado.entradas[0].nombre == "Pollo"
        assert resultado.entradas[0].kcal == pytest.approx(247.5)

    def test_dia_vacio_devuelve_totales_en_cero_no_none(self, session, usuario):
        save_token(session, usuario.id, "tok-abc")
        wger = _wger_doble()
        wger.get_food_diary.return_value = []

        resultado = get_daily_food_log(session, usuario.id, target_date=date(2026, 8, 4), wger=wger)

        assert resultado.kcal_total == 0.0
        assert resultado.entradas == []

    def test_sin_token_configurado_lanza_entitynotfounderror(self, session, usuario):
        wger = _wger_doble()
        with pytest.raises(EntityNotFoundError):
            get_daily_food_log(session, usuario.id, target_date=date(2026, 8, 4), wger=wger)

    def test_un_ingrediente_que_falla_al_resolverse_no_tumba_el_resto_del_dia(self, session, usuario):
        # Aislamiento por-item (mismo principio que garmin_sync/wger_client):
        # un ingrediente borrado/con datos malos en wger no debe impedir
        # ver el resto del diario del día.
        save_token(session, usuario.id, "tok-abc")
        wger = _wger_doble()

        def get_ingredient_con_fallo(ingredient_id):
            if ingredient_id == 2:
                raise WgerRequestError("ingrediente sin macros")
            return {
                "id": 3,
                "nombre": "Arroz",
                "kcal_100g": 130.0,
                "proteina_100g_g": 2.7,
                "carbohidratos_100g_g": 28.0,
                "grasa_100g_g": 0.3,
            }

        wger.get_ingredient.side_effect = get_ingredient_con_fallo

        resultado = get_daily_food_log(session, usuario.id, target_date=date(2026, 8, 4), wger=wger)

        assert len(resultado.entradas) == 1
        assert resultado.entradas[0].nombre == "Arroz"
        assert resultado.entradas_omitidas == 1

    def test_token_invalido_a_mitad_de_dia_se_propaga_en_vez_de_aislarse(self, session, usuario):
        # Q5 de code-review: WgerAuthError NO debe tratarse como un
        # ingrediente más que se omite - si el token ya no es válido,
        # TODAS las llamadas siguientes fallarían igual, así que se deja
        # propagar para que la capa API la mapee a 401 explícito, en vez
        # de devolver una lista de comidas silenciosamente incompleta.
        save_token(session, usuario.id, "tok-caducado")
        wger = _wger_doble()
        wger.get_ingredient.side_effect = WgerAuthError("token ya no válido")

        with pytest.raises(WgerAuthError):
            get_daily_food_log(session, usuario.id, target_date=date(2026, 8, 4), wger=wger)
