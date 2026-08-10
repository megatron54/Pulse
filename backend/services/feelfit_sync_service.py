"""Sincroniza mediciones de báscula Feelfit hacia `BodyMeasurements`
(petición explícita del usuario: conexión custom con su báscula
FeelFit, confirmada Android - ver `feelfit_client.client` para el
contrato HTTP verificado contra dos implementaciones reales).

Idempotente vía `BodyMeasurements.fuente_externa_id` (mismo criterio
que `save_activity_if_new` en `repositories.garmin_repository`): el
check-then-insert de abajo contra el set en memoria es solo una
optimización para el caso común (evita el roundtrip de un INSERT
fallido en el 99% de los casos donde de verdad es nueva) - la garantía
real de no-duplicado la da el UNIQUE(user_id, fuente_externa_id) del
esquema. Si el scheduler nocturno y un `POST /feelfit-connect` corrieran
en paralelo (carrera real: ambos llaman a esta función), el
`IntegrityError` de la fila que pierde la carrera se captura POR FILA
(commit individual, no un commit bulk al final) y se trata igual que
"ya existía" - nunca tumba el resto del lote ni se propaga como 500
(hallazgo HIGH de code-review: la versión anterior hacía un único
commit final sin capturar `IntegrityError`, así que una sola carrera
abortaba TODAS las mediciones nuevas de esa pasada, no solo la
conflictiva).

"unknown is not zero": la fecha de cada medición se deriva de
`time_stamp` (epoch UTC) - ASUNCIÓN A VALIDAR con una cuenta Feelfit
real: no está confirmado si la báscula reporta epoch en UTC puro o ya
ajustado a la zona horaria del dispositivo (mismo tipo de hallazgo que
ya tuvo `GarminIntradayMetric` con el desfase de madrugada). El epoch
crudo se conserva en `fuente_externa_id` precisamente para poder
reprocesar la fecha sin volver a golpear la API si esta asunción
resulta incorrecta."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from feelfit_client.client import FeelfitClient, normalize_measurement
from models.schema import BodyMeasurements, UserProfile
from services.errors import EntityNotFoundError


def sync_feelfit_measurements(
    session: Session, user_id: int, client: FeelfitClient, last_updated_at: int = 0
) -> int:
    """Sincroniza las mediciones nuevas desde `last_updated_at` (epoch,
    0 = todo el histórico disponible). Devuelve el número de mediciones
    NUEVAS insertadas (las ya vistas, vía `fuente_externa_id`, se
    omiten sin error).

    Lanza `EntityNotFoundError` si `user_id` no existe. Cualquier fallo
    de red/autenticación del `client` (ej. `FeelfitAuthError`) se
    propaga tal cual - la capa llamante (`scheduler_service`) ya aísla
    fallos por usuario, igual que con Garmin."""
    if session.get(UserProfile, user_id) is None:
        raise EntityNotFoundError(f"No existe UserProfile con id={user_id}")

    ids_existentes = {
        fila[0]
        for fila in session.query(BodyMeasurements.fuente_externa_id)
        .filter(
            BodyMeasurements.user_id == user_id,
            BodyMeasurements.fuente_externa_id.is_not(None),
        )
        .all()
    }

    datos = client.get_measurements_raw(last_updated_at=last_updated_at)
    mediciones_crudas = datos.get("measurements") or []

    insertadas = 0
    for cruda in mediciones_crudas:
        normalizada = normalize_measurement(cruda)
        fuente_id = normalizada["fuente_externa_id"]
        peso_kg = normalizada["peso_kg"]

        if peso_kg is None:
            # "unknown is not zero": sin peso no hay medición válida
            # que registrar (el resto de campos son complementarios).
            continue
        if fuente_id is not None and fuente_id in ids_existentes:
            continue

        timestamp_epoch = normalizada["timestamp_epoch"]
        if timestamp_epoch is None:
            continue
        fecha = datetime.fromtimestamp(timestamp_epoch, tz=timezone.utc).date()

        bodyfat_pct = normalizada["bodyfat_pct"]
        medicion = BodyMeasurements(
            user_id=user_id,
            fecha=fecha,
            peso_kg=peso_kg,
            bodyfat_pct_rango_min=bodyfat_pct,
            bodyfat_pct_rango_max=bodyfat_pct,
            metodo="feelfit_bioimpedance" if bodyfat_pct is not None else "manual",
            fuente_externa_id=fuente_id,
        )
        session.add(medicion)
        try:
            session.commit()
        except IntegrityError:
            # Perdió la carrera contra otra sincronización concurrente
            # (mismo user_id + fuente_externa_id) - se trata igual que
            # "ya existía", nunca se propaga como 500 ni tumba el resto
            # del lote (a diferencia de un commit bulk al final).
            session.rollback()
            continue

        if fuente_id is not None:
            ids_existentes.add(fuente_id)
        insertadas += 1

    return insertadas
