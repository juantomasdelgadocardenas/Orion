"""Planes de pago: cuánto se paga en cada cuota y cómo va bajando el saldo."""
from dataclasses import dataclass
from datetime import date

from app.services.fechas import tasa_mensual


@dataclass(frozen=True)
class Cuota:
    numero: int
    fecha: date
    capital: int
    interes: int
    saldo: int  # lo que queda debiendo después de pagar esta cuota

    @property
    def total(self) -> int:
        return self.capital + self.interes


def plan_capital_constante(monto: int, tasa_ea: float, fechas: list[date]) -> list[Cuota]:
    """Compra con tarjeta diferida: abono a capital igual cada mes + interés sobre el saldo.
    A una sola cuota no hay interés."""
    n = len(fechas)
    tasa = tasa_mensual(tasa_ea) if n > 1 else 0.0
    base = monto // n
    saldo, plan = monto, []
    for i, fecha in enumerate(fechas, start=1):
        capital = saldo if i == n else base
        interes = round(saldo * tasa)
        saldo -= capital
        plan.append(Cuota(i, fecha, capital, interes, saldo))
    return plan


def cuota_fija(monto: int, tasa_ea: float, n: int) -> int:
    tasa = tasa_mensual(tasa_ea)
    if n <= 0:
        return 0
    if tasa == 0:
        return -(-monto // n)
    return round(monto * tasa / (1 - (1 + tasa) ** -n))


def plan_cuota_fija(monto: int, tasa_ea: float, fechas: list[date]) -> list[Cuota]:
    """Crédito de cuota fija: cada mes baja el interés y sube el abono a capital."""
    n = len(fechas)
    tasa = tasa_mensual(tasa_ea)
    cuota = cuota_fija(monto, tasa_ea, n)
    saldo, plan = monto, []
    for i, fecha in enumerate(fechas, start=1):
        interes = round(saldo * tasa)
        capital = saldo if i == n else min(saldo, cuota - interes)
        saldo -= capital
        plan.append(Cuota(i, fecha, capital, interes, saldo))
    return plan
