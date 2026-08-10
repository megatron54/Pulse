"""Punto de entrada de la app de escritorio nativa (Épica K,
00-research/09-app-nativa-escritorio.md) - este módulo es lo que
PyInstaller empaqueta en un único ejecutable, y lo que Tauri lanza como
proceso "sidecar" al arrancar la ventana nativa.

Diferencias deliberadas frente a `api.main:app` corriendo en Docker:
- `DATABASE_URL` apunta SIEMPRE a un archivo SQLite en el directorio de
  datos del usuario (`~/.pulse/pulse.db` por defecto, o
  `PULSE_DESKTOP_DB_PATH` si se define) - nunca a Postgres. Se crea el
  directorio y el schema (`ensure_schema`) si hace falta, para que un
  usuario nuevo pueda abrir la app por primera vez sin ningún paso
  manual.
- `PULSE_ENV=dev` se fuerza aquí: la app de escritorio es de un único
  usuario local, sin superficie de red expuesta (escucha solo en
  127.0.0.1) - el mismo modelo de "sin API key en dev" que ya usa
  `api.dependencies.verify_api_key` para desarrollo local, aplicado
  aquí porque el equivalente de producción (una API key) no tendría a
  quién protegerse: el propio usuario es el único que puede llegar a
  este puerto.
- CORS se abre a cualquier origen: el frontend se sirve desde el
  esquema `tauri://localhost` (Windows: `http://tauri.localhost`), no
  desde un puerto HTTP fijo conocido de antemano - fijar un origen
  exacto aquí sería frágil entre versiones de Tauri/SO, y no hay ganancia
  de seguridad real (loopback-only, un único usuario).
- Puerto fijo (`8756`, arbitrario) en vez de aleatorio: el frontend
  estático ya tiene compilado `NEXT_PUBLIC_API_URL` con ese valor
  (`package.json` -> `build:tauri`), y un puerto elegido en caliente no
  se podría comunicar de vuelta a un bundle ya compilado."""
from __future__ import annotations

import os
from pathlib import Path

_PUERTO_DESKTOP = 8756


def _ruta_base_datos() -> Path:
    override = os.environ.get("PULSE_DESKTOP_DB_PATH")
    if override:
        return Path(override)
    return Path.home() / ".pulse" / "pulse.db"


def main() -> None:
    db_path = _ruta_base_datos()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("PULSE_ENV", "dev")

    # Import diferido: hay que fijar DATABASE_URL/PULSE_ENV en el
    # entorno ANTES de importar `api.main` (lee `os.environ` en tiempo
    # de import de sus dependencias, ej. `models.database`).
    import uvicorn

    from scripts.ensure_schema import main as ensure_schema

    ensure_schema()

    import api.main as api_main

    # Sustituye el CORSMiddleware ya registrado por api.main (fijo al
    # origen del frontend de Docker) por uno abierto a cualquier
    # origen - ver docstring del módulo. Seguro solo porque
    # `middleware_stack` todavía no se ha construido (ningún request
    # servido todavía): `add_middleware` lanzaría RuntimeError si ya
    # estuviera construido.
    from fastapi.middleware.cors import CORSMiddleware

    api_main.app.user_middleware = [
        m for m in api_main.app.user_middleware if m.cls.__name__ != "CORSMiddleware"
    ]
    api_main.app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(api_main.app, host="127.0.0.1", port=_PUERTO_DESKTOP, log_level="info")


if __name__ == "__main__":
    main()
