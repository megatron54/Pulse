"""Test mínimo para scripts.garmin_pair — solo la parte no interactiva
(el directorio de tokens por defecto). El resto del script es
deliberadamente interactivo (email/password por terminal) y queda
fuera de TDD a propósito, ver el docstring del propio script."""
from pathlib import Path

from scripts.garmin_pair import _directorio_tokens_por_defecto


class TestDirectorioTokensPorDefecto:
    def test_usa_home_del_usuario_sin_la_variable_de_entorno(self, monkeypatch):
        monkeypatch.delenv("PULSE_GARMIN_TOKENS_DIR", raising=False)
        assert _directorio_tokens_por_defecto() == Path.home() / ".garminconnect"

    def test_usa_pulse_garmin_tokens_dir_si_esta_definida(self, monkeypatch):
        # Hallazgo real al containerizar el scheduler (docker-compose.yml):
        # el home del contenedor no es un buen sitio para el token cacheado
        # (no persiste igual que un volumen nombrado compartido entre
        # `backend` y `scheduler`) - PULSE_GARMIN_TOKENS_DIR permite
        # apuntar al volumen montado en /data/garmin-tokens.
        monkeypatch.setenv("PULSE_GARMIN_TOKENS_DIR", "/data/garmin-tokens")
        assert _directorio_tokens_por_defecto() == Path("/data/garmin-tokens")
