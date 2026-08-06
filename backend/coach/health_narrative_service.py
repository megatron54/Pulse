"""Primer contexto real de la Capa 3 generalizada (Épica H del plan de
expansión, 02-roadmap/03-vision-produccion.md): explica el estado de
recovery/salud de un día concreto, citando los datos crudos reales de
Garmin (HRV, body battery, sueño, estrés, pulso en reposo).

Principio no negociable preservado: la "decisión" que se explica es el
`ReadinessLog.resultado` YA calculado por
`services.readiness_service.sync_and_compute_readiness` (Capa 1/2) -
este servicio NUNCA recalcula el semáforo de recovery, solo lo lee y
construye el texto. Si ese día no tiene ningún ReadinessLog todavía
(scheduler no ha corrido, día futuro, usuario sin check-in), se
devuelve `None` explícitamente - "unknown is not zero" también aplica a
la propia decisión: no hay nada honesto que explicar sin ella.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from coach.gemini_client import GeminiClient
from coach.narrative_service import generate_context_narrative
from models.schema import UserProfile
from repositories.garmin_repository import get_daily_metrics_history, get_hrv_baseline_28d
from repositories.readiness_log_repository import get_readiness_log_for_date
from services.errors import EntityNotFoundError

_ETIQUETAS_RESULTADO = {
    "green": "recuperación buena (verde)",
    "yellow": "recuperación moderada (amarillo)",
    "red": "recuperación baja (rojo)",
}


@dataclass(frozen=True)
class HealthNarrativeResult:
    text: str
    source: str  # "llm" | "template"


def generate_health_narrative_for_user(
    session: Session,
    user_id: int,
    fecha: date,
    gemini_client: GeminiClient | None,
) -> HealthNarrativeResult | None:
    """`None` si la Capa 1 todavía no ha decidido nada para `fecha`
    (nunca se inventa un estado de recovery que no existe)."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    readiness_log = get_readiness_log_for_date(session, user_id, fecha)
    if readiness_log is None:
        return None

    metricas_del_dia = get_daily_metrics_history(session, user_id, as_of=fecha, days=1)
    metrica_hoy = metricas_del_dia[0] if metricas_del_dia else None
    baseline_hrv = get_hrv_baseline_28d(session, user_id, fecha)

    datos = {
        "hrv_hoy_ms": metrica_hoy.hrv_value if metrica_hoy else None,
        "hrv_baseline_28d_ms": round(baseline_hrv, 1) if baseline_hrv is not None else None,
        "body_battery": metrica_hoy.body_battery_am if metrica_hoy else None,
        "sleep_score": metrica_hoy.sleep_score if metrica_hoy else None,
        "estres_medio": metrica_hoy.stress_avg if metrica_hoy else None,
        "pulso_en_reposo": metrica_hoy.resting_hr if metrica_hoy else None,
    }
    decision_label = _ETIQUETAS_RESULTADO.get(readiness_log.resultado, readiness_log.resultado)

    resultado = generate_context_narrative(
        contexto="salud", decision_label=decision_label, datos=datos, gemini_client=gemini_client
    )
    return HealthNarrativeResult(text=resultado.text, source=resultado.source)
