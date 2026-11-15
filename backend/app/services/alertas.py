"""Alertas de la app, ordenadas por severidad. El id es estable para poder descartarlas."""
from dataclasses import dataclass
from datetime import date

from app.services.deudas import EstadoDeuda
from app.services.dinero_real import DineroReal
from app.services.metas import AvanceMeta
from app.services.motor_tarjetas import clasificar_dia
from app.services.presupuesto import GastoCategoria

_ORDEN = {"critica": 0, "aviso": 1, "info": 2}


@dataclass
class Alerta:
    id: str
    tipo: str
    severidad: str  # critica | aviso | info
    titulo: str
    detalle: str
    monto: int | None = None


def generar(
    hoy: date,
    dinero: DineroReal,
    estados_deuda: list[EstadoDeuda],
    gastos: list[GastoCategoria],
    metas: list[AvanceMeta],
    dias_alerta_pago: int = 5,
    dias_zona_riesgo: int = 5,
    umbral_aviso: float = 0.8,
) -> list[Alerta]:
    periodo = f"{hoy.year}-{hoy.month:02d}"
    alertas: list[Alerta] = []

    if dinero.total < 0:
        alertas.append(Alerta(f"dinero_real:{periodo}", "dinero_real_negativo", "critica",
                              "Tu dinero real está en negativo",
                              "Lo comprometido este mes supera lo que hay en las cuentas.", dinero.total))

    for e in estados_deuda:
        d = e.deuda
        if e.vencido > 0:
            alertas.append(Alerta(f"vencido:{d.id}:{periodo}", "pago_vencido", "critica",
                                  f"Pago sin registrar: {d.nombre}",
                                  "El pago del ciclo anterior no aparece registrado.", e.vencido))
        if e.proximo_pago and e.pendiente_ciclo > 0:
            dias = (e.proximo_pago - hoy).days
            if dias < 0:
                alertas.append(Alerta(f"mora:{d.id}:{e.proximo_pago}", "pago_vencido", "critica",
                                      f"Cuota vencida: {d.nombre}",
                                      f"Venció hace {-dias} día(s).", e.pendiente_ciclo))
            elif dias <= dias_alerta_pago:
                cuando = "hoy" if dias == 0 else "mañana" if dias == 1 else f"en {dias} días"
                alertas.append(Alerta(f"pago:{d.id}:{e.proximo_pago}", "pago_cercano",
                                      "critica" if dias <= 2 else "aviso",
                                      f"{d.nombre}: pago {cuando}",
                                      f"Fecha límite {e.proximo_pago.strftime('%d/%m')}.", e.pendiente_ciclo))
        if d.tipo == "tarjeta_credito":
            if e.uso_cupo >= 0.8:
                alertas.append(Alerta(f"cupo:{d.id}:{periodo}", "cupo_alto", "aviso",
                                      f"{d.nombre}: cupo al {round(e.uso_cupo * 100)} %",
                                      "Usar más del 80 % del cupo sube el riesgo de sobregiro."))
            dia = clasificar_dia(d, hoy, dias_zona_riesgo)
            if dia.estado == "riesgo":
                alertas.append(Alerta(f"riesgo:{d.id}:{hoy}", "dia_de_riesgo", "info",
                                      f"Hoy no conviene comprar con {d.nombre}",
                                      f"Está cerca del corte: lo que compres se paga en {dia.dias_financiacion} días."))

    for g in gastos:
        presupuesto = g.categoria.presupuesto_mensual
        if presupuesto <= 0:
            continue
        if g.uso >= 1:
            alertas.append(Alerta(f"presupuesto:{g.categoria.id}:{periodo}", "presupuesto_excedido", "critica",
                                  f"Presupuesto excedido: {g.categoria.nombre}",
                                  f"Llevas el {round(g.uso * 100)} % del límite del mes.", g.gastado - presupuesto))
        elif g.uso >= umbral_aviso:
            alertas.append(Alerta(f"presupuesto_cerca:{g.categoria.id}:{periodo}", "presupuesto_cerca", "aviso",
                                  f"{g.categoria.nombre}: {round(g.uso * 100)} % del presupuesto",
                                  "Estás cerca del límite del mes.", presupuesto - g.gastado))

    for a in metas:
        if a.estado == "atrasada":
            alertas.append(Alerta(f"meta:{a.meta.id}:{periodo}", "meta_atrasada", "aviso",
                                  f"Meta atrasada: {a.meta.nombre}",
                                  "Con el aporte actual no llegas a la fecha objetivo.", a.ritmo_necesario or None))

    return sorted(alertas, key=lambda x: _ORDEN[x.severidad])
