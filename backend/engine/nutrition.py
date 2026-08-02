"""Motor de reglas determinista — Nutrición (TDEE + macros).

Ninguna función de este módulo llama a un LLM ni a la red: son cálculos
puros, testeables y auditables. Es la Capa 1 de la arquitectura descrita en
docs/01-arquitectura/01-arquitectura-general.md.

Fórmulas y umbrales con respaldo científico (ver docs/00-research/
06-periodizacion-ciencia-deportiva.md para las citas completas):
- BMR: Mifflin-St Jeor.
- Tasa de pérdida de peso en corte: 0.5-0.7% del peso corporal/semana
  (Garthe et al. 2011) -> traducido aquí a un déficit calórico diario
  moderado (10-25% del TDEE), nunca "crash diet".
- Proteína: 1.6-2.2 g/kg/día, con el extremo alto (>=2.0 g/kg) reservado
  para fase de corte, donde proteger la masa magra es prioritario
  (Garthe 2011, Campbell et al. 2020).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

_SEXOS_VALIDOS = {"M", "F"}
_ACTIVIDAD_MIN = 1.0
_ACTIVIDAD_MAX = 2.5

# Límites fisiológicos plausibles - evita que NaN/infinito o valores
# absurdos se propaguen silenciosamente a los cálculos de macros.
_PESO_KG_MIN, _PESO_KG_MAX = 20.0, 400.0
_ALTURA_CM_MIN, _ALTURA_CM_MAX = 50.0, 260.0
_EDAD_MIN, _EDAD_MAX = 5, 120

# kcal por gramo de cada macronutriente (Atwater).
_KCAL_PER_G_PROTEIN = 4
_KCAL_PER_G_CARB = 4
_KCAL_PER_G_FAT = 9


def _is_valid_positive_finite(value: float, minimum: float, maximum: float) -> bool:
    return math.isfinite(value) and minimum <= value <= maximum


class WeightPhase(str, Enum):
    """Fase de manejo de peso activa para el usuario."""

    CUT = "cut"
    MAINTENANCE = "maintenance"
    RECOMP = "recomp"
    SURPLUS = "surplus"


@dataclass(frozen=True)
class UserBiometrics:
    """Datos biométricos mínimos necesarios para BMR/TDEE."""

    peso_kg: float
    altura_cm: float
    edad: int
    sexo: str  # "M" | "F"

    def __post_init__(self) -> None:
        if not _is_valid_positive_finite(self.peso_kg, _PESO_KG_MIN, _PESO_KG_MAX):
            raise ValueError(
                f"peso_kg debe ser un número finito entre {_PESO_KG_MIN} y {_PESO_KG_MAX}"
            )
        if not _is_valid_positive_finite(
            self.altura_cm, _ALTURA_CM_MIN, _ALTURA_CM_MAX
        ):
            raise ValueError(
                f"altura_cm debe ser un número finito entre {_ALTURA_CM_MIN} y {_ALTURA_CM_MAX}"
            )
        if not (_EDAD_MIN <= self.edad <= _EDAD_MAX):
            raise ValueError(f"edad debe estar entre {_EDAD_MIN} y {_EDAD_MAX}")
        if self.sexo not in _SEXOS_VALIDOS:
            raise ValueError(f"sexo debe ser uno de {_SEXOS_VALIDOS}")


@dataclass(frozen=True)
class MacroTargets:
    """Objetivo nutricional diario ya calculado por el motor de reglas."""

    kcal_objetivo: float
    proteina_g: float
    carbohidratos_g: float
    grasa_g: float


def calculate_bmr(bio: UserBiometrics) -> float:
    """BMR vía Mifflin-St Jeor.

    Hombre: 10*peso + 6.25*altura - 5*edad + 5
    Mujer:  10*peso + 6.25*altura - 5*edad - 161
    """
    base = 10 * bio.peso_kg + 6.25 * bio.altura_cm - 5 * bio.edad
    return base + 5 if bio.sexo == "M" else base - 161


def calculate_tdee(bio: UserBiometrics, factor_actividad: float) -> float:
    """TDEE = BMR * factor de actividad.

    factor_actividad se acota a un rango razonable (1.0-2.5) para evitar
    entradas erróneas que produzcan objetivos calóricos absurdos.
    """
    if not (_ACTIVIDAD_MIN <= factor_actividad <= _ACTIVIDAD_MAX):
        raise ValueError(
            f"factor_actividad debe estar entre {_ACTIVIDAD_MIN} y {_ACTIVIDAD_MAX}"
        )
    return calculate_bmr(bio) * factor_actividad


# Ajustes calóricos por fase, expresados como fracción del TDEE.
# Corte: rango 10-25% de déficit (moderado, nunca agresivo) -> Garthe 2011.
# Superávit: leve, 5-15%, para minimizar ganancia de grasa innecesaria.
_DEFICIT_CUT = 0.18
_SURPLUS_GAIN = 0.10

# Gramos de proteína por kg de peso corporal, según fase.
_PROTEIN_G_PER_KG = {
    WeightPhase.CUT: 2.2,  # extremo alto: proteger masa magra en déficit
    WeightPhase.MAINTENANCE: 1.8,
    WeightPhase.RECOMP: 2.0,
    WeightPhase.SURPLUS: 1.8,
}

# Reparto de grasa como fracción de las calorías totales (resto va a carbos).
_FAT_FRACTION_OF_KCAL = 0.25


def calculate_macros(peso_kg: float, tdee: float, fase: WeightPhase) -> MacroTargets:
    """Calcula el objetivo calórico y de macros del día según la fase.

    - CUT: TDEE * (1 - 0.18) -> déficit moderado y seguro.
    - MAINTENANCE: TDEE sin ajuste.
    - RECOMP: TDEE sin ajuste (recomposición a calorías de mantenimiento
      con proteína alta, ver Lafontant et al. 2025).
    - SURPLUS: TDEE * (1 + 0.10) -> superávit leve.
    """
    if not _is_valid_positive_finite(peso_kg, _PESO_KG_MIN, _PESO_KG_MAX):
        raise ValueError(
            f"peso_kg debe ser un número finito entre {_PESO_KG_MIN} y {_PESO_KG_MAX}"
        )
    if not math.isfinite(tdee) or tdee <= 0:
        raise ValueError("tdee debe ser un número finito positivo")

    if fase == WeightPhase.CUT:
        kcal_objetivo = tdee * (1 - _DEFICIT_CUT)
    elif fase == WeightPhase.SURPLUS:
        kcal_objetivo = tdee * (1 + _SURPLUS_GAIN)
    else:  # MAINTENANCE, RECOMP
        kcal_objetivo = tdee

    proteina_g = peso_kg * _PROTEIN_G_PER_KG[fase]
    kcal_proteina = proteina_g * _KCAL_PER_G_PROTEIN

    kcal_grasa = kcal_objetivo * _FAT_FRACTION_OF_KCAL
    grasa_g = kcal_grasa / _KCAL_PER_G_FAT

    kcal_restantes = max(kcal_objetivo - kcal_proteina - kcal_grasa, 0)
    carbohidratos_g = kcal_restantes / _KCAL_PER_G_CARB

    return MacroTargets(
        kcal_objetivo=kcal_objetivo,
        proteina_g=proteina_g,
        carbohidratos_g=carbohidratos_g,
        grasa_g=grasa_g,
    )
