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
        fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 65}}
        fake_api.get_training_readiness.return_value = [{"level": "HIGH"}]
        fake_api.get_body_battery.return_value = [{"charged": 80, "drained": 10}]
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 85}}}}

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert raw["hrv_today"] == 65
        assert raw["training_readiness"] == "high"
        assert raw["body_battery_am"] == 80
        assert raw["sleep_score"] == 85
        fake_api.get_hrv_data.assert_called_once_with("2026-08-02")

    def test_un_campo_fallido_no_tumba_a_los_demas(self):
        # Garmin entrega payloads independientes por tipo de dato: un
        # fallo puntual en uno no debe impedir obtener el resto.
        fake_api = MagicMock()
        fake_api.get_hrv_data.side_effect = Exception("temporalmente caído")
        fake_api.get_training_readiness.return_value = [{"level": "MODERATE"}]
        fake_api.get_body_battery.return_value = [{"charged": 55, "drained": 5}]
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 70}}}}

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert raw["hrv_today"] is None
        assert raw["training_readiness"] == "moderate"
        assert raw["body_battery_am"] == 55
        assert raw["sleep_score"] == 70

    def test_payload_vacio_o_inesperado_da_none_en_vez_de_lanzar(self):
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {}
        fake_api.get_training_readiness.return_value = []
        fake_api.get_body_battery.return_value = None
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {}}

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert raw["hrv_today"] is None
        assert raw["training_readiness"] is None
        assert raw["body_battery_am"] is None
        assert raw["sleep_score"] is None

    def test_conserva_el_payload_crudo_para_auditoria_y_reprocesado(self):
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 60}}
        fake_api.get_training_readiness.return_value = [{"level": "LOW"}]
        fake_api.get_body_battery.return_value = [{"charged": 40, "drained": 20}]
        fake_api.get_sleep_data.return_value = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 55}}}}

        client = self._client_logueado(fake_api)
        raw = client.get_daily_recovery_raw("2026-08-02")

        assert "raw_json" in raw
        assert raw["raw_json"]["hrv"] == {"hrvSummary": {"lastNightAvg": 60}}

    def test_rechaza_fecha_con_formato_invalido(self):
        fake_api = MagicMock()
        client = self._client_logueado(fake_api)
        with pytest.raises(ValueError):
            client.get_daily_recovery_raw("02-08-2026")
        with pytest.raises(ValueError):
            client.get_daily_recovery_raw("no-es-una-fecha")
        # No debe haber llegado a llamar a la API con una fecha inválida.
        fake_api.get_hrv_data.assert_not_called()
