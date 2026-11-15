"""Proyección de metas y bolsillos."""
import math
from dataclasses import dataclass
from datetime import date

from app.domain.modelos import BolsilloMeta
from app.repositories.almacen import Libro
from app.services.deudas import EstadoDeuda
from app.services.fechas import dia_en_mes_relativo


@dataclass
class AvanceMeta:
    meta: BolsilloMeta
    objetivo: int
    actual: int
    aporte_mensual: int
    estado: str  # cumplida | en_ritmo | atrasada | sin_plan
    fecha_estimada: date | None = None
    ritmo_necesario: int = 0
    meses_cubiertos: float | None = None  # solo fondo de emergencia
    cuotas_pagadas: int = 0
    cuotas_totales: int = 0

    @property
    def restante(self) -> int:
        return max(0, self.objetivo - self.actual)

    @property
    def avance(self) -> float:
        return max(0.0, min(1.0, self.actual / self.objetivo)) if self.objetivo > 0 else 0.0


def _meses_entre(a: date, b: date) -> int:
    return max(0, (b.year - a.year) * 12 + b.month - a.month)


def proyectar(libro: Libro, montos: dict[str, int], estados_deuda: list[EstadoDeuda], hoy: date) -> list[AvanceMeta]:
    deudas = {e.deuda.id: e for e in estados_deuda}
    fijos_mes = sum(g.monto for g in libro.gastos_fijos if g.activo)
    resultado = []
    for b in sorted(libro.bolsillos, key=lambda x: x.prioridad):
        if b.estado == "pausada":
            continue
        e = deudas.get(b.deuda_id) if b.modo_avance == "pago_deuda" else None
        if e:
            objetivo = e.monto_original or b.monto_objetivo
            a = AvanceMeta(b, objetivo, objetivo - e.saldo, e.pago_ciclo, "en_ritmo",
                           cuotas_pagadas=e.cuotas_pagadas, cuotas_totales=e.cuotas_totales)
            pendientes = [p for p in e.plan if not p.pagada]
            a.fecha_estimada = pendientes[-1].fecha if pendientes else None
            if e.en_mora:
                a.estado = "atrasada"
        else:
            a = AvanceMeta(b, b.monto_objetivo, montos.get(b.id, 0), b.aporte_mensual, "sin_plan")
            if b.aporte_mensual > 0 and a.restante > 0:
                a.fecha_estimada = dia_en_mes_relativo(hoy, math.ceil(a.restante / b.aporte_mensual), hoy.day)
                a.estado = "en_ritmo"
            if b.fecha_objetivo and a.restante > 0:
                meses = _meses_entre(hoy, b.fecha_objetivo)
                a.ritmo_necesario = a.restante if meses == 0 else math.ceil(a.restante / meses)
                if b.fecha_objetivo < hoy or b.aporte_mensual < a.ritmo_necesario:
                    a.estado = "atrasada"
        if a.objetivo > 0 and a.restante == 0:
            a.estado = "cumplida"
        if b.tipo == "fondo_emergencia" and fijos_mes > 0:
            a.meses_cubiertos = round(a.actual / fijos_mes, 1)
        resultado.append(a)
    return resultado
