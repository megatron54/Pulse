"""Tests para repositories.garmin_repository — TDD.

Cubre las dos señales derivadas de historial que engine.periodization
necesita y que Garmin no da "ya calculadas": la línea base de HRV de 28
días y la tendencia de 7 días (ver 00-research/06-periodizacion-
ciencia-deportiva.md: "usar tendencia de 3-7 días vs baseline de 4-6
semanas, nunca el dato de un solo día").
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, GarminActivity, GarminDailyMetrics, UserProfile
from repositories.garmin_repository import (
    get_activity_history,
    get_hrv_baseline_28d,
    get_hrv_trend_7d,
    save_activity_if_new,
    save_daily_metrics,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def usuario(session):
    u = UserProfile(
        nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M"
    )
    session.add(u)
    session.commit()
    return u


def _sembrar_hrv(session, user_id, hoy, valores_por_dias_atras: dict[int, float]):
    """valores_por_dias_atras: {dias_atras: hrv_value}"""
    for dias_atras, valor in valores_por_dias_atras.items():
        session.add(
            GarminDailyMetrics(
                user_id=user_id, fecha=hoy - timedelta(days=dias_atras), hrv_value=valor
            )
        )
    session.commit()


class TestSaveDailyMetrics:
    def test_persiste_los_campos_normalizados_del_raw(self, session, usuario):
        raw = {
            "hrv_today": 65.0,
            "hrv_status": "BALANCED",
            "training_readiness": "high",
            "body_battery_am": 80,
            "sleep_score": 85,
            "stress_avg": 25,
            "resting_hr": 54,
            "vo2max": 47.5,
            "raw_json": {"hrv": {}, "sleep": {}},
        }
        fila = save_daily_metrics(session, usuario.id, date(2026, 8, 2), raw)
        assert fila.id is not None
        assert fila.hrv_value == 65.0
        assert fila.hrv_status == "BALANCED"
        assert fila.training_readiness == "high"
        assert fila.body_battery_am == 80
        assert fila.sleep_score == 85
        assert fila.stress_avg == 25
        assert fila.resting_hr == 54
        assert fila.vo2max == 47.5

    def test_campos_ausentes_en_el_raw_quedan_none_no_provocan_error(self, session, usuario):
        # Épica A (02-roadmap/03-vision-produccion.md): hrv_status,
        # vo2max, stress_avg y resting_hr son campos nuevos - un raw
        # que todavía no los traiga (p.ej. datos ya sincronizados antes
        # del fix) no debe romper la persistencia de los demás campos.
        fila = save_daily_metrics(session, usuario.id, date(2026, 8, 2), {"hrv_today": 60})
        assert fila.hrv_value == 60
        assert fila.hrv_status is None
        assert fila.stress_avg is None
        assert fila.resting_hr is None
        assert fila.vo2max is None

    def test_es_append_only_no_sobreescribe_sincronizaciones_previas(self, session, usuario):
        fecha = date(2026, 8, 2)
        save_daily_metrics(session, usuario.id, fecha, {"hrv_today": 60})
        save_daily_metrics(session, usuario.id, fecha, {"hrv_today": 62})
        filas = (
            session.query(GarminDailyMetrics)
            .filter_by(user_id=usuario.id, fecha=fecha)
            .all()
        )
        assert len(filas) == 2


class TestHrvBaseline28d:
    def test_calcula_media_de_los_ultimos_28_dias_excluyendo_hoy(self, session, usuario):
        hoy = date(2026, 8, 29)
        # 28 días con HRV=60, más un dato de hace 40 días (fuera de rango)
        # con un valor muy distinto que NO debe contaminar la media.
        valores = {i: 60.0 for i in range(1, 29)}
        valores[40] = 200.0
        _sembrar_hrv(session, usuario.id, hoy, valores)

        baseline = get_hrv_baseline_28d(session, usuario.id, hoy)
        assert baseline == pytest.approx(60.0, abs=0.01)

    def test_ignora_filas_sin_valor_de_hrv(self, session, usuario):
        hoy = date(2026, 8, 10)
        session.add(GarminDailyMetrics(user_id=usuario.id, fecha=hoy - timedelta(days=1), hrv_value=None))
        session.add(GarminDailyMetrics(user_id=usuario.id, fecha=hoy - timedelta(days=2), hrv_value=70.0))
        session.commit()
        baseline = get_hrv_baseline_28d(session, usuario.id, hoy)
        assert baseline == pytest.approx(70.0, abs=0.01)

    def test_devuelve_none_si_no_hay_historial_suficiente(self, session, usuario):
        assert get_hrv_baseline_28d(session, usuario.id, date(2026, 8, 10)) is None


class TestHrvTrend7d:
    def test_tendencia_positiva_si_hrv_sube_en_los_ultimos_7_dias(self, session, usuario):
        hoy = date(2026, 8, 10)
        valores = {7: 50.0, 6: 52.0, 5: 54.0, 4: 56.0, 3: 58.0, 2: 60.0, 1: 62.0}
        _sembrar_hrv(session, usuario.id, hoy, valores)
        trend = get_hrv_trend_7d(session, usuario.id, hoy)
        assert trend > 0

    def test_tendencia_negativa_si_hrv_baja_en_los_ultimos_7_dias(self, session, usuario):
        hoy = date(2026, 8, 10)
        valores = {7: 70.0, 6: 68.0, 5: 66.0, 4: 64.0, 3: 62.0, 2: 60.0, 1: 55.0}
        _sembrar_hrv(session, usuario.id, hoy, valores)
        trend = get_hrv_trend_7d(session, usuario.id, hoy)
        assert trend < 0

    def test_devuelve_none_si_no_hay_suficiente_historial(self, session, usuario):
        assert get_hrv_trend_7d(session, usuario.id, date(2026, 8, 10)) is None

    def test_devuelve_none_con_un_unico_valor_en_la_ventana(self, session, usuario):
        hoy = date(2026, 8, 10)
        _sembrar_hrv(session, usuario.id, hoy, {3: 60.0})
        assert get_hrv_trend_7d(session, usuario.id, hoy) is None

    def test_border_exacto_28_dias_dentro_29_fuera(self, session, usuario):
        hoy = date(2026, 8, 29)
        valores = {i: 60.0 for i in range(1, 29)}  # día 28: dentro
        _sembrar_hrv(session, usuario.id, hoy, valores)
        # Un valor claramente distinto justo en el borde de exclusión (29)
        session.add(
            GarminDailyMetrics(user_id=usuario.id, fecha=hoy - timedelta(days=29), hrv_value=999.0)
        )
        session.commit()
        baseline = get_hrv_baseline_28d(session, usuario.id, hoy)
        assert baseline == pytest.approx(60.0, abs=0.01)


class TestSaveActivityIfNew:
    def _actividad(self, **overrides):
        base = {
            "activity_id": "111",
            "fecha": date(2026, 8, 1),
            "tipo": "running",
            "duracion_seg": 1800,
            "distancia_m": 5000.0,
            "hr_avg": 150,
            "hr_max": 172,
            "training_effect": 3.2,
            "raw_json": {"activityId": 111},
        }
        base.update(overrides)
        return base

    def test_inserta_una_actividad_nueva_y_devuelve_true(self, session, usuario):
        insertada = save_activity_if_new(session, usuario.id, self._actividad())
        assert insertada is True
        filas = session.query(GarminActivity).filter_by(user_id=usuario.id).all()
        assert len(filas) == 1
        assert filas[0].activity_id == "111"

    def test_reintentar_la_misma_actividad_no_duplica_ni_lanza(self, session, usuario):
        # Idempotencia: reprocesar el mismo rango de sincronización (p.ej.
        # tras un fallo parcial de red) nunca debe duplicar filas.
        save_activity_if_new(session, usuario.id, self._actividad())
        insertada_de_nuevo = save_activity_if_new(session, usuario.id, self._actividad())

        assert insertada_de_nuevo is False
        assert session.query(GarminActivity).filter_by(user_id=usuario.id).count() == 1

    def test_el_mismo_activity_id_en_dos_usuarios_distintos_no_choca(self, session, usuario):
        # Garmin no garantiza que activity_id sea único entre cuentas
        # distintas de la app - la unicidad real es (user_id, activity_id).
        otro = UserProfile(
            nombre="Otro", altura_cm=170.0, fecha_nacimiento=date(1990, 1, 1), sexo="F"
        )
        session.add(otro)
        session.commit()

        save_activity_if_new(session, usuario.id, self._actividad())
        insertada = save_activity_if_new(session, otro.id, self._actividad())

        assert insertada is True
        assert session.query(GarminActivity).count() == 2


class TestGetActivityHistory:
    def test_devuelve_las_actividades_del_usuario_en_la_ventana_ordenadas(self, session, usuario):
        save_activity_if_new(session, usuario.id, self._actividad_de(session, usuario))
        historial = get_activity_history(session, usuario.id, as_of=date(2026, 8, 10), days=30)
        assert len(historial) == 1
        assert historial[0].activity_id == "111"

    def _actividad_de(self, session, usuario):
        return {
            "activity_id": "111",
            "fecha": date(2026, 8, 1),
            "tipo": "running",
            "duracion_seg": 1800,
            "distancia_m": 5000.0,
            "hr_avg": 150,
            "hr_max": 172,
            "training_effect": 3.2,
            "raw_json": {"activityId": 111},
        }

    def test_no_incluye_actividades_fuera_de_la_ventana(self, session, usuario):
        save_activity_if_new(
            session,
            usuario.id,
            {
                "activity_id": "222",
                "fecha": date(2026, 1, 1),
                "tipo": "cycling",
                "duracion_seg": 1200,
                "distancia_m": None,
                "hr_avg": None,
                "hr_max": None,
                "training_effect": None,
                "raw_json": {},
            },
        )
        historial = get_activity_history(session, usuario.id, as_of=date(2026, 8, 10), days=30)
        assert historial == []
