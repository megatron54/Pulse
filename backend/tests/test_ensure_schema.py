"""Test de regresión del hallazgo real de Fase J: un Postgres/SQLite
recién creado (sin tablas) debe quedar con el schema completo tras
ejecutar `scripts.ensure_schema.main()`, y una segunda ejecución sobre
una base YA poblada no debe fallar ni borrar datos (idempotencia de
`create_all`)."""
from datetime import date

import pytest
from sqlalchemy import create_engine, inspect
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
