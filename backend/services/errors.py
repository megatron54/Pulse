"""Excepciones de dominio compartidas entre servicios.

`EntityNotFoundError` es subclase de `ValueError` a propósito: cualquier
código existente que capture `ValueError` en general sigue funcionando
sin cambios, pero la API (api/main.py) puede registrar un handler HTTP
dedicado que la mapea a 404 en vez de al 400 genérico del resto de
errores de dominio (medida inválida, input inconsistente, etc.).
"""
from __future__ import annotations


class EntityNotFoundError(ValueError):
    """La entidad solicitada (usuario, etc.) no existe."""


class SessionNotDecidableError(ValueError):
    """No se puede decidir la sesión de hoy porque falta una
    precondición del usuario, no porque haya un bug.

    Existe para que la interfaz pueda decir QUÉ falta y qué hacer al
    respecto. Antes ambos casos (sin recovery sincronizado, sin plan
    semanal) llegaban al frontend como un 400 con un mensaje escrito
    para desarrolladores ("ejecutar sync_and_compute_readiness
    primero"), así que la app solo podía mostrar un "falta una de las
    dos cosas" que no orientaba a nadie. `motivo` es un código estable
    para el cliente; el texto sigue siendo para los logs.
    """

    motivo: str = "desconocido"


class ReadinessNotComputedError(SessionNotDecidableError):
    """Todavía no hay readiness calculado para esa fecha."""

    motivo = "sin_recovery"


class NoActiveWeeklyPlanError(SessionNotDecidableError):
    """No hay plan semanal activo y no se pasó una sesión explícita."""

    motivo = "sin_plan"
