"""Ingesta y consulta de la serie minuto a minuto de Garmin (petición
explícita del usuario: "el ritmo cardiaco, body battery, etc son
valores que cambian cada minuto, quiero todo ese histórico, no me vale
que cojas la media del día").

Ingesta idempotente por diseño (a diferencia de `save_daily_metrics`,
que es append-only sin UNIQUE): la sincronización de un día puede
correr varias veces (backfill + sync frecuente + resincronización
manual) y NUNCA debe duplicar un punto ya guardado - con cientos de
puntos por día, el patrón "check-then-insert punto a punto" de
`save_activity_if_new` sería demasiado lento (un roundtrip por punto).
Aquí se hace una única consulta de los timestamps ya existentes en el
rango, y un solo INSERT masivo con los puntos realmente nuevos."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.schema import GarminIntradayMetric


def save_intraday_points(
    session: Session,
    user_id: int,
    metrica: str,
    fecha: date,
    puntos: list[tuple[int, float]],
) -> int:
    """Persiste `puntos` (`[(timestamp_ms, valor), ...]`) para
    `metrica`, devolviendo cuántos eran realmente nuevos.

    `fecha` se recibe como parámetro EXPLÍCITO (el día calendario que
    se le pidió a Garmin, ej. `garmin_client.get_intraday_series_raw(
    target_date.isoformat())`) en vez de derivarse del timestamp UTC de
    cada punto (hallazgo de code-review): Garmin ya agrupa la serie por
    día calendario de la cuenta/dispositivo al responder a la llamada -
    recalcular la fecha a partir de un timestamp UTC desplazaba
    incorrectamente los puntos de madrugada (23:00-01:00 hora local) al
    día UTC equivocado, dejando huecos justo en la franja de sueño que
    más interesa mirar."""
    if not puntos:
        return 0

    timestamps_utc = [datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(tzinfo=None) for ts_ms, _ in puntos]

    existentes = set(
        session.execute(
            select(GarminIntradayMetric.timestamp_utc).where(
                GarminIntradayMetric.user_id == user_id,
                GarminIntradayMetric.metrica == metrica,
                GarminIntradayMetric.timestamp_utc.in_(timestamps_utc),
            )
        )
        .scalars()
        .all()
    )

    filas_nuevas = [
        GarminIntradayMetric(
            user_id=user_id,
            metrica=metrica,
            fecha=fecha,
            timestamp_utc=ts,
            valor=valor,
        )
        for ts, (_, valor) in zip(timestamps_utc, puntos)
        if ts not in existentes
    ]
    if not filas_nuevas:
        return 0

    session.add_all(filas_nuevas)
    session.commit()
    return len(filas_nuevas)


def get_intraday_history(
    session: Session, user_id: int, metrica: str, fecha: date
) -> list[GarminIntradayMetric]:
    """Puntos de `metrica` para `fecha`, en orden cronológico - para
    graficar la serie minuto a minuto de un día concreto."""
    return list(
        session.execute(
            select(GarminIntradayMetric)
            .where(
                GarminIntradayMetric.user_id == user_id,
                GarminIntradayMetric.metrica == metrica,
                GarminIntradayMetric.fecha == fecha,
            )
            .order_by(GarminIntradayMetric.timestamp_utc.asc())
        )
        .scalars()
        .all()
    )
