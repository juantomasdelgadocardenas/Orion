"""Almacén en memoria: pruebas y modo demo (sin Google)."""
import copy
import threading

from app.domain import modelos as m
from app.repositories.almacen import Libro, NoEncontrado, tabla


class AlmacenMemoria:
    def __init__(self, libro: Libro | None = None):
        self._libro = libro or Libro()
        self._candado = threading.Lock()

    def leer(self) -> Libro:
        with self._candado:
            return copy.deepcopy(self._libro)

    def agregar(self, clave: str, filas: list[m.Fila]) -> None:
        with self._candado:
            getattr(self._libro, tabla(clave).clave).extend(copy.deepcopy(filas))

    def _indice(self, clave: str, id_: str) -> tuple[list, int]:
        t = tabla(clave)
        lista = getattr(self._libro, t.clave)
        for i, fila in enumerate(lista):
            if getattr(fila, t.campo_id) == id_:
                return lista, i
        raise NoEncontrado(f"No existe {id_} en {t.pestana}")

    def actualizar(self, clave: str, id_: str, fila: m.Fila) -> None:
        with self._candado:
            lista, i = self._indice(clave, id_)
            lista[i] = copy.deepcopy(fila)

    def eliminar(self, clave: str, id_: str) -> None:
        with self._candado:
            lista, i = self._indice(clave, id_)
            del lista[i]
