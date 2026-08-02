"""Orquesta el flujo diario de readiness: sincroniza Garmin, calcula el
semáforo del motor de reglas, y persiste tanto el resultado como el
rastro de auditoría.

Conecta explícitamente:
- garmin_sync.client (ingesta) -> repositories.garmin_repository (persistencia
  + baseline/tendencia de HRV) -> garmin_sync.mapper (traducción a
  RecoveryContext) -> engine.periodization (Capa 1, decide) ->
  models.schema (persistencia del resultado + auditoría).

Ninguna lógica de decisión vive aquí: este módulo es orquestación pura.
Si el motor de reglas cambia, este módulo no debería necesitar cambios
salvo en el mapeo de campos a persistir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from engine.periodization import RecoveryContext, compute_readiness
from garmin_sync.client import GarminClient
from garmin_sync.mapper import map_garmin_raw_to_recovery_context
from models.schema import AuditLog, ReadinessLog
from repositories.garmin_repository import (
    get_hrv_baseline_28d,
    get_hrv_trend_7d,
    save_daily_metrics,
)


def sync_and_compute_readiness(
    session: Session,
    user_id: int,
    garmin_client: GarminClient,
    target_date: date,
    acwr: float,
    joint_pain_flag: bool,
) -> ReadinessLog:
    """Sincroniza los datos de recuperación de `target_date`, calcula el
    readiness del día con el motor de reglas, y persiste tanto el
    resultado (`ReadinessLog`, append-only) como una entrada de
    auditoría (`AuditLog`).

    `acwr` y `joint_pain_flag` se reciben como parámetros porque su
    cálculo/origen es responsabilidad de otros módulos: ACWR depende del
    historial de carga de entrenamiento (GarminActivity, aún sin motor
    de cálculo dedicado - ver TODO en el roadmap), y joint_pain_flag es
    inherentemente una entrada manual del usuario, nunca inferible de
    Garmin.

    Si Garmin no entrega alguno de los 4 campos críticos de recuperación
    ese día, se propaga `garmin_sync.mapper.InsufficientDataError` tal
    cual (principio "unknown is not zero") - pero el payload crudo ya se
    ha persistido en `GarminDailyMetrics` antes de ese punto, para no
    perder el dato aunque falte un campo puntual.
    """
    raw = garmin_client.get_daily_recovery_raw(target_date.isoformat())
    save_daily_metrics(session, user_id, target_date, raw)

    hrv_baseline_28d = get_hrv_baseline_28d(session, user_id, target_date)
    hrv_trend_7d = get_hrv_trend_7d(session, user_id, target_date)

    # Fallback documentado: sin historial suficiente (usuario nuevo o
    # primeros días de uso), no hay señal de desviación posible. Se
    # asume neutral (delta=0, trend=0.0) en vez de bloquear el uso desde
    # el día 1 o inventar una degradación que no está respaldada por
    # datos. Nota importante: esto deja el subsistema HRV completo
    # "mudo" durante los primeros ~7-28 días de uso - pero el resto de
    # señales (training_readiness, body_battery, acwr, sleep_score,
    # joint_pain_flag) siguen plenamente activas en compute_readiness,
    # por lo que un usuario nuevo con mala recuperación real sigue
    # pudiendo recibir RED por esas otras señales.
    if hrv_baseline_28d is None:
        # `raw["hrv_today"]` no puede ser None aquí: si lo fuera, el
        # mapper de más abajo ya habría lanzado InsufficientDataError
        # antes de que este valor se usara. Se evita `or` para no tratar
        # un HRV=0.0 (inexistente en la práctica, pero no imposible por
        # tipo) como "falsy" y sustituirlo por un 1.0 espurio.
        hrv_today = raw.get("hrv_today")
        hrv_baseline_28d = hrv_today if hrv_today is not None else 1.0
    if hrv_trend_7d is None:
        hrv_trend_7d = 0.0

    ctx: RecoveryContext = map_garmin_raw_to_recovery_context(
        raw=raw,
        hrv_baseline_28d=hrv_baseline_28d,
        hrv_trend_7d=hrv_trend_7d,
        acwr=acwr,
        joint_pain_flag=joint_pain_flag,
    )

    readiness = compute_readiness(ctx)
    hrv_delta_pct = (ctx.hrv_today - ctx.hrv_baseline_28d) / ctx.hrv_baseline_28d

    log = ReadinessLog(
        user_id=user_id,
        fecha=target_date,
        hrv_delta_pct=hrv_delta_pct,
        training_readiness=ctx.training_readiness,
        body_battery_am=ctx.body_battery_am,
        acwr=ctx.acwr,
        sleep_score=ctx.sleep_score,
        joint_pain_flag=ctx.joint_pain_flag,
        resultado=readiness.value,
    )
    session.add(log)

    session.add(
        AuditLog(
            user_id=user_id,
            modulo="periodization",
            inputs_json={
                "hrv_today": ctx.hrv_today,
                "hrv_baseline_28d": ctx.hrv_baseline_28d,
                "hrv_trend_7d": ctx.hrv_trend_7d,
                "body_battery_am": ctx.body_battery_am,
                "training_readiness": ctx.training_readiness,
                "sleep_score": ctx.sleep_score,
                "acwr": ctx.acwr,
                "joint_pain_flag": ctx.joint_pain_flag,
            },
            regla_disparada="compute_readiness",
            output=readiness.value,
            decision_final=readiness.value,
        )
    )
    session.commit()
    session.refresh(log)
    return log
