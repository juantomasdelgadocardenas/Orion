"""Rutas HTTP. Sin lógica de negocio: valida, llama a servicios y responde."""
from datetime import date, datetime
from typing import Callable, Literal, get_args
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field, ValidationError

from app.core.auth import Bloqueado, GuardiaPin
from app.domain import modelos as m
from app.importers import extractos
from app.repositories.almacen import Almacen, NoEncontrado, ahora_iso, nuevo_id, tabla
from app.repositories.esquema import CONFIGURABLES, TABLAS
from app.services import tablero


class PinEntrada(BaseModel):
    pin: str = Field(min_length=1, max_length=12)


class TransaccionEntrada(BaseModel):
    monto: int = Field(gt=0, le=10_000_000_000)
    tipo: m.TipoTransaccion = "gasto"
    fecha: date | None = None
    responsable: str = ""
    categoria_id: str = ""
    cuenta_id: str
    cuenta_destino_id: str = ""
    bolsillo_id: str = ""
    gasto_fijo_id: str = ""
    descripcion: str = ""
    cuotas: int = Field(1, ge=1, le=72)


class FilaImportada(BaseModel):
    fecha: date
    monto: int = Field(gt=0)
    tipo: Literal["gasto", "ingreso", "pago_deuda"]
    descripcion: str = ""
    huella: str = Field(min_length=8, max_length=64)
    categoria_id: str = ""


class ConfirmarImportacion(BaseModel):
    cuenta_id: str
    responsable: str = ""
    huella_archivo: str = ""
    filas_leidas: int = 0
    filas_rechazadas: int = 0
    filas: list[FilaImportada] = Field(max_length=extractos.FILAS_MAXIMAS)


def _tipo_campo(anotacion) -> tuple[str, list[str]]:
    args = get_args(anotacion)
    if args and all(isinstance(a, str) for a in args):
        return "opcion", list(args)
    tipos = (anotacion, *args)
    for tipo, nombre in ((bool, "booleano"), (int, "entero"), (float, "decimal"), (date, "fecha")):
        if tipo in tipos:
            return nombre, []
    return "texto", []


def describir_tablas() -> dict:
    """Metadatos para que el frontend arme los formularios de Ajustes sin conocer cada tabla."""
    salida = {}
    for clave in CONFIGURABLES:
        t = TABLAS[clave]
        campos = []
        for nombre, info in t.modelo.model_fields.items():
            extra = info.json_schema_extra or {}
            if extra.get("oculto"):
                continue
            tipo, opciones = _tipo_campo(info.annotation)
            campos.append({"nombre": nombre, "titulo": info.title or nombre, "tipo": tipo, "opciones": opciones,
                           "requerido": info.is_required(),
                           "defecto": None if info.is_required() else info.default, **extra})
        salida[clave] = {"pestana": t.pestana, "singular": t.singular, "campos": campos}
    return salida


def _referencias(libro, clave: str, id_: str) -> int:
    x = libro.transacciones
    if clave in ("cuentas", "deudas"):
        return sum(1 for t in x if id_ in (t.cuenta_id, t.cuenta_destino_id))
    campo = {"bolsillos": "bolsillo_id", "categorias": "categoria_id", "gastos_fijos": "gasto_fijo_id",
             "usuarios": "responsable"}[clave]
    return sum(1 for t in x if getattr(t, campo) == id_)


def crear_rutas(almacen: Almacen, guardia: GuardiaPin, modo: str, reloj: Callable[[], date] | None = None) -> APIRouter:
    r = APIRouter(prefix="/api")

    def hoy() -> date:
        if reloj:
            return reloj()
        zona = almacen.leer().ajuste("zona_horaria") or "America/Bogota"
        try:
            return datetime.now(ZoneInfo(zona)).date()
        except Exception:
            return date.today()

    def sesion(authorization: str = Header(default="")) -> None:
        token = authorization.removeprefix("Bearer ").strip()
        if not token or not guardia.validar(token):
            raise HTTPException(401, "Sesión no válida. Ingresa el PIN.")

    protegido = [Depends(sesion)]

    @r.get("/salud")
    def salud():
        return {"ok": True, "app": "orion", "modo": modo}

    @r.post("/auth/desbloquear")
    def desbloquear(entrada: PinEntrada):
        try:
            return {"token": guardia.desbloquear(entrada.pin)}
        except Bloqueado as b:
            raise HTTPException(429, f"Demasiados intentos. Espera {b.segundos // 60 + 1} min.")
        except PermissionError:
            raise HTTPException(401, "PIN incorrecto")

    @r.get("/tablero", dependencies=protegido)
    def ver_tablero(responsable: str | None = None):
        datos = tablero.construir(almacen.leer(), hoy(), responsable or None)
        datos["modo"] = modo
        return datos

    @r.post("/transacciones", dependencies=protegido, status_code=201)
    def crear_transaccion(entrada: TransaccionEntrada, tareas: BackgroundTasks):
        libro = almacen.leer()
        origenes = {c.id for c in libro.cuentas} | {d.id for d in libro.deudas}
        if entrada.cuenta_id not in origenes:
            raise HTTPException(422, "La cuenta no existe")
        if entrada.cuenta_destino_id and entrada.cuenta_destino_id not in origenes:
            raise HTTPException(422, "La cuenta de destino no existe")
        if entrada.tipo in ("transferencia", "pago_deuda") and not entrada.cuenta_destino_id:
            raise HTTPException(422, "Falta la cuenta de destino")
        es_tarjeta = any(d.id == entrada.cuenta_id and d.tipo == "tarjeta_credito" for d in libro.deudas)
        marca = ahora_iso()
        nueva = m.Transaccion(
            **entrada.model_dump(exclude={"fecha", "descripcion", "cuotas"}),
            id=nuevo_id(TABLAS["transacciones"]),
            fecha=entrada.fecha or hoy(),
            descripcion=extractos.sanear_descripcion(entrada.descripcion),
            cuotas=entrada.cuotas if es_tarjeta and entrada.tipo == "gasto" else 1,
            creado_por=entrada.responsable, creado_en=marca, actualizado_en=marca,
        )
        almacen.agregar("transacciones", [nueva])
        tareas.add_task(tablero.refrescar_caches, almacen, hoy())
        return nueva.model_dump(mode="json")

    @r.delete("/transacciones/{id_}", dependencies=protegido)
    def anular_transaccion(id_: str, tareas: BackgroundTasks):
        actual = next((x for x in almacen.leer().transacciones if x.id == id_), None)
        if actual is None:
            raise HTTPException(404, "No existe ese movimiento")
        almacen.actualizar("transacciones", id_, actual.model_copy(
            update={"estado": "anulada", "actualizado_en": ahora_iso()}))
        tareas.add_task(tablero.refrescar_caches, almacen, hoy())
        return {"ok": True}

    # --- Ajustes: CRUD genérico de las tablas configurables --------------------
    def _tabla_configurable(clave: str):
        if clave not in CONFIGURABLES:
            raise HTTPException(404, "Tabla no configurable")
        return tabla(clave)

    def _validar(t, datos: dict):
        try:
            return t.modelo.model_validate(datos)
        except ValidationError as error:
            primero = error.errors()[0]
            raise HTTPException(422, f"{'.'.join(map(str, primero['loc']))}: {primero['msg']}")

    @r.get("/config/esquema", dependencies=protegido)
    def esquema():
        return describir_tablas()

    @r.get("/config/{clave}", dependencies=protegido)
    def listar(clave: str):
        t = _tabla_configurable(clave)
        return [f.model_dump(mode="json") for f in getattr(almacen.leer(), t.clave)]

    @r.post("/config/{clave}", dependencies=protegido, status_code=201)
    def crear(clave: str, datos: dict, tareas: BackgroundTasks):
        t = _tabla_configurable(clave)
        fila = _validar(t, {**datos, "id": nuevo_id(t)})
        if "actualizado_en" in t.columnas:
            fila = fila.model_copy(update={"actualizado_en": ahora_iso()})
        almacen.agregar(clave, [fila])
        tareas.add_task(tablero.refrescar_caches, almacen, hoy())
        return fila.model_dump(mode="json")

    @r.put("/config/{clave}/{id_}", dependencies=protegido)
    def editar(clave: str, id_: str, datos: dict, tareas: BackgroundTasks):
        t = _tabla_configurable(clave)
        actual = next((f for f in getattr(almacen.leer(), t.clave) if f.id == id_), None)
        if actual is None:
            raise HTTPException(404, "No existe")
        # Los campos vacíos del formulario vuelven a su valor por defecto; los ocultos se conservan.
        ocultos = {k: v for k, v in actual.model_dump().items()
                   if (t.modelo.model_fields[k].json_schema_extra or {}).get("oculto")}
        fila = _validar(t, {**ocultos, **datos, "id": id_})
        if "actualizado_en" in t.columnas:
            fila = fila.model_copy(update={"actualizado_en": ahora_iso()})
        almacen.actualizar(clave, id_, fila)
        tareas.add_task(tablero.refrescar_caches, almacen, hoy())
        return fila.model_dump(mode="json")

    @r.delete("/config/{clave}/{id_}", dependencies=protegido)
    def borrar(clave: str, id_: str):
        _tabla_configurable(clave)
        usos = _referencias(almacen.leer(), clave, id_)
        if usos:
            raise HTTPException(409, f"Tiene {usos} movimiento(s) asociados. Desactívala en lugar de borrarla.")
        try:
            almacen.eliminar(clave, id_)
        except NoEncontrado:
            raise HTTPException(404, "No existe")
        return {"ok": True}

    # --- Importación de extractos ------------------------------------------------
    @r.post("/importacion/previsualizar", dependencies=protegido)
    async def previsualizar(archivo: UploadFile = File(...), cuenta_id: str = Form(...)):
        contenido = await archivo.read(extractos.TAMANO_MAXIMO + 1)
        libro = almacen.leer()
        deuda = next((d for d in libro.deudas if d.id == cuenta_id), None)
        if deuda is None and not any(c.id == cuenta_id for c in libro.cuentas):
            raise HTTPException(422, "La cuenta no existe")
        try:
            movimientos, rechazadas = extractos.leer_extracto(archivo.filename or "", contenido)
        except extractos.ArchivoInvalido as error:
            raise HTTPException(422, str(error))
        huella = extractos.huella_archivo(contenido)
        return {
            "huella_archivo": huella,
            "ya_importado": any(i.huella_archivo == huella for i in libro.importaciones),
            "filas_leidas": len(movimientos) + rechazadas,
            "filas_rechazadas": rechazadas,
            "filas": extractos.previsualizar(movimientos, cuenta_id, libro, es_tarjeta=deuda is not None),
        }

    @r.post("/importacion/confirmar", dependencies=protegido)
    def confirmar(entrada: ConfirmarImportacion, tareas: BackgroundTasks):
        libro = almacen.leer()
        deuda = next((d for d in libro.deudas if d.id == entrada.cuenta_id), None)
        cuentas = [c for c in libro.cuentas if c.incluir_en_dinero_real and c.activa]
        if deuda is None and not any(c.id == entrada.cuenta_id for c in libro.cuentas):
            raise HTTPException(422, "La cuenta no existe")
        existentes = {x.huella_importacion for x in libro.transacciones if x.huella_importacion}
        marca, nuevas, duplicadas = ahora_iso(), [], 0
        for i, fila in enumerate(entrada.filas):
            if fila.huella in existentes:
                duplicadas += 1
                continue
            existentes.add(fila.huella)
            es_pago = fila.tipo == "pago_deuda" and deuda is not None
            nuevas.append(m.Transaccion(
                id=f"{nuevo_id(TABLAS['transacciones'])}{i:x}", fecha=fila.fecha, monto=fila.monto,
                tipo=fila.tipo if (es_pago or fila.tipo != "pago_deuda") else "gasto",
                responsable=entrada.responsable, categoria_id=fila.categoria_id,
                # Un pago visto en el extracto de la tarjeta sale de una cuenta que el extracto no dice.
                cuenta_id=(cuentas[0].id if cuentas else "") if es_pago else entrada.cuenta_id,
                cuenta_destino_id=entrada.cuenta_id if es_pago else "",
                descripcion=extractos.sanear_descripcion(fila.descripcion),
                estado="confirmada", origen="importacion", huella_importacion=fila.huella,
                creado_por=entrada.responsable, creado_en=marca, actualizado_en=marca,
            ))
        almacen.agregar("transacciones", nuevas)
        almacen.agregar("importaciones", [m.Importacion(
            id=nuevo_id(TABLAS["importaciones"]), fecha=marca, responsable=entrada.responsable,
            cuenta_id=entrada.cuenta_id, huella_archivo=entrada.huella_archivo,
            filas_leidas=entrada.filas_leidas, filas_nuevas=len(nuevas),
            filas_duplicadas=duplicadas, filas_rechazadas=entrada.filas_rechazadas,
        )])
        tareas.add_task(tablero.refrescar_caches, almacen, hoy())
        return {"nuevas": len(nuevas), "duplicadas": duplicadas}

    return r
