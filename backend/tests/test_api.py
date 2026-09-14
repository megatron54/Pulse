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
from models.schema import Base, WeeklySchedule


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
    cliente = TestClient(app)
    # Para los pocos tests que necesitan comprobar en la BD un efecto
    # que la API no expone por ningún endpoint (p. ej. que borrar un
    # bloque borre también sus filas de WeeklySchedule, que no se
    # pueden leer de vuelta).
    cliente.engine_de_test = engine
    yield cliente
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
        # El tope subió de 730 días a 10 años: el usuario pidió ver el
        # historial completo ("I want full info, not just last 90 days")
        # y con 730 la app no podía pedir las 275 pesadas importadas de
        # la báscula. Sigue habiendo tope, solo que más arriba.
        resp = client.get(
            f"/users/{usuario['id']}/body-measurements/history", params={"days": 731}
        )
        assert resp.status_code == 200
        resp = client.get(
            f"/users/{usuario['id']}/body-measurements/history", params={"days": 3651}
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

    def test_training_readiness_null_es_valido_relojes_que_no_lo_calculan(self, client):
        # Regresión Fase H: dispositivos como el Forerunner 165 nunca
        # calculan Training Readiness - el check-in manual no debe
        # obligar a inventar un valor que el usuario no puede medir.
        usuario = _crear_usuario(client)
        resp = client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "training_readiness": None,
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["resultado"] == "green"

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
        cuerpo = resp.json()
        # El frontend distingue cada caso por `motivo` para decir qué
        # hacer; sin código propio, "planes solapados" caía en el mismo
        # mensaje genérico y sin acción que "falta algún dato".
        assert cuerpo["motivo"] == "planes_solapados"
        # Doctrina 8: el `detail` es texto de interfaz. Antes decía
        # "user_id=4 tiene múltiples TrainingBlock activos y solapados".
        for jerga in ("TrainingBlock", "user_id"):
            assert jerga not in cuerpo["detail"]


class TestListarYBorrarTrainingBlocks:
    """El mensaje de bloques solapados le pide al usuario dejar solo un
    plan activo; sin listar ni borrar desde la API, eso solo se podía
    hacer entrando a la base de datos a mano."""

    def _crear_bloque(self, client, user_id, fecha_inicio, fecha_fin, objetivo="strength"):
        resp = client.post(
            f"/users/{user_id}/training-blocks",
            json={
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "objetivo_prioritario": objetivo,
                "weekly_schedule": {"mon": "strength_heavy"},
            },
        )
        assert resp.status_code == 201
        return resp.json()

    def test_lista_los_bloques_del_mas_reciente_al_mas_antiguo(self, client):
        usuario = _crear_usuario(client)
        self._crear_bloque(client, usuario["id"], "2026-07-01", "2026-07-28", "endurance")
        self._crear_bloque(client, usuario["id"], "2026-08-01", "2026-09-12", "strength")

        resp = client.get(f"/users/{usuario['id']}/training-blocks")

        assert resp.status_code == 200
        assert [b["objetivo_prioritario"] for b in resp.json()] == ["strength", "endurance"]

    def test_lista_vacia_si_no_hay_ningun_plan(self, client):
        usuario = _crear_usuario(client)
        assert client.get(f"/users/{usuario['id']}/training-blocks").json() == []

    def test_no_lista_los_planes_de_otro_usuario(self, client):
        usuario = _crear_usuario(client)
        otro = _crear_usuario(client)
        self._crear_bloque(client, otro["id"], "2026-08-01", "2026-09-12")

        assert client.get(f"/users/{usuario['id']}/training-blocks").json() == []

    def test_borrar_uno_de_dos_solapados_desbloquea_la_sesion_del_dia(self, client):
        """La razón de existir del borrado: el usuario resuelve el
        solapamiento y la sesión de hoy vuelve a poder calcularse."""
        usuario = _crear_usuario(client)
        self._crear_bloque(client, usuario["id"], "2026-08-01", "2026-09-12")
        sobrante = self._crear_bloque(client, usuario["id"], "2026-08-01", "2026-09-12")
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

        assert (
            client.delete(f"/users/{usuario['id']}/training-blocks/{sobrante['id']}").status_code
            == 204
        )

        resp = client.post(
            f"/users/{usuario['id']}/session/daily", json={"target_date": "2026-08-03"}
        )
        assert resp.status_code == 200
        assert resp.json()["session_type"] == "strength_heavy"

    def test_borrar_un_bloque_borra_tambien_su_plan_semanal(self, client):
        # La FK de WeeklySchedule no declara ON DELETE CASCADE: si el
        # router no las borra, quedan filas de plan semanal apuntando a
        # un bloque que ya no existe.
        usuario = _crear_usuario(client)
        bloque = self._crear_bloque(client, usuario["id"], "2026-08-01", "2026-09-12")

        client.delete(f"/users/{usuario['id']}/training-blocks/{bloque['id']}")

        with Session(client.engine_de_test) as s:
            assert s.query(WeeklySchedule).filter_by(training_block_id=bloque["id"]).count() == 0

    def test_borrar_un_bloque_inexistente_da_404(self, client):
        usuario = _crear_usuario(client)
        assert (
            client.delete(f"/users/{usuario['id']}/training-blocks/9999").status_code == 404
        )

    def test_no_se_puede_borrar_el_plan_de_otro_usuario(self, client):
        # Sin filtrar por user_id en el DELETE, poner otro id en la URL
        # borraba un plan ajeno.
        usuario = _crear_usuario(client)
        otro = _crear_usuario(client)
        ajeno = self._crear_bloque(client, otro["id"], "2026-08-01", "2026-09-12")

        resp = client.delete(f"/users/{usuario['id']}/training-blocks/{ajeno['id']}")

        assert resp.status_code == 404
        assert len(client.get(f"/users/{otro['id']}/training-blocks").json()) == 1


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

    def test_cada_dia_trae_el_desglose_por_senal_que_explica_su_veredicto(self, client):
        """El caso real que el usuario no entendía: veredicto ROJO con la
        VFC de hoy POR ENCIMA de su media. La señal que lo decidía era
        la tendencia de 7 días, que no salía por la API y por tanto no
        aparecía en ninguna pantalla."""
        usuario = _crear_usuario(client)
        client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 69.0,
                "hrv_baseline_28d": 59.3,  # VFC de hoy un 16% POR ENCIMA
                "hrv_trend_7d": -0.19,  # ...pero la semana cayendo
                "body_battery_am": 80,
                "training_readiness": "high",
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )

        dia = client.get(
            f"/users/{usuario['id']}/readiness/history",
            params={"as_of": "2026-08-02", "days": 1},
        ).json()[0]

        assert dia["resultado"] == "red"
        assert dia["hrv_trend_7d"] == pytest.approx(-0.19)
        por_senal = {s["senal"]: s for s in dia["senales"]}
        # La que está mal, y la que está bien: sin las dos, la pantalla
        # no puede decir cuál mirar.
        assert por_senal["hrv_trend"]["estado"] == "red"
        assert por_senal["hrv_delta"]["estado"] == "ok"
        assert por_senal["body_battery"]["estado"] == "ok"
        # Los umbrales viajan con la señal para que el cliente no los
        # repita por su cuenta.
        assert por_senal["body_battery"]["umbral_rojo"] == 30
        assert por_senal["acwr"]["peor_hacia"] == "arriba"

    def test_una_senal_que_el_reloj_no_mide_llega_como_sin_dato(self, client):
        # Varios Garmin de gama media no calculan Training Readiness:
        # eso no es "moderado", es que no hay dato (doctrina 6).
        usuario = _crear_usuario(client)
        client.post(
            f"/users/{usuario['id']}/readiness/manual-checkin",
            json={
                "target_date": "2026-08-02",
                "hrv_today": 65.0,
                "hrv_baseline_28d": 65.0,
                "hrv_trend_7d": 0.0,
                "body_battery_am": 80,
                "sleep_score": 85,
                "acwr": 1.0,
                "joint_pain_flag": False,
            },
        )

        dia = client.get(
            f"/users/{usuario['id']}/readiness/history",
            params={"as_of": "2026-08-02", "days": 1},
        ).json()[0]

        por_senal = {s["senal"]: s["estado"] for s in dia["senales"]}
        assert por_senal["training_readiness"] == "unknown"
        assert dia["resultado"] == "green"  # el resto de señales deciden solas

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

    def test_el_400_incluye_un_motivo_legible_por_maquina(self, client):
        """La interfaz necesita distinguir "falta sincronizar Garmin" de
        "falta crear un plan", porque la acción que debe ofrecer es
        distinta. El `detail` está escrito para los logs; `motivo` es el
        contrato estable con el cliente."""
        usuario = _crear_usuario(client)

        sin_recovery = client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-02", "planned_session": "strength_heavy"},
        )
        assert sin_recovery.status_code == 400
        assert sin_recovery.json()["motivo"] == "sin_recovery"

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
        # Sin `planned_session` y sin plan semanal activo: la otra rama.
        sin_plan = client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-02"},
        )
        assert sin_plan.status_code == 400
        assert sin_plan.json()["motivo"] == "sin_plan"

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


class TestTrainingLoad:
    def test_sin_historial_devuelve_datos_insuficientes(self, client):
        usuario = _crear_usuario(client)
        resp = client.get(f"/users/{usuario['id']}/session/training-load")
        assert resp.status_code == 200
        body = resp.json()
        assert body["datos_suficientes"] is False
        assert body["acwr"] is None

    def test_tras_calcular_una_sesion_el_volumen_queda_en_el_historial(self, client):
        # Regresión end-to-end: crear readiness -> pedir sesión (que
        # ahora persiste volume_pct) -> el endpoint de carga ya ve ese día.
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
        client.post(
            f"/users/{usuario['id']}/session/daily",
            json={"target_date": "2026-08-02", "planned_session": "strength_heavy"},
        )
        resp = client.get(
            f"/users/{usuario['id']}/session/training-load", params={"as_of": "2026-08-02"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["acute_avg_7d"] == 100.0
        assert body["chronic_avg_28d"] == 100.0
        assert body["acwr"] == 1.0
