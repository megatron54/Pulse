"""Emparejamiento inicial de una cuenta Garmin REAL con un usuario de
Pulse (Fase H, desbloqueada por el usuario con su cuenta/dispositivo
real).

USO: se ejecuta A MANO, una sola vez, desde tu propia terminal local -
NUNCA a través de la API/web de Pulse ni pegando tu contraseña en un
chat con un agente de IA (ni este mismo, ni ningún otro). El motivo:
- Un agente de IA (incluida esta sesión) no debe ver nunca tu
  contraseña real de Garmin; escribirla en un chat quedaría en el
  historial de la conversación de forma permanente.
- Este script pide el email/contraseña por `input()`/`getpass` (que no
  hace eco en pantalla) y los usa EXCLUSIVAMENTE para una llamada de
  login en memoria - nunca se escriben a disco, a un log, ni a la base
  de datos de Pulse. Lo único que se persiste es la ruta al directorio
  donde `python-garminconnect` cachea el token OAuth ya autenticado
  (ver docstring de `models.schema.GarminCredentials`).

Ejecución:
    cd backend
    .venv\\Scripts\\python.exe -m scripts.garmin_pair --user-id 1

Tras un emparejamiento exitoso, el scheduler nocturno
(`services.scheduler_service`) ya puede sincronizar recovery y
actividades reales para ese usuario sin volver a pedir la contraseña.
"""
from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from garmin_sync.client import GarminAuthError, GarminRateLimitedError
from models.database import get_session
from services.errors import EntityNotFoundError
from services.garmin_pairing_service import pair_garmin_account

_DIRECTORIO_TOKENS_POR_DEFECTO = Path.home() / ".garminconnect"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id", type=int, required=True, help="id de UserProfile en Pulse a emparejar"
    )
    parser.add_argument(
        "--token-store-dir",
        type=str,
        default=None,
        help=(
            "Directorio donde cachear el token de Garmin "
            f"(por defecto: {_DIRECTORIO_TOKENS_POR_DEFECTO}/pulse-user-<user-id>)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    token_store_dir = args.token_store_dir or str(
        _DIRECTORIO_TOKENS_POR_DEFECTO / f"pulse-user-{args.user_id}"
    )

    print("=== Emparejamiento de cuenta Garmin con Pulse ===")
    print(
        "Tu contraseña se usa SOLO para este login y nunca se guarda en "
        "ningún sitio (ni disco, ni log, ni base de datos)."
    )
    email = input("Email de Garmin Connect: ").strip()
    password = getpass.getpass("Contraseña de Garmin Connect (no se muestra en pantalla): ")

    session = get_session()
    try:
        pair_garmin_account(
            session,
            user_id=args.user_id,
            email=email,
            password=password,
            token_store_dir=token_store_dir,
            mfa_code_prompt=lambda: input(
                "Código de verificación en dos pasos (revisa tu email/app Garmin): "
            ).strip(),
        )
        print(f"OK: cuenta emparejada. Token cacheado en: {token_store_dir}")
        print(
            "El scheduler nocturno ya puede sincronizar recovery y "
            "actividades reales para este usuario."
        )
    except EntityNotFoundError as exc:
        print(f"ERROR: {exc}")
    except GarminRateLimitedError:
        print(
            "ERROR: Garmin ha aplicado rate-limiting a esta cuenta (429/403). "
            "NO reintentes de inmediato - espera unas horas antes de volver a "
            "intentar el emparejamiento (ver 00-research/03-garmin-integracion.md: "
            "el login repetido fallido puede bloquear la cuenta 48-72h)."
        )
    except GarminAuthError as exc:
        print(
            f"ERROR de autenticación: {exc}\n"
            "Verifica el email/contraseña. Si tu cuenta tiene verificación en "
            "dos pasos, puede requerir un paso adicional no cubierto por este "
            "script todavía."
        )
    finally:
        # `password`/`email` quedan solo en variables locales de este
        # proceso; al terminar el script no queda ningún rastro salvo
        # el propio token que python-garminconnect ya cachea en disco
        # (gestionado por esa librería, no por este script).
        session.close()


if __name__ == "__main__":
    main()
