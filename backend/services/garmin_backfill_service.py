"""Backfill histórico completo tras conectar una cuenta Garmin por
primera vez (petición explícita del usuario: "debería extraerse todo
el histórico de Garmin, no solo lo de los últimos 5 min... luego
cuando esté al día, que pida solo los últimos minutos").

Dos preocupaciones independientes, mismo principio de aislamiento que
`services.scheduler_service` ya aplica al sync incremental:
- Actividades: Garmin acepta un rango amplio en UNA sola llamada
  (`get_activities_raw`), así que no hay motivo para trocearlo día a
  día.
- Recovery (HRV/sleep/body battery/...): la API de Garmin solo da un
  día a la vez (`get_daily_recovery_raw`), así que el backfill recorre
  el rango día a día - un fallo puntual en un día concreto (Garmin no
  tenía datos ese día, error transitorio) nunca debe abortar el resto
  del rango.

Nota de seguridad de cuenta (IMPORTANTE, ver docs/00-research/
03-garmin-integracion.md): un backfill de varios AÑOS día a día contra
la API no oficial de Garmin es medio a alto riesgo de disparar
rate-limiting/bloqueo temporal de la cuenta (documentado en
`garmin_sync.client`: "reutilizar SIEMPRE el token cacheado, nunca
relogin agresivo" - el riesgo aquí es de volumen de peticiones, no de
relogin, pero la cautela aplica igual). Este módulo NO decide un rango
por defecto - la capa llamante (endpoint de conexión) es quien fija
`start_date`/`end_date`, y debe hacerlo con un valor conservador salvo
que el usuario confirme explícitamente que acepta el riesgo de un
rango más amplio."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from services.garmin_activity_service import sync_activities
from services.readiness_service import sync_and_compute_readiness

_ACWR_NEUTRAL_POR_DEFECTO = 1.0
_JOINT_PAIN_FLAG_POR_DEFECTO = False


@dataclass(frozen=True)
class BackfillResult:
    actividades_ingresadas: int
    actividades_fallo: bool
    dias_recovery_exitosos: int
    dias_recovery_fallidos: int


def backfill_full_history(
    session: Session,
    *,
    user_id: int,
    garmin_client: Any,
    start_date: date,
    end_date: date,
) -> BackfillResult:
    actividades_ingresadas = 0
    actividades_fallo = False
    try:
        resultado_actividades = sync_activities(session, user_id, garmin_client, start_date, end_date)
        actividades_ingresadas = resultado_actividades.ingresadas
        session.commit()  # mismo motivo que el commit por día de más abajo
    except Exception:  # noqa: BLE001 - aislamiento intencional, ver docstring del módulo
        session.rollback()
        actividades_fallo = True

    dias_recovery_exitosos = 0
    dias_recovery_fallidos = 0
    dia = start_date
    while dia <= end_date:
        try:
            sync_and_compute_readiness(
                session,
                user_id=user_id,
                garmin_client=garmin_client,
                target_date=dia,
                acwr=_ACWR_NEUTRAL_POR_DEFECTO,
                joint_pain_flag=_JOINT_PAIN_FLAG_POR_DEFECTO,
            )
            # Commit INMEDIATO tras cada día exitoso (hallazgo de
            # code-review, MEDIO): sin esto, un `rollback()` en un día
            # posterior que fallara revertiría también los días
            # anteriores todavía no commiteados en la misma
            # transacción - el contador `dias_recovery_exitosos`
            # mentiría respecto a lo realmente persistido en la BD.
            session.commit()
            dias_recovery_exitosos += 1
        except Exception:  # noqa: BLE001 - aislamiento día a día, ver docstring del módulo
            session.rollback()
            dias_recovery_fallidos += 1
        dia += timedelta(days=1)

    return BackfillResult(
        actividades_ingresadas=actividades_ingresadas,
        actividades_fallo=actividades_fallo,
        dias_recovery_exitosos=dias_recovery_exitosos,
        dias_recovery_fallidos=dias_recovery_fallidos,
    )
