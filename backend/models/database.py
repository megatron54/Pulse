"""Creación del engine/sesión de SQLAlchemy para Pulse.

Lee `DATABASE_URL` del entorno; si no está definida, usa por defecto el
Postgres local de desarrollo levantado en
infra/docker-compose.pulse.yml (puerto 5433, ver infra/README.md).

Todo local por ahora (decisión explícita del usuario). Si en el futuro
se despliega online, la opción evaluada es Vercel + Supabase (Supabase
es Postgres real, por lo que `DATABASE_URL` apuntaría simplemente a la
cadena de conexión de Supabase sin cambios de código aquí).

Épica K (00-research/09-app-nativa-escritorio.md): la app de escritorio
empaquetada (Tauri + sidecar PyInstaller) usa SQLite en vez de Postgres
- sin servidor externo que instalar, coherente con la recomendación de
esa investigación. `create_pulse_engine` detecta el dialecto SQLite y
añade `check_same_thread=False`: FastAPI/uvicorn atiende requests desde
varios threads, y sin este flag SQLite lanza
`sqlite3.ProgrammingError` en cuanto una conexión se usa desde un
thread distinto al que la abrió.
"""
from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

_DEFAULT_LOCAL_URL = "postgresql+psycopg2://pulse:pulse_dev_password@localhost:5433/pulse"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", _DEFAULT_LOCAL_URL)


def create_pulse_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def get_session(engine: Engine | None = None) -> Session:
    return Session(engine or create_pulse_engine())
