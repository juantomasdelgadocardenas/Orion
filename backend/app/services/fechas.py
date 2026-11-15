"""Aritmética de fechas y tasas."""
import calendar
from datetime import date

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def mover_mes(anio: int, mes: int, n: int) -> tuple[int, int]:
    total = anio * 12 + (mes - 1) + n
    return total // 12, total % 12 + 1


def dia_en_mes(anio: int, mes: int, dia: int) -> date:
    """Día del mes; si el mes no lo tiene (29–31), el último día."""
    return date(anio, mes, min(dia, calendar.monthrange(anio, mes)[1]))


def dia_en_mes_relativo(base: date, n: int, dia: int) -> date:
    anio, mes = mover_mes(base.year, base.month, n)
    return dia_en_mes(anio, mes, dia)


def fin_de_mes(d: date) -> date:
    return dia_en_mes(d.year, d.month, 31)


def mismo_mes(a: date, b: date) -> bool:
    return (a.year, a.month) == (b.year, b.month)


def tasa_mensual(tasa_ea: float) -> float:
    """Efectiva anual → efectiva mensual."""
    return (1 + tasa_ea) ** (1 / 12) - 1 if tasa_ea > 0 else 0.0
