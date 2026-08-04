"""Correlaciona hábitos registrados (`HabitLog`) con el readiness del
día SIGUIENTE - un hábito de hoy (alcohol, dormir poco, estrés) afecta
la recuperación de mañana, no la de hoy mismo.

Fase MUST-HAVE #3 del backlog priorizado (02-roadmap/
03-vision-produccion.md, auditoría frente a WHOOP/Garmin Connect/
Strava): "Journal" de WHOOP - diario de hábitos con correlación
estadística frente a recovery. Investigación citada en ese documento:
WHOOP exige un mínimo de "5+5 muestras" antes de mostrar una
correlación como fiable - mismo umbral aplicado aquí.

Deliberadamente NO se usa ningún test estadístico de significancia
(p-value, chi-cuadrado...) - sería aparentar un rigor que una muestra
de 5-10 días no sostiene. Se muestra el porcentaje crudo de días RED en
cada grupo, con el tamaño de muestra siempre visible, y se deja al
usuario/coach juzgar la magnitud - coherente con "nunca falsa
precisión"."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models.schema import UserProfile
from repositories.habit_log_repository import (
    get_dates_with_habit,
    get_dates_without_habit_in_window,
)
from repositories.readiness_log_repository import get_latest_readiness_level
from services.errors import EntityNotFoundError

_VENTANA_POR_DEFECTO_DIAS = 90
_MINIMO_MUESTRAS_POR_GRUPO = 5


@dataclass(frozen=True)
class HabitCorrelationResult:
    habito: str
    dias_con_habito_con_dato: int
    dias_sin_habito_con_dato: int
    pct_red_con_habito: float | None
    pct_red_sin_habito: float | None
    datos_suficientes: bool


def _pct_red_del_dia_siguiente(session: Session, user_id: int, dias: set[date]) -> tuple[float | None, int]:
    resultados = []
    for dia in dias:
        nivel = get_latest_readiness_level(session, user_id, dia + timedelta(days=1))
        if nivel is not None:
            resultados.append(nivel.value == "red")
    if not resultados:
        return None, 0
    return sum(resultados) / len(resultados), len(resultados)


def compute_habit_correlation(
    session: Session,
    user_id: int,
    habito: str,
    as_of: date,
    window_days: int = _VENTANA_POR_DEFECTO_DIAS,
) -> HabitCorrelationResult:
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    dias_con_habito = get_dates_with_habit(session, user_id, habito, as_of, window_days)
    dias_sin_habito = get_dates_without_habit_in_window(session, user_id, habito, as_of, window_days)

    pct_con, n_con = _pct_red_del_dia_siguiente(session, user_id, dias_con_habito)
    pct_sin, n_sin = _pct_red_del_dia_siguiente(session, user_id, dias_sin_habito)

    return HabitCorrelationResult(
        habito=habito,
        dias_con_habito_con_dato=n_con,
        dias_sin_habito_con_dato=n_sin,
        pct_red_con_habito=pct_con,
        pct_red_sin_habito=pct_sin,
        datos_suficientes=(n_con >= _MINIMO_MUESTRAS_POR_GRUPO and n_sin >= _MINIMO_MUESTRAS_POR_GRUPO),
    )
