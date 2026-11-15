import io
from datetime import date

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.core.config import Ajustes
from app.domain import modelos as m
from app.importers import extractos
from app.main import crear_app
from app.repositories.almacen import a_celdas, de_celdas
from app.repositories.demo import libro_demo
from app.repositories.esquema import TABLAS
from app.repositories.memoria import AlmacenMemoria

HOY = date(2026, 11, 15)


@pytest.fixture
def cliente():
    ajustes = Ajustes(orion_modo="demo", orion_pin="4821", _env_file=None)
    app = crear_app(ajustes, AlmacenMemoria(libro_demo(HOY)), reloj=lambda: HOY)
    c = TestClient(app)
    token = c.post("/api/auth/desbloquear", json={"pin": "4821"}).json()["token"]
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def test_pin_protege_y_bloquea():
    app = crear_app(Ajustes(orion_modo="demo", orion_pin="4821", _env_file=None), AlmacenMemoria(), reloj=lambda: HOY)
    c = TestClient(app)
    assert c.get("/api/tablero").status_code == 401
    assert c.get("/api/tablero", headers={"Authorization": "Bearer 9999999999.abc"}).status_code == 401
    for _ in range(4):
        assert c.post("/api/auth/desbloquear", json={"pin": "0000"}).status_code == 401
    assert c.post("/api/auth/desbloquear", json={"pin": "0000"}).status_code == 429
    assert c.post("/api/auth/desbloquear", json={"pin": "4821"}).status_code == 429  # sigue bloqueado


def test_libro_vacio_no_rompe():
    app = crear_app(Ajustes(orion_modo="demo", orion_pin="4821", _env_file=None), AlmacenMemoria(), reloj=lambda: HOY)
    c = TestClient(app)
    token = c.post("/api/auth/desbloquear", json={"pin": "4821"}).json()["token"]
    datos = c.get("/api/tablero", headers={"Authorization": f"Bearer {token}"}).json()
    assert datos["dinero_real"]["total"] == 0 and datos["deudas"] == [] and datos["alertas"] == []


def test_tablero_demo(cliente):
    datos = cliente.get("/api/tablero").json()
    assert len(datos["flujo"]) == 6 and all(f["ingresos"] > 0 for f in datos["flujo"])
    moto = next(d for d in datos["deudas"] if d["id"] == "deu_moto")
    assert moto["cuotas_pagadas"] == 10 and len(moto["plan"]) == 24 and moto["proximo_pago"] == "2026-11-20"
    meta = next(x for x in datos["metas"] if x["id"] == "bol_moto")
    assert meta["avance"] == moto["avance"] > 0
    assert any(a["tipo"] == "pago_cercano" for a in datos["alertas"])
    dr = datos["dinero_real"]
    assert dr["total"] == dr["saldo_bruto"] - dr["gastos_fijos"] - dr["deudas"] - dr["ahorro"]


def test_captura_rapida_y_deshacer(cliente):
    antes = cliente.get("/api/tablero").json()
    r = cliente.post("/api/transacciones", json={"monto": 25_000, "cuenta_id": "cta_efectivo",
                                                 "categoria_id": "cat_restaurantes", "responsable": "usr_sofia",
                                                 "descripcion": "=HYPERLINK(\"x\") almuerzo"})
    assert r.status_code == 201 and r.json()["fecha"] == "2026-11-15"
    assert not r.json()["descripcion"].startswith("=")
    despues = cliente.get("/api/tablero").json()
    assert despues["dinero_real"]["total"] == antes["dinero_real"]["total"] - 25_000
    assert cliente.delete(f"/api/transacciones/{r.json()['id']}").status_code == 200
    assert cliente.get("/api/tablero").json()["dinero_real"]["total"] == antes["dinero_real"]["total"]
    assert cliente.post("/api/transacciones", json={"monto": 5, "cuenta_id": "no_existe"}).status_code == 422


def test_compra_a_cuotas_en_tarjeta(cliente):
    r = cliente.post("/api/transacciones", json={"monto": 600_000, "cuenta_id": "deu_tc_nu", "cuotas": 6,
                                                 "categoria_id": "cat_hogar", "descripcion": "Silla"})
    assert r.json()["cuotas"] == 6
    tarjeta = next(d for d in cliente.get("/api/tablero").json()["deudas"] if d["id"] == "deu_tc_nu")
    silla = next(c for c in tarjeta["compras"] if c["descripcion"] == "Silla")
    assert silla["cuotas"] == 6 and silla["restante"] == 600_000


def test_ajustes_crud(cliente):
    esquema = cliente.get("/api/config/esquema").json()
    assert {"usuarios", "cuentas", "deudas", "bolsillos", "categorias", "gastos_fijos"} == set(esquema)
    assert all(c["nombre"] != "saldo_actual" for c in esquema["cuentas"]["campos"])
    nueva = cliente.post("/api/config/cuentas", json={"nombre": "Nequi", "tipo": "billetera", "institucion": "Nequi",
                                                      "saldo_inicial": 50_000, "fecha_saldo_inicial": "2026-11-01"})
    assert nueva.status_code == 201
    id_ = nueva.json()["id"]
    assert cliente.put(f"/api/config/cuentas/{id_}", json={**nueva.json(), "nombre": "Nequi Sofi"}).json()["nombre"] == "Nequi Sofi"
    assert cliente.post("/api/config/cuentas", json={"nombre": "x", "tipo": "raro",
                                                     "fecha_saldo_inicial": "2026-11-01"}).status_code == 422
    assert cliente.delete(f"/api/config/cuentas/{id_}").status_code == 200
    assert cliente.delete("/api/config/cuentas/cta_davivienda").status_code == 409  # tiene movimientos


CSV = """Extracto de cuenta;;;
Fecha;Descripción;Valor;Saldo
01/11/2026;COMPRA EXITO 1234567890123;-85.300,00;1.000.000,00
02/11/2026;=cmd|' /C calc'!A0;-12.000;988.000
03/11/2026;TRANSFERENCIA RECIBIDA;"250.000,80";1.238.000
;fila sin fecha;100;0
"""


def test_lectura_de_montos():
    assert extractos.leer_monto("1.234.567,89") == 1_234_568
    assert extractos.leer_monto("$ 1,234,567.89") == 1_234_568
    assert extractos.leer_monto("12.000") == 12_000
    assert extractos.leer_monto("(5.000)") == -5_000
    assert extractos.leer_monto("-85.300,00") == -85_300
    assert extractos.leer_monto("") is None


def test_importacion_idempotente(cliente):
    def subir():
        return cliente.post("/api/importacion/previsualizar", data={"cuenta_id": "cta_davivienda"},
                            files={"archivo": ("extracto.csv", CSV.encode("latin-1"), "text/csv")})

    previa = subir().json()
    assert previa["filas_rechazadas"] == 1 and len(previa["filas"]) == 3
    f1, f2, f3 = previa["filas"]
    assert (f1["tipo"], f1["monto"], f1["estado"]) == ("gasto", 85_300, "nueva")
    assert "1234567890123" not in f1["descripcion"] and "****0123" in f1["descripcion"]
    assert not f2["descripcion"].startswith("=")
    assert (f3["tipo"], f3["monto"]) == ("ingreso", 250_001)
    cuerpo = {"cuenta_id": "cta_davivienda", "responsable": "usr_juan", "huella_archivo": previa["huella_archivo"],
              "filas": previa["filas"]}
    assert cliente.post("/api/importacion/confirmar", json=cuerpo).json() == {"nuevas": 3, "duplicadas": 0}
    otra = subir().json()
    assert otra["ya_importado"] and all(f["estado"] == "duplicada" for f in otra["filas"])
    assert cliente.post("/api/importacion/confirmar", json=cuerpo).json() == {"nuevas": 0, "duplicadas": 3}


def test_importacion_excel_y_rechazos(cliente):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Fecha", "Detalle", "Débitos", "Créditos"])
    hoja.append([date(2026, 11, 3), "Pago servicios", 120000, None])
    hoja.append([date(2026, 11, 4), "Abono nómina", None, 3000000])
    flujo = io.BytesIO()
    libro.save(flujo)
    r = cliente.post("/api/importacion/previsualizar", data={"cuenta_id": "cta_nubank"},
                     files={"archivo": ("mov.xlsx", flujo.getvalue(), "application/octet-stream")})
    assert [(f["tipo"], f["monto"]) for f in r.json()["filas"]] == [("gasto", 120_000), ("ingreso", 3_000_000)]
    for nombre, contenido in [("macro.xlsm", b"PK"), ("falso.xlsx", b"no soy excel"), ("sin.csv", b"a,b\n1,2\n")]:
        mal = cliente.post("/api/importacion/previsualizar", data={"cuenta_id": "cta_nubank"},
                           files={"archivo": (nombre, contenido, "text/plain")})
        assert mal.status_code == 422, nombre


def test_ida_y_vuelta_de_celdas_tolera_lo_que_devuelve_sheets():
    t = TABLAS["cuentas"]
    cuenta = m.Cuenta(id="c", nombre="Banco", saldo_inicial=10, fecha_saldo_inicial=date(2026, 11, 1))
    celdas = a_celdas(t, cuenta)
    assert celdas[t.columnas.index("fecha_saldo_inicial")] == "2026-11-01"
    assert de_celdas(t, t.columnas, celdas) == cuenta
    # Lo que llega cuando alguien edita la hoja a mano: fecha como número de serie, booleano en español,
    # número donde va texto, celdas finales ausentes.
    crudo = ["c", 123, "ahorros", "", "", "COP", 10.0, 46327, "", "VERDADERO"]
    leida = de_celdas(t, t.columnas, crudo)
    assert leida.nombre == "123" and leida.fecha_saldo_inicial == date(2026, 11, 1)
    assert leida.incluir_en_dinero_real is True and leida.activa is True
