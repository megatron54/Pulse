"""Interfaz genérica de la Capa 3 (conversacional) de Pulse - agnóstica
del proveedor real (Ollama local, Gemini, o cualquier otro).

Toda la Capa 3 (`narrative_service`, `health_narrative_service`,
`sport_narrative_service`) depende SOLO de `LlmClient`/`LlmError`, nunca
de un cliente concreto - así un cambio de proveedor (ej. `GeminiClient`
-> `OllamaClient`) no toca ninguna lógica de negocio, solo la fábrica en
`coach.llm_factory`.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


class LlmError(Exception):
    """Fallo al generar texto con un proveedor de LLM (red, cuota,
    modelo no disponible, respuesta con forma inesperada). La capa
    llamante NUNCA debe dejar que esto rompa el flujo del usuario - ver
    coach.narrative_service, que hace fallback a una plantilla
    determinista ante cualquier LlmError."""


@runtime_checkable
class LlmClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Genera texto a partir de `prompt`. Debe lanzar `LlmError` (o
        una subclase) ante cualquier fallo, nunca una excepción cruda
        del SDK/HTTP subyacente."""
        ...
