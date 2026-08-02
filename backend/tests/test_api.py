"""Tests de integración de la API REST (Fase A del plan autónomo).

Capa fina sobre services/* ya probados: aquí se verifica sobre todo el
cableado HTTP (rutas, códigos de estado, mapeo de errores), no la
lógica de negocio en sí (ya cubierta en test_*_service.py).

Base de datos: SQLite en memoria compartida entre requests de un mismo
test vía StaticPool (patrón estándar de testing de FastAPI+SQLAlchemy).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from models.schema import Base


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _crear_usuario(client, sexo="M", fase_peso_actual="maintenance"):
    resp = client.post(
        "/users",
        json={
            "nombre": "Test",
            "altura_cm": 180.0,
            "fecha_nacimiento": "1995-01-01",
            "sexo": sexo,
            "fase_peso_actual": fase_peso_actual,
        },
    )
    assert resp.status_code == 201
    return resp.json()


class TestHealth:
    def test_health_devuelve_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAuth:
    """Verifica el comportamiento fail-closed de verify_api_key
    (ver api/dependencies.py): sin PULSE_API_KEY y sin PULSE_ENV, el
    modo dev implícito permite el acceso; con PULSE_API_KEY configurada,
    exige el header correcto; fuera de dev sin key configurada, falla
    ruidosamente (500) en vez de quedar abierto en silencio."""

    def test_sin_api_key_configurada_permite_acceso_en_dev(self, client, monkeypatch):
        monkeypatch.delenv("PULSE_API_KEY", raising=False)
        monkeypatch.delenv("PULSE_ENV", raising=False)
        resp = client.get("/health")  # /health no requiere auth, pero /users sí
        assert resp.status_code == 200
        resp = client.get("/users/1")
        assert resp.status_code == 404  # pasó la auth, llegó a "no existe"

    def test_con_api_key_configurada_rechaza_key_incorrecta(self, client, monkeypatch):
        monkeypatch.setenv("PULSE_API_KEY", "secreto-correcto")
        resp = client.get("/users/1", headers={"X-API-Key": "incorrecta"})
        assert resp.status_code == 401

    def test_con_api_key_configurada_acepta_key_correcta(self, client, monkeypatch):
        monkeypatch.setenv("PULSE_API_KEY", "secreto-correcto")
        resp = client.get("/users/1", headers={"X-API-Key": "secreto-correcto"})
        assert resp.status_code == 404  # pasó la auth, llegó a "no existe"

    def test_fuera_de_dev_sin_api_key_falla_cerrado(self, client, monkeypatch):
        monkeypatch.setenv("PULSE_ENV", "production")
        monkeypatch.delenv("PULSE_API_KEY", raising=False)
        resp = client.get("/users/1")
        assert resp.status_code == 500


class TestUsers:
    def test_crea_y_obtiene_usuario(self, client):
        usuario = _crear_usuario(client)
        resp = client.get(f"/users/{usuario['id']}")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Test"

    def test_obtener_usuario_inexistente_da_404(self, client):
        resp = client.get("/users/9999")
        assert resp.status_code == 404

    def test_rechaza_sexo_invalido_con_422(self, client):
        resp = client.post(
            "/users",
            json={
                "nombre": "X",
                "altura_cm": 180.0,
                "fecha_nacimiento": "1995-01-01",
                "sexo": "Z",
            },
        )
        assert resp.status_code == 422

    def test_rechaza_fase_peso_invalida_con_422(self, client):
        resp = client.post(
            "/users",
            json={
                "nombre": "X",
                "altura_cm": 180.0,
                "fecha_nacimiento": "1995-01-01",
                "sexo": "M",
                "fase_peso_actual": "no_existe",
            },
        )
        assert resp.status_code == 422


class TestBodyMeasurements:
    def test_registra_peso_sin_medidas(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/body-measurements",
            json={"target_date": "2026-08-02", "peso_kg": 80.0},
        )
        assert resp.status_code == 201
        assert resp.json()["metodo"] == "manual"

    def test_registra_con_medidas_calcula_navy(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/body-measurements",
            json={
                "target_date": "2026-08-02",
                "peso_kg": 80.0,
                "cuello_cm": 38.1,
                "cintura_cm": 86.36,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["metodo"] == "navy"
        assert body["bodyfat_pct_rango_min"] is not None

    def test_usuario_inexistente_da_404(self, client):
        resp = client.post(
            "/users/9999/body-measurements",
            json={"target_date": "2026-08-02", "peso_kg": 80.0},
        )
        assert resp.status_code == 404


class TestBodyMeasurementHistory:
    def test_devuelve_historial_en_orden_cronologico(self, client):
        usuario = _crear_usuario(client)
        client.post(
            f"/users/{usuario['id']}/body-measurements",
            json={"target_date": "2026-07-01", "peso_kg": 82.0},
        )
        client.post(
            f"/users/{usuario['id']}/body-measurements",
            json={"target_date": "2026-08-01", "peso_kg": 80.0},
        )
        resp = client.get(
            f"/users/{usuario['id']}/body-measurements/history",
            params={"as_of": "2026-08-02", "days": 90},
        )
        assert resp.status_code == 200
        pesos = [m["peso_kg"] for m in resp.json()]
        assert pesos == [82.0, 80.0]

    def test_lista_vacia_sin_historial(self, client):
        usuario = _crear_usuario(client)
        resp = client.get(f"/users/{usuario['id']}/body-measurements/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_dias_fuera_de_rango_da_422(self, client):
        usuario = _crear_usuario(client)
        resp = client.get(
            f"/users/{usuario['id']}/body-measurements/history", params={"days": 0}
        )
        assert resp.status_code == 422
        resp = client.get(
            f"/users/{usuario['id']}/body-measurements/history", params={"days": 731}
        )
        assert resp.status_code == 422

    def test_usuario_inexistente_devuelve_lista_vacia_no_404(self, client):
        # Decisión deliberada (no accidental): este endpoint de solo
        # lectura no valida existencia del usuario, a diferencia de los
        # endpoints de escritura - no hay nada que filtrar/exponer, así
        # que un usuario inexistente da 200 [] en vez de 404. Fijado
        # aquí como contrato explícito, no como comportamiento implícito.
        resp = client.get("/users/9999/body-measurements/history")
        assert resp.status_code == 200
        assert resp.json() == []


class TestNutrition:
    def test_calcula_objetivo_diario(self, client):
        usuario = _crear_usuario(client)
        client.post(
            f"/users/{usuario['id']}/body-measurements",
            json={"target_date": "2026-07-01", "peso_kg": 80.0},
        )
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/daily-target",
            json={"target_date": "2026-08-02", "factor_actividad": 1.55},
        )
        assert resp.status_code == 200
        assert resp.json()["kcal_objetivo"] > 0

    def test_sin_peso_registrado_da_400(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/nutrition/daily-target",
            json={"target_date": "2026-08-02"},
        )
        assert resp.status_code == 400

    def test_usuario_inexistente_da_404(self, client):
        resp = client.post(
            "/users/9999/nutrition/daily-target",
            json={"target_date": "2026-08-02"},
        )
        assert resp.status_code == 404


class TestReadinessManualCheckin:
    def test_checkin_manual_persiste_y_devuelve_resultado(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["resultado"] == "green"

    def test_dolor_articular_fuerza_red(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": True,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["resultado"] == "red"

    def test_training_readiness_invalido_da_422(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "excelente",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        assert resp.status_code == 422

    def test_usuario_inexistente_da_404(self, client):
        resp = client.post(
            "/users/9999/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        assert resp.status_code == 404

    def test_sleep_score_fuera_de_rango_da_422(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 999,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        assert resp.status_code == 422


class TestTrainingBlocks:
    def test_crea_bloque_con_weekly_schedule(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/training-blocks",
            json={
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-09-12",
                "objetivo_prioritario": "strength",
                "objetivos_mantenimiento": ["running"],
                "weekly_schedule": {"mon": "strength_heavy", "wed": "endurance_intervals"},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["objetivo_prioritario"] == "strength"

    def test_usuario_inexistente_da_404(self, client):
        resp = client.post(
            "/users/9999/training-blocks",
            json={
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-09-12",
                "objetivo_prioritario": "strength",
            },
        )
        assert resp.status_code == 404

    def test_dia_semana_invalido_da_422(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/training-blocks",
            json={
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-09-12",
                "objetivo_prioritario": "strength",
                "weekly_schedule": {"lunes": "strength_heavy"},
            },
        )
        assert resp.status_code == 422

    def test_flujo_completo_plan_semanal_auto_deriva_sesion_del_dia(self, client):
        # End-to-end: crear bloque -> check-in -> sesión SIN planned_session
        # explícito -> se deriva automáticamente del plan semanal (Fase F).
        usuario = _crear_usuario(client)
        client.post(
            f"/users/{usuario['id']}/training-blocks",
            json={
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-09-12",
                "objetivo_prioritario": "strength",
                "weekly_schedule": {"mon": "strength_heavy"},
            },
        )
        client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-03",  # lunes
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        resp = client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-03"},  # sin planned_session
        )
        assert resp.status_code == 200
        assert resp.json()["session_type"] == "strength_heavy"

    def test_bloques_solapados_da_400_no_500(self, client):
        # Regresión del hallazgo de code-review: bloques solapados deben
        # dar un error de dominio claro (400), nunca un 500 opaco por
        # una excepción cruda de SQLAlchemy sin mapear.
        usuario = _crear_usuario(client)
        for _ in range(2):
            client.post(
                f"/users/{usuario['id']}/training-blocks",
                json={
                    "fecha_inicio": "2026-08-01",
                    "fecha_fin": "2026-09-12",
                    "objetivo_prioritario": "strength",
                    "weekly_schedule": {"mon": "strength_heavy"},
                },
            )
        client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-03",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        resp = client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-03"},
        )
        assert resp.status_code == 400


class TestReadinessHistory:
    def test_devuelve_historial_incluyendo_hoy(self, client):
        usuario = _crear_usuario(client)
        client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-01",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 40,
                "training_readiness": "moderate",
                "sleep_score": 40,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        resp = client.get(
            f"/users/{usuario['id']}/readiness/history",
            params={"as_of": "2026-08-02", "days": 30},
        )
        assert resp.status_code == 200
        resultados = [r["resultado"] for r in resp.json()]
        assert resultados == ["yellow", "green"]

    def test_lista_vacia_sin_historial(self, client):
        usuario = _crear_usuario(client)
        resp = client.get(f"/users/{usuario['id']}/readiness/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_dias_fuera_de_rango_da_422(self, client):
        usuario = _crear_usuario(client)
        resp = client.get(f"/users/{usuario['id']}/readiness/history", params={"days": 0})
        assert resp.status_code == 422
        resp = client.get(f"/users/{usuario['id']}/readiness/history", params={"days": 366})
        assert resp.status_code == 422

    def test_usuario_inexistente_devuelve_lista_vacia_no_404(self, client):
        # Misma decisión deliberada que en body-measurements/history.
        resp = client.get("/users/9999/readiness/history")
        assert resp.status_code == 200
        assert resp.json() == []


class TestDailySession:
    def test_flujo_completo_readiness_luego_sesion(self, client):
        usuario = _crear_usuario(client)
        client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        resp = client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-02", "planned_session": "strength_heavy"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_type"] == "strength_heavy"
        assert body["volume_pct"] == 100
        assert body["narrative_source"] == "template"  # sin GEMINI_API_KEY en tests
        assert body["narrative_text"]

    def test_sin_readiness_previo_da_400(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-02", "planned_session": "strength_heavy"},
        )
        assert resp.status_code == 400

    def test_usuario_inexistente_da_404(self, client):
        resp = client.post(
            "/users/9999/session/daily",
            json={"target_date": "2026-08-02", "planned_session": "strength_heavy"},
        )
        assert resp.status_code == 404

    def test_planned_session_invalido_da_422(self, client):
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-02", "planned_session": "no_existe"},
        )
        assert resp.status_code == 422
