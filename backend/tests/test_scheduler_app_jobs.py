"""Tests del CUERPO de los jobs de scheduler.app (no solo su cableado -
eso ya lo cubre test_scheduler_app.py). Aislado en su propio módulo
porque necesita parchear `get_session`/las funciones de sync, algo que
el módulo de wiring evita a propósito."""
from datetime import date
from unittest.mock import MagicMock

from scheduler.app import job_sincronizacion_frecuente


class TestJobSincronizacionFrecuente:
    def test_sincroniza_recovery_y_actividades_del_dia_en_curso(self, monkeypatch):
        """Hallazgo del usuario (2026-09-14): una actividad recién
        terminada no aparecía hasta el job nocturno de actividades, un
        día de retraso. El job frecuente (cada 2h) debe traer ambas
        cosas, no solo recovery."""
        session_recovery = MagicMock()
        session_actividades = MagicMock()
        sesiones = iter([session_recovery, session_actividades])
        monkeypatch.setattr("scheduler.app.get_session", lambda: next(sesiones))

        resultado_recovery = MagicMock(exitosos=1, fallidos=0, omitidos=0)
        resultado_actividades = MagicMock(exitosos=1, fallidos=0, omitidos=0)
        mock_recovery = MagicMock(return_value=resultado_recovery)
        mock_actividades = MagicMock(return_value=resultado_actividades)
        monkeypatch.setattr("scheduler.app.run_daily_sync_for_all_users", mock_recovery)
        monkeypatch.setattr(
            "scheduler.app.run_daily_activity_sync_for_all_users", mock_actividades
        )

        job_sincronizacion_frecuente()

        mock_recovery.assert_called_once_with(session_recovery, target_date=date.today())
        mock_actividades.assert_called_once_with(session_actividades, end_date=date.today())
        session_recovery.close.assert_called_once()
        session_actividades.close.assert_called_once()

    def test_un_fallo_sincronizando_actividades_no_impide_haber_sincronizado_recovery(
        self, monkeypatch
    ):
        session_recovery = MagicMock()
        session_actividades = MagicMock()
        sesiones = iter([session_recovery, session_actividades])
        monkeypatch.setattr("scheduler.app.get_session", lambda: next(sesiones))

        monkeypatch.setattr(
            "scheduler.app.run_daily_sync_for_all_users",
            MagicMock(return_value=MagicMock(exitosos=1, fallidos=0, omitidos=0)),
        )
        monkeypatch.setattr(
            "scheduler.app.run_daily_activity_sync_for_all_users",
            MagicMock(side_effect=RuntimeError("fallo inesperado")),
        )

        job_sincronizacion_frecuente()  # no debe propagar la excepción

        session_actividades.close.assert_called_once()
