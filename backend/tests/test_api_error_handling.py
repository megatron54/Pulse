"""Tests para el manejador genérico de excepciones no controladas de
la API — TDD.

Hallazgo real durante verificación manual con Playwright (Wed 5 ago):
un fallo real de base de datos (`wger_credentials` no existía en el
Postgres de desarrollo) se propagó tal cual al cliente - el frontend
mostró el mensaje crudo de `psycopg2`/SQLAlchemy, incluyendo la
consulta SQL completa y los parámetros, directamente en pantalla. Esto
viola el principio de seguridad "los errores nunca deben filtrar
detalles internos" (ver AGENTS.md, sección de seguridad) - antes de
este fix, la API solo tenía handlers para `EntityNotFoundError`,
`ValueError` e `InsufficientDataError`; cualquier excepción NO prevista
(bug real, fallo de infraestructura) se propagaba con el traceback
completo de FastAPI/Starlette en modo debug.
"""
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db, verify_api_key
from api.main import app
from models.schema import Base


def _ruta_que_siempre_falla(db: Session = Depends(get_db)) -> None:
    raise RuntimeError(
        "relation \"wger_credentials\" does not exist LINE 2: FROM wger_credentials "
        "[SQL: SELECT ...] [parameters: {'user_id_1': 3, 'password': 'hunter2'}]"
    )


def test_excepcion_no_controlada_devuelve_500_generico_sin_filtrar_detalles():
    """Registra una ruta que lanza una excepción arbitraria NO prevista
    por ningún handler específico, y confirma que el cliente recibe un
    mensaje genérico - nunca el mensaje real de la excepción (que aquí
    simula un fallo real de SQL con datos sensibles)."""
    router_de_prueba = APIRouter()
    router_de_prueba.add_api_route(
        "/test-error-no-controlado",
        _ruta_que_siempre_falla,
        methods=["GET"],
        dependencies=[Depends(verify_api_key)],
    )
    app.include_router(router_de_prueba)

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test-error-no-controlado")

        assert resp.status_code == 500
        cuerpo = resp.json()
        assert "wger_credentials" not in str(cuerpo)
        assert "hunter2" not in str(cuerpo)
        assert "SELECT" not in str(cuerpo)
        assert cuerpo == {"detail": "Ha ocurrido un error interno. Inténtalo de nuevo."}
    finally:
        app.dependency_overrides.clear()
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", None) != "/test-error-no-controlado"
        ]
