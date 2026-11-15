"""Pestañas del libro. Las columnas salen de los modelos: una sola fuente de verdad."""
from dataclasses import dataclass

from app.domain import modelos as m


@dataclass(frozen=True)
class Tabla:
    clave: str  # nombre corto usado en la API y en el código
    pestana: str  # nombre de la pestaña en Google Sheets
    modelo: type[m.Fila]
    prefijo: str
    campo_id: str = "id"
    singular: str = ""

    @property
    def columnas(self) -> list[str]:
        return list(self.modelo.model_fields)


TABLAS: dict[str, Tabla] = {
    t.clave: t
    for t in [
        Tabla("usuarios", "Usuarios", m.Usuario, "usr", singular="Persona"),
        Tabla("cuentas", "Cuentas", m.Cuenta, "cta", singular="Cuenta"),
        Tabla("deudas", "Tarjetas_Deudas", m.TarjetaDeuda, "deu", singular="Tarjeta o crédito"),
        Tabla("transacciones", "Transacciones", m.Transaccion, "txn"),
        Tabla("bolsillos", "Bolsillos_Metas", m.BolsilloMeta, "bol", singular="Bolsillo o meta"),
        Tabla("categorias", "Categorias", m.Categoria, "cat", singular="Categoría"),
        Tabla("gastos_fijos", "Gastos_Fijos", m.GastoFijo, "gf", singular="Gasto fijo"),
        Tabla("config", "Config", m.ConfigItem, "cfg", campo_id="clave"),
        Tabla("importaciones", "Importaciones", m.Importacion, "imp"),
    ]
}

# Tablas que la persona edita desde Ajustes.
CONFIGURABLES = ["usuarios", "cuentas", "deudas", "bolsillos", "categorias", "gastos_fijos"]

CONFIG_POR_DEFECTO = {
    "version_esquema": "1",
    "dias_alerta_pago": "5",
    "dias_zona_riesgo": "5",
    "umbral_presupuesto_aviso": "0.8",
    "zona_horaria": "America/Bogota",
}
