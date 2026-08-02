"""Orquesta el registro de una medición corporal del día.

Conecta: UserProfile (sexo, altura) -> engine.body_composition (Capa 1,
fórmula US Navy) -> models.BodyMeasurements (persistencia append-only)
-> AuditLog.

Diseño deliberado: registrar solo el peso (sin cinta métrica) es el caso
de uso más común (pesaje diario rápido). Cuando faltan medidas
OPCIONALES para calcular %grasa (cuello/cintura, o cadera en mujeres),
se persiste igualmente el peso con `metodo="manual"` - no es un error,
es un dato incompleto pero válido. En cambio, si las medidas SÍ se
proporcionan pero son fisiológicamente inconsistentes (ej. cintura menor
que cuello), `engine.body_composition` lanza ValueError y aquí se deja
propagar sin persistir nada a medias (ver test de transacción limpia).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from engine.body_composition import estimate_body_fat_navy
from models.schema import AuditLog, BodyMeasurements, UserProfile
from services.errors import EntityNotFoundError


def record_body_measurement(
    session: Session,
    user_id: int,
    target_date: date,
    peso_kg: float,
    cuello_cm: float | None = None,
    cintura_cm: float | None = None,
    cadera_cm: float | None = None,
) -> BodyMeasurements:
    """Registra una medición corporal para `target_date`.

    Lanza ValueError si `user_id` no existe, o si `cuello_cm`/`cintura_cm`
    se proporcionan pero son fisiológicamente inconsistentes (propagado
    desde engine.body_composition.estimate_body_fat_navy).
    """
    usuario = session.get(UserProfile, user_id)
    if usuario is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    bodyfat_min: float | None = None
    bodyfat_max: float | None = None
    metodo = "manual"
    tiene_cuello_y_cintura = cuello_cm is not None and cintura_cm is not None
    puede_calcular_navy = tiene_cuello_y_cintura
    if usuario.sexo == "F":
        puede_calcular_navy = puede_calcular_navy and cadera_cm is not None

    if puede_calcular_navy:
        regla_disparada = "estimate_body_fat_navy"
    elif tiene_cuello_y_cintura:
        # Distinción de auditoría: no es "el usuario no dio medidas",
        # es específicamente "faltó la cadera" (solo aplica a mujeres,
        # dado que tiene_cuello_y_cintura ya es True aquí).
        regla_disparada = "manual_cadera_faltante"
    else:
        regla_disparada = "manual_sin_medidas"

    if puede_calcular_navy:
        estimacion = estimate_body_fat_navy(
            sexo=usuario.sexo,
            altura_cm=usuario.altura_cm,
            cuello_cm=cuello_cm,
            cintura_cm=cintura_cm,
            cadera_cm=cadera_cm,
        )
        bodyfat_min = estimacion.rango_min
        bodyfat_max = estimacion.rango_max
        metodo = estimacion.metodo

    medicion = BodyMeasurements(
        user_id=user_id,
        fecha=target_date,
        peso_kg=peso_kg,
        cuello_cm=cuello_cm,
        cintura_cm=cintura_cm,
        cadera_cm=cadera_cm,
        bodyfat_pct_rango_min=bodyfat_min,
        bodyfat_pct_rango_max=bodyfat_max,
        metodo=metodo,
    )
    session.add(medicion)

    session.add(
        AuditLog(
            user_id=user_id,
            modulo="body_composition",
            inputs_json={
                "peso_kg": peso_kg,
                "cuello_cm": cuello_cm,
                "cintura_cm": cintura_cm,
                "cadera_cm": cadera_cm,
                "sexo": usuario.sexo,
            },
            regla_disparada=regla_disparada,
            output=metodo,
            decision_final=(
                f"bodyfat_pct=[{bodyfat_min:.1f},{bodyfat_max:.1f}]"
                if bodyfat_min is not None
                else "peso_sin_bodyfat"
            ),
        )
    )
    session.commit()
    session.refresh(medicion)
    return medicion
