"""Contrato de almacenamiento y conversión fila ⇄ modelo. Los servicios solo conocen `Libro`."""
import secrets
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Protocol

from app.domain import modelos as m
from app.repositories.esquema import CONFIG_POR_DEFECTO, TABLAS, Tabla


@dataclass
class Libro:
    usuarios: list[m.Usuario] = field(default_factory=list)
    cuentas: list[m.Cuenta] = field(default_factory=list)
    deudas: list[m.TarjetaDeuda] = field(default_factory=list)
    transacciones: list[m.Transaccion] = field(default_factory=list)
    bolsillos: list[m.BolsilloMeta] = field(default_factory=list)
    categorias: list[m.Categoria] = field(default_factory=list)
    gastos_fijos: list[m.GastoFijo] = field(default_factory=list)
    config: list[m.ConfigItem] = field(default_factory=list)
    importaciones: list[m.Importacion] = field(default_factory=list)

    def ajuste(self, clave: str) -> str:
        for item in self.config:
            if item.clave == clave:
                return item.valor
        return CONFIG_POR_DEFECTO.get(clave, "")


class Almacen(Protocol):
    def leer(self) -> Libro: ...
    def agregar(self, tabla: str, filas: list[m.Fila]) -> None: ...
    def actualizar(self, tabla: str, id_: str, fila: m.Fila) -> None: ...
    def eliminar(self, tabla: str, id_: str) -> None: ...


class NoEncontrado(LookupError):
    pass


def nuevo_id(tabla: Tabla) -> str:
    return f"{tabla.prefijo}_{int(time.time() * 1000):x}{secrets.token_hex(2)}"


def ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def a_celdas(tabla: Tabla, fila: m.Fila) -> list:
    """Modelo → valores de celda. Las fechas van como texto ISO; nada se interpreta como fórmula (RAW)."""
    celdas = []
    for columna in tabla.columnas:
        valor = getattr(fila, columna)
        if valor is None:
            valor = ""
        elif isinstance(valor, date):
            valor = valor.isoformat()
        celdas.append(valor)
    return celdas


def de_celdas(tabla: Tabla, encabezados: list[str], celdas: list) -> m.Fila:
    return tabla.modelo.model_validate(dict(zip(encabezados, celdas)))


def tabla(clave: str) -> Tabla:
    if clave not in TABLAS:
        raise NoEncontrado(f"Tabla desconocida: {clave}")
    return TABLAS[clave]
