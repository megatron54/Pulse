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
    Garmin (ver backend/garmin_sync/) más flags manuales del usuario.

    `training_readiness` es OPCIONAL (a diferencia del resto de señales):
    varios relojes Garmin de gama de entrada/media (Forerunner 55, 165,
    Instinct...) no calculan Training Readiness en absoluto - es una
    limitación estructural del dispositivo, no un dato que "todavía no
    ha llegado". Exigirlo como obligatorio bloquearía el cálculo de
    readiness PARA SIEMPRE en esas cuentas. Cuando es `None`, esa señal
    simplemente no aporta flags rojos/amarillos - el resto de señales
    (HRV, Body Battery, ACWR, sueño) sí lo hacen con normalidad. Esto
    es distinto de "fabricar un valor neutral": es excluir
    honestamente una señal que no existe para ese dispositivo, en vez
    de inventar un "moderate" que no se midió."""

    hrv_today: float
    hrv_baseline_28d: float
    hrv_trend_7d: float  # pendiente relativa de los últimos 7 días
    body_battery_am: int
    sleep_score: int
    acwr: float  # Acute:Chronic Workload Ratio
    joint_pain_flag: bool
    training_readiness: str | None = None  # "high" | "moderate" | "low" | "very_low" | None

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
        if (
            self.training_readiness is not None
            and self.training_readiness not in _TRAINING_READINESS_VALIDOS
        ):
            raise ValueError(
                f"training_readiness debe ser None o uno de {_TRAINING_READINESS_VALIDOS}"
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


class SignalState(str, Enum):
    """En qué estado está UNA señal de recuperación, por separado del
    veredicto global.

    `UNKNOWN` no es "normal": es que esa señal no se midió (el reloj no
    calcula Training Readiness, o es una fila de historial anterior a
    que se guardara ese campo). Se mantiene distinguible de `OK` para
    que la interfaz pueda dibujar la ausencia como ausencia en vez de
    darla por buena ("unknown is not zero")."""

    RED = "red"
    YELLOW = "yellow"
    OK = "ok"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SignalAssessment:
    """Una señal, su valor, y el umbral que la habría puesto en rojo o
    en ámbar.

    Existe porque el semáforo era una caja negra: la pantalla decía
    "Recuperación baja" y debajo enseñaba seis cifras, sin ninguna
    relación visible entre las dos cosas. El usuario preguntó
    literalmente "¿por qué está en rojo, por qué está baja, cómo puedo
    ayudarlo?" y la aplicación no tenía la respuesta en ninguna parte.

    Los umbrales viajan con la señal en vez de estar duplicados en el
    frontend: si un umbral cambia aquí, el texto que lo explica cambia
    con él. Un `30` escrito a mano en un componente de React se queda
    atrás en el primer ajuste del motor.

    `senal` es un código estable para el cliente (como `motivo` en
    `services.errors`); el texto que lee la persona lo pone la interfaz,
    no este módulo.
    """

    senal: str
    estado: SignalState
    valor: float | None
    umbral_rojo: float | None = None
    umbral_amarillo: float | None = None
    # Si el rojo/ámbar se cruza por ARRIBA (ACWR: más carga es peor) o
    # por ABAJO (Body Battery, sueño, VFC). Sin esto la interfaz no
    # puede escribir "por encima de" / "por debajo de" sin volver a
    # codificar la dirección de cada regla a mano.
    peor_hacia: str = "abajo"


def _estado_por_umbral_inferior(
    valor: float, umbral_rojo: float | None, umbral_amarillo: float | None
) -> SignalState:
    if umbral_rojo is not None and valor < umbral_rojo:
        return SignalState.RED
    if umbral_amarillo is not None and valor < umbral_amarillo:
        return SignalState.YELLOW
    return SignalState.OK


def assess_signals_from_values(
    *,
    hrv_delta_pct: float | None,
    hrv_trend_7d: float | None,
    training_readiness: str | None,
    body_battery_am: int | None,
    acwr: float | None,
    sleep_score: int | None,
    joint_pain_flag: bool,
) -> tuple[SignalAssessment, ...]:
    """Evalúa cada señal por separado, a partir de valores YA
    normalizados (delta de VFC en fracción, no VFC de hoy + baseline).

    Toma valores y no un `RecoveryContext` a propósito: la fila de
    `ReadinessLog` guarda `hrv_delta_pct` ya calculado y no guarda
    `hrv_today` ni la baseline, así que exigir un `RecoveryContext`
    obligaría a inventarse dos números para poder explicar un día del
    historial. Cualquier valor `None` (columna nullable, fila antigua,
    señal que el dispositivo no mide) se evalúa como `UNKNOWN` en vez de
    contar como buena.

    La VFC se devuelve como DOS señales, no como una: el motor las trata
    como un único flag (un OR), pero son dos preguntas distintas -
    "¿cómo estás hoy respecto a tu media?" y "¿hacia dónde va la semana?"
    - y colapsarlas escondía justo la que decidía. Caso real: la tarjeta
    mostraba una VFC un 16 % POR ENCIMA de la baseline mientras el
    veredicto era rojo, porque lo que había cruzado el umbral era la
    tendencia de 7 días, que no aparecía en ninguna pantalla.
    """
    senales: list[SignalAssessment] = []

    senales.append(
        SignalAssessment(
            senal="hrv_delta",
            estado=(
                SignalState.UNKNOWN
                if hrv_delta_pct is None
                else _estado_por_umbral_inferior(
                    hrv_delta_pct, _HRV_DELTA_RED, _HRV_DELTA_YELLOW
                )
            ),
            valor=hrv_delta_pct,
            umbral_rojo=_HRV_DELTA_RED,
            umbral_amarillo=_HRV_DELTA_YELLOW,
        )
    )
    senales.append(
        SignalAssessment(
            senal="hrv_trend",
            estado=(
                SignalState.UNKNOWN
                if hrv_trend_7d is None
                else _estado_por_umbral_inferior(hrv_trend_7d, _HRV_TREND_RED, None)
            ),
            valor=hrv_trend_7d,
            umbral_rojo=_HRV_TREND_RED,
        )
    )
    # Categórica, sin umbral numérico: su `valor` es None y la interfaz
    # la escribe a partir del propio `estado`.
    senales.append(
        SignalAssessment(
            senal="training_readiness",
            estado={
                "very_low": SignalState.RED,
                "low": SignalState.YELLOW,
                "moderate": SignalState.OK,
                "high": SignalState.OK,
            }.get(training_readiness or "", SignalState.UNKNOWN),
            valor=None,
        )
    )
    senales.append(
        SignalAssessment(
            senal="body_battery",
            estado=(
                SignalState.UNKNOWN
                if body_battery_am is None
                else _estado_por_umbral_inferior(
                    body_battery_am, _BODY_BATTERY_RED, _BODY_BATTERY_YELLOW
                )
            ),
            valor=body_battery_am,
            umbral_rojo=_BODY_BATTERY_RED,
            umbral_amarillo=_BODY_BATTERY_YELLOW,
        )
    )
    senales.append(
        SignalAssessment(
            senal="acwr",
            estado=(
                SignalState.UNKNOWN
                if acwr is None
                else SignalState.RED
                if acwr > _ACWR_RED
                else SignalState.YELLOW
                if acwr > _ACWR_YELLOW
                else SignalState.OK
            ),
            valor=acwr,
            umbral_rojo=_ACWR_RED,
            umbral_amarillo=_ACWR_YELLOW,
            peor_hacia="arriba",
        )
    )
    # El sueño no tiene umbral rojo en el motor: por sí solo nunca pone
    # el día en rojo, solo aporta un flag ámbar.
    senales.append(
        SignalAssessment(
            senal="sleep",
            estado=(
                SignalState.UNKNOWN
                if sleep_score is None
                else _estado_por_umbral_inferior(sleep_score, None, _SLEEP_SCORE_YELLOW)
            ),
            valor=sleep_score,
            umbral_amarillo=_SLEEP_SCORE_YELLOW,
        )
    )
    senales.append(
        SignalAssessment(
            senal="joint_pain",
            estado=SignalState.RED if joint_pain_flag else SignalState.OK,
            valor=None,
        )
    )
    return tuple(senales)


def assess_signals(ctx: RecoveryContext) -> tuple[SignalAssessment, ...]:
    """`assess_signals_from_values` para un `RecoveryContext` completo."""
    return assess_signals_from_values(
        hrv_delta_pct=(ctx.hrv_today - ctx.hrv_baseline_28d) / ctx.hrv_baseline_28d,
        hrv_trend_7d=ctx.hrv_trend_7d,
        training_readiness=ctx.training_readiness,
        body_battery_am=ctx.body_battery_am,
        acwr=ctx.acwr,
        sleep_score=ctx.sleep_score,
        joint_pain_flag=ctx.joint_pain_flag,
    )


# Un flag por GRUPO de señales, no por señal: las dos señales de VFC
# cuentan como un único flag (el motor las combinaba con un OR desde el
# principio), así que una VFC baja hoy Y cayendo no vale por dos.
_GRUPOS_DE_FLAG: tuple[tuple[str, ...], ...] = (
    ("hrv_delta", "hrv_trend"),
    ("training_readiness",),
    ("body_battery",),
    ("acwr",),
    ("sleep",),
)


def compute_readiness(ctx: RecoveryContext) -> ReadinessLevel:
    """Semáforo de readiness diario (RED/YELLOW/GREEN).

    Regla dura no negociable: dolor articular -> RED siempre, sin
    importar el resto de señales (Ibrahim et al. 2024).

    Para el resto de señales se cuentan "red flags" y "yellow flags"
    (patrón documentado en la literatura de autorregulación, ver
    Ibrahim/Beaumont/Strohacker 2024): 1+ red flag -> RED; 2+ yellow
    flags sin red flags -> YELLOW; en otro caso -> GREEN.

    Cuenta sobre el resultado de `assess_signals` en vez de repetir las
    comparaciones: el veredicto y la explicación que la interfaz muestra
    salen así del MISMO cálculo y no pueden contradecirse. Antes eran
    dos listas de umbrales, una aquí y otra implícita en la pantalla.
    """
    if ctx.joint_pain_flag:
        return ReadinessLevel.RED

    por_senal = {s.senal: s.estado for s in assess_signals(ctx)}
    estados_de_grupo = [
        {por_senal[nombre] for nombre in grupo} for grupo in _GRUPOS_DE_FLAG
    ]
    red_flags = sum(1 for estados in estados_de_grupo if SignalState.RED in estados)
    yellow_flags = sum(
        1
        for estados in estados_de_grupo
        if SignalState.RED not in estados and SignalState.YELLOW in estados
    )

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
