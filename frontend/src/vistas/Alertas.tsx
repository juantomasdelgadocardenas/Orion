import type { Alerta } from '../tipos'
import { dinero } from '../formato'
import { Hoja, Vacio } from '../ui'

const ICONO = { critica: '!', aviso: '!', info: 'i' }
const NOMBRE = { critica: 'Importante', aviso: 'Aviso', info: 'Dato' }

export const alertasVisibles = (alertas: Alerta[], descartadas: string[]) => alertas.filter(a => !descartadas.includes(a.id))

export default function PanelAlertas({ alertas, alDescartar, alCerrar }: {
  alertas: Alerta[]; alDescartar: (id: string) => void; alCerrar: () => void
}) {
  return (
    <Hoja titulo="Alertas" alCerrar={alCerrar}>
      {alertas.length === 0 && <Vacio icono="✨" titulo="Todo en orden">No hay alertas por ahora.</Vacio>}
      {alertas.map(a => (
        <article key={a.id} className={`alerta ${a.severidad}`}>
          <span className="icono" aria-hidden>{ICONO[a.severidad]}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p className="chico tenue">{NOMBRE[a.severidad]}</p>
            <p><b>{a.titulo}</b></p>
            <p className="sec chico">{a.detalle}{a.monto ? ` · ${dinero(Math.abs(a.monto))}` : ''}</p>
          </div>
          <button className="enlace" onClick={() => alDescartar(a.id)} aria-label={`Descartar: ${a.titulo}`}>Listo</button>
        </article>
      ))}
    </Hoja>
  )
}
