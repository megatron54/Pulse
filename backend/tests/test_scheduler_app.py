"""Tests para scheduler.app — solo verifican el cableado (construcción
de los jobs y sus triggers), nunca ejecutan el bucle bloqueante de
APScheduler ni tocan una base de datos real."""
from scheduler.app import build_scheduler


def _job(scheduler, job_id):
    return next(j for j in scheduler.get_jobs() if j.id == job_id)


class TestBuildScheduler:
    def test_registra_el_job_de_sync_diario_y_el_de_actividades(self):
        scheduler = build_scheduler()
        ids = {j.id for j in scheduler.get_jobs()}
        assert ids == {"sync_diario_garmin", "sync_actividades_garmin"}

    def test_usa_hora_por_defecto_04_00_si_no_hay_env(self, monkeypatch):
        monkeypatch.delenv("PULSE_SCHEDULER_HORA", raising=False)
        monkeypatch.delenv("PULSE_SCHEDULER_MINUTO", raising=False)
        scheduler = build_scheduler()
        trigger = _job(scheduler, "sync_diario_garmin").trigger
        campos = {f.name: str(f) for f in trigger.fields}
        assert campos["hour"] == "4"
        assert campos["minute"] == "0"

    def test_respeta_hora_configurada_por_env(self, monkeypatch):
        monkeypatch.setenv("PULSE_SCHEDULER_HORA", "6")
        monkeypatch.setenv("PULSE_SCHEDULER_MINUTO", "30")
        scheduler = build_scheduler()
        trigger = _job(scheduler, "sync_diario_garmin").trigger
        campos = {f.name: str(f) for f in trigger.fields}
        assert campos["hour"] == "6"
        assert campos["minute"] == "30"

    def test_actividades_usa_hora_por_defecto_04_15_si_no_hay_env(self, monkeypatch):
        monkeypatch.delenv("PULSE_SCHEDULER_ACTIVIDADES_HORA", raising=False)
        monkeypatch.delenv("PULSE_SCHEDULER_ACTIVIDADES_MINUTO", raising=False)
        scheduler = build_scheduler()
        trigger = _job(scheduler, "sync_actividades_garmin").trigger
        campos = {f.name: str(f) for f in trigger.fields}
        assert campos["hour"] == "4"
        assert campos["minute"] == "15"

    def test_actividades_respeta_hora_configurada_por_env(self, monkeypatch):
        monkeypatch.setenv("PULSE_SCHEDULER_ACTIVIDADES_HORA", "5")
        monkeypatch.setenv("PULSE_SCHEDULER_ACTIVIDADES_MINUTO", "45")
        scheduler = build_scheduler()
        trigger = _job(scheduler, "sync_actividades_garmin").trigger
        campos = {f.name: str(f) for f in trigger.fields}
        assert campos["hour"] == "5"
        assert campos["minute"] == "45"
