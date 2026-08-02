"""Tests para models.schema — TDD: escritos antes que la implementación.

Verifica el esquema de datos descrito en docs/01-arquitectura/03-modelo-
datos.md: creación de tablas, principio "append-only" (nunca se
sobreescriben mediciones/logs pasados - se comprueba insertando múltiples
filas para la misma fecha/usuario y verificando que todas persisten), y
las restricciones básicas de cada tabla.

Se usa SQLite en memoria (rápido, sin dependencia de Docker) para el
suite de tests. La base de datos real de desarrollo es PostgreSQL
(infra/docker-compose.pulse.yml, puerto 5433) - el mismo motor de
producción, por lo que SQLite es válido para verificar el esquema en CI
sin renunciar a Postgres en local (ver models/database.py).
"""
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import (
    AuditLog,
    Base,
    BodyMeasurements,
    CoachConversation,
    GarminActivity,
    GarminDailyMetrics,
    NutritionLog,
    ProgressPhoto,
    ReadinessLog,
    TrainingBlock,
    UserProfile,
    WeeklySchedule,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _crear_usuario(session, **overrides):
    defaults = dict(
        nombre="Test User",
        altura_cm=180.0,
        fecha_nacimiento=date(1995, 1, 1),
        sexo="M",
        fase_peso_actual="maintenance",
    )
    defaults.update(overrides)
    usuario = UserProfile(**defaults)
    session.add(usuario)
    session.commit()
    return usuario


class TestUserProfile:
    def test_crea_perfil_de_usuario(self, session):
        usuario = _crear_usuario(session)
        assert usuario.id is not None
        assert usuario.fase_peso_actual == "maintenance"

    def test_objetivos_activos_se_guardan_como_json(self, session):
        usuario = _crear_usuario(
            session,
            objetivos_activos=[
                {"tipo": "fuerza", "prioridad": 1},
                {"tipo": "running", "prioridad": 2},
            ],
        )
        session.refresh(usuario)
        assert usuario.objetivos_activos[0]["tipo"] == "fuerza"

    def test_rechaza_fase_peso_invalida(self, session):
        with pytest.raises(Exception):
            usuario = UserProfile(
                nombre="X",
                altura_cm=180.0,
                fecha_nacimiento=date(1995, 1, 1),
                sexo="M",
                fase_peso_actual="fase_inexistente",
            )
            session.add(usuario)
            session.commit()

    def test_default_json_no_comparte_estado_mutable_entre_instancias(self, session):
        # Trampa clásica: si default=[] fuera un único objeto compartido
        # (en vez de una fábrica por instancia), modificar los objetivos
        # de un usuario contaminaría los de otro.
        u1 = _crear_usuario(session, nombre="U1")
        u2 = _crear_usuario(session, nombre="U2")
        u1.objetivos_activos.append({"tipo": "fuerza", "prioridad": 1})
        session.commit()
        session.refresh(u2)
        assert u2.objetivos_activos == []


class TestGarminDailyMetricsAppendOnly:
    def test_permite_multiples_filas_para_la_misma_fecha(self, session):
        # Append-only: si Garmin se re-sincroniza el mismo día (ej. tras
        # un fallo parcial), NO se sobreescribe el registro anterior -
        # se añade una fila nueva con su propio timestamp de ingesta.
        usuario = _crear_usuario(session)
        fecha = date(2026, 8, 1)
        m1 = GarminDailyMetrics(
            user_id=usuario.id, fecha=fecha, hrv_value=65.0, sleep_score=80
        )
        m2 = GarminDailyMetrics(
            user_id=usuario.id, fecha=fecha, hrv_value=63.0, sleep_score=82
        )
        session.add_all([m1, m2])
        session.commit()

        filas = (
            session.query(GarminDailyMetrics)
            .filter_by(user_id=usuario.id, fecha=fecha)
            .all()
        )
        assert len(filas) == 2

    def test_ingested_at_se_asigna_automaticamente(self, session):
        usuario = _crear_usuario(session)
        m = GarminDailyMetrics(user_id=usuario.id, fecha=date(2026, 8, 1))
        session.add(m)
        session.commit()
        session.refresh(m)
        assert isinstance(m.ingested_at, datetime)


class TestBodyMeasurements:
    def test_guarda_rango_de_bodyfat_no_solo_un_numero(self, session):
        usuario = _crear_usuario(session)
        medida = BodyMeasurements(
            user_id=usuario.id,
            fecha=date(2026, 8, 1),
            peso_kg=80.0,
            bodyfat_pct_rango_min=18.0,
            bodyfat_pct_rango_max=22.0,
            metodo="navy",
        )
        session.add(medida)
        session.commit()
        session.refresh(medida)
        assert medida.bodyfat_pct_rango_min < medida.bodyfat_pct_rango_max

    def test_metodo_por_defecto_es_manual(self, session):
        usuario = _crear_usuario(session)
        medida = BodyMeasurements(user_id=usuario.id, fecha=date(2026, 8, 1), peso_kg=80.0)
        session.add(medida)
        session.commit()
        session.refresh(medida)
        assert medida.metodo == "manual"

    def test_permite_multiples_filas_para_la_misma_fecha(self, session):
        usuario = _crear_usuario(session)
        fecha = date(2026, 8, 1)
        session.add_all(
            [
                BodyMeasurements(user_id=usuario.id, fecha=fecha, peso_kg=80.0),
                BodyMeasurements(user_id=usuario.id, fecha=fecha, peso_kg=79.8),
            ]
        )
        session.commit()
        filas = session.query(BodyMeasurements).filter_by(user_id=usuario.id, fecha=fecha).all()
        assert len(filas) == 2

    def test_rechaza_metodo_invalido(self, session):
        usuario = _crear_usuario(session)
        with pytest.raises(Exception):
            medida = BodyMeasurements(
                user_id=usuario.id, fecha=date(2026, 8, 1), peso_kg=80.0, metodo="rayos_x"
            )
            session.add(medida)
            session.commit()


class TestReadinessLogAppendOnly:
    def test_una_fila_por_dia_con_resultado_del_semaforo(self, session):
        usuario = _crear_usuario(session)
        log = ReadinessLog(
            user_id=usuario.id,
            fecha=date(2026, 8, 1),
            hrv_delta_pct=-0.05,
            training_readiness="high",
            acwr=1.1,
            resultado="green",
            sesion_recomendada="strength_heavy",
            volumen_pct_ajustado=100,
        )
        session.add(log)
        session.commit()
        assert log.resultado == "green"

    def test_permite_multiples_filas_para_la_misma_fecha(self, session):
        usuario = _crear_usuario(session)
        fecha = date(2026, 8, 1)
        session.add_all(
            [
                ReadinessLog(user_id=usuario.id, fecha=fecha, resultado="green"),
                ReadinessLog(user_id=usuario.id, fecha=fecha, resultado="yellow"),
            ]
        )
        session.commit()
        filas = session.query(ReadinessLog).filter_by(user_id=usuario.id, fecha=fecha).all()
        assert len(filas) == 2

    def test_rechaza_resultado_invalido(self, session):
        usuario = _crear_usuario(session)
        with pytest.raises(Exception):
            log = ReadinessLog(user_id=usuario.id, fecha=date(2026, 8, 1), resultado="naranja")
            session.add(log)
            session.commit()


class TestNutritionLog:
    def test_registra_fuente_del_dato(self, session):
        usuario = _crear_usuario(session)
        entrada = NutritionLog(
            user_id=usuario.id,
            fecha=date(2026, 8, 1),
            comida="desayuno",
            fuente="foto_ia",
            alimentos=[{"nombre": "avena", "gramos": 80}],
            kcal_estimadas=350,
            confirmado_por_usuario=False,
        )
        session.add(entrada)
        session.commit()
        assert entrada.confirmado_por_usuario is False

    def test_permite_multiples_filas_para_la_misma_fecha(self, session):
        usuario = _crear_usuario(session)
        fecha = date(2026, 8, 1)
        session.add_all(
            [
                NutritionLog(user_id=usuario.id, fecha=fecha, comida="desayuno", fuente="manual"),
                NutritionLog(user_id=usuario.id, fecha=fecha, comida="comida", fuente="manual"),
            ]
        )
        session.commit()
        filas = session.query(NutritionLog).filter_by(user_id=usuario.id, fecha=fecha).all()
        assert len(filas) == 2

    def test_rechaza_fuente_invalida(self, session):
        usuario = _crear_usuario(session)
        with pytest.raises(Exception):
            entrada = NutritionLog(
                user_id=usuario.id, fecha=date(2026, 8, 1), comida="desayuno", fuente="telepatia"
            )
            session.add(entrada)
            session.commit()


class TestAuditLogTrazabilidad:
    def test_guarda_la_decision_completa_del_motor_de_reglas(self, session):
        usuario = _crear_usuario(session)
        entrada = AuditLog(
            user_id=usuario.id,
            modulo="periodization",
            inputs_json={"hrv_today": 60, "hrv_baseline_28d": 65},
            regla_disparada="hrv_delta_yellow",
            output="YELLOW",
            decision_final="strength_hyper@65%",
        )
        session.add(entrada)
        session.commit()
        assert entrada.modulo == "periodization"
        assert entrada.user_id == usuario.id
        assert isinstance(entrada.timestamp, datetime)


class TestTrainingBlockYCoachConversation:
    def test_training_block_guarda_objetivos_de_mantenimiento_como_json(self, session):
        usuario = _crear_usuario(session)
        bloque = TrainingBlock(
            user_id=usuario.id,
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 9, 12),
            objetivo_prioritario="strength",
            objetivos_mantenimiento=["running", "bjj"],
            semana_actual=1,
            es_deload=False,
        )
        session.add(bloque)
        session.commit()
        assert "bjj" in bloque.objetivos_mantenimiento

    def test_weekly_schedule_asigna_session_type_por_dia(self, session):
        usuario = _crear_usuario(session)
        bloque = TrainingBlock(
            user_id=usuario.id,
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 9, 12),
            objetivo_prioritario="strength",
        )
        session.add(bloque)
        session.commit()

        entrada = WeeklySchedule(
            training_block_id=bloque.id, dia_semana="mon", session_type="strength_heavy"
        )
        session.add(entrada)
        session.commit()
        assert entrada.session_type == "strength_heavy"

    def test_weekly_schedule_rechaza_dia_duplicado_para_el_mismo_bloque(self, session):
        usuario = _crear_usuario(session)
        bloque = TrainingBlock(
            user_id=usuario.id,
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 9, 12),
            objetivo_prioritario="strength",
        )
        session.add(bloque)
        session.commit()

        session.add(
            WeeklySchedule(
                training_block_id=bloque.id, dia_semana="mon", session_type="strength_heavy"
            )
        )
        session.commit()
        session.add(
            WeeklySchedule(
                training_block_id=bloque.id, dia_semana="mon", session_type="rest"
            )
        )
        with pytest.raises(Exception):
            session.commit()

    def test_weekly_schedule_rechaza_dia_semana_invalido(self, session):
        usuario = _crear_usuario(session)
        bloque = TrainingBlock(
            user_id=usuario.id,
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 9, 12),
            objetivo_prioritario="strength",
        )
        session.add(bloque)
        session.commit()
        with pytest.raises(Exception):
            entrada = WeeklySchedule(
                training_block_id=bloque.id, dia_semana="lunes", session_type="strength_heavy"
            )
            session.add(entrada)
            session.commit()

    def test_coach_conversation_referencia_opcional_a_decision(self, session):
        usuario = _crear_usuario(session)
        mensaje = CoachConversation(
            user_id=usuario.id,
            thread_id="t1",
            rol="coach",
            mensaje="Hoy toca volumen reducido porque tu HRV bajó.",
            modelo_usado="gemini-1.5-flash",
        )
        session.add(mensaje)
        session.commit()
        assert mensaje.decision_tipada_asociada is None


class TestGarminActivityYProgressPhoto:
    def test_garmin_activity_conserva_raw_json(self, session):
        usuario = _crear_usuario(session)
        actividad = GarminActivity(
            user_id=usuario.id,
            activity_id="12345",
            fecha=date(2026, 8, 1),
            tipo="running",
            duracion_seg=1800,
            raw_json={"distance": 5000},
        )
        session.add(actividad)
        session.commit()
        assert actividad.raw_json["distance"] == 5000

    def test_garmin_activity_permite_multiples_filas_para_la_misma_fecha(self, session):
        usuario = _crear_usuario(session)
        fecha = date(2026, 8, 1)
        session.add_all(
            [
                GarminActivity(user_id=usuario.id, activity_id="1", fecha=fecha, tipo="running"),
                GarminActivity(user_id=usuario.id, activity_id="2", fecha=fecha, tipo="strength"),
            ]
        )
        session.commit()
        filas = session.query(GarminActivity).filter_by(user_id=usuario.id, fecha=fecha).all()
        assert len(filas) == 2

    def test_progress_photo_guarda_landmarks_no_la_imagen(self, session):
        # Privacidad: la foto vive cifrada en el dispositivo; aquí solo
        # se persiste la ruta local cifrada y los landmarks de MediaPipe,
        # nunca la imagen en sí (ver 00-research/05-analisis-corporal-foto.md).
        # Aserto real sobre el ESQUEMA (no sobre la instancia): no existe
        # ninguna columna que pueda almacenar la imagen.
        columnas = set(ProgressPhoto.__table__.columns.keys())
        assert "imagen" not in columnas
        assert "photo_bytes" not in columnas
        assert "landmarks_json" in columnas
        assert "ruta_cifrada_local" in columnas

        usuario = _crear_usuario(session)
        foto = ProgressPhoto(
            user_id=usuario.id,
            fecha=date(2026, 8, 1),
            angulo="frontal",
            ruta_cifrada_local="/local/encrypted/abc.enc",
            landmarks_json={"nose": [0.5, 0.3]},
        )
        session.add(foto)
        session.commit()
        assert foto.landmarks_json["nose"] == [0.5, 0.3]

    def test_progress_photo_rechaza_angulo_invalido(self, session):
        usuario = _crear_usuario(session)
        with pytest.raises(Exception):
            foto = ProgressPhoto(
                user_id=usuario.id,
                fecha=date(2026, 8, 1),
                angulo="arriba",
                ruta_cifrada_local="/local/encrypted/abc.enc",
            )
            session.add(foto)
            session.commit()
