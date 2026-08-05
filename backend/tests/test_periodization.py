"""Tests para engine.periodization — TDD: escritos antes que la implementación.

Referencias (ver 00-research/06-periodizacion-ciencia-deportiva.md):
- HRV/Training Readiness/Body Battery como inputs de autorregulación diaria
  (Di, Hongye & Donglin 2025; Williams et al. 2020) — usar tendencia vs.
  baseline personal, no el valor absoluto de un día.
- ACWR (Acute:Chronic Workload Ratio) > 1.5 -> riesgo real de lesión.
- Reglas duras no negociables: dolor articular -> descanso total sin
  excepción, independientemente de lo buenos que sean el resto de datos.
"""
import pytest

from engine.periodization import (
    ReadinessLevel,
    RecoveryContext,
    SessionType,
    compute_readiness,
    decide_session,
)


def _ctx(**overrides) -> RecoveryContext:
    """Contexto de recuperación 'todo perfecto' por defecto, para que cada
    test solo tenga que sobreescribir la señal que le interesa."""
    defaults = dict(
        hrv_today=65.0,
        hrv_baseline_28d=65.0,
        hrv_trend_7d=0.0,
        body_battery_am=80,
        training_readiness="high",
        sleep_score=85,
        acwr=1.0,
        joint_pain_flag=False,
    )
    defaults.update(overrides)
    return RecoveryContext(**defaults)


class TestComputeReadiness:
    def test_todo_perfecto_da_green(self):
        assert compute_readiness(_ctx()) == ReadinessLevel.GREEN

    def test_dolor_articular_siempre_da_red_sin_excepcion(self):
        # Hard gate: incluso con todas las demás señales perfectas.
        ctx = _ctx(joint_pain_flag=True)
        assert compute_readiness(ctx) == ReadinessLevel.RED

    def test_acwr_alto_da_red(self):
        ctx = _ctx(acwr=1.6)
        assert compute_readiness(ctx) == ReadinessLevel.RED

    def test_acwr_moderadamente_alto_da_yellow(self):
        ctx = _ctx(acwr=1.35, sleep_score=45)  # 2º yellow flag para cruzar umbral
        assert compute_readiness(ctx) == ReadinessLevel.YELLOW

    def test_hrv_caida_fuerte_vs_baseline_da_red(self):
        # Caída >15% respecto a la media móvil de 28 días.
        ctx = _ctx(hrv_today=50.0, hrv_baseline_28d=65.0)  # -23%
        assert compute_readiness(ctx) == ReadinessLevel.RED

    def test_hrv_caida_leve_es_solo_yellow_flag(self):
        # -10%: por debajo de -7% (yellow) pero no de -15% (red).
        ctx = _ctx(hrv_today=58.5, hrv_baseline_28d=65.0, sleep_score=45)
        assert compute_readiness(ctx) == ReadinessLevel.YELLOW

    def test_training_readiness_very_low_da_red(self):
        ctx = _ctx(training_readiness="very_low")
        assert compute_readiness(ctx) == ReadinessLevel.RED

    def test_training_readiness_low_es_yellow_flag(self):
        ctx = _ctx(training_readiness="low", sleep_score=45)
        assert compute_readiness(ctx) == ReadinessLevel.YELLOW

    def test_training_readiness_none_no_aporta_flags_calcula_con_el_resto_de_senales(self):
        # Regresión del hallazgo real de Fase H: relojes que no calculan
        # Training Readiness (Forerunner 165 y similares) deben poder
        # llegar a GREEN igualmente si el resto de señales son buenas -
        # None no debe interpretarse como "low"/"very_low" ni como
        # ninguna otra categoría, simplemente no cuenta.
        ctx = _ctx(training_readiness=None)
        assert compute_readiness(ctx) == ReadinessLevel.GREEN

    def test_training_readiness_none_no_impide_detectar_red_por_otra_senal(self):
        ctx = _ctx(training_readiness=None, acwr=1.6)
        assert compute_readiness(ctx) == ReadinessLevel.RED

    def test_acepta_training_readiness_none_sin_lanzar_valueerror(self):
        # __post_init__ no debe validar None contra el enum de valores.
        RecoveryContext(
            hrv_today=65.0,
            hrv_baseline_28d=65.0,
            hrv_trend_7d=0.0,
            body_battery_am=80,
            training_readiness=None,
            sleep_score=85,
            acwr=1.0,
            joint_pain_flag=False,
        )

    def test_body_battery_muy_bajo_da_red(self):
        ctx = _ctx(body_battery_am=25)
        assert compute_readiness(ctx) == ReadinessLevel.RED

    def test_body_battery_bajo_es_yellow_flag(self):
        ctx = _ctx(body_battery_am=45, sleep_score=45)
        assert compute_readiness(ctx) == ReadinessLevel.YELLOW

    def test_un_solo_yellow_flag_no_basta_para_bajar_de_green(self):
        # Solo el sueño algo bajo, todo lo demás perfecto -> sigue en GREEN
        # (se requieren >=2 yellow flags para bajar a YELLOW).
        ctx = _ctx(sleep_score=45)
        assert compute_readiness(ctx) == ReadinessLevel.GREEN

    def test_rechaza_body_battery_fuera_de_rango(self):
        with pytest.raises(ValueError):
            _ctx(body_battery_am=150)

    def test_rechaza_training_readiness_invalido(self):
        with pytest.raises(ValueError):
            _ctx(training_readiness="excelente")

    def test_rechaza_acwr_negativo(self):
        with pytest.raises(ValueError):
            _ctx(acwr=-0.5)

    def test_rechaza_acwr_nan_o_infinito(self):
        with pytest.raises(ValueError):
            _ctx(acwr=float("nan"))
        with pytest.raises(ValueError):
            _ctx(acwr=float("inf"))

    def test_rechaza_hrv_nan_o_infinito(self):
        with pytest.raises(ValueError):
            _ctx(hrv_today=float("nan"))
        with pytest.raises(ValueError):
            _ctx(hrv_trend_7d=float("inf"))

    def test_rechaza_joint_pain_flag_no_booleano(self):
        # Regla de seguridad núcleo: no debe poder colarse un 0/1/None que
        # se comporte como "falsy" y salte el gate de dolor articular.
        with pytest.raises(ValueError):
            _ctx(joint_pain_flag=0)
        with pytest.raises(ValueError):
            _ctx(joint_pain_flag=1)
        with pytest.raises(ValueError):
            _ctx(joint_pain_flag=None)

    def test_rechaza_body_battery_booleano(self):
        with pytest.raises(ValueError):
            _ctx(body_battery_am=True)

    def test_rechaza_sleep_score_booleano(self):
        with pytest.raises(ValueError):
            _ctx(sleep_score=True)

    # --- Bordes exactos de umbral (>, no >=): confirman que un futuro
    # cambio accidental de operador rompería estos tests, no la seguridad
    # del usuario en silencio. ---

    def test_acwr_en_el_borde_exacto_1_5_no_es_red(self):
        ctx = _ctx(acwr=1.5)
        assert compute_readiness(ctx) == ReadinessLevel.GREEN

    def test_acwr_en_el_borde_exacto_1_3_no_es_yellow(self):
        ctx = _ctx(acwr=1.3)
        assert compute_readiness(ctx) == ReadinessLevel.GREEN

    def test_body_battery_en_el_borde_exacto_30_no_es_red(self):
        ctx = _ctx(body_battery_am=30)
        assert compute_readiness(ctx) == ReadinessLevel.GREEN

    def test_body_battery_en_el_borde_exacto_50_no_es_yellow(self):
        ctx = _ctx(body_battery_am=50)
        assert compute_readiness(ctx) == ReadinessLevel.GREEN

    def test_sleep_score_en_el_borde_exacto_50_no_es_yellow(self):
        ctx = _ctx(sleep_score=50)
        assert compute_readiness(ctx) == ReadinessLevel.GREEN

    def test_hrv_delta_en_el_borde_exacto_15_por_ciento_no_es_red(self):
        # -15% exacto: 55.25/65.0 = -0.15 -> la condición es estrictamente
        # "<", no "<=", así que el borde exacto no debe disparar RED.
        ctx = _ctx(hrv_today=55.25, hrv_baseline_28d=65.0)
        assert compute_readiness(ctx) != ReadinessLevel.RED


class TestDecideSession:
    def test_green_sigue_el_plan_al_100_por_cien(self):
        resultado = decide_session(
            planned_session=SessionType.STRENGTH_HEAVY, readiness=ReadinessLevel.GREEN
        )
        assert resultado.session_type == SessionType.STRENGTH_HEAVY
        assert resultado.volume_pct == 100

    def test_yellow_reduce_volumen_entre_30_y_50_por_ciento(self):
        resultado = decide_session(
            planned_session=SessionType.STRENGTH_HEAVY,
            readiness=ReadinessLevel.YELLOW,
        )
        assert resultado.session_type == SessionType.STRENGTH_HEAVY
        assert 50 <= resultado.volume_pct <= 70
        assert resultado.intensity_rpe_cap is not None
        assert resultado.intensity_rpe_cap <= 7

    def test_red_en_sesion_de_alta_demanda_fuerza_sesion_de_descanso(self):
        for planned in (
            SessionType.STRENGTH_HEAVY,
            SessionType.MARTIAL_ARTS_SPARRING,
            SessionType.ENDURANCE_INTERVALS,
        ):
            resultado = decide_session(planned_session=planned, readiness=ReadinessLevel.RED)
            assert resultado.session_type in (
                SessionType.REST,
                SessionType.ACTIVE_RECOVERY,
            )
            assert resultado.volume_pct == 0

    def test_red_en_sesion_ya_ligera_se_permite_a_baja_intensidad(self):
        resultado = decide_session(
            planned_session=SessionType.MARTIAL_ARTS_TECHNICAL,
            readiness=ReadinessLevel.RED,
        )
        assert resultado.session_type == SessionType.MARTIAL_ARTS_TECHNICAL
        assert resultado.volume_pct <= 50

    def test_nunca_devuelve_volumen_negativo_ni_mayor_a_100(self):
        for readiness in ReadinessLevel:
            for planned in SessionType:
                if planned in (SessionType.REST, SessionType.ACTIVE_RECOVERY):
                    continue
                resultado = decide_session(planned_session=planned, readiness=readiness)
                assert 0 <= resultado.volume_pct <= 100
