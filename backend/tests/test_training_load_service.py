"""Tests para services.training_load_service — TDD.

Fase MUST-HAVE #1 del backlog priorizado (docs/02-roadmap/
03-vision-produccion.md, investigación de auditoría de competidores):
hoy el ACWR es un número que el usuario escribe a mano en el check-in,
no una medida real. Este servicio calcula un ACWR de verdad a partir
del historial de `volume_pct` que `session_service` ya decide cada día
(agudo = media móvil 7 días, crónico = media móvil 28 días, formula
estándar de la literatura de carga de entrenamiento citada en
engine/periodization.py).
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, ReadinessLog, UserProfile
from services.training_load_service import compute_training_load


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


def _agregar_volumen(session, user_id, fecha, volumen):
    log = ReadinessLog(user_id=user_id, fecha=fecha, resultado="green")
    session.add(log)
    session.flush()
    log.volumen_pct_ajustado = volumen
    session.commit()


class TestComputeTrainingLoad:
    def test_sin_historial_devuelve_datos_insuficientes_sin_fabricar_un_acwr(self, session, usuario):
        # Principio "unknown is not zero": sin ningún día de volumen
        # registrado, NO se devuelve un ACWR de 0 o 1 fabricado.
        resultado = compute_training_load(session, usuario.id, as_of=date(2026, 8, 10))
        assert resultado.datos_suficientes is False
        assert resultado.acwr is None

    def test_calcula_acwr_como_media_7d_entre_media_28d(self, session, usuario):
        hoy = date(2026, 8, 28)
        # 28 días de historial: los últimos 7 con volumen alto (100),
        # los 21 anteriores con volumen moderado (50).
        for i in range(28):
            fecha = hoy - timedelta(days=27 - i)
            volumen = 100 if i >= 21 else 50
            _agregar_volumen(session, usuario.id, fecha, volumen)

        resultado = compute_training_load(session, usuario.id, as_of=hoy)

        # agudo (últimos 7 días, incluyendo hoy) = 100
        # crónico (últimos 28 días) = (21*50 + 7*100) / 28 = 62.5
        assert resultado.acute_avg_7d == pytest.approx(100.0)
        assert resultado.chronic_avg_28d == pytest.approx(62.5)
        assert resultado.acwr == pytest.approx(100.0 / 62.5)
        assert resultado.datos_suficientes is True

    def test_datos_suficientes_exige_al_menos_14_dias_de_historial_cronico(self, session, usuario):
        hoy = date(2026, 8, 10)
        # Solo 5 días de historial - muy poco para un crónico de 28d fiable.
        for i in range(5):
            _agregar_volumen(session, usuario.id, hoy - timedelta(days=4 - i), 80)

        resultado = compute_training_load(session, usuario.id, as_of=hoy)

        assert resultado.dias_con_dato_cronico == 5
        assert resultado.datos_suficientes is False
        # Aun así se devuelve el ACWR calculable (informativo), pero
        # marcado como no fiable via datos_suficientes=False - la UI
        # decide si lo muestra atenuado/con aviso.
        assert resultado.acwr is not None

    def test_no_falla_con_division_por_cero_si_el_cronico_es_todo_volumen_0(self, session, usuario):
        hoy = date(2026, 8, 10)
        for i in range(28):
            _agregar_volumen(session, usuario.id, hoy - timedelta(days=27 - i), 0)

        resultado = compute_training_load(session, usuario.id, as_of=hoy)

        assert resultado.chronic_avg_28d == 0.0
        assert resultado.acwr is None  # 0/0 no es un ratio significativo, no se fabrica

    def test_ignora_dias_sin_dato_en_vez_de_tratarlos_como_volumen_0(self, session, usuario):
        hoy = date(2026, 8, 10)
        # Solo 2 días con dato en toda la ventana - el resto de días sin
        # check-in NO deben contar como volumen 0 en la media.
        _agregar_volumen(session, usuario.id, hoy, 100)
        _agregar_volumen(session, usuario.id, hoy - timedelta(days=1), 100)

        resultado = compute_training_load(session, usuario.id, as_of=hoy)

        assert resultado.acute_avg_7d == pytest.approx(100.0)
        assert resultado.chronic_avg_28d == pytest.approx(100.0)
