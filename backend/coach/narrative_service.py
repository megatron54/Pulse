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

import re
from dataclasses import dataclass
from typing import Any

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


# ---------------------------------------------------------------------------
# Épica H del plan de expansión (02-roadmap/03-vision-produccion.md):
# generaliza la Capa 3 a más contextos (salud, por deporte, nutrición)
# SIN reabrir generate_session_narrative (ya probada y en producción) -
# servicio HERMANO con la misma garantía: la decisión (`decision_label`)
# y los datos reales (`datos`) ya vienen calculados por capas
# anteriores, esta función solo redacta.
# ---------------------------------------------------------------------------

_MAX_LONGITUD_TEXTO_CONTEXTO = 500
_PATRON_NUMERO = re.compile(r"-?\d+(?:\.\d+)?")

# Defensa adicional (hallazgo de @code-reviewer sobre la Épica H): el
# regex de dígitos NO detecta un número inventado si el LLM lo escribe
# en palabras ("sesenta" en vez de "60") - un caso plausible en
# redacción en español, y el vector de invención de cifras más
# preocupante de esta barrera. No se intenta parsear/convertir estas
# palabras a un valor (sería un parser de números completo, fuera de
# alcance) - más simple y conservador: si aparece CUALQUIER palabra
# numérica española (de dos en adelante), se rechaza el texto
# directamente (cae a plantilla), sin intentar decidir si esa palabra
# citaba un dato real o no. "uno"/"una" se EXCLUYEN a propósito: son
# artículos indefinidos omnipresentes en español ("una recuperación
# buena") - incluirlos rechazaría casi cualquier texto del LLM,
# inutilizando la ruta LLM por completo. Lista no exhaustiva a
# propósito (mismo criterio que `_FRASES_CONTRADICTORIAS_CON_ENTRENAR`):
# cubre las unidades/decenas/centenas más comunes, no es un diccionario
# numeral completo.
_PALABRAS_NUMERICAS_ES = re.compile(
    r"\b("
    r"cero|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
    r"once|doce|trece|catorce|quince|dieci(?:s[ée]is|siete|ocho|nueve)|"
    r"veinti?(?:un[oa]?|d[oó]s|tr[eé]s|cuatro|cinco|s[eé]is|siete|ocho|nueve)?|"
    r"treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|"
    r"cien(?:to)?s?|mil(?:es)?|mill[oó]n(?:es)?"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ContextNarrativeResult:
    text: str
    source: str  # "llm" | "template"


def _formatear_datos_legibles(datos: dict[str, Any]) -> list[str]:
    """Solo los pares con valor real (nunca None) - "unknown is not
    zero": un dato ausente no aparece en absoluto, nunca como "None" ni
    como 0 inventado."""
    return [
        f"{clave.replace('_', ' ')}: {valor}"
        for clave, valor in datos.items()
        if valor is not None
    ]


def _plantilla_generica_contexto(
    contexto: str, decision_label: str, datos: dict[str, Any]
) -> str:
    partes = _formatear_datos_legibles(datos)
    base = f"Tu estado de {contexto} hoy: {decision_label}."
    if not partes:
        return base
    return f"{base} ({', '.join(partes)})"


def _construir_prompt_contexto(
    contexto: str, decision_label: str, datos: dict[str, Any]
) -> str:
    lineas_datos = "\n".join(f"- {linea}" for linea in _formatear_datos_legibles(datos))
    return (
        "Eres el coach de una app de salud y entrenamiento personal. "
        f"El motor de reglas ya decidió el estado de {contexto}; tu única tarea es "
        "explicarlo en 1-2 frases, en español, tono cercano y directo. "
        "Cita ÚNICAMENTE los datos reales de abajo - nunca inventes ninguna "
        "cifra que no aparezca en esta lista, ni sugieras un estado distinto "
        "al ya decidido.\n\n"
        f"Estado decidido: {decision_label}\n"
        f"Datos reales:\n{lineas_datos if lineas_datos else '(sin datos numéricos disponibles)'}\n"
    )


def _numeros_permitidos(datos: dict[str, Any]) -> set[str]:
    """Todas las representaciones textuales razonables de los valores
    numéricos reales de `datos` - un float que es un entero exacto
    (60.0) debe aceptar tanto "60.0" como "60" (formas típicas en que
    un LLM redondearía al citarlo), sin por ello aceptar un número
    arbitrario que no venga de aquí."""
    permitidos: set[str] = set()
    for valor in datos.values():
        if isinstance(valor, bool) or valor is None:
            continue
        if isinstance(valor, (int, float)):
            permitidos.add(str(valor))
            if isinstance(valor, float) and valor == int(valor):
                permitidos.add(str(int(valor)))
    return permitidos


def _es_texto_llm_coherente_contexto(texto: str, datos: dict[str, Any]) -> bool:
    """Barrera arquitectónica de esta épica: el LLM no puede citar
    ninguna cifra que no venga de `datos` ya calculados. Defensa barata
    por regex (no un parser semántico completo, mismo criterio que
    `_es_texto_llm_coherente` para la narrativa de sesión) - deliberadamente
    estricta: ante la duda, se prefiere caer a la plantilla determinista
    (siempre honesta) antes que arriesgar un número inventado.

    Dos comprobaciones independientes, ambas deben pasar:
    1. Los números en DÍGITOS del texto deben ser subconjunto de los
       valores reales de `datos`.
    2. El texto no debe contener NINGUNA palabra numérica en español
       (ver `_PALABRAS_NUMERICAS_ES`) - un LLM que escriba "sesenta" en
       vez de "60" evadiría por completo la comprobación 1, así que se
       rechaza cualquier redacción en palabras sin excepción (no se
       intenta verificar si esa palabra citaba un dato real)."""
    if _PALABRAS_NUMERICAS_ES.search(texto):
        return False
    numeros_en_texto = set(_PATRON_NUMERO.findall(texto))
    if not numeros_en_texto:
        return True
    return numeros_en_texto.issubset(_numeros_permitidos(datos))


def generate_context_narrative(
    contexto: str,
    decision_label: str,
    datos: dict[str, Any],
    gemini_client: GeminiClient | None,
) -> ContextNarrativeResult:
    """Genera la explicación en lenguaje natural de un estado/decisión
    ya calculado para `contexto` (ej. "salud", "running", "nutrición"),
    citando `datos` reales. Mismo patrón de robustez que
    `generate_session_narrative`: ante cualquier fallo o respuesta que
    no pase la validación (forma + coherencia numérica), cae a la
    plantilla determinista - el usuario SIEMPRE recibe una explicación,
    nunca un error de la capa conversacional."""
    if gemini_client is not None:
        try:
            texto_llm = gemini_client.generate(
                _construir_prompt_contexto(contexto, decision_label, datos)
            )
        except GeminiError:
            texto_llm = None

        if (
            texto_llm is not None
            and _es_texto_llm_valido(texto_llm)
            and len(texto_llm.strip()) <= _MAX_LONGITUD_TEXTO_CONTEXTO
            and _es_texto_llm_coherente_contexto(texto_llm, datos)
        ):
            return ContextNarrativeResult(text=texto_llm.strip(), source="llm")

    return ContextNarrativeResult(
        text=_plantilla_generica_contexto(contexto, decision_label, datos), source="template"
    )
