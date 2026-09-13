"""Alta de un usuario nuevo conectando directamente su cuenta de Garmin
(petición explícita del usuario: "no quiero tokens míos hardcodeados...
y si otra persona quiere usar la app, debería poder configurárselo para
sí mismo con su propia cuenta", "sin cuenta local, que al conectar
Garmin se saquen esos datos de ahí").

Sustituye al flujo de onboarding manual (formulario de nombre/altura/
fecha de nacimiento) como vía principal de alta: los mismos campos se
extraen de `GarminClient.get_user_profile_raw()`. Sigue la misma
política de contraseña que `scripts/garmin_pair.py` y
`garmin_sync.client.GarminClient.login`: la contraseña vive solo en
memoria durante esta llamada (variable local de Python, nunca se
asigna a un atributo de modelo ni se persiste en la base de datos) -
solo se guarda el `token_store_dir` resultante en `GarminCredentials`,
igual que ya hacía el script manual."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from garmin_sync.client import GarminClient
from models.schema import GarminCredentials, UserProfile
from services.garmin_backfill_service import backfill_full_history

_CAMPOS_REQUERIDOS = ("nombre", "sexo", "altura_cm", "fecha_nacimiento")


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


def find_user_by_garmin_email(session: Session, email: str) -> UserProfile | None:
    """Busca un usuario YA conectado con esa cuenta de Garmin, por el
    `garmin_email` (no secreto) guardado en `GarminCredentials` -
    permite distinguir "reconectar una cuenta existente" de "dar de
    alta una cuenta nueva" en `connect_or_reconnect_via_garmin`.
    `None` si el email nunca se vio antes (incluye credenciales
    creadas antes de que existiera esta columna, que quedan con
    `garmin_email=None` y por tanto nunca hacen match)."""
    credenciales = (
        session.query(GarminCredentials)
        .filter(GarminCredentials.garmin_email == _normalizar_email(email))
        .one_or_none()
    )
    if credenciales is None:
        return None
    return session.get(UserProfile, credenciales.user_id)


@dataclass(frozen=True)
class ConexionGarminResultado:
    usuario: UserProfile
    es_nuevo: bool
    token_store_dir: str

# Rango de backfill histórico por defecto tras conectar una cuenta
# nueva (petición explícita del usuario: "debería extraerse todo el
# histórico de Garmin, no solo lo de los últimos 5 min"). NO se usa
# "todo el histórico disponible" (años) como pidió literalmente el
# usuario: `garmin_backfill_service` documenta el riesgo real de
# rate-limiting/bloqueo de cuenta de la API no oficial de Garmin con
# un volumen de peticiones día-a-día tan grande. 90 días es un
# compromiso conservador - vale la pena revisar con el usuario si
# quiere ampliarlo una vez confirmado que no dispara ningún bloqueo.
_BACKFILL_DIAS_POR_DEFECTO = 90


class GarminPerfilIncompletoError(Exception):
    """Garmin no expuso todos los campos requeridos del perfil y no se
    proporcionó un `override` para completarlos. `campos_faltantes` es
    la lista exacta (nunca más, nunca menos) de campos que la capa
    llamante (API/frontend) debe pedir - jamás se re-pide un campo que
    Garmin sí dio, por decisión explícita del usuario."""

    def __init__(self, campos_faltantes: list[str]) -> None:
        self.campos_faltantes = campos_faltantes
        super().__init__(f"Faltan campos del perfil: {', '.join(campos_faltantes)}")


def connect_new_user_via_garmin(
    session: Session,
    *,
    email: str,
    password: str,
    token_store_dir: str,
    overrides: dict[str, Any] | None = None,
    api_factory: Callable[..., Any] | None = None,
    mfa_code_prompt: Callable[[], str] | None = None,
    backfill_dias: int = _BACKFILL_DIAS_POR_DEFECTO,
    hoy: date | None = None,
) -> UserProfile:
    """Inicia sesión en Garmin, extrae el perfil, crea el `UserProfile`
    + `GarminCredentials`, y dispara el backfill histórico de los
    últimos `backfill_dias` (petición explícita del usuario: que la
    conexión traiga histórico real, no solo el día de hoy) - reutiliza
    la MISMA sesión ya autenticada, sin un segundo login.

    Nunca crea un usuario a medias: si falta cualquier campo requerido
    tras aplicar `overrides` (petición explícita del usuario: "pedir
    solo lo que falte"), se lanza `GarminPerfilIncompletoError` con la
    lista exacta de campos que faltan, ANTES de tocar la base de datos.
    Si el login en sí falla (credenciales inválidas, rate-limit), la
    excepción de `GarminClient.login` (`GarminAuthError`/
    `GarminRateLimitedError`) se propaga tal cual - tampoco en ese caso
    se crea nada.

    El backfill de histórico NUNCA se ejecuta aquí (hallazgo de
    code-review, CRÍTICO): con 90 días por defecto, `backfill_full_history`
    dispara ~7 llamadas de recovery + 3 de intradía POR DÍA a la API de
    Garmin (~900 peticiones HTTP secuenciales) - ejecutarlo dentro de
    esta misma llamada síncrona dejaba la petición HTTP de conexión
    colgada varios minutos y era la causa real del rate-limiting que
    sufría el usuario al conectar su cuenta (nunca fue un problema de
    reintentos de login, que ya estaban bien resueltos). Esta función
    ahora termina en cuanto el usuario existe en la base de datos - la
    capa llamante (`api.routers.users.garmin_connect`) es quien decide
    disparar `backfill_new_user_history` como tarea en background,
    fuera del ciclo request/response."""
    client = GarminClient(
        token_store_dir=token_store_dir,
        email=email,
        password=password,
        api_factory=api_factory,
        mfa_code_prompt=mfa_code_prompt,
    )
    client.login()
    perfil_garmin = client.get_user_profile_raw()

    overrides = overrides or {}
    valores = {
        campo: overrides.get(campo) if overrides.get(campo) is not None else perfil_garmin.get(campo)
        for campo in _CAMPOS_REQUERIDOS
    }

    faltantes = [campo for campo, valor in valores.items() if valor is None]
    if faltantes:
        raise GarminPerfilIncompletoError(faltantes)

    fecha_nacimiento = valores["fecha_nacimiento"]
    if isinstance(fecha_nacimiento, str):
        fecha_nacimiento = date.fromisoformat(fecha_nacimiento)

    usuario = UserProfile(
        nombre=valores["nombre"],
        sexo=valores["sexo"],
        altura_cm=valores["altura_cm"],
        fecha_nacimiento=fecha_nacimiento,
    )
    session.add(usuario)
    session.flush()  # asigna usuario.id sin cerrar la transacción

    session.add(
        GarminCredentials(
            user_id=usuario.id,
            token_store_dir=token_store_dir,
            garmin_email=_normalizar_email(email),
            activo=True,
        )
    )
    session.commit()
    session.refresh(usuario)

    return usuario


def reconnect_existing_user_via_garmin(
    session: Session,
    *,
    usuario: UserProfile,
    email: str,
    password: str,
    api_factory: Callable[..., Any] | None = None,
    mfa_code_prompt: Callable[[], str] | None = None,
) -> None:
    """Reconecta una cuenta de Garmin YA vinculada a `usuario` (hallazgo
    real: sin esto, perder el `pulse_user_id` de localStorage - nuevo
    navegador, caché borrada, otro dispositivo - obligaba a crear un
    `UserProfile` duplicado y repetir el backfill completo de 90 días,
    la causa real del rate-limit de Garmin reportado por el usuario).

    Reutiliza el `token_store_dir` YA existente de la primera conexión:
    `GarminClient.login()` intenta primero el token OAuth cacheado ahí
    (ver `garmin_sync.client`) y solo hace un login con contraseña de
    verdad si ese token expiró - normalmente un simple "reconectar" no
    dispara ninguna petición extra de volumen a Garmin. NO se toca el
    histórico ya sincronizado ni se dispara ningún backfill: los datos
    de este usuario ya están en la base de datos."""
    credenciales = session.query(GarminCredentials).filter_by(user_id=usuario.id).one()
    client = GarminClient(
        token_store_dir=credenciales.token_store_dir,
        email=email,
        password=password,
        api_factory=api_factory,
        mfa_code_prompt=mfa_code_prompt,
    )
    client.login()
    credenciales.activo = True
    session.commit()


def connect_or_reconnect_via_garmin(
    session: Session,
    *,
    email: str,
    password: str,
    token_store_dir: str,
    overrides: dict[str, Any] | None = None,
    api_factory: Callable[..., Any] | None = None,
    mfa_code_prompt: Callable[[], str] | None = None,
) -> ConexionGarminResultado:
    """Punto de entrada único del router: decide entre "reconectar una
    cuenta ya vista" y "dar de alta una cuenta nueva" según
    `find_user_by_garmin_email`, para que `garmin_connect` nunca vuelva
    a crear un `UserProfile` duplicado de una cuenta de Garmin que ya
    existe en la base de datos (ver docstring de
    `reconnect_existing_user_via_garmin`)."""
    usuario_existente = find_user_by_garmin_email(session, email)
    if usuario_existente is not None:
        reconnect_existing_user_via_garmin(
            session,
            usuario=usuario_existente,
            email=email,
            password=password,
            api_factory=api_factory,
            mfa_code_prompt=mfa_code_prompt,
        )
        credenciales = session.query(GarminCredentials).filter_by(user_id=usuario_existente.id).one()
        return ConexionGarminResultado(
            usuario=usuario_existente, es_nuevo=False, token_store_dir=credenciales.token_store_dir
        )

    usuario_nuevo = connect_new_user_via_garmin(
        session,
        email=email,
        password=password,
        token_store_dir=token_store_dir,
        overrides=overrides,
        api_factory=api_factory,
        mfa_code_prompt=mfa_code_prompt,
    )
    return ConexionGarminResultado(usuario=usuario_nuevo, es_nuevo=True, token_store_dir=token_store_dir)


def backfill_new_user_history(
    session: Session,
    *,
    user_id: int,
    token_store_dir: str,
    api_factory: Callable[..., Any] | None = None,
    backfill_dias: int = _BACKFILL_DIAS_POR_DEFECTO,
    hoy: date | None = None,
) -> None:
    """Ejecuta el backfill histórico de un usuario recién conectado -
    pensada para correr como `BackgroundTask` de FastAPI (o un job
    encolado equivalente) con SU PROPIA sesión de base de datos, nunca
    la del request original (que FastAPI puede cerrar en cuanto la
    respuesta HTTP se envía).

    Vuelve a autenticar contra Garmin (`token_store_dir` ya tiene el
    token cacheado del login hecho en `connect_new_user_via_garmin`,
    así que este segundo `login()` reutiliza sesión, no hace un login
    fresco - ver política de autenticación en `garmin_sync.client`).

    El fallo del backfill NUNCA debe perderse en silencio ni tumbar
    nada: `garmin_backfill_service` ya aísla sus propios fallos día a
    día internamente, y las credenciales/usuario ya quedaron creados
    antes de que esta función se invoque - el scheduler nocturno
    seguirá intentando sincronizar de todos modos aunque este backfill
    puntual falle del todo (p.ej. por un rate-limit inesperado)."""
    client = GarminClient(
        token_store_dir=token_store_dir,
        api_factory=api_factory,
    )
    client.login()

    hoy = hoy or date.today()
    inicio = hoy - timedelta(days=backfill_dias - 1)
    backfill_full_history(
        session,
        user_id=user_id,
        garmin_client=client,
        start_date=inicio,
        end_date=hoy,
    )

    # Marca la "frontera" del histórico ya sincronizado - punto de
    # partida de `garmin_history_deepening_service` para seguir
    # extendiendo hacia atrás en pasadas nocturnas acotadas, en vez de
    # repetir este mismo rango cada vez (petición explícita del
    # usuario: quiere todo su histórico, no solo estos días iniciales).
    credenciales = session.query(GarminCredentials).filter_by(user_id=user_id).one_or_none()
    if credenciales is not None:
        credenciales.historial_sincronizado_desde = inicio
        session.commit()
