"""Punto de entrada: `uvicorn app.main:app`."""
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.rutas import crear_rutas
from app.core.auth import GuardiaPin
from app.core.config import Ajustes, obtener_ajustes
from app.repositories.almacen import Almacen

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# La extensión de Chrome y el servidor de desarrollo llaman desde otro origen.
ORIGENES = r"^(chrome-extension://[a-p]{32}|https?://(localhost|127\.0\.0\.1)(:\d+)?)$"


def construir_almacen(ajustes: Ajustes) -> Almacen:
    if ajustes.orion_modo == "demo":
        from app.repositories.demo import libro_demo
        from app.repositories.memoria import AlmacenMemoria

        return AlmacenMemoria(libro_demo(date.today()))
    from app.core.google_auth import abrir_libro
    from app.repositories.sheets import AlmacenSheets

    almacen = AlmacenSheets(abrir_libro(ajustes))
    almacen.leer()  # valida encabezados al arrancar; falla con un mensaje claro si algo no coincide
    return almacen


def crear_app(ajustes: Ajustes | None = None, almacen: Almacen | None = None, reloj=None) -> FastAPI:
    ajustes = ajustes or obtener_ajustes()
    almacen = almacen or construir_almacen(ajustes)
    secreto = ajustes.orion_secreto.get_secret_value() if ajustes.orion_secreto else None
    guardia = GuardiaPin(ajustes.orion_pin.get_secret_value(), secreto)

    app = FastAPI(title="Orion", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware, allow_origin_regex=ORIGENES,
        allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(crear_rutas(almacen, guardia, ajustes.orion_modo, reloj))
    if FRONTEND.is_dir():
        # Sirve la app web ya compilada: útil para abrirla desde el celular en la misma red.
        app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")
    return app


def __getattr__(nombre: str):
    # `app` se construye solo cuando uvicorn lo pide, no al importar el módulo en pruebas.
    if nombre == "app":
        return crear_app()
    raise AttributeError(nombre)
