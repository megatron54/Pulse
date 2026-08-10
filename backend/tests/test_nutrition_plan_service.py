"""TDD - services.nutrition_plan_service: planes de deficit/superavit/
mantenimiento con duración determinada (petición explícita del
usuario: "planes de deficit, superhabit y mantenimiento dedicados, con
duración determinada, como tu nutricionista personal")."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.schema import Base, NutritionPlan, UserProfile
from services.errors import EntityNotFoundError
from services.nutrition_plan_service import create_nutrition_plan, get_active_nutrition_plan


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def usuario(session):
    u = UserProfile(nombre="Test", altura_cm=180.0, fecha_nacimiento=date(1995, 1, 1), sexo="M")
    session.add(u)
    session.commit()
    return u


class TestCreateNutritionPlan:
    def test_crea_el_plan_y_lo_marca_activo(self, session, usuario):
        plan = create_nutrition_plan(
            session,
            user_id=usuario.id,
            fase="cut",
            semanas_duracion=8,
            fecha_inicio=date(2026, 8, 10),
        )

        assert plan.fase == "cut"
        assert plan.semanas_duracion == 8
        assert plan.activo is True

    def test_sincroniza_fase_peso_actual_del_perfil(self, session, usuario):
        create_nutrition_plan(
            session, user_id=usuario.id, fase="surplus", semanas_duracion=6, fecha_inicio=date(2026, 8, 10)
        )

        session.refresh(usuario)
        assert usuario.fase_peso_actual == "surplus"

    def test_crear_un_plan_nuevo_desactiva_el_anterior(self, session, usuario):
        plan_1 = create_nutrition_plan(
            session, user_id=usuario.id, fase="cut", semanas_duracion=8, fecha_inicio=date(2026, 8, 10)
        )
        plan_2 = create_nutrition_plan(
            session,
            user_id=usuario.id,
            fase="maintenance",
            semanas_duracion=4,
            fecha_inicio=date(2026, 10, 5),
        )

        session.refresh(plan_1)
        assert plan_1.activo is False
        assert plan_2.activo is True

    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        with pytest.raises(EntityNotFoundError):
            create_nutrition_plan(
                session, user_id=99999, fase="cut", semanas_duracion=8, fecha_inicio=date(2026, 8, 10)
            )

    def test_semanas_duracion_debe_ser_positiva(self, session, usuario):
        with pytest.raises(ValueError):
            create_nutrition_plan(
                session, user_id=usuario.id, fase="cut", semanas_duracion=0, fecha_inicio=date(2026, 8, 10)
            )


class TestGetActiveNutritionPlan:
    def test_devuelve_none_si_no_hay_plan(self, session, usuario):
        assert get_active_nutrition_plan(session, usuario.id, as_of=date(2026, 8, 10)) is None

    def test_devuelve_el_plan_activo_con_fecha_fin_y_dias_restantes_calculados(
        self, session, usuario
    ):
        create_nutrition_plan(
            session, user_id=usuario.id, fase="cut", semanas_duracion=8, fecha_inicio=date(2026, 8, 10)
        )

        resultado = get_active_nutrition_plan(session, usuario.id, as_of=date(2026, 9, 10))

        assert resultado is not None
        assert resultado.fecha_fin == date(2026, 10, 5)  # 8 semanas = 56 días
        assert resultado.dias_restantes == (date(2026, 10, 5) - date(2026, 9, 10)).days
        assert resultado.expirado is False

    def test_marca_expirado_si_as_of_es_posterior_a_fecha_fin(self, session, usuario):
        create_nutrition_plan(
            session, user_id=usuario.id, fase="cut", semanas_duracion=2, fecha_inicio=date(2026, 8, 1)
        )

        resultado = get_active_nutrition_plan(session, usuario.id, as_of=date(2026, 9, 1))

        assert resultado.expirado is True
        assert resultado.dias_restantes == 0

    def test_borde_exacto_as_of_igual_a_fecha_fin_cuenta_como_expirado(self, session, usuario):
        # Fija la semántica (code-review: borde no testeado antes):
        # 2 semanas desde 2026-08-01 -> fecha_fin = 2026-08-15. El
        # último día VIGENTE es 2026-08-14; el día fecha_fin en sí
        # mismo ya cuenta como expirado (semántica de límite superior
        # exclusivo, igual que un rango [inicio, fin)).
        create_nutrition_plan(
            session, user_id=usuario.id, fase="cut", semanas_duracion=2, fecha_inicio=date(2026, 8, 1)
        )

        resultado = get_active_nutrition_plan(session, usuario.id, as_of=date(2026, 8, 15))

        assert resultado.fecha_fin == date(2026, 8, 15)
        assert resultado.expirado is True
        assert resultado.dias_restantes == 0

    def test_usuario_inexistente_lanza_entity_not_found(self, session):
        with pytest.raises(EntityNotFoundError):
            get_active_nutrition_plan(session, 99999, as_of=date(2026, 8, 10))
