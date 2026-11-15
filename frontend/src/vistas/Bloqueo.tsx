import { useEffect, useState } from 'react'
import { api, sesion } from '../api'
import { TecladoNumerico } from '../ui'

const LARGO_MAXIMO = 8

export default function Bloqueo({ alEntrar }: { alEntrar: () => void }) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [verServidor, setVerServidor] = useState(false)
  const [servidor, setServidor] = useState(sesion.servidor)

  const entrar = async (valor: string) => {
    if (valor.length < 4 || ocupado) return
    setOcupado(true)
    try {
      sesion.token = (await api.desbloquear(valor)).token
      alEntrar()
    } catch (e) {
      setError((e as Error).message)
      setPin('')
    } finally {
      setOcupado(false)
    }
  }

  const pulsar = (tecla: string) => {
    setError('')
    if (tecla === '⌫') return setPin(p => p.slice(0, -1))
    if (tecla === 'OK') return entrar(pin)
    if (pin.length >= LARGO_MAXIMO) return
    const nuevo = pin + tecla
    setPin(nuevo)
    if (nuevo.length === 4) entrar(nuevo) // el PIN habitual es de 4 dígitos; los más largos se confirman con OK
  }

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      if (/^\d$/.test(e.key)) pulsar(e.key)
      else if (e.key === 'Backspace') pulsar('⌫')
      else if (e.key === 'Enter') pulsar('OK')
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  })

  return (
    <main className="bloqueo">
      <img src="./icons/icon-128.png" alt="" />
      <h1>Orion</h1>
      <p className="sec">Ingresa el PIN</p>
      <div className="puntos" aria-label={`${pin.length} dígitos ingresados`}>
        {Array.from({ length: Math.max(4, pin.length) }, (_, i) => <i key={i} className={i < pin.length ? 'lleno' : ''} />)}
      </div>
      <p className="error" role="alert" style={{ minHeight: 20, margin: '0 0 8px' }}>{error}</p>
      <TecladoNumerico alPulsar={pulsar} extra="OK" />
      <button className="enlace" style={{ marginTop: 18 }} onClick={() => setVerServidor(v => !v)}>Servidor</button>
      {verServidor && (
        <label className="campo" style={{ width: '100%', textAlign: 'left' }}>
          <span>Dirección del servidor de Orion</span>
          <input value={servidor} placeholder="(el mismo de esta página)" onChange={e => setServidor(e.target.value)}
            onBlur={() => { sesion.servidor = servidor }} inputMode="url" autoCapitalize="off" />
          <small>Ej.: http://localhost:8000 o http://192.168.1.20:8000</small>
        </label>
      )}
    </main>
  )
}
