"""Tests para repositories.readiness_log_repository — TDD."""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from engine.periodization import ReadinessLevel
from models.schema import Base, ReadinessLog, UserProfile
from repositories.readiness_log_repository import (
    get_readiness_log_for_date,
    get_recent_readiness_levels,
    get_volumen_pct_history,
    set_volumen_pct_ajustado,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def usuario(session):
    u = UserProfile(nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M")
    session.add(u)
    session.commit()
    return u


class TestGetReadinessLogForDate:
    """Épica H del plan de expansión (02-roadmap/03-vision-produccion.md):
    el coach de salud necesita la FILA completa de ReadinessLog de un
    día concreto (no solo el `resultado`, como ya da
    `get_latest_readiness_level`) para poder explicar la decisión con
    los campos estructurados que la motivaron."""

    def test_devuelve_none_si_no_hay_ningun_readiness_log_ese_dia(self, session, usuario):
        assert get_readiness_log_for_date(session, usuario.id, date(2026, 8, 6)) is None

    def test_devuelve_la_fila_del_dia_indicado(self, session, usuario):
        session.add(
            ReadinessLog(
                user_id=usuario.id,
                fecha=date(2026, 8, 6),
                resultado=ReadinessLevel.GREEN.value,
                sesion_recomendada="strength_heavy",
            )
        )
        session.commit()

        fila = get_readiness_log_for_date(session, usuario.id, date(2026, 8, 6))

        assert fila is not None
        assert fila.resultado == ReadinessLevel.GREEN.value
        assert fila.sesion_recomendada == "strength_heavy"

    def test_si_hay_varias_filas_el_mismo_dia_devuelve_la_mas_reciente(self, session, usuario):
        # Append-only: un check-in re-ejecutado el mismo día no
        # sobreescribe, añade una fila nueva - "la última gana", mismo
        # criterio que get_latest_readiness_level.
        session.add(
            ReadinessLog(user_id=usuario.id, fecha=date(2026, 8, 6), resultado=ReadinessLevel.RED.value)
        )
        session.commit()
        session.add(
            ReadinessLog(user_id=usuario.id, fecha=date(2026, 8, 6), resultado=ReadinessLevel.GREEN.value)
        )
        session.commit()

        fila = get_readiness_log_for_date(session, usuario.id, date(2026, 8, 6))

        assert fila.resultado == ReadinessLevel.GREEN.value

    def test_no_mezcla_datos_de_otro_usuario(self, session, usuario):
        otro = UserProfile(nombre="Otro", altura_cm=170.0, fecha_nacimiento=date(1990, 1, 1), sexo="F")
        session.add(otro)
        session.commit()
        session.add(
            ReadinessLog(user_id=otro.id, fecha=date(2026, 8, 6), resultado=ReadinessLevel.RED.value)
        )
        session.commit()

        assert get_readiness_log_for_date(session, usuario.id, date(2026, 8, 6)) is None


class TestGetRecentReadinessLevels:
    def test_devuelve_los_ultimos_n_en_orden_cronologico(self, session, usuario):
        hoy = date(2026, 8, 10)
        for i, resultado in enumerate(["green", "yellow", "red"]):
            session.add(
                ReadinessLog(
                    user_id=usuario.id,
                    fecha=hoy - timedelta(days=3 - i),
                    resultado=resultado,
                )
            )
        session.commit()

        niveles = get_recent_readiness_levels(session, usuario.id, hoy, n=3)
        assert niveles == [
            ReadinessLevel.GREEN,
            ReadinessLevel.YELLOW,
            ReadinessLevel.RED,
        ]

    def test_devuelve_lista_vacia_sin_historial(self, session, usuario):
        assert get_recent_readiness_levels(session, usuario.id, date(2026, 8, 10), n=3) == []

    def test_no_incluye_el_dia_de_hoy(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="red"))
        session.commit()
        assert get_recent_readiness_levels(session, usuario.id, hoy, n=3) == []


class TestSetVolumenPctAjustado:
    def test_actualiza_la_fila_mas_reciente_del_dia(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="green"))
        session.commit()

        set_volumen_pct_ajustado(session, usuario.id, hoy, 85)

        fila = session.query(ReadinessLog).filter_by(user_id=usuario.id, fecha=hoy).one()
        assert fila.volumen_pct_ajustado == 85

    def test_si_hay_varias_filas_el_mismo_dia_actualiza_la_mas_reciente(self, session, usuario):
        hoy = date(2026, 8, 10)
        vieja = ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="red")
        session.add(vieja)
        session.commit()
        nueva = ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="green")
        session.add(nueva)
        session.commit()

        set_volumen_pct_ajustado(session, usuario.id, hoy, 100)

        session.refresh(vieja)
        session.refresh(nueva)
        assert vieja.volumen_pct_ajustado is None
        assert nueva.volumen_pct_ajustado == 100

    def test_no_falla_si_no_hay_ningun_readiness_log_ese_dia(self, session, usuario):
        # No hay check-in de recuperación ese día todavía (p.ej. el
        # usuario pidió una sesión manual sin haber hecho check-in) -
        # no hay ninguna fila a la que adjuntar el volumen, así que esta
        # función simplemente no hace nada, en vez de fallar.
        set_volumen_pct_ajustado(session, usuario.id, date(2026, 8, 10), 50)
        assert session.query(ReadinessLog).count() == 0


class TestGetVolumenPctHistory:
    def test_devuelve_fecha_y_volumen_en_orden_cronologico(self, session, usuario):
        hoy = date(2026, 8, 10)
        for i, volumen in enumerate([100, 80, 60]):
            log = ReadinessLog(
                user_id=usuario.id, fecha=hoy - timedelta(days=2 - i), resultado="green"
            )
            session.add(log)
            session.flush()
            log.volumen_pct_ajustado = volumen
        session.commit()

        historial = get_volumen_pct_history(session, usuario.id, as_of=hoy, days=28)
        assert historial == [
            (hoy - timedelta(days=2), 100),
            (hoy - timedelta(days=1), 80),
            (hoy, 60),
        ]

    def test_omite_dias_sin_volumen_asignado_todavia(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="green"))
        session.commit()

        assert get_volumen_pct_history(session, usuario.id, as_of=hoy, days=28) == []

    def test_se_queda_con_el_volumen_de_la_fila_mas_reciente_por_dia(self, session, usuario):
        hoy = date(2026, 8, 10)
        vieja = ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="red")
        session.add(vieja)
        session.flush()
        vieja.volumen_pct_ajustado = 30
        session.commit()

        nueva = ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="green")
        session.add(nueva)
        session.flush()
        nueva.volumen_pct_ajustado = 90
        session.commit()

        assert get_volumen_pct_history(session, usuario.id, as_of=hoy, days=28) == [(hoy, 90)]

    def test_respeta_la_ventana_de_dias(self, session, usuario):
        hoy = date(2026, 8, 10)
        antiguo = ReadinessLog(user_id=usuario.id, fecha=hoy - timedelta(days=40), resultado="green")
        session.add(antiguo)
        session.flush()
        antiguo.volumen_pct_ajustado = 70
        session.commit()

        assert get_volumen_pct_history(session, usuario.id, as_of=hoy, days=28) == []

    def test_la_ventana_de_28_dias_es_exactamente_28_no_29(self, session, usuario):
        # Regresión de hallazgo real de code-review (H1): con límites
        # inclusivos por ambos lados y `as_of - timedelta(days=28)`, la
        # ventana daba 29 días reales en vez de 28. El día exactamente
        # 28 hacia atrás debe quedar FUERA de una ventana de 28 días
        # (la ventana correcta es [as_of-27, as_of]).
        hoy = date(2026, 8, 28)
        fuera_de_ventana = hoy - timedelta(days=28)
        dentro_de_ventana = hoy - timedelta(days=27)
        _fila = ReadinessLog(user_id=usuario.id, fecha=fuera_de_ventana, resultado="green")
        session.add(_fila)
        session.flush()
        _fila.volumen_pct_ajustado = 999
        session.add(ReadinessLog(user_id=usuario.id, fecha=dentro_de_ventana, resultado="green"))
        session.flush()
        session.query(ReadinessLog).filter_by(fecha=dentro_de_ventana).one().volumen_pct_ajustado = 50
        session.commit()

        historial = get_volumen_pct_history(session, usuario.id, as_of=hoy, days=28)
        assert historial == [(dentro_de_ventana, 50)]

    def test_una_fila_nueva_sin_volumen_no_borra_el_volumen_de_una_fila_anterior_el_mismo_dia(
        self, session, usuario
    ):
        # L2 de code-review: el docstring dice "la fila más reciente
        # CON VOLUMEN gana", no "la fila más reciente a secas" - un
        # re-check-in de recuperación posterior el mismo día, sin
        # volumen todavía, no debe borrar el dato ya calculado por
        # session_service antes.
        hoy = date(2026, 8, 10)
        con_volumen = ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="green")
        session.add(con_volumen)
        session.flush()
        con_volumen.volumen_pct_ajustado = 80
        session.commit()

        session.add(ReadinessLog(user_id=usuario.id, fecha=hoy, resultado="yellow"))
        session.commit()

        assert get_volumen_pct_history(session, usuario.id, as_of=hoy, days=28) == [(hoy, 80)]
