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

Por eso mismo, `create_all` NUNCA añade una columna nueva a una tabla
YA EXISTENTE (hallazgo MEDIUM de code-review, integración Feelfit): el
volumen `pulse-postgres-data` de `docker-compose.yml` es persistente,
así que `body_measurements.fuente_externa_id` (columna añadida junto a
`FeelfitCredentials`) NO aparecería solo con `create_all` en cualquier
Postgres que ya tuviera la tabla `body_measurements` de antes - el
primer INSERT con ese campo fallaría con `UndefinedColumn`, el mismo
tipo de fallo silencioso que motivó este script. `_migrar_columnas_
aditivas` de abajo cubre este caso concreto de forma explícita e
idempotente (columna + índice único, sin tocar filas existentes -
`fuente_externa_id` queda `NULL` en las mediciones manuales ya
guardadas, que es exactamente su valor por defecto para ese caso).

Incluye un reintento acotado con backoff: `depends_on: condition:
service_healthy` en docker-compose garantiza que `pg_isready` responda,
pero no que Postgres acepte ya conexiones de aplicación en el primer
intento (carrera de arranque conocida) - sin este reintento, un fallo
transitorio aquí tumbaría el contenedor entero (H2 de code-review)."""
from __future__ import annotations

import time

from sqlalchemy import inspect, text

from models.database import create_pulse_engine
from models.schema import Base

_INTENTOS = 5
_ESPERA_INICIAL_SEGUNDOS = 2


def _migrar_columnas_aditivas(engine) -> None:
    """Migración manual mínima para columnas añadidas a tablas YA
    EXISTENTES tras el primer despliegue (ver docstring del módulo) -
    NUNCA borra ni altera datos, solo añade lo que falte. Deliberadamente
    no se adopta Alembic completo todavía (decisión explícita: el
    proyecto es de un solo desarrollador con una base de datos local,
    ver `models/database.py`) - si esta lista de parches manuales crece
    más allá de un puñado de casos, ese es el momento de migrar a
    Alembic de verdad."""
    inspector = inspect(engine)
    if "body_measurements" not in inspector.get_table_names():
        return  # create_all ya la habrá creado completa, nada que parchear

    columnas = {c["name"] for c in inspector.get_columns("body_measurements")}

    if "fuente_externa_id" not in columnas:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE body_measurements ADD COLUMN fuente_externa_id VARCHAR(100)")
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX uq_body_measurements_user_fuente_externa "
                    "ON body_measurements (user_id, fuente_externa_id)"
                )
            )
        print("OK: migración aditiva body_measurements.fuente_externa_id aplicada.")

    # Composición completa de bioimpedancia (báscula Feelfit) - añadida
    # después de fuente_externa_id, así que se migra por separado: una
    # base ya migrada con fuente_externa_id puede seguir sin estas 4.
    columnas_bioimpedancia = {"muscle_kg", "bone_kg", "water_pct", "bmi"}
    faltantes = columnas_bioimpedancia - columnas
    if faltantes:
        with engine.begin() as conn:
            for columna in faltantes:
                conn.execute(
                    text(f"ALTER TABLE body_measurements ADD COLUMN {columna} FLOAT")
                )
        print(f"OK: migración aditiva body_measurements bioimpedancia aplicada ({sorted(faltantes)}).")


def main() -> None:
    engine = create_pulse_engine()
    ultimo_error: Exception | None = None
    for intento in range(1, _INTENTOS + 1):
        try:
            Base.metadata.create_all(engine)
            _migrar_columnas_aditivas(engine)
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
