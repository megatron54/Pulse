"""Repositorio del diario de hábitos (ver docstring de
`models.schema.HabitLog` y `models.schema.HabitCheckin` para el
razonamiento completo, incluido el hallazgo CRITICAL de code-review
que motivó la tabla `HabitCheckin`)."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from models.schema import HabitCheckin, HabitLog
from sqlalchemy.orm import Session


def set_habits_for_date(
    session: Session, user_id: int, target_date: date, habitos: list[str]
) -> None:
    """Reemplaza TODOS los hábitos registrados ese día por la lista
    dada (semántica de "guardar el check-in completo del día", no de
    "añadir uno más") - si el usuario vuelve a enviar el formulario tras
    corregirse, no se acumulan filas duplicadas ni hábitos que ya
    desmarcó. Una lista vacía borra los hábitos de ese día (el usuario
    confirmó que no ocurrió ninguno).

    Además de los hábitos en sí, registra SIEMPRE (haya marcado algo o
    no) una fila en `HabitCheckin` para esa fecha - es lo que permite a
    `get_dates_without_habit_in_window` distinguir "el usuario confirmó
    que no pasó" de "el usuario nunca hizo check-in ese día"."""
    session.query(HabitLog).filter_by(user_id=user_id, fecha=target_date).delete()
    # dedupe defensivo (MEDIUM de code-review): la API es pública y no
    # hay UNIQUE constraint en habit_log - un payload con duplicados no
    # debe inflar la tabla, aunque no afecte a la correlación (que
    # trabaja sobre sets de fechas).
    for habito in dict.fromkeys(habitos):
        session.add(HabitLog(user_id=user_id, fecha=target_date, habito=habito))

    # Upsert idempotente del checkin: si ya existe (el usuario reenvía
    # el formulario el mismo día), no debe fallar por UNIQUE constraint.
    # SELECT-then-INSERT en vez de un upsert nativo de dialecto (evitando
    # `sqlalchemy.dialects.postgresql`/`sqlite` acopladas): la tabla es
    # de escritura poco frecuente (una vez al día por usuario), así que
    # la carrera teórica entre el SELECT y el INSERT (dos requests
    # simultáneos del mismo usuario) no justifica el acoplamiento a un
    # dialecto concreto - el proyecto corre en Postgres en producción y
    # SQLite en tests (ver scripts/ensure_schema.py).
    ya_existe = (
        session.query(HabitCheckin).filter_by(user_id=user_id, fecha=target_date).first()
        is not None
    )
    if not ya_existe:
        session.add(HabitCheckin(user_id=user_id, fecha=target_date))
    session.commit()


def get_dates_with_any_checkin(
    session: Session, user_id: int, as_of: date, days: int
) -> set[date]:
    """Fechas (dentro de la ventana) en las que el usuario completó su
    check-in de hábitos, se haya marcado algo o no - base del grupo de
    "control" en `get_dates_without_habit_in_window`."""
    fecha_inicio = as_of - timedelta(days=days - 1)
    stmt = (
        select(HabitCheckin.fecha)
        .where(HabitCheckin.user_id == user_id)
        .where(HabitCheckin.fecha >= fecha_inicio)
        .where(HabitCheckin.fecha <= as_of)
    )
    return set(session.execute(stmt).scalars().all())


def get_dates_with_habit(
    session: Session, user_id: int, habito: str, as_of: date, days: int
) -> set[date]:
    """Fechas (dentro de la ventana `[as_of-days+1, as_of]`) en las que
    se registró `habito` - base para
    `services.habit_correlation_service`."""
    fecha_inicio = as_of - timedelta(days=days - 1)
    stmt = (
        select(HabitLog.fecha)
        .where(HabitLog.user_id == user_id)
        .where(HabitLog.habito == habito)
        .where(HabitLog.fecha >= fecha_inicio)
        .where(HabitLog.fecha <= as_of)
    )
    return set(session.execute(stmt).scalars().all())


def get_dates_without_habit_in_window(
    session: Session, user_id: int, habito: str, as_of: date, days: int
) -> set[date]:
    """Complementario a `get_dates_with_habit`: días de la ventana en
    los que el usuario SÍ completó su check-in de hábitos pero NO
    marcó `habito` - el grupo de "control" para la correlación.

    Deliberadamente NO usa "todos los días del calendario menos los que
    tienen el hábito" (ese fue el bug CRITICAL detectado en
    code-review): un día sin check-in no es evidencia de que el hábito
    no ocurrió, es simplemente un día sin dato, y "unknown is not
    zero"."""
    dias_registrados = get_dates_with_any_checkin(session, user_id, as_of, days)
    con_habito = get_dates_with_habit(session, user_id, habito, as_of, days)
    return dias_registrados - con_habito
