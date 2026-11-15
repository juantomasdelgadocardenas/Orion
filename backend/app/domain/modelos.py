"""Modelos de dominio. El orden de los campos es el orden exacto de las columnas en Google Sheets."""
from datetime import date, timedelta
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

EPOCA_SHEETS = date(1899, 12, 30)
_VERDADERO = {"true", "verdadero", "si", "sí", "1", "x"}
_FALSO = {"false", "falso", "no", "0"}


def campo(titulo: str, defecto=..., **extra):
    """Campo con etiqueta para la UI. extra: dinero, ref, oculto, ayuda, porcentaje."""
    return Field(defecto, title=titulo, json_schema_extra=extra or None)


def _tipos(anotacion) -> tuple:
    return (anotacion, *get_args(anotacion))


class Fila(BaseModel):
    """Base tolerante: acepta lo que devuelve Sheets (celdas vacías, fechas como número de serie…)."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _limpiar(cls, datos):
        if not isinstance(datos, dict):
            return datos
        limpio = {}
        for clave, valor in datos.items():
            info = cls.model_fields.get(clave)
            if info is None or valor is None or (isinstance(valor, str) and not valor.strip()):
                continue
            tipos = _tipos(info.annotation)
            es_numero = isinstance(valor, (int, float)) and not isinstance(valor, bool)
            if date in tipos and es_numero:
                valor = EPOCA_SHEETS + timedelta(days=int(valor))
            elif bool in tipos and isinstance(valor, str):
                texto = valor.strip().lower()
                valor = True if texto in _VERDADERO else False if texto in _FALSO else valor
            elif str in tipos and es_numero:
                valor = str(int(valor)) if float(valor).is_integer() else str(valor)
            elif isinstance(valor, str):
                valor = valor.strip()
            limpio[clave] = valor
        return limpio


class Usuario(Fila):
    id: str = campo("ID", "", oculto=True)
    nombre: str = campo("Nombre")
    color: str = campo("Color", "#F6AE57", color=True)
    activo: bool = campo("Activo", True)


class Cuenta(Fila):
    id: str = campo("ID", "", oculto=True)
    nombre: str = campo("Nombre")
    tipo: Literal["ahorros", "corriente", "billetera", "efectivo"] = campo("Tipo", "ahorros")
    institucion: str = campo("Banco o entidad", "", ayuda="Ej.: Daviplata, Davivienda, Nubank, Efectivo")
    titular: str = campo("Titular", "compartida", ref="titulares")
    moneda: str = campo("Moneda", "COP")
    saldo_inicial: int = campo("Saldo inicial", 0, dinero=True)
    fecha_saldo_inicial: date = campo("Fecha del saldo inicial", ayuda="Orion suma y resta movimientos desde esta fecha")
    saldo_actual: int = campo("Saldo actual", 0, oculto=True)
    incluir_en_dinero_real: bool = campo("Cuenta para Dinero Real", True)
    activa: bool = campo("Activa", True)
    actualizado_en: str = campo("Actualizado", "", oculto=True)


class TarjetaDeuda(Fila):
    id: str = campo("ID", "", oculto=True)
    nombre: str = campo("Nombre")
    tipo: Literal["tarjeta_credito", "credito"] = campo("Tipo", "tarjeta_credito")
    institucion: str = campo("Banco o entidad", "")
    titular: str = campo("Titular", "compartida", ref="titulares")
    moneda: str = campo("Moneda", "COP")
    cupo_total: int = campo("Cupo total", 0, dinero=True, solo="tarjeta_credito")
    dia_corte: int | None = campo("Día de corte", None, solo="tarjeta_credito", min=1, max=31)
    dia_pago: int = campo("Día de pago", 1, min=1, max=31)
    corte_inclusivo: bool = campo("La compra del día de corte entra en ese corte", True, solo="tarjeta_credito")
    cuota_manejo_mensual: int = campo("Cuota de manejo mensual", 0, dinero=True, solo="tarjeta_credito")
    tasa_ea: float = campo("Tasa efectiva anual", 0.0, porcentaje=True, ayuda="Ej.: 26.5")
    saldo_inicial: int = campo("Deuda al empezar a usar Orion", 0, dinero=True, solo="tarjeta_credito")
    fecha_saldo_inicial: date | None = campo("Fecha de esa deuda", None, solo="tarjeta_credito")
    cuotas_saldo_inicial: int = campo("Cuotas en que se paga esa deuda", 1, solo="tarjeta_credito", min=1)
    monto_original: int = campo("Valor financiado", 0, dinero=True, solo="credito")
    cuotas_totales: int = campo("Número de cuotas", 0, solo="credito")
    cuotas_pagadas_iniciales: int = campo("Cuotas ya pagadas al empezar", 0, solo="credito")
    fecha_inicio: date | None = campo("Fecha de la primera cuota", None, solo="credito")
    saldo_pendiente: int = campo("Saldo pendiente", 0, oculto=True)
    activa: bool = campo("Activa", True)
    actualizado_en: str = campo("Actualizado", "", oculto=True)


TipoTransaccion = Literal["gasto", "ingreso", "transferencia", "pago_deuda", "aporte_bolsillo"]


class Transaccion(Fila):
    id: str = ""
    fecha: date
    monto: int = Field(gt=0)
    tipo: TipoTransaccion = "gasto"
    responsable: str = ""
    categoria_id: str = ""
    cuenta_id: str = ""
    cuenta_destino_id: str = ""
    bolsillo_id: str = ""
    gasto_fijo_id: str = ""
    descripcion: str = Field("", max_length=140)
    cuotas: int = Field(1, ge=1, le=72)
    estado: Literal["pendiente", "confirmada", "anulada"] = "confirmada"
    origen: Literal["manual", "importacion", "recurrente"] = "manual"
    huella_importacion: str = ""
    creado_por: str = ""
    creado_en: str = ""
    actualizado_en: str = ""


class BolsilloMeta(Fila):
    id: str = campo("ID", "", oculto=True)
    nombre: str = campo("Nombre")
    tipo: Literal["fondo_emergencia", "meta", "bolsillo"] = campo("Tipo", "meta")
    modo_avance: Literal["ahorro", "pago_deuda"] = campo(
        "Cómo se mide el avance", "ahorro", ayuda="ahorro = plata apartada · pago_deuda = lo ya pagado de un crédito"
    )
    monto_objetivo: int = campo("Monto objetivo", 0, dinero=True)
    monto_actual: int = campo("Monto actual", 0, oculto=True)
    aporte_mensual: int = campo("Aporte mensual", 0, dinero=True)
    fecha_inicio: date | None = campo("Fecha de inicio", None)
    fecha_objetivo: date | None = campo("Fecha objetivo", None)
    cuenta_id: str = campo("Cuenta donde está la plata", "", ref="cuentas")
    deuda_id: str = campo("Crédito asociado", "", ref="deudas")
    responsable: str = campo("Responsable", "compartida", ref="titulares")
    prioridad: int = campo("Prioridad", 1)
    imagen: str = campo("Imagen", "", ayuda="Clave de la imagen, ej.: akt-tt-200-rally")
    destacar_en_dashboard: bool = campo("Destacar en el inicio", False)
    estado: Literal["activa", "pausada", "cumplida"] = campo("Estado", "activa")
    actualizado_en: str = campo("Actualizado", "", oculto=True)


class Categoria(Fila):
    id: str = campo("ID", "", oculto=True)
    nombre: str = campo("Nombre")
    tipo: Literal["gasto", "ingreso"] = campo("Tipo", "gasto")
    grupo: Literal["necesidades", "gustos", "ahorro_deuda", "ingresos"] = campo("Grupo", "necesidades")
    presupuesto_mensual: int = campo("Presupuesto mensual", 0, dinero=True, ayuda="0 = sin límite")
    icono: str = campo("Icono", "", ayuda="Un emoji")
    color: str = campo("Color", "#3987e5", color=True)
    orden: int = campo("Orden", 0)
    activa: bool = campo("Activa", True)


class GastoFijo(Fila):
    id: str = campo("ID", "", oculto=True)
    nombre: str = campo("Nombre")
    monto: int = campo("Monto mensual", 0, dinero=True)
    dia_cobro: int = campo("Día de cobro", 1, min=1, max=31)
    categoria_id: str = campo("Categoría", "", ref="categorias")
    cuenta_id: str = campo("Cuenta de pago", "", ref="cuentas")
    responsable: str = campo("Responsable", "compartida", ref="titulares")
    activo: bool = campo("Activo", True)


class ConfigItem(Fila):
    clave: str
    valor: str = ""


class Importacion(Fila):
    id: str = ""
    fecha: str = ""
    responsable: str = ""
    cuenta_id: str = ""
    huella_archivo: str = ""
    filas_leidas: int = 0
    filas_nuevas: int = 0
    filas_duplicadas: int = 0
    filas_rechazadas: int = 0
