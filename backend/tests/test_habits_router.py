"""Tests de integración del router de hábitos — TDD. Patrón de
TestClient + SQLite en memoria establecido en test_garmin_router.py."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from models.schema import Base, ReadinessLog


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), engine
    app.dependency_overrides.clear()


def _crear_usuario(client):
    resp = client.post(
        "/users",
        json={
            "nombre": "Test",
            "altura_cm": 180,
            "fecha_nacimiento": "1995-01-01",
            "sexo": "M",
            "fase_peso_actual": "maintenance",
        },
    )
    return resp.json()


class TestSetHabits:
    def test_guarda_los_habitos_del_dia_y_devuelve_204(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.post(
            f"/users/{usuario['id']}/habits?date=2026-08-04",
            json={"habitos": ["alcohol", "siesta"]},
        )
        assert resp.status_code == 204

    def test_rechaza_un_habito_fuera_del_catalogo_cerrado(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.post(
            f"/users/{usuario['id']}/habits?date=2026-08-04",
            json={"habitos": ["no_existe"]},
        )
        assert resp.status_code == 422

    def test_usuario_inexistente_da_404(self, client):
        # HIGH-2 de code-review: sin esta validación, en Postgres real
        # esto habría escapado como un 500 (IntegrityError de FK) en vez
        # de un 404 limpio.
        c, _ = client
        resp = c.post(
            "/users/99999/habits?date=2026-08-04",
            json={"habitos": ["alcohol"]},
        )
        assert resp.status_code == 404


class TestGetHabitCorrelation:
    def test_sin_datos_suficientes_lo_indica_explicitamente(self, client):
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(
            f"/users/{usuario['id']}/habits/correlation",
            params={"habito": "alcohol", "as_of": "2026-08-10"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["datos_suficientes"] is False
        assert body["pct_red_con_habito"] is None

    def test_rechaza_un_habito_fuera_del_catalogo_cerrado(self, client):
        # HIGH-1 de code-review: `habito` es texto libre en el query
        # param si no se tipa con el Literal compartido - un valor
        # arbitrario debía devolver 422, no 200 con datos vacíos.
        c, _ = client
        usuario = _crear_usuario(c)
        resp = c.get(
            f"/users/{usuario['id']}/habits/correlation",
            params={"habito": "no_existe", "as_of": "2026-08-10"},
        )
        assert resp.status_code == 422

    def test_usuario_inexistente_da_404(self, client):
        c, _ = client
        resp = c.get(
            "/users/99999/habits/correlation",
            params={"habito": "alcohol", "as_of": "2026-08-10"},
        )
        assert resp.status_code == 404

    def test_con_datos_suficientes_devuelve_los_porcentajes(self, client):
        c, engine = client
        usuario = _crear_usuario(c)
        hoy = date(2026, 8, 20)

        dias_con_habito = [hoy - timedelta(days=d) for d in range(1, 13, 2)]
        for i, dia in enumerate(dias_con_habito):
            c.post(
                f"/users/{usuario['id']}/habits?date={dia.isoformat()}",
                json={"habitos": ["alcohol"]},
            )
        with Session(engine) as session:
            for i, dia in enumerate(dias_con_habito):
                resultado = "red" if i < 4 else "green"
                session.add(
                    ReadinessLog(
                        user_id=usuario["id"],
                        fecha=dia + timedelta(days=1),
                        resultado=resultado,
                    )
                )
            dias_sin_habito = [hoy - timedelta(days=d) for d in range(2, 14, 2)]
            for dia in dias_sin_habito:
                c.post(
                    f"/users/{usuario['id']}/habits?date={dia.isoformat()}",
                    json={"habitos": []},
                )
            for i, dia in enumerate(dias_sin_habito):
                resultado = "red" if i < 1 else "green"
                session.add(
                    ReadinessLog(
                        user_id=usuario["id"],
                        fecha=dia + timedelta(days=1),
                        resultado=resultado,
                    )
                )
            session.commit()

        resp = c.get(
            f"/users/{usuario['id']}/habits/correlation",
            params={"habito": "alcohol", "as_of": hoy.isoformat()},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["datos_suficientes"] is True
        assert body["pct_red_con_habito"] == pytest.approx(4 / 6)
        assert body["pct_red_sin_habito"] == pytest.approx(1 / 6)
