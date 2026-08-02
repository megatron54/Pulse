"""Motor de reglas determinista — Periodización y readiness diario.

Capa 1 de la arquitectura: sin llamadas a red ni a LLM, 100% testeable.
Esta es la pieza central del "semáforo" que decide, cada día, si el plan
de entrenamiento se ejecuta tal cual, se reduce, o se sustituye por
descanso — a partir de datos de recuperación (Garmin: HRV, Body Battery,
Training Readiness, sueño) y carga de entrenamiento (ACWR).

Fuentes (ver docs/00-research/06-periodizacion-ciencia-deportiva.md):
- Di, Hongye & Donglin 2025 (PMC12859854): autorregulación en tiempo real
  con HRV + ratio de carga mejora la adaptabilidad frente a carga fija.
- Williams et al. 2020 (PMC7795557): HRV detecta bien cambios de carga si
  se compara contra una línea base personal, no un valor absoluto.
- Regla operativa: usar la TENDENCIA de 3-7 días vs. baseline de 4-6
  semanas, nunca el dato de un solo día.
- ACWR > 1.5: umbral de riesgo de lesión ampliamente citado en la
  literatura de carga de entrenamiento (Banister TSB / ACWR).
- Regla dura no negociable: dolor articular -> descanso total, sin
  excepción, independientemente del resto de señales.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

_TRAINING_READINESS_VALIDOS = {"high", "moderate", "low", "very_low"}

_BODY_BATTERY_MIN, _BODY_BATTERY_MAX = 0, 100
_SLEEP_SCORE_MIN, _SLEEP_SCORE_MAX = 0, 100

# Umbrales del semáforo de readiness (ver select_session_type en la
# investigación original: red_flags/yellow_flags por señal).
_HRV_DELTA_RED = -0.15
_HRV_DELTA_YELLOW = -0.07
_HRV_TREND_RED = -0.10
_BODY_BATTERY_RED = 30
_BODY_BATTERY_YELLOW = 50
_ACWR_RED = 1.5
_ACWR_YELLOW = 1.3
_SLEEP_SCORE_YELLOW = 50
_YELLOW_FLAGS_PARA_BAJAR_A_YELLOW = 2

# Ajustes de sesión por nivel de readiness.
_YELLOW_VOLUME_PCT = 65
_YELLOW_RPE_CAP = 7
_RED_TECHNICAL_VOLUME_PCT = 40
_RED_TECHNICAL_RPE_CAP = 6


class ReadinessLevel(str, Enum):
    """Salida tipada y cerrada del semáforo diario de recuperación."""

    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class SessionType(str, Enum):
    """Tipos de sesión que el plan semanal puede programar para un día.

    Se dividen conceptualmente en "alta demanda neuromuscular/metabólica"
    (STRENGTH_HEAVY, MARTIAL_ARTS_SPARRING, ENDURANCE_INTERVALS) y "menor
    demanda / técnicas" (el resto), porque el semáforo RED las trata de
    forma distinta: las de alta demanda se sustituyen por descanso: las
    de menor demanda se permiten a volumen/intensidad reducidos.
    """

    REST = "rest"
    ACTIVE_RECOVERY = "active_recovery"
    STRENGTH_HEAVY = "strength_heavy"
    STRENGTH_HYPERTROPHY = "strength_hypertrophy"
    ENDURANCE_INTERVALS = "endurance_intervals"
    ENDURANCE_LONG = "endurance_long"
    MARTIAL_ARTS_TECHNICAL = "martial_arts_technical"
    MARTIAL_ARTS_SPARRING = "martial_arts_sparring"


# Sesiones de alta demanda neuromuscular/metabólica: en RED se sustituyen
# por descanso, nunca se permiten "a poco volumen".
_ALTA_DEMANDA = frozenset(
    {
        SessionType.STRENGTH_HEAVY,
        SessionType.MARTIAL_ARTS_SPARRING,
        SessionType.ENDURANCE_INTERVALS,
    }
)

# Sesiones que no requieren ajuste (ya son descanso/recuperación).
_SESIONES_DE_DESCANSO = frozenset({SessionType.REST, SessionType.ACTIVE_RECOVERY})


def _validar_entero_en_rango(nombre: str, valor: int, minimo: int, maximo: int) -> None:
    """Rechaza bool (subclase de int en Python) y float/NaN/inf disfrazados
    de int, igual que el guard equivalente en engine/progression.py."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{nombre} debe ser un entero")
    if not (minimo <= valor <= maximo):
        raise ValueError(f"{nombre} debe estar entre {minimo} y {maximo}")


@dataclass(frozen=True)
class RecoveryContext:
    """Datos de recuperación del día, típicamente sincronizados desde
    Garmin (ver backend/garmin_sync/) más flags manuales del usuario."""

    hrv_today: float
    hrv_baseline_28d: float
    hrv_trend_7d: float  # pendiente relativa de los últimos 7 días
    body_battery_am: int
    training_readiness: str  # "high" | "moderate" | "low" | "very_low"
    sleep_score: int
    acwr: float  # Acute:Chronic Workload Ratio
    joint_pain_flag: bool

    def __post_init__(self) -> None:
        for nombre, valor in (
            ("hrv_today", self.hrv_today),
            ("hrv_baseline_28d", self.hrv_baseline_28d),
            ("hrv_trend_7d", self.hrv_trend_7d),
        ):
            if not math.isfinite(valor):
                raise ValueError(f"{nombre} debe ser un número finito")
        if self.hrv_baseline_28d <= 0:
            raise ValueError("hrv_baseline_28d debe ser positivo (no puede ser 0)")
        _validar_entero_en_rango(
            "body_battery_am", self.body_battery_am, _BODY_BATTERY_MIN, _BODY_BATTERY_MAX
        )
        _validar_entero_en_rango(
            "sleep_score", self.sleep_score, _SLEEP_SCORE_MIN, _SLEEP_SCORE_MAX
        )
        if self.training_readiness not in _TRAINING_READINESS_VALIDOS:
            raise ValueError(
                f"training_readiness debe ser uno de {_TRAINING_READINESS_VALIDOS}"
            )
        if not math.isfinite(self.acwr) or self.acwr < 0:
            raise ValueError("acwr debe ser un número finito no negativo")
        # Regla de seguridad núcleo: dolor articular -> RED sin excepción
        # (ver compute_readiness). Se exige bool estricto para que un
        # `None`/`0` accidental desde la capa de sync NUNCA pueda saltarse
        # este gate por comportarse como "falsy".
        if not isinstance(self.joint_pain_flag, bool):
            raise ValueError("joint_pain_flag debe ser bool (True/False explícito)")


@dataclass(frozen=True)
class SessionRecommendation:
    """Decisión tipada de la sesión del día, lista para que la Capa 3
    (LLM) la explique - nunca decide, solo redacta."""

    session_type: SessionType
    volume_pct: int
    intensity_rpe_cap: int | None = None


def compute_readiness(ctx: RecoveryContext) -> ReadinessLevel:
    """Semáforo de readiness diario (RED/YELLOW/GREEN).

    Regla dura no negociable: dolor articular -> RED siempre, sin
    importar el resto de señales (Ibrahim et al. 2024).

    Para el resto de señales se cuentan "red flags" y "yellow flags"
    (patrón documentado en la literatura de autorregulación, ver
    Ibrahim/Beaumont/Strohacker 2024): 1+ red flag -> RED; 2+ yellow
    flags sin red flags -> YELLOW; en otro caso -> GREEN.
    """
    if ctx.joint_pain_flag:
        return ReadinessLevel.RED

    red_flags = 0
    yellow_flags = 0

    hrv_delta_pct = (ctx.hrv_today - ctx.hrv_baseline_28d) / ctx.hrv_baseline_28d
    if hrv_delta_pct < _HRV_DELTA_RED or ctx.hrv_trend_7d < _HRV_TREND_RED:
        red_flags += 1
    elif hrv_delta_pct < _HRV_DELTA_YELLOW:
        yellow_flags += 1

    if ctx.training_readiness == "very_low":
        red_flags += 1
    elif ctx.training_readiness == "low":
        yellow_flags += 1

    if ctx.body_battery_am < _BODY_BATTERY_RED:
        red_flags += 1
    elif ctx.body_battery_am < _BODY_BATTERY_YELLOW:
        yellow_flags += 1

    if ctx.acwr > _ACWR_RED:
        red_flags += 1
    elif ctx.acwr > _ACWR_YELLOW:
        yellow_flags += 1

    if ctx.sleep_score < _SLEEP_SCORE_YELLOW:
        yellow_flags += 1

    if red_flags >= 1:
        return ReadinessLevel.RED
    if yellow_flags >= _YELLOW_FLAGS_PARA_BAJAR_A_YELLOW:
        return ReadinessLevel.YELLOW
    return ReadinessLevel.GREEN


def decide_session(
    planned_session: SessionType, readiness: ReadinessLevel
) -> SessionRecommendation:
    """Decide la sesión final del día combinando el plan semanal con el
    readiness calculado por compute_readiness.

    - GREEN: sigue el plan al 100%.
    - YELLOW: reduce volumen (~35%) y acota el RPE, sin cambiar el tipo
      de sesión planificada.
    - RED + sesión de alta demanda (fuerza pesada, sparring, intervalos):
      se sustituye por descanso activo (volumen 0) - nunca se "reduce",
      se elimina, porque el riesgo de lesión/sobreentrenamiento en alta
      demanda con mala recuperación no es aceptable.
    - RED + sesión técnica/menor demanda (MARTIAL_ARTS_TECHNICAL,
      STRENGTH_HYPERTROPHY, ENDURANCE_LONG): se permite a volumen e
      intensidad muy reducidos (40%, RPE<=6; nunca al fallo, nunca
      sparring duro). Decisión consciente, no un descuido: hipertrofia
      ligera y cardio suave en zona 2 son estímulos de bajo coste
      neuromuscular aceptables incluso con recuperación pobre; si en el
      futuro se quiere tratar STRENGTH_HYPERTROPHY como alta demanda
      también en RED, basta con añadirlo a _ALTA_DEMANDA.
    """
    if planned_session in _SESIONES_DE_DESCANSO:
        return SessionRecommendation(session_type=planned_session, volume_pct=100)

    if readiness == ReadinessLevel.GREEN:
        return SessionRecommendation(session_type=planned_session, volume_pct=100)

    if readiness == ReadinessLevel.YELLOW:
        return SessionRecommendation(
            session_type=planned_session,
            volume_pct=_YELLOW_VOLUME_PCT,
            intensity_rpe_cap=_YELLOW_RPE_CAP,
        )

    # readiness == RED
    if planned_session in _ALTA_DEMANDA:
        return SessionRecommendation(
            session_type=SessionType.ACTIVE_RECOVERY, volume_pct=0
        )
    return SessionRecommendation(
        session_type=planned_session,
        volume_pct=_RED_TECHNICAL_VOLUME_PCT,
        intensity_rpe_cap=_RED_TECHNICAL_RPE_CAP,
    )
