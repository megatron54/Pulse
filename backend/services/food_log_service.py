"""Orquesta el diario de comidas real del usuario, vía SU PROPIO wger
(petición explícita del usuario: "quiero input diario" en la página de
Nutrición - ver 02-roadmap/03-vision-produccion.md, épica de food log).

Conecta: WgerCredentials (token permanente, nunca la contraseña del
usuario) -> WgerClient.log_food_diary_entry/get_food_diary (el diario
real vive en wger, Pulse no lo duplica) -> WgerClient.get_ingredient
(una entrada del diario de wger solo trae `ingredient` + `amount`, así
que hay que resolver cada ingrediente para calcular macros) -> totales
del día.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from models.schema import AuditLog, UserProfile
from repositories.wger_credentials_repository import get_active_token, save_token
from services.errors import EntityNotFoundError
from wger_client.client import WgerClient, WgerRequestError


@dataclass(frozen=True)
class FoodLogEntry:
    ingredient_id: int
    nombre: str
    amount_grams: float
    kcal: float
    proteina_g: float
    carbohidratos_g: float
    grasa_g: float


@dataclass(frozen=True)
class DailyFoodLog:
    entradas: list[FoodLogEntry]
    kcal_total: float
    proteina_g_total: float
    carbohidratos_g_total: float
    grasa_g_total: float
    # Ingredientes del diario de wger que no se pudieron resolver
    # (borrados, datos incompletos) - aislamiento por-item: no impiden
    # ver el resto del día, pero se cuentan para que la UI pueda avisar
    # de que el total podría estar incompleto.
    entradas_omitidas: int = field(default=0)


def _token_o_lanzar(session: Session, user_id: int) -> str:
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")
    token = get_active_token(session, user_id)
    if token is None:
        raise EntityNotFoundError(
            f"user_id={user_id} no tiene credenciales de wger configuradas - "
            "guarda tu token permanente de wger primero"
        )
    return token


def save_wger_token(session: Session, user_id: int, token: str) -> None:
    """Valida que el usuario exista antes de guardar (hallazgo de
    code-review MEDIUM-2: sin esto, en SQLite se creaba una fila
    huérfana en silencio, y en Postgres real un `IntegrityError` de FK
    escapaba como 500 sin traducir) y deja rastro en `AuditLog` (Q2 de
    code-review: "si no se puede auditar, no se puede confiar" -
    NUNCA se audita el valor del token en sí, solo el hecho de que se
    guardó/reemplazó uno)."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")
    save_token(session, user_id, token)
    session.add(
        AuditLog(
            user_id=user_id,
            modulo="wger_credentials",
            inputs_json={},
            regla_disparada="save_wger_token",
            output="token_guardado",
            decision_final="Token de wger guardado/reemplazado para este usuario",
        )
    )
    session.commit()


def log_food_entry(
    session: Session,
    user_id: int,
    ingredient_id: int,
    amount_grams: float,
    wger: WgerClient,
) -> None:
    """Registra una comida en el diario REAL de wger del usuario (no en
    la base de datos de Pulse - wger es la única fuente de verdad del
    diario, mismo principio arquitectónico que ya rige la integración
    de ejercicios: Pulse consume la API de wger, nunca duplica sus
    datos)."""
    token = _token_o_lanzar(session, user_id)
    wger.log_food_diary_entry(token=token, ingredient_id=ingredient_id, amount_grams=amount_grams)


def get_daily_food_log(
    session: Session, user_id: int, target_date: date, wger: WgerClient
) -> DailyFoodLog:
    token = _token_o_lanzar(session, user_id)
    diario_crudo = wger.get_food_diary(token=token, target_date=target_date.isoformat())

    entradas: list[FoodLogEntry] = []
    omitidas = 0
    for fila in diario_crudo:
        try:
            ingredient_id = fila["ingredient"]
            amount_grams = float(fila["amount"])
            ingrediente = wger.get_ingredient(ingredient_id)
        except (WgerRequestError, KeyError, TypeError, ValueError):
            # Aislamiento por-item: un ingrediente borrado o con datos
            # incompletos en wger no debe tumbar la vista del resto del
            # día - se cuenta como omitido en vez de fabricar sus macros.
            #
            # DELIBERADAMENTE no se captura `WgerAuthError` aquí
            # (code-review, decisión A): si el token ya no es válido,
            # TODAS las llamadas siguientes van a fallar igual - aislar
            # esta por-item solo produciría N omisiones inútiles en vez
            # de una señal clara. Se deja propagar para que el router
            # (api/routers/food_log.py) la mapee a 401 explícito
            # ("tu token ya no es válido"), no a un 502 genérico ni a
            # una lista de comidas silenciosamente incompleta.
            omitidas += 1
            continue

        factor = amount_grams / 100
        entradas.append(
            FoodLogEntry(
                ingredient_id=ingredient_id,
                nombre=ingrediente["nombre"],
                amount_grams=amount_grams,
                kcal=ingrediente["kcal_100g"] * factor,
                proteina_g=ingrediente["proteina_100g_g"] * factor,
                carbohidratos_g=ingrediente["carbohidratos_100g_g"] * factor,
                grasa_g=ingrediente["grasa_100g_g"] * factor,
            )
        )

    return DailyFoodLog(
        entradas=entradas,
        kcal_total=sum(e.kcal for e in entradas),
        proteina_g_total=sum(e.proteina_g for e in entradas),
        carbohidratos_g_total=sum(e.carbohidratos_g for e in entradas),
        grasa_g_total=sum(e.grasa_g for e in entradas),
        entradas_omitidas=omitidas,
    )
