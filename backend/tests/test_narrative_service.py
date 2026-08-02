"""Tests para coach.narrative_service — TDD.

Principios de la Capa 3 (ver docs/00-research/07-arquitectura-coach-ia.md):
- El LLM NUNCA decide, solo explica una decisión ya tomada por la Capa 1.
- La IA es opcional y no autoritativa: el producto debe funcionar sin
  LLM (plantilla determinista de respaldo, siempre disponible).
- Validación post-generación en dos niveles: FORMA (no vacío, longitud
  razonable, `_es_texto_llm_valido`) y CONTENIDO (no debe contradecir la
  decisión estructurada, `_es_texto_llm_coherente` - ver clase
  `TestGenerateSessionNarrativeConLLM.test_rechaza_texto_llm_que_contradice...`).
"""
from unittest.mock import MagicMock

import pytest

from coach.gemini_client import GeminiClient, GeminiError
from coach.narrative_service import generate_session_narrative
from engine.periodization import ReadinessLevel, SessionRecommendation, SessionType


class TestGenerateSessionNarrativeSinLLM:
    def test_sin_cliente_gemini_usa_plantilla_determinista(self):
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=100
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.GREEN, gemini_client=None
        )
        assert resultado.source == "template"
        assert resultado.text  # no vacío
        assert "strength_heavy" in resultado.text or "fuerza" in resultado.text.lower()

    def test_plantilla_menciona_descanso_cuando_toca_active_recovery(self):
        recomendacion = SessionRecommendation(
            session_type=SessionType.ACTIVE_RECOVERY, volume_pct=0
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.RED, gemini_client=None
        )
        assert resultado.source == "template"
        assert "recuperación" in resultado.text.lower() or "descanso" in resultado.text.lower()

    def test_plantilla_nunca_esta_vacia_para_ningun_session_type(self):
        for session_type in SessionType:
            for readiness in ReadinessLevel:
                recomendacion = SessionRecommendation(session_type=session_type, volume_pct=50)
                resultado = generate_session_narrative(
                    recomendacion, readiness=readiness, gemini_client=None
                )
                assert resultado.text.strip() != ""

    def test_plantilla_incluye_el_cap_de_rpe_cuando_esta_presente(self):
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=65, intensity_rpe_cap=7
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.YELLOW, gemini_client=None
        )
        assert "RPE" in resultado.text
        assert "7" in resultado.text


class TestGenerateSessionNarrativeConLLM:
    def test_usa_el_texto_del_llm_si_es_valido(self):
        fake_client = MagicMock(spec=GeminiClient)
        fake_client.generate.return_value = (
            "Hoy toca fuerza pesada al 100% porque tu recuperación es excelente."
        )
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=100
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.GREEN, gemini_client=fake_client
        )
        assert resultado.source == "llm"
        assert "fuerza pesada" in resultado.text

    def test_cae_a_plantilla_si_gemini_lanza_error(self):
        fake_client = MagicMock(spec=GeminiClient)
        fake_client.generate.side_effect = GeminiError("quota exceeded")
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=100
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.GREEN, gemini_client=fake_client
        )
        assert resultado.source == "template"
        assert resultado.text  # nunca se rompe el flujo del usuario

    def test_cae_a_plantilla_si_el_llm_devuelve_texto_vacio(self):
        fake_client = MagicMock(spec=GeminiClient)
        fake_client.generate.return_value = "   "
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=100
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.GREEN, gemini_client=fake_client
        )
        assert resultado.source == "template"

    def test_cae_a_plantilla_si_el_llm_devuelve_texto_absurdamente_largo(self):
        # Validación post-generación: un texto desproporcionado sugiere
        # una respuesta degenerada/no confiable del modelo - mejor la
        # plantilla corta y auditada que un output sin control de forma.
        fake_client = MagicMock(spec=GeminiClient)
        fake_client.generate.return_value = "x" * 5000
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=100
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.GREEN, gemini_client=fake_client
        )
        assert resultado.source == "template"

    def test_el_llm_nunca_decide_solo_explica_la_decision_ya_tomada(self):
        # No hay ningún parámetro por el que el LLM pueda influir en
        # session_type/volume_pct - eso ya viene fijado en `recomendacion`
        # (calculado por engine.periodization, Capa 1).
        fake_client = MagicMock(spec=GeminiClient)
        fake_client.generate.return_value = "Hoy toca fuerza pesada, dale con todo."
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=100
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.GREEN, gemini_client=fake_client
        )
        # El texto puede variar, pero el objeto de decisión estructurado
        # que consume el resto del sistema sigue siendo `recomendacion`,
        # inalterado - el narrative_service no devuelve una decisión, solo texto.
        assert recomendacion.session_type == SessionType.STRENGTH_HEAVY
        assert resultado.source == "llm"

    def test_rechaza_texto_llm_que_contradice_la_decision_de_entrenar(self):
        # Validación de contenido (no solo forma): si el motor decidió
        # entrenar, un texto que sugiera "descanso total" contradice el
        # dato estructurado y debe descartarse, cayendo a la plantilla.
        fake_client = MagicMock(spec=GeminiClient)
        fake_client.generate.return_value = (
            "Deberías hacer descanso total en vez de entrenar hoy."
        )
        recomendacion = SessionRecommendation(
            session_type=SessionType.STRENGTH_HEAVY, volume_pct=100
        )
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.GREEN, gemini_client=fake_client
        )
        assert resultado.source == "template"

    def test_no_rechaza_mencion_de_descanso_cuando_la_decision_es_descanso(self):
        # La misma frase es válida si la decisión estructurada SÍ es
        # descanso - la validación debe ser contextual, no una lista
        # negra ciega.
        fake_client = MagicMock(spec=GeminiClient)
        fake_client.generate.return_value = "Hoy toca descanso total, tu cuerpo lo necesita."
        recomendacion = SessionRecommendation(session_type=SessionType.REST, volume_pct=0)
        resultado = generate_session_narrative(
            recomendacion, readiness=ReadinessLevel.RED, gemini_client=fake_client
        )
        assert resultado.source == "llm"
