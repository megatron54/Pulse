"""Entrypoint del scheduler diario de Pulse (Fase C del plan autónomo).

Ejecuta `services.scheduler_service.run_daily_sync_for_all_users` una
vez al día a la hora configurada (por defecto 04:00, hora del servidor -
Garmin suele terminar de consolidar los datos de la noche anterior para
esa hora), MÁS un job adicional de sync frecuente del día en curso
(por defecto cada 2h) que reutiliza la misma función con
`target_date=hoy` - es lo que da datos "quasi en tiempo real" sin
volumen de peticiones adicional relevante (mismas ~10 llamadas por
usuario que ya hacía el sync nocturno, solo que repetidas varias veces
al día en vez de una). Pensado para correr como proceso de larga
duración separado de la API (`python -m scheduler.app`), igual que un
worker de colas.

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
from apscheduler.triggers.interval import IntervalTrigger

from models.database import get_session
from services.garmin_history_deepening_service import (
    DIAS_MAXIMO_HISTORIAL_POR_DEFECTO,
    DIAS_POR_PASADA_POR_DEFECTO,
    deepen_history_for_all_users,
)
from services.scheduler_service import (
    run_daily_activity_sync_for_all_users,
    run_daily_feelfit_sync_for_all_users,
    run_daily_sync_for_all_users,
)

logger = logging.getLogger("pulse.scheduler")

_HORA_POR_DEFECTO = "4"
_MINUTO_POR_DEFECTO = "0"
# Actividades corre 15 min después del sync de recovery (mismo Garmin,
# mismo usuario, sin necesidad real de paralelismo entre ambos jobs).
_HORA_ACTIVIDADES_POR_DEFECTO = "4"
_MINUTO_ACTIVIDADES_POR_DEFECTO = "15"
# Feelfit corre 30 min después (fuente independiente de Garmin, sin
# relación de orden real con los otros dos jobs - solo se espacia para
# no competir por conexión a la base de datos en el mismo instante).
_HORA_FEELFIT_POR_DEFECTO = "4"
_MINUTO_FEELFIT_POR_DEFECTO = "30"
# Sync frecuente del día en curso ("quasi tiempo real") - cada 2h por
# defecto. Reutiliza run_daily_sync_for_all_users con target_date=hoy,
# así que cada pasada solo pide el día de hoy (nunca repite días
# anteriores): el volumen de peticiones a Garmin por pasada es idéntico
# al del job nocturno, solo cambia la cadencia.
_INTERVALO_FRECUENTE_HORAS_POR_DEFECTO = "2"
# Profundización de histórico ("quiero todo mi historial, no solo 90
# días") - corre 45 min después del sync nocturno (mismo Garmin, mismo
# usuario, evita competir con los otros tres jobs de las 04:xx).
_HORA_PROFUNDIZACION_POR_DEFECTO = "4"
_MINUTO_PROFUNDIZACION_POR_DEFECTO = "45"


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


def job_sincronizacion_feelfit() -> None:
    """Mismo patrón de aislamiento que los jobs de Garmin, para la
    báscula Feelfit (petición explícita del usuario, ver docstring de
    `run_daily_feelfit_sync_for_all_users`) - fuente totalmente
    independiente de Garmin, con su propia tabla de credenciales."""
    session = get_session()
    try:
        resultado = run_daily_feelfit_sync_for_all_users(session)
        logger.info(
            "sync de Feelfit completado: exitosos=%s fallidos=%s omitidos=%s",
            resultado.exitosos,
            resultado.fallidos,
            resultado.omitidos,
        )
    except Exception:  # noqa: BLE001 - el proceso del scheduler debe sobrevivir
        logger.exception("Fallo inesperado en el batch de sincronización de Feelfit")
    finally:
        session.close()


def job_sincronizacion_frecuente() -> None:
    """Mismo patrón de aislamiento que `job_sincronizacion_diaria`,
    pero disparado cada pocas horas y siempre con `target_date=hoy` -
    ver docstring del módulo. Job SEPARADO del nocturno a propósito:
    el nocturno documenta/audita como "sync diario" y este como "sync
    frecuente", para poder distinguirlos en `AuditLog` si algo falla.

    Incluye también actividades (no solo recovery): antes de este
    cambio una actividad recién terminada no aparecía hasta el job
    nocturno de actividades (04:15), hasta 24h de retraso para algo que
    Garmin ya tiene disponible en minutos. `sync_activities` es
    idempotente (`save_activity_if_new`), así que repetirla aquí no
    duplica nada - solo añade una llamada de lista + detalle de lo
    nuevo desde la última pasada."""
    session = get_session()
    try:
        resultado = run_daily_sync_for_all_users(session, target_date=date.today())
        logger.info(
            "sync frecuente completado: exitosos=%s fallidos=%s omitidos=%s",
            resultado.exitosos,
            resultado.fallidos,
            resultado.omitidos,
        )
    except Exception:  # noqa: BLE001 - el proceso del scheduler debe sobrevivir
        logger.exception("Fallo inesperado en el batch de sincronización frecuente")
    finally:
        session.close()

    session = get_session()
    try:
        resultado_actividades = run_daily_activity_sync_for_all_users(
            session, end_date=date.today()
        )
        logger.info(
            "sync frecuente de actividades completado: exitosos=%s fallidos=%s omitidos=%s",
            resultado_actividades.exitosos,
            resultado_actividades.fallidos,
            resultado_actividades.omitidos,
        )
    except Exception:  # noqa: BLE001 - el proceso del scheduler debe sobrevivir
        logger.exception("Fallo inesperado sincronizando actividades en el batch frecuente")
    finally:
        session.close()


def job_profundizacion_historial() -> None:
    """Extiende el histórico ya sincronizado hacia atrás en pasadas
    nocturnas acotadas - ver docstring de
    `garmin_history_deepening_service`. Mismo patrón de aislamiento que
    el resto de jobs: un fallo inesperado no debe tumbar el proceso del
    scheduler."""
    session = get_session()
    try:
        dias_por_pasada = int(
            os.environ.get("PULSE_GARMIN_HISTORIAL_DIAS_POR_NOCHE", str(DIAS_POR_PASADA_POR_DEFECTO))
        )
        dias_maximo = int(
            os.environ.get("PULSE_GARMIN_HISTORIAL_MAX_DIAS", str(DIAS_MAXIMO_HISTORIAL_POR_DEFECTO))
        )
        resultado = deepen_history_for_all_users(
            session, dias_por_pasada=dias_por_pasada, dias_maximo_historial=dias_maximo
        )
        logger.info(
            "profundización de histórico completada: avanzados=%s completos=%s fallidos=%s",
            resultado.usuarios_avanzados,
            resultado.usuarios_completos,
            resultado.usuarios_fallidos,
        )
    except Exception:  # noqa: BLE001 - el proceso del scheduler debe sobrevivir
        logger.exception("Fallo inesperado profundizando el histórico de Garmin")
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
    hora_feelfit = os.environ.get("PULSE_SCHEDULER_FEELFIT_HORA", _HORA_FEELFIT_POR_DEFECTO)
    minuto_feelfit = os.environ.get(
        "PULSE_SCHEDULER_FEELFIT_MINUTO", _MINUTO_FEELFIT_POR_DEFECTO
    )
    intervalo_frecuente_horas = int(
        os.environ.get(
            "PULSE_SCHEDULER_FRECUENTE_INTERVALO_HORAS",
            _INTERVALO_FRECUENTE_HORAS_POR_DEFECTO,
        )
    )
    hora_profundizacion = os.environ.get(
        "PULSE_SCHEDULER_HISTORIAL_HORA", _HORA_PROFUNDIZACION_POR_DEFECTO
    )
    minuto_profundizacion = os.environ.get(
        "PULSE_SCHEDULER_HISTORIAL_MINUTO", _MINUTO_PROFUNDIZACION_POR_DEFECTO
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
    scheduler.add_job(
        job_sincronizacion_feelfit,
        trigger=CronTrigger(hour=hora_feelfit, minute=minuto_feelfit),
        id="sync_feelfit",
        replace_existing=True,
    )
    scheduler.add_job(
        job_sincronizacion_frecuente,
        trigger=IntervalTrigger(hours=intervalo_frecuente_horas),
        id="sync_frecuente_garmin",
        replace_existing=True,
    )
    scheduler.add_job(
        job_profundizacion_historial,
        trigger=CronTrigger(hour=hora_profundizacion, minute=minuto_profundizacion),
        id="profundizacion_historial_garmin",
        replace_existing=True,
    )
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Iniciando scheduler diario de Pulse...")
    build_scheduler().start()
