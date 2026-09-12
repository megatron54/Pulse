"""Tests para services.feelfit_sync_service - TDD."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, BodyMeasurements, UserProfile
from services.errors import EntityNotFoundError
from services.feelfit_sync_service import sync_feelfit_measurements


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def usuario(session):
    u = UserProfile(nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M")
    session.add(u)
    session.commit()
    return u


class _FakeFeelfitClient:
    def __init__(self, mediciones: list[dict]):
        self._mediciones = mediciones

    def get_measurements_raw(self, last_updated_at=0):
        return {"measurements": self._mediciones}


class TestSyncFeelfitMeasurements:
    def test_inserta_las_mediciones_nuevas(self, session, usuario):
        client = _FakeFeelfitClient(
            [
                {
                    "time_stamp": 1723300000,
                    "weight": 74.1,
                    "bodyfat": 19.4,
                    "muscle": 33.2,
                    "bone": 3.1,
                    "water": 55.6,
                    "bmi": 22.9,
                },
                {"time_stamp": 1723400000, "weight": 73.8},
            ]
        )

        insertadas = sync_feelfit_measurements(session, usuario.id, client)

        assert insertadas == 2
        filas = session.query(BodyMeasurements).filter_by(user_id=usuario.id).all()
        assert len(filas) == 2
        con_bodyfat = next(f for f in filas if f.peso_kg == 74.1)
        assert con_bodyfat.bodyfat_pct_rango_min == 19.4
        assert con_bodyfat.metodo == "feelfit_bioimpedance"
        assert con_bodyfat.muscle_kg == 33.2
        assert con_bodyfat.bone_kg == 3.1
        assert con_bodyfat.water_pct == 55.6
        assert con_bodyfat.bmi == 22.9
        sin_bodyfat = next(f for f in filas if f.peso_kg == 73.8)
        assert sin_bodyfat.bodyfat_pct_rango_min is None
        assert sin_bodyfat.metodo == "manual"
        # "unknown is not zero": sin datos de bioimpedancia en el
        # payload crudo, nunca se rellenan con 0.
        assert sin_bodyfat.muscle_kg is None
        assert sin_bodyfat.bone_kg is None
        assert sin_bodyfat.water_pct is None
        assert sin_bodyfat.bmi is None

    def test_es_idempotente_no_duplica_mediciones_ya_sincronizadas(self, session, usuario):
        client = _FakeFeelfitClient([{"time_stamp": 1723300000, "weight": 74.1}])
        sync_feelfit_measurements(session, usuario.id, client)

        insertadas_segunda_vez = sync_feelfit_measurements(session, usuario.id, client)

        assert insertadas_segunda_vez == 0
        assert session.query(BodyMeasurements).filter_by(user_id=usuario.id).count() == 1

    def test_ignora_mediciones_sin_peso(self, session, usuario):
        # "unknown is not zero": una medición sin peso (payload
        # inesperado) no debe registrarse como peso_kg=0.
        client = _FakeFeelfitClient([{"time_stamp": 1723300000, "bodyfat": 19.4}])

        insertadas = sync_feelfit_measurements(session, usuario.id, client)

        assert insertadas == 0
        assert session.query(BodyMeasurements).filter_by(user_id=usuario.id).count() == 0

    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        client = _FakeFeelfitClient([])
        with pytest.raises(EntityNotFoundError):
            sync_feelfit_measurements(session, 99999, client)

    def test_no_permite_mezclar_mediciones_de_otro_usuario_en_la_deduplicacion(
        self, session, usuario
    ):
        otro = UserProfile(nombre="Otro", altura_cm=170.0, fecha_nacimiento=date(1990, 1, 1), sexo="F")
        session.add(otro)
        session.commit()
        session.add(
            BodyMeasurements(
                user_id=otro.id, fecha=date(2026, 8, 1), peso_kg=60.0, fuente_externa_id="1723300000"
            )
        )
        session.commit()

        client = _FakeFeelfitClient([{"time_stamp": 1723300000, "weight": 74.1}])
        insertadas = sync_feelfit_measurements(session, usuario.id, client)

        assert insertadas == 1

    def test_carrera_real_dos_procesos_sincronizando_la_misma_medicion_a_la_vez(
        self, tmp_path
    ):
        # Carrera real (no simulada con mocks): dos ENGINES/SESIONES
        # separadas apuntando al MISMO archivo SQLite, sincronizando en
        # paralelo la MISMA medición para el mismo usuario. El
        # UNIQUE(user_id, fuente_externa_id) debe rechazar al perdedor
        # de la carrera vía IntegrityError, capturado por fila (hallazgo
        # HIGH de code-review) - nunca debe tumbar el hilo entero ni
        # duplicar la fila.
        import threading

        from sqlalchemy import create_engine

        db_path = tmp_path / "carrera.db"
        engine_setup = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine_setup)
        with Session(engine_setup) as s:
            u = UserProfile(
                nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M"
            )
            s.add(u)
            s.commit()
            user_id = u.id

        errores = []

        def _sincronizar():
            try:
                engine = create_engine(f"sqlite:///{db_path}")
                with Session(engine) as s:
                    client = _FakeFeelfitClient([{"time_stamp": 1723300000, "weight": 74.1}])
                    sync_feelfit_measurements(s, user_id, client)
            except Exception as exc:  # noqa: BLE001 - la carrera NUNCA debe propagar un error
                errores.append(exc)

        hilos = [threading.Thread(target=_sincronizar) for _ in range(5)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        assert errores == []
        with Session(create_engine(f"sqlite:///{db_path}")) as s:
            filas = s.query(BodyMeasurements).filter_by(user_id=user_id).all()
            assert len(filas) == 1  # la carrera nunca duplica la medición
