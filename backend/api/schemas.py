"""Esquemas Pydantic de request/response de la API. Capa de
serialización pura: sin lógica de negocio, todo delega en services/*."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

_FasePeso = Literal["cut", "maintenance", "recomp", "surplus"]
_SessionTypeLiteral = Literal[
    "rest",
    "active_recovery",
    "strength_heavy",
    "strength_hypertrophy",
    "endurance_intervals",
    "endurance_long",
    "martial_arts_technical",
    "martial_arts_sparring",
]


class UserCreateRequest(BaseModel):
    nombre: str
    altura_cm: float = Field(gt=0)
    fecha_nacimiento: date
    sexo: str = Field(pattern="^[MF]$")
    fase_peso_actual: _FasePeso = "maintenance"


class UserOut(BaseModel):
    id: int
    nombre: str
    altura_cm: float
    fecha_nacimiento: date
    sexo: str
    fase_peso_actual: str

    model_config = {"from_attributes": True}


class BodyMeasurementCreateRequest(BaseModel):
    target_date: date
    peso_kg: float = Field(gt=0)
    cuello_cm: float | None = Field(default=None, gt=0)
    cintura_cm: float | None = Field(default=None, gt=0)
    cadera_cm: float | None = Field(default=None, gt=0)


class BodyMeasurementOut(BaseModel):
    id: int
    fecha: date
    peso_kg: float
    metodo: str
    bodyfat_pct_rango_min: float | None
    bodyfat_pct_rango_max: float | None

    model_config = {"from_attributes": True}


class NutritionTargetRequest(BaseModel):
    target_date: date
    factor_actividad: float = 1.55


class NutritionTargetOut(BaseModel):
    kcal_objetivo: float
    proteina_g: float
    carbohidratos_g: float
    grasa_g: float
    fase_aplicada: str
    deficit_pausado_por_guardrail: bool


class ManualReadinessRequest(BaseModel):
    target_date: date
    hrv_today: float = Field(gt=0)
    hrv_baseline_28d: float = Field(gt=0)
    hrv_trend_7d: float
    body_battery_am: int = Field(ge=0, le=100)
    training_readiness: Literal["high", "moderate", "low", "very_low"]
    sleep_score: int = Field(ge=0, le=100)
    acwr: float = Field(ge=0)
    joint_pain_flag: bool = False


class ReadinessOut(BaseModel):
    id: int
    fecha: date
    resultado: str
    hrv_delta_pct: float | None
    training_readiness: str | None
    acwr: float | None

    model_config = {"from_attributes": True}


class DailySessionRequest(BaseModel):
    target_date: date
    planned_session: _SessionTypeLiteral | None = None
    acwr_history: list[float] | None = None
    days_to_competition: int | None = None


class DailySessionOut(BaseModel):
    session_type: str
    volume_pct: int
    intensity_rpe_cap: int | None
    narrative_text: str
    narrative_source: str


class TrainingLoadOut(BaseModel):
    acute_avg_7d: float | None
    chronic_avg_28d: float | None
    acwr: float | None
    dias_con_dato_agudo: int
    dias_con_dato_cronico: int
    datos_suficientes: bool

    model_config = {"from_attributes": True}


_DiaSemana = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class TrainingBlockCreateRequest(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    objetivo_prioritario: str
    objetivos_mantenimiento: list[str] = []
    weekly_schedule: dict[_DiaSemana, _SessionTypeLiteral] = {}


class TrainingBlockOut(BaseModel):
    id: int
    fecha_inicio: date
    fecha_fin: date
    objetivo_prioritario: str
    semana_actual: int
    es_deload: bool

    model_config = {"from_attributes": True}


class ExerciseCategoryOut(BaseModel):
    id: int
    name: str


class EquipmentOut(BaseModel):
    id: int
    name: str


class ExerciseOut(BaseModel):
    id: int
    nombre: str
    categoria: str
    equipamiento: list[str]


class WgerTokenRequest(BaseModel):
    token: str


class IngredientOut(BaseModel):
    id: int
    nombre: str
    kcal_100g: float
    proteina_100g_g: float
    carbohidratos_100g_g: float
    grasa_100g_g: float


class FoodLogEntryRequest(BaseModel):
    ingredient_id: int
    # gt=0: 0/negativo no tiene sentido para una cantidad de comida.
    # le=9999: límite real del formato `decimal` que exige el schema de
    # wger (`^-?\d{0,4}(?:\.\d{0,2})?$`, máx. 4 dígitos enteros) -
    # hallazgo de code-review: sin este límite, un valor >9999g pasaba
    # el 422 de Pulse y llegaba a wger como un 400 confuso convertido
    # en un 502 opaco.
    amount_grams: float = Field(gt=0, le=9999)


class FoodLogEntryOut(BaseModel):
    ingredient_id: int
    nombre: str
    amount_grams: float
    kcal: float
    proteina_g: float
    carbohidratos_g: float
    grasa_g: float

    model_config = {"from_attributes": True}


class DailyFoodLogOut(BaseModel):
    entradas: list[FoodLogEntryOut]
    kcal_total: float
    proteina_g_total: float
    carbohidratos_g_total: float
    grasa_g_total: float
    entradas_omitidas: int

    model_config = {"from_attributes": True}


Habito = Literal[
    "alcohol",
    "cafeina_tarde",
    "comida_tardia",
    "estres_alto",
    "siesta",
    "ayuno_intermitente",
    "doble_sesion",
    "viaje",
]
"""Catálogo cerrado de hábitos - debe coincidir exactamente con
`_HABITO_VALORES` en `models.schema`. Exportado (sin prefijo `_`, a
diferencia de los demás Literal de este módulo) porque
`api.routers.habits.get_habit_correlation` también lo usa para validar
el query param `habito` (hallazgo HIGH de code-review: sin este tipo,
un valor fuera de catálogo devolvía 200 con datos vacíos en vez de
422)."""


class SetHabitsRequest(BaseModel):
    habitos: list[Habito]


class HabitCorrelationOut(BaseModel):
    habito: str
    dias_con_habito_con_dato: int
    dias_sin_habito_con_dato: int
    pct_red_con_habito: float | None
    pct_red_sin_habito: float | None
    datos_suficientes: bool

    model_config = {"from_attributes": True}
