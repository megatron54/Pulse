"""Capa 3 (conversacional): redacta la explicación de una decisión YA
tomada por el motor de reglas. Nunca calcula ni decide nada.

Principios (ver docs/00-research/07-arquitectura-coach-ia.md):
- "La IA es opcional y no autoritativa": el producto debe funcionar sin
  LLM - por eso existe siempre una plantilla determinista de respaldo,
  usada si no hay `gemini_client`, si Gemini falla, o si su respuesta no
  pasa la validación post-generación.
- "Si no se puede auditar, no se puede confiar": el resultado indica
  siempre su `source` ("llm" | "template") para que quede claro de dónde
  vino el texto mostrado al usuario.
"""
from __future__ import annotations

from dataclasses import dataclass

from coach.gemini_client import GeminiClient, GeminiError
from engine.periodization import ReadinessLevel, SessionRecommendation, SessionType

_MAX_LONGITUD_TEXTO_LLM = 800

_NOMBRES_LEGIBLES_SESSION = {
    SessionType.REST: "descanso completo",
    SessionType.ACTIVE_RECOVERY: "recuperación activa",
    SessionType.STRENGTH_HEAVY: "fuerza pesada",
    SessionType.STRENGTH_HYPERTROPHY: "hipertrofia",
    SessionType.ENDURANCE_INTERVALS: "intervalos de resistencia",
    SessionType.ENDURANCE_LONG: "resistencia larga",
    SessionType.MARTIAL_ARTS_TECHNICAL: "artes marciales (técnica)",
    SessionType.MARTIAL_ARTS_SPARRING: "artes marciales (sparring)",
}

_NOMBRES_LEGIBLES_READINESS = {
    ReadinessLevel.RED: "tu recuperación está baja",
    ReadinessLevel.YELLOW: "tu recuperación es moderada",
    ReadinessLevel.GREEN: "tu recuperación es buena",
}

# Frases que contradicen una decisión de ENTRENAR (session_type distinto
# de REST/ACTIVE_RECOVERY). Lista no exhaustiva a propósito - es una
# defensa barata contra el caso más peligroso (el LLM sugiriendo
# descansar cuando el motor de reglas decidió entrenar), no un parser
# semántico completo.
_FRASES_CONTRADICTORIAS_CON_ENTRENAR = (
    "descanso total",
    "no entrenes",
    "haz reposo",
    "descansa hoy",
    "mejor no entrenar",
)


@dataclass(frozen=True)
class NarrativeResult:
    text: str
    source: str  # "llm" | "template"


def _plantilla_determinista(
    recomendacion: SessionRecommendation, readiness: ReadinessLevel
) -> str:
    nombre_sesion = _NOMBRES_LEGIBLES_SESSION.get(
        recomendacion.session_type, recomendacion.session_type.value
    )
    motivo_readiness = _NOMBRES_LEGIBLES_READINESS.get(readiness, readiness.value)

    if recomendacion.volume_pct == 0:
        return f"Hoy toca {nombre_sesion} porque {motivo_readiness}."

    texto = f"Hoy toca {nombre_sesion} al {recomendacion.volume_pct}% porque {motivo_readiness}."
    if recomendacion.intensity_rpe_cap is not None:
        texto += f" Mantén el RPE por debajo de {recomendacion.intensity_rpe_cap}."
    return texto


def _construir_prompt(recomendacion: SessionRecommendation, readiness: ReadinessLevel) -> str:
    """Prompt corto y acotado: el LLM recibe la decisión ya tomada
    (tipada) y solo debe redactar 1-2 frases explicándola en lenguaje
    natural - nunca se le pide que decida nada."""
    return (
        "Eres el coach de una app de entrenamiento personal. "
        "El motor de reglas ya decidió la sesión de hoy; tu única tarea es "
        "explicarla en 1-2 frases, en español, tono cercano y directo. "
        "No sugieras cambiar la decisión.\n\n"
        f"Sesión decidida: {recomendacion.session_type.value}\n"
        f"Volumen: {recomendacion.volume_pct}%\n"
        f"Cap de RPE: {recomendacion.intensity_rpe_cap}\n"
        f"Nivel de recuperación (readiness): {readiness.value}\n"
    )


def _es_texto_llm_valido(texto: str | None) -> bool:
    """Validación de FORMA: no vacío, longitud razonable."""
    if texto is None:
        return False
    texto_limpio = texto.strip()
    if not texto_limpio:
        return False
    if len(texto_limpio) > _MAX_LONGITUD_TEXTO_LLM:
        return False
    return True


def _es_texto_llm_coherente(texto: str, recomendacion: SessionRecommendation) -> bool:
    """Validación de CONTENIDO contra el dato estructurado (principio
    "el texto no debe contradecir el número/decisión calculada", ver
    docs/00-research/07-arquitectura-coach-ia.md). Defensa barata, no
    un parser semántico completo: si la decisión real es entrenar
    (session_type distinto de REST/ACTIVE_RECOVERY), el texto no debe
    contener frases que instruyan lo contrario (ej. "descanso total").
    """
    if recomendacion.session_type in (SessionType.REST, SessionType.ACTIVE_RECOVERY):
        return True
    texto_lower = texto.lower()
    return not any(frase in texto_lower for frase in _FRASES_CONTRADICTORIAS_CON_ENTRENAR)


def generate_session_narrative(
    recomendacion: SessionRecommendation,
    readiness: ReadinessLevel,
    gemini_client: GeminiClient | None,
) -> NarrativeResult:
    """Genera la explicación en lenguaje natural de `recomendacion`.

    Intenta usar Gemini si se proporciona `gemini_client`; ante
    cualquier fallo (GeminiError) o respuesta que no pase la validación
    post-generación (vacía, o desproporcionadamente larga), cae a la
    plantilla determinista - el usuario SIEMPRE recibe una explicación,
    nunca un error de la capa conversacional.
    """
    if gemini_client is not None:
        try:
            texto_llm = gemini_client.generate(_construir_prompt(recomendacion, readiness))
        except GeminiError:
            texto_llm = None

        if _es_texto_llm_valido(texto_llm) and _es_texto_llm_coherente(texto_llm, recomendacion):
            return NarrativeResult(text=texto_llm.strip(), source="llm")

    return NarrativeResult(
        text=_plantilla_determinista(recomendacion, readiness), source="template"
    )
