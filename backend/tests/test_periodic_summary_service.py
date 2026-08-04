"""Tests para services.periodic_summary_service — TDD.

Épica MUST-HAVE #4 del backlog priorizado (02-roadmap/
03-vision-produccion.md): resumen periódico (semanal/mensual) de
tendencias - agregación pura sobre datos ya existentes (readiness,
carga de entrenamiento, peso, actividades Garmin), sin integración
externa nueva.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, BodyMeasurements, GarminActivity, ReadinessLog, UserProfile
from services.periodic_summary_service import compute_periodic_summary


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


class TestComputePeriodicSummary:
    def test_sin_ningun_dato_devuelve_ceros_no_fabrica_tendencias(self, session, usuario):
        resultado = compute_periodic_summary(
            session, usuario.id, as_of=date(2026, 8, 20), days=7
        )
        assert resultado.dias_con_checkin_readiness == 0
        assert resultado.distribucion_readiness == {"green": 0, "yellow": 0, "red": 0}
        assert resultado.peso_inicio_kg is None
        assert resultado.peso_fin_kg is None
        assert resultado.peso_delta_kg is None
        assert resultado.actividades_totales == 0

    def test_cuenta_la_distribucion_de_readiness_por_dia_no_por_fila(self, session, usuario):
        hoy = date(2026, 8, 20)
        # Dos check-ins el mismo día: debe contar solo el ÚLTIMO (append-only,
        # mismo criterio que get_latest_readiness_level en el resto del proyecto).
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="yellow"))
        session.commit()
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="green"))
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=1), resultado="red"))
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)

        assert resultado.dias_con_checkin_readiness == 2
        assert resultado.distribucion_readiness == {"green": 1, "yellow": 0, "red": 1}

    def test_calcula_delta_de_peso_entre_primera_y_ultima_medicion_de_la_ventana(
        self, session, usuario
    ):
        hoy = date(2026, 8, 20)
        session.add(
            BodyMeasurements(user_id=usuario.id, fecha=hoy - timedelta(days=6), peso_kg=80.0)
        )
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=79.2))
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)

        assert resultado.peso_inicio_kg == 80.0
        assert resultado.peso_fin_kg == 79.2
        assert resultado.peso_delta_kg == pytest.approx(-0.8)

    def test_una_sola_medicion_de_peso_no_da_delta(self, session, usuario):
        hoy = date(2026, 8, 20)
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=80.0))
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)

        assert resultado.peso_inicio_kg == 80.0
        assert resultado.peso_fin_kg == 80.0
        assert resultado.peso_delta_kg is None

    def test_cuenta_actividades_garmin_de_la_ventana(self, session, usuario):
        hoy = date(2026, 8, 20)
        session.add(
            GarminActivity(
                user_id=usuario.id,
                activity_id="1",
                fecha=hoy - timedelta(days=2),
                tipo="running",
                duracion_seg=1800,
            )
        )
        session.add(
            GarminActivity(
                user_id=usuario.id,
                activity_id="2",
                fecha=hoy - timedelta(days=1),
                tipo="strength_training",
                duracion_seg=2700,
            )
        )
        # Fuera de la ventana de 7 días.
        session.add(
            GarminActivity(
                user_id=usuario.id,
                activity_id="3",
                fecha=hoy - timedelta(days=30),
                tipo="cycling",
                duracion_seg=3600,
            )
        )
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)

        assert resultado.actividades_totales == 2
        assert resultado.duracion_actividades_total_seg == 4500

    def test_no_incluye_datos_de_otro_usuario(self, session, usuario):
        hoy = date(2026, 8, 20)
        otro = UserProfile(
            nombre="Otro", altura_cm=170.0, fecha_nacimiento=date(1990, 1, 1), sexo="F"
        )
        session.add(otro)
        session.commit()
        session.add(ReadinessLog(user_id=otro.id, fecha=hoy, resultado="red"))
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)
        assert resultado.dias_con_checkin_readiness == 0

    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        from services.errors import EntityNotFoundError

        with pytest.raises(EntityNotFoundError):
            compute_periodic_summary(session, 99999, as_of=date(2026, 8, 20), days=7)

    def test_ventana_de_7_dias_excluye_el_octavo_dia_hacia_atras(self, session, usuario):
        # Regresión CRITICAL de code-review: get_readiness_history y
        # get_weight_history devuelven internamente days+1 días (límites
        # inclusivos por ambos lados) - el servicio debe filtrar
        # explícitamente para que la ventana sea EXACTAMENTE
        # [as_of-6, as_of] con days=7, igual que get_activity_history.
        hoy = date(2026, 8, 20)
        dentro_de_la_ventana = hoy - timedelta(days=6)
        justo_fuera = hoy - timedelta(days=7)

        session.add(ReadinessLog(user_id=usuario.id, fecha=dentro_de_la_ventana, resultado="green"))
        session.add(ReadinessLog(user_id=usuario.id, fecha=justo_fuera, resultado="red"))
        session.add(BodyMeasurements(user_id=usuario.id, fecha=dentro_de_la_ventana, peso_kg=80.0))
        session.add(BodyMeasurements(user_id=usuario.id, fecha=justo_fuera, peso_kg=999.0))
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)

        assert resultado.dias_con_checkin_readiness == 1
        assert resultado.distribucion_readiness == {"green": 1, "yellow": 0, "red": 0}
        assert resultado.peso_inicio_kg == 80.0
        assert resultado.peso_fin_kg == 80.0

    def test_varias_mediciones_de_peso_el_mismo_dia_no_fabrican_una_tendencia_intradia(
        self, session, usuario
    ):
        # Regresión H1 de code-review: dos filas de peso el MISMO día
        # (p.ej. una resincronización) no deben contarse como "2 días"
        # con un delta espurio - se colapsan a la última fila del día,
        # mismo criterio que get_latest_weight_kg.
        hoy = date(2026, 8, 20)
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=81.0))
        session.commit()
        session.add(BodyMeasurements(user_id=usuario.id, fecha=hoy, peso_kg=79.5))
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)

        assert resultado.peso_inicio_kg == 79.5
        assert resultado.peso_fin_kg == 79.5
        assert resultado.peso_delta_kg is None

    def test_actividades_sin_duracion_cuentan_en_el_total_pero_no_en_los_minutos(
        self, session, usuario
    ):
        hoy = date(2026, 8, 20)
        session.add(
            GarminActivity(
                user_id=usuario.id,
                activity_id="1",
                fecha=hoy,
                tipo="running",
                duracion_seg=None,
            )
        )
        session.commit()

        resultado = compute_periodic_summary(session, usuario.id, as_of=hoy, days=7)

        assert resultado.actividades_totales == 1
        assert resultado.duracion_actividades_total_seg == 0
