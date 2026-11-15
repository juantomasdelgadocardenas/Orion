"""Único módulo que construye credenciales de Google. Nunca las imprime ni las registra."""
import base64
import json

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import Ajustes

# Mínimo privilegio: solo hojas de cálculo, sin acceso a Drive.
ALCANCES = ["https://www.googleapis.com/auth/spreadsheets"]


def _credenciales(ajustes: Ajustes) -> Credentials:
    if ajustes.google_service_account_json_b64 is not None:
        info = json.loads(base64.b64decode(ajustes.google_service_account_json_b64.get_secret_value()))
        return Credentials.from_service_account_info(info, scopes=ALCANCES)
    ruta = ajustes.ruta_credenciales()
    if ruta is None or not ruta.exists():
        raise FileNotFoundError(f"No encuentro el JSON de la cuenta de servicio en {ruta}")
    return Credentials.from_service_account_file(str(ruta), scopes=ALCANCES)


def correo_cuenta_servicio(ajustes: Ajustes) -> str:
    return _credenciales(ajustes).service_account_email


def abrir_libro(ajustes: Ajustes) -> gspread.Spreadsheet:
    cliente = gspread.authorize(_credenciales(ajustes))
    return cliente.open_by_key(ajustes.orion_sheet_id)
