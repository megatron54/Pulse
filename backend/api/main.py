"""Punto de entrada de la API REST de Pulse (Fase A del plan autónomo,
ver docs/02-roadmap/02-plan-autonomo.md).

Principio: esta capa es un adaptador HTTP fino sobre `services/*`, ya
probados de forma independiente. Cero lógica de negocio nueva aquí -
solo serialización (Pydantic) y mapeo de errores a códigos HTTP.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import (
    body_composition,
    exercises,
    feelfit,
    garmin,
    habits,
    nutrition,
    readiness,
    session,
    summary,
    training_blocks,
    users,
)
from garmin_sync.mapper import InsufficientDataError
from services.errors import EntityNotFoundError

logger = logging.getLogger("pulse.api")

app = FastAPI(
    title="Pulse API",
    description="Entrenador personal con IA - motor de reglas determinista + coach conversacional.",
    version="0.1.0",
)

# CORS: necesario para que el frontend (Fase B, Next.js en otro puerto/
# origen) pueda llamar a esta API desde el navegador. En dev, el origen
# se toma de PULSE_FRONTEND_ORIGIN (por defecto localhost:3000, el
# puerto estándar de `next dev`); en producción se debe fijar al dominio
# real del frontend desplegado.
_frontend_origin = os.environ.get("PULSE_FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    """Registrado ANTES/más específico que el handler genérico de
    ValueError: FastAPI/Starlette resuelve el handler exacto de la clase
    de la excepción, así que EntityNotFoundError (subclase de ValueError)
    usa este 404 en vez del 400 genérico de abajo."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Los servicios lanzan ValueError para errores de dominio (medida
    inválida, input inconsistente, precondición no cumplida, etc.) - se
    mapean uniformemente a 400. Las ausencias de entidad usan
    EntityNotFoundError -> 404 (ver handler de arriba)."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(InsufficientDataError)
async def insufficient_data_handler(request: Request, exc: InsufficientDataError) -> JSONResponse:
    """Principio 'unknown is not zero': datos de Garmin insuficientes se
    comunican como 422 (entidad no procesable), distinto de un 400 de
    input malformado por parte del cliente."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad final: cualquier excepción NO prevista por los
    handlers específicos de arriba (un bug real, un fallo de
    infraestructura como una tabla que falta) se registra completa en
    el log del servidor, pero al cliente solo le llega un mensaje
    genérico - NUNCA el mensaje de la excepción original.

    Hallazgo real (verificación manual con Playwright, Fase de pulido
    de frontend): un fallo de Postgres (`relation "wger_credentials"
    does not exist`) se propagó sin este handler y el frontend mostró
    en pantalla el mensaje crudo de psycopg2/SQLAlchemy, incluyendo la
    consulta SQL completa y los parámetros - una fuga de información
    interna real, no solo teórica."""
    logger.exception(
        "Excepción no controlada en %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(
        status_code=500, content={"detail": "Ha ocurrido un error interno. Inténtalo de nuevo."}
    )


app.include_router(users.router)
app.include_router(body_composition.router)
app.include_router(nutrition.router)
app.include_router(readiness.router)
app.include_router(session.router)
app.include_router(training_blocks.router)
app.include_router(exercises.router)
app.include_router(habits.router)
app.include_router(garmin.router)
app.include_router(feelfit.router)
app.include_router(summary.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
