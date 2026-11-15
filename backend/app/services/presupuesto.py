"""Gasto del mes por categoría contra su presupuesto, y flujo mensual."""
from dataclasses import dataclass
from datetime import date

from app.domain.modelos import Categoria
from app.repositories.almacen import Libro
from app.services.fechas import MESES, mismo_mes, mover_mes


@dataclass
class GastoCategoria:
    categoria: Categoria
    gastado: int

    @property
    def uso(self) -> float:
        p = self.categoria.presupuesto_mensual
        return self.gastado / p if p > 0 else 0.0


def _visibles(libro: Libro, responsable: str | None):
    return [
        x for x in libro.transacciones
        if x.estado == "confirmada" and (not responsable or x.responsable == responsable)
    ]


def gasto_por_categoria(libro: Libro, hoy: date, responsable: str | None = None) -> list[GastoCategoria]:
    totales: dict[str, int] = {}
    for x in _visibles(libro, responsable):
        if x.tipo == "gasto" and mismo_mes(x.fecha, hoy):
            totales[x.categoria_id] = totales.get(x.categoria_id, 0) + x.monto
    filas = [
        GastoCategoria(c, totales.pop(c.id, 0))
        for c in libro.categorias if c.tipo == "gasto" and c.activa
    ]
    sin_categoria = sum(totales.values())
    if sin_categoria:
        filas.append(GastoCategoria(Categoria(id="", nombre="Sin categoría", color="#898781", icono="❓"), sin_categoria))
    return sorted((f for f in filas if f.gastado or f.categoria.presupuesto_mensual), key=lambda f: -f.gastado)


def flujo_mensual(libro: Libro, hoy: date, meses: int = 6, responsable: str | None = None) -> list[dict]:
    periodos = [mover_mes(hoy.year, hoy.month, -i) for i in range(meses - 1, -1, -1)]
    flujo = {p: {"mes": f"{p[0]}-{p[1]:02d}", "etiqueta": MESES[p[1] - 1], "ingresos": 0, "gastos": 0} for p in periodos}
    for x in _visibles(libro, responsable):
        fila = flujo.get((x.fecha.year, x.fecha.month))
        if fila is None:
            continue
        if x.tipo == "ingreso":
            fila["ingresos"] += x.monto
        elif x.tipo == "gasto":
            fila["gastos"] += x.monto
    return list(flujo.values())
