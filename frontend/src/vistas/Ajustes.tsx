import { useCallback, useEffect, useState } from 'react'
import { api, sesion } from '../api'
import type { Campo, Esquema, Fila, Tablero } from '../tipos'
import { dinero } from '../formato'
import { Hoja, Vacio } from '../ui'

const TITULOS: Record<string, [string, string]> = {
  usuarios: ['👥', 'Personas'], cuentas: ['🏦', 'Cuentas'], deudas: ['💳', 'Tarjetas y créditos'],
  bolsillos: ['🎯', 'Bolsillos y metas'], categorias: ['🏷️', 'Categorías y presupuestos'], gastos_fijos: ['📅', 'Gastos fijos'],
}
const legible = (v: string) => v.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase())
const estaActiva = (f: Fila) => f.activa !== false && f.activo !== false && f.estado !== 'pausada'

function Formulario({ campos, inicial, t, alGuardar, alBorrar }: {
  campos: Campo[]; inicial: Fila; t: Tablero
  alGuardar: (f: Fila) => Promise<void>; alBorrar?: () => Promise<void>
}) {
  const [fila, setFila] = useState<Fila>(inicial)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const poner = (nombre: string, valor: unknown) => setFila(f => ({ ...f, [nombre]: valor }))

  const referencias = (ref: string): [string, string][] => {
    if (ref === 'titulares') return [['compartida', 'Compartida'], ...t.usuarios.map(u => [u.id, u.nombre] as [string, string])]
    if (ref === 'cuentas') return [['', '—'], ...t.cuentas.map(c => [c.id, c.nombre] as [string, string]),
      ...t.deudas.filter(d => d.tipo === 'tarjeta_credito').map(d => [d.id, d.nombre] as [string, string])]
    if (ref === 'deudas') return [['', '—'], ...t.deudas.map(d => [d.id, d.nombre] as [string, string])]
    return [['', '—'], ...t.categorias.map(c => [c.id, c.nombre] as [string, string])]
  }

  const ejecutar = async (accion: () => Promise<void>) => {
    setOcupado(true); setError('')
    try { await accion() } catch (e) { setError((e as Error).message) } finally { setOcupado(false) }
  }

  return (
    <form onSubmit={e => { e.preventDefault(); ejecutar(() => alGuardar(fila)) }}>
      {campos.filter(c => !c.solo || fila.tipo === c.solo).map(c => {
        const valor = fila[c.nombre]
        if (c.tipo === 'booleano') {
          return <label className="campo casilla" key={c.nombre}>
            <input type="checkbox" checked={!!valor} onChange={e => poner(c.nombre, e.target.checked)} /><span>{c.titulo}</span>
          </label>
        }
        let entrada
        if (c.tipo === 'opcion' || c.ref) {
          const opciones = c.ref ? referencias(c.ref) : c.opciones.map(o => [o, legible(o)] as [string, string])
          entrada = <select value={valor ?? ''} onChange={e => poner(c.nombre, e.target.value)}>
            {opciones.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select>
        } else if (c.tipo === 'fecha') {
          entrada = <input type="date" value={valor ?? ''} required={c.requerido} onChange={e => poner(c.nombre, e.target.value)} />
        } else if (c.color) {
          entrada = <input type="color" value={valor || '#3987e5'} onChange={e => poner(c.nombre, e.target.value)} />
        } else if (c.tipo === 'entero' || c.tipo === 'decimal') {
          const mostrado = valor === null || valor === undefined || valor === '' ? '' : c.porcentaje ? +(valor * 100).toFixed(4) : valor
          entrada = <input type="number" inputMode="decimal" value={mostrado} min={c.min ?? 0} max={c.max}
            step={c.tipo === 'decimal' ? 'any' : 1}
            onChange={e => poner(c.nombre, e.target.value === '' ? '' : c.porcentaje ? Number(e.target.value) / 100 : Number(e.target.value))} />
        } else {
          entrada = <input value={valor ?? ''} required={c.requerido} onChange={e => poner(c.nombre, e.target.value)} />
        }
        return <label className="campo" key={c.nombre}>
          <span>{c.titulo}{c.porcentaje && ' (%)'}{c.dinero && typeof valor === 'number' && valor > 0 && <span className="tenue"> · {dinero(valor)}</span>}</span>
          {entrada}{c.ayuda && <small>{c.ayuda}</small>}
        </label>
      })}
      {error && <p className="error" role="alert">{error}</p>}
      <button className="boton" disabled={ocupado}>Guardar</button>
      {alBorrar && <button type="button" className="boton peligro" disabled={ocupado} onClick={() => ejecutar(alBorrar)}>Borrar</button>}
    </form>
  )
}

export default function Ajustes({ t, usuario, alElegirUsuario, alCambiar, alSalir }: {
  t: Tablero; usuario: string; alElegirUsuario: (id: string) => void; alCambiar: () => void; alSalir: () => void
}) {
  const [esquema, setEsquema] = useState<Esquema | null>(null)
  const [tabla, setTabla] = useState('')
  const [filas, setFilas] = useState<Fila[]>([])
  const [editando, setEditando] = useState<Fila | null>(null)
  const [error, setError] = useState('')
  const [servidor, setServidor] = useState(sesion.servidor)

  useEffect(() => { api.esquema().then(setEsquema).catch(e => setError(e.message)) }, [])
  const abrir = useCallback(async (clave: string) => {
    setTabla(clave); setEditando(null)
    setFilas(await api.listar(clave))
  }, [])

  const def = esquema?.[tabla]
  const nueva = (): Fila => {
    const fila: Fila = {}
    for (const c of def!.campos) fila[c.nombre] = c.tipo === 'fecha' && c.requerido ? t.hoy : c.defecto ?? ''
    return fila
  }
  const guardar = async (fila: Fila) => {
    if (fila.id) await api.editar(tabla, fila.id, fila)
    else await api.crear(tabla, fila)
    await abrir(tabla)
    alCambiar()
  }
  const borrar = async (id: string) => { await api.borrar(tabla, id); await abrir(tabla); alCambiar() }

  return (
    <>
      <section className="tarjeta">
        <header><h2>Configuración</h2></header>
        {error && <p className="error">{error}</p>}
        {Object.entries(TITULOS).map(([clave, [icono, nombre]]) => (
          <button className="item" key={clave} onClick={() => abrir(clave)} disabled={!esquema}>
            <span className="emoji" aria-hidden>{icono}</span>
            <div className="cuerpo"><p>{nombre}</p></div>
            <span className="tenue" aria-hidden>›</span>
          </button>
        ))}
      </section>

      {t.usuarios.length > 0 && (
        <section className="tarjeta">
          <header><h2>¿Quién usa este dispositivo?</h2></header>
          <div className="chips">
            {t.usuarios.map(u => <button key={u.id} className="chip" aria-pressed={usuario === u.id} onClick={() => alElegirUsuario(u.id)}>{u.nombre}</button>)}
          </div>
          <p className="tenue chico">Los movimientos que registres quedan a nombre de esta persona.</p>
        </section>
      )}

      <section className="tarjeta">
        <header><h2>Conexión</h2><span className="insignia">{t.modo === 'demo' ? 'Datos de ejemplo' : 'Google Sheets'}</span></header>
        <label className="campo"><span>Servidor de Orion</span>
          <input value={servidor} placeholder="(el mismo de esta página)" onChange={e => setServidor(e.target.value)}
            onBlur={() => { if (servidor !== sesion.servidor) { sesion.servidor = servidor; alCambiar() } }} />
        </label>
        <button className="boton secundario" onClick={alSalir}>Bloquear con PIN</button>
      </section>

      {def && !editando && (
        <Hoja titulo={TITULOS[tabla][1]} alCerrar={() => setTabla('')}>
          {filas.length === 0 && <Vacio icono={TITULOS[tabla][0]} titulo="Aún no hay nada aquí" />}
          {filas.map(f => (
            <button className="item" key={f.id} onClick={() => setEditando(f)}>
              <div className="cuerpo">
                <p>{f.icono ? `${f.icono} ` : ''}{f.nombre}</p>
                <p className="tenue chico">{[f.tipo && legible(f.tipo), f.institucion, !estaActiva(f) && 'Inactiva'].filter(Boolean).join(' · ')}</p>
              </div>
              <span className="tenue" aria-hidden>›</span>
            </button>
          ))}
          <button className="boton" onClick={() => setEditando(nueva())}>Agregar {def.singular.toLowerCase()}</button>
        </Hoja>
      )}
      {def && editando && (
        <Hoja titulo={editando.id ? `Editar ${def.singular.toLowerCase()}` : `Nueva: ${def.singular.toLowerCase()}`} alCerrar={() => setEditando(null)}>
          <Formulario key={editando.id ?? 'nueva'} campos={def.campos} inicial={editando} t={t} alGuardar={guardar}
            alBorrar={editando.id ? () => borrar(editando.id) : undefined} />
        </Hoja>
      )}
    </>
  )
}
