"""Calcula un ACWR (Acute:Chronic Workload Ratio) REAL a partir del
historial de `volume_pct` que `session_service.compute_daily_session`
ya decide y persiste cada día - en vez del número que hoy escribe a
mano el usuario en el check-in de recuperación.

Hallazgo de la Fase MUST-HAVE #1 del backlog priorizado (docs/
02-roadmap/03-vision-produccion.md, auditoría frente a WHOOP/Garmin
Connect/Strava): "el mayor gap no son las funcionalidades exóticas de
los wearables, es que la señal de recovery de Pulse es categórica
mientras que su motor de recomendación se beneficiaría claramente de
una tendencia de carga numérica". Este módulo es esa tendencia.

Fórmula estándar de la literatura de carga de entrenamiento (misma
fuente ya citada en engine/periodization.py: Banister TSB / ACWR):
ACWR = media móvil aguda (7 días) / media móvil crónica (28 días).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from repositories.readiness_log_repository import get_volumen_pct_history

_VENTANA_AGUDA_DIAS = 7
_VENTANA_CRONICA_DIAS = 28
# 14 = la mitad de la ventana crónica. La literatura clásica de ACWR
# (Banister TSB, misma fuente citada en engine/periodization.py) pide
# los 28 días completos para que el denominador sea representativo -
# aquí se relaja conscientemente a la mitad para poder dar una señal
# temprana a un usuario nuevo, en vez de no mostrar nada durante casi
# un mes. Por debajo de este umbral el ratio existe (es informativo)
# pero se marca `datos_suficientes=False` porque el denominador está
# dominado por pocos días y es volátil.
_MINIMO_DIAS_CRONICO_PARA_CONFIAR = 14


@dataclass(frozen=True)
class TrainingLoadResult:
    """`acwr` es `None` cuando no hay suficiente historial para
    calcularlo de forma significativa (0 días de dato, o crónico=0) -
    principio "unknown is not zero": nunca se fabrica un ACWR de 1.0
    neutral aquí (ese valor neutral SÍ existe, pero vive en
    `services.scheduler_service` para el caso específico de la
    sincronización automática sin señal de dolor articular - aquí, en
    cambio, el objetivo es mostrar al usuario un dato reputadamente
    calculado o decirle explícitamente que no hay suficiente historial
    todavía, nunca rellenar con un valor inventado).

    `datos_suficientes` es una bandera de CONFIANZA, no de
    disponibilidad: un ACWR calculado con solo 5 días de historial
    crónico se devuelve igualmente (puede ser informativo), pero
    marcado como no fiable para que la UI decida si lo atenúa/avisa."""

    acute_avg_7d: float | None
    chronic_avg_28d: float | None
    acwr: float | None
    dias_con_dato_agudo: int
    dias_con_dato_cronico: int
    datos_suficientes: bool


def compute_training_load(session: Session, user_id: int, as_of: date) -> TrainingLoadResult:
    historial_cronico = get_volumen_pct_history(
        session, user_id, as_of=as_of, days=_VENTANA_CRONICA_DIAS
    )
    if not historial_cronico:
        return TrainingLoadResult(
            acute_avg_7d=None,
            chronic_avg_28d=None,
            acwr=None,
            dias_con_dato_agudo=0,
            dias_con_dato_cronico=0,
            datos_suficientes=False,
        )

    fecha_inicio_aguda = as_of.toordinal() - _VENTANA_AGUDA_DIAS + 1
    historial_agudo = [
        (fecha, volumen)
        for fecha, volumen in historial_cronico
        if fecha.toordinal() >= fecha_inicio_aguda
    ]

    chronic_avg = sum(v for _, v in historial_cronico) / len(historial_cronico)
    acute_avg = (
        sum(v for _, v in historial_agudo) / len(historial_agudo) if historial_agudo else None
    )

    acwr = None
    if acute_avg is not None and chronic_avg > 0:
        acwr = acute_avg / chronic_avg

    return TrainingLoadResult(
        acute_avg_7d=acute_avg,
        chronic_avg_28d=chronic_avg,
        acwr=acwr,
        dias_con_dato_agudo=len(historial_agudo),
        dias_con_dato_cronico=len(historial_cronico),
        datos_suficientes=len(historial_cronico) >= _MINIMO_DIAS_CRONICO_PARA_CONFIAR,
    )
