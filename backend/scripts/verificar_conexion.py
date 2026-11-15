"""Iteración 1: prueba la conexión con Google Sheets.  Uso: uv run python -m scripts.verificar_conexion"""
import sys

from app.core.config import obtener_ajustes


def main() -> int:
    try:
        ajustes = obtener_ajustes()
    except Exception as error:
        print(f"✗ Configuración incompleta:\n{error}")
        return 1
    if ajustes.orion_modo != "sheets":
        print("ORION_MODO=demo: no hay nada que conectar. Cambia a ORION_MODO=sheets en backend/.env.")
        return 1
    from app.core.google_auth import abrir_libro, correo_cuenta_servicio

    try:
        correo = correo_cuenta_servicio(ajustes)
        print(f"Cuenta de servicio: {correo}")
        libro = abrir_libro(ajustes)
    except FileNotFoundError as error:
        print(f"✗ {error}")
        return 1
    except Exception as error:
        print(f"✗ No pude abrir el libro ({type(error).__name__}).")
        print("  Revisa: 1) que la API de Google Sheets esté habilitada en el proyecto,")
        print("          2) que el libro esté compartido como Editor con la cuenta de servicio,")
        print("          3) que ORION_SHEET_ID sea el ID correcto.")
        return 1
    print(f"✓ Conectado al libro: «{libro.title}»")
    print("  Pestañas:", ", ".join(ws.title for ws in libro.worksheets()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
