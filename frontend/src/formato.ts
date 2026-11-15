const pesos = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })
const miles = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 })
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

export const dinero = (n: number) => pesos.format(n).replace(/ /g, ' ')
export const numero = (n: number) => miles.format(n)
export const porcentaje = (fraccion: number) => `${Math.round(fraccion * 100)} %`

/** 1.250.000 → "1,3 M" · 85.000 → "85 K". Para ejes y espacios pequeños. */
export function compacto(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1_000_000) return `${(n / 1_000_000).toLocaleString('es-CO', { maximumFractionDigits: 1 })} M`
  if (abs >= 1_000) return `${Math.round(n / 1_000)} K`
  return String(n)
}

const partes = (iso: string) => iso.split('-').map(Number)
export const fechaCorta = (iso: string) => { const [, m, d] = partes(iso); return `${d} ${MESES[m - 1]}` }
export const mesAnio = (iso: string) => { const [a, m] = partes(iso); return `${MESES[m - 1]} ${a}` }

export function enDias(dias: number): string {
  if (dias === 0) return 'hoy'
  if (dias === 1) return 'mañana'
  if (dias < 0) return `hace ${-dias} día${dias === -1 ? '' : 's'}`
  return `en ${dias} días`
}

/** Escala "bonita" para un eje que empieza en cero. */
export function escalaEje(maximo: number, divisiones = 4): number[] {
  if (maximo <= 0) return [0, 1]
  const bruto = maximo / divisiones
  const potencia = 10 ** Math.floor(Math.log10(bruto))
  const paso = [1, 2, 2.5, 5, 10].map(f => f * potencia).find(p => p >= bruto)!
  const marcas = []
  for (let v = 0; v < maximo + paso; v += paso) marcas.push(Math.round(v))
  return marcas
}

// Colores de marca aproximados para reconocer cada entidad de un vistazo (no son sus logos oficiales).
const ENTIDADES: Record<string, string> = {
  daviplata: '#e4002b', davivienda: '#d6001c', nubank: '#820ad1', nu: '#820ad1', nequi: '#da0081',
  bancolombia: '#2c2a29', efectivo: '#1a7f4b', bbva: '#004481', 'banco de bogota': '#00387a', falabella: '#3f8f2f',
  akt: '#c81d25',
}
export function colorEntidad(nombre: string): string {
  const clave = nombre.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
  if (ENTIDADES[clave]) return ENTIDADES[clave]
  let h = 0
  for (const c of clave) h = (h * 31 + c.charCodeAt(0)) % 360
  return `hsl(${h} 45% 38%)`
}
export const iniciales = (nombre: string) =>
  nombre.trim().split(/\s+/).slice(0, 2).map(p => p[0]?.toUpperCase() ?? '').join('') || '?'
