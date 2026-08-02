"""Motor de reglas determinista — Guardrails transversales de seguridad.

Capa 1 de la arquitectura: sin llamadas a red ni a LLM, 100% testeable.

A diferencia de `periodization.py` (que decide la sesión de HOY a partir
del readiness de HOY), este módulo combina estado de VARIOS DÍAS y de
VARIOS MÓDULOS (periodización + nutrición) para aplicar las reglas duras
no negociables descritas en docs/00-research/06-periodizacion-ciencia-
deportiva.md, sección "Reglas de seguridad duras (hard gates)":

1. ACWR > 1.5 durante 2 días consecutivos -> deload automático inmediato,
   independiente del calendario de bloque.
2. CUT + readiness RED durante >=3 días consecutivos -> pausar el
   déficit calórico (subir a mantenimiento) hasta normalizar.
3. RED + competición en <72h -> forzar descanso total, nunca sesión
   técnica de sparring intenso (el taper normal ya lo gestiona el plan;
   esto es la salvaguarda de última instancia si la recuperación falla).
4. Nunca 2 sesiones de alta demanda neuromuscular el mismo día salvo que
   ambas estén en modo mantenimiento Y separadas por un descanso real.

Todas las funciones son puras: reciben el historial/contexto ya calculado
por otros módulos (periodization.py, nutrition.py) y devuelven una
decisión booleana + motivo, nunca texto libre generado dinámicamente.
"""
from __future__ import annotations

import math

from engine.nutrition import WeightPhase
from engine.periodization import ReadinessLevel

# Guardrail 1: ACWR > 1.5 sostenido.
_ACWR_DELOAD_UMBRAL = 1.5
_ACWR_DELOAD_DIAS_CONSECUTIVOS = 2

# Guardrail 2: CUT + RED sostenido.
_CUT_PAUSA_DIAS_RED_CONSECUTIVOS = 3

# Guardrail 3: proximidad de competición.
_HORAS_PRE_COMPETICION_CRITICAS = 72
_DIAS_PRE_COMPETICION_CRITICOS = _HORAS_PRE_COMPETICION_CRITICAS // 24  # 3

# Guardrail 4: separación mínima entre sesiones de alta demanda.
_SEPARACION_MINIMA_HORAS = 6


def _validar_entero_no_negativo(nombre: str, valor: int) -> None:
    """Rechaza bool (subclase de int en Python) y cualquier tipo que no
    sea int, igual que el guard equivalente en engine/progression.py y
    engine/periodization.py. Un guardrail de seguridad no puede confiar
    en que un `bool`/`NaN` disfrazado se comporte como se espera."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{nombre} debe ser un entero")
    if valor < 0:
        raise ValueError(f"{nombre} no puede ser negativo")


def _validar_finito_no_negativo(nombre: str, valor: float) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{nombre} debe ser numérico")
    if not math.isfinite(valor) or valor < 0:
        raise ValueError(f"{nombre} debe ser un número finito no negativo")


def should_force_deload(acwr_history: list[float]) -> bool:
    """Guardrail 1: ACWR > 1.5 en los últimos 2 días consecutivos ->
    deload inmediato, sin esperar al final del bloque de periodización.

    Solo mira los últimos `_ACWR_DELOAD_DIAS_CONSECUTIVOS` valores del
    historial (los más recientes van al final de la lista): un pico
    antiguo ya resuelto no debe disparar el guardrail hoy.
    """
    if not acwr_history:
        raise ValueError("acwr_history no puede estar vacío")
    for valor in acwr_history:
        _validar_finito_no_negativo("acwr_history[i]", valor)

    ultimos = acwr_history[-_ACWR_DELOAD_DIAS_CONSECUTIVOS:]
    if len(ultimos) < _ACWR_DELOAD_DIAS_CONSECUTIVOS:
        return False
    return all(valor > _ACWR_DELOAD_UMBRAL for valor in ultimos)


def should_pause_calorie_deficit(
    weight_phase: WeightPhase, readiness_history: list[ReadinessLevel]
) -> bool:
    """Guardrail 2: si el usuario está en fase CUT (déficit activo) y
    lleva >=3 días consecutivos en RED, se pausa el déficit (el motor de
    nutrición debe usar WeightPhase.MAINTENANCE en su lugar) hasta que la
    recuperación se normalice. Evita apilar déficit energético sobre
    fatiga/sobreentrenamiento ya instalado (relacionado con RED-S).

    Solo aplica a WeightPhase.CUT: las demás fases no tienen un déficit
    que pausar.
    """
    if not readiness_history:
        raise ValueError("readiness_history no puede estar vacío")
    if not isinstance(weight_phase, WeightPhase):
        raise ValueError("weight_phase debe ser un WeightPhase")
    for nivel in readiness_history:
        if not isinstance(nivel, ReadinessLevel):
            raise ValueError("readiness_history solo puede contener ReadinessLevel")
    if weight_phase != WeightPhase.CUT:
        return False

    ultimos = readiness_history[-_CUT_PAUSA_DIAS_RED_CONSECUTIVOS:]
    if len(ultimos) < _CUT_PAUSA_DIAS_RED_CONSECUTIVOS:
        return False
    return all(nivel == ReadinessLevel.RED for nivel in ultimos)


def should_force_full_rest_pre_competition(
    days_to_competition: int | None, readiness: ReadinessLevel
) -> bool:
    """Guardrail 3: si hay una competición en menos de 72h Y el readiness
    de hoy es RED, se fuerza descanso total (nunca sparring/técnica
    intensa), como salvaguarda de última instancia sobre el taper normal
    del plan. Sin readiness RED, la proximidad de competición por sí sola
    no dispara este guardrail (eso ya lo gestiona el plan de taper).
    """
    if days_to_competition is not None:
        _validar_entero_no_negativo("days_to_competition", days_to_competition)
    if not isinstance(readiness, ReadinessLevel):
        raise ValueError("readiness debe ser un ReadinessLevel")
    if days_to_competition is None:
        return False
    if readiness != ReadinessLevel.RED:
        return False
    return days_to_competition <= _DIAS_PRE_COMPETICION_CRITICOS


def validate_same_day_sessions(
    ambas_en_mantenimiento: bool, separacion_horas: float
) -> tuple[bool, str | None]:
    """Guardrail 4: dos sesiones de alta demanda neuromuscular el mismo
    día solo son válidas si AMBAS están en modo mantenimiento (volumen
    reducido) Y están separadas por al menos `_SEPARACION_MINIMA_HORAS`.

    Devuelve (es_valido, motivo). `motivo` es None si es_valido=True, o
    una clave corta y estable (no texto libre variable) explicando qué
    condición falló, para que la Capa 3 la traduzca a lenguaje natural.
    """
    if not isinstance(ambas_en_mantenimiento, bool):
        raise ValueError("ambas_en_mantenimiento debe ser bool explícito")
    _validar_finito_no_negativo("separacion_horas", separacion_horas)

    if not ambas_en_mantenimiento and separacion_horas < _SEPARACION_MINIMA_HORAS:
        return False, "sin_mantenimiento_y_sin_separacion_suficiente"
    if not ambas_en_mantenimiento:
        return False, "sin_mantenimiento"
    if separacion_horas < _SEPARACION_MINIMA_HORAS:
        return False, "separacion_insuficiente"
    return True, None
