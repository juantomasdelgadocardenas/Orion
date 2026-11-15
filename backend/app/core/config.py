"""Configuración: único lugar que lee variables de entorno."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ_BACKEND / ".env", extra="ignore")

    orion_modo: Literal["demo", "sheets"] = "demo"
    orion_pin: SecretStr
    orion_secreto: SecretStr | None = None
    orion_sheet_id: str = ""
    google_service_account_file: Path | None = None
    google_service_account_json_b64: SecretStr | None = None

    @model_validator(mode="after")
    def _validar(self):
        pin = self.orion_pin.get_secret_value()
        if not (pin.isdigit() and 4 <= len(pin) <= 8):
            raise ValueError("ORION_PIN debe tener entre 4 y 8 dígitos")
        if self.orion_modo == "sheets":
            if not self.orion_sheet_id:
                raise ValueError("Falta ORION_SHEET_ID (modo sheets)")
            if not (self.google_service_account_file or self.google_service_account_json_b64):
                raise ValueError(
                    "Falta GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_SERVICE_ACCOUNT_JSON_B64 (modo sheets)"
                )
        return self

    def ruta_credenciales(self) -> Path | None:
        ruta = self.google_service_account_file
        if ruta is None:
            return None
        return ruta if ruta.is_absolute() else RAIZ_BACKEND / ruta


@lru_cache
def obtener_ajustes() -> Ajustes:
    return Ajustes()
