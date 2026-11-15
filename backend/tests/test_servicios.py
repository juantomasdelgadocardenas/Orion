from datetime import date

from app.domain import modelos as m
from app.repositories.almacen import Libro
from app.services import deudas, dinero_real, metas, motor_tarjetas, saldos
from app.services.cuotas import cuota_fija, plan_capital_constante, plan_cuota_fija
from app.services.fechas import dia_en_mes, dia_en_mes_relativo, tasa_mensual

HOY = date(2026, 11, 15)


def tarjeta(**extra):
    base = dict(id="tc", nombre="TC", dia_corte=25, dia_pago=10, tasa_ea=0.26, cupo_total=4_000_000)
    return m.TarjetaDeuda(**{**base, **extra})


def gasto(fecha, monto, cuenta="tc", **extra):
    return m.Transaccion(id=f"t{fecha}{monto}", fecha=fecha, monto=monto, cuenta_id=cuenta, **extra)


def test_fechas_ajustan_meses_cortos():
    assert dia_en_mes(2026, 2, 31) == date(2026, 2, 28)
    assert dia_en_mes_relativo(date(2026, 12, 31), 2, 31) == date(2027, 2, 28)


def test_plan_capital_constante_suma_el_monto_y_baja_a_cero():
    fechas = [dia_en_mes_relativo(HOY, i, 10) for i in range(12)]
    plan = plan_capital_constante(1_000_000, 0.26, fechas)
    assert sum(c.capital for c in plan) == 1_000_000
    assert plan[-1].saldo == 0
    assert plan[0].interes == round(1_000_000 * tasa_mensual(0.26))
    assert [c.interes for c in plan] == sorted((c.interes for c in plan), reverse=True)


def test_una_sola_cuota_no_genera_interes():
    plan = plan_capital_constante(500_000, 0.30, [HOY])
    assert plan[0].interes == 0 and plan[0].total == 500_000


def test_plan_cuota_fija_es_constante_y_amortiza_todo():
    fechas = [dia_en_mes_relativo(HOY, i, 20) for i in range(24)]
    plan = plan_cuota_fija(9_600_000, 0.24, fechas)
    cuota = cuota_fija(9_600_000, 0.24, 24)
    assert all(abs(c.total - cuota) <= 1 for c in plan[:-1])
    assert abs(plan[-1].total - cuota) < 50  # la última absorbe el redondeo
    assert sum(c.capital for c in plan) == 9_600_000 and plan[-1].saldo == 0
    assert plan[0].capital < plan[-1].capital  # cada mes se abona más a capital


def test_compra_despues_del_corte_se_paga_un_ciclo_despues():
    t = tarjeta()
    assert motor_tarjetas.primer_pago(t, date(2026, 11, 25)) == date(2026, 12, 10)  # día de corte, inclusivo
    assert motor_tarjetas.primer_pago(t, date(2026, 11, 26)) == date(2027, 1, 10)
    no_inclusiva = tarjeta(corte_inclusivo=False)
    assert motor_tarjetas.primer_pago(no_inclusiva, date(2026, 11, 25)) == date(2027, 1, 10)


def test_clasificacion_de_dias():
    t = tarjeta()
    assert motor_tarjetas.clasificar_dia(t, date(2026, 11, 26), 5).estado == "optimo"
    assert motor_tarjetas.clasificar_dia(t, date(2026, 11, 26), 5).dias_financiacion == 45
    assert motor_tarjetas.clasificar_dia(t, date(2026, 11, 23), 5).estado == "riesgo"
    assert motor_tarjetas.clasificar_dia(t, date(2026, 11, 25), 5).estado == "riesgo"
    assert motor_tarjetas.clasificar_dia(t, date(2026, 11, 10), 5).estado == "neutro"
    assert motor_tarjetas.proximo_dia_optimo(t, HOY, 5) == date(2026, 11, 26)


def test_tarjeta_reparte_compra_en_cuotas_y_descuenta_pagos():
    t = tarjeta()
    compras = [gasto(date(2026, 10, 20), 1_200_000, cuotas=12), gasto(date(2026, 10, 22), 100_000)]
    e = deudas.estado_tarjeta(t, compras, HOY)  # ambas caen en el corte del 25-oct → pago 10-nov (ya pasó)
    assert e.proximo_pago == date(2026, 12, 10)
    interes_1 = round(1_200_000 * tasa_mensual(0.26))
    assert e.vencido == 100_000 + 100_000 + interes_1  # el pago de noviembre no se registró
    assert len(e.plan) == 11 and e.plan[-1].saldo == 0
    assert e.compras[0].cuota_actual == 2 and e.compras[0].restante == 1_100_000

    pago = m.Transaccion(id="p", fecha=date(2026, 11, 9), monto=e.vencido, tipo="pago_deuda",
                         cuenta_id="cta", cuenta_destino_id="tc")
    e2 = deudas.estado_tarjeta(t, compras + [pago], HOY)
    assert e2.vencido == 0 and e2.saldo == 1_100_000
    assert e2.pago_ciclo == 100_000 + round(1_100_000 * tasa_mensual(0.26))
    saldos_plan = [p.saldo for p in e2.plan]
    assert saldos_plan == sorted(saldos_plan, reverse=True)  # la deuda va bajando


def test_credito_avanza_con_pagos_registrados():
    d = m.TarjetaDeuda(id="moto", nombre="Moto", tipo="credito", dia_pago=20, tasa_ea=0.24,
                       monto_original=9_600_000, cuotas_totales=24, cuotas_pagadas_iniciales=10,
                       fecha_inicio=date(2026, 1, 20))
    e = deudas.estado_credito(d, [], HOY)
    assert e.cuotas_pagadas == 10 and e.proximo_pago == date(2026, 11, 20) and not e.en_mora
    assert 0.35 < e.avance < 0.45  # al inicio se paga más interés que capital
    pago = m.Transaccion(id="p", fecha=HOY, monto=e.pago_ciclo, tipo="pago_deuda", cuenta_id="c", cuenta_destino_id="moto")
    e2 = deudas.estado_credito(d, [pago], HOY)
    assert e2.cuotas_pagadas == 11 and e2.saldo < e.saldo and e2.proximo_pago == date(2026, 12, 20)


def _libro():
    return Libro(
        cuentas=[m.Cuenta(id="c1", nombre="Banco", saldo_inicial=2_000_000, fecha_saldo_inicial=date(2026, 11, 1)),
                 m.Cuenta(id="c2", nombre="Efectivo", tipo="efectivo", saldo_inicial=100_000,
                          fecha_saldo_inicial=date(2026, 11, 1))],
        gastos_fijos=[m.GastoFijo(id="g1", nombre="Arriendo", monto=900_000, dia_cobro=5),
                      m.GastoFijo(id="g2", nombre="Internet", monto=80_000, dia_cobro=20)],
        bolsillos=[m.BolsilloMeta(id="b1", nombre="Emergencia", tipo="fondo_emergencia", monto_objetivo=1_000_000,
                                  aporte_mensual=200_000, cuenta_id="c1")],
        deudas=[tarjeta(fecha_saldo_inicial=date(2026, 10, 1), saldo_inicial=300_000)],
        transacciones=[
            gasto(date(2026, 11, 5), 900_000, "c1", gasto_fijo_id="g1"),
            gasto(date(2026, 10, 30), 50_000, "c1"),  # anterior al saldo inicial: no cuenta
            m.Transaccion(id="tr", fecha=date(2026, 11, 6), monto=50_000, tipo="transferencia",
                          cuenta_id="c1", cuenta_destino_id="c2"),
            m.Transaccion(id="ap", fecha=date(2026, 11, 7), monto=120_000, tipo="aporte_bolsillo",
                          cuenta_id="c1", bolsillo_id="b1"),
            gasto(date(2026, 11, 8), 70_000, "c1", estado="anulada"),
        ],
    )


def test_saldos_derivados():
    assert saldos.saldos_cuentas(_libro()) == {"c1": 1_050_000, "c2": 150_000}
    assert saldos.montos_bolsillos(_libro()) == {"b1": 120_000}


def test_dinero_real_no_resta_dos_veces():
    libro = _libro()
    estados = deudas.estados(libro.deudas, libro.transacciones, HOY)
    r = dinero_real.calcular(libro, saldos.saldos_cuentas(libro), saldos.montos_bolsillos(libro), estados, HOY)
    assert r.saldo_bruto == 1_200_000
    assert r.gastos_fijos == 80_000  # el arriendo ya se pagó este mes
    assert r.deudas == 300_000  # deuda inicial: vencía el 10-nov y no hay pago registrado
    assert r.ahorro == 120_000 + 80_000  # lo apartado + lo que falta del aporte del mes
    assert r.total == 1_200_000 - 80_000 - 300_000 - 200_000


def test_metas():
    libro = _libro()
    libro.bolsillos.append(m.BolsilloMeta(id="b2", nombre="Viaje", monto_objetivo=2_000_000, aporte_mensual=100_000,
                                          fecha_objetivo=date(2027, 3, 1)))
    avances = {a.meta.id: a for a in metas.proyectar(libro, {"b1": 120_000, "b2": 0}, [], HOY)}
    assert avances["b1"].avance == 0.12 and avances["b1"].estado == "en_ritmo"
    assert avances["b1"].meses_cubiertos == round(120_000 / 980_000, 1)
    assert avances["b2"].estado == "atrasada" and avances["b2"].ritmo_necesario == 500_000
