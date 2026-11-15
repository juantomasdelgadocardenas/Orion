import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ErrorApi, sesion } from './api'
import type { InicioCaptura, NuevaTransaccion, Tablero } from './tipos'
import { dinero } from './formato'
import { Vacio } from './ui'
import Bloqueo from './vistas/Bloqueo'
import Inicio from './vistas/Inicio'
import Captura from './vistas/Captura'
import Deudas from './vistas/Deudas'
import Importar from './vistas/Importar'
import Ajustes from './vistas/Ajustes'
import PanelAlertas, { alertasVisibles } from './vistas/Alertas'

type Pestana = 'inicio' | 'deudas' | 'importar' | 'ajustes'
const PESTANAS: [Pestana, string, string][] = [
  ['inicio', '◎', 'Inicio'], ['deudas', '▤', 'Deudas'], ['importar', '⇪', 'Importar'], ['ajustes', '⚙', 'Ajustes'],
]

interface Aviso { texto: string; deshacer?: () => void }

export default function App() {
  const [conSesion, setConSesion] = useState(!!sesion.token)
  const [tablero, setTablero] = useState<Tablero | null>(null)
  const [error, setError] = useState('')
  const [pestana, setPestana] = useState<Pestana>('inicio')
  const [filtro, setFiltro] = useState('')
  const [captura, setCaptura] = useState<InicioCaptura | null>(null)
  const [verAlertas, setVerAlertas] = useState(false)
  const [descartadas, setDescartadas] = useState<string[]>(() => JSON.parse(localStorage.getItem('orion_alertas') ?? '[]'))
  const [usuario, setUsuario] = useState(sesion.usuario ?? '')
  const [aviso, setAviso] = useState<Aviso | null>(null)
  const reloj = useRef(0)

  const avisar = useCallback((a: Aviso) => {
    setAviso(a)
    clearTimeout(reloj.current)
    reloj.current = window.setTimeout(() => setAviso(null), 6000)
  }, [])

  const cargar = useCallback(async () => {
    try {
      setTablero(await api.tablero(filtro || undefined))
      setError('')
    } catch (e) {
      if (e instanceof ErrorApi && e.estado === 401) { sesion.token = null; setConSesion(false) }
      else setError((e as Error).message)
    }
  }, [filtro])

  useEffect(() => { if (conSesion) cargar() }, [conSesion, cargar])

  // Quien usa la app: si no se ha elegido, la primera persona configurada.
  useEffect(() => {
    if (tablero && !tablero.usuarios.some(u => u.id === usuario) && tablero.usuarios[0]) setUsuario(tablero.usuarios[0].id)
  }, [tablero, usuario])
  useEffect(() => { if (usuario) sesion.usuario = usuario }, [usuario])

  const guardar = async (t: NuevaTransaccion) => {
    setCaptura(null) // la hoja se cierra de inmediato; no se espera a la hoja de cálculo
    try {
      const creada = await api.crearTransaccion(t)
      avisar({
        texto: `Guardado · ${dinero(t.monto)}`,
        deshacer: async () => { setAviso(null); await api.anularTransaccion(creada.id); cargar() },
      })
      cargar()
    } catch (e) {
      avisar({ texto: `No se guardó: ${(e as Error).message}` })
    }
  }

  const descartar = (id: string) => {
    const nuevas = [...descartadas, id].slice(-200)
    setDescartadas(nuevas)
    localStorage.setItem('orion_alertas', JSON.stringify(nuevas))
  }

  if (!conSesion) return <Bloqueo alEntrar={() => setConSesion(true)} />

  const salir = () => { sesion.token = null; setTablero(null); setConSesion(false) }
  const alertas = tablero ? alertasVisibles(tablero.alertas, descartadas) : []
  const criticas = alertas.filter(a => a.severidad === 'critica')

  return (
    <div className="app">
      <header className="barra-sup">
        <img src="./icons/icon-128.png" alt="" />
        <h1>Orion</h1>
        {tablero?.modo === 'demo' && <span className="insignia" title="Datos de ejemplo, no reales">Demo</span>}
        <button className="boton-icono" onClick={() => setVerAlertas(true)} aria-label={`Alertas: ${alertas.length}`}>
          🔔{alertas.length > 0 && <span className="punto">{alertas.length}</span>}
        </button>
      </header>

      {error && <div className="tarjeta"><Vacio icono="📡" titulo="Sin conexión con Orion">{error}</Vacio>
        <button className="boton secundario" onClick={cargar}>Reintentar</button></div>}
      {!tablero && !error && <Vacio icono="🐈" titulo="Cargando…" />}

      {tablero && pestana === 'inicio' && (
        <>
          {criticas.length > 0 && (
            <button className="franja" onClick={() => setVerAlertas(true)}>
              <span aria-hidden>⚠️</span>
              <b>{criticas.length === 1 ? criticas[0].titulo : `${criticas.length} alertas importantes`}</b>
              <span className="tenue">Ver</span>
            </button>
          )}
          <Inicio t={tablero} filtro={filtro} alFiltrar={setFiltro} abrirCaptura={setCaptura}
            irA={p => setPestana(p)} />
        </>
      )}
      {tablero && pestana === 'deudas' && <Deudas t={tablero} abrirCaptura={setCaptura} />}
      {tablero && pestana === 'importar' && <Importar t={tablero} usuario={usuario} alTerminar={texto => { avisar({ texto }); cargar() }} />}
      {tablero && pestana === 'ajustes' && (
        <Ajustes t={tablero} usuario={usuario} alElegirUsuario={setUsuario} alCambiar={cargar} alSalir={salir} />
      )}

      <nav className="nav-inf" aria-label="Secciones">
        <div>
          {PESTANAS.slice(0, 2).map(([id, icono, nombre]) => (
            <button key={id} className="pestana" aria-current={pestana === id ? 'page' : undefined} onClick={() => setPestana(id)}>
              <span aria-hidden>{icono}</span><span>{nombre}</span>
            </button>
          ))}
          <button className="fab" onClick={() => setCaptura({})} aria-label="Registrar movimiento" disabled={!tablero}>+</button>
          {PESTANAS.slice(2).map(([id, icono, nombre]) => (
            <button key={id} className="pestana" aria-current={pestana === id ? 'page' : undefined} onClick={() => setPestana(id)}>
              <span aria-hidden>{icono}</span><span>{nombre}</span>
            </button>
          ))}
        </div>
      </nav>

      {captura && tablero && (
        <Captura t={tablero} inicio={captura} usuario={usuario} alGuardar={guardar} alCerrar={() => setCaptura(null)} />
      )}
      {verAlertas && tablero && (
        <PanelAlertas alertas={alertas} alDescartar={descartar} alCerrar={() => setVerAlertas(false)} />
      )}
      {aviso && (
        <div className="toast" role="status">
          <span>{aviso.texto}</span>
          {aviso.deshacer && <button onClick={aviso.deshacer}>Deshacer</button>}
        </div>
      )}
    </div>
  )
}
