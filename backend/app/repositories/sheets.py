"""Almacén sobre Google Sheets. Único módulo (junto a google_auth) que usa gspread."""
import threading
import time

import gspread

from app.domain import modelos as m
from app.repositories.almacen import Libro, NoEncontrado, a_celdas, de_celdas, tabla
from app.repositories.esquema import CONFIG_POR_DEFECTO, TABLAS

TTL_CACHE = 20  # segundos; la API de Sheets limita las lecturas por minuto


class EsquemaInvalido(RuntimeError):
    pass


def _letra(n: int) -> str:
    texto = ""
    while n:
        n, resto = divmod(n - 1, 26)
        texto = chr(65 + resto) + texto
    return texto


class AlmacenSheets:
    def __init__(self, libro: gspread.Spreadsheet):
        self._sh = libro
        self._cache: tuple[float, Libro] | None = None
        self._candado = threading.Lock()

    # --- esquema -----------------------------------------------------------
    def crear_esquema(self) -> list[str]:
        """Crea pestañas y encabezados que falten. No toca datos existentes. Devuelve lo que hizo."""
        hecho = []
        existentes = {ws.title: ws for ws in self._sh.worksheets()}
        for t in TABLAS.values():
            ws = existentes.get(t.pestana)
            if ws is None:
                ws = self._sh.add_worksheet(title=t.pestana, rows=200, cols=len(t.columnas))
                hecho.append(f"pestaña creada: {t.pestana}")
            actuales = ws.row_values(1)
            if not actuales:
                ws.update(range_name="A1", values=[t.columnas], value_input_option="RAW")
                ws.freeze(rows=1)
                hecho.append(f"encabezados escritos: {t.pestana}")
            elif actuales[: len(t.columnas)] != t.columnas:
                raise EsquemaInvalido(self._mensaje(t.pestana, t.columnas, actuales))
        cfg = self._sh.worksheet(TABLAS["config"].pestana)
        claves = set(cfg.col_values(1)[1:])
        faltan = [[k, v] for k, v in CONFIG_POR_DEFECTO.items() if k not in claves]
        if faltan:
            cfg.append_rows(faltan, value_input_option="RAW", table_range="A1")
            hecho.append(f"config por defecto: {len(faltan)} claves")
        self._cache = None
        return hecho

    @staticmethod
    def _mensaje(pestana: str, esperadas: list[str], actuales: list[str]) -> str:
        return (
            f"Los encabezados de la pestaña '{pestana}' no coinciden.\n"
            f"  esperados: {esperadas}\n  encontrados: {actuales}"
        )

    # --- lectura -----------------------------------------------------------
    def leer(self) -> Libro:
        with self._candado:
            if self._cache and time.monotonic() - self._cache[0] < TTL_CACHE:
                return self._cache[1]
            tablas = list(TABLAS.values())
            respuesta = self._sh.values_batch_get(
                ranges=[f"'{t.pestana}'!A1:{_letra(len(t.columnas))}" for t in tablas],
                params={"valueRenderOption": "UNFORMATTED_VALUE"},
            )
            libro = Libro()
            for t, rango in zip(tablas, respuesta.get("valueRanges", [])):
                valores = rango.get("values", [])
                if not valores:
                    raise EsquemaInvalido(f"La pestaña '{t.pestana}' no tiene encabezados. Ejecuta crear_esquema.")
                encabezados = [str(c).strip() for c in valores[0]]
                if encabezados != t.columnas:
                    raise EsquemaInvalido(self._mensaje(t.pestana, t.columnas, encabezados))
                filas = []
                for n, celdas in enumerate(valores[1:], start=2):
                    if not any(str(c).strip() for c in celdas):
                        continue
                    try:
                        filas.append(de_celdas(t, encabezados, celdas))
                    except ValueError as error:
                        raise EsquemaInvalido(f"Fila {n} de '{t.pestana}' inválida: {error}") from error
                setattr(libro, t.clave, filas)
            self._cache = (time.monotonic(), libro)
            return libro

    # --- escritura (siempre RAW: ningún texto se interpreta como fórmula) ----
    def agregar(self, clave: str, filas: list[m.Fila]) -> None:
        if not filas:
            return
        t = tabla(clave)
        with self._candado:
            self._sh.worksheet(t.pestana).append_rows(
                [a_celdas(t, f) for f in filas], value_input_option="RAW", table_range="A1"
            )
            self._cache = None

    def _fila_de(self, ws: gspread.Worksheet, t, id_: str) -> int:
        columna = t.columnas.index(t.campo_id) + 1
        ids = ws.col_values(columna)
        for n, valor in enumerate(ids[1:], start=2):
            if str(valor) == id_:
                return n
        raise NoEncontrado(f"No existe {id_} en {t.pestana}")

    def actualizar(self, clave: str, id_: str, fila: m.Fila) -> None:
        t = tabla(clave)
        with self._candado:
            ws = self._sh.worksheet(t.pestana)
            n = self._fila_de(ws, t, id_)
            ws.update(
                range_name=f"A{n}:{_letra(len(t.columnas))}{n}",
                values=[a_celdas(t, fila)],
                value_input_option="RAW",
            )
            self._cache = None

    def eliminar(self, clave: str, id_: str) -> None:
        t = tabla(clave)
        with self._candado:
            ws = self._sh.worksheet(t.pestana)
            ws.delete_rows(self._fila_de(ws, t, id_))
            self._cache = None
