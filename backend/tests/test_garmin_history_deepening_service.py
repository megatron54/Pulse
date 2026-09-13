"""Profundización gradual del histórico de Garmin (petición explícita del
usuario: "sería genial tener todo mi historial, no solo los últimos 90
días") - ver services.garmin_history_deepening_service."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminCredentials, UserProfile
from services.garmin_history_deepening_service import deepen_history_for_all_users


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _api_factory(fake_api):
    return lambda *args, **kwargs: fake_api


def _fake_api_sin_datos():
    fake_api = MagicMock()
    fake_api.get_activities_by_date.return_value = []
    fake_api.get_hrv_data.return_value = None
    fake_api.get_training_readiness.return_value = None
    fake_api.get_body_battery.return_value = None
    fake_api.get_sleep_data.return_value = None
    fake_api.get_stress_data.return_value = None
    fake_api.get_rhr_day.return_value = None
    fake_api.get_max_metrics.return_value = None
    return fake_api


def _usuario_con_credenciales(session, *, frontera: date) -> GarminCredentials:
    usuario = UserProfile(nombre="Miguel", sexo="M", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28))
    session.add(usuario)
    session.flush()
    cred = GarminCredentials(
        user_id=usuario.id,
        token_store_dir="/data/garmin-tokens/pulse-user-1",
        activo=True,
        historial_sincronizado_desde=frontera,
    )
    session.add(cred)
    session.commit()
    return cred


class TestDeepenHistoryForAllUsers:
    def test_retrocede_la_frontera_dias_por_pasada_dias(self, session):
        cred = _usuario_con_credenciales(session, frontera=date(2026, 6, 1))
        fake_api = _fake_api_sin_datos()

        resultado = deepen_history_for_all_users(
            session,
            hoy=date(2026, 9, 1),
            dias_por_pasada=30,
            api_factory=_api_factory(fake_api),
        )

        session.refresh(cred)
        assert resultado.usuarios_avanzados == 1
        assert resultado.usuarios_completos == 0
        assert resultado.usuarios_fallidos == 0
        assert cred.historial_sincronizado_desde == date(2026, 5, 2)

    def test_se_detiene_en_el_limite_de_historial_maximo(self, session):
        # Frontera a solo 10 días del límite de 730: la pasada debe
        # acotarse a esos 10 días, no a los 30 de `dias_por_pasada`, y
        # marcar al usuario como completo.
        hoy = date(2026, 9, 1)
        limite = hoy.toordinal() - 729
        frontera = date.fromordinal(limite + 10)
        cred = _usuario_con_credenciales(session, frontera=frontera)
        fake_api = _fake_api_sin_datos()

        resultado = deepen_history_for_all_users(
            session,
            hoy=hoy,
            dias_por_pasada=30,
            dias_maximo_historial=730,
            api_factory=_api_factory(fake_api),
        )

        session.refresh(cred)
        assert resultado.usuarios_avanzados == 1
        assert resultado.usuarios_completos == 1
        assert cred.historial_sincronizado_desde == date.fromordinal(limite)

    def test_usuario_ya_completo_no_se_vuelve_a_procesar(self, session):
        hoy = date(2026, 9, 1)
        limite = date.fromordinal(hoy.toordinal() - 729)
        _usuario_con_credenciales(session, frontera=limite)
        fake_api = _fake_api_sin_datos()

        resultado = deepen_history_for_all_users(
            session,
            hoy=hoy,
            dias_maximo_historial=730,
            api_factory=_api_factory(fake_api),
        )

        assert resultado.usuarios_avanzados == 0
        assert resultado.usuarios_completos == 0
        assert resultado.usuarios_fallidos == 0
        fake_api.login.assert_not_called()

    def test_usuario_sin_frontera_definida_se_ignora(self, session):
        # Sin backfill inicial completado todavía (historial_sincronizado_
        # desde=None) no hay desde dónde retroceder - este job no
        # sustituye al backfill inicial, solo lo extiende.
        usuario = UserProfile(
            nombre="Miguel", sexo="M", altura_cm=176.0, fecha_nacimiento=date(2002, 11, 28)
        )
        session.add(usuario)
        session.flush()
        session.add(
            GarminCredentials(
                user_id=usuario.id,
                token_store_dir="/data/garmin-tokens/pulse-user-1",
                activo=True,
                historial_sincronizado_desde=None,
            )
        )
        session.commit()
        fake_api = _fake_api_sin_datos()

        resultado = deepen_history_for_all_users(session, api_factory=_api_factory(fake_api))

        assert resultado.usuarios_avanzados == 0
        assert resultado.usuarios_completos == 0
        fake_api.login.assert_not_called()

    def test_un_fallo_de_un_usuario_no_impide_avanzar_a_los_demas(self, session):
        cred_falla = _usuario_con_credenciales(session, frontera=date(2026, 6, 1))
        cred_ok = _usuario_con_credenciales(session, frontera=date(2026, 6, 1))

        fake_api_falla = MagicMock()
        fake_api_falla.login.side_effect = Exception("Garmin caído")
        fake_api_ok = _fake_api_sin_datos()

        llamadas = {"n": 0}

        def api_factory(*args, **kwargs):
            llamadas["n"] += 1
            return fake_api_falla if llamadas["n"] == 1 else fake_api_ok

        resultado = deepen_history_for_all_users(
            session, hoy=date(2026, 9, 1), dias_por_pasada=30, api_factory=api_factory
        )

        assert resultado.usuarios_avanzados == 1
        assert resultado.usuarios_fallidos == 1
        session.refresh(cred_falla)
        session.refresh(cred_ok)
        assert cred_falla.historial_sincronizado_desde == date(2026, 6, 1)  # sin cambios
        assert cred_ok.historial_sincronizado_desde == date(2026, 5, 2)
