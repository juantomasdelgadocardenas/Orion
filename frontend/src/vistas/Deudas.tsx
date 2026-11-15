import type { Deuda, InicioCaptura, Tablero } from '../tipos'
import { dinero, enDias, fechaCorta, mesAnio, porcentaje } from '../formato'
import { SaldoBajando } from '../graficos'
import { Entidad, Medidor, Vacio } from '../ui'

const SEMAFORO = { optimo: 'Buen día para comprar', neutro: 'Día normal', riesgo: 'Evita comprar hoy' }

function Calendario({ d }: { d: Deuda }) {
  if (!d.calendario) return null
  return (
    <>
      <p className="etiqueta">Próximos 35 días para comprar con esta tarjeta</p>
      <div className="calendario">
        {d.calendario.map((dia, i) => (
          <div key={dia.fecha} className={`dia ${dia.estado} ${i === 0 ? 'hoy' : ''}`}
            title={`${fechaCorta(dia.fecha)}: ${SEMAFORO[dia.estado]} · ${dia.dias_financiacion} días para pagar${dia.es_corte ? ' · corte' : ''}${dia.es_pago ? ' · pago' : ''}`}>
            {Number(dia.fecha.slice(8))}
            {(dia.es_corte || dia.es_pago) && <small>{dia.es_corte ? 'CORTE' : 'PAGO'}</small>}
          </div>
        ))}
      </div>
      <div className="claves">
        <span><i style={{ background: 'rgba(47,191,79,.6)' }} />Mejores días</span>
        <span><i style={{ background: 'rgba(240,105,106,.6)' }} />Días de riesgo</span>
        <span><i style={{ outline: '2px solid var(--acento)', background: 'transparent' }} />Hoy</span>
      </div>
      {d.proximo_dia_optimo && d.hoy?.estado !== 'optimo' && (
        <p className="sec chico" style={{ marginTop: 8 }}>
          Mejor día para una compra grande: <b>{fechaCorta(d.proximo_dia_optimo)}</b>, justo después del corte.
        </p>
      )}
      {d.hoy && <p className="sec chico" style={{ marginTop: 4 }}>Si compras hoy tienes <b>{d.hoy.dias_financiacion} días</b> antes de pagar.</p>}
    </>
  )
}

function Plan({ d }: { d: Deuda }) {
  const pendientes = d.plan.filter(p => !p.pagada)
  if (pendientes.length === 0) return null
  const puntos = [{ etiqueta: 'hoy', saldo: d.saldo, pago: 0 },
    ...pendientes.map(p => ({ etiqueta: mesAnio(p.fecha), saldo: p.saldo, pago: p.total }))]
  const manejo = d.plan.some(p => p.manejo > 0)
  return (
    <>
      <p className="etiqueta">Cómo va bajando la deuda</p>
      <SaldoBajando puntos={puntos} />
      <details className="tabla" open={d.tipo === 'credito' ? undefined : false}>
        <summary>Plan de pagos: cuánto pagas cada mes ({pendientes.length} pendientes)</summary>
        <div className="desplazable">
          <table>
            <thead><tr><th>Fecha</th><th>Pagas</th><th>A capital</th><th>Interés</th>{manejo && <th>Manejo</th>}<th>Quedas debiendo</th></tr></thead>
            <tbody>
              {d.plan.map(p => (
                <tr key={p.numero} className={p.pagada ? 'pagada' : ''}>
                  <td>{d.tipo === 'credito' ? `${p.numero}. ` : ''}{mesAnio(p.fecha)}{p.pagada ? ' ✓' : ''}</td>
                  <td>{dinero(p.total)}</td><td>{dinero(p.capital)}</td><td>{dinero(p.interes)}</td>
                  {manejo && <td>{dinero(p.manejo)}</td>}<td>{dinero(p.saldo)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  )
}

export default function Deudas({ t, abrirCaptura }: { t: Tablero; abrirCaptura: (i: InicioCaptura) => void }) {
  if (t.deudas.length === 0) {
    return <div className="tarjeta"><Vacio icono="💳" titulo="Sin tarjetas ni créditos">Agrégalos en Ajustes → Tarjetas y créditos.</Vacio></div>
  }
  return (
    <>
      <section className="rejilla-2">
        <div className="tarjeta dato"><p className="tenue chico">Deuda total</p><p className="valor num">{dinero(t.deuda_total)}</p></div>
        <div className="tarjeta dato"><p className="tenue chico">Por pagar este mes</p><p className="valor num">{dinero(t.dinero_real.deudas)}</p></div>
      </section>
      {t.deudas.map(d => {
        const porPagar = d.pendiente_ciclo + d.vencido
        return (
          <section className="tarjeta" key={d.id}>
            <div className="item" style={{ paddingTop: 0 }}>
              <Entidad nombre={d.institucion || d.nombre} lado={40} />
              <div className="cuerpo">
                <p>{d.nombre}</p>
                <p className="tenue chico">{d.tipo === 'tarjeta_credito' ? 'Tarjeta de crédito' : `Crédito · cuota ${d.cuotas_pagadas} de ${d.cuotas_totales}`}</p>
              </div>
              {d.hoy && <span className={`estado ${d.hoy.estado}`}>{SEMAFORO[d.hoy.estado]}</span>}
              {d.tipo === 'credito' && <span className={`estado ${d.en_mora ? 'critica' : 'bien'}`}>{d.en_mora ? 'Cuota vencida' : 'Al día'}</span>}
            </div>

            <div className="renglon"><span className="sec">Debes</span><b className="num">{dinero(d.saldo)}</b></div>
            {d.tipo === 'tarjeta_credito' && d.cupo_total > 0 && (
              <>
                <Medidor fraccion={d.uso_cupo} estado={d.uso_cupo >= 0.8 ? 'critico' : d.uso_cupo >= 0.5 ? 'aviso' : ''} />
                <p className="tenue chico" style={{ margin: '4px 0 8px' }}>
                  {porcentaje(d.uso_cupo)} del cupo usado · {dinero(d.cupo_disponible)} disponible
                </p>
              </>
            )}
            {d.tipo === 'credito' && (
              <>
                <Medidor fraccion={d.avance} estado="bien" />
                <p className="tenue chico" style={{ margin: '4px 0 8px' }}>
                  {porcentaje(d.avance)} pagado de {dinero(d.monto_original)} · faltan {dinero(d.intereses_restantes)} en intereses
                </p>
              </>
            )}
            {d.proximo_pago && (
              <div className="renglon">
                <span className="sec">Próximo pago · {fechaCorta(d.proximo_pago)}{d.dias_para_pago !== null && ` (${enDias(d.dias_para_pago)})`}</span>
                <b className="num">{dinero(d.pendiente_ciclo)}</b>
              </div>
            )}
            {d.pagado_ciclo > 0 && <div className="renglon chico"><span className="tenue">Ya abonaste a este pago</span><span className="num">{dinero(d.pagado_ciclo)}</span></div>}
            {d.vencido > 0 && <div className="renglon"><span>⚠️ Pago anterior sin registrar</span><b className="num">{dinero(d.vencido)}</b></div>}
            {porPagar > 0 && (
              <button className="boton secundario" style={{ margin: '8px 0 4px' }}
                onClick={() => abrirCaptura({ tipo: 'pago_deuda', cuenta_destino_id: d.id, monto: porPagar, titulo: `Pago: ${d.nombre}` })}>
                Registrar pago
              </button>
            )}

            <Calendario d={d} />

            {d.compras.length > 0 && (
              <>
                <p className="etiqueta" style={{ marginTop: 14 }}>Compras a cuotas</p>
                {d.compras.map((c, i) => (
                  <div className="item" key={i}>
                    <div className="cuerpo">
                      <p>{c.descripcion}</p>
                      <p className="tenue chico">Cuota {c.cuota_actual} de {c.cuotas} · {dinero(c.valor_cuota)} este mes · {fechaCorta(c.fecha)}</p>
                    </div>
                    <span className="monto num" title="Capital que falta">{dinero(c.restante)}</span>
                  </div>
                ))}
              </>
            )}
            <Plan d={d} />
          </section>
        )
      })}
    </>
  )
}
