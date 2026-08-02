"""Punto de entrada de la API REST de Pulse (Fase A del plan autónomo,
ver docs/02-roadmap/02-plan-autonomo.md).

Principio: esta capa es un adaptador HTTP fino sobre `services/*`, ya
probados de forma independiente. Cero lógica de negocio nueva aquí -
solo serialización (Pydantic) y mapeo de errores a códigos HTTP.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import body_composition, nutrition, readiness, session, users
from garmin_sync.mapper import InsufficientDataError
from services.errors import EntityNotFoundError

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


app.include_router(users.router)
app.include_router(body_composition.router)
app.include_router(nutrition.router)
app.include_router(readiness.router)
app.include_router(session.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
