"""Serie de tiempo intradía (petición explícita del usuario: "el ritmo
cardiaco, body battery, etc son valores que cambian cada minuto, quiero
todo ese histórico"). Verificado contra el JSON real de una cuenta
Garmin real (docker exec pulse-scheduler-1, sesión de esta épica):
`get_heart_rates`/`get_body_battery`/`get_stress_data` devuelven un
array `[timestamp_ms, valor]` con un punto cada ~2-3 minutos - TDD."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from garmin_sync.client import GarminClient


def _fake_api_factory(fake_api):
    return lambda *args, **kwargs: fake_api


def _client_logueado(fake_api):
    client = GarminClient(
        token_store_dir="C:/fake/.garminconnect",
        api_factory=_fake_api_factory(fake_api),
    )
    client.login()
    return client


class TestGetIntradaySeriesRaw:
    def test_extrae_la_serie_de_ritmo_cardiaco(self):
        fake_api = MagicMock()
        fake_api.get_heart_rates.return_value = {
            "heartRateValues": [
                [1786226400000, 107],
                [1786226520000, 103],
            ]
        }
        fake_api.get_body_battery.return_value = None
        fake_api.get_stress_data.return_value = None
        client = _client_logueado(fake_api)

        serie = client.get_intraday_series_raw("2026-08-09")

        assert serie["heart_rate"] == [(1786226400000, 107), (1786226520000, 103)]

    def test_extrae_la_serie_de_body_battery_de_la_lista_de_garmin(self):
        # get_body_battery devuelve una LISTA (normalmente de 1 elemento
        # para un solo día), no un dict - forma real verificada.
        fake_api = MagicMock()
        fake_api.get_heart_rates.return_value = None
        fake_api.get_body_battery.return_value = [
            {
                "bodyBatteryValuesArray": [
                    [1786226400000, 9],
                    [1786230000000, 5],
                ]
            }
        ]
        fake_api.get_stress_data.return_value = None
        client = _client_logueado(fake_api)

        serie = client.get_intraday_series_raw("2026-08-09")

        assert serie["body_battery"] == [(1786226400000, 9), (1786230000000, 5)]

    def test_descarta_los_valores_centinela_negativos_de_estres(self):
        # "unknown is not zero": Garmin usa -1/-2 para "sin datos
        # suficientes ese minuto" dentro de stressValuesArray - nunca
        # se persisten como si fueran un valor real de estrés.
        fake_api = MagicMock()
        fake_api.get_heart_rates.return_value = None
        fake_api.get_body_battery.return_value = None
        fake_api.get_stress_data.return_value = {
            "stressValuesArray": [
                [1786226400000, -1],
                [1786226580000, 84],
                [1786226760000, -2],
                [1786226940000, 72],
            ]
        }
        client = _client_logueado(fake_api)

        serie = client.get_intraday_series_raw("2026-08-09")

        assert serie["stress"] == [(1786226580000, 84), (1786226940000, 72)]

    def test_un_campo_fallido_no_tumba_a_los_demas(self):
        fake_api = MagicMock()
        fake_api.get_heart_rates.side_effect = Exception("fallo puntual de Garmin")
        fake_api.get_body_battery.return_value = [
            {"bodyBatteryValuesArray": [[1786226400000, 9]]}
        ]
        fake_api.get_stress_data.return_value = None
        client = _client_logueado(fake_api)

        serie = client.get_intraday_series_raw("2026-08-09")

        assert serie["heart_rate"] == []
        assert serie["body_battery"] == [(1786226400000, 9)]

    def test_payload_vacio_o_ausente_da_lista_vacia_en_vez_de_lanzar(self):
        fake_api = MagicMock()
        fake_api.get_heart_rates.return_value = None
        fake_api.get_body_battery.return_value = []
        fake_api.get_stress_data.return_value = {}
        client = _client_logueado(fake_api)

        serie = client.get_intraday_series_raw("2026-08-09")

        assert serie == {"heart_rate": [], "body_battery": [], "stress": []}

    def test_operar_sin_login_previo_lanza_runtime_error(self):
        fake_api = MagicMock()
        client = GarminClient(
            token_store_dir="C:/fake/.garminconnect",
            api_factory=_fake_api_factory(fake_api),
        )
        with pytest.raises(RuntimeError):
            client.get_intraday_series_raw("2026-08-09")

    def test_rechaza_fecha_con_formato_invalido(self):
        fake_api = MagicMock()
        client = _client_logueado(fake_api)
        with pytest.raises(ValueError):
            client.get_intraday_series_raw("09-08-2026")

    def test_reutiliza_el_payload_ya_pedido_por_get_daily_recovery_raw_del_mismo_dia(self):
        # Hallazgo de code-review: get_daily_recovery_raw y
        # get_intraday_series_raw pedían body_battery/stress DOS veces
        # para el mismo día - la caché por-fecha del cliente evita la
        # llamada de red duplicada (mismo dato, menos riesgo de
        # rate-limit).
        fake_api = MagicMock()
        fake_api.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 65.0}}
        fake_api.get_training_readiness.return_value = [{"level": "HIGH"}]
        fake_api.get_body_battery.return_value = [
            {"charged": 80, "drained": 10, "bodyBatteryValuesArray": [[1786226400000, 50]]}
        ]
        fake_api.get_sleep_data.return_value = {}
        fake_api.get_stress_data.return_value = {"stressValuesArray": [[1786226400000, 40]]}
        fake_api.get_rhr_day.return_value = {}
        fake_api.get_max_metrics.return_value = []
        fake_api.get_heart_rates.return_value = {}
        client = _client_logueado(fake_api)

        client.get_daily_recovery_raw("2026-08-09")
        serie = client.get_intraday_series_raw("2026-08-09")

        fake_api.get_body_battery.assert_called_once()
        fake_api.get_stress_data.assert_called_once()
        assert serie["body_battery"] == [(1786226400000, 50)]
        assert serie["stress"] == [(1786226400000, 40)]

    def test_dias_distintos_no_comparten_cache(self):
        fake_api = MagicMock()
        fake_api.get_body_battery.return_value = []
        fake_api.get_stress_data.return_value = {}
        fake_api.get_heart_rates.return_value = {}
        client = _client_logueado(fake_api)

        client.get_intraday_series_raw("2026-08-09")
        client.get_intraday_series_raw("2026-08-10")

        assert fake_api.get_body_battery.call_count == 2
        assert fake_api.get_stress_data.call_count == 2
