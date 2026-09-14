from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import (
    ConexionesOut,
    ConexionFeelfitOut,
    ConexionGarminOut,
    GarminConnectRequest,
    UserCreateRequest,
    UserOut,
    UserUpdateRequest,
)
from garmin_sync.client import GarminAuthError, GarminRateLimitedError
from models.database import get_session
from models.schema import (
    BodyMeasurements,
    FeelfitCredentials,
    GarminCredentials,
    GarminDailyMetrics,
    UserProfile,
)
from services.garmin_manual_sync_service import sync_today_for_user
from services.garmin_onboarding_service import (
    GarminPerfilIncompletoError,
    backfill_new_user_history,
    connect_or_reconnect_via_garmin,
)

logger = logging.getLogger("pulse.users")

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(verify_api_key)])


def _ejecutar_backfill_en_background(user_id: int, token_store_dir: str) -> None:
    """Wrapper de `BackgroundTasks` (hallazgo de code-review, CRÍTICO -
    ver docstring de `garmin_onboarding_service.backfill_new_user_history`):
    abre su PROPIA sesión de base de datos, independiente de la del
    request que ya terminó, y nunca deja que un fallo se propague fuera
    de esta tarea en background (no hay ninguna respuesta HTTP a la que
    devolver un error a estas alturas - el usuario ya fue creado)."""
    session = get_session()
    try:
        backfill_new_user_history(session, user_id=user_id, token_store_dir=token_store_dir)
    except Exception:  # noqa: BLE001 - tarea en background, el scheduler nocturno reintentará
        logger.exception(
            "Fallo el backfill en background del usuario %s (token_store_dir=%s)",
            user_id,
            token_store_dir,
        )
    finally:
        session.close()


def _ejecutar_sync_ligero_en_background(user_id: int) -> None:
    """Equivalente a `_ejecutar_backfill_en_background` pero para la rama
    de reconexión: un usuario ya existente no necesita backfill (sus
    datos históricos ya están en la base de datos), solo traer el día de
    hoy cuanto antes - reutiliza el mismo camino que el botón "sincronizar
    ahora" (`POST /garmin/sync`), con su propia sesión de base de datos."""
    session = get_session()
    try:
        sync_today_for_user(session, user_id)
    except Exception:  # noqa: BLE001 - tarea en background, el scheduler nocturno reintentará
        logger.exception("Fallo el sync ligero en background del usuario %s", user_id)
    finally:
        session.close()


def _directorio_tokens_por_defecto() -> Path:
    # Mismo criterio que scripts/garmin_pair.py (PULSE_GARMIN_TOKENS_DIR,
    # con fallback a ~/.garminconnect) - un solo lugar de verdad para
    # dónde vive el token cacheado de cada usuario.
    return Path(os.environ.get("PULSE_GARMIN_TOKENS_DIR", str(Path.home() / ".garminconnect")))


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserProfile:
    usuario = UserProfile(**payload.model_dump())
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/garmin-connect", response_model=UserOut)
def garmin_connect(
    payload: GarminConnectRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
) -> UserProfile:
    """Alta de un usuario nuevo conectando su cuenta de Garmin, O reconexión
    de una cuenta de Garmin ya vinculada a un usuario existente - sustituye
    al formulario manual de onboarding (petición explícita del usuario:
    "sin cuenta local, que al conectar Garmin se saquen esos datos de
    ahí"). `email`/`password` viajan solo en esta petición HTTPS, nunca
    se persisten (ver `GarminConnectRequest`/`connect_or_reconnect_via_garmin`).

    Hallazgo real (rate-limit reportado por el usuario): sin distinguir
    estas dos ramas, perder `pulse_user_id` de localStorage obligaba a
    crear un `UserProfile` duplicado y repetir el backfill completo de
    90 días en cada "login" - la causa real del rate-limiting. Ahora se
    busca primero por `garmin_email` (`find_user_by_garmin_email`): si ya
    existe, se reconecta (sin backfill, `200 OK`) en vez de crear una
    cuenta nueva (`201 Created`).

    El directorio de tokens usa un UUID en vez de un id de usuario (que
    todavía no existe en este punto) - no tiene que coincidir con
    ninguna convención de nombre, solo ser único y estable para que
    `python-garminconnect` cachee la sesión ahí.

    El backfill histórico (90 días) corre en background tras responder
    (hallazgo de code-review, CRÍTICO - ver docstring de
    `garmin_onboarding_service.connect_new_user_via_garmin`): esta
    petición vuelve en cuanto el login+perfil+usuario están listos (2
    llamadas a Garmin), no tras las ~900 llamadas que tardaba antes -
    eso es lo que dejaba "iniciando sesión" colgado varios minutos y
    disparaba el rate-limit de la cuenta.

    Limitación conocida (no soportada todavía): cuentas de Garmin con
    verificación en dos pasos (MFA) fallarán aquí con un 401 genérico -
    a diferencia de `services.garmin_pairing_service` (emparejamiento
    de una cuenta YA existente), este endpoint no pasa `mfa_code_prompt`
    porque una petición HTTP única no puede pedir el código interactivo
    a mitad de un login. Si se necesita soportar MFA en este flujo, hace
    falta un segundo endpoint que reciba el código tras un primer 401
    específico de MFA.
    """
    token_store_dir = str(_directorio_tokens_por_defecto() / f"pulse-connect-{uuid.uuid4().hex}")
    overrides = {
        campo: valor
        for campo, valor in (
            ("nombre", payload.nombre),
            ("altura_cm", payload.altura_cm),
            ("fecha_nacimiento", payload.fecha_nacimiento),
            ("sexo", payload.sexo),
        )
        if valor is not None
    }
    try:
        resultado = connect_or_reconnect_via_garmin(
            db,
            email=payload.email,
            password=payload.password,
            token_store_dir=token_store_dir,
            overrides=overrides,
        )
        if resultado.es_nuevo:
            response.status_code = 201
            background_tasks.add_task(
                _ejecutar_backfill_en_background, resultado.usuario.id, resultado.token_store_dir
            )
        else:
            response.status_code = 200
            background_tasks.add_task(_ejecutar_sync_ligero_en_background, resultado.usuario.id)
        return resultado.usuario
    except GarminPerfilIncompletoError as exc:
        raise HTTPException(
            status_code=422,
            detail={"campos_faltantes": exc.campos_faltantes},
        ) from exc
    except GarminRateLimitedError as exc:
        raise HTTPException(
            status_code=429,
            detail="Garmin ha aplicado rate-limiting a esta cuenta. Espera unos minutos antes de reintentar.",
        ) from exc
    except GarminAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail="No se pudo iniciar sesión en Garmin Connect - revisa tu email y contraseña.",
        ) from exc


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserProfile:
    usuario = db.get(UserProfile, user_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail=f"No existe usuario con id={user_id}")
    return usuario


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, payload: UserUpdateRequest, db: Session = Depends(get_db)
) -> UserProfile:
    """Edición del propio perfil desde la página de Perfil.

    Hasta ahora el perfil solo se podía crear (alta vía Garmin) pero no
    corregir: si Garmin daba una altura mal o el usuario cambiaba de
    fase de peso (`cut` -> `maintenance`), no había forma de arreglarlo
    desde la app. `fase_peso_actual` además alimenta el objetivo
    nutricional, así que dejarlo inmutable era un error funcional, no
    solo de comodidad.

    Un PATCH sin ningún campo es un 400, no un no-op silencioso: casi
    siempre significa que el cliente mandó los nombres de campo mal.
    """
    usuario = db.get(UserProfile, user_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail=f"No existe usuario con id={user_id}")

    cambios = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="No se envió ningún campo que actualizar.")

    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/{user_id}/connections", response_model=ConexionesOut)
def get_connections(user_id: int, db: Session = Depends(get_db)) -> ConexionesOut:
    """Estado real de las integraciones externas, para la página de Perfil.

    Existe como endpoint propio en vez de deducirlo en el frontend a
    partir de "¿hay datos?": la ausencia de datos no distingue entre
    "no conectado", "conectado y el token caducó" y "conectado pero el
    scheduler aún no ha corrido" (principio de "unknown is not zero").

    `activo=False` cuenta como NO conectado: es la marca que deja el
    scheduler cuando las credenciales dejan de funcionar, y mostrarlo
    como conectado sería precisamente la falsa precisión que el
    proyecto evita.
    """
    if db.get(UserProfile, user_id) is None:
        raise HTTPException(status_code=404, detail=f"No existe usuario con id={user_id}")

    garmin = db.scalar(select(GarminCredentials).where(GarminCredentials.user_id == user_id))
    dias_garmin = db.scalar(
        select(func.count())
        .select_from(GarminDailyMetrics)
        .where(GarminDailyMetrics.user_id == user_id)
    )
    feelfit = db.scalar(select(FeelfitCredentials).where(FeelfitCredentials.user_id == user_id))
    # Solo las mediciones que realmente vinieron de la báscula: las
    # manuales tienen `fuente_externa_id IS NULL` y contarlas aquí
    # atribuiría a Feelfit datos que el usuario metió a mano.
    mediciones_feelfit = db.scalar(
        select(func.count())
        .select_from(BodyMeasurements)
        .where(
            BodyMeasurements.user_id == user_id,
            BodyMeasurements.metodo == "feelfit_bioimpedance",
        )
    )

    return ConexionesOut(
        garmin=ConexionGarminOut(
            conectado=garmin is not None and garmin.activo,
            email=garmin.garmin_email if garmin is not None else None,
            historial_desde=garmin.historial_sincronizado_desde if garmin is not None else None,
            # Paréntesis explícitos: sin conexión el valor es `None`
            # ("no se sabe"), y con conexión pero sin días sincronizados
            # todavía es `0`. Son dos cosas distintas y la precedencia
            # de Python aquí se lee mal de un vistazo.
            dias_de_historial=(dias_garmin or 0) if garmin is not None else None,
        ),
        feelfit=ConexionFeelfitOut(
            conectado=feelfit is not None and feelfit.activo,
            conectado_desde=feelfit.created_at.date() if feelfit is not None else None,
            mediciones_importadas=mediciones_feelfit or 0,
        ),
    )
