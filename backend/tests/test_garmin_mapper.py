"""Tests para garmin_sync.mapper — TDD: escritos antes que la implementación.

Principio "unknown is not zero" (ver 00-research/07-arquitectura-coach-ia.md):
si falta un dato crítico de recuperación, se debe fallar explícitamente
(InsufficientDataError) en vez de rellenar con un valor por defecto que
enmascare la ausencia de datos ante engine.periodization.compute_readiness.
"""
import pytest

from engine.periodization import RecoveryContext
from garmin_sync.mapper import InsufficientDataError, map_garmin_raw_to_recovery_context


def _raw_completo(**overrides):
    base = dict(
        hrv_today=65.0,
        training_readiness="high",
        body_battery_am=80,
        sleep_score=85,
        raw_json={},
    )
    base.update(overrides)
    return base


class TestMapGarminRawToRecoveryContext:
    def test_mapea_correctamente_con_todos_los_campos_presentes(self):
        ctx = map_garmin_raw_to_recovery_context(
            raw=_raw_completo(),
            hrv_baseline_28d=65.0,
            hrv_trend_7d=0.0,
            acwr=1.0,
            joint_pain_flag=False,
        )
        assert isinstance(ctx, RecoveryContext)
        assert ctx.hrv_today == 65.0
        assert ctx.training_readiness == "high"
        assert ctx.body_battery_am == 80
        assert ctx.sleep_score == 85

    def test_lanza_insufficient_data_si_falta_hrv(self):
        with pytest.raises(InsufficientDataError):
            map_garmin_raw_to_recovery_context(
                raw=_raw_completo(hrv_today=None),
                hrv_baseline_28d=65.0,
                hrv_trend_7d=0.0,
                acwr=1.0,
                joint_pain_flag=False,
            )

    def test_lanza_insufficient_data_si_falta_training_readiness(self):
        with pytest.raises(InsufficientDataError):
            map_garmin_raw_to_recovery_context(
                raw=_raw_completo(training_readiness=None),
                hrv_baseline_28d=65.0,
                hrv_trend_7d=0.0,
                acwr=1.0,
                joint_pain_flag=False,
            )

    def test_lanza_insufficient_data_si_falta_body_battery(self):
        with pytest.raises(InsufficientDataError):
            map_garmin_raw_to_recovery_context(
                raw=_raw_completo(body_battery_am=None),
                hrv_baseline_28d=65.0,
                hrv_trend_7d=0.0,
                acwr=1.0,
                joint_pain_flag=False,
            )

    def test_lanza_insufficient_data_si_falta_sleep_score(self):
        with pytest.raises(InsufficientDataError):
            map_garmin_raw_to_recovery_context(
                raw=_raw_completo(sleep_score=None),
                hrv_baseline_28d=65.0,
                hrv_trend_7d=0.0,
                acwr=1.0,
                joint_pain_flag=False,
            )

    def test_el_mensaje_de_error_identifica_los_campos_faltantes(self):
        with pytest.raises(InsufficientDataError) as exc_info:
            map_garmin_raw_to_recovery_context(
                raw=_raw_completo(hrv_today=None, sleep_score=None),
                hrv_baseline_28d=65.0,
                hrv_trend_7d=0.0,
                acwr=1.0,
                joint_pain_flag=False,
            )
        mensaje = str(exc_info.value)
        assert "hrv_today" in mensaje
        assert "sleep_score" in mensaje

    def test_propaga_joint_pain_flag_hacia_el_gate_de_seguridad(self):
        ctx = map_garmin_raw_to_recovery_context(
            raw=_raw_completo(),
            hrv_baseline_28d=65.0,
            hrv_trend_7d=0.0,
            acwr=1.0,
            joint_pain_flag=True,
        )
        assert ctx.joint_pain_flag is True

    def test_valores_invalidos_de_recoverycontext_siguen_lanzando_valueerror(self):
        # El mapper no debe "arreglar" datos de Garmin fuera de rango
        # (ej. body_battery > 100 por un bug de la API): debe propagar la
        # misma validación estricta de RecoveryContext.
        with pytest.raises(ValueError):
            map_garmin_raw_to_recovery_context(
                raw=_raw_completo(body_battery_am=150),
                hrv_baseline_28d=65.0,
                hrv_trend_7d=0.0,
                acwr=1.0,
                joint_pain_flag=False,
            )
