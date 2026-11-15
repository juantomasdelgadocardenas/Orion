import { useEffect, useMemo, useState } from 'react'
import type { InicioCaptura, NuevaTransaccion, Tablero, TipoMov } from '../tipos'
import { dinero, numero } from '../formato'
import { Entidad, Hoja, TecladoNumerico } from '../ui'

const TITULO: Record<TipoMov, string> = {
  gasto: 'Nuevo gasto', ingreso: 'Nuevo ingreso', transferencia: 'Transferencia',
  pago_deuda: 'Pago de deuda', aporte_bolsillo: 'Aporte a bolsillo',
}
const CUOTAS = [1, 2, 3, 6, 12, 18, 24, 36]
const recordado = (clave: string) => { try { return localStorage.getItem(clave) ?? '' } catch { return '' } }

/** Captura rápida: monto → banco → categoría → guardar. */
export default function Captura({ t, inicio, usuario, alGuardar, alCerrar }: {
  t: Tablero; inicio: InicioCaptura; usuario: string
  alGuardar: (x: NuevaTransaccion) => void; alCerrar: () => void
}) {
  const [tipo, setTipo] = useState<TipoMov>(inicio.tipo ?? 'gasto')
  const [texto, setTexto] = useState(inicio.monto ? String(inicio.monto) : '')
  const tarjetas = t.deudas.filter(d => d.tipo === 'tarjeta_credito')
  // Con tarjeta solo se compra: ingresos, pagos y aportes salen de (o entran a) una cuenta.
  const origenes = useMemo(
    () => [...t.cuentas.map(c => ({ id: c.id, nombre: c.nombre, entidad: c.institucion || c.nombre, tarjeta: false })),
      ...(tipo === 'gasto' ? tarjetas.map(d => ({ id: d.id, nombre: d.nombre, entidad: d.institucion || d.nombre, tarjeta: true })) : [])],
    [t, tipo], // eslint-disable-line react-hooks/exhaustive-deps
  )
  const [cuenta, setCuenta] = useState(() => recordado('orion_ultima_cuenta'))
  const [categoria, setCategoria] = useState('')
  const [responsable, setResponsable] = useState(usuario)
  const [detalles, setDetalles] = useState(false)
  const [fecha, setFecha] = useState(t.hoy)
  const [nota, setNota] = useState('')
  const [cuotas, setCuotas] = useState(1)
  const [fijo, setFijo] = useState('')
  const [destino, setDestino] = useState(inicio.cuenta_destino_id ?? '')

  const origen = origenes.find(o => o.id === cuenta) ?? origenes[0]
  const monto = Number(texto || 0)
  const categorias = t.categorias.filter(c => c.tipo === (tipo === 'ingreso' ? 'ingreso' : 'gasto'))
  const conCategoria = tipo === 'gasto' || tipo === 'ingreso'
  const faltaDestino = tipo === 'transferencia' && (!destino || destino === origen?.id)
  const listo = monto > 0 && !!origen && !faltaDestino

  const pulsar = (tecla: string) => setTexto(v => {
    if (tecla === '⌫') return v.slice(0, -1)
    const nuevo = (v + tecla).replace(/^0+/, '')
    return nuevo.length > 11 ? v : nuevo
  })

  const guardar = () => {
    if (!listo) return
    try { localStorage.setItem('orion_ultima_cuenta', origen.id) } catch { /* sin almacenamiento */ }
    alGuardar({
      monto, tipo, cuenta_id: origen.id, responsable, fecha,
      categoria_id: conCategoria ? categoria : '',
      cuenta_destino_id: tipo === 'transferencia' || tipo === 'pago_deuda' ? destino : '',
      bolsillo_id: inicio.bolsillo_id ?? '',
      gasto_fijo_id: tipo === 'gasto' ? fijo : '',
      descripcion: nota, cuotas: origen.tarjeta ? cuotas : 1,
    })
  }

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (['INPUT', 'SELECT'].includes((e.target as HTMLElement).tagName)) return
      if (/^\d$/.test(e.key)) pulsar(e.key)
      else if (e.key === 'Backspace') pulsar('⌫')
      else if (e.key === 'Enter') { e.preventDefault(); guardar() }
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  })

  return (
    <Hoja titulo={inicio.titulo ?? TITULO[tipo]} alCerrar={alCerrar}>
      {!inicio.tipo && (
        <div className="chips" role="group" aria-label="Tipo de movimiento">
          {(['gasto', 'ingreso', 'transferencia'] as TipoMov[]).map(x => (
            <button key={x} className="chip" aria-pressed={tipo === x} onClick={() => { setTipo(x); setCategoria('') }}>
              {{ gasto: 'Gasto', ingreso: 'Ingreso', transferencia: 'Transferencia' }[x as 'gasto']}
            </button>
          ))}
        </div>
      )}
      <p className={`monto-captura num ${monto ? '' : 'vacio'}`} aria-live="polite">{monto ? dinero(monto) : '$ 0'}</p>

      <span className="etiqueta">{tipo === 'ingreso' ? '¿A dónde entra?' : '¿De dónde sale?'}</span>
      <div className="chips" role="group" aria-label="Cuenta">
        {origenes.map(o => (
          <button key={o.id} className="banco" aria-pressed={origen?.id === o.id} onClick={() => setCuenta(o.id)} title={o.nombre}>
            <Entidad nombre={o.entidad} lado={34} /><span>{o.nombre}</span>
          </button>
        ))}
      </div>

      {tipo === 'transferencia' && (
        <>
          <span className="etiqueta">¿A dónde va?</span>
          <div className="chips" role="group" aria-label="Cuenta de destino">
            {t.cuentas.filter(c => c.id !== origen?.id).map(c => (
              <button key={c.id} className="banco" aria-pressed={destino === c.id} onClick={() => setDestino(c.id)}>
                <Entidad nombre={c.institucion || c.nombre} lado={34} /><span>{c.nombre}</span>
              </button>
            ))}
          </div>
        </>
      )}

      {origen?.tarjeta && (
        <>
          <span className="etiqueta">Cuotas{cuotas > 1 && monto > 0 && ` · ${cuotas} de ${dinero(Math.floor(monto / cuotas))} + intereses`}</span>
          <div className="chips" role="group" aria-label="Número de cuotas">
            {CUOTAS.map(n => <button key={n} className="chip" aria-pressed={cuotas === n} onClick={() => setCuotas(n)}>{numero(n)}</button>)}
          </div>
        </>
      )}

      {conCategoria && categorias.length > 0 && (
        <>
          <span className="etiqueta">Categoría</span>
          <div className="chips" role="group" aria-label="Categoría">
            {categorias.map(c => (
              <button key={c.id} className="chip" aria-pressed={categoria === c.id} onClick={() => setCategoria(categoria === c.id ? '' : c.id)}>
                {c.icono} {c.nombre}
              </button>
            ))}
          </div>
        </>
      )}

      {t.usuarios.length > 1 && (
        <div className="chips" role="group" aria-label="Responsable" style={{ marginTop: 4 }}>
          {t.usuarios.map(u => (
            <button key={u.id} className="chip" aria-pressed={responsable === u.id} onClick={() => setResponsable(u.id)}>{u.nombre}</button>
          ))}
          <button className="chip" aria-pressed={detalles} onClick={() => setDetalles(v => !v)}>Más detalles</button>
        </div>
      )}
      {t.usuarios.length <= 1 && <button className="enlace" onClick={() => setDetalles(v => !v)}>Más detalles</button>}

      {detalles && (
        <div style={{ marginTop: 8 }}>
          <div className="dos">
            <label className="campo"><span>Fecha</span><input type="date" value={fecha} max={t.hoy} onChange={e => setFecha(e.target.value || t.hoy)} /></label>
            <label className="campo"><span>Nota</span><input value={nota} maxLength={140} onChange={e => setNota(e.target.value)} placeholder="Opcional" /></label>
          </div>
          {tipo === 'gasto' && t.gastos_fijos.length > 0 && (
            <label className="campo"><span>¿Es el pago de un gasto fijo?</span>
              <select value={fijo} onChange={e => setFijo(e.target.value)}>
                <option value="">No</option>
                {t.gastos_fijos.map(g => <option key={g.id} value={g.id}>{g.nombre} · {dinero(g.monto)}</option>)}
              </select>
            </label>
          )}
        </div>
      )}

      <TecladoNumerico alPulsar={pulsar} />
      <button className="boton" disabled={!listo} onClick={guardar}>Guardar</button>
    </Hoja>
  )
}
