import { useState } from 'react'
import { api } from '../api'
import type { Tablero, VistaPrevia } from '../tipos'
import { dinero, fechaCorta } from '../formato'
import { Vacio } from '../ui'

const ESTADO = { nueva: 'Nueva', duplicada: 'Ya importada', posible_duplicada: 'Posible repetida' }
const TIPO: Record<string, string> = { gasto: 'Gasto', ingreso: 'Ingreso', pago_deuda: 'Pago a la tarjeta' }

export default function Importar({ t, usuario, alTerminar }: { t: Tablero; usuario: string; alTerminar: (mensaje: string) => void }) {
  const destinos = [...t.cuentas.map(c => ({ id: c.id, nombre: c.nombre })),
    ...t.deudas.filter(d => d.tipo === 'tarjeta_credito').map(d => ({ id: d.id, nombre: `${d.nombre} (tarjeta)` }))]
  const [cuenta, setCuenta] = useState(destinos[0]?.id ?? '')
  const [previa, setPrevia] = useState<VistaPrevia | null>(null)
  const [elegidas, setElegidas] = useState<Set<string>>(new Set())
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)

  if (destinos.length === 0) {
    return <div className="tarjeta"><Vacio icono="📄" titulo="Primero crea una cuenta">Los movimientos importados se asignan a una cuenta o tarjeta. Créala en Ajustes.</Vacio></div>
  }

  const leer = async (archivo: File | undefined) => {
    if (!archivo) return
    setError(''); setPrevia(null); setOcupado(true)
    try {
      const v = await api.previsualizar(archivo, cuenta)
      setPrevia(v)
      setElegidas(new Set(v.filas.filter(f => f.estado === 'nueva').map(f => f.huella)))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setOcupado(false)
    }
  }

  const confirmar = async () => {
    if (!previa) return
    setOcupado(true)
    try {
      const r = await api.confirmarImportacion({
        cuenta_id: cuenta, responsable: usuario, huella_archivo: previa.huella_archivo,
        filas_leidas: previa.filas_leidas, filas_rechazadas: previa.filas_rechazadas,
        filas: previa.filas.filter(f => elegidas.has(f.huella)),
      })
      setPrevia(null)
      alTerminar(`${r.nuevas} movimiento(s) importados`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setOcupado(false)
    }
  }

  const alternar = (huella: string) => setElegidas(s => {
    const n = new Set(s)
    n.has(huella) ? n.delete(huella) : n.add(huella)
    return n
  })

  return (
    <>
      <section className="tarjeta">
        <header><h2>Importar extracto</h2></header>
        <p className="sec chico" style={{ marginBottom: 12 }}>
          Descarga los movimientos desde la app o la web de tu banco en CSV o Excel (.xlsx) y súbelos aquí.
          Orion no se conecta a tu banco, y el archivo no se guarda.
        </p>
        <label className="campo"><span>¿De qué cuenta o tarjeta es?</span>
          <select value={cuenta} onChange={e => { setCuenta(e.target.value); setPrevia(null) }}>
            {destinos.map(d => <option key={d.id} value={d.id}>{d.nombre}</option>)}
          </select>
        </label>
        <label className="campo"><span>Archivo</span>
          <input type="file" accept=".csv,.xlsx" disabled={ocupado} style={{ paddingTop: 9 }}
            onChange={e => { leer(e.target.files?.[0]); e.target.value = '' }} />
          <small>Necesita una columna de fecha y una de valor (o débito y crédito). Máx. 5 MB.</small>
        </label>
        {ocupado && <p className="tenue chico">Leyendo…</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {previa && (
        <section className="tarjeta">
          <header><h2>Revisa antes de guardar</h2><span className="tenue chico">{previa.filas.length} movimientos</span></header>
          {previa.ya_importado && <p className="sec chico" style={{ marginBottom: 8 }}>⚠️ Este mismo archivo ya se había importado.</p>}
          {previa.filas_rechazadas > 0 && (
            <p className="tenue chico" style={{ marginBottom: 8 }}>{previa.filas_rechazadas} fila(s) sin fecha o sin valor se ignoraron.</p>
          )}
          {previa.filas.length === 0 && <p className="tenue">No encontré movimientos en el archivo.</p>}
          {previa.filas.map(f => (
            <label className="item" key={f.huella} style={{ cursor: f.estado === 'duplicada' ? 'default' : 'pointer' }}>
              <input type="checkbox" checked={elegidas.has(f.huella)} disabled={f.estado === 'duplicada'} onChange={() => alternar(f.huella)} />
              <div className="cuerpo">
                <p>{f.descripcion || 'Sin descripción'}</p>
                <p className="tenue chico">{fechaCorta(f.fecha)} · {TIPO[f.tipo]}{f.estado !== 'nueva' && <b> · {ESTADO[f.estado]}</b>}</p>
              </div>
              <span className="monto num">{f.tipo === 'ingreso' ? '+' : '−'} {dinero(f.monto)}</span>
            </label>
          ))}
          <button className="boton" disabled={ocupado || elegidas.size === 0} onClick={confirmar}>
            Importar {elegidas.size} movimiento{elegidas.size === 1 ? '' : 's'}
          </button>
        </section>
      )}
    </>
  )
}
