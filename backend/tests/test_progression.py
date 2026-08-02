"""Tests para engine.progression — TDD: escritos antes que la implementación.

Referencias (ver 00-research/06-periodizacion-ciencia-deportiva.md):
- Epley (1RM estimation): 1RM = peso * (1 + reps/30)
- Doble progresión: patrón estándar de programación de fuerza/hipertrofia.
- RIR/RPE autoregulation (Helms, Zourdos): ajustar carga según reps-in-reserve
  real vs. objetivo, no solo según el peso levantado.
"""
import pytest

from engine.progression import (
    RepRange,
    SetPerformance,
    estimate_1rm,
    suggest_double_progression,
    ProgressionAction,
    suggest_rir_load_adjustment,
)


class TestEstimate1RM:
    def test_epley_formula_referencia(self):
        # 100kg x 5 reps -> 100 * (1 + 5/30) = 116.666...
        assert estimate_1rm(peso_kg=100, reps=5) == pytest.approx(116.6667, abs=0.01)

    def test_una_repeticion_da_un_valor_ligeramente_superior_al_peso(self):
        # Epley: 1RM = peso*(1+reps/30). En reps=1 no da exactamente el
        # peso (es una aproximación, no una identidad) - da peso*1.0333.
        assert estimate_1rm(peso_kg=100, reps=1) == pytest.approx(103.333, abs=0.01)

    def test_rechaza_peso_no_positivo(self):
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=0, reps=5)

    def test_rechaza_reps_no_positivas(self):
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=100, reps=0)

    def test_rechaza_reps_fuera_del_rango_fiable(self):
        # Epley se degrada mucho por encima de ~15-20 reps: no es fiable
        # para estimar 1RM real, mejor rechazar que devolver un número falso.
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=100, reps=25)

    def test_acepta_el_limite_exacto_de_reps_fiables(self):
        # Frontera: 15 reps debe pasar (límite inclusivo), 16 debe fallar.
        assert estimate_1rm(peso_kg=100, reps=15) == pytest.approx(150, abs=0.01)
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=100, reps=16)

    def test_rechaza_reps_no_finitas(self):
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=100, reps=float("nan"))
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=100, reps=float("inf"))

    def test_rechaza_peso_no_finito(self):
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=float("nan"), reps=5)
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=float("inf"), reps=5)

    def test_rechaza_peso_fuera_de_rango_superior(self):
        with pytest.raises(ValueError):
            estimate_1rm(peso_kg=600, reps=5)


class TestDoubleProgression:
    """Doble progresión: subir reps dentro del rango objetivo; al tocar
    el techo del rango, subir peso y reiniciar reps al suelo del rango."""

    def test_reps_por_debajo_del_techo_sube_solo_reps_objetivo(self):
        rango = RepRange(min_reps=8, max_reps=12)
        resultado = suggest_double_progression(
            peso_actual_kg=60, reps_logradas=10, rango=rango
        )
        assert resultado.accion == ProgressionAction.INCREASE_REPS
        assert resultado.peso_siguiente_kg == 60
        assert resultado.reps_objetivo_siguiente == 11

    def test_reps_en_el_techo_sube_peso_y_reinicia_reps(self):
        rango = RepRange(min_reps=8, max_reps=12)
        resultado = suggest_double_progression(
            peso_actual_kg=60, reps_logradas=12, rango=rango
        )
        assert resultado.accion == ProgressionAction.INCREASE_WEIGHT
        assert resultado.peso_siguiente_kg > 60
        assert resultado.reps_objetivo_siguiente == rango.min_reps

    def test_reps_por_debajo_del_minimo_mantiene_peso_y_reps_minimas(self):
        # No se alcanzó ni el mínimo del rango: no hay progreso que dar,
        # se mantiene el mismo estímulo (no se penaliza bajando peso aquí,
        # eso lo decide guardrails/fatiga, no este módulo).
        rango = RepRange(min_reps=8, max_reps=12)
        resultado = suggest_double_progression(
            peso_actual_kg=60, reps_logradas=5, rango=rango
        )
        assert resultado.accion == ProgressionAction.HOLD
        assert resultado.peso_siguiente_kg == 60
        assert resultado.reps_objetivo_siguiente == rango.min_reps

    def test_incremento_de_peso_es_moderado(self):
        # El incremento no debe ser agresivo (evitar saltos >10% en un
        # ejercicio de fuerza/hipertrofia estándar).
        rango = RepRange(min_reps=8, max_reps=12)
        resultado = suggest_double_progression(
            peso_actual_kg=100, reps_logradas=12, rango=rango
        )
        incremento_pct = (resultado.peso_siguiente_kg - 100) / 100
        assert 0.01 <= incremento_pct <= 0.10

    def test_rechaza_rango_invertido(self):
        with pytest.raises(ValueError):
            RepRange(min_reps=12, max_reps=8)

    def test_rango_con_min_igual_a_max_es_valido(self):
        # Rango de un único valor (ej. series a repeticiones fijas):
        # cualquier reps_logradas >= ese valor sube peso de inmediato.
        rango = RepRange(min_reps=10, max_reps=10)
        resultado = suggest_double_progression(
            peso_actual_kg=60, reps_logradas=10, rango=rango
        )
        assert resultado.accion == ProgressionAction.INCREASE_WEIGHT

    def test_reps_logradas_cero_no_lanza_y_devuelve_hold(self):
        rango = RepRange(min_reps=8, max_reps=12)
        resultado = suggest_double_progression(
            peso_actual_kg=60, reps_logradas=0, rango=rango
        )
        assert resultado.accion == ProgressionAction.HOLD

    def test_rechaza_peso_no_positivo(self):
        rango = RepRange(min_reps=8, max_reps=12)
        with pytest.raises(ValueError):
            suggest_double_progression(peso_actual_kg=0, reps_logradas=10, rango=rango)

    def test_rechaza_reps_logradas_no_finitas(self):
        rango = RepRange(min_reps=8, max_reps=12)
        with pytest.raises(ValueError):
            suggest_double_progression(
                peso_actual_kg=60, reps_logradas=float("nan"), rango=rango
            )


class TestRirLoadAdjustment:
    """Autorregulación estilo APRE/RIR: comparar RIR real vs objetivo."""

    def test_rir_real_mayor_al_objetivo_sube_carga(self):
        # Le sobró mucha reserva (fue más fácil de lo esperado) -> subir carga.
        performance = SetPerformance(rir_objetivo=2, rir_real=4)
        resultado = suggest_rir_load_adjustment(
            peso_actual_kg=100, performance=performance
        )
        assert resultado.accion == ProgressionAction.INCREASE_WEIGHT
        assert resultado.peso_siguiente_kg > 100

    def test_rir_real_menor_al_objetivo_baja_carga(self):
        # Le costó más de lo esperado (RIR real por debajo del objetivo)
        # -> bajar carga para no acumular fatiga excesiva.
        performance = SetPerformance(rir_objetivo=2, rir_real=0)
        resultado = suggest_rir_load_adjustment(
            peso_actual_kg=100, performance=performance
        )
        assert resultado.accion == ProgressionAction.DECREASE_WEIGHT
        assert resultado.peso_siguiente_kg < 100

    def test_rir_real_igual_al_objetivo_mantiene_carga(self):
        performance = SetPerformance(rir_objetivo=2, rir_real=2)
        resultado = suggest_rir_load_adjustment(
            peso_actual_kg=100, performance=performance
        )
        assert resultado.accion == ProgressionAction.HOLD
        assert resultado.peso_siguiente_kg == 100

    def test_ajuste_de_carga_es_moderado_no_agresivo(self):
        performance = SetPerformance(rir_objetivo=2, rir_real=5)
        resultado = suggest_rir_load_adjustment(
            peso_actual_kg=100, performance=performance
        )
        cambio_pct = abs(resultado.peso_siguiente_kg - 100) / 100
        assert cambio_pct <= 0.10

    def test_rechaza_rir_negativo(self):
        with pytest.raises(ValueError):
            SetPerformance(rir_objetivo=2, rir_real=-1)

    def test_rechaza_rir_no_finito(self):
        with pytest.raises(ValueError):
            SetPerformance(rir_objetivo=2, rir_real=float("nan"))
        with pytest.raises(ValueError):
            SetPerformance(rir_objetivo=float("inf"), rir_real=2)

    def test_rir_alto_simetrico_mantiene_carga(self):
        performance = SetPerformance(rir_objetivo=5, rir_real=5)
        resultado = suggest_rir_load_adjustment(
            peso_actual_kg=100, performance=performance
        )
        assert resultado.accion == ProgressionAction.HOLD

    def test_rechaza_peso_no_positivo(self):
        performance = SetPerformance(rir_objetivo=2, rir_real=2)
        with pytest.raises(ValueError):
            suggest_rir_load_adjustment(peso_actual_kg=0, performance=performance)
