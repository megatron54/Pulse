"""Épica K (app de escritorio nativa, 00-research/09-app-nativa-escritorio.md):
`create_pulse_engine` debe funcionar igual de bien contra SQLite (motor
de la app de escritorio empaquetada) que contra Postgres (motor de
desarrollo/Docker) - sin esto, un `SELECT` concurrente desde dos threads
de FastAPI contra un archivo SQLite falla con
`sqlite3.ProgrammingError: SQLite objects created in a thread...`."""
from __future__ import annotations

from sqlalchemy import text

from models.database import create_pulse_engine


class TestCreatePulseEngineSqlite:
    def test_engine_sqlite_admite_uso_desde_otro_thread(self, tmp_path):
        db_path = tmp_path / "pulse.db"
        engine = create_pulse_engine(f"sqlite:///{db_path}")

        resultado = {}

        def consulta_en_otro_thread():
            with engine.connect() as conn:
                resultado["valor"] = conn.execute(text("SELECT 1")).scalar()

        import threading

        conexion_inicial = engine.connect()
        conexion_inicial.close()

        hilo = threading.Thread(target=consulta_en_otro_thread)
        hilo.start()
        hilo.join()

        assert resultado["valor"] == 1

    def test_engine_postgres_no_recibe_connect_args_de_sqlite(self):
        # No debe reventar al construir el engine (no se conecta de
        # verdad en este test) - confirma que el connect_args especial
        # de SQLite no se aplica incondicionalmente a cualquier motor.
        engine = create_pulse_engine("postgresql+psycopg2://u:p@localhost:5433/db")
        assert engine.url.get_backend_name() == "postgresql"
