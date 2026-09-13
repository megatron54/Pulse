"""Tests para coach.ollama_client — TDD.

Sin red real: `requests.post` se inyecta como dependencia reemplazable,
mismo patrón que garmin_sync.client (GarminClient con api_factory) y
coach.gemini_client (GeminiClient con model_factory)."""
from unittest.mock import MagicMock

import pytest

from coach.ollama_client import OllamaClient, OllamaError


def _fake_post(fake_response):
    return MagicMock(return_value=fake_response)


class TestOllamaClientGenerate:
    def test_generate_devuelve_el_texto_de_la_respuesta(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {"response": "Hoy toca volumen reducido."}
        post = _fake_post(fake_response)

        client = OllamaClient(host="http://localhost:11434", model_name="llama3.1", post=post)
        texto = client.generate("explica esta decision")

        assert texto == "Hoy toca volumen reducido."
        post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.1", "prompt": "explica esta decision", "stream": False},
            timeout=60,
        )

    def test_normaliza_una_barra_final_en_el_host(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {"response": "ok"}
        post = _fake_post(fake_response)

        client = OllamaClient(host="http://localhost:11434/", post=post)
        client.generate("prompt")

        assert post.call_args[0][0] == "http://localhost:11434/api/generate"

    def test_generate_propaga_error_de_red_como_ollamaerror(self):
        post = MagicMock(side_effect=Exception("connection refused"))
        client = OllamaClient(post=post)

        with pytest.raises(OllamaError):
            client.generate("prompt")

    def test_generate_propaga_status_no_2xx_como_ollamaerror(self):
        fake_response = MagicMock()
        fake_response.raise_for_status.side_effect = Exception("404 model not found")
        post = _fake_post(fake_response)
        client = OllamaClient(post=post)

        with pytest.raises(OllamaError):
            client.generate("prompt")

    def test_generate_rechaza_respuesta_sin_campo_response(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {"error": "model not found"}
        post = _fake_post(fake_response)
        client = OllamaClient(post=post)

        with pytest.raises(OllamaError):
            client.generate("prompt")

    def test_host_vacio_lanza_valueerror(self):
        with pytest.raises(ValueError):
            OllamaClient(host="")
