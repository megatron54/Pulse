"""Repositorio de historial de readiness — usado por engine.guardrails
para detectar rachas de RED sostenido (ver should_pause_calorie_deficit
en 00-research/06-periodizacion-ciencia-deportiva.md)."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.periodization import ReadinessLevel
from models.schema import ReadinessLog


def get_latest_readiness_level(
    session: Session, user_id: int, target_date: date
) -> ReadinessLevel | None:
    """El resultado de readiness más reciente para `user_id` en
    `target_date` (append-only: puede haber varias filas si se
    re-ejecutó el check-in ese día - se usa siempre la última, mismo
    criterio que `services.session_service` y `services.readiness_service`).
    Devuelve None si no hay ningún ReadinessLog para ese día.

    Centraliza esta consulta para que tanto `services.session_service`
    como la capa HTTP (api/routers/session.py) usen exactamente la misma
    lógica, evitando que dos queries independientes puedan divergir.
    """
    log = (
        session.query(ReadinessLog)
        .filter_by(user_id=user_id, fecha=target_date)
        .order_by(ReadinessLog.created_at.desc(), ReadinessLog.id.desc())
        .first()
    )
    return ReadinessLevel(log.resultado) if log is not None else None


def get_readiness_log_for_date(
    session: Session, user_id: int, target_date: date
) -> ReadinessLog | None:
    """La fila COMPLETA de ReadinessLog más reciente para `user_id` en
    `target_date` (mismo criterio "la última gana" que
    `get_latest_readiness_level`, que solo devuelve el `resultado`
    aislado). Épica H del plan de expansión (02-roadmap/
    03-vision-produccion.md): el coach de salud necesita más campos
    estructurados (`sesion_recomendada`, `hrv_delta_pct`...) para poder
    explicar la decisión, no solo el semáforo."""
    return (
        session.query(ReadinessLog)
        .filter_by(user_id=user_id, fecha=target_date)
        .order_by(ReadinessLog.created_at.desc(), ReadinessLog.id.desc())
        .first()
    )


def get_recent_readiness_levels(
    session: Session, user_id: int, as_of: date, n: int
) -> list[ReadinessLevel]:
    """Últimos `n` resultados de readiness ANTERIORES a `as_of` (no
    incluye el día actual, que aún no se ha calculado en el momento en
    que se consulta este historial), en orden cronológico ascendente -
    el formato que espera engine.guardrails.should_pause_calorie_deficit."""
    fecha_inicio = as_of - timedelta(days=n)
    stmt = (
        select(ReadinessLog.resultado)
        .where(ReadinessLog.user_id == user_id)
        .where(ReadinessLog.fecha >= fecha_inicio)
        .where(ReadinessLog.fecha < as_of)
        .order_by(ReadinessLog.fecha.asc())
    )
    filas = session.execute(stmt).scalars().all()
    return [ReadinessLevel(valor) for valor in filas]


def get_readiness_history(
    session: Session, user_id: int, as_of: date, days: int
) -> list[ReadinessLog]:
    """Historial de ReadinessLog de los últimos `days` días EXACTOS,
    INCLUYENDO `as_of` - para dashboards de tendencia (Fase I). A
    diferencia de `get_recent_readiness_levels` (usado por guardrails,
    que excluye el día actual a propósito porque ese aún se está
    calculando en el momento de la consulta), aquí sí interesa el dato
    de hoy si ya existe.

    Corregido el off-by-one histórico (hallazgo #10 del doc vivo,
    02-roadmap/03-vision-produccion.md): antes devolvía `days+1` días
    (límites inclusivos por ambos lados sobre `as_of - timedelta(days)`)
    - ahora la ventana es exactamente `[as_of-days+1, as_of]`, mismo
    criterio que `get_activity_history`/`get_daily_metrics_history`.
    `services.periodic_summary_service` ya filtraba explícitamente para
    compensar esta inconsistencia; ese filtro queda ahora redundante
    pero inofensivo (no cambia ningún resultado)."""
    fecha_inicio = as_of - timedelta(days=days - 1)
    stmt = (
        select(ReadinessLog)
        .where(ReadinessLog.user_id == user_id)
        .where(ReadinessLog.fecha >= fecha_inicio)
        .where(ReadinessLog.fecha <= as_of)
        .order_by(ReadinessLog.fecha.asc(), ReadinessLog.id.asc())
    )
    return list(session.execute(stmt).scalars().all())


def set_volumen_pct_ajustado(
    session: Session, user_id: int, target_date: date, volumen_pct: int
) -> None:
    """Adjunta el `volume_pct` finalmente decidido por
    `services.session_service.compute_daily_session` a la fila de
    `ReadinessLog` de ese día - cierra el hueco real encontrado en la
    Fase de carga de entrenamiento numérica (docs/02-roadmap/
    03-vision-produccion.md): el campo `volumen_pct_ajustado` existía
    en el schema desde el principio pero ningún código lo escribía
    nunca, así que no había historial real de carga con el que calcular
    un ACWR de verdad (el ACWR de hoy es un número que el usuario
    escribe a mano en el check-in, no una medida).

    Si hay varias filas ese día (append-only, re-check-ins), actualiza
    la más reciente - mismo criterio de "la última gana" que
    `get_latest_readiness_level`. Si no hay NINGUNA fila ese día (se
    pidió una sesión sin haber hecho check-in de recuperación), no hay
    nada a lo que adjuntar el volumen - no falla, simplemente no hace
    nada, para no romper el flujo de `compute_daily_session` por un
    dato que no es indispensable en el momento en que se calcula."""
    log = (
        session.query(ReadinessLog)
        .filter_by(user_id=user_id, fecha=target_date)
        .order_by(ReadinessLog.created_at.desc(), ReadinessLog.id.desc())
        .first()
    )
    if log is None:
        return
    log.volumen_pct_ajustado = volumen_pct
    session.commit()


def get_volumen_pct_history(
    session: Session, user_id: int, as_of: date, days: int
) -> list[tuple[date, int]]:
    """Historial de `(fecha, volumen_pct_ajustado)` de los últimos
    `days` días EXACTOS (incluyendo `as_of`, ventana `[as_of-days+1,
    as_of]` - mismo criterio que usa `services.training_load_service`
    para la ventana aguda, corregido aquí para la crónica tras un
    hallazgo real de code-review: la ventana anterior usaba
    `as_of - timedelta(days=days)` con límites inclusivos por ambos
    lados, lo que daba `days+1` días reales en vez de `days` - un
    ACWR "de 28 días" que en realidad promediaba 29).

    Se queda con la fila más reciente **que tenga volumen asignado**
    si hubo varias ese día (no simplemente la fila más reciente a
    secas: una fila nueva sin volumen todavía - p.ej. un re-check-in de
    recuperación posterior en el mismo día antes de que
    `session_service` calcule la sesión - no debe borrar el volumen ya
    registrado por una fila anterior ese mismo día). OMITE los días sin
    ningún volumen asignado todavía (principio "unknown is not zero":
    no rellenar con 0, que se leería como "no entrenaste" en vez de "no
    hay dato"). Base para `services.training_load_service.
    compute_training_load` (medias móviles 7d/28d, ACWR real)."""
    fecha_inicio = as_of - timedelta(days=days - 1)
    stmt = (
        select(ReadinessLog)
        .where(ReadinessLog.user_id == user_id)
        .where(ReadinessLog.fecha >= fecha_inicio)
        .where(ReadinessLog.fecha <= as_of)
        .order_by(ReadinessLog.fecha.asc(), ReadinessLog.id.asc())
    )
    filas = session.execute(stmt).scalars().all()
    por_fecha: dict[date, int] = {}
    for fila in filas:
        if fila.volumen_pct_ajustado is not None:
            por_fecha[fila.fecha] = fila.volumen_pct_ajustado
    return sorted(por_fecha.items())
