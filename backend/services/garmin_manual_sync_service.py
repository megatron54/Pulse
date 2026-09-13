"""Sync manual bajo demanda ("actualizar ahora" desde el frontend) -
complementa al job nocturno de backfill/scheduler sin sustituirlo.

Deliberadamente acotado a un puñado de días recientes (por defecto solo
HOY): a diferencia de `garmin_backfill_service.backfill_full_history`
(pensado para 90 días de histórico en una conexión nueva), este módulo
existe justo para el caso contrario - refrescar el día en curso con
pocas llamadas (recovery + intradía de un solo día = 10 peticiones a
Garmin), sin el riesgo de rate-limit de un backfill amplio. Ver
docstring de `garmin_backfill_service` para el razonamiento completo
del riesgo de volumen de peticiones.

También es la base del job de sync frecuente (`scheduler/app.py`,
cada 1-3h) que da datos "quasi en tiempo real": mismo camino, solo
cambia quién lo dispara (usuario vs. cron)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from garmin_sync.client import GarminClient
from repositories.garmin_credentials_repository import get_active_garmin_credentials
from services.errors import EntityNotFoundError
from services.garmin_intraday_service import sync_intraday_metrics
from services.readiness_service import sync_and_compute_readiness

_ACWR_NEUTRAL_POR_DEFECTO = 1.0
_JOINT_PAIN_FLAG_POR_DEFECTO = False


class GarminNoConectadoError(EntityNotFoundError):
    """El usuario no tiene una cuenta de Garmin conectada (o fue
    desactivada) - no hay `token_store_dir` con el que autenticar."""


@dataclass(frozen=True)
class ManualSyncResult:
    fecha: date
    puntos_intradia_nuevos: int


def sync_today_for_user(
    session: Session,
    user_id: int,
    *,
    target_date: date | None = None,
) -> ManualSyncResult:
    """Sincroniza `target_date` (por defecto hoy) para un único usuario,
    reutilizando el mismo camino de dominio que el job nocturno
    (`sync_and_compute_readiness`/`sync_intraday_metrics`) - un solo
    login, sin backfill de días anteriores. Propaga
    `GarminRateLimitedError`/`GarminAuthError` tal cual si el login
    falla (mismo contrato que el resto de los flujos de Garmin), para
    que la capa API los traduzca a 429/401."""
    cred = get_active_garmin_credentials(session, user_id)
    if cred is None:
        raise GarminNoConectadoError(f"El usuario {user_id} no tiene Garmin conectado")

    target_date = target_date or date.today()

    client = GarminClient(token_store_dir=cred.token_store_dir)
    client.login()

    sync_and_compute_readiness(
        session,
        user_id=user_id,
        garmin_client=client,
        target_date=target_date,
        acwr=_ACWR_NEUTRAL_POR_DEFECTO,
        joint_pain_flag=_JOINT_PAIN_FLAG_POR_DEFECTO,
    )
    resultado_intradia = sync_intraday_metrics(session, user_id, client, target_date)
    session.commit()

    return ManualSyncResult(
        fecha=target_date, puntos_intradia_nuevos=resultado_intradia.total_puntos_nuevos
    )
