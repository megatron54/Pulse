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
