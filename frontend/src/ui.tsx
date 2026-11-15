import { useEffect, useState, type ReactNode } from 'react'
import { colorEntidad, iniciales } from './formato'

export function Entidad({ nombre, lado = 36 }: { nombre: string; lado?: number }) {
  return (
    <span className="entidad" aria-hidden style={{ width: lado, height: lado, background: colorEntidad(nombre), fontSize: lado * 0.38 }}>
      {iniciales(nombre)}
    </span>
  )
}

/** Anillo de avance con contenido en el centro (foto de la meta o texto). */
export function Anillo({ fraccion, lado = 132, children }: { fraccion: number; lado?: number; children?: ReactNode }) {
  const radio = 44
  const largo = 2 * Math.PI * radio
  return (
    <div className="anillo" style={{ width: lado, height: lado }} role="img" aria-label={`Avance ${Math.round(fraccion * 100)} %`}>
      <svg viewBox="0 0 100 100" width={lado} height={lado}>
        <circle cx="50" cy="50" r={radio} fill="none" stroke="rgba(246,174,87,0.2)" strokeWidth="7" />
        <circle cx="50" cy="50" r={radio} fill="none" stroke="var(--acento)" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={`${Math.max(0.001, fraccion) * largo} ${largo}`} />
      </svg>
      <div className="centro">{children}</div>
    </div>
  )
}

export function ImagenMeta({ clave }: { clave: string }) {
  const [falla, setFalla] = useState(false)
  if (!clave || falla) return <span aria-hidden>{clave.includes('akt') || clave.includes('moto') ? '🏍️' : '🎯'}</span>
  return <img src={`./metas/${clave}.jpg`} alt="" onError={() => setFalla(true)} />
}

export function Medidor({ fraccion, estado = '' }: { fraccion: number; estado?: '' | 'aviso' | 'critico' | 'bien' }) {
  return <div className={`medidor ${estado}`}><i style={{ width: `${Math.min(100, Math.max(0, fraccion * 100))}%` }} /></div>
}

export function Hoja({ titulo, alCerrar, children }: { titulo: string; alCerrar: () => void; children: ReactNode }) {
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => { if (e.key === 'Escape') alCerrar() }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [alCerrar])
  return (
    <div className="telon" onClick={e => { if (e.target === e.currentTarget) alCerrar() }}>
      <section className="hoja" role="dialog" aria-modal="true" aria-label={titulo}>
        <header>
          <h2>{titulo}</h2>
          <button className="cerrar" onClick={alCerrar} aria-label="Cerrar">✕</button>
        </header>
        {children}
      </section>
    </div>
  )
}

export function Vacio({ icono, titulo, children }: { icono: string; titulo: string; children?: ReactNode }) {
  return (
    <div className="vacio">
      <div className="grande" aria-hidden>{icono}</div>
      <p><b>{titulo}</b></p>
      {children && <p className="chico" style={{ marginTop: 4 }}>{children}</p>}
    </div>
  )
}

export function TecladoNumerico({ alPulsar, extra = '000' }: { alPulsar: (tecla: string) => void; extra?: string }) {
  return (
    <div className="teclado">
      {['1', '2', '3', '4', '5', '6', '7', '8', '9', extra, '0', '⌫'].map(t => (
        <button key={t || 'vacio'} type="button" onClick={() => t && alPulsar(t)} disabled={!t}
          aria-label={t === '⌫' ? 'Borrar' : t} style={t ? undefined : { visibility: 'hidden' }}>{t}</button>
      ))}
    </div>
  )
}
