import { useState } from 'react'
import type { InicioCaptura, Linea, Tablero } from '../tipos'
import { dinero, enDias, fechaCorta, mesAnio, porcentaje } from '../formato'
import { FlujoMensual } from '../graficos'
import { Anillo, Entidad, ImagenMeta, Medidor, Vacio } from '../ui'

const GRUPOS: [Linea['grupo'], string, string][] = [
  ['saldo', 'En tus cuentas', '+'], ['fijos', 'Gastos fijos por pagar', '−'],
  ['deudas', 'Tarjetas y créditos del mes', '−'], ['ahorro', 'Ahorro apartado', '−'],
]
const SEMAFORO = { optimo: 'Buen día para comprar', neutro: 'Día normal', riesgo: 'Evita comprar hoy' }
const SIGNO = { gasto: '−', ingreso: '+', transferencia: '⇄', pago_deuda: '−', aporte_bolsillo: '→' }

export default function Inicio({ t, filtro, alFiltrar, abrirCaptura, irA }: {
  t: Tablero; filtro: string; alFiltrar: (id: string) => void
  abrirCaptura: (i: InicioCaptura) => void; irA: (p: 'deudas' | 'ajustes') => void
}) {
  const [desglose, setDesglose] = useState(false)
  const dr = t.dinero_real
  const destacada = t.metas.find(m => m.destacar_en_dashboard)
  const otras = t.metas.filter(m => m !== destacada)
  const tarjetas = t.deudas.filter(d => d.tipo === 'tarjeta_credito')
  const categorias = Object.fromEntries(t.categorias.map(c => [c.id, c]))
  const nombres = Object.fromEntries([...t.cuentas, ...t.deudas].map(c => [c.id, c.nombre]))
  const personas = Object.fromEntries(t.usuarios.map(u => [u.id, u.nombre]))

  if (t.cuentas.length === 0 && t.deudas.length === 0) {
    return (
      <div className="tarjeta">
        <Vacio icono="🐈" titulo="Orion está listo para configurar">
          Crea tus personas, cuentas y tarjetas. Después puedes cargar los extractos del banco.
        </Vacio>
        <button className="boton" onClick={() => irA('ajustes')}>Ir a Ajustes</button>
      </div>
    )
  }

  return (
    <>
      <section className="tarjeta heroe">
        <p className="sec">Dinero real disponible</p>
        <p className={`cifra num ${dr.total < 0 ? 'negativa' : ''}`}>{dinero(dr.total)}</p>
        <p className="tenue chico">
          {dinero(dr.saldo_bruto)} en cuentas − {dinero(dr.comprometido)} comprometido este mes
        </p>
        <button className="enlace" onClick={() => setDesglose(v => !v)} aria-expanded={desglose}>
          {desglose ? 'Ocultar desglose' : 'Ver de dónde sale'}
        </button>
        {desglose && (
          <div className="desglose">
            {GRUPOS.map(([grupo, titulo, signo]) => {
              const lineas = dr.lineas.filter(l => l.grupo === grupo)
              if (!lineas.length) return null
              return (
                <div key={grupo}>
                  <h3><span>{titulo}</span><span className="num">{signo} {dinero(lineas.reduce((s, l) => s + l.monto, 0))}</span></h3>
                  {lineas.map((l, i) => (
                    <div className="renglon" key={i}>
                      <span className="sec">{l.nombre}{l.fecha && grupo !== 'saldo' ? ` · ${fechaCorta(l.fecha)}` : ''}</span>
                      <span className="num">{dinero(l.monto)}</span>
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        )}
      </section>

      <section className="rejilla-2" aria-label="Resumen">
        {[['Saldo en cuentas', dr.saldo_bruto], ['Comprometido del mes', dr.comprometido],
          ['Deuda en tarjetas', t.deuda_tarjetas], ['Ahorro apartado', t.ahorro_total]].map(([nombre, valor]) => (
          <div className="tarjeta dato" key={nombre}>
            <p className="tenue chico">{nombre}</p>
            <p className="valor num">{dinero(valor as number)}</p>
          </div>
        ))}
      </section>

      {destacada && (
        <section className="tarjeta">
          <header><h2>{destacada.nombre}</h2>
            <span className={`estado ${destacada.estado_avance === 'atrasada' ? 'critica' : 'bien'}`}>
              {destacada.estado_avance === 'cumplida' ? 'Pagada' : destacada.estado_avance === 'atrasada' ? 'Atrasada' : 'Al día'}
            </span>
          </header>
          <div className="moto">
            <Anillo fraccion={destacada.avance}><ImagenMeta clave={destacada.imagen} /></Anillo>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p className="pct num">{porcentaje(destacada.avance)}</p>
              <p className="sec chico" style={{ marginBottom: 8 }}>
                {destacada.modo_avance === 'pago_deuda' ? 'pagado' : 'ahorrado'}
                {destacada.cuotas_totales > 0 && ` · cuota ${destacada.cuotas_pagadas} de ${destacada.cuotas_totales}`}
              </p>
              <div className="renglon"><span className="tenue">{destacada.modo_avance === 'pago_deuda' ? 'Pagado' : 'Llevas'}</span><span className="num">{dinero(destacada.actual)}</span></div>
              <div className="renglon"><span className="tenue">Falta</span><span className="num">{dinero(destacada.restante)}</span></div>
              {destacada.fecha_estimada && (
                <div className="renglon"><span className="tenue">Terminas</span><span>{mesAnio(destacada.fecha_estimada)}</span></div>
              )}
            </div>
          </div>
        </section>
      )}

      <section className="tarjeta">
        <header><h2>Flujo de dinero</h2><span className="tenue chico">Últimos 6 meses</span></header>
        {t.usuarios.length > 1 && (
          <div className="chips" role="group" aria-label="Filtrar por persona">
            <button className="chip" aria-pressed={!filtro} onClick={() => alFiltrar('')}>Todos</button>
            {t.usuarios.map(u => (
              <button key={u.id} className="chip" aria-pressed={filtro === u.id} onClick={() => alFiltrar(u.id)}>{u.nombre}</button>
            ))}
          </div>
        )}
        <FlujoMensual datos={t.flujo} />
      </section>

      <section className="tarjeta">
        <header><h2>Gastos del mes</h2><span className="tenue chico">contra el presupuesto</span></header>
        {t.gasto_categorias.length === 0 && <p className="tenue chico">Aún no hay gastos este mes.</p>}
        {t.gasto_categorias.map(g => {
          const estado = g.presupuesto > 0 ? (g.uso >= 1 ? 'critico' : g.uso >= 0.8 ? 'aviso' : '') : ''
          return (
            <div key={g.id || 'sin'} style={{ marginBottom: 12 }}>
              <div className="renglon">
                <span>{g.icono} {g.nombre}{estado === 'critico' && <b className="chico"> · Excedido</b>}{estado === 'aviso' && <b className="chico"> · Cerca del límite</b>}</span>
                <span className="num">{dinero(g.gastado)}{g.presupuesto > 0 && <span className="tenue"> / {dinero(g.presupuesto)}</span>}</span>
              </div>
              {g.presupuesto > 0 && <Medidor fraccion={g.uso} estado={estado} />}
            </div>
          )
        })}
      </section>

      {tarjetas.length > 0 && (
        <section className="tarjeta">
          <header><h2>Tarjetas hoy</h2><button className="enlace" onClick={() => irA('deudas')}>Ver plan</button></header>
          {tarjetas.map(d => (
            <div className="item" key={d.id}>
              <Entidad nombre={d.institucion || d.nombre} />
              <div className="cuerpo">
                <p>{d.nombre}</p>
                <p className="tenue chico">
                  {d.pendiente_ciclo > 0 && d.dias_para_pago !== null
                    ? `Pagas ${dinero(d.pendiente_ciclo)} ${enDias(d.dias_para_pago)}`
                    : 'Sin pago pendiente'}
                </p>
              </div>
              {d.hoy && <span className={`estado ${d.hoy.estado}`}>{SEMAFORO[d.hoy.estado]}</span>}
            </div>
          ))}
        </section>
      )}

      {otras.length > 0 && (
        <section className="tarjeta">
          <header><h2>Bolsillos y metas</h2></header>
          {otras.map(m => (
            <div key={m.id} style={{ marginBottom: 14 }}>
              <div className="renglon">
                <span><b>{m.nombre}</b>{m.estado_avance === 'atrasada' && <span className="chico"> · Atrasada</span>}</span>
                <span className="num">{porcentaje(m.avance)}</span>
              </div>
              <Medidor fraccion={m.avance} estado={m.estado_avance === 'atrasada' ? 'aviso' : m.estado_avance === 'cumplida' ? 'bien' : ''} />
              <div className="renglon chico">
                <span className="tenue">
                  {dinero(m.actual)} de {dinero(m.objetivo)}
                  {m.meses_cubiertos !== null && ` · cubre ${m.meses_cubiertos} mes(es) de gastos fijos`}
                  {m.fecha_estimada && m.meses_cubiertos === null && ` · ${mesAnio(m.fecha_estimada)}`}
                </span>
                {m.modo_avance === 'ahorro' && m.estado_avance !== 'cumplida' && (
                  <button className="enlace" style={{ padding: 0 }}
                    onClick={() => abrirCaptura({ tipo: 'aporte_bolsillo', bolsillo_id: m.id, monto: m.aporte || undefined, titulo: `Aporte a ${m.nombre}` })}>
                    Aportar
                  </button>
                )}
              </div>
            </div>
          ))}
        </section>
      )}

      <section className="tarjeta">
        <header><h2>Movimientos recientes</h2></header>
        {t.recientes.length === 0 && <p className="tenue chico">Registra el primero con el botón +.</p>}
        {t.recientes.slice(0, 12).map(x => {
          const cat = categorias[x.categoria_id]
          const titulo = x.descripcion || cat?.nombre || { gasto: 'Gasto', ingreso: 'Ingreso', transferencia: 'Transferencia', pago_deuda: 'Pago de deuda', aporte_bolsillo: 'Aporte' }[x.tipo]
          return (
            <div className="item" key={x.id}>
              <span className="emoji" aria-hidden>{cat?.icono || { gasto: '🧾', ingreso: '💰', transferencia: '🔁', pago_deuda: '💳', aporte_bolsillo: '🐖' }[x.tipo]}</span>
              <div className="cuerpo">
                <p>{titulo}</p>
                <p className="tenue chico">
                  {fechaCorta(x.fecha)} · {nombres[x.cuenta_id] ?? '—'}
                  {x.cuenta_destino_id && ` → ${nombres[x.cuenta_destino_id] ?? ''}`}
                  {personas[x.responsable] && ` · ${personas[x.responsable]}`}
                  {x.cuotas > 1 && ` · ${x.cuotas} cuotas`}
                </p>
              </div>
              <span className="monto num">{SIGNO[x.tipo]} {dinero(x.monto)}</span>
            </div>
          )
        })}
      </section>
    </>
  )
}
