"""Test de regresión del hallazgo real de Fase J: un Postgres/SQLite
recién creado (sin tablas) debe quedar con el schema completo tras
ejecutar `scripts.ensure_schema.main()`, y una segunda ejecución sobre
una base YA poblada no debe fallar ni borrar datos (idempotencia de
`create_all`).

También cubre el hallazgo MEDIUM de code-review de la integración
Feelfit: `create_all` NUNCA añade una columna a una tabla YA EXISTENTE
- `_migrar_columnas_aditivas` debe parchear `body_measurements` con
`fuente_externa_id` cuando la tabla ya existía de antes (simulando el
volumen `pulse-postgres-data` real de docker-compose), sin perder las
filas ya guardadas."""
from datetime import date

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from models.schema import Base, UserProfile
from scripts.ensure_schema import main as ensure_schema_main


def test_crea_todas_las_tablas_en_una_base_de_datos_vacia(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr("scripts.ensure_schema.create_pulse_engine", lambda: engine)

    ensure_schema_main()

    tablas = inspect(engine).get_table_names()
    assert "user_profile" in tablas
    assert "garmin_credentials" in tablas
    assert len(tablas) == len(Base.metadata.tables)


def test_es_idempotente_y_no_borra_datos_existentes(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr("scripts.ensure_schema.create_pulse_engine", lambda: engine)

    ensure_schema_main()
    with Session(engine) as session:
        session.add(
            UserProfile(
                nombre="Persistente",
                altura_cm=180.0,
                fecha_nacimiento=date(1995, 1, 1),
                sexo="M",
            )
        )
        session.commit()

    ensure_schema_main()  # segunda ejecución, no debe borrar nada

    with Session(engine) as session:
        assert session.query(UserProfile).filter_by(nombre="Persistente").count() == 1


def test_reintenta_con_backoff_si_falla_transitoriamente_y_luego_funciona(monkeypatch):
    """H2 de code-review: `pg_isready` no garantiza que Postgres acepte
    ya conexiones de aplicación (carrera de arranque conocida) - un
    fallo transitorio en el primer intento no debe tumbar el contenedor
    entero, debe reintentar con backoff."""
    llamadas = {"n": 0}
    engine_real = create_engine("sqlite:///:memory:")
    create_all_original = Base.metadata.create_all

    def create_all_con_fallo_inicial(bind):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise RuntimeError("Postgres aún no acepta conexiones")
        create_all_original(bind)

    monkeypatch.setattr("scripts.ensure_schema.create_pulse_engine", lambda: engine_real)
    monkeypatch.setattr(Base.metadata, "create_all", create_all_con_fallo_inicial)
    monkeypatch.setattr("scripts.ensure_schema.time.sleep", lambda _segundos: None)

    ensure_schema_main()  # no debe lanzar - el segundo intento funciona

    assert llamadas["n"] == 2


def test_lanza_tras_agotar_los_reintentos_si_el_fallo_persiste(monkeypatch):
    def create_all_que_siempre_falla(bind):
        raise RuntimeError("Postgres caído de verdad")

    monkeypatch.setattr(
        "scripts.ensure_schema.create_pulse_engine", lambda: create_engine("sqlite:///:memory:")
    )
    monkeypatch.setattr(Base.metadata, "create_all", create_all_que_siempre_falla)
    monkeypatch.setattr("scripts.ensure_schema.time.sleep", lambda _segundos: None)

    with pytest.raises(RuntimeError, match="tras 5 intentos"):
        ensure_schema_main()


def test_migra_fuente_externa_id_en_una_body_measurements_ya_existente(monkeypatch):
    # Simula el volumen pulse-postgres-data real: una tabla
    # body_measurements creada ANTES de que existiera la columna
    # fuente_externa_id (forma mínima, sin ella), con una fila real ya
    # guardada - create_all por sí solo NUNCA la habría añadido.
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE body_measurements ("
                "id INTEGER PRIMARY KEY, user_id INTEGER, fecha DATE, peso_kg FLOAT, "
                "metodo VARCHAR(30) DEFAULT 'manual')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO body_measurements (id, user_id, fecha, peso_kg, metodo) "
                "VALUES (1, 1, '2026-08-01', 81.0, 'manual')"
            )
        )

    monkeypatch.setattr("scripts.ensure_schema.create_pulse_engine", lambda: engine)

    ensure_schema_main()

    inspector = inspect(engine)
    columnas = {c["name"] for c in inspector.get_columns("body_measurements")}
    assert "fuente_externa_id" in columnas
    indices = {ix["name"] for ix in inspector.get_indexes("body_measurements")}
    assert "uq_body_measurements_user_fuente_externa" in indices

    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT peso_kg, fuente_externa_id FROM body_measurements WHERE id=1")
        ).one()
        assert fila.peso_kg == 81.0
        assert fila.fuente_externa_id is None  # dato preexistente intacto, sin inventar un valor

    # Segunda ejecución: ya migrada, no debe fallar ni volver a intentar
    # el ALTER/CREATE INDEX (que rompería con "columna ya existe").
    ensure_schema_main()
