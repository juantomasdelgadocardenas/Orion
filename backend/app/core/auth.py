"""Acceso por PIN: sesión firmada con HMAC y bloqueo temporal ante intentos fallidos."""
import hashlib
import hmac
import secrets
import time

DURACION_SESION = 30 * 24 * 3600
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 5 * 60


class Bloqueado(Exception):
    def __init__(self, segundos: int):
        self.segundos = segundos


class GuardiaPin:
    def __init__(self, pin: str, secreto: str | None = None, reloj=time.time):
        self._pin = pin
        self._clave = (secreto or secrets.token_hex(32)).encode()
        self._reloj = reloj
        self._fallos = 0
        self._bloqueado_hasta = 0.0

    def _firma(self, expira: int) -> str:
        return hmac.new(self._clave, str(expira).encode(), hashlib.sha256).hexdigest()

    def desbloquear(self, pin: str) -> str:
        ahora = self._reloj()
        if ahora < self._bloqueado_hasta:
            raise Bloqueado(int(self._bloqueado_hasta - ahora) + 1)
        if not hmac.compare_digest(pin.encode(), self._pin.encode()):
            self._fallos += 1
            if self._fallos >= MAX_INTENTOS:
                self._fallos = 0
                self._bloqueado_hasta = ahora + BLOQUEO_SEGUNDOS
                raise Bloqueado(BLOQUEO_SEGUNDOS)
            raise PermissionError("PIN incorrecto")
        self._fallos = 0
        expira = int(ahora) + DURACION_SESION
        return f"{expira}.{self._firma(expira)}"

    def validar(self, token: str) -> bool:
        try:
            expira_txt, firma = token.split(".", 1)
            expira = int(expira_txt)
        except ValueError:
            return False
        return expira > self._reloj() and hmac.compare_digest(firma, self._firma(expira))
