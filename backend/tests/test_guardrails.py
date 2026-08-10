"""Tests para engine.guardrails — TDD: escritos antes que la implementación.

Guardrails duros no negociables (ver 00-research/06-periodizacion-ciencia-
deportiva.md, sección "Reglas de seguridad duras (hard gates)"):

1. ACWR > 1.5 durante 2 días consecutivos -> deload automático inmediato
   (3-5 días), independiente del calendario de bloque.
2. weight_phase = CUT AND readiness = RED durante >=3 días consecutivos
   -> pausar el déficit (subir a mantenimiento) hasta normalizar.
3. RED + evento de competición <72h -> forzar descanso total, nunca
   sesión técnica de sparring intenso.
4. Nunca 2 sesiones de alta demanda neuromuscular el mismo día salvo que
   ambas estén en modo mantenimiento y separadas >=6h (verificado aquí a
   nivel de "misma franja horaria" simplificado a un flag explícito).

Estos guardrails combinan estado de varios días/módulos (periodización +
nutrición), a diferencia de compute_readiness/decide_session que solo
miran el día actual.
"""
import pytest

from engine.nutrition import WeightPhase
from engine.periodization import ReadinessLevel
from engine.guardrails import (
    should_force_deload,
    should_pause_calorie_deficit,
    should_pause_calorie_deficit_for_poor_sleep,
    should_force_full_rest_pre_competition,
    validate_same_day_sessions,
)


class TestShouldForceDeload:
    def test_acwr_alto_dos_dias_seguidos_fuerza_deload(self):
        assert should_force_deload(acwr_history=[1.6, 1.55]) is True

    def test_acwr_alto_un_solo_dia_no_fuerza_deload(self):
        # Un pico aislado no es suficiente; hace falta la persistencia.
        assert should_force_deload(acwr_history=[1.6, 1.2]) is False

    def test_acwr_normal_no_fuerza_deload(self):
        assert should_force_deload(acwr_history=[1.1, 1.05]) is False

    def test_solo_mira_los_dos_ultimos_dias(self):
        # Un pico antiguo ya resuelto no debe disparar el guardrail hoy.
        assert should_force_deload(acwr_history=[1.8, 1.8, 1.1, 1.1]) is False

    def test_rechaza_historial_vacio(self):
        with pytest.raises(ValueError):
            should_force_deload(acwr_history=[])

    def test_rechaza_valores_negativos(self):
        with pytest.raises(ValueError):
            should_force_deload(acwr_history=[1.6, -0.5])

    def test_rechaza_bool_disfrazado_en_historial(self):
        with pytest.raises(ValueError):
            should_force_deload(acwr_history=[1.6, True])

    def test_rechaza_nan_o_infinito_en_historial(self):
        with pytest.raises(ValueError):
            should_force_deload(acwr_history=[1.6, float("nan")])
        with pytest.raises(ValueError):
            should_force_deload(acwr_history=[1.6, float("inf")])


class TestShouldPauseCalorieDeficit:
    def test_cut_con_tres_dias_red_seguidos_pausa_deficit(self):
        historial = [ReadinessLevel.RED] * 3
        assert (
            should_pause_calorie_deficit(
                weight_phase=WeightPhase.CUT, readiness_history=historial
            )
            is True
        )

    def test_cut_con_dos_dias_red_seguidos_no_pausa_aun(self):
        historial = [ReadinessLevel.RED, ReadinessLevel.RED]
        assert (
            should_pause_calorie_deficit(
                weight_phase=WeightPhase.CUT, readiness_history=historial
            )
            is False
        )

    def test_cut_con_red_no_consecutivo_no_pausa(self):
        historial = [ReadinessLevel.RED, ReadinessLevel.GREEN, ReadinessLevel.RED]
        assert (
            should_pause_calorie_deficit(
                weight_phase=WeightPhase.CUT, readiness_history=historial
            )
            is False
        )

    def test_fase_distinta_de_cut_nunca_pausa_nada(self):
        # El guardrail solo aplica a fases con déficit activo (CUT).
        historial = [ReadinessLevel.RED] * 5
        for fase in (WeightPhase.MAINTENANCE, WeightPhase.RECOMP, WeightPhase.SURPLUS):
            assert (
                should_pause_calorie_deficit(
                    weight_phase=fase, readiness_history=historial
                )
                is False
            )

    def test_rechaza_historial_vacio(self):
        with pytest.raises(ValueError):
            should_pause_calorie_deficit(
                weight_phase=WeightPhase.CUT, readiness_history=[]
            )

    def test_rechaza_elemento_no_readinesslevel_en_historial(self):
        with pytest.raises(ValueError):
            should_pause_calorie_deficit(
                weight_phase=WeightPhase.CUT,
                readiness_history=["red", "red", "red"],
            )

    def test_rechaza_weight_phase_invalido(self):
        with pytest.raises(ValueError):
            should_pause_calorie_deficit(
                weight_phase="cut", readiness_history=[ReadinessLevel.RED] * 3
            )


class TestShouldPauseCalorieDeficitForPoorSleep:
    """Épica I del plan de expansión (02-roadmap/03-vision-produccion.md):
    extensión CONSERVADORA de la regla ya existente
    (should_pause_calorie_deficit), usando sleep_score crudo en vez del
    semáforo categórico - misma filosofía (pausar, nunca "aflojar" el
    déficit), mismos 3 días consecutivos que la regla hermana, para no
    introducir un criterio temporal nuevo sin justificación.

    Umbrales confirmados explícitamente por el usuario tras revisar
    00-research/08-nutricion-recovery-ciencia.md (nunca inventados
    unilateralmente por el agente): sleep_score < 60 (categoría "poor"
    oficial de Garmin) durante 3 noches consecutivas."""

    def test_cut_con_tres_noches_de_sleep_score_bajo_pausa_deficit(self):
        assert (
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase=WeightPhase.CUT, sleep_scores=[55, 58, 50]
            )
            is True
        )

    def test_cut_con_dos_noches_bajas_no_pausa_aun(self):
        assert (
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase=WeightPhase.CUT, sleep_scores=[55, 58]
            )
            is False
        )

    def test_sleep_score_exactamente_60_no_cuenta_como_bajo(self):
        # Umbral estrictamente menor que 60 (categoría "poor" de Garmin
        # es <60) - 60 exacto ya es "fair", no debe disparar la pausa.
        assert (
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase=WeightPhase.CUT, sleep_scores=[60, 60, 60]
            )
            is False
        )

    def test_una_sola_noche_buena_en_la_racha_no_pausa(self):
        assert (
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase=WeightPhase.CUT, sleep_scores=[55, 70, 50]
            )
            is False
        )

    def test_un_dato_ausente_en_la_racha_no_pausa(self):
        # "unknown is not zero": un día sin sleep_score (None, no
        # sincronizado o el dispositivo no lo calculó) NUNCA se trata
        # como si fuera un dato malo - se necesitan 3 noches CONFIRMADAS
        # por debajo del umbral, no 2 malas + 1 desconocida.
        assert (
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase=WeightPhase.CUT, sleep_scores=[55, None, 50]
            )
            is False
        )

    def test_fase_distinta_de_cut_nunca_pausa_nada(self):
        for fase in (WeightPhase.MAINTENANCE, WeightPhase.RECOMP, WeightPhase.SURPLUS):
            assert (
                should_pause_calorie_deficit_for_poor_sleep(
                    weight_phase=fase, sleep_scores=[55, 58, 50]
                )
                is False
            )

    def test_rechaza_lista_vacia(self):
        with pytest.raises(ValueError):
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase=WeightPhase.CUT, sleep_scores=[]
            )

    def test_rechaza_weight_phase_invalido(self):
        with pytest.raises(ValueError):
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase="cut", sleep_scores=[55, 58, 50]
            )

    def test_rechaza_elemento_de_tipo_invalido_en_sleep_scores(self):
        with pytest.raises(ValueError):
            should_pause_calorie_deficit_for_poor_sleep(
                weight_phase=WeightPhase.CUT, sleep_scores=["55", 58, 50]
            )


class TestShouldForceFullRestPreCompetition:
    def test_red_con_competicion_en_menos_de_72h_fuerza_descanso(self):
        assert (
            should_force_full_rest_pre_competition(
                days_to_competition=2, readiness=ReadinessLevel.RED
            )
            is True
        )

    def test_green_con_competicion_cercana_no_fuerza_descanso(self):
        # Sin señales de mala recuperación, la proximidad de competición
        # sola no basta - eso ya lo gestiona el taper del plan semanal.
        assert (
            should_force_full_rest_pre_competition(
                days_to_competition=2, readiness=ReadinessLevel.GREEN
            )
            is False
        )

    def test_red_sin_competicion_programada_no_aplica(self):
        assert (
            should_force_full_rest_pre_competition(
                days_to_competition=None, readiness=ReadinessLevel.RED
            )
            is False
        )

    def test_red_con_competicion_lejana_no_aplica(self):
        assert (
            should_force_full_rest_pre_competition(
                days_to_competition=10, readiness=ReadinessLevel.RED
            )
            is False
        )

    def test_limite_exacto_72h_si_aplica(self):
        assert (
            should_force_full_rest_pre_competition(
                days_to_competition=3, readiness=ReadinessLevel.RED
            )
            is True
        )

    def test_rechaza_dias_negativos(self):
        with pytest.raises(ValueError):
            should_force_full_rest_pre_competition(
                days_to_competition=-1, readiness=ReadinessLevel.RED
            )

    def test_rechaza_dias_booleanos(self):
        # True/False son subclases de int en Python: sin blindaje explícito,
        # False (0 días) pasaría silenciosamente en vez de lanzar.
        with pytest.raises(ValueError):
            should_force_full_rest_pre_competition(
                days_to_competition=True, readiness=ReadinessLevel.RED
            )
        with pytest.raises(ValueError):
            should_force_full_rest_pre_competition(
                days_to_competition=False, readiness=ReadinessLevel.RED
            )

    def test_rechaza_dias_no_finitos_o_no_enteros(self):
        with pytest.raises(ValueError):
            should_force_full_rest_pre_competition(
                days_to_competition=float("nan"), readiness=ReadinessLevel.RED
            )
        with pytest.raises(ValueError):
            should_force_full_rest_pre_competition(
                days_to_competition=2.5, readiness=ReadinessLevel.RED
            )

    def test_rechaza_readiness_invalido(self):
        with pytest.raises(ValueError):
            should_force_full_rest_pre_competition(
                days_to_competition=2, readiness="red"
            )


class TestValidateSameDaySessions:
    def test_dos_sesiones_alta_demanda_sin_mantenimiento_ni_separacion_es_invalido(self):
        es_valido, motivo = validate_same_day_sessions(
            ambas_en_mantenimiento=False, separacion_horas=2
        )
        assert es_valido is False
        assert motivo == "sin_mantenimiento_y_sin_separacion_suficiente"

    def test_dos_sesiones_alta_demanda_en_mantenimiento_y_separadas_es_valido(self):
        es_valido, motivo = validate_same_day_sessions(
            ambas_en_mantenimiento=True, separacion_horas=8
        )
        assert es_valido is True
        assert motivo is None

    def test_mantenimiento_pero_poca_separacion_es_invalido(self):
        es_valido, motivo = validate_same_day_sessions(
            ambas_en_mantenimiento=True, separacion_horas=3
        )
        assert es_valido is False
        assert motivo == "separacion_insuficiente"

    def test_separacion_suficiente_pero_sin_mantenimiento_es_invalido(self):
        es_valido, motivo = validate_same_day_sessions(
            ambas_en_mantenimiento=False, separacion_horas=8
        )
        assert es_valido is False
        assert motivo == "sin_mantenimiento"

    def test_rechaza_separacion_negativa(self):
        with pytest.raises(ValueError):
            validate_same_day_sessions(ambas_en_mantenimiento=True, separacion_horas=-1)

    def test_rechaza_separacion_nan_o_infinita(self):
        with pytest.raises(ValueError):
            validate_same_day_sessions(
                ambas_en_mantenimiento=True, separacion_horas=float("nan")
            )
        with pytest.raises(ValueError):
            validate_same_day_sessions(
                ambas_en_mantenimiento=True, separacion_horas=float("inf")
            )

    def test_rechaza_ambas_en_mantenimiento_no_booleano(self):
        # int(1) es "truthy" pero no debe aceptarse como bool implícito:
        # un guardrail de seguridad no debe inferir tipos.
        with pytest.raises(ValueError):
            validate_same_day_sessions(ambas_en_mantenimiento=1, separacion_horas=8)
