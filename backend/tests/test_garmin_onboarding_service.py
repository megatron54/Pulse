"""Épica de conexión Garmin desde la propia app (petición explícita del
usuario: "no quiero tokens míos hardcodeados... y si otra persona
quiere usar la app, debería poder configurárselo para sí mismo con su
propia cuenta"). Sustituye al script manual `garmin_pair.py` como vía
de alta de un usuario nuevo: la contraseña solo vive en memoria durante
esta llamada, nunca se persiste (mismo principio que `garmin_pair.py`
y `GarminClient.login`)."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminCredentials, UserProfile
from services.garmin_onboarding_service import (
    GarminPerfilIncompletoError,
    connect_new_user_via_garmin,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _api_factory(fake_api):
    return lambda *args, **kwargs: fake_api


class TestConnectNewUserViaGarmin:
    def test_crea_el_usuario_con_los_datos_de_garmin_sin_pedir_nada_a_mano(self, session):
        fake_api = MagicMock()
        fake_api.get_full_name.return_value = "Miguel"
        fake_api.get_user_profile.return_value = {
            "userData": {"gender": "MALE", "weight": 77100.0, "height": 176.0, "birthDate": "2002-11-28"}
        }

        usuario = connect_new_user_via_garmin(
            session,
            email="miguel@example.com",
            password="hunter2",
            token_store_dir="/data/garmin-tokens/pulse-user-1",
            api_factory=_api_factory(fake_api),
        )

        assert usuario.nombre == "Miguel"
        assert usuario.sexo == "M"
        assert usuario.altura_cm == 176.0
        assert usuario.fecha_nacimiento == date(2002, 11, 28)
        # Credenciales creadas y activas - listas para que el scheduler
        # las reutilice sin volver a pedir contraseña.
        cred = session.query(GarminCredentials).filter_by(user_id=usuario.id).one()
        assert cred.activo is True
        assert cred.token_store_dir == "/data/garmin-tokens/pulse-user-1"

    def test_la_contrasena_nunca_se_persiste_en_ningun_campo(self, session):
        fake_api = MagicMock()
        fake_api.get_full_name.return_value = "Miguel"
        fake_api.get_user_profile.return_value = {
            "userData": {"gender": "MALE", "weight": 77000.0, "height": 176.0, "birthDate": "2002-11-28"}
        }

        connect_new_user_via_garmin(
            session,
            email="miguel@example.com",
            password="el-secreto-de-verdad",
            token_store_dir="/data/garmin-tokens/pulse-user-1",
            api_factory=_api_factory(fake_api),
        )

        usuario = session.query(UserProfile).one()
        cred = session.query(GarminCredentials).one()
        assert "el-secreto-de-verdad" not in str(vars(usuario))
        assert "el-secreto-de-verdad" not in str(vars(cred))

    def test_campo_faltante_en_garmin_lanza_error_listando_solo_lo_que_falta(self, session):
        # "pedir solo lo que falte, nunca lo que Garmin ya dio" -
        # decisión explícita del usuario.
        fake_api = MagicMock()
        fake_api.get_full_name.return_value = "Miguel"
        fake_api.get_user_profile.return_value = {
            "userData": {"gender": None, "weight": 77000.0, "height": None, "birthDate": "2002-11-28"}
        }

        with pytest.raises(GarminPerfilIncompletoError) as excinfo:
            connect_new_user_via_garmin(
                session,
                email="miguel@example.com",
                password="hunter2",
                token_store_dir="/data/garmin-tokens/pulse-user-1",
                api_factory=_api_factory(fake_api),
            )

        assert set(excinfo.value.campos_faltantes) == {"sexo", "altura_cm"}
        # Nunca se crea un usuario a medias.
        assert session.query(UserProfile).count() == 0

    def test_overrides_rellenan_solo_los_campos_que_garmin_no_dio(self, session):
        fake_api = MagicMock()
        fake_api.get_full_name.return_value = "Miguel"
        fake_api.get_user_profile.return_value = {
            "userData": {"gender": None, "weight": 77000.0, "height": 176.0, "birthDate": "2002-11-28"}
        }

        usuario = connect_new_user_via_garmin(
            session,
            email="miguel@example.com",
            password="hunter2",
            token_store_dir="/data/garmin-tokens/pulse-user-1",
            overrides={"sexo": "M"},
            api_factory=_api_factory(fake_api),
        )

        assert usuario.sexo == "M"
        assert usuario.altura_cm == 176.0  # de Garmin, no sobreescrito

    def test_no_crea_credenciales_si_el_login_falla(self, session):
        from garmin_sync.client import GarminAuthError

        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("401 invalid credentials")

        with pytest.raises(GarminAuthError):
            connect_new_user_via_garmin(
                session,
                email="miguel@example.com",
                password="contrasena-incorrecta",
                token_store_dir="/data/garmin-tokens/pulse-user-1",
                api_factory=_api_factory(fake_api),
            )

        assert session.query(UserProfile).count() == 0
        assert session.query(GarminCredentials).count() == 0

    def test_dispara_el_backfill_historico_reutilizando_la_sesion_ya_logueada(self, session):
        # Hallazgo BLOQUEANTE de code-review: el backfill estaba
        # construido y testeado pero nunca se llamaba desde el flujo de
        # conexión - petición explícita del usuario: "debería
        # extraerse todo el histórico de Garmin, no solo lo de los
        # últimos 5 min".
        fake_api = MagicMock()
        fake_api.get_full_name.return_value = "Miguel"
        fake_api.get_user_profile.return_value = {
            "userData": {"gender": "MALE", "weight": 77000.0, "height": 176.0, "birthDate": "2002-11-28"}
        }
        fake_api.get_activities_by_date.return_value = []
        fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 65}}
        fake_api.get_training_readiness.return_value = None
        fake_api.get_body_battery.return_value = None
        fake_api.get_sleep_data.return_value = None
        fake_api.get_stress_data.return_value = None
        fake_api.get_rhr_day.return_value = None
        fake_api.get_max_metrics.return_value = None

        connect_new_user_via_garmin(
            session,
            email="miguel@example.com",
            password="hunter2",
            token_store_dir="/data/garmin-tokens/pulse-user-1",
            api_factory=_api_factory(fake_api),
            backfill_dias=3,
            hoy=date(2026, 8, 10),
        )

        # 3 días (08-08, 09-08, 10-08) piden actividades EN UNA sola
        # llamada de rango, y recovery día a día (mismo login
        # reutilizado, sin volver a pedir contraseña).
        fake_api.get_activities_by_date.assert_called_once_with("2026-08-08", "2026-08-10")
        assert fake_api.get_hrv_data.call_count == 3
        fake_api.login.assert_called_once()  # nunca un segundo login para el backfill

    def test_el_backfill_nunca_impide_devolver_el_usuario_ya_creado(self, session):
        # Aunque el backfill falle por completo (Garmin caído tras el
        # login inicial), el usuario ya está creado y debe devolverse -
        # la conexión en sí ya tuvo éxito.
        fake_api = MagicMock()
        fake_api.get_full_name.return_value = "Miguel"
        fake_api.get_user_profile.return_value = {
            "userData": {"gender": "MALE", "weight": 77000.0, "height": 176.0, "birthDate": "2002-11-28"}
        }
        fake_api.get_activities_by_date.side_effect = Exception("Garmin caído")
        fake_api.get_hrv_data.side_effect = Exception("Garmin caído")

        usuario = connect_new_user_via_garmin(
            session,
            email="miguel@example.com",
            password="hunter2",
            token_store_dir="/data/garmin-tokens/pulse-user-1",
            api_factory=_api_factory(fake_api),
            backfill_dias=2,
        )

        assert usuario.nombre == "Miguel"
        assert session.query(UserProfile).count() == 1
