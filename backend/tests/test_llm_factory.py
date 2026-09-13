"""Tests para coach.llm_factory — orden de preferencia de proveedor
(Ollama local > Gemini > ninguno), sin red real."""
import pytest

from coach.gemini_client import GeminiClient
from coach.llm_factory import build_default_llm_client
from coach.ollama_client import OllamaClient


@pytest.fixture(autouse=True)
def _limpia_env(monkeypatch):
    monkeypatch.delenv("COACH_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


class TestBuildDefaultLlmClient:
    def test_sin_ninguna_variable_configurada_devuelve_none(self):
        assert build_default_llm_client() is None

    def test_ollama_host_configurado_devuelve_ollamaclient(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://mi-servidor:11434")
        cliente = build_default_llm_client()
        assert isinstance(cliente, OllamaClient)

    def test_coach_llm_provider_ollama_sin_host_usa_localhost(self, monkeypatch):
        monkeypatch.setenv("COACH_LLM_PROVIDER", "ollama")
        cliente = build_default_llm_client()
        assert isinstance(cliente, OllamaClient)

    def test_gemini_api_key_configurada_devuelve_geminiclient(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        cliente = build_default_llm_client()
        assert isinstance(cliente, GeminiClient)

    def test_ollama_tiene_preferencia_sobre_gemini_si_ambas_estan_configuradas(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        cliente = build_default_llm_client()
        assert isinstance(cliente, OllamaClient)
