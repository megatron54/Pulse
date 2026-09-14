"""Slot de coach por deporte (Épica G2 del plan de desarrollo, Fase 1
punto 1, 02-roadmap/04-plan-desarrollo-siguiente-fase.md) - extiende
la Capa 3 generalizada (Épica H) a `/running`, `/ciclismo`, `/gimnasio`.

A diferencia de `health_narrative_service` (que explica una decisión
YA tomada por la Capa 1, el semáforo de readiness), aquí no existe
todavía un motor de reglas de carga POR DEPORTE - la "decisión" que se
explica es una comparación aritmética simple y auditable (sesiones de
la semana en curso frente a la media de las 4 semanas previas, sobre
`WeeklyVolume` ya agregado por `garmin_query_service`), no una
predicción ni un ACWR por deporte. Mismo principio "unknown is not
zero": sin ninguna actividad de esa categoría todavía, se devuelve
`None` en vez de fabricar una tendencia.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from coach.llm_client import LlmClient
from coach.narrative_service import generate_context_narrative
from models.schema import UserProfile
from services.errors import EntityNotFoundError
from services.garmin_query_service import CategoriaDeporte, get_weekly_volume_for_user

_SEMANAS_PREVIAS = 4
_TOLERANCIA_ESTABLE_PCT = 20  # variación dentro de +/-20% se lee como "estable"

_ETIQUETAS_CATEGORIA = {
    CategoriaDeporte.RUNNING: "running",
    CategoriaDeporte.CICLISMO: "ciclismo",
    CategoriaDeporte.GIMNASIO: "gimnasio",
}


@dataclass(frozen=True)
class SportNarrativeResult:
    text: str
    source: str  # "llm" | "template"


def _etiqueta_tendencia(sesiones_actual: int, media_previas: float) -> str:
    if media_previas == 0:
        return "primera semana con actividad registrada"
    delta_pct = ((sesiones_actual - media_previas) / media_previas) * 100
    if delta_pct > _TOLERANCIA_ESTABLE_PCT:
        return "carga en aumento"
    if delta_pct < -_TOLERANCIA_ESTABLE_PCT:
        return "carga en descenso"
    return "carga estable"


def generate_sport_narrative_for_user(
    session: Session,
    user_id: int,
    categoria: CategoriaDeporte,
    as_of: date,
    llm_client: LlmClient | None,
) -> SportNarrativeResult | None:
    """`None` si no hay ninguna actividad de `categoria` registrada
    todavía en la semana actual ni en las `_SEMANAS_PREVIAS` previas -
    nunca se inventa una tendencia de carga sin datos reales."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    semanas = get_weekly_volume_for_user(
        session, user_id, as_of=as_of, categoria=categoria, weeks=_SEMANAS_PREVIAS + 1
    )
    semana_actual = semanas[-1]
    semanas_previas = semanas[:-1]

    if semana_actual.num_sesiones == 0 and all(s.num_sesiones == 0 for s in semanas_previas):
        return None

    media_previas = (
        sum(s.num_sesiones for s in semanas_previas) / len(semanas_previas)
        if semanas_previas
        else 0.0
    )
    decision_label = _etiqueta_tendencia(semana_actual.num_sesiones, media_previas)

    # Claves en español legible: si cae a la plantilla de respaldo se ven
    # tal cual en pantalla (doctrina 8), y `_formatear_datos_legibles`
    # (narrative_service.py) solo cambia "_" por espacios, no traduce.
    datos = {
        "sesiones esta semana": semana_actual.num_sesiones,
        "media de sesiones en las 4 semanas previas": (
            round(media_previas, 1) if media_previas else None
        ),
        "distancia esta semana (km)": (
            round(semana_actual.distancia_total_m / 1000, 1)
            if semana_actual.distancia_total_m is not None
            else None
        ),
    }

    resultado = generate_context_narrative(
        contexto=_ETIQUETAS_CATEGORIA[categoria],
        decision_label=decision_label,
        datos=datos,
        llm_client=llm_client,
    )
    return SportNarrativeResult(text=resultado.text, source=resultado.source)
