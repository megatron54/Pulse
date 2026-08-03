"""Crea las tablas del schema de Pulse si no existen todavía.

Hallazgo real de Fase J (empaquetado único, docs/02-roadmap/
02-plan-autonomo.md): al levantar el stack con `docker compose up` sobre
un volumen de Postgres NUEVO, la base de datos queda vacía - nada hasta
ahora ejecutaba `Base.metadata.create_all()` fuera de los tests (que
usan su propio engine SQLite en memoria) y del paso explícito de
verificación en CI. El primer request real a la API contra ese Postgres
limpio fallaba con `UndefinedTable` (verificado a mano, no solo
teorizado).

Deliberadamente NO se resuelve con un evento `lifespan` de FastAPI en
`api/main.py`: los tests de integración de la API (`tests/test_api.py`)
instancian `app` con su propio engine SQLite vía `dependency_overrides`,
así que un `create_all` en el lifespan usando el `DATABASE_URL` real
correría contra el Postgres de verdad durante tests unitarios que no
deberían necesitar red - un acoplamiento sutil y frágil. En su lugar,
este script se ejecuta como un paso EXPLÍCITO antes de arrancar uvicorn
(ver el `CMD` de `Dockerfile`, que encadena
`python -m scripts.ensure_schema && exec uvicorn ...`), igual que ya
hace el step "Verify schema" del CI (`.github/workflows/ci.yml`).

`create_all` es idempotente: solo crea las tablas que faltan, nunca
altera ni borra las que ya existen - seguro de ejecutar en cada arranque
del contenedor, incluso contra una base de datos de producción con
datos reales.

Incluye un reintento acotado con backoff: `depends_on: condition:
service_healthy` en docker-compose garantiza que `pg_isready` responda,
pero no que Postgres acepte ya conexiones de aplicación en el primer
intento (carrera de arranque conocida) - sin este reintento, un fallo
transitorio aquí tumbaría el contenedor entero (H2 de code-review)."""
from __future__ import annotations

import time

from models.database import create_pulse_engine
from models.schema import Base

_INTENTOS = 5
_ESPERA_INICIAL_SEGUNDOS = 2


def main() -> None:
    engine = create_pulse_engine()
    ultimo_error: Exception | None = None
    for intento in range(1, _INTENTOS + 1):
        try:
            Base.metadata.create_all(engine)
            print("OK: schema de Pulse verificado/creado.")
            return
        except Exception as exc:  # noqa: BLE001 - se reintenta, no se traga el error final
            ultimo_error = exc
            espera = _ESPERA_INICIAL_SEGUNDOS * intento
            print(
                f"Intento {intento}/{_INTENTOS} fallido creando el schema "
                f"({exc}); reintentando en {espera}s..."
            )
            time.sleep(espera)
    raise RuntimeError(
        f"No se pudo crear/verificar el schema tras {_INTENTOS} intentos"
    ) from ultimo_error


if __name__ == "__main__":
    main()
