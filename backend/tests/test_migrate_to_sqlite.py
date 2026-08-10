"""Épica K: `scripts.migrate_to_sqlite` copia datos entre dos bases -
se prueba SQLite->SQLite (no depende de un Postgres real en CI), pero
la lógica de copia genérica por `Base.metadata.sorted_tables` es
idéntica al caso real Postgres->SQLite."""
from __future__ import annotations

from datetime import date

import pytest

from models.database import create_pulse_engine
from models.schema import Base, ReadinessLog, UserProfile
from scripts.migrate_to_sqlite import migrar


def _crear_origen_con_un_usuario(tmp_path):
    origen_path = tmp_path / "origen.db"
    origen_url = f"sqlite:///{origen_path}"
    engine = create_pulse_engine(origen_url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            UserProfile.__table__.insert(),
            [
                {
                    "nombre": "Miguel",
                    "fecha_nacimiento": date(1990, 1, 1),
                    "sexo": "M",
                    "altura_cm": 180,
                }
            ],
        )
    return origen_url


class TestMigrarASqlite:
    def test_copia_las_filas_del_origen_al_destino_nuevo(self, tmp_path):
        origen_url = _crear_origen_con_un_usuario(tmp_path)
        destino_path = tmp_path / "destino.db"

        migrar(origen_url, destino_path)

        engine_destino = create_pulse_engine(f"sqlite:///{destino_path}")
        with engine_destino.connect() as conn:
            filas = conn.execute(UserProfile.__table__.select()).fetchall()
        assert len(filas) == 1
        assert filas[0].nombre == "Miguel"

    def test_respeta_el_orden_topologico_de_fks_entre_tablas(self, tmp_path):
        # Épica K, hallazgo de code-review (M-3): el motivo de ser de
        # `Base.metadata.sorted_tables` es respetar dependencias FK -
        # sin este test, un cambio que rompiera ese orden (ej. volver
        # a un `Base.metadata.tables.values()` sin ordenar) pasaría
        # inadvertido con el test de una sola tabla.
        origen_url = _crear_origen_con_un_usuario(tmp_path)
        origen_engine = create_pulse_engine(origen_url)
        with origen_engine.begin() as conn:
            conn.execute(
                ReadinessLog.__table__.insert(),
                [
                    {
                        "user_id": 1,
                        "fecha": date(2026, 8, 1),
                        "resultado": "green",
                        "joint_pain_flag": False,
                    }
                ],
            )
        destino_path = tmp_path / "destino.db"

        migrar(origen_url, destino_path)

        engine_destino = create_pulse_engine(f"sqlite:///{destino_path}")
        with engine_destino.connect() as conn:
            logs = conn.execute(ReadinessLog.__table__.select()).fetchall()
        assert len(logs) == 1
        assert logs[0].user_id == 1

    def test_origen_vacio_no_copia_ninguna_fila(self, tmp_path):
        origen_path = tmp_path / "origen_vacio.db"
        origen_url = f"sqlite:///{origen_path}"
        create_all_engine = create_pulse_engine(origen_url)
        Base.metadata.create_all(create_all_engine)
        destino_path = tmp_path / "destino.db"

        migrar(origen_url, destino_path)

        engine_destino = create_pulse_engine(f"sqlite:///{destino_path}")
        with engine_destino.connect() as conn:
            filas = conn.execute(UserProfile.__table__.select()).fetchall()
        assert len(filas) == 0

    def test_falla_si_el_destino_ya_existe(self, tmp_path):
        origen_url = _crear_origen_con_un_usuario(tmp_path)
        destino_path = tmp_path / "destino.db"
        destino_path.write_text("no deberia sobrescribirse")

        with pytest.raises(FileExistsError):
            migrar(origen_url, destino_path)
