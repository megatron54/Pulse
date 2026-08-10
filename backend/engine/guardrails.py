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

# Guardrail 2b (Épica I, 02-roadmap/03-vision-produccion.md): CUT +
# sueño crudo pobre sostenido - extensión conservadora de la guardrail
# 2, usando sleep_score en vez del semáforo categórico. Umbrales
# confirmados explícitamente por el usuario tras revisar
# 00-research/08-nutricion-recovery-ciencia.md (evidencia hormonal
# débil/contradictoria, pero un RCT controlado - Nedeltcheva/Penev
# 2010 - muestra que el sueño pobre sostenido en déficit empeora la
# partición grasa/músculo, aunque el peso total perdido sea el mismo) -
# NUNCA inventados unilateralmente. sleep_score < 60 es la categoría
# "poor" oficial de Garmin (no un número inventado por este proyecto).
_CUT_PAUSA_SLEEP_SCORE_UMBRAL = 60
_CUT_PAUSA_DIAS_SLEEP_CONSECUTIVOS = 3

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


def should_pause_calorie_deficit_for_poor_sleep(
    weight_phase: WeightPhase, sleep_scores: list[int | None]
) -> bool:
    """Guardrail 2b (Épica I del plan de expansión): si el usuario está
    en fase CUT y lleva >=3 noches CONSECUTIVAS CONFIRMADAS con
    `sleep_score` por debajo del umbral "poor" de Garmin (<60), se
    pausa el déficit igual que la guardrail 2 (readiness categórico) -
    misma acción (subir a MAINTENANCE), señal adicional distinta.

    Nota de asimetría INTENCIONAL con la guardrail 2 (hallazgo de
    @code-reviewer, documentado explícitamente para no repetir la
    duda): la ventana de días que consume esta guardrail en la capa de
    servicio SÍ incluye la fecha de hoy (`target_date`), a diferencia
    de `get_recent_readiness_levels` que la excluye. Esto es correcto
    y deliberado, no un descuido de "misma ventana temporal": el
    `sleep_score` de la noche anterior ya está disponible por la
    mañana del día que se está calculando (Garmin lo sincroniza al
    despertar), mientras que el readiness de HOY normalmente aún no se
    ha calculado en el momento en que se consulta este historial. Esta
    función en sí misma es agnóstica a esa ventana - solo mira los
    últimos 3 valores de la lista que se le pasan.

    "unknown is not zero": un `None` en la ventana (día sin sincronizar,
    dispositivo sin ese dato) NUNCA cuenta como "malo" - rompe la racha
    de días confirmados, no la sostiene. Solo dispara con 3 valores
    NUMÉRICOS reales, todos por debajo del umbral.

    Solo aplica a WeightPhase.CUT, igual que la guardrail 2 - las demás
    fases no tienen un déficit que pausar."""
    if not sleep_scores:
        raise ValueError("sleep_scores no puede estar vacío")
    if not isinstance(weight_phase, WeightPhase):
        raise ValueError("weight_phase debe ser un WeightPhase")
    for valor in sleep_scores:
        if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int)):
            raise ValueError("sleep_scores solo puede contener int o None")
    if weight_phase != WeightPhase.CUT:
        return False

    ultimos = sleep_scores[-_CUT_PAUSA_DIAS_SLEEP_CONSECUTIVOS:]
    if len(ultimos) < _CUT_PAUSA_DIAS_SLEEP_CONSECUTIVOS:
        return False
    return all(
        valor is not None and valor < _CUT_PAUSA_SLEEP_SCORE_UMBRAL for valor in ultimos
    )


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
