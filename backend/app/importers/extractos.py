"""Importación de extractos CSV/Excel sin conexión a bancos.

Lector genérico: reconoce las columnas por su encabezado (fecha, descripción, valor o débito/crédito),
así sirve para distintos bancos. El archivo se procesa en memoria y nunca se guarda.
"""
import csv
import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

from app.repositories.almacen import Libro

TAMANO_MAXIMO = 5 * 1024 * 1024
EXTENSIONES = {".csv", ".xlsx"}
FILAS_MAXIMAS = 5000

_PISTAS = {
    "fecha": ["fecha", "date"],
    "descripcion": ["descrip", "detalle", "concepto", "movimiento", "transacc", "referencia", "comercio"],
    "debito": ["debito", "cargo", "retiro", "egreso", "salida"],
    "credito": ["credito", "abono", "deposito", "ingreso", "entrada"],
    "monto": ["valor", "monto", "importe", "amount"],
}
_FORMATOS_FECHA = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d", "%d.%m.%Y", "%d %b %Y"]


class ArchivoInvalido(ValueError):
    pass


@dataclass
class Movimiento:
    fecha: date
    descripcion: str
    monto: int  # con signo: negativo = salida de plata


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def sanear_descripcion(texto) -> str:
    """Texto seguro para la hoja: sin prefijos de fórmula, sin números de cuenta completos, máx. 140."""
    limpio = re.sub(r"\s+", " ", str(texto or "")).strip()
    limpio = limpio.lstrip("=+-@\t\r ")
    limpio = re.sub(r"\d{8,}", lambda m: "****" + m.group()[-4:], limpio)
    return limpio[:140]


def leer_monto(valor) -> int | None:
    """Acepta 1.234.567,89 · 1,234,567.89 · $ 12.000 · (5.000) · -5000."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return round(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    negativo = texto.startswith("(") or "-" in texto
    texto = re.sub(r"[^\d.,]", "", texto)
    if not texto:
        return None
    ultimo = max(texto.rfind("."), texto.rfind(","))
    if ultimo >= 0 and len(texto) - ultimo - 1 in (1, 2):  # separador decimal
        entero, decimales = texto[:ultimo], texto[ultimo + 1:]
    else:
        entero, decimales = texto, ""
    entero = re.sub(r"[.,]", "", entero) or "0"
    numero = round(float(f"{entero}.{decimales or 0}"))
    return -numero if negativo else numero


def leer_fecha(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()[:20]
    for candidato in (texto, texto.split(" ")[0], texto.split("T")[0]):
        for formato in _FORMATOS_FECHA:
            try:
                return datetime.strptime(candidato, formato).date()
            except ValueError:
                continue
    return None


def _filas_csv(contenido: bytes) -> list[list]:
    if b"\x00" in contenido:
        raise ArchivoInvalido("El archivo no es un CSV de texto.")
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")
    muestra = texto[:4000]
    delimitador = max(";,\t|", key=muestra.count)
    return list(csv.reader(io.StringIO(texto), delimiter=delimitador))


def _filas_xlsx(contenido: bytes) -> list[list]:
    if not contenido.startswith(b"PK"):
        raise ArchivoInvalido("El archivo no es un Excel .xlsx válido.")
    from openpyxl import load_workbook

    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as error:  # archivo dañado o protegido con contraseña
        raise ArchivoInvalido("No pude abrir el Excel (¿está protegido con contraseña?).") from error
    hoja = libro.worksheets[0]
    return [list(fila) for fila in hoja.iter_rows(values_only=True, max_row=FILAS_MAXIMAS + 60)]


def _detectar_columnas(filas: list[list]) -> tuple[int, dict[str, int]]:
    for n, fila in enumerate(filas[:40]):
        columnas: dict[str, int] = {}
        for i, celda in enumerate(fila):
            texto = _plano(celda) if celda is not None else ""
            if not texto or len(texto) > 40:
                continue
            for campo, pistas in _PISTAS.items():
                if campo not in columnas and any(p in texto for p in pistas):
                    columnas[campo] = i
                    break
        tiene_valor = "monto" in columnas or "debito" in columnas or "credito" in columnas
        if "fecha" in columnas and tiene_valor:
            return n, columnas
    raise ArchivoInvalido(
        "No encontré los encabezados. El archivo necesita una columna de fecha y una de valor "
        "(o columnas de débito y crédito)."
    )


def leer_extracto(nombre: str, contenido: bytes) -> tuple[list[Movimiento], int]:
    """Devuelve (movimientos, filas_rechazadas)."""
    extension = "." + nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if extension not in EXTENSIONES:
        raise ArchivoInvalido("Solo se aceptan archivos .csv y .xlsx.")
    if not contenido:
        raise ArchivoInvalido("El archivo está vacío.")
    if len(contenido) > TAMANO_MAXIMO:
        raise ArchivoInvalido("El archivo supera los 5 MB.")
    filas = _filas_csv(contenido) if extension == ".csv" else _filas_xlsx(contenido)
    inicio, col = _detectar_columnas(filas)

    def celda(fila, campo):
        i = col.get(campo)
        return fila[i] if i is not None and i < len(fila) else None

    movimientos, rechazadas = [], 0
    for fila in filas[inicio + 1: inicio + 1 + FILAS_MAXIMAS]:
        if not any(str(c or "").strip() for c in fila):
            continue
        fecha = leer_fecha(celda(fila, "fecha"))
        monto = leer_monto(celda(fila, "monto"))
        if monto is None:
            debito, credito = leer_monto(celda(fila, "debito")), leer_monto(celda(fila, "credito"))
            if debito or credito:
                monto = abs(credito or 0) - abs(debito or 0)
        if fecha is None or not monto:
            rechazadas += 1
            continue
        movimientos.append(Movimiento(fecha, sanear_descripcion(celda(fila, "descripcion")), monto))
    return movimientos, rechazadas


def huella_archivo(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def huella_movimiento(cuenta_id: str, fecha: date, monto: int, descripcion: str, ordinal: int) -> str:
    base = f"{cuenta_id}|{fecha.isoformat()}|{monto}|{_plano(descripcion)}|{ordinal}"
    return hashlib.sha256(base.encode()).hexdigest()[:32]


def previsualizar(movimientos: list[Movimiento], cuenta_id: str, libro: Libro, es_tarjeta: bool) -> list[dict]:
    """Clasifica cada movimiento: nueva, duplicada (ya importada) o posible_duplicada (parece una captura manual)."""
    huellas = {x.huella_importacion for x in libro.transacciones if x.huella_importacion}
    manuales = [
        x for x in libro.transacciones
        if not x.huella_importacion and x.estado != "anulada" and cuenta_id in (x.cuenta_id, x.cuenta_destino_id)
    ]
    vistos: dict[tuple, int] = {}
    filas = []
    for mov in movimientos:
        clave = (mov.fecha, mov.monto, _plano(mov.descripcion))
        vistos[clave] = vistos.get(clave, 0) + 1
        huella = huella_movimiento(cuenta_id, mov.fecha, mov.monto, mov.descripcion, vistos[clave])
        # En una cuenta, negativo = gasto. En un extracto de tarjeta, positivo = compra.
        es_salida = mov.monto > 0 if es_tarjeta else mov.monto < 0
        if es_tarjeta:
            tipo = "gasto" if es_salida else "pago_deuda"
        else:
            tipo = "gasto" if es_salida else "ingreso"
        if huella in huellas:
            estado = "duplicada"
        elif any(x.monto == abs(mov.monto) and abs((x.fecha - mov.fecha).days) <= 2 for x in manuales):
            estado = "posible_duplicada"
        else:
            estado = "nueva"
        filas.append({
            "fecha": mov.fecha.isoformat(), "descripcion": mov.descripcion, "monto": abs(mov.monto),
            "tipo": tipo, "huella": huella, "estado": estado,
        })
    return filas
