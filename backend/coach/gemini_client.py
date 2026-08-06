"""Cliente de la API gratuita de Google Gemini para la Capa 3
(conversacional) de Pulse.

Decisión de stack (ver docs/01-arquitectura/02-stack-tecnologico.md):
Google Gemini API (free tier) en vez de GPT-4o-mini/Ollama - coste $0,
suficiente porque esta capa SOLO redacta explicaciones de decisiones ya
tomadas por el motor de reglas (Capa 1), nunca calcula ni decide nada.

Mismo patrón de inyección que garmin_sync.client.GarminClient
(`api_factory`): el SDK real se importa de forma perezosa, sustituible
por un doble de prueba en tests, sin red ni credenciales reales.
"""
from __future__ import annotations

import os
from typing import Any, Callable

_DEFAULT_MODEL_NAME = "gemini-1.5-flash"


class GeminiError(Exception):
    """Fallo al generar contenido con Gemini (red, cuota, respuesta con
    forma inesperada). La capa llamante NUNCA debe dejar que esto rompa
    el flujo del usuario - ver coach.narrative_service, que hace
    fallback a una plantilla determinista ante cualquier GeminiError."""


def _default_model_factory() -> Callable[..., Any]:
    import google.generativeai as genai

    def factory(api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name)

    return factory


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model_name: str = _DEFAULT_MODEL_NAME,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key no puede estar vacía")
        self._model_factory = model_factory or _default_model_factory()
        self._model = self._model_factory(api_key, model_name)

    def generate(self, prompt: str) -> str:
        """Genera texto a partir de `prompt`. Lanza GeminiError ante
        cualquier fallo (red, cuota, respuesta sin `.text`) - nunca deja
        pasar una excepción cruda del SDK, para que la capa llamante
        solo tenga que manejar un único tipo de error."""
        try:
            respuesta = self._model.generate_content(prompt)
            if respuesta.text is None:
                raise GeminiError(
                    "Respuesta de Gemini con text=None (posible bloqueo por filtros de seguridad)"
                )
            return respuesta.text
        except AttributeError as exc:
            raise GeminiError(f"Respuesta de Gemini sin atributo 'text': {exc}") from exc
        except GeminiError:
            raise
        except Exception as exc:
            raise GeminiError(str(exc)) from exc


def build_gemini_client_if_configured() -> GeminiClient | None:
    """La IA es opcional y no autoritativa (ver docs/00-research/
    07-arquitectura-coach-ia.md): si no hay GEMINI_API_KEY configurada,
    la Capa 3 usa su plantilla determinista de respaldo sin que ningún
    endpoint falle ni se degrade la decisión estructurada. Extraído de
    `api/routers/session.py` (Épica H, 02-roadmap/03-vision-produccion.md)
    para que cada router nuevo que use la Capa 3 no reimplemente esta
    misma comprobación de variable de entorno."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return GeminiClient(api_key=api_key)
