import { useRef, useState } from 'react'
import { compacto, dinero, escalaEje } from './formato'

const ANCHO = 340

function columna(x: number, y: number, ancho: number, base: number) {
  const r = Math.min(4, (base - y) / 2, ancho / 2)
  if (base - y < 0.5) return ''
  return `M${x},${base}V${y + r}Q${x},${y} ${x + r},${y}H${x + ancho - r}Q${x + ancho},${y} ${x + ancho},${y + r}V${base}Z`
}

/** Ingresos y gastos por mes: columnas agrupadas sobre una sola escala. */
export function FlujoMensual({ datos }: { datos: { mes: string; etiqueta: string; ingresos: number; gastos: number }[] }) {
  const [activo, setActivo] = useState<number | null>(null)
  const alto = 172, izq = 36, der = 4, arriba = 8, abajo = 22
  const marcas = escalaEje(Math.max(1, ...datos.flatMap(d => [d.ingresos, d.gastos])))
  const tope = marcas[marcas.length - 1]
  const base = alto - abajo
  const y = (v: number) => base - (v / tope) * (base - arriba)
  const banda = (ANCHO - izq - der) / datos.length
  const barra = Math.min(16, banda / 2 - 5)
  const d = activo === null ? null : datos[activo]
  return (
    <div className="grafico">
      <div className="leyenda">
        <span><i style={{ background: 'var(--serie-ingresos)' }} />Ingresos</span>
        <span><i style={{ background: 'var(--serie-gastos)' }} />Gastos</span>
      </div>
      <svg viewBox={`0 0 ${ANCHO} ${alto}`} role="img" aria-label="Ingresos y gastos de los últimos meses" onPointerLeave={() => setActivo(null)}>
        {marcas.map(m => (
          <g key={m}>
            <line x1={izq} x2={ANCHO - der} y1={y(m)} y2={y(m)} stroke="var(--rejilla)" />
            <text x={izq - 6} y={y(m) + 3.5} textAnchor="end">{compacto(m)}</text>
          </g>
        ))}
        {datos.map((f, i) => {
          const centro = izq + banda * (i + 0.5)
          return (
            <g key={f.mes} opacity={activo === null || activo === i ? 1 : 0.45}>
              <path d={columna(centro - barra - 1, y(f.ingresos), barra, base)} fill="var(--serie-ingresos)" />
              <path d={columna(centro + 1, y(f.gastos), barra, base)} fill="var(--serie-gastos)" />
              <text x={centro} y={alto - 6} textAnchor="middle">{f.etiqueta}</text>
              <rect x={izq + banda * i} y={0} width={banda} height={alto} fill="transparent"
                onPointerEnter={() => setActivo(i)} onPointerDown={() => setActivo(i)} />
            </g>
          )
        })}
      </svg>
      {d && activo !== null && (
        <div className="globo" style={{ left: `${Math.min(78, Math.max(22, ((izq + banda * (activo + 0.5)) / ANCHO) * 100))}%`, top: `${(y(Math.max(d.ingresos, d.gastos)) / alto) * 100}%` }}>
          <b>{d.etiqueta} {d.mes.slice(0, 4)}</b>
          <div><span>Ingresos</span><span>{dinero(d.ingresos)}</span></div>
          <div><span>Gastos</span><span>{dinero(d.gastos)}</span></div>
          <div><span>Balance</span><span>{dinero(d.ingresos - d.gastos)}</span></div>
        </div>
      )}
      <details className="tabla">
        <summary>Ver como tabla</summary>
        <table>
          <thead><tr><th>Mes</th><th>Ingresos</th><th>Gastos</th><th>Balance</th></tr></thead>
          <tbody>{datos.map(f => (
            <tr key={f.mes}><td>{f.etiqueta}</td><td>{dinero(f.ingresos)}</td><td>{dinero(f.gastos)}</td><td>{dinero(f.ingresos - f.gastos)}</td></tr>
          ))}</tbody>
        </table>
      </details>
    </div>
  )
}

/** Cómo va bajando una deuda: saldo después de cada pago. Una sola serie, así que no lleva leyenda. */
export function SaldoBajando({ puntos }: { puntos: { etiqueta: string; saldo: number; pago: number }[] }) {
  const [activo, setActivo] = useState<number | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const alto = 150, izq = 36, der = 10, arriba = 10, abajo = 22
  if (puntos.length < 2) return null
  const marcas = escalaEje(Math.max(1, ...puntos.map(p => p.saldo)), 3)
  const tope = marcas[marcas.length - 1]
  const base = alto - abajo
  const x = (i: number) => izq + (i / (puntos.length - 1)) * (ANCHO - izq - der)
  const y = (v: number) => base - (v / tope) * (base - arriba)
  const linea = puntos.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.saldo).toFixed(1)}`).join('')
  const mover = (e: React.PointerEvent) => {
    const caja = svg.current!.getBoundingClientRect()
    const px = ((e.clientX - caja.left) / caja.width) * ANCHO
    const i = Math.round(((px - izq) / (ANCHO - izq - der)) * (puntos.length - 1))
    setActivo(Math.min(puntos.length - 1, Math.max(0, i)))
  }
  const etiquetas = [0, Math.floor((puntos.length - 1) / 2), puntos.length - 1].filter((v, i, a) => a.indexOf(v) === i)
  const p = activo === null ? null : puntos[activo]
  return (
    <div className="grafico">
      <svg ref={svg} viewBox={`0 0 ${ANCHO} ${alto}`} role="img" aria-label="Saldo de la deuda después de cada pago"
        onPointerMove={mover} onPointerDown={mover} onPointerLeave={() => setActivo(null)} style={{ touchAction: 'pan-y' }}>
        {marcas.map(m => (
          <g key={m}>
            <line x1={izq} x2={ANCHO - der} y1={y(m)} y2={y(m)} stroke="var(--rejilla)" />
            <text x={izq - 6} y={y(m) + 3.5} textAnchor="end">{compacto(m)}</text>
          </g>
        ))}
        <path d={`${linea}L${x(puntos.length - 1)},${base}L${x(0)},${base}Z`} fill="var(--acento)" opacity="0.1" />
        <path d={linea} fill="none" stroke="var(--acento)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {etiquetas.map(i => (
          <text key={i} x={x(i)} y={alto - 6} textAnchor={i === 0 ? 'start' : i === puntos.length - 1 ? 'end' : 'middle'}>{puntos[i].etiqueta}</text>
        ))}
        {activo !== null && p && (
          <g>
            <line x1={x(activo)} x2={x(activo)} y1={arriba} y2={base} stroke="var(--tenue)" />
            <circle cx={x(activo)} cy={y(p.saldo)} r="5" fill="var(--acento)" stroke="var(--superficie)" strokeWidth="2" />
          </g>
        )}
      </svg>
      {p && activo !== null && (
        <div className="globo" style={{ left: `${Math.min(76, Math.max(24, (x(activo) / ANCHO) * 100))}%`, top: `${(y(p.saldo) / alto) * 100 - 4}%` }}>
          <b>{p.etiqueta}</b>
          {p.pago > 0 && <div><span>Pagas</span><span>{dinero(p.pago)}</span></div>}
          <div><span>Quedas debiendo</span><span>{dinero(p.saldo)}</span></div>
        </div>
      )}
    </div>
  )
}
