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

from datetime import date, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from garmin_sync.client import GarminClient
from models.schema import GarminCredentials, UserProfile
from services.garmin_backfill_service import backfill_full_history

_CAMPOS_REQUERIDOS = ("nombre", "sexo", "altura_cm", "fecha_nacimiento")

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

    El backfill NUNCA puede tumbar la conexión ya exitosa: si falla
    parcial o totalmente, el usuario ya fue creado y sus credenciales
    ya están activas - el scheduler nocturno seguirá intentando
    sincronizar de todos modos. `garmin_backfill_service` ya aísla sus
    propios fallos día a día internamente."""
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
        GarminCredentials(user_id=usuario.id, token_store_dir=token_store_dir, activo=True)
    )
    session.commit()
    session.refresh(usuario)

    hoy = hoy or date.today()
    backfill_full_history(
        session,
        user_id=usuario.id,
        garmin_client=client,
        start_date=hoy - timedelta(days=backfill_dias - 1),
        end_date=hoy,
    )

    return usuario
