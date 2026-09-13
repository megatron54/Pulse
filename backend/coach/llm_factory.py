"""Fábrica única del cliente LLM de la Capa 3, para que cada router que
la use (`session.py`, `garmin.py`, futuros) no reimplemente la misma
lógica de selección de proveedor vía variables de entorno.

Orden de preferencia (todas opcionales - "la IA es opcional y no
autoritativa", ver docs/00-research/07-arquitectura-coach-ia.md; si
ninguna está configurada, la Capa 3 cae a su plantilla determinista sin
que ningún endpoint falle):
1. `COACH_LLM_PROVIDER=ollama` u `OLLAMA_HOST` configurado - local,
   gratis, sin cuota, sin enviar datos de salud a un tercero. Proveedor
   preferido (ver nota de deprecación en `coach/gemini_client.py`).
2. `GEMINI_API_KEY` configurada - API gratuita externa, se mantiene por
   compatibilidad con instalaciones existentes.
3. Ninguna configurada -> `None` (plantilla determinista).
"""
from __future__ import annotations

import os

from coach.gemini_client import build_gemini_client_if_configured
from coach.llm_client import LlmClient
from coach.ollama_client import OllamaClient


def build_default_llm_client() -> LlmClient | None:
    proveedor = os.environ.get("COACH_LLM_PROVIDER", "").strip().lower()
    ollama_host = os.environ.get("OLLAMA_HOST")

    if proveedor == "ollama" or ollama_host:
        return OllamaClient(
            host=ollama_host or "http://localhost:11434",
            model_name=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        )

    return build_gemini_client_if_configured()
