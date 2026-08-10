"""Orquesta la sincronización diaria masiva de Garmin para TODOS los
usuarios con `GarminCredentials` activas (Fase C del plan autónomo,
docs/02-roadmap/02-plan-autonomo.md).

Este módulo es el punto de entrada que usará el scheduler (APScheduler,
ver `scheduler/app.py`) para ejecutar el job nocturno. Sin credenciales
reales todavía (Fase H sigue bloqueada por falta de una cuenta Garmin de
prueba), pero la infraestructura queda lista: en cuanto exista al menos
una fila en `GarminCredentials`, el job empieza a sincronizar de verdad
sin cambios de código.

Limitación conocida y documentada: `acwr` y `joint_pain_flag` no pueden
calcularse/obtenerse de forma automática todavía (ver docstring de
`services.readiness_service.sync_and_compute_readiness`) - joint_pain_flag
es inherentemente una entrada manual, y ACWR no tiene motor de cálculo
dedicado aún. El job nocturno usa por tanto los valores neutrales
documentados (acwr=1.0, joint_pain_flag=False) en vez de bloquear la
sincronización automática; esto NUNCA debe inventar una señal de dolor
articular o de carga de entrenamiento que no existe. Cuando el usuario
quiera declarar dolor articular real, debe seguir usando el check-in
manual (`services.readiness_service.record_manual_readiness`), que
sobreescribe/complementa este resultado automático vía el mismo patrón
append-only de `ReadinessLog`.

Principio de aislamiento: un fallo sincronizando UN usuario nunca debe
impedir sincronizar a los demás - mismo principio que
`garmin_sync.client._llamada_segura` aplica campo a campo, aquí aplicado
usuario a usuario.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from garmin_sync.client import GarminClient
from models.schema import AuditLog, GarminCredentials
from services.garmin_activity_service import sync_activities
from services.garmin_intraday_service import sync_intraday_metrics
from services.readiness_service import sync_and_compute_readiness

_ACWR_NEUTRAL_POR_DEFECTO = 1.0
_JOINT_PAIN_FLAG_POR_DEFECTO = False
_VENTANA_ACTIVIDADES_DIAS_POR_DEFECTO = 3


@dataclass(frozen=True)
class SyncBatchResult:
    """Resumen del resultado de una pasada de sincronización masiva."""

    exitosos: int
    fallidos: int
    omitidos: int


def run_daily_sync_for_all_users(
    session: Session,
    target_date: date,
    api_factory: Callable[..., Any] | None = None,
) -> SyncBatchResult:
    """Sincroniza `target_date` para cada usuario con `GarminCredentials`
    activas, registrando en `AuditLog` (modulo="scheduler") tanto los
    fallos individuales como - implícitamente vía `ReadinessLog` - los
    éxitos, para no perder trazabilidad de qué corrió cada noche.

    Nunca lanza excepción por un fallo individual: acumula el conteo y
    continúa con el siguiente usuario. Si `session.commit()` en sí mismo
    fallara (p.ej. la base de datos caída), esa excepción sí se propaga,
    porque en ese caso ningún usuario podría sincronizarse igualmente.
    """
    credenciales_activas = (
        session.query(GarminCredentials).filter_by(activo=True).all()
    )

    exitosos = 0
    fallidos = 0
    omitidos = (
        session.query(GarminCredentials).filter_by(activo=False).count()
    )

    for cred in credenciales_activas:
        try:
            garmin_client = GarminClient(
                token_store_dir=cred.token_store_dir,
                api_factory=api_factory,
            )
            garmin_client.login()
            sync_and_compute_readiness(
                session,
                user_id=cred.user_id,
                garmin_client=garmin_client,
                target_date=target_date,
                acwr=_ACWR_NEUTRAL_POR_DEFECTO,
                joint_pain_flag=_JOINT_PAIN_FLAG_POR_DEFECTO,
            )
            exitosos += 1
            # Serie minuto a minuto (petición explícita del usuario:
            # "quiero todo ese histórico, no me vale que cojas la media
            # del día") - preocupación INDEPENDIENTE del agregado diario
            # de arriba: un fallo aquí no debe invalidar un sync de
            # recovery ya exitoso, así que se aísla en su propio
            # try/except y su propio commit, sin afectar a
            # `exitosos`/`fallidos`.
            try:
                sync_intraday_metrics(session, cred.user_id, garmin_client, target_date)
                session.commit()
            except Exception as exc_intradia:  # noqa: BLE001 - aislamiento intencional
                session.rollback()
                try:
                    session.add(
                        AuditLog(
                            user_id=cred.user_id,
                            modulo="scheduler",
                            inputs_json={"target_date": target_date.isoformat()},
                            regla_disparada="sync_intradia_fallido",
                            output="error",
                            decision_final=str(exc_intradia)[:200],
                        )
                    )
                    session.commit()
                except Exception:  # noqa: BLE001 - misma salvaguarda que la auditoría de recovery
                    session.rollback()
        except Exception as exc:  # noqa: BLE001 - aislamiento intencional por usuario
            session.rollback()
            try:
                session.add(
                    AuditLog(
                        user_id=cred.user_id,
                        modulo="scheduler",
                        inputs_json={"target_date": target_date.isoformat()},
                        regla_disparada="sync_diario_fallido",
                        output="error",
                        decision_final=str(exc)[:200],
                    )
                )
                session.commit()
            except Exception:  # noqa: BLE001 - la auditoría del fallo NUNCA
                # debe poder tumbar el resto del batch (p.ej. FK inválida si
                # el usuario fue borrado entre la lectura de credenciales y
                # este punto). Se descarta el intento de auditoría y se
                # sigue con el resto de usuarios; el conteo en `fallidos`
                # ya refleja que este usuario no se sincronizó.
                session.rollback()
            fallidos += 1

    return SyncBatchResult(exitosos=exitosos, fallidos=fallidos, omitidos=omitidos)


def run_daily_activity_sync_for_all_users(
    session: Session,
    end_date: date,
    api_factory: Callable[..., Any] | None = None,
    ventana_dias: int = _VENTANA_ACTIVIDADES_DIAS_POR_DEFECTO,
) -> SyncBatchResult:
    """Ingiere actividades (carrera/ciclismo/fuerza) para cada usuario
    con `GarminCredentials` activas, en la ventana
    `[end_date-ventana_dias+1, end_date]`.

    Función SEPARADA de `run_daily_sync_for_all_users` (recovery)
    aunque comparten el mismo login/aislamiento por usuario - son dos
    preocupaciones independientes con cadencias razonables distintas:
    recovery necesita el día exacto de ayer, actividades puede mirar
    una ventana de varios días para no perder actividades que Garmin
    tarda en consolidar o que el job nocturno anterior no vio todavía
    (idempotente vía `save_activity_if_new`, así que revisitar días ya
    sincronizados nunca duplica).

    Mismo principio de aislamiento por usuario que
    `run_daily_sync_for_all_users`: un fallo (login, rate-limit)
    sincronizando un usuario nunca debe impedir sincronizar a los
    demás."""
    credenciales_activas = session.query(GarminCredentials).filter_by(activo=True).all()

    exitosos = 0
    fallidos = 0
    omitidos = session.query(GarminCredentials).filter_by(activo=False).count()
    start_date = end_date - timedelta(days=ventana_dias - 1)

    for cred in credenciales_activas:
        try:
            garmin_client = GarminClient(
                token_store_dir=cred.token_store_dir,
                api_factory=api_factory,
            )
            garmin_client.login()
            sync_activities(session, cred.user_id, garmin_client, start_date, end_date)
            exitosos += 1
        except Exception as exc:  # noqa: BLE001 - aislamiento intencional por usuario
            session.rollback()
            try:
                session.add(
                    AuditLog(
                        user_id=cred.user_id,
                        modulo="scheduler_activities",
                        inputs_json={
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                        },
                        regla_disparada="sync_actividades_fallido",
                        output="error",
                        decision_final=str(exc)[:200],
                    )
                )
                session.commit()
            except Exception:  # noqa: BLE001 - misma salvaguarda que la auditoría de recovery
                session.rollback()
            fallidos += 1

    return SyncBatchResult(exitosos=exitosos, fallidos=fallidos, omitidos=omitidos)
