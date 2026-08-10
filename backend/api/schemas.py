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


class GarminConnectRequest(BaseModel):
    """Alta de un usuario nuevo conectando su cuenta de Garmin
    (services.garmin_onboarding_service.connect_new_user_via_garmin).
    `email`/`password` nunca se persisten - solo viven en memoria
    durante esta petición HTTP, igual que en `garmin_pair.py`.
    `overrides` rellena ÚNICAMENTE los campos que Garmin no expuso
    (petición explícita del usuario: nunca sobreescribir un dato real
    de Garmin con uno introducido a mano)."""

    email: str
    password: str
    nombre: str | None = None
    altura_cm: float | None = Field(default=None, gt=0)
    fecha_nacimiento: date | None = None
    sexo: str | None = Field(default=None, pattern="^[MF]$")


class FeelfitConnectRequest(BaseModel):
    """Conecta la báscula Feelfit de un usuario YA EXISTENTE
    (services.feelfit_onboarding_service.connect_feelfit_account).
    `email`/`password` nunca se persisten - solo viven en memoria
    durante esta petición HTTP, igual que `GarminConnectRequest`."""

    email: str
    password: str


class FeelfitConnectOut(BaseModel):
    mediciones_importadas: int


class GarminConnectIncompleteOut(BaseModel):
    """422: Garmin no expuso todos los campos requeridos. El cliente
    debe re-enviar la misma petición con `overrides` rellenando
    SOLO estos campos - nunca los que ya vinieron de Garmin."""

    campos_faltantes: list[str]


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


_FaseNutritionPlan = Literal["cut", "maintenance", "recomp", "surplus"]


class NutritionPlanRequest(BaseModel):
    """Alta de un plan de fase de peso con duración determinada
    (petición explícita del usuario: "planes de deficit, superhabit y
    mantenimiento dedicados, con duración determinada")."""

    fase: _FaseNutritionPlan
    semanas_duracion: int = Field(gt=0, le=52)
    fecha_inicio: date
    # max_length alineado con la columna motivo=String(300) del modelo
    # (code-review: sin esto un motivo largo rompía como 500 de DB en
    # vez de un 422 limpio de validación).
    motivo: str | None = Field(default=None, max_length=300)


class NutritionPlanOut(BaseModel):
    id: int
    fase: str
    fecha_inicio: date
    semanas_duracion: int
    motivo: str | None
    activo: bool

    model_config = {"from_attributes": True}


class ActiveNutritionPlanOut(BaseModel):
    """`None` si no hay ningún plan activo - "unknown is not zero", la
    ausencia de plan es un estado real, nunca se inventa uno."""

    plan: NutritionPlanOut
    fecha_fin: date
    dias_restantes: int
    expirado: bool


class NutritionPhaseRecommendationOut(BaseModel):
    fase_recomendada: str
    accion: Literal["sin_cambios", "nuevo_plan_sugerido"]
    motivo: str
    semanas_sugeridas: int | None


class ManualReadinessRequest(BaseModel):
    target_date: date
    hrv_today: float = Field(gt=0)
    hrv_baseline_28d: float = Field(gt=0)
    hrv_trend_7d: float
    body_battery_am: int = Field(ge=0, le=100)
    training_readiness: Literal["high", "moderate", "low", "very_low"] | None = None
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


class GarminActivityOut(BaseModel):
    activity_id: str
    fecha: date
    tipo: str
    duracion_seg: int | None
    distancia_m: float | None
    hr_avg: int | None
    hr_max: int | None
    training_effect: float | None

    model_config = {"from_attributes": True}


class GarminDailyMetricsOut(BaseModel):
    """Épica C del plan de expansión (02-roadmap/03-vision-produccion.md):
    un punto del historial de recovery. Cada campo es honesto sobre su
    ausencia (None) - "unknown is not zero", nunca se rellena un hueco
    con 0 ni se interpola."""

    fecha: date
    hrv_value: float | None
    hrv_status: str | None
    body_battery_am: int | None
    training_readiness: str | None
    sleep_score: int | None
    stress_avg: int | None
    resting_hr: int | None
    vo2max: float | None


class GarminIntradayPointOut(BaseModel):
    """Un punto de la serie minuto a minuto (petición explícita del
    usuario: "quiero todo ese histórico, no me vale que cojas la media
    del día")."""

    timestamp_utc: datetime
    valor: float

    model_config = {"from_attributes": True}


class HealthNarrativeOut(BaseModel):
    """Épica H del plan de expansión (02-roadmap/03-vision-produccion.md):
    explicación conversacional (Capa 3) del estado de recovery de un
    día - `text`/`source` son `None` cuando la Capa 1 todavía no ha
    calculado ningún ReadinessLog para esa fecha (nunca se inventa un
    estado de recovery ni una explicación de algo que no se decidió)."""

    text: str | None
    source: str | None  # "llm" | "template" | None


class WeeklyVolumeOut(BaseModel):
    """Épica 10 del plan de expansión: un punto de la gráfica de
    volumen semanal por deporte. `distancia_total_m`/`duracion_total_seg`
    son `None` si ninguna actividad de esa semana trae ese campo -
    "unknown is not zero", nunca 0 inventado."""

    semana_inicio: date
    distancia_total_m: float | None
    duracion_total_seg: int | None
    num_sesiones: int

    model_config = {"from_attributes": True}


class PeriodicSummaryOut(BaseModel):
    dias_con_checkin_readiness: int
    distribucion_readiness: dict[str, int]
    training_load: TrainingLoadOut
    peso_inicio_kg: float | None
    peso_fin_kg: float | None
    peso_delta_kg: float | None
    actividades_totales: int
    duracion_actividades_total_seg: int

    model_config = {"from_attributes": True}
