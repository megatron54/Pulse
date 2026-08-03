"""Tests para scheduler.app — solo verifican el cableado (construcción
del job y su trigger), nunca ejecutan el bucle bloqueante de
APScheduler ni tocan una base de datos real."""
import os

from scheduler.app import build_scheduler


class TestBuildScheduler:
    def test_registra_el_job_de_sync_diario(self):
        scheduler = build_scheduler()
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "sync_diario_garmin"

    def test_usa_hora_por_defecto_04_00_si_no_hay_env(self, monkeypatch):
        monkeypatch.delenv("PULSE_SCHEDULER_HORA", raising=False)
        monkeypatch.delenv("PULSE_SCHEDULER_MINUTO", raising=False)
        scheduler = build_scheduler()
        trigger = scheduler.get_jobs()[0].trigger
        campos = {f.name: str(f) for f in trigger.fields}
        assert campos["hour"] == "4"
        assert campos["minute"] == "0"

    def test_respeta_hora_configurada_por_env(self, monkeypatch):
        monkeypatch.setenv("PULSE_SCHEDULER_HORA", "6")
        monkeypatch.setenv("PULSE_SCHEDULER_MINUTO", "30")
        scheduler = build_scheduler()
        trigger = scheduler.get_jobs()[0].trigger
        campos = {f.name: str(f) for f in trigger.fields}
        assert campos["hour"] == "6"
        assert campos["minute"] == "30"
