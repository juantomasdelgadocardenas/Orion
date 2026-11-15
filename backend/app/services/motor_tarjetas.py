"""Motor de tarjetas: en qué corte cae una compra, cuándo se paga y qué tan buen día es para comprar."""
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.modelos import TarjetaDeuda
from app.services.fechas import dia_en_mes, dia_en_mes_relativo

DIAS_VENTANA_OPTIMA = 5


def _dia_corte(t: TarjetaDeuda) -> int:
    # Sin día de corte configurado se asume 15 días antes del pago.
    return t.dia_corte or ((t.dia_pago - 16) % 28 + 1)


def corte_de_compra(t: TarjetaDeuda, fecha: date) -> date:
    """Fecha del corte en el que queda facturada una compra hecha en `fecha`."""
    corte = dia_en_mes(fecha.year, fecha.month, _dia_corte(t))
    if fecha < corte or (fecha == corte and t.corte_inclusivo):
        return corte
    return dia_en_mes_relativo(fecha, 1, _dia_corte(t))


def pago_de_corte(t: TarjetaDeuda, corte: date) -> date:
    """Fecha límite de pago de lo facturado en `corte`."""
    pago = dia_en_mes(corte.year, corte.month, t.dia_pago)
    return pago if pago > corte else dia_en_mes_relativo(corte, 1, t.dia_pago)


def primer_pago(t: TarjetaDeuda, fecha_compra: date) -> date:
    return pago_de_corte(t, corte_de_compra(t, fecha_compra))


def proximo_pago(t: TarjetaDeuda, hoy: date) -> date:
    pago = dia_en_mes(hoy.year, hoy.month, t.dia_pago)
    return pago if pago >= hoy else dia_en_mes_relativo(hoy, 1, t.dia_pago)


@dataclass(frozen=True)
class DiaTarjeta:
    fecha: date
    estado: str  # optimo | neutro | riesgo
    dias_financiacion: int  # días entre comprar ese día y tener que pagar
    es_corte: bool
    es_pago: bool


def clasificar_dia(t: TarjetaDeuda, dia: date, zona_riesgo: int) -> DiaTarjeta:
    corte = corte_de_compra(t, dia)
    corte_previo = dia_en_mes_relativo(corte, -1, _dia_corte(t))
    dias_hasta_corte = (corte - dia).days
    dias_desde_corte = (dia - corte_previo).days
    if dias_hasta_corte < zona_riesgo:
        estado = "riesgo"
    elif dias_desde_corte <= DIAS_VENTANA_OPTIMA:
        estado = "optimo"
    else:
        estado = "neutro"
    return DiaTarjeta(
        fecha=dia,
        estado=estado,
        dias_financiacion=(pago_de_corte(t, corte) - dia).days,
        es_corte=dia == dia_en_mes(dia.year, dia.month, _dia_corte(t)),
        es_pago=dia == dia_en_mes(dia.year, dia.month, t.dia_pago),
    )


def calendario(t: TarjetaDeuda, hoy: date, zona_riesgo: int, dias: int = 35) -> list[DiaTarjeta]:
    return [clasificar_dia(t, hoy + timedelta(days=i), zona_riesgo) for i in range(dias)]


def proximo_dia_optimo(t: TarjetaDeuda, hoy: date, zona_riesgo: int) -> date:
    for i in range(62):
        dia = clasificar_dia(t, hoy + timedelta(days=i), zona_riesgo)
        if dia.estado == "optimo":
            return dia.fecha
    return hoy
