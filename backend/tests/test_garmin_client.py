"""Tests para garmin_sync.client — TDD: escritos antes que la implementación.

Sin red real ni credenciales: la librería `garminconnect` se inyecta como
una factory reemplazable (`api_factory`), y en los tests se sustituye por
un doble de prueba (Mock/Fake). Esto cumple la arquitectura de sync
documentada en docs/00-research/03-garmin-integracion.md:

- Reutilizar SIEMPRE el token cacheado, NUNCA relogin agresivo.
- Backoff/propagación clara ante 429/rate-limit, sin reintentos ciegos.
- Cada campo de recuperación (HRV, sleep, body battery, training
  readiness) se obtiene con su propia llamada — un fallo en una no debe
  tumbar las demás (Garmin entrega payloads separados por tipo de dato).
"""
from unittest.mock import MagicMock

import pytest

from garmin_sync.client import (
    GarminAuthError,
    GarminClient,
    GarminRateLimitedError,
)


def _fake_api_factory(fake_api):
    """Factory que siempre devuelve el mismo doble de prueba, imitando la
    firma real de garminconnect.Garmin(email, password)."""
    return lambda *args, **kwargs: fake_api


def _fake_api_factory_que_registra_kwargs(fake_api, llamadas: dict):
    """Variante que además registra los kwargs de la última llamada, para
    poder comprobar qué le pasa GarminClient a la factory (p.ej.
    `prompt_mfa`) sin depender de la firma interna real de
    garminconnect.Garmin."""

    def factory(*args, **kwargs):
        llamadas["kwargs"] = kwargs
        return fake_api

    return factory


class TestLogin:
    def test_login_exitoso_devuelve_la_api_autenticada(self):
        fake_api = MagicMock()
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        client.login()
        fake_api.login.assert_called_once_with("C:/fake/.garminconnect")

    def test_login_no_reintenta_agresivamente_en_caso_de_error(self):
        # Política explícita: un único intento; nunca un bucle de reintento
        # de login (causa raíz documentada de bloqueos de cuenta de 48-72h).
        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("boom")
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        with pytest.raises(GarminAuthError):
            client.login()
        assert fake_api.login.call_count == 1

    def test_login_detecta_rate_limit_y_lo_distingue_de_otros_errores(self):
        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("429 Too Many Requests")
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        with pytest.raises(GarminRateLimitedError):
            client.login()

    def test_login_detecta_bloqueo_403_como_rate_limit(self):
        # Bloqueo de Cloudflare (fingerprint TLS), distinto de 429 pero
        # con la misma respuesta correcta: backoff, no relogin agresivo.
        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("403 Forbidden")
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        with pytest.raises(GarminRateLimitedError):
            client.login()

    def test_login_nunca_expone_la_contrasena_en_el_mensaje_de_error(self):
        # LOW-1 de code-review de seguridad: defensa en profundidad -
        # si el mensaje de error de la librería externa incluyera la
        # contraseña por cualquier motivo, nunca debe propagarse tal
        # cual en la excepción que ve el resto del sistema (y que el
        # script CLI imprime en pantalla).
        fake_api = MagicMock()
        fake_api.login.side_effect = Exception("login failed for password=hunter2")
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            email="atleta@example.com",
            password="hunter2",
            api_factory=_fake_api_factory(fake_api),
        )
        with pytest.raises(GarminAuthError) as excinfo:
            client.login()
        assert "hunter2" not in str(excinfo.value)

    def test_login_pasa_el_prompt_mfa_a_la_api_factory_si_se_proporciona(self):
        # LOW-2 de code-review: cuentas reales con verificación en dos
        # pasos necesitan que garminconnect reciba un callback
        # `prompt_mfa` para poder completar el login en una sola
        # llamada - sin esto, el emparejamiento fallaría a la primera
        # para cualquier usuario con MFA activado.
        fake_api = MagicMock()
        llamadas: dict = {}
        prompt = lambda: "123456"  # noqa: E731 - callback trivial de test
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory_que_registra_kwargs(fake_api, llamadas),
            mfa_code_prompt=prompt,
        )
        client.login()
        assert llamadas["kwargs"].get("prompt_mfa") is prompt

    def test_login_sin_prompt_mfa_no_lo_pasa_a_la_api_factory(self):
        fake_api = MagicMock()
        llamadas: dict = {}
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory_que_registra_kwargs(fake_api, llamadas),
        )
        client.login()
        assert "prompt_mfa" not in llamadas["kwargs"]

    def test_operar_sin_login_previo_lanza_runtime_error(self):
        fake_api = MagicMock()
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        with pytest.raises(RuntimeError):
            client.get_daily_recovery_raw("2026-08-02")


class TestGetDailyRecoveryRaw:
    def _client_logueado(self, fake_api):
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        client.login()
        return client

    def test_combina_los_cuatro_campos_de_recuperacion(self):
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 65, "status": "BALANCED"}}
        fake_api.get_training_readiness.return_value = [{"level": "HIGH"}]
        fake_api.get_body_battery.return_value = [{"charged": 80, "drained": 10}]
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 85}}}}
        fake_api.get_stress_data.return_value = {"avgStressLevel": 25}
        fake_api.get_rhr_day.return_value = {
            "allMetrics": {"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [{"value": 54.0}]}}
        }
        fake_api.get_max_metrics.return_value = [{"generic": {"vo2MaxPreciseValue": 47.5}}]

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert raw["hrv_today"] == 65
        assert raw["hrv_status"] == "BALANCED"
        assert raw["training_readiness"] == "high"
        assert raw["body_battery_am"] == 80
        assert raw["sleep_score"] == 85
        assert raw["stress_avg"] == 25
        assert raw["resting_hr"] == 54
        assert raw["vo2max"] == 47.5
        fake_api.get_hrv_data.assert_called_once_with("2026-08-02")

    def test_un_campo_fallido_no_tumba_a_los_demas(self):
        # Garmin entrega payloads independientes por tipo de dato: un
        # fallo puntual en uno no debe impedir obtener el resto.
        fake_api = MagicMock()
        fake_api.get_hrv_data.side_effect = Exception("temporalmente caído")
        fake_api.get_training_readiness.return_value = [{"level": "MODERATE"}]
        fake_api.get_body_battery.return_value = [{"charged": 55, "drained": 5}]
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 70}}}}
        fake_api.get_stress_data.side_effect = Exception("temporalmente caído")
        fake_api.get_rhr_day.return_value = {
            "allMetrics": {"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [{"value": 60.0}]}}
        }
        fake_api.get_max_metrics.return_value = []

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert raw["hrv_today"] is None
        assert raw["hrv_status"] is None
        assert raw["training_readiness"] == "moderate"
        assert raw["body_battery_am"] == 55
        assert raw["sleep_score"] == 70
        assert raw["stress_avg"] is None
        assert raw["resting_hr"] == 60
        assert raw["vo2max"] is None

    def test_payload_vacio_o_inesperado_da_none_en_vez_de_lanzar(self):
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {}
        fake_api.get_training_readiness.return_value = []
        fake_api.get_body_battery.return_value = None
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {}}
        fake_api.get_stress_data.return_value = {}
        fake_api.get_rhr_day.return_value = {"allMetrics": {"metricsMap": {}}}
        fake_api.get_max_metrics.return_value = None

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert raw["hrv_today"] is None
        assert raw["hrv_status"] is None
        assert raw["training_readiness"] is None
        assert raw["body_battery_am"] is None
        assert raw["sleep_score"] is None
        assert raw["stress_avg"] is None
        assert raw["resting_hr"] is None
        assert raw["vo2max"] is None

    def test_conserva_el_payload_crudo_para_auditoria_y_reprocesado(self):
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 60}}
        fake_api.get_training_readiness.return_value = [{"level": "LOW"}]
        fake_api.get_body_battery.return_value = [{"charged": 40, "drained": 20}]
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 55}}}}
        fake_api.get_stress_data.return_value = {"avgStressLevel": 30}
        fake_api.get_rhr_day.return_value = {}
        fake_api.get_max_metrics.return_value = []

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert "raw_json" in raw
        assert raw["raw_json"]["hrv"] == {"hrvSummary": {"lastNightAvg": 60}}
        assert raw["raw_json"]["stress"] == {"avgStressLevel": 30}
        assert raw["raw_json"]["rhr"] == {}
        assert raw["raw_json"]["max_metrics"] == []

    def test_rechaza_fecha_con_formato_invalido(self):
        fake_api = MagicMock()
        client = self._client_logueado(fake_api)
        with pytest.raises(ValueError):
            client.get_daily_recovery_raw("02-08-2026")
        with pytest.raises(ValueError):
            client.get_daily_recovery_raw("no-es-una-fecha")
        # No debe haber llegado a llamar a la API con una fecha inválida.
        fake_api.get_hrv_data.assert_not_called()

    def test_resting_hr_cero_o_negativo_se_trata_como_ausente(self):
        # No se pudo confirmar contra un payload real si Garmin usa un
        # centinela negativo aquí (como sí confirmado en stress) - por
        # prudencia se descarta igual, un pulso en reposo real nunca es
        # <=0 (ver docstring de _extraer_resting_hr).
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {}
        fake_api.get_training_readiness.return_value = []
        fake_api.get_body_battery.return_value = None
        fake_api.get_sleep_data.return_value = {}
        fake_api.get_stress_data.return_value = {}
        fake_api.get_rhr_day.return_value = {
            "allMetrics": {"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [{"value": 0}]}}
        }
        fake_api.get_max_metrics.return_value = []

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert raw["resting_hr"] is None


class TestGetActivitiesRaw:
    """`get_activities_by_date` de python-garminconnect (ver
    00-research/03-garmin-integracion.md) - a diferencia de
    get_daily_recovery_raw (4 llamadas independientes de un solo día),
    esta es UNA sola llamada que devuelve la lista cruda de actividades
    en el rango - se devuelve tal cual, sin normalizar aquí (eso es
    responsabilidad de garmin_sync.activity_mapper, para mantener el
    cliente como un wrapper fino sobre la API externa)."""

    def _client_logueado(self, fake_api):
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        client.login()
        return client

    def test_devuelve_la_lista_cruda_de_actividades_del_rango(self):
        fake_api = MagicMock()
        fake_api.get_activities_by_date.return_value = [
            {"activityId": 111, "activityType": {"typeKey": "running"}}
        ]
        client = self._client_logueado(fake_api)

        actividades = client.get_activities_raw("2026-08-01", "2026-08-04")

        assert actividades == [{"activityId": 111, "activityType": {"typeKey": "running"}}]
        fake_api.get_activities_by_date.assert_called_once_with("2026-08-01", "2026-08-04")

    def test_payload_none_devuelve_lista_vacia_en_vez_de_lanzar(self):
        # "unknown is not zero" en su variante de colección: sin
        # actividades ese día no es un error, es una lista vacía.
        fake_api = MagicMock()
        fake_api.get_activities_by_date.return_value = None
        client = self._client_logueado(fake_api)

        assert client.get_activities_raw("2026-08-01", "2026-08-04") == []

    def test_operar_sin_login_previo_lanza_runtime_error(self):
        fake_api = MagicMock()
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        with pytest.raises(RuntimeError):
            client.get_activities_raw("2026-08-01", "2026-08-04")

    def test_rechaza_fechas_con_formato_invalido(self):
        fake_api = MagicMock()
        client = self._client_logueado(fake_api)
        with pytest.raises(ValueError):
            client.get_activities_raw("01-08-2026", "2026-08-04")
        with pytest.raises(ValueError):
            client.get_activities_raw("2026-08-01", "no-es-una-fecha")
        fake_api.get_activities_by_date.assert_not_called()
