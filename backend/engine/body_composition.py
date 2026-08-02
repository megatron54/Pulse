"""Motor de reglas determinista — Estimación de composición corporal.

Capa 1: sin llamadas a red ni a LLM, sin dependencia de MediaPipe/fotos
(esa pieza de extracción de medidas desde imagen es una capa de
ingesta separada, aún no implementada - ver docs/00-research/
05-analisis-corporal-foto.md, Fase 2 del roadmap). Este módulo solo
implementa la fórmula, que recibe medidas ya extraídas (a mano con
cinta métrica, o en el futuro derivadas de landmarks de pose).

Fórmula: US Navy body fat percentage (Hodgdon & Beckett 1984), la
opción recomendada en la investigación por ser auditable, gratuita, y
con décadas de validación (MAE ~3-4% vs DEXA) - frente a modelos de
visión propietarios no reproducibles.

Principio "nunca un número falso-preciso" (ver 00-research/
05-analisis-corporal-foto.md): el resultado es SIEMPRE un rango, nunca
un valor puntual. El margen de incertidumbre (±3%) refleja el error
reportado del método en uso doméstico no controlado (apps serias como
LeanLens/BiteKit declaran el mismo orden de magnitud).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

_SEXOS_VALIDOS = {"M", "F"}
_CM_A_PULGADAS = 1 / 2.54

# Margen de incertidumbre aplicado alrededor del valor puntual de la
# fórmula, para mostrar siempre un rango (ver principio arriba).
_MARGEN_INCERTIDUMBRE_PCT = 3.0

_BODYFAT_MIN, _BODYFAT_MAX = 0.0, 100.0

_ALTURA_CM_MIN, _ALTURA_CM_MAX = 50.0, 260.0
_MEDIDA_CM_MIN, _MEDIDA_CM_MAX = 10.0, 300.0


@dataclass(frozen=True)
class BodyFatEstimate:
    """Estimación de %grasa corporal como RANGO, nunca un único número."""

    rango_min: float
    rango_max: float
    metodo: str = "navy"


def _validar_medida(nombre: str, valor: float, minimo: float, maximo: float) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{nombre} debe ser numérico")
    if not math.isfinite(valor) or not (minimo <= valor <= maximo):
        raise ValueError(f"{nombre} debe ser un número finito entre {minimo} y {maximo}")


def _acotar_rango_fisico(valor_pct: float) -> float:
    return max(_BODYFAT_MIN, min(_BODYFAT_MAX, valor_pct))


def estimate_body_fat_navy(
    sexo: str,
    altura_cm: float,
    cuello_cm: float,
    cintura_cm: float,
    cadera_cm: float | None = None,
) -> BodyFatEstimate:
    """Estima el % de grasa corporal vía la fórmula US Navy.

    - Hombre: no requiere `cadera_cm`.
    - Mujer: requiere `cadera_cm` (ValueError si no se proporciona).

    Lanza ValueError si las medidas producirían un logaritmo de un
    número no positivo (cintura <= cuello en hombres; cintura+cadera <=
    cuello en mujeres) - típicamente indica un error de medición, no un
    caso válido a extrapolar.
    """
    if sexo not in _SEXOS_VALIDOS:
        raise ValueError(f"sexo debe ser uno de {_SEXOS_VALIDOS}")
    _validar_medida("altura_cm", altura_cm, _ALTURA_CM_MIN, _ALTURA_CM_MAX)
    _validar_medida("cuello_cm", cuello_cm, _MEDIDA_CM_MIN, _MEDIDA_CM_MAX)
    _validar_medida("cintura_cm", cintura_cm, _MEDIDA_CM_MIN, _MEDIDA_CM_MAX)

    altura_in = altura_cm * _CM_A_PULGADAS
    cuello_in = cuello_cm * _CM_A_PULGADAS
    cintura_in = cintura_cm * _CM_A_PULGADAS

    if sexo == "M":
        diferencia = cintura_in - cuello_in
        if diferencia <= 0:
            raise ValueError(
                "cintura_cm debe ser mayor que cuello_cm (medida inválida para la fórmula)"
            )
        valor_pct = (
            495
            / (
                1.0324
                - 0.19077 * math.log10(diferencia)
                + 0.15456 * math.log10(altura_in)
            )
            - 450
        )
    else:  # F
        if cadera_cm is None:
            raise ValueError("cadera_cm es obligatorio para sexo='F'")
        _validar_medida("cadera_cm", cadera_cm, _MEDIDA_CM_MIN, _MEDIDA_CM_MAX)
        cadera_in = cadera_cm * _CM_A_PULGADAS
        diferencia = cintura_in + cadera_in - cuello_in
        if diferencia <= 0:
            raise ValueError(
                "cintura_cm + cadera_cm debe ser mayor que cuello_cm (medida inválida)"
            )
        valor_pct = (
            495
            / (
                1.29579
                - 0.35004 * math.log10(diferencia)
                + 0.22100 * math.log10(altura_in)
            )
            - 450
        )

    rango_min = _acotar_rango_fisico(valor_pct - _MARGEN_INCERTIDUMBRE_PCT)
    rango_max = _acotar_rango_fisico(valor_pct + _MARGEN_INCERTIDUMBRE_PCT)
    return BodyFatEstimate(rango_min=rango_min, rango_max=rango_max, metodo="navy")
