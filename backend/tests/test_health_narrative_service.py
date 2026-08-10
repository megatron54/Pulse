"""Tests para coach.health_narrative_service — TDD.

Épica H del plan de expansión (02-roadmap/03-vision-produccion.md):
primer contexto real que consume `generate_context_narrative`. La
"decisión" que se explica es el `ReadinessLog.resultado` YA calculado
por `services.readiness_service.sync_and_compute_readiness` (Capa 1/2)
- este servicio nunca recalcula nada, solo lee lo ya decidido y lo
combina con los datos crudos de recovery para que la Capa 3 los cite.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from coach.health_narrative_service import generate_health_narrative_for_user
from models.schema import Base, GarminDailyMetrics, ReadinessLog, UserProfile
from services.errors import EntityNotFoundError


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


class TestGenerateHealthNarrativeForUser:
    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        with pytest.raises(EntityNotFoundError):
            generate_health_narrative_for_user(
                session, user_id=99999, fecha=date(2026, 8, 6), gemini_client=None
            )

    def test_sin_readiness_calculado_ese_dia_devuelve_none(self, session, usuario):
        # "unknown is not zero" a nivel de decisión: si la Capa 1 aún no
        # ha decidido nada para ese día (el scheduler no ha corrido, o
        # es un día futuro), no hay nada honesto que explicar todavía -
        # nunca se inventa un estado de recovery.
        resultado = generate_health_narrative_for_user(
            session, user_id=usuario.id, fecha=date(2026, 8, 6), gemini_client=None
        )
        assert resultado is None

    def test_con_readiness_calculado_genera_narrativa_citando_los_datos_reales(
        self, session, usuario
    ):
        session.add(
            ReadinessLog(user_id=usuario.id, fecha=date(2026, 8, 6), resultado="green")
        )
        session.add(
            GarminDailyMetrics(
                user_id=usuario.id,
                fecha=date(2026, 8, 6),
                hrv_value=60.0,
                body_battery_am=77,
                sleep_score=82,
                stress_avg=10,
                resting_hr=54,
            )
        )
        session.commit()

        resultado = generate_health_narrative_for_user(
            session, user_id=usuario.id, fecha=date(2026, 8, 6), gemini_client=None
        )

        assert resultado is not None
        assert resultado.source == "template"
        assert "60" in resultado.text
        assert "82" in resultado.text

    def test_sin_metricas_garmin_ese_dia_igual_explica_solo_la_decision(self, session, usuario):
        # El readiness pudo calcularse por check-in manual sin que
        # existan filas de GarminDailyMetrics ese día exacto - no debe
        # romperse, solo tendrá menos datos que citar.
        session.add(ReadinessLog(user_id=usuario.id, fecha=date(2026, 8, 6), resultado="red"))
        session.commit()

        resultado = generate_health_narrative_for_user(
            session, user_id=usuario.id, fecha=date(2026, 8, 6), gemini_client=None
        )

        assert resultado is not None
        assert "rojo" in resultado.text.lower() or "baja" in resultado.text.lower()

    def test_usa_la_baseline_de_hrv_28d_cuando_hay_historial_suficiente(self, session, usuario):
        from datetime import timedelta

        for dias_atras in range(1, 29):
            session.add(
                GarminDailyMetrics(
                    user_id=usuario.id,
                    fecha=date(2026, 8, 6) - timedelta(days=dias_atras),
                    hrv_value=50.0,
                )
            )
        session.add(
            GarminDailyMetrics(user_id=usuario.id, fecha=date(2026, 8, 6), hrv_value=60.0)
        )
        session.add(ReadinessLog(user_id=usuario.id, fecha=date(2026, 8, 6), resultado="green"))
        session.commit()

        resultado = generate_health_narrative_for_user(
            session, user_id=usuario.id, fecha=date(2026, 8, 6), gemini_client=None
        )

        assert "50" in resultado.text  # baseline citada en la plantilla
