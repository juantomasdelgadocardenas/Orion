# Orion — Arquitectura y esquema de datos

Finanzas personales compartidas. **React** (frontend, empaquetado como extensión de Chrome y como app web) ·
**Python / FastAPI** (lógica de negocio) · **Google Sheets vía `gspread`** (base de datos).

Nada de personas, bancos ni tarjetas está escrito en el código: todo se configura desde la pantalla de Ajustes
o cargando extractos, así cada hogar usa su propio libro.

## 1. Decisiones

| # | Decisión | Por qué |
|---|----------|---------|
| D1 | El frontend nunca habla con Google; solo el backend usa la cuenta de servicio | Las credenciales no pueden vivir en un navegador ni en una extensión. |
| D2 | Tres capas: `repositories` (única que importa `gspread`) → `services` (funciones puras) → `api` | Los cálculos se prueban sin red; el modo demo usa un almacén en memoria con la misma interfaz. |
| D3 | Los modelos Pydantic definen las columnas (`domain/modelos.py`) | Una sola fuente de verdad para la hoja, la validación y los formularios de Ajustes. |
| D4 | Saldos derivados: `saldo_inicial + Σ movimientos confirmados`. `saldo_actual`, `saldo_pendiente` y `monto_actual` son cachés | Dos personas registrando a la vez no se pisan; solo se agregan filas. |
| D5 | Montos enteros en pesos, siempre positivos; el signo lo da `tipo` | Sin errores de coma flotante ni de formato regional. |
| D6 | Escritura `RAW`, lectura `UNFORMATTED_VALUE`, fechas como texto `YYYY-MM-DD` | Ningún texto se ejecuta como fórmula y Sheets no reinterpreta fechas. |
| D7 | Una sola lectura por lote de todas las pestañas + caché de 20 s | La API de Sheets limita las lecturas por minuto. |
| D8 | Acceso por PIN compartido; cada dispositivo elige qué persona lo usa | Simple para un hogar. El PIN vive en `backend/.env`, nunca en el repositorio. |

## 2. Árbol de directorios

```
orion/
├── brand/                      logo (fuente de los iconos)
├── docs/ARQUITECTURA.md
├── backend/
│   ├── .env.example            variables necesarias (sin valores)
│   ├── secrets/                IGNORADO por git: JSON de la cuenta de servicio
│   ├── app/
│   │   ├── main.py             crea la app, CORS, sirve el frontend compilado
│   │   ├── core/
│   │   │   ├── config.py       única lectura de variables de entorno
│   │   │   ├── google_auth.py  única construcción de credenciales
│   │   │   └── auth.py         PIN, sesión firmada, bloqueo por intentos
│   │   ├── domain/modelos.py   modelos = columnas de la hoja
│   │   ├── repositories/
│   │   │   ├── esquema.py      pestañas y tablas configurables
│   │   │   ├── almacen.py      contrato + conversión fila ⇄ modelo
│   │   │   ├── sheets.py       Google Sheets
│   │   │   ├── memoria.py      en memoria (pruebas y demo)
│   │   │   └── demo.py         datos de ejemplo
│   │   ├── services/
│   │   │   ├── cuotas.py       planes de pago (capital constante y cuota fija)
│   │   │   ├── motor_tarjetas.py   cortes, pagos, mejores días y días de riesgo
│   │   │   ├── deudas.py       estado y plan mes a mes de cada tarjeta o crédito
│   │   │   ├── saldos.py       saldos derivados
│   │   │   ├── dinero_real.py
│   │   │   ├── metas.py
│   │   │   ├── presupuesto.py
│   │   │   ├── alertas.py
│   │   │   └── tablero.py      arma la respuesta única de la app
│   │   ├── importers/extractos.py  CSV/Excel → movimientos
│   │   └── api/rutas.py
│   ├── scripts/
│   │   ├── verificar_conexion.py
│   │   └── crear_esquema.py
│   └── tests/
└── frontend/
    ├── public/
    │   ├── manifest.json       extensión de Chrome (Manifest V3)
    │   ├── manifest.webmanifest    app web instalable (iPhone/Android)
    │   ├── icons/
    │   └── metas/              fotos de las metas (ej. akt-tt-200-rally.jpg)
    └── src/
        ├── App.tsx             navegación, sesión, avisos
        ├── api.ts · tipos.ts · formato.ts · estilos.css
        ├── ui.tsx              Anillo, Entidad, Hoja, Medidor, TecladoNumerico
        ├── graficos.tsx        FlujoMensual, SaldoBajando
        └── vistas/             Bloqueo, Inicio, Captura, Deudas, Importar, Ajustes, Alertas
```

## 3. Esquema de Google Sheets

Un libro, nueve pestañas. La fila 1 son los encabezados exactos; `scripts/crear_esquema.py` los crea y el backend
los valida al arrancar. Tipos: `texto` · `entero` · `decimal` · `booleano` (`TRUE`/`FALSE`) · `fecha` (`YYYY-MM-DD`) ·
`opcion` (valores listados).

### Pestaña `Usuarios`

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | ID |
| B | `nombre` | texto | Nombre |
| C | `color` | texto | Color |
| D | `activo` | booleano | Activo |

### Pestaña `Cuentas`

`saldo_actual` es un caché que escribe Orion; la verdad es `saldo_inicial` + movimientos.

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | ID |
| B | `nombre` | texto | Nombre |
| C | `tipo` | opcion | Tipo · `ahorros` · `corriente` · `billetera` · `efectivo` |
| D | `institucion` | texto | Banco o entidad |
| E | `titular` | texto | Titular → id de titulares |
| F | `moneda` | texto | Moneda |
| G | `saldo_inicial` | entero (pesos) | Saldo inicial |
| H | `fecha_saldo_inicial` | fecha | Fecha del saldo inicial |
| I | `saldo_actual` | entero | Saldo actual — caché, lo escribe Orion |
| J | `incluir_en_dinero_real` | booleano | Cuenta para Dinero Real |
| K | `activa` | booleano | Activa |
| L | `actualizado_en` | texto | Actualizado |

### Pestaña `Tarjetas_Deudas`

Una fila por tarjeta de crédito o crédito. Las columnas que no aplican al tipo se dejan vacías.

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | ID |
| B | `nombre` | texto | Nombre |
| C | `tipo` | opcion | Tipo · `tarjeta_credito` · `credito` |
| D | `institucion` | texto | Banco o entidad |
| E | `titular` | texto | Titular → id de titulares |
| F | `moneda` | texto | Moneda |
| G | `cupo_total` | entero (pesos) | Cupo total (solo `tarjeta_credito`) |
| H | `dia_corte` | entero | Día de corte (solo `tarjeta_credito`) |
| I | `dia_pago` | entero | Día de pago |
| J | `corte_inclusivo` | booleano | La compra del día de corte entra en ese corte (solo `tarjeta_credito`) |
| K | `cuota_manejo_mensual` | entero (pesos) | Cuota de manejo mensual (solo `tarjeta_credito`) |
| L | `tasa_ea` | decimal | Tasa efectiva anual (fracción: `0.265` = 26,5 %) |
| M | `saldo_inicial` | entero (pesos) | Deuda al empezar a usar Orion (solo `tarjeta_credito`) |
| N | `fecha_saldo_inicial` | fecha | Fecha de esa deuda (solo `tarjeta_credito`) |
| O | `cuotas_saldo_inicial` | entero | Cuotas en que se paga esa deuda (solo `tarjeta_credito`) |
| P | `monto_original` | entero (pesos) | Valor financiado (solo `credito`) |
| Q | `cuotas_totales` | entero | Número de cuotas (solo `credito`) |
| R | `cuotas_pagadas_iniciales` | entero | Cuotas ya pagadas al empezar (solo `credito`) |
| S | `fecha_inicio` | fecha | Fecha de la primera cuota (solo `credito`) |
| T | `saldo_pendiente` | entero | Saldo pendiente — caché, lo escribe Orion |
| U | `activa` | booleano | Activa |
| V | `actualizado_en` | texto | Actualizado |

### Pestaña `Transacciones`

Solo se agregan filas. Corregir = `estado` pasa a `anulada`.

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto |  |
| B | `fecha` | fecha |  |
| C | `monto` | entero |  |
| D | `tipo` | opcion | `gasto` · `ingreso` · `transferencia` · `pago_deuda` · `aporte_bolsillo` |
| E | `responsable` | texto |  |
| F | `categoria_id` | texto |  |
| G | `cuenta_id` | texto |  |
| H | `cuenta_destino_id` | texto |  |
| I | `bolsillo_id` | texto |  |
| J | `gasto_fijo_id` | texto |  |
| K | `descripcion` | texto |  |
| L | `cuotas` | entero |  |
| M | `estado` | opcion | `pendiente` · `confirmada` · `anulada` |
| N | `origen` | opcion | `manual` · `importacion` · `recurrente` |
| O | `huella_importacion` | texto |  |
| P | `creado_por` | texto |  |
| Q | `creado_en` | texto |  |
| R | `actualizado_en` | texto |  |

### Pestaña `Bolsillos_Metas`

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | ID |
| B | `nombre` | texto | Nombre |
| C | `tipo` | opcion | Tipo · `fondo_emergencia` · `meta` · `bolsillo` |
| D | `modo_avance` | opcion | Cómo se mide el avance · `ahorro` · `pago_deuda` |
| E | `monto_objetivo` | entero (pesos) | Monto objetivo |
| F | `monto_actual` | entero | Monto actual — caché, lo escribe Orion |
| G | `aporte_mensual` | entero (pesos) | Aporte mensual |
| H | `fecha_inicio` | fecha | Fecha de inicio |
| I | `fecha_objetivo` | fecha | Fecha objetivo |
| J | `cuenta_id` | texto | Cuenta donde está la plata → id de cuentas |
| K | `deuda_id` | texto | Crédito asociado → id de deudas |
| L | `responsable` | texto | Responsable → id de titulares |
| M | `prioridad` | entero | Prioridad |
| N | `imagen` | texto | Imagen |
| O | `destacar_en_dashboard` | booleano | Destacar en el inicio |
| P | `estado` | opcion | Estado · `activa` · `pausada` · `cumplida` |
| Q | `actualizado_en` | texto | Actualizado |

### Pestaña `Categorias`

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | ID |
| B | `nombre` | texto | Nombre |
| C | `tipo` | opcion | Tipo · `gasto` · `ingreso` |
| D | `grupo` | opcion | Grupo · `necesidades` · `gustos` · `ahorro_deuda` · `ingresos` |
| E | `presupuesto_mensual` | entero (pesos) | Presupuesto mensual |
| F | `icono` | texto | Icono |
| G | `color` | texto | Color |
| H | `orden` | entero | Orden |
| I | `activa` | booleano | Activa |

### Pestaña `Gastos_Fijos`

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | ID |
| B | `nombre` | texto | Nombre |
| C | `monto` | entero (pesos) | Monto mensual |
| D | `dia_cobro` | entero | Día de cobro |
| E | `categoria_id` | texto | Categoría → id de categorias |
| F | `cuenta_id` | texto | Cuenta de pago → id de cuentas |
| G | `responsable` | texto | Responsable → id de titulares |
| H | `activo` | booleano | Activo |

### Pestaña `Config`

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `clave` | texto |  |
| B | `valor` | texto |  |

### Pestaña `Importaciones`

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto |  |
| B | `fecha` | texto |  |
| C | `responsable` | texto |  |
| D | `cuenta_id` | texto |  |
| E | `huella_archivo` | texto |  |
| F | `filas_leidas` | entero |  |
| G | `filas_nuevas` | entero |  |
| H | `filas_duplicadas` | entero |  |
| I | `filas_rechazadas` | entero |  |

Claves de `Config`: `dias_alerta_pago` (5), `dias_zona_riesgo` (5), `umbral_presupuesto_aviso` (0.8), `zona_horaria` (America/Bogota).

## 4. Lógica de negocio

**Dinero Real** = saldo en cuentas − (gastos fijos sin pagar este mes + pagos de tarjetas y créditos que vencen este mes
+ ahorro apartado + aporte del mes que falta). Un gasto fijo deja de restar cuando existe un movimiento del mes con su
`gasto_fijo_id`; un pago de deuda deja de restar cuando se registra el `pago_deuda`.

**Cuotas.** Cada compra con tarjeta se reparte en `cuotas` pagos: abono a capital igual cada mes más interés sobre el
saldo con la tasa de la tarjeta (a una cuota no hay interés). La primera cuota cae en el pago del corte en el que entró
la compra. Los créditos usan cuota fija. De ahí salen el pago de cada mes, el plan completo y la curva de saldo.
Es una proyección: el banco puede cobrar una tasa distinta cada mes, así que el extracto manda.

**Motor de tarjetas.** Para cada día: *óptimo* (los 5 días siguientes al corte: máximo plazo para pagar),
*riesgo* (los `dias_zona_riesgo` anteriores al corte, incluido el día de corte si `corte_inclusivo`) o *neutro*.

**Metas.** Avance = apartado / objetivo; en modo `pago_deuda`, capital pagado / valor financiado.

**Alertas.** Dinero real negativo, pago vencido o sin registrar, pago en ≤ `dias_alerta_pago` días, cupo ≥ 80 %,
día de riesgo, presupuesto excedido o cerca del límite, meta atrasada.

## 5. Seguridad

- Secretos fuera de git: `.gitignore` cubre `.env`, `secrets/` y cualquier `*service-account*.json`.
- Alcance mínimo de Google: solo `spreadsheets`, sin Drive. La cuenta de servicio solo ve el libro que se le comparte.
- PIN comparado en tiempo constante; 5 intentos fallidos bloquean 5 minutos. Sesión firmada con HMAC, 30 días.
- CORS limitado a `localhost` y a extensiones de Chrome.
- Importación: solo `.csv` y `.xlsx` (sin macros), máx. 5 MB, en memoria; descripciones sin prefijos de fórmula y con
  números largos enmascarados; huella por movimiento para no duplicar; vista previa obligatoria; el archivo no se guarda.

## 6. Límites conocidos

- El lector de extractos es genérico (busca columnas de fecha y valor). No lee PDF.
- Día de corte, día de pago, cupo y tasa de cada tarjeta se escriben una vez en Ajustes: los extractos en CSV/Excel no los traen.
- Un PIN de 4 dígitos es suficiente en la red de la casa; antes de exponer el backend a internet hay que usar HTTPS y un PIN más largo.
