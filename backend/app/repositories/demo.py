"""Datos de ejemplo (inventados) para ver la app funcionando sin conectar nada."""
from datetime import date

from app.domain import modelos as m
from app.repositories.almacen import Libro
from app.repositories.esquema import CONFIG_POR_DEFECTO
from app.services.fechas import dia_en_mes, dia_en_mes_relativo, mover_mes

CATEGORIAS = [
    ("cat_mercado", "Mercado", "necesidades", 900_000, "🛒", "#3987e5"),
    ("cat_transporte", "Transporte", "necesidades", 300_000, "⛽", "#199e70"),
    ("cat_restaurantes", "Restaurantes", "gustos", 350_000, "🍔", "#d95926"),
    ("cat_servicios", "Servicios", "necesidades", 400_000, "💡", "#c98500"),
    ("cat_salud", "Salud", "necesidades", 200_000, "💊", "#d55181"),
    ("cat_ocio", "Ocio", "gustos", 250_000, "🎬", "#9085e9"),
    ("cat_hogar", "Hogar", "necesidades", 1_500_000, "🏠", "#0ca30c"),
    ("cat_otros", "Otros", "gustos", 0, "📦", "#898781"),
]


def libro_demo(hoy: date) -> Libro:
    inicio = dia_en_mes_relativo(hoy, -6, 1)
    libro = Libro(
        usuarios=[m.Usuario(id="usr_juan", nombre="Juan", color="#3987e5"),
                  m.Usuario(id="usr_sofia", nombre="Sofía", color="#d55181")],
        cuentas=[
            m.Cuenta(id="cta_davivienda", nombre="Davivienda", tipo="ahorros", institucion="Davivienda",
                     saldo_inicial=2_400_000, fecha_saldo_inicial=inicio),
            m.Cuenta(id="cta_daviplata", nombre="Daviplata", tipo="billetera", institucion="Daviplata",
                     titular="usr_sofia", saldo_inicial=350_000, fecha_saldo_inicial=inicio),
            m.Cuenta(id="cta_nubank", nombre="Nubank", tipo="ahorros", institucion="Nubank",
                     titular="usr_juan", saldo_inicial=800_000, fecha_saldo_inicial=inicio),
            m.Cuenta(id="cta_efectivo", nombre="Efectivo", tipo="efectivo", institucion="Efectivo",
                     saldo_inicial=120_000, fecha_saldo_inicial=inicio),
        ],
        deudas=[
            m.TarjetaDeuda(id="deu_tc_nu", nombre="Tarjeta Nu", tipo="tarjeta_credito", institucion="Nubank",
                           titular="usr_juan", cupo_total=4_000_000, dia_corte=25, dia_pago=10,
                           tasa_ea=0.26, fecha_saldo_inicial=inicio),
            m.TarjetaDeuda(id="deu_tc_davi", nombre="Visa Davivienda", tipo="tarjeta_credito",
                           institucion="Davivienda", titular="usr_sofia", cupo_total=3_000_000, dia_corte=15,
                           dia_pago=2, cuota_manejo_mensual=24_900, tasa_ea=0.265, fecha_saldo_inicial=inicio),
            m.TarjetaDeuda(id="deu_moto", nombre="Crédito AKT TT 200 Rally", tipo="credito", institucion="AKT",
                           dia_pago=20, tasa_ea=0.24, monto_original=9_600_000, cuotas_totales=24,
                           cuotas_pagadas_iniciales=10, fecha_inicio=dia_en_mes_relativo(hoy, -10, 20)),
        ],
        bolsillos=[
            m.BolsilloMeta(id="bol_moto", nombre="AKT TT 200 Rally", tipo="meta", modo_avance="pago_deuda",
                           deuda_id="deu_moto", imagen="akt-tt-200-rally", destacar_en_dashboard=True, prioridad=1),
            m.BolsilloMeta(id="bol_emergencia", nombre="Fondo de emergencia", tipo="fondo_emergencia",
                           monto_objetivo=9_000_000, aporte_mensual=300_000, cuenta_id="cta_davivienda",
                           fecha_inicio=inicio, prioridad=2),
            m.BolsilloMeta(id="bol_viaje", nombre="Viaje a San Andrés", tipo="meta", monto_objetivo=3_500_000,
                           aporte_mensual=150_000, cuenta_id="cta_nubank", fecha_inicio=inicio,
                           fecha_objetivo=dia_en_mes_relativo(hoy, 8, 1), prioridad=3),
        ],
        categorias=[
            m.Categoria(id=i, nombre=n, grupo=g, presupuesto_mensual=p, icono=ic, color=c, orden=k)
            for k, (i, n, g, p, ic, c) in enumerate(CATEGORIAS)
        ] + [m.Categoria(id="cat_salario", nombre="Salario", tipo="ingreso", grupo="ingresos", icono="💼", orden=20),
             m.Categoria(id="cat_extra", nombre="Ingreso extra", tipo="ingreso", grupo="ingresos", icono="✨", orden=21)],
        gastos_fijos=[
            m.GastoFijo(id="gf_arriendo", nombre="Arriendo", monto=1_300_000, dia_cobro=5,
                        categoria_id="cat_hogar", cuenta_id="cta_davivienda"),
            m.GastoFijo(id="gf_internet", nombre="Internet", monto=95_000, dia_cobro=12,
                        categoria_id="cat_servicios", cuenta_id="cta_davivienda"),
            m.GastoFijo(id="gf_celulares", nombre="Planes de celular", monto=110_000, dia_cobro=18,
                        categoria_id="cat_servicios", cuenta_id="cta_nubank"),
            m.GastoFijo(id="gf_streaming", nombre="Streaming", monto=45_000, dia_cobro=22,
                        categoria_id="cat_ocio", cuenta_id="deu_tc_nu"),
        ],
        config=[m.ConfigItem(clave=k, valor=v) for k, v in CONFIG_POR_DEFECTO.items()],
    )

    n = 0

    def mov(fecha, monto, tipo="gasto", quien="usr_juan", cat="", cuenta="cta_davivienda", desc="", **extra):
        nonlocal n
        if fecha > hoy:
            return
        n += 1
        libro.transacciones.append(m.Transaccion(
            id=f"txn_demo{n:04d}", fecha=fecha, monto=monto, tipo=tipo, responsable=quien, categoria_id=cat,
            cuenta_id=cuenta, descripcion=desc, creado_por=quien, creado_en=f"{fecha}T12:00:00Z", **extra))

    for i in range(-6, 1):
        anio, mes = mover_mes(hoy.year, hoy.month, i)
        d = lambda dia: dia_en_mes(anio, mes, dia)  # noqa: E731
        v = (i * 7) % 5  # variación determinista entre meses
        mov(d(1), 2_600_000, "ingreso", "usr_juan", "cat_salario", "cta_davivienda", "Nómina")
        mov(d(1), 1_900_000, "ingreso", "usr_sofia", "cat_salario", "cta_daviplata", "Nómina")
        mov(d(5), 1_300_000, cat="cat_hogar", desc="Arriendo", gasto_fijo_id="gf_arriendo")
        mov(d(12), 95_000, cat="cat_servicios", desc="Internet", gasto_fijo_id="gf_internet")
        mov(d(18), 110_000, cat="cat_servicios", cuenta="cta_nubank", desc="Celulares", gasto_fijo_id="gf_celulares")
        mov(d(3), 280_000 + v * 15_000, quien="usr_sofia", cat="cat_mercado", cuenta="cta_daviplata", desc="Mercado quincena")
        mov(d(17), 310_000 + v * 12_000, cat="cat_mercado", cuenta="deu_tc_nu", desc="Mercado quincena")
        mov(d(8), 120_000 + v * 8_000, cat="cat_transporte", cuenta="cta_efectivo", desc="Gasolina")
        mov(d(9), 85_000 + v * 20_000, quien="usr_sofia", cat="cat_restaurantes", cuenta="deu_tc_davi", desc="Salida a comer")
        mov(d(14), 60_000 + v * 9_000, cat="cat_ocio", cuenta="deu_tc_nu", desc="Cine")
        mov(d(22), 45_000, cat="cat_ocio", cuenta="deu_tc_nu", desc="Streaming", gasto_fijo_id="gf_streaming")
        mov(d(10), 240_000 + v * 10_000, cat="cat_servicios", desc="Luz, agua y gas")
        mov(d(19), 330_000 + v * 14_000, quien="usr_sofia", cat="cat_mercado", cuenta="cta_daviplata", desc="Mercado quincena")
        mov(d(11), 160_000 + v * 6_000, quien="usr_sofia", cat="cat_transporte", cuenta="cta_daviplata", desc="Transporte")
        mov(d(13), 70_000 + v * 12_000, quien="usr_sofia", cat="cat_salud", cuenta="cta_daviplata", desc="Droguería")
        mov(d(7), 180_000 + v * 25_000, cat="cat_otros", cuenta="cta_nubank", desc="Varios")
        mov(d(2), 700_000, "transferencia", "usr_sofia", cuenta="cta_daviplata", cuenta_destino_id="cta_davivienda",
            desc="Parte del arriendo")
        mov(d(2), 300_000, "aporte_bolsillo", cuenta="cta_davivienda", bolsillo_id="bol_emergencia", desc="Aporte")
        mov(d(2), 150_000, "aporte_bolsillo", cuenta="cta_nubank", bolsillo_id="bol_viaje", desc="Aporte")
        mov(d(4), 400_000, "transferencia", cuenta="cta_davivienda", cuenta_destino_id="cta_nubank", desc="Traslado")
        mov(d(6), 100_000, "transferencia", cuenta="cta_davivienda", cuenta_destino_id="cta_efectivo", desc="Retiro")

    mov(dia_en_mes_relativo(hoy, -3, 20), 1_800_000, cat="cat_hogar", cuenta="deu_tc_nu", desc="Nevera", cuotas=12)
    mov(dia_en_mes_relativo(hoy, -1, 28), 720_000, quien="usr_sofia", cat="cat_salud", cuenta="deu_tc_davi",
        desc="Gafas", cuotas=6)

    # Pagos: las tarjetas se pagan completas cada mes hasta el mes pasado; la moto, una cuota este ciclo.
    from app.services import deudas as servicio_deudas

    for i in range(-5, 1):
        for tarjeta in libro.deudas[:2]:
            fecha = dia_en_mes_relativo(hoy, i, tarjeta.dia_pago)
            estado = servicio_deudas.estado_tarjeta(tarjeta, libro.transacciones, fecha)
            if estado.pendiente_ciclo > 0:
                mov(fecha, estado.pendiente_ciclo, "pago_deuda", cuenta="cta_davivienda",
                    cuenta_destino_id=tarjeta.id, desc=f"Pago {tarjeta.nombre}")
    return libro
