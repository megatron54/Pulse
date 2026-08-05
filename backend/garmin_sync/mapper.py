"""Traduce el payload normalizado de garmin_sync.client a un
engine.periodization.RecoveryContext.

Principio "unknown is not zero" (docs/00-research/07-arquitectura-coach-ia.md):
si Garmin no entregó alguno de los campos críticos de recuperación hoy
(fallo de red puntual, campo ausente para ese día, etc.), este módulo
NUNCA rellena con un valor por defecto que enmascare la ausencia de
datos — lanza InsufficientDataError explícitamente, para que la capa
llamante decida (reintentar más tarde, usar el dato del día anterior,
pedir al usuario un check-in manual...), en vez de que
compute_readiness tome una decisión de seguridad sobre datos inventados.

`training_readiness` NO está en `_CAMPOS_CRITICOS`: varios relojes
Garmin de gama de entrada/media (Forerunner 55, 165, Instinct...) no
calculan esta métrica en absoluto - es una limitación estructural del
dispositivo (confirmado contra una cuenta real con un Forerunner 165,
Fase H), no un dato puntualmente ausente. Exigirlo bloquearía el
cálculo de readiness PARA SIEMPRE en esas cuentas. `RecoveryContext`
acepta `training_readiness=None` y simplemente no le asigna flags
(ver docstring de esa clase)."""
from __future__ import annotations

from engine.periodization import RecoveryContext

_CAMPOS_CRITICOS = ("hrv_today", "body_battery_am", "sleep_score")


class InsufficientDataError(Exception):
    """Faltan uno o más campos críticos de recuperación para el día."""


def map_garmin_raw_to_recovery_context(
    raw: dict,
    hrv_baseline_28d: float,
    hrv_trend_7d: float,
    acwr: float,
    joint_pain_flag: bool,
) -> RecoveryContext:
    """Combina el payload normalizado de Garmin (un solo día) con señales
    que requieren historial (`hrv_baseline_28d`, `hrv_trend_7d`, `acwr`,
    calculadas por otra parte del sistema) y el flag manual de dolor
    articular, para construir un RecoveryContext listo para
    engine.periodization.compute_readiness.
    """
    faltantes = [campo for campo in _CAMPOS_CRITICOS if raw.get(campo) is None]
    if faltantes:
        raise InsufficientDataError(
            f"Faltan campos críticos de recuperación de Garmin: {', '.join(faltantes)}"
        )

    return RecoveryContext(
        hrv_today=raw["hrv_today"],
        hrv_baseline_28d=hrv_baseline_28d,
        hrv_trend_7d=hrv_trend_7d,
        body_battery_am=raw["body_battery_am"],
        training_readiness=raw["training_readiness"],
        sleep_score=raw["sleep_score"],
        acwr=acwr,
        joint_pain_flag=joint_pain_flag,
    )
