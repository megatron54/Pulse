"""Motor de reglas determinista — Progresión de carga y series.

Capa 1 de la arquitectura: sin llamadas a red ni a LLM, 100% testeable.

Fuentes (ver docs/00-research/06-periodizacion-ciencia-deportiva.md):
- Epley: estimación de 1RM a partir de peso y repeticiones.
- Doble progresión: patrón estándar de programación de fuerza/hipertrofia
  (subir reps dentro de un rango objetivo; al llegar al techo, subir peso
  y reiniciar reps al suelo del rango).
- APRE / RIR-RPE autoregulation (Mann et al. 2010; Helms, Zourdos): ajustar
  la carga de la siguiente sesión según reps-en-reserva (RIR) real vs.
  objetivo, no solo según el peso levantado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

# Epley se degrada mucho por encima de este umbral de repeticiones: no es
# fiable estimar 1RM real con series muy largas, mejor rechazar que mentir.
_MAX_REPS_FIABLES_1RM = 15

# Tope superior fisiológicamente plausible para reps logradas en una serie
# (evita que un entero disparatado se propague sin control aguas abajo).
_MAX_REPS_LOGRADAS = 100

_PESO_KG_MIN, _PESO_KG_MAX = 1.0, 500.0

# Incremento de peso al completar la doble progresión (techo del rango).
_INCREMENTO_PESO_PCT = 0.025  # +2.5%, moderado y auditable

# Ajuste de carga por punto de diferencia entre RIR real y objetivo,
# acotado para que nunca sea un salto agresivo en una sola sesión.
_AJUSTE_RIR_PCT_POR_PUNTO = 0.02
_AJUSTE_RIR_PCT_MAX = 0.10


class ProgressionAction(str, Enum):
    """Salida tipada y cerrada: nunca texto libre, siempre auditable."""

    INCREASE_REPS = "increase_reps"
    INCREASE_WEIGHT = "increase_weight"
    DECREASE_WEIGHT = "decrease_weight"
    HOLD = "hold"


@dataclass(frozen=True)
class RepRange:
    """Rango de repeticiones objetivo para un ejercicio (doble progresión)."""

    min_reps: int
    max_reps: int

    def __post_init__(self) -> None:
        _validar_entero_no_negativo("min_reps", self.min_reps, maximo=_MAX_REPS_LOGRADAS)
        _validar_entero_no_negativo("max_reps", self.max_reps, maximo=_MAX_REPS_LOGRADAS)
        if self.min_reps == 0 or self.max_reps == 0:
            raise ValueError("min_reps y max_reps deben ser positivos")
        if self.min_reps > self.max_reps:
            raise ValueError("min_reps no puede ser mayor que max_reps")


@dataclass(frozen=True)
class SetPerformance:
    """Resultado subjetivo/objetivo de una serie para autorregulación RIR."""

    rir_objetivo: int
    rir_real: int

    def __post_init__(self) -> None:
        _validar_entero_no_negativo("rir_objetivo", self.rir_objetivo, maximo=10)
        _validar_entero_no_negativo("rir_real", self.rir_real, maximo=10)


@dataclass(frozen=True)
class ProgressionResult:
    """Decisión tipada de progresión, lista para que la Capa 3 la explique.

    Nota de diseño: `peso_siguiente_kg` es el peso matemáticamente ideal
    (ej. 74.46kg), NO redondeado a incrementos de disco cargables (1.25kg,
    2.5kg...). Ese redondeo es responsabilidad deliberada de una capa
    posterior (UI/presentación), para que este módulo siga siendo agnóstico
    del equipamiento disponible del usuario (mancuernas, discos, máquinas
    con incrementos fijos, etc.).
    """

    accion: ProgressionAction
    peso_siguiente_kg: float
    reps_objetivo_siguiente: int | None = None


def _validar_peso(peso_kg: float) -> None:
    if not math.isfinite(peso_kg) or not (_PESO_KG_MIN <= peso_kg <= _PESO_KG_MAX):
        raise ValueError(
            f"peso_kg debe ser un número finito entre {_PESO_KG_MIN} y {_PESO_KG_MAX}"
        )


def _validar_entero_no_negativo(nombre: str, valor: int, maximo: int | None = None) -> None:
    """Rechaza bool (subclase de int en Python), float/NaN/inf disfrazados
    de int, y negativos. Blinda la Capa 1 contra la misma clase de bug
    que motivó el hardening de NaN/infinito en engine/nutrition.py."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{nombre} debe ser un entero")
    if valor < 0:
        raise ValueError(f"{nombre} no puede ser negativo")
    if maximo is not None and valor > maximo:
        raise ValueError(f"{nombre} no puede superar {maximo}")


def estimate_1rm(peso_kg: float, reps: int) -> float:
    """1RM estimado vía fórmula de Epley: peso * (1 + reps/30).

    Rechaza series de más de _MAX_REPS_FIABLES_1RM repeticiones: la fórmula
    se degrada demasiado ahí y devolvería un número falsamente preciso.
    """
    _validar_peso(peso_kg)
    _validar_entero_no_negativo("reps", reps, maximo=_MAX_REPS_LOGRADAS)
    if reps == 0:
        raise ValueError("reps debe ser positivo")
    if reps > _MAX_REPS_FIABLES_1RM:
        raise ValueError(
            f"reps={reps} supera el umbral fiable de Epley "
            f"({_MAX_REPS_FIABLES_1RM}); no se puede estimar 1RM con garantía"
        )
    return peso_kg * (1 + reps / 30)


def suggest_double_progression(
    peso_actual_kg: float, reps_logradas: int, rango: RepRange
) -> ProgressionResult:
    """Decide la siguiente sesión según el patrón de doble progresión.

    - reps_logradas >= max_reps: sube peso (+2.5%) y reinicia reps al mínimo.
    - min_reps <= reps_logradas < max_reps: mantiene peso, sube el objetivo
      de reps en 1.
    - reps_logradas < min_reps: no hubo progreso suficiente; se mantiene
      el mismo estímulo (peso y reps al mínimo del rango). Bajar carga por
      fatiga/dolor es responsabilidad de guardrails, no de este módulo.
    """
    _validar_peso(peso_actual_kg)
    _validar_entero_no_negativo(
        "reps_logradas", reps_logradas, maximo=_MAX_REPS_LOGRADAS
    )

    if reps_logradas >= rango.max_reps:
        return ProgressionResult(
            accion=ProgressionAction.INCREASE_WEIGHT,
            peso_siguiente_kg=peso_actual_kg * (1 + _INCREMENTO_PESO_PCT),
            reps_objetivo_siguiente=rango.min_reps,
        )
    if reps_logradas >= rango.min_reps:
        return ProgressionResult(
            accion=ProgressionAction.INCREASE_REPS,
            peso_siguiente_kg=peso_actual_kg,
            reps_objetivo_siguiente=reps_logradas + 1,
        )
    return ProgressionResult(
        accion=ProgressionAction.HOLD,
        peso_siguiente_kg=peso_actual_kg,
        reps_objetivo_siguiente=rango.min_reps,
    )


def suggest_rir_load_adjustment(
    peso_actual_kg: float, performance: SetPerformance
) -> ProgressionResult:
    """Autorregulación estilo APRE/RIR: ajusta la carga de la próxima sesión
    según la diferencia entre RIR real y RIR objetivo.

    - RIR real > objetivo (sobró reserva, fue más fácil): sube carga.
    - RIR real < objetivo (costó más de lo esperado): baja carga.
    - RIR real == objetivo: mantiene.

    El ajuste se acota a +/- _AJUSTE_RIR_PCT_MAX para evitar saltos
    agresivos en una sola sesión, independientemente de cuán grande sea
    la diferencia de RIR reportada.
    """
    _validar_peso(peso_actual_kg)

    diferencia = performance.rir_real - performance.rir_objetivo
    if diferencia == 0:
        return ProgressionResult(
            accion=ProgressionAction.HOLD, peso_siguiente_kg=peso_actual_kg
        )

    ajuste_pct = min(
        abs(diferencia) * _AJUSTE_RIR_PCT_POR_PUNTO, _AJUSTE_RIR_PCT_MAX
    )
    if diferencia > 0:
        return ProgressionResult(
            accion=ProgressionAction.INCREASE_WEIGHT,
            peso_siguiente_kg=peso_actual_kg * (1 + ajuste_pct),
        )
    return ProgressionResult(
        accion=ProgressionAction.DECREASE_WEIGHT,
        peso_siguiente_kg=peso_actual_kg * (1 - ajuste_pct),
    )
