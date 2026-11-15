"""Crea las pestañas y encabezados que falten (no borra nada).

Uso:  uv run python -m scripts.crear_esquema            # solo estructura
      uv run python -m scripts.crear_esquema --demo     # además carga los datos de ejemplo
      uv run python -m scripts.crear_esquema --categorias   # además carga categorías sugeridas
"""
import sys
from datetime import date

from app.core.config import obtener_ajustes
from app.core.google_auth import abrir_libro
from app.repositories.demo import libro_demo
from app.repositories.esquema import TABLAS
from app.repositories.sheets import AlmacenSheets


def main() -> int:
    ajustes = obtener_ajustes()
    if ajustes.orion_modo != "sheets":
        print("Cambia ORION_MODO=sheets en backend/.env antes de crear el esquema.")
        return 1
    almacen = AlmacenSheets(abrir_libro(ajustes))
    for linea in almacen.crear_esquema() or ["El esquema ya estaba completo."]:
        print("•", linea)

    cargar = [a for a in ("--demo", "--categorias") if a in sys.argv]
    if cargar:
        actual, demo = almacen.leer(), libro_demo(date.today())
        claves = [c for c in TABLAS if c != "config"] if "--demo" in cargar else ["categorias"]
        for clave in claves:
            if getattr(actual, clave):
                print(f"• {TABLAS[clave].pestana}: ya tiene datos, no la toco")
                continue
            filas = getattr(demo, clave)
            almacen.agregar(clave, filas)
            print(f"• {TABLAS[clave].pestana}: {len(filas)} filas de ejemplo")
    print("✓ Listo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
