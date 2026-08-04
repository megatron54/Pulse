"""Resumen periódico (semanal/mensual) de tendencias - Épica MUST-HAVE
#4 del backlog priorizado (02-roadmap/03-vision-produccion.md):
agregación pura sobre datos ya existentes (readiness, carga de
entrenamiento, peso, actividades Garmin), sin ninguna integración
externa nueva.

Principio "unknown is not zero" aplicado a agregados: cada campo que
puede faltar por completo (peso, actividades) se deja en `None`/`0`
distinguiendo explícitamente "no hay dato en la ventana" (campos en
`None` o contadores en `0`, que aquí SÍ son informativos: "0
actividades" es un hecho real, no una ausencia de medición) de
"la ventana tiene datos parciales" (p.ej. `peso_delta_kg=None` con
`peso_inicio_kg`/`peso_fin_kg` iguales cuando solo hay una medición -
no se fabrica una tendencia de una sola muestra)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models.schema import UserProfile
from repositories.body_measurements_repository import get_weight_history
from repositories.garmin_repository import get_activity_history
from repositories.readiness_log_repository import get_readiness_history
from services.errors import EntityNotFoundError
from services.training_load_service import TrainingLoadResult, compute_training_load

_DIAS_POR_DEFECTO = 7


@dataclass(frozen=True)
class PeriodicSummaryResult:
    dias_con_checkin_readiness: int
    distribucion_readiness: dict[str, int]
    training_load: TrainingLoadResult
    peso_inicio_kg: float | None
    peso_fin_kg: float | None
    peso_delta_kg: float | None
    actividades_totales: int
    duracion_actividades_total_seg: int


def _distribucion_readiness_por_dia(historial) -> tuple[dict[str, int], int]:
    """`historial` viene en orden cronológico ascendente y puede tener
    varias filas el mismo día (append-only, re-check-ins) - se queda
    con la última fila de cada día antes de contar, mismo criterio que
    `get_latest_readiness_level` usa para un solo día."""
    ultimo_resultado_por_dia: dict[date, str] = {}
    for log in historial:
        ultimo_resultado_por_dia[log.fecha] = log.resultado

    distribucion = {"green": 0, "yellow": 0, "red": 0}
    for resultado in ultimo_resultado_por_dia.values():
        distribucion[resultado] += 1
    return distribucion, len(ultimo_resultado_por_dia)


def _peso_inicio_fin_delta(
    historial_peso: list,
) -> tuple[float | None, float | None, float | None]:
    """Colapsa a UN peso por día (última fila del día gana, mismo
    criterio que `get_latest_weight_kg`) antes de calcular inicio/fin/
    delta - `get_weight_history` devuelve TODAS las filas sin agregar
    por diseño (ver su propio docstring), así que sin este paso una
    resincronización con varias filas el mismo día fabricaría una
    "tendencia" intra-día de una sola medición real (hallazgo H1 de
    code-review). El delta solo se calcula con >= 2 DÍAS distintos, no
    >= 2 filas."""
    ultimo_peso_por_dia: dict[date, float] = {}
    for medicion in historial_peso:
        ultimo_peso_por_dia[medicion.fecha] = medicion.peso_kg

    if not ultimo_peso_por_dia:
        return None, None, None

    dias_ordenados = sorted(ultimo_peso_por_dia)
    peso_inicio = ultimo_peso_por_dia[dias_ordenados[0]]
    peso_fin = ultimo_peso_por_dia[dias_ordenados[-1]]
    delta = peso_fin - peso_inicio if len(dias_ordenados) >= 2 else None
    return peso_inicio, peso_fin, delta


def compute_periodic_summary(
    session: Session, user_id: int, as_of: date, days: int = _DIAS_POR_DEFECTO
) -> PeriodicSummaryResult:
    """Nota sobre `training_load`: usa SIEMPRE las ventanas fijas 7d/28d
    de `compute_training_load` (hallazgo H2 de code-review) - el ACWR
    es una fórmula estandarizada de la literatura de carga de
    entrenamiento con esas ventanas canónicas, NO se re-escala al
    `days` del resumen. En un resumen mensual (`days=30`), readiness/
    peso/actividades reflejan el mes completo pero `training_load`
    sigue siendo el ACWR 7d/28d de siempre - es intencional, no un bug,
    pero hay que comunicarlo así en la UI (no como "ACWR del mes")."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    # Filtrado explícito a la ventana exacta `[as_of-days+1, as_of]`
    # (hallazgo CRITICAL de code-review): los repositorios subyacentes
    # NO comparten todos el mismo criterio de ventana entre sí
    # (`get_readiness_history`/`get_weight_history` devuelven `days+1`
    # días con límites inclusivos por ambos lados, mientras que
    # `get_activity_history` ya usa el criterio correcto de `days`
    # exactos) - en vez de tocar esos repositorios compartidos (usados
    # por otros módulos que pueden depender de su comportamiento
    # actual), este servicio filtra explícitamente aquí para que los
    # tres agregados usen exactamente la misma ventana entre sí.
    fecha_inicio_ventana = as_of - timedelta(days=days - 1)

    historial_readiness = [
        log
        for log in get_readiness_history(session, user_id, as_of, days)
        if log.fecha >= fecha_inicio_ventana
    ]
    distribucion, dias_con_checkin = _distribucion_readiness_por_dia(historial_readiness)

    training_load = compute_training_load(session, user_id, as_of)

    historial_peso = [
        medicion
        for medicion in get_weight_history(session, user_id, as_of, days)
        if medicion.fecha >= fecha_inicio_ventana
    ]
    peso_inicio, peso_fin, peso_delta = _peso_inicio_fin_delta(historial_peso)

    actividades = get_activity_history(session, user_id, as_of, days)
    duracion_total = sum(a.duracion_seg for a in actividades if a.duracion_seg is not None)

    return PeriodicSummaryResult(
        dias_con_checkin_readiness=dias_con_checkin,
        distribucion_readiness=distribucion,
        training_load=training_load,
        peso_inicio_kg=peso_inicio,
        peso_fin_kg=peso_fin,
        peso_delta_kg=peso_delta,
        actividades_totales=len(actividades),
        duracion_actividades_total_seg=duracion_total,
    )
