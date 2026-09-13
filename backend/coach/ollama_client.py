"""Cliente de Ollama (servidor LLM local, gratis, sin red externa) para
la Capa 3 (conversacional) de Pulse.

Decisión de stack (reemplaza a `google-generativeai`, cuyo SDK anunció
el fin de soporte - ver `coach/gemini_client.py` y
`02-roadmap/03-vision-produccion.md`): Ollama corre en la propia
máquina/red del usuario, sin cuota ni clave de API, y sin enviar datos
de salud a un tercero - encaja mejor con "la IA es opcional y no
autoritativa" que una API gratuita de un proveedor externo. Se habla
por HTTP puro contra `/api/generate` (`stream=False`), sin SDK
dedicado - un único `requests.post`, mismo patrón de dependencia mínima
que `feelfit_client`.
"""
from __future__ import annotations

from typing import Any, Callable

import requests

from coach.llm_client import LlmError

_DEFAULT_HOST = "http://localhost:11434"
_DEFAULT_MODEL_NAME = "llama3.1"
_DEFAULT_TIMEOUT_SEG = 60


class OllamaError(LlmError):
    """Fallo al generar texto con Ollama (servidor no accesible, modelo
    no descargado, timeout, respuesta con forma inesperada). Subclase
    de `LlmError` - la capa llamante puede capturar `LlmError`
    genéricamente sin conocer el proveedor real."""


def _default_post() -> Callable[..., Any]:
    return requests.post


class OllamaClient:
    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        model_name: str = _DEFAULT_MODEL_NAME,
        timeout_seg: int = _DEFAULT_TIMEOUT_SEG,
        post: Callable[..., Any] | None = None,
    ) -> None:
        if not host:
            raise ValueError("host no puede estar vacío")
        self._host = host.rstrip("/")
        self._model_name = model_name
        self._timeout_seg = timeout_seg
        self._post = post or _default_post()

    def generate(self, prompt: str) -> str:
        """Genera texto a partir de `prompt`. Lanza `OllamaError` ante
        cualquier fallo (servidor caído, timeout, modelo inexistente,
        respuesta sin `response`) - nunca deja pasar una excepción
        cruda de `requests`, para que la capa llamante solo tenga que
        manejar un único tipo de error."""
        try:
            respuesta = self._post(
                f"{self._host}/api/generate",
                json={"model": self._model_name, "prompt": prompt, "stream": False},
                timeout=self._timeout_seg,
            )
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
        except OllamaError:
            raise
        except Exception as exc:
            raise OllamaError(str(exc)) from exc

        texto = cuerpo.get("response")
        if not texto:
            raise OllamaError(f"Respuesta de Ollama sin campo 'response' útil: {cuerpo}")
        return texto
