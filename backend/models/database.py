"""Creación del engine/sesión de SQLAlchemy para Pulse.

Lee `DATABASE_URL` del entorno; si no está definida, usa por defecto el
Postgres local de desarrollo levantado en
infra/docker-compose.pulse.yml (puerto 5433, ver infra/README.md).

Todo local por ahora (decisión explícita del usuario). Si en el futuro
se despliega online, la opción evaluada es Vercel + Supabase (Supabase
es Postgres real, por lo que `DATABASE_URL` apuntaría simplemente a la
cadena de conexión de Supabase sin cambios de código aquí).
"""
from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

_DEFAULT_LOCAL_URL = "postgresql+psycopg2://pulse:pulse_dev_password@localhost:5433/pulse"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", _DEFAULT_LOCAL_URL)


def create_pulse_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or get_database_url())


def get_session(engine: Engine | None = None) -> Session:
    return Session(engine or create_pulse_engine())
