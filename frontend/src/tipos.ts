export interface Usuario { id: string; nombre: string; color: string }
export interface Cuenta { id: string; nombre: string; tipo: string; institucion: string; titular: string; saldo: number }
export interface Categoria { id: string; nombre: string; tipo: 'gasto' | 'ingreso'; icono: string; color: string }
export interface GastoFijo { id: string; nombre: string; monto: number }

export interface PagoPlan {
  numero: number; fecha: string; capital: number; interes: number; manejo: number
  total: number; saldo: number; pagada: boolean
}
export interface CompraDiferida {
  descripcion: string; fecha: string; monto: number; cuotas: number
  cuota_actual: number; restante: number; valor_cuota: number
}
export interface DiaTarjeta { fecha: string; estado: EstadoDia; dias_financiacion: number; es_corte: boolean; es_pago: boolean }
export type EstadoDia = 'optimo' | 'neutro' | 'riesgo'

export interface Deuda {
  id: string; nombre: string; tipo: 'tarjeta_credito' | 'credito'; institucion: string
  cupo_total: number; cuota_manejo_mensual: number; tasa_ea: number
  saldo: number; proximo_pago: string | null; dias_para_pago: number | null
  pago_ciclo: number; pagado_ciclo: number; pendiente_ciclo: number; vencido: number; en_mora: boolean
  avance: number; uso_cupo: number; cupo_disponible: number
  cuotas_pagadas: number; cuotas_totales: number; monto_original: number; intereses_restantes: number
  plan: PagoPlan[]; compras: CompraDiferida[]
  hoy?: { estado: EstadoDia; dias_financiacion: number }
  proximo_corte?: string; proximo_dia_optimo?: string; calendario?: DiaTarjeta[]
}

export interface Meta {
  id: string; nombre: string; tipo: string; modo_avance: 'ahorro' | 'pago_deuda'; imagen: string
  destacar_en_dashboard: boolean; cuenta_id: string; deuda_id: string
  objetivo: number; actual: number; restante: number; avance: number
  estado_avance: 'cumplida' | 'en_ritmo' | 'atrasada' | 'sin_plan'
  aporte: number; ritmo_necesario: number; fecha_estimada: string | null; meses_cubiertos: number | null
  cuotas_pagadas: number; cuotas_totales: number
}

export interface Alerta { id: string; tipo: string; severidad: 'critica' | 'aviso' | 'info'; titulo: string; detalle: string; monto: number | null }
export interface Linea { grupo: 'saldo' | 'fijos' | 'deudas' | 'ahorro'; nombre: string; monto: number; fecha: string | null }

export interface Transaccion {
  id: string; fecha: string; monto: number; tipo: TipoMov; responsable: string; categoria_id: string
  cuenta_id: string; cuenta_destino_id: string; descripcion: string; cuotas: number; estado: string
}
export type TipoMov = 'gasto' | 'ingreso' | 'transferencia' | 'pago_deuda' | 'aporte_bolsillo'

export interface Tablero {
  hoy: string; modo: 'demo' | 'sheets'
  usuarios: Usuario[]; cuentas: Cuenta[]; categorias: Categoria[]; gastos_fijos: GastoFijo[]
  dinero_real: { total: number; saldo_bruto: number; comprometido: number; gastos_fijos: number; deudas: number; ahorro: number; lineas: Linea[] }
  deuda_tarjetas: number; deuda_total: number; ahorro_total: number
  flujo: { mes: string; etiqueta: string; ingresos: number; gastos: number }[]
  gasto_categorias: { id: string; nombre: string; icono: string; color: string; gastado: number; presupuesto: number; uso: number }[]
  deudas: Deuda[]; metas: Meta[]; alertas: Alerta[]; recientes: Transaccion[]
}

export interface NuevaTransaccion {
  monto: number; tipo: TipoMov; cuenta_id: string; fecha?: string; responsable?: string; categoria_id?: string
  cuenta_destino_id?: string; bolsillo_id?: string; gasto_fijo_id?: string; descripcion?: string; cuotas?: number
}

/** Con qué arranca la captura rápida cuando se abre desde otra pantalla. */
export interface InicioCaptura { tipo?: TipoMov; monto?: number; cuenta_destino_id?: string; bolsillo_id?: string; titulo?: string }

export interface Campo {
  nombre: string; titulo: string; tipo: 'texto' | 'entero' | 'decimal' | 'booleano' | 'fecha' | 'opcion'
  opciones: string[]; requerido: boolean; dinero?: boolean; ref?: string; ayuda?: string; solo?: string
  porcentaje?: boolean; color?: boolean; min?: number; max?: number; defecto?: unknown
}
export type Esquema = Record<string, { pestana: string; singular: string; campos: Campo[] }>
export type Fila = Record<string, any>

export interface FilaImportada { fecha: string; descripcion: string; monto: number; tipo: string; huella: string; estado: 'nueva' | 'duplicada' | 'posible_duplicada' }
export interface VistaPrevia { huella_archivo: string; ya_importado: boolean; filas_leidas: number; filas_rechazadas: number; filas: FilaImportada[] }
