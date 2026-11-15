"""Arma todo lo que pinta la app en una sola respuesta."""
from datetime import date

from app.repositories.almacen import Libro
from app.services import alertas, deudas, dinero_real, metas, motor_tarjetas, presupuesto, saldos


def _num(texto: str, defecto: float) -> float:
    try:
        return float(str(texto).replace(",", "."))
    except ValueError:
        return defecto


def _deuda_json(e: deudas.EstadoDeuda, hoy: date, zona: int) -> dict:
    d = e.deuda
    datos = {
        **d.model_dump(mode="json"),
        "saldo": e.saldo,
        "proximo_pago": e.proximo_pago.isoformat() if e.proximo_pago else None,
        "dias_para_pago": (e.proximo_pago - hoy).days if e.proximo_pago else None,
        "pago_ciclo": e.pago_ciclo,
        "pagado_ciclo": e.pagado_ciclo,
        "pendiente_ciclo": e.pendiente_ciclo,
        "vencido": e.vencido,
        "en_mora": e.en_mora,
        "avance": round(e.avance, 4),
        "uso_cupo": round(e.uso_cupo, 4),
        "cupo_disponible": max(0, d.cupo_total - e.saldo),
        "cuotas_pagadas": e.cuotas_pagadas,
        "cuotas_totales": e.cuotas_totales,
        "monto_original": e.monto_original,
        "intereses_restantes": e.total_intereses_restantes,
        "plan": [
            {"numero": p.numero, "fecha": p.fecha.isoformat(), "capital": p.capital, "interes": p.interes,
             "manejo": p.manejo, "total": p.total, "saldo": p.saldo, "pagada": p.pagada}
            for p in e.plan
        ],
        "compras": [
            {"descripcion": c.descripcion, "fecha": c.fecha.isoformat(), "monto": c.monto, "cuotas": c.cuotas,
             "cuota_actual": c.cuota_actual, "restante": c.restante, "valor_cuota": c.valor_cuota}
            for c in e.compras
        ],
    }
    if d.tipo == "tarjeta_credito":
        dia = motor_tarjetas.clasificar_dia(d, hoy, zona)
        datos["hoy"] = {"estado": dia.estado, "dias_financiacion": dia.dias_financiacion}
        datos["proximo_corte"] = motor_tarjetas.corte_de_compra(d, hoy).isoformat()
        datos["proximo_dia_optimo"] = motor_tarjetas.proximo_dia_optimo(d, hoy, zona).isoformat()
        datos["calendario"] = [
            {"fecha": c.fecha.isoformat(), "estado": c.estado, "dias_financiacion": c.dias_financiacion,
             "es_corte": c.es_corte, "es_pago": c.es_pago}
            for c in motor_tarjetas.calendario(d, hoy, zona)
        ]
    return datos


def construir(libro: Libro, hoy: date, responsable: str | None = None) -> dict:
    zona = int(_num(libro.ajuste("dias_zona_riesgo"), 5))
    saldos_ctas = saldos.saldos_cuentas(libro)
    montos = saldos.montos_bolsillos(libro)
    estados = deudas.estados(libro.deudas, libro.transacciones, hoy)
    dinero = dinero_real.calcular(libro, saldos_ctas, montos, estados, hoy)
    avances = metas.proyectar(libro, montos, estados, hoy)
    gastos = presupuesto.gasto_por_categoria(libro, hoy, responsable)
    gastos_hogar = gastos if not responsable else presupuesto.gasto_por_categoria(libro, hoy)
    lista_alertas = alertas.generar(
        hoy, dinero, estados, gastos_hogar, avances,
        dias_alerta_pago=int(_num(libro.ajuste("dias_alerta_pago"), 5)),
        dias_zona_riesgo=zona,
        umbral_aviso=_num(libro.ajuste("umbral_presupuesto_aviso"), 0.8),
    )
    recientes = sorted(
        (x for x in libro.transacciones
         if x.estado != "anulada" and (not responsable or x.responsable == responsable)),
        key=lambda x: (x.fecha, x.creado_en, x.id), reverse=True,
    )[:25]
    tarjetas = [e for e in estados if e.deuda.tipo == "tarjeta_credito"]
    return {
        "hoy": hoy.isoformat(),
        "usuarios": [u.model_dump() for u in libro.usuarios if u.activo],
        "cuentas": [{**c.model_dump(mode="json"), "saldo": saldos_ctas.get(c.id, 0)} for c in libro.cuentas if c.activa],
        "categorias": [c.model_dump() for c in sorted(libro.categorias, key=lambda c: c.orden) if c.activa],
        "gastos_fijos": [g.model_dump() for g in libro.gastos_fijos if g.activo],
        "dinero_real": {
            "total": dinero.total, "saldo_bruto": dinero.saldo_bruto, "comprometido": dinero.comprometido,
            "gastos_fijos": dinero.gastos_fijos, "deudas": dinero.deudas, "ahorro": dinero.ahorro,
            "lineas": [
                {"grupo": x.grupo, "nombre": x.nombre, "monto": x.monto,
                 "fecha": x.fecha.isoformat() if x.fecha else None}
                for x in dinero.lineas
            ],
        },
        "deuda_tarjetas": sum(e.saldo for e in tarjetas),
        "deuda_total": sum(e.saldo for e in estados),
        "ahorro_total": sum(montos.values()),
        "flujo": presupuesto.flujo_mensual(libro, hoy, 6, responsable),
        "gasto_categorias": [
            {"id": g.categoria.id, "nombre": g.categoria.nombre, "icono": g.categoria.icono,
             "color": g.categoria.color, "gastado": g.gastado,
             "presupuesto": g.categoria.presupuesto_mensual, "uso": round(g.uso, 4)}
            for g in gastos
        ],
        "deudas": [_deuda_json(e, hoy, zona) for e in estados],
        "metas": [
            {**a.meta.model_dump(mode="json"), "objetivo": a.objetivo, "actual": a.actual,
             "restante": a.restante, "avance": round(a.avance, 4), "estado_avance": a.estado,
             "aporte": a.aporte_mensual, "ritmo_necesario": a.ritmo_necesario,
             "fecha_estimada": a.fecha_estimada.isoformat() if a.fecha_estimada else None,
             "meses_cubiertos": a.meses_cubiertos,
             "cuotas_pagadas": a.cuotas_pagadas, "cuotas_totales": a.cuotas_totales}
            for a in avances
        ],
        "alertas": [vars(a) for a in lista_alertas],
        "recientes": [x.model_dump(mode="json") for x in recientes],
    }


def refrescar_caches(almacen, hoy: date) -> int:
    """Escribe en la hoja los valores derivados (saldo_actual, saldo_pendiente, monto_actual) que cambiaron."""
    libro = almacen.leer()
    cambios = 0
    saldos_ctas = saldos.saldos_cuentas(libro)
    for c in libro.cuentas:
        if c.saldo_actual != saldos_ctas[c.id]:
            almacen.actualizar("cuentas", c.id, c.model_copy(update={"saldo_actual": saldos_ctas[c.id]}))
            cambios += 1
    por_id = {e.deuda.id: e for e in deudas.estados(libro.deudas, libro.transacciones, hoy)}
    for d in libro.deudas:
        e = por_id.get(d.id)
        if e and d.saldo_pendiente != e.saldo:
            almacen.actualizar("deudas", d.id, d.model_copy(update={"saldo_pendiente": e.saldo}))
            cambios += 1
    montos = saldos.montos_bolsillos(libro)
    for b in libro.bolsillos:
        if b.modo_avance == "ahorro" and b.monto_actual != montos[b.id]:
            almacen.actualizar("bolsillos", b.id, b.model_copy(update={"monto_actual": montos[b.id]}))
            cambios += 1
    return cambios
