"""Estado de cada tarjeta o crédito: cuánto se debe, cuánto toca pagar y el plan mes a mes."""
from dataclasses import dataclass, field
from datetime import date

from app.domain.modelos import TarjetaDeuda, Transaccion
from app.services import motor_tarjetas as motor
from app.services.cuotas import plan_capital_constante, plan_cuota_fija
from app.services.fechas import dia_en_mes_relativo


@dataclass
class PagoPlan:
    numero: int
    fecha: date
    capital: int
    interes: int
    manejo: int
    saldo: int
    pagada: bool = False

    @property
    def total(self) -> int:
        return self.capital + self.interes + self.manejo


@dataclass
class CompraDiferida:
    descripcion: str
    fecha: date
    monto: int
    cuotas: int
    cuota_actual: int
    restante: int
    valor_cuota: int


@dataclass
class EstadoDeuda:
    deuda: TarjetaDeuda
    saldo: int = 0  # capital pendiente
    proximo_pago: date | None = None
    pago_ciclo: int = 0  # lo que toca pagar en el próximo pago
    pagado_ciclo: int = 0
    vencido: int = 0  # pagos de ciclos anteriores sin registrar (no incluido en pago_ciclo)
    en_mora: bool = False
    plan: list[PagoPlan] = field(default_factory=list)
    compras: list[CompraDiferida] = field(default_factory=list)
    cuotas_pagadas: int = 0
    cuotas_totales: int = 0
    monto_original: int = 0

    @property
    def pendiente_ciclo(self) -> int:
        return max(0, self.pago_ciclo - self.pagado_ciclo)

    @property
    def avance(self) -> float:
        if self.monto_original <= 0:
            return 0.0
        return max(0.0, min(1.0, (self.monto_original - self.saldo) / self.monto_original))

    @property
    def uso_cupo(self) -> float:
        cupo = self.deuda.cupo_total
        return self.saldo / cupo if cupo > 0 else 0.0

    @property
    def total_intereses_restantes(self) -> int:
        return sum(p.interes for p in self.plan if not p.pagada)


def _pagos(d: TarjetaDeuda, transacciones: list[Transaccion]) -> list[Transaccion]:
    return [
        x for x in transacciones
        if x.tipo == "pago_deuda" and x.estado == "confirmada" and x.cuenta_destino_id == d.id
    ]


def estado_tarjeta(t: TarjetaDeuda, transacciones: list[Transaccion], hoy: date) -> EstadoDeuda:
    desde = t.fecha_saldo_inicial
    compras: list[tuple[date, int, int, str]] = []
    if t.saldo_inicial > 0 and desde:
        compras.append((desde, t.saldo_inicial, max(1, t.cuotas_saldo_inicial), "Deuda inicial"))
    for x in transacciones:
        if x.tipo == "gasto" and x.estado == "confirmada" and x.cuenta_id == t.id and (not desde or x.fecha > desde):
            compras.append((x.fecha, x.monto, x.cuotas, x.descripcion or "Compra"))

    prox = motor.proximo_pago(t, hoy)
    anterior = dia_en_mes_relativo(prox, -1, t.dia_pago)
    previo = dia_en_mes_relativo(prox, -2, t.dia_pago)

    por_fecha: dict[date, list[int]] = {}
    diferidas = []
    for fecha, monto, n, descripcion in compras:
        primera = motor.primer_pago(t, fecha)
        fechas = [dia_en_mes_relativo(primera, i, t.dia_pago) for i in range(n)]
        plan = plan_capital_constante(monto, t.tasa_ea, fechas)
        for c in plan:
            acumulado = por_fecha.setdefault(c.fecha, [0, 0])
            acumulado[0] += c.capital
            acumulado[1] += c.interes
        pendientes = [c for c in plan if c.fecha >= prox]
        if n > 1 and pendientes:
            diferidas.append(CompraDiferida(
                descripcion, fecha, monto, n, pendientes[0].numero,
                sum(c.capital for c in pendientes), pendientes[0].total,
            ))

    pagos = _pagos(t, transacciones)
    pagado = sum(x.monto for x in pagos if anterior < x.fecha <= prox)
    pagado_anterior = sum(x.monto for x in pagos if previo < x.fecha <= anterior)
    manejo = t.cuota_manejo_mensual

    cap_ant, int_ant = por_fecha.get(anterior, [0, 0])
    vencido = max(0, cap_ant + int_ant + manejo - pagado_anterior) if cap_ant + int_ant > 0 else 0

    futuras = sorted(f for f in por_fecha if f >= prox)
    if prox not in futuras:
        futuras.insert(0, prox)
    saldo = sum(por_fecha[f][0] for f in futuras if f in por_fecha)
    cap_prox, int_prox = por_fecha.get(prox, [0, 0])
    abono_capital = max(0, min(cap_prox, pagado - int_prox - manejo))

    plan_total, corriendo = [], saldo
    for i, f in enumerate(futuras, start=1):
        capital, interes = por_fecha.get(f, [0, 0])
        corriendo -= capital
        plan_total.append(PagoPlan(i, f, capital, interes, manejo, corriendo))
    if plan_total and pagado >= plan_total[0].total > 0:
        plan_total[0].pagada = True

    return EstadoDeuda(
        deuda=t,
        saldo=saldo - abono_capital + vencido,
        proximo_pago=prox,
        pago_ciclo=cap_prox + int_prox + manejo,
        pagado_ciclo=pagado,
        vencido=vencido,
        en_mora=vencido > 0,
        plan=plan_total,
        compras=sorted(diferidas, key=lambda c: c.fecha, reverse=True),
        monto_original=0,
    )


def estado_credito(d: TarjetaDeuda, transacciones: list[Transaccion], hoy: date) -> EstadoDeuda:
    n = d.cuotas_totales
    if not d.fecha_inicio or n <= 0 or d.monto_original <= 0:
        return EstadoDeuda(deuda=d, saldo=d.monto_original, monto_original=d.monto_original, cuotas_totales=n)

    fechas = [d.fecha_inicio] + [dia_en_mes_relativo(d.fecha_inicio, i, d.dia_pago) for i in range(1, n)]
    cuotas = plan_cuota_fija(d.monto_original, d.tasa_ea, fechas)

    pagadas = min(n, max(0, d.cuotas_pagadas_iniciales))
    bolsa = sum(x.monto for x in _pagos(d, transacciones))
    while pagadas < n and bolsa >= cuotas[pagadas].total:
        bolsa -= cuotas[pagadas].total
        pagadas += 1

    plan = [PagoPlan(c.numero, c.fecha, c.capital, c.interes, 0, c.saldo, c.numero <= pagadas) for c in cuotas]
    saldo = d.monto_original if pagadas == 0 else cuotas[pagadas - 1].saldo
    estado = EstadoDeuda(
        deuda=d, saldo=saldo, plan=plan, cuotas_pagadas=pagadas, cuotas_totales=n,
        monto_original=d.monto_original,
    )
    if pagadas < n:
        siguiente = cuotas[pagadas]
        estado.proximo_pago = siguiente.fecha
        estado.pago_ciclo = siguiente.total
        estado.pagado_ciclo = min(bolsa, siguiente.total)
        estado.en_mora = siguiente.fecha < hoy
    return estado


def estado_de(d: TarjetaDeuda, transacciones: list[Transaccion], hoy: date) -> EstadoDeuda:
    if d.tipo == "tarjeta_credito":
        return estado_tarjeta(d, transacciones, hoy)
    return estado_credito(d, transacciones, hoy)


def estados(deudas: list[TarjetaDeuda], transacciones: list[Transaccion], hoy: date) -> list[EstadoDeuda]:
    return [estado_de(d, transacciones, hoy) for d in deudas if d.activa]
