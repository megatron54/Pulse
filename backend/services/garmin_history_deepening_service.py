"""Extiende gradualmente el histórico de Garmin de cada usuario hacia
atrás en el tiempo (petición explícita del usuario: "sería genial tener
todo mi historial, no solo los últimos 90 días").

Deliberadamente NO se hace de una vez (un backfill de años día a día es
justo el patrón de volumen de peticiones que documenta
`garmin_backfill_service` como riesgo de rate-limit/bloqueo de cuenta -
el mismo problema real que ya sufrió el usuario al conectar). En su
lugar, cada pasada (pensada para correr una vez por noche, ver
`scheduler/app.py`) retrocede como mucho `dias_por_pasada` días más allá
de `GarminCredentials.historial_sincronizado_desde`, hasta llegar a
`dias_maximo_historial` (por defecto ~2 años) o hasta que Garmin
empiece a fallar por falta de datos más antiguos (se detiene ese
usuario, no aborta el resto del batch).

Mismo principio de aislamiento que `scheduler_service`: un fallo con UN
usuario nunca debe impedir que los demás avancen su propio histórico.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from garmin_sync.client import GarminClient
from models.schema import GarminCredentials
from services.garmin_backfill_service import backfill_full_history

# ~2 años: suficiente para ver tendencias estacionales de entrenamiento
# sin ser "todo lo que Garmin tenga" (algunos relojes ni siquiera
# retienen tanto en su propio historial online). Configurable por el
# llamante (`scheduler/app.py` lo expone vía variable de entorno) si el
# usuario quiere ampliarlo una vez visto que no dispara ningún bloqueo.
DIAS_MAXIMO_HISTORIAL_POR_DEFECTO = 730
# Ritmo conservador: ~10 llamadas/día * 30 días = 300 peticiones/noche
# por usuario, muy por debajo de las ~900 de una sola vez que causaron
# el rate-limit original, y separado por 24h entre pasadas.
DIAS_POR_PASADA_POR_DEFECTO = 30


@dataclass(frozen=True)
class DeepeningResult:
    usuarios_avanzados: int
    usuarios_completos: int
    usuarios_fallidos: int


def deepen_history_for_all_users(
    session: Session,
    *,
    hoy: date | None = None,
    dias_por_pasada: int = DIAS_POR_PASADA_POR_DEFECTO,
    dias_maximo_historial: int = DIAS_MAXIMO_HISTORIAL_POR_DEFECTO,
    api_factory: Callable[..., Any] | None = None,
) -> DeepeningResult:
    hoy = hoy or date.today()
    limite_historial = hoy - timedelta(days=dias_maximo_historial - 1)

    credenciales_activas = (
        session.query(GarminCredentials)
        .filter_by(activo=True)
        # Solo usuarios que ya completaron su backfill inicial (tienen
        # una frontera de la que partir) y que todavía no alcanzaron el
        # límite de histórico configurado.
        .filter(GarminCredentials.historial_sincronizado_desde.is_not(None))
        .filter(GarminCredentials.historial_sincronizado_desde > limite_historial)
        .all()
    )

    avanzados = 0
    completos = 0
    fallidos = 0

    for cred in credenciales_activas:
        frontera_actual = cred.historial_sincronizado_desde
        assert frontera_actual is not None  # ya filtrado arriba
        nuevo_fin = frontera_actual - timedelta(days=1)
        nuevo_inicio = max(nuevo_fin - timedelta(days=dias_por_pasada - 1), limite_historial)

        if nuevo_inicio > nuevo_fin:
            completos += 1
            continue

        try:
            garmin_client = GarminClient(
                token_store_dir=cred.token_store_dir,
                api_factory=api_factory,
            )
            garmin_client.login()
            backfill_full_history(
                session,
                user_id=cred.user_id,
                garmin_client=garmin_client,
                start_date=nuevo_inicio,
                end_date=nuevo_fin,
            )
            cred.historial_sincronizado_desde = nuevo_inicio
            session.commit()
            avanzados += 1
            if nuevo_inicio <= limite_historial:
                completos += 1
        except Exception:  # noqa: BLE001 - aislamiento intencional por usuario, ver docstring
            session.rollback()
            fallidos += 1

    return DeepeningResult(
        usuarios_avanzados=avanzados, usuarios_completos=completos, usuarios_fallidos=fallidos
    )
