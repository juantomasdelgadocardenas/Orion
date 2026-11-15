import type { Esquema, Fila, NuevaTransaccion, Tablero, Transaccion, VistaPrevia } from './tipos'

const guardado = (clave: string) => { try { return localStorage.getItem(clave) } catch { return null } }
const guardar = (clave: string, valor: string | null) => {
  try { valor === null ? localStorage.removeItem(clave) : localStorage.setItem(clave, valor) } catch { /* sin almacenamiento */ }
}

export const sesion = {
  get token() { return guardado('orion_token') },
  set token(v: string | null) { guardar('orion_token', v) },
  get usuario() { return guardado('orion_usuario') },
  set usuario(v: string | null) { guardar('orion_usuario', v) },
  /** Dirección del backend. En la extensión, por defecto el computador local. */
  get servidor() {
    return guardado('orion_servidor') ?? (location.protocol === 'chrome-extension:' ? 'http://localhost:8000' : '')
  },
  set servidor(v: string) { guardar('orion_servidor', v.trim().replace(/\/+$/, '')) },
}

export class ErrorApi extends Error {
  constructor(public estado: number, mensaje: string) { super(mensaje) }
}

async function pedir<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const cabeceras: Record<string, string> = { ...(opciones.headers as Record<string, string>) }
  if (sesion.token) cabeceras.Authorization = `Bearer ${sesion.token}`
  if (typeof opciones.body === 'string') cabeceras['Content-Type'] = 'application/json'
  let r: Response
  try {
    r = await fetch(`${sesion.servidor}/api${ruta}`, { ...opciones, headers: cabeceras })
  } catch {
    throw new ErrorApi(0, 'No pude conectar con el servidor de Orion. ¿Está encendido?')
  }
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => ({}))
    throw new ErrorApi(r.status, typeof cuerpo.detail === 'string' ? cuerpo.detail : `Error ${r.status}`)
  }
  return r.json()
}

const json = (metodo: string, datos: unknown): RequestInit => ({ method: metodo, body: JSON.stringify(datos) })

export const api = {
  desbloquear: (pin: string) => pedir<{ token: string }>('/auth/desbloquear', json('POST', { pin })),
  tablero: (responsable?: string) => pedir<Tablero>(`/tablero${responsable ? `?responsable=${encodeURIComponent(responsable)}` : ''}`),
  crearTransaccion: (t: NuevaTransaccion) => pedir<Transaccion>('/transacciones', json('POST', t)),
  anularTransaccion: (id: string) => pedir<unknown>(`/transacciones/${id}`, { method: 'DELETE' }),
  esquema: () => pedir<Esquema>('/config/esquema'),
  listar: (tabla: string) => pedir<Fila[]>(`/config/${tabla}`),
  crear: (tabla: string, fila: Fila) => pedir<Fila>(`/config/${tabla}`, json('POST', fila)),
  editar: (tabla: string, id: string, fila: Fila) => pedir<Fila>(`/config/${tabla}/${id}`, json('PUT', fila)),
  borrar: (tabla: string, id: string) => pedir<unknown>(`/config/${tabla}/${id}`, { method: 'DELETE' }),
  previsualizar: (archivo: File, cuentaId: string) => {
    const cuerpo = new FormData()
    cuerpo.append('archivo', archivo)
    cuerpo.append('cuenta_id', cuentaId)
    return pedir<VistaPrevia>('/importacion/previsualizar', { method: 'POST', body: cuerpo })
  },
  confirmarImportacion: (datos: unknown) => pedir<{ nuevas: number; duplicadas: number }>('/importacion/confirmar', json('POST', datos)),
}
