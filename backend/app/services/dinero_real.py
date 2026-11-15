"""Dinero Real = saldo bruto − (gastos fijos pendientes + pagos de deuda del mes + ahorro)."""
from dataclasses import dataclass, field
from datetime import date

from app.repositories.almacen import Libro
from app.services.deudas import EstadoDeuda
from app.services.fechas import dia_en_mes, fin_de_mes, mismo_mes


@dataclass
class Linea:
    grupo: str  # saldo | fijos | deudas | ahorro
    nombre: str
    monto: int
    fecha: date | None = None


@dataclass
class DineroReal:
    saldo_bruto: int = 0
    gastos_fijos: int = 0
    deudas: int = 0
    ahorro: int = 0
    lineas: list[Linea] = field(default_factory=list)

    @property
    def comprometido(self) -> int:
        return self.gastos_fijos + self.deudas + self.ahorro

    @property
    def total(self) -> int:
        return self.saldo_bruto - self.comprometido


def calcular(
    libro: Libro,
    saldos: dict[str, int],
    montos_bolsillos: dict[str, int],
    estados_deuda: list[EstadoDeuda],
    hoy: date,
) -> DineroReal:
    r = DineroReal()
    incluidas = set()
    for c in libro.cuentas:
        if c.activa and c.incluir_en_dinero_real:
            incluidas.add(c.id)
            r.saldo_bruto += saldos.get(c.id, 0)
            r.lineas.append(Linea("saldo", c.nombre, saldos.get(c.id, 0)))

    del_mes = [x for x in libro.transacciones if x.estado == "confirmada" and mismo_mes(x.fecha, hoy)]

    # Un gasto fijo deja de restar cuando ya hay un movimiento del mes enlazado a él.
    pagados = {x.gasto_fijo_id for x in del_mes if x.gasto_fijo_id}
    for g in libro.gastos_fijos:
        if g.activo and g.id not in pagados and g.monto > 0:
            r.gastos_fijos += g.monto
            r.lineas.append(Linea("fijos", g.nombre, g.monto, dia_en_mes(hoy.year, hoy.month, g.dia_cobro)))

    limite = fin_de_mes(hoy)
    for e in estados_deuda:
        pendiente = e.vencido
        if e.proximo_pago and e.proximo_pago <= limite:
            pendiente += e.pendiente_ciclo
        if pendiente > 0:
            r.deudas += pendiente
            r.lineas.append(Linea("deudas", e.deuda.nombre, pendiente, e.proximo_pago))

    aportado = {}
    for x in del_mes:
        if x.tipo == "aporte_bolsillo":
            aportado[x.bolsillo_id] = aportado.get(x.bolsillo_id, 0) + x.monto
    for b in libro.bolsillos:
        if b.estado != "activa" or b.modo_avance != "ahorro":
            continue
        # Plata ya apartada que sigue dentro de una cuenta contada en el saldo bruto.
        apartado = montos_bolsillos.get(b.id, 0) if b.cuenta_id in incluidas else 0
        por_aportar = max(0, b.aporte_mensual - aportado.get(b.id, 0))
        if apartado:
            r.ahorro += apartado
            r.lineas.append(Linea("ahorro", f"{b.nombre} (apartado)", apartado))
        if por_aportar:
            r.ahorro += por_aportar
            r.lineas.append(Linea("ahorro", f"{b.nombre} (aporte del mes)", por_aportar))
    return r
