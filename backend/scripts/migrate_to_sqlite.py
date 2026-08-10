"""Copia TODOS los datos del Postgres de desarrollo (Docker) a un
archivo SQLite nuevo - Épica K (00-research/09-app-nativa-escritorio.md),
paso 2: la app de escritorio empaquetada usa SQLite, y este script es
lo que la deja inmediatamente útil con los datos reales de Miguel en
vez de arrancar vacía.

USO (a mano, una sola vez por cada archivo SQLite que se quiera
poblar - re-ejecutarlo sobre un archivo ya migrado falla a propósito
(`FileExistsError`, ver `migrar()` más abajo), para no duplicar filas
ni pisar datos silenciosamente):

    python -m scripts.migrate_to_sqlite --destino C:\\ruta\\pulse.db

Requiere que `DATABASE_URL` (o el valor por defecto de
`models.database`) apunte al Postgres de origen con el stack de Docker
levantado.

Genérico a propósito: recorre `Base.metadata.sorted_tables` (ya en
orden topológico de FKs) y copia fila a fila con INSERT crudos, en vez
de listar cada modelo a mano - así no hay que tocar este script cada
vez que se añade una tabla nueva al esquema."""
from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from models.database import create_pulse_engine
from models.schema import Base


def migrar(origen_url: str, destino_path: Path) -> None:
    if destino_path.exists():
        raise FileExistsError(
            f"{destino_path} ya existe - bórralo antes si quieres una migración limpia "
            "(este script nunca sobrescribe un archivo SQLite existente)."
        )

    engine_origen = create_pulse_engine(origen_url)
    engine_destino = create_pulse_engine(f"sqlite:///{destino_path}")
    Base.metadata.create_all(engine_destino)

    total_filas = 0
    with engine_origen.connect() as conn_origen, engine_destino.begin() as conn_destino:
        for tabla in Base.metadata.sorted_tables:
            filas = conn_origen.execute(select(tabla)).mappings().all()
            if not filas:
                print(f"  {tabla.name}: 0 filas (nada que copiar)")
                continue
            conn_destino.execute(tabla.insert(), [dict(fila) for fila in filas])
            total_filas += len(filas)
            print(f"  {tabla.name}: {len(filas)} filas copiadas")

    print(f"OK: {total_filas} filas migradas a {destino_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destino",
        required=True,
        type=Path,
        help="Ruta del archivo SQLite nuevo a crear (debe NO existir todavía).",
    )
    parser.add_argument(
        "--origen-url",
        default=None,
        help="Cadena de conexión Postgres de origen (por defecto, la de models.database).",
    )
    args = parser.parse_args()
    from models.database import get_database_url

    migrar(args.origen_url or get_database_url(), args.destino)


if __name__ == "__main__":
    main()
