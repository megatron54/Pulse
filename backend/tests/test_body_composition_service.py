"""Tests para services.body_composition_service — TDD.

Conecta: UserProfile (sexo, altura) -> engine.body_composition (Capa 1,
ya aprobado) -> models.BodyMeasurements (persistencia, append-only) ->
AuditLog.

Permite registrar solo el peso (sin medidas de cinta) para el caso
común de un pesaje diario rápido - en ese caso no se calcula %grasa y
el método queda como "manual" (ver BodyMeasurements.metodo por defecto
en models/schema.py).
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import AuditLog, Base, BodyMeasurements, UserProfile
from services.body_composition_service import record_body_measurement


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def usuario_hombre(session):
    u = UserProfile(
        nombre="Test", altura_cm=177.8, fecha_nacimiento=date(1995, 1, 1), sexo="M"
    )
    session.add(u)
    session.commit()
    return u


@pytest.fixture()
def usuario_mujer(session):
    u = UserProfile(
        nombre="Test", altura_cm=165.1, fecha_nacimiento=date(1995, 1, 1), sexo="F"
    )
    session.add(u)
    session.commit()
    return u


class TestRecordBodyMeasurement:
    def test_solo_peso_no_calcula_bodyfat_y_metodo_es_manual(self, session, usuario_hombre):
        resultado = record_body_measurement(
            session, usuario_hombre.id, target_date=date(2026, 8, 2), peso_kg=80.0
        )
        assert resultado.metodo == "manual"
        assert resultado.bodyfat_pct_rango_min is None
        assert resultado.bodyfat_pct_rango_max is None

    def test_con_cuello_y_cintura_calcula_bodyfat_navy_hombre(self, session, usuario_hombre):
        resultado = record_body_measurement(
            session,
            usuario_hombre.id,
            target_date=date(2026, 8, 2),
            peso_kg=80.0,
            cuello_cm=38.1,
            cintura_cm=86.36,
        )
        assert resultado.metodo == "navy"
        assert resultado.bodyfat_pct_rango_min is not None
        assert resultado.bodyfat_pct_rango_min < resultado.bodyfat_pct_rango_max

    def test_mujer_requiere_cadera_para_navy_si_no_lanza_error_de_dominio(
        self, session, usuario_mujer
    ):
        # Sin cadera, no se puede aplicar Navy a una mujer - se registra
        # el peso igualmente (metodo=manual) en vez de fallar toda la
        # operación por un dato opcional incompleto.
        resultado = record_body_measurement(
            session,
            usuario_mujer.id,
            target_date=date(2026, 8, 2),
            peso_kg=60.0,
            cuello_cm=33.0,
            cintura_cm=76.2,
        )
        assert resultado.metodo == "manual"
        assert resultado.bodyfat_pct_rango_min is None

    def test_mujer_con_cadera_calcula_bodyfat_navy(self, session, usuario_mujer):
        resultado = record_body_measurement(
            session,
            usuario_mujer.id,
            target_date=date(2026, 8, 2),
            peso_kg=60.0,
            cuello_cm=33.0,
            cintura_cm=76.2,
            cadera_cm=96.5,
        )
        assert resultado.metodo == "navy"
        assert resultado.bodyfat_pct_rango_min is not None

    def test_persiste_en_body_measurements_append_only(self, session, usuario_hombre):
        record_body_measurement(
            session, usuario_hombre.id, target_date=date(2026, 8, 2), peso_kg=80.0
        )
        record_body_measurement(
            session, usuario_hombre.id, target_date=date(2026, 8, 2), peso_kg=79.8
        )
        filas = session.query(BodyMeasurements).filter_by(user_id=usuario_hombre.id).all()
        assert len(filas) == 2

    def test_registra_auditoria(self, session, usuario_hombre):
        record_body_measurement(
            session,
            usuario_hombre.id,
            target_date=date(2026, 8, 2),
            peso_kg=80.0,
            cuello_cm=38.1,
            cintura_cm=86.36,
        )
        auditoria = (
            session.query(AuditLog)
            .filter_by(user_id=usuario_hombre.id, modulo="body_composition")
            .one()
        )
        assert auditoria.output == "navy"
        assert auditoria.regla_disparada == "estimate_body_fat_navy"

    def test_auditoria_distingue_sin_medidas_de_cadera_faltante(self, session, usuario_hombre, usuario_mujer):
        record_body_measurement(
            session, usuario_hombre.id, target_date=date(2026, 8, 2), peso_kg=80.0
        )
        record_body_measurement(
            session,
            usuario_mujer.id,
            target_date=date(2026, 8, 2),
            peso_kg=60.0,
            cuello_cm=33.0,
            cintura_cm=76.2,
        )
        auditoria_sin_medidas = (
            session.query(AuditLog).filter_by(user_id=usuario_hombre.id).one()
        )
        auditoria_cadera_faltante = (
            session.query(AuditLog).filter_by(user_id=usuario_mujer.id).one()
        )
        assert auditoria_sin_medidas.regla_disparada == "manual_sin_medidas"
        assert auditoria_sin_medidas.decision_final == "peso_sin_bodyfat"
        assert auditoria_cadera_faltante.regla_disparada == "manual_cadera_faltante"

    def test_rechaza_si_el_usuario_no_existe(self, session):
        with pytest.raises(ValueError):
            record_body_measurement(
                session, user_id=9999, target_date=date(2026, 8, 2), peso_kg=80.0
            )

    def test_rechaza_medidas_invalidas_de_navy_sin_perder_la_transaccion_limpia(
        self, session, usuario_hombre
    ):
        # cintura <= cuello es un error de medición real (engine.body_
        # composition ya lo rechaza) - debe propagarse, no silenciarse
        # como si fuera "manual".
        with pytest.raises(ValueError):
            record_body_measurement(
                session,
                usuario_hombre.id,
                target_date=date(2026, 8, 2),
                peso_kg=80.0,
                cuello_cm=40.0,
                cintura_cm=38.0,
            )
        # No debe haber quedado ninguna medición a medias persistida.
        filas = session.query(BodyMeasurements).filter_by(user_id=usuario_hombre.id).all()
        assert len(filas) == 0
        # Tampoco ningún AuditLog huérfano de una decisión que nunca se
        # completó (misma vulnerabilidad estructural que BodyMeasurements).
        auditoria = session.query(AuditLog).filter_by(user_id=usuario_hombre.id).all()
        assert len(auditoria) == 0
