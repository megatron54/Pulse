"""Entrypoint del scheduler diario de Pulse (Fase C del plan autónomo).

Ejecuta `services.scheduler_service.run_daily_sync_for_all_users` una
vez al día a la hora configurada (por defecto 04:00, hora del servidor -
Garmin suele terminar de consolidar los datos de la noche anterior para
esa hora). Pensado para correr como proceso de larga duración separado
de la API (`python -m scheduler.app`), igual que un worker de colas.

No hace nada útil todavía en producción real: sin filas en
`GarminCredentials` (Fase H bloqueada), cada pasada sincroniza 0
usuarios y termina en <1s. Se deja corriendo igualmente porque es
infraestructura de bajo costo y cero riesgo, lista para el día en que
existan credenciales reales.
"""
from __future__ import annotations

import logging
import os
from datetime import date

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from models.database import get_session
from services.scheduler_service import (
    run_daily_activity_sync_for_all_users,
    run_daily_sync_for_all_users,
)

logger = logging.getLogger("pulse.scheduler")

_HORA_POR_DEFECTO = "4"
_MINUTO_POR_DEFECTO = "0"
# Actividades corre 15 min después del sync de recovery (mismo Garmin,
# mismo usuario, sin necesidad real de paralelismo entre ambos jobs).
_HORA_ACTIVIDADES_POR_DEFECTO = "4"
_MINUTO_ACTIVIDADES_POR_DEFECTO = "15"


def job_sincronizacion_diaria() -> None:
    """Envuelve el batch completo en try/except: un fallo inesperado no
    documentado (p.ej. la base de datos caída) no debe poder tumbar el
    proceso `BlockingScheduler` de larga duración - se registra el error
    y se espera a la siguiente ejecución programada en vez de que el
    scheduler entero deje de correr silenciosamente (MED-2 de
    code-review)."""
    session = get_session()
    try:
        resultado = run_daily_sync_for_all_users(session, target_date=date.today())
        logger.info(
            "sync diario completado: exitosos=%s fallidos=%s omitidos=%s",
            resultado.exitosos,
            resultado.fallidos,
            resultado.omitidos,
        )
    except Exception:  # noqa: BLE001 - el proceso del scheduler debe sobrevivir
        logger.exception("Fallo inesperado en el batch de sincronización diaria")
    finally:
        session.close()


def job_sincronizacion_actividades() -> None:
    """Mismo patrón de aislamiento que `job_sincronizacion_diaria`, para
    la ingestión de actividades (Épica 2 de 02-roadmap/
    03-vision-produccion.md) - job separado a propósito, ver docstring
    de `run_daily_activity_sync_for_all_users`."""
    session = get_session()
    try:
        resultado = run_daily_activity_sync_for_all_users(session, end_date=date.today())
        logger.info(
            "sync de actividades completado: exitosos=%s fallidos=%s omitidos=%s",
            resultado.exitosos,
            resultado.fallidos,
            resultado.omitidos,
        )
    except Exception:  # noqa: BLE001 - el proceso del scheduler debe sobrevivir
        logger.exception("Fallo inesperado en el batch de sincronización de actividades")
    finally:
        session.close()


def build_scheduler() -> BlockingScheduler:
    hora = os.environ.get("PULSE_SCHEDULER_HORA", _HORA_POR_DEFECTO)
    minuto = os.environ.get("PULSE_SCHEDULER_MINUTO", _MINUTO_POR_DEFECTO)
    hora_actividades = os.environ.get(
        "PULSE_SCHEDULER_ACTIVIDADES_HORA", _HORA_ACTIVIDADES_POR_DEFECTO
    )
    minuto_actividades = os.environ.get(
        "PULSE_SCHEDULER_ACTIVIDADES_MINUTO", _MINUTO_ACTIVIDADES_POR_DEFECTO
    )

    scheduler = BlockingScheduler()
    scheduler.add_job(
        job_sincronizacion_diaria,
        trigger=CronTrigger(hour=hora, minute=minuto),
        id="sync_diario_garmin",
        replace_existing=True,
    )
    scheduler.add_job(
        job_sincronizacion_actividades,
        trigger=CronTrigger(hour=hora_actividades, minute=minuto_actividades),
        id="sync_actividades_garmin",
        replace_existing=True,
    )
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Iniciando scheduler diario de Pulse...")
    build_scheduler().start()
