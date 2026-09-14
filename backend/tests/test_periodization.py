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
    SignalState,
    assess_signals,
    assess_signals_from_values,
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


def _estado(senales, nombre):
    return next(s.estado for s in senales if s.senal == nombre)


class TestAssessSignals:
    """La explicación que ve el usuario y el veredicto del semáforo
    salen del mismo cálculo: la pantalla decía "Recuperación baja" y
    debajo enseñaba seis cifras buenas, sin nada que uniera las dos
    cosas ("¿por qué está en rojo?" fue la pregunta literal)."""

    def test_todo_perfecto_deja_todas_las_senales_en_ok(self):
        estados = {s.senal: s.estado for s in assess_signals(_ctx())}
        assert set(estados.values()) == {SignalState.OK}

    def test_senala_la_tendencia_de_vfc_cuando_es_ella_la_que_cruza_el_umbral(self):
        # El caso real: VFC de hoy POR ENCIMA de la baseline (+16%) y
        # aun así rojo, porque la tendencia de 7 días estaba en -0,19.
        # Colapsar las dos en una sola señal "VFC" escondía justo la que
        # decidía, y era la única que no aparecía en ninguna pantalla.
        ctx = _ctx(hrv_today=69.0, hrv_baseline_28d=59.3, hrv_trend_7d=-0.19)
        senales = assess_signals(ctx)

        assert _estado(senales, "hrv_delta") == SignalState.OK
        assert _estado(senales, "hrv_trend") == SignalState.RED
        assert compute_readiness(ctx) == ReadinessLevel.RED

    def test_una_senal_no_medida_es_unknown_y_no_se_da_por_buena(self):
        # Varios Garmin de gama media no calculan Training Readiness:
        # eso no es "moderado", es que no hay dato (doctrina 6).
        senales = assess_signals(_ctx(training_readiness=None))
        assert _estado(senales, "training_readiness") == SignalState.UNKNOWN

    def test_el_sueno_bajo_nunca_es_rojo_por_si_solo(self):
        senales = assess_signals(_ctx(sleep_score=10))
        assert _estado(senales, "sleep") == SignalState.YELLOW

    def test_el_acwr_empeora_hacia_arriba_no_hacia_abajo(self):
        # La interfaz necesita saber la dirección para escribir "por
        # encima de 1,5" en vez de "por debajo de": un ACWR bajo no es
        # un problema, uno alto sí.
        senales = assess_signals(_ctx(acwr=1.6))
        acwr = next(s for s in senales if s.senal == "acwr")
        assert acwr.estado == SignalState.RED
        assert acwr.peor_hacia == "arriba"

    def test_los_umbrales_viajan_con_la_senal(self):
        # Para que el frontend no tenga que repetir los números del
        # motor: un 30 escrito a mano en React se queda atrás en el
        # primer ajuste de umbral.
        bb = next(s for s in assess_signals(_ctx()) if s.senal == "body_battery")
        assert (bb.umbral_rojo, bb.umbral_amarillo) == (30, 50)

    @pytest.mark.parametrize(
        "overrides",
        [
            {},
            {"joint_pain_flag": True},
            {"acwr": 1.6},
            {"acwr": 1.35, "sleep_score": 45},
            {"hrv_today": 50.0, "hrv_baseline_28d": 65.0},
            {"hrv_trend_7d": -0.2},
            {"training_readiness": "very_low"},
            {"training_readiness": None, "body_battery_am": 25},
            {"body_battery_am": 45, "sleep_score": 45},
            {"sleep_score": 45},
        ],
    )
    def test_el_veredicto_nunca_contradice_a_las_senales(self, overrides):
        """Invariante que justifica el refactor: si el semáforo dice
        ROJO, alguna señal tiene que estar en rojo; si dice ÁMBAR, al
        menos dos en ámbar y ninguna en rojo; si dice VERDE, ninguna
        en rojo ni dos en ámbar. Antes los umbrales vivían dos veces
        (aquí y, implícitos, en la pantalla) y podían divergir."""
        ctx = _ctx(**overrides)
        nivel = compute_readiness(ctx)
        estados = [s.estado for s in assess_signals(ctx)]
        rojas = estados.count(SignalState.RED)
        ambares = estados.count(SignalState.YELLOW)

        if nivel is ReadinessLevel.RED:
            assert rojas >= 1
        elif nivel is ReadinessLevel.YELLOW:
            assert rojas == 0 and ambares >= 2
        else:
            assert rojas == 0 and ambares < 2


class TestAssessSignalsFromValues:
    """Entrada alternativa para explicar un día del HISTORIAL: la fila
    de ReadinessLog guarda el delta de VFC ya calculado y no guarda la
    VFC de hoy ni la baseline, así que pedir un RecoveryContext
    obligaría a inventarse dos números."""

    def test_valores_ausentes_son_unknown_no_ok(self):
        senales = assess_signals_from_values(
            hrv_delta_pct=None,
            hrv_trend_7d=None,
            training_readiness=None,
            body_battery_am=None,
            acwr=None,
            sleep_score=None,
            joint_pain_flag=False,
        )
        no_medidas = {s.senal for s in senales if s.estado is SignalState.UNKNOWN}
        assert no_medidas == {
            "hrv_delta",
            "hrv_trend",
            "training_readiness",
            "body_battery",
            "acwr",
            "sleep",
        }

    def test_da_el_mismo_resultado_que_desde_un_contexto_completo(self):
        ctx = _ctx(hrv_today=55.0, hrv_baseline_28d=65.0, body_battery_am=40)
        desde_valores = assess_signals_from_values(
            hrv_delta_pct=(55.0 - 65.0) / 65.0,
            hrv_trend_7d=ctx.hrv_trend_7d,
            training_readiness=ctx.training_readiness,
            body_battery_am=ctx.body_battery_am,
            acwr=ctx.acwr,
            sleep_score=ctx.sleep_score,
            joint_pain_flag=ctx.joint_pain_flag,
        )
        assert [s.estado for s in desde_valores] == [s.estado for s in assess_signals(ctx)]
