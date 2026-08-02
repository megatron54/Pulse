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
    planned_session: _SessionTypeLiteral
    acwr_history: list[float] | None = None
    days_to_competition: int | None = None


class DailySessionOut(BaseModel):
    session_type: str
    volume_pct: int
    intensity_rpe_cap: int | None
    narrative_text: str
    narrative_source: str
