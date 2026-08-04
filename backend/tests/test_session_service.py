"""Tests para services.session_service — TDD.

Conecta: ReadinessLog (ya persistido por services.readiness_service) ->
repositories.training_block_repository (deriva planned_session del plan
semanal activo si no se pasa explícito) -> engine.periodization.decide_session
(Capa 1) + engine.guardrails (deload forzado por ACWR sostenido,
descanso forzado pre-competición) -> AuditLog.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from engine.periodization import SessionType
from models.schema import AuditLog, Base, ReadinessLog, TrainingBlock, UserProfile, WeeklySchedule
from services.session_service import compute_daily_session


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


def _sembrar_readiness(session, user_id, fecha, resultado):
    session.add(ReadinessLog(user_id=user_id, fecha=fecha, resultado=resultado))
    session.commit()


def _crear_bloque_con_schedule(session, user_id, fecha_inicio, fecha_fin, schedule: dict):
    bloque = TrainingBlock(
        user_id=user_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        objetivo_prioritario="strength",
    )
    session.add(bloque)
    session.commit()
    for dia, tipo in schedule.items():
        session.add(WeeklySchedule(training_block_id=bloque.id, dia_semana=dia, session_type=tipo))
    session.commit()
    return bloque


class TestComputeDailySessionAutoDerivedPlan:
    """planned_session=None debe derivarse del TrainingBlock/WeeklySchedule
    activo (Fase F) en vez de exigir que el caller lo calcule a mano."""

    def test_deriva_planned_session_del_plan_semanal_activo(self, session, usuario):
        hoy = date(2026, 8, 3)  # lunes
        _sembrar_readiness(session, usuario.id, hoy, "green")
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"mon": "strength_heavy"}
        )
        resultado = compute_daily_session(session, usuario.id, target_date=hoy)
        assert resultado.session_type == SessionType.STRENGTH_HEAVY
        assert resultado.volume_pct == 100

    def test_planned_session_explicito_tiene_prioridad_sobre_el_plan_semanal(
        self, session, usuario
    ):
        # Override manual: aunque el plan diga strength_heavy, si se pasa
        # planned_session explícito, ese gana (permite excepciones puntuales
        # sin tocar el bloque persistido).
        hoy = date(2026, 8, 3)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"mon": "strength_heavy"}
        )
        resultado = compute_daily_session(
            session, usuario.id, target_date=hoy, planned_session=SessionType.REST
        )
        assert resultado.session_type == SessionType.REST

    def test_sin_planned_session_ni_plan_semanal_activo_lanza_valueerror(self, session, usuario):
        hoy = date(2026, 8, 3)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        with pytest.raises(ValueError):
            compute_daily_session(session, usuario.id, target_date=hoy)

    def test_dia_sin_entrada_en_el_schedule_lanza_valueerror(self, session, usuario):
        hoy = date(2026, 8, 4)  # martes, sin entrada en el schedule de abajo
        _sembrar_readiness(session, usuario.id, hoy, "green")
        _crear_bloque_con_schedule(
            session, usuario.id, date(2026, 8, 1), date(2026, 9, 12), {"mon": "strength_heavy"}
        )
        with pytest.raises(ValueError):
            compute_daily_session(session, usuario.id, target_date=hoy)


class TestComputeDailySession:
    def test_green_sigue_el_plan_al_100_por_cien(self, session, usuario):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        resultado = compute_daily_session(
            session, usuario.id, target_date=hoy, planned_session=SessionType.STRENGTH_HEAVY
        )
        assert resultado.session_type == SessionType.STRENGTH_HEAVY
        assert resultado.volume_pct == 100

    def test_persiste_el_volume_pct_en_el_readiness_log_del_dia(self, session, usuario):
        # Regresión del hallazgo real de la Fase "carga de entrenamiento
        # numérica" (docs/02-roadmap/03-vision-produccion.md):
        # ReadinessLog.volumen_pct_ajustado existía en el schema pero
        # nada lo escribía nunca, así que no había historial real de
        # carga con el que calcular un ACWR de verdad.
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        compute_daily_session(
            session, usuario.id, target_date=hoy, planned_session=SessionType.STRENGTH_HEAVY
        )
        fila = session.query(ReadinessLog).filter_by(user_id=usuario.id, fecha=hoy).one()
        assert fila.volumen_pct_ajustado == 100

    def test_un_fallo_al_persistir_el_volumen_no_rompe_la_decision_de_sesion(
        self, session, usuario, monkeypatch, caplog
    ):
        # H2 de code-review: el enriquecimiento best-effort debe ser
        # resiliente Y observable - un fallo no debe tumbar la decisión
        # ya calculada, pero tampoco debe tragarse en silencio (eso
        # sería el mismo tipo de bug que esta épica existe para arreglar).
        import services.session_service as session_service_module

        def set_volumen_que_falla(*args, **kwargs):
            raise RuntimeError("fallo simulado de base de datos")

        monkeypatch.setattr(
            session_service_module, "set_volumen_pct_ajustado", set_volumen_que_falla
        )

        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        with caplog.at_level("WARNING"):
            resultado = compute_daily_session(
                session, usuario.id, target_date=hoy, planned_session=SessionType.STRENGTH_HEAVY
            )

        assert resultado.session_type == SessionType.STRENGTH_HEAVY
        assert resultado.volume_pct == 100
        assert "volumen_pct_ajustado" in caplog.text

    def test_rechaza_si_no_hay_readiness_calculado_ese_dia(self, session, usuario):
        with pytest.raises(ValueError):
            compute_daily_session(
                session,
                usuario.id,
                target_date=date(2026, 8, 2),
                planned_session=SessionType.STRENGTH_HEAVY,
            )

    def test_rechaza_si_el_usuario_no_existe(self, session):
        with pytest.raises(ValueError):
            compute_daily_session(
                session,
                user_id=9999,
                target_date=date(2026, 8, 2),
                planned_session=SessionType.STRENGTH_HEAVY,
            )

    def test_acwr_history_vacia_no_lanza_y_cae_a_decide_session(self, session, usuario):
        # Regresión: [] es falsy igual que None, no debe intentar llamar
        # a should_force_deload (que lanza ValueError con lista vacía).
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        resultado = compute_daily_session(
            session,
            usuario.id,
            target_date=hoy,
            planned_session=SessionType.STRENGTH_HEAVY,
            acwr_history=[],
        )
        assert resultado.session_type == SessionType.STRENGTH_HEAVY

    def test_usa_el_readiness_mas_reciente_si_hay_varias_filas_el_mismo_dia(
        self, session, usuario
    ):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "red")  # primera sync: mala lectura
        _sembrar_readiness(session, usuario.id, hoy, "green")  # re-sync: dato corregido
        resultado = compute_daily_session(
            session, usuario.id, target_date=hoy, planned_session=SessionType.STRENGTH_HEAVY
        )
        # Debe usar "green" (la más reciente), no "red" (la primera).
        assert resultado.session_type == SessionType.STRENGTH_HEAVY
        assert resultado.volume_pct == 100

    def test_colision_de_ambos_guardrails_acwr_gana_sobre_pre_competicion(
        self, session, usuario
    ):
        # Caso límite de seguridad: ACWR sostenido Y competición <72h con
        # RED a la vez. Documentado como decisión consciente: ambos
        # resultados son volumen 0, por lo que el orden no compromete la
        # seguridad, pero el comportamiento debe ser determinista y
        # verificado, no accidental.
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "red")
        resultado = compute_daily_session(
            session,
            usuario.id,
            target_date=hoy,
            planned_session=SessionType.MARTIAL_ARTS_SPARRING,
            acwr_history=[1.6, 1.55],
            days_to_competition=2,
        )
        assert resultado.session_type == SessionType.ACTIVE_RECOVERY
        assert resultado.volume_pct == 0

    def test_acwr_sostenido_fuerza_descanso_incluso_con_green(self, session, usuario):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        resultado = compute_daily_session(
            session,
            usuario.id,
            target_date=hoy,
            planned_session=SessionType.STRENGTH_HEAVY,
            acwr_history=[1.6, 1.55],
        )
        assert resultado.session_type == SessionType.ACTIVE_RECOVERY
        assert resultado.volume_pct == 0

    def test_acwr_no_sostenido_no_fuerza_nada(self, session, usuario):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        resultado = compute_daily_session(
            session,
            usuario.id,
            target_date=hoy,
            planned_session=SessionType.STRENGTH_HEAVY,
            acwr_history=[1.6, 1.1],
        )
        assert resultado.session_type == SessionType.STRENGTH_HEAVY

    def test_competicion_cercana_con_red_fuerza_descanso_total(self, session, usuario):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "red")
        resultado = compute_daily_session(
            session,
            usuario.id,
            target_date=hoy,
            planned_session=SessionType.MARTIAL_ARTS_TECHNICAL,
            days_to_competition=2,
        )
        assert resultado.session_type == SessionType.REST
        assert resultado.volume_pct == 0

    def test_competicion_lejana_con_red_usa_la_regla_normal_de_decide_session(
        self, session, usuario
    ):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "red")
        resultado = compute_daily_session(
            session,
            usuario.id,
            target_date=hoy,
            planned_session=SessionType.MARTIAL_ARTS_TECHNICAL,
            days_to_competition=10,
        )
        # RED + sesión de menor demanda -> reducido, no descanso total
        assert resultado.volume_pct == 40

    def test_registra_auditoria_de_la_decision(self, session, usuario):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "yellow")
        resultado = compute_daily_session(
            session, usuario.id, target_date=hoy, planned_session=SessionType.STRENGTH_HEAVY
        )
        auditoria = (
            session.query(AuditLog).filter_by(user_id=usuario.id, modulo="session_decision").one()
        )
        assert "strength_heavy" in auditoria.inputs_json["planned_session"]
        assert auditoria.regla_disparada == "decide_session"
        # El cap de RPE (salida de seguridad de YELLOW) debe quedar en
        # la auditoría, no perderse.
        assert "rpe_cap" in auditoria.decision_final
        assert resultado.intensity_rpe_cap is not None

    def test_registra_auditoria_en_camino_de_guardrail_con_regla_correcta(
        self, session, usuario
    ):
        hoy = date(2026, 8, 2)
        _sembrar_readiness(session, usuario.id, hoy, "green")
        compute_daily_session(
            session,
            usuario.id,
            target_date=hoy,
            planned_session=SessionType.STRENGTH_HEAVY,
            acwr_history=[1.6, 1.55],
        )
        auditoria = (
            session.query(AuditLog).filter_by(user_id=usuario.id, modulo="session_decision").one()
        )
        assert auditoria.regla_disparada == "should_force_deload"
        assert auditoria.output == SessionType.ACTIVE_RECOVERY.value
