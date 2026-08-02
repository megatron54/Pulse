"""Tests para coach.gemini_client — TDD.

Sin red real ni API key: el SDK de Gemini se inyecta como un
`model_factory` reemplazable, mismo patrón que garmin_sync.client
(GarminClient con api_factory), ya validado en test_garmin_client.py.
"""
from unittest.mock import MagicMock

import pytest

from coach.gemini_client import GeminiClient, GeminiError


def _fake_model_factory(fake_model):
    return lambda *args, **kwargs: fake_model


class TestGeminiClientGenerate:
    def test_generate_devuelve_el_texto_de_la_respuesta(self):
        fake_response = MagicMock()
        fake_response.text = "Hoy toca volumen reducido porque tu HRV bajó."
        fake_model = MagicMock()
        fake_model.generate_content.return_value = fake_response

        client = GeminiClient(api_key="fake-key", model_factory=_fake_model_factory(fake_model))
        texto = client.generate("explica esta decision")

        assert texto == "Hoy toca volumen reducido porque tu HRV bajó."
        fake_model.generate_content.assert_called_once_with("explica esta decision")

    def test_generate_propaga_error_como_geminierror(self):
        fake_model = MagicMock()
        fake_model.generate_content.side_effect = Exception("quota exceeded")
        client = GeminiClient(api_key="fake-key", model_factory=_fake_model_factory(fake_model))

        with pytest.raises(GeminiError):
            client.generate("prompt")

    def test_generate_rechaza_respuesta_sin_atributo_text(self):
        fake_model = MagicMock()
        fake_model.generate_content.return_value = object()  # sin .text
        client = GeminiClient(api_key="fake-key", model_factory=_fake_model_factory(fake_model))

        with pytest.raises(GeminiError):
            client.generate("prompt")

    def test_generate_rechaza_respuesta_con_text_none(self):
        # Caso real del SDK: respuesta bloqueada por filtros de seguridad
        # de Gemini devuelve un objeto con .text = None.
        fake_response = MagicMock()
        fake_response.text = None
        fake_model = MagicMock()
        fake_model.generate_content.return_value = fake_response
        client = GeminiClient(api_key="fake-key", model_factory=_fake_model_factory(fake_model))

        with pytest.raises(GeminiError):
            client.generate("prompt")

    def test_rechaza_api_key_vacia(self):
        with pytest.raises(ValueError):
            GeminiClient(api_key="", model_factory=_fake_model_factory(MagicMock()))

    def test_rechaza_api_key_none(self):
        with pytest.raises(ValueError):
            GeminiClient(api_key=None, model_factory=_fake_model_factory(MagicMock()))
