"""Saldos derivados: saldo_inicial + movimientos confirmados. Nunca se edita un saldo a mano."""
from app.repositories.almacen import Libro


def saldos_cuentas(libro: Libro) -> dict[str, int]:
    cuentas = {c.id: c for c in libro.cuentas}
    saldos = {c.id: c.saldo_inicial for c in libro.cuentas}

    def mover(cuenta_id: str, monto: int, fecha) -> None:
        cuenta = cuentas.get(cuenta_id)
        if cuenta and fecha >= cuenta.fecha_saldo_inicial:
            saldos[cuenta_id] += monto

    for x in libro.transacciones:
        if x.estado != "confirmada":
            continue
        if x.tipo == "ingreso":
            mover(x.cuenta_id, x.monto, x.fecha)
        elif x.tipo in ("gasto", "pago_deuda"):
            mover(x.cuenta_id, -x.monto, x.fecha)
        elif x.tipo == "transferencia" or (x.tipo == "aporte_bolsillo" and x.cuenta_destino_id):
            if x.cuenta_destino_id != x.cuenta_id:
                mover(x.cuenta_id, -x.monto, x.fecha)
                mover(x.cuenta_destino_id, x.monto, x.fecha)
    return saldos


def montos_bolsillos(libro: Libro) -> dict[str, int]:
    montos = {b.id: 0 for b in libro.bolsillos}
    for x in libro.transacciones:
        if x.tipo == "aporte_bolsillo" and x.estado == "confirmada" and x.bolsillo_id in montos:
            montos[x.bolsillo_id] += x.monto
    return montos
