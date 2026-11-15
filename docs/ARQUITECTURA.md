# Orion — Arquitectura y esquema de datos (v0.1)

Finanzas personales compartidas para Juan y Sofía.
Stack: **React** (frontend) · **Python** (lógica de negocio y API) · **Google Sheets vía `gspread`** (base de datos).

Estado: diseño. Todavía no hay código de aplicación; este documento es el contrato que seguirán las iteraciones 1 a 4.

---

## 0. Decisiones de arquitectura

| # | Decisión | Por qué |
|---|----------|---------|
| D1 | Monorepo con `backend/` y `frontend/` | Un solo lugar para el contrato API y los tipos; despliegues independientes. |
| D2 | El frontend **nunca** habla con Google. Solo el backend usa la cuenta de servicio | Las credenciales no pueden vivir en un navegador. |
| D3 | Tres capas en Python: `repositories` (única capa que importa `gspread`) → `services` (funciones puras) → `api` | Los servicios se prueban con datos simulados sin tocar la hoja (Iteración 2). |
| D4 | El saldo de una cuenta se **deriva**: `saldo_inicial + Σ transacciones confirmadas`. La columna `saldo_actual` es un caché que escribe el backend | Dos personas escribiendo a la vez no pueden pisarse el saldo; solo se agregan filas. |
| D5 | Montos como enteros en la unidad menor de la moneda (COP sin decimales), siempre positivos; el signo lo da `tipo` | Evita errores de coma flotante y de formato regional (`1.234.567,89`). |
| D6 | Fechas como texto ISO `YYYY-MM-DD`; marcas de tiempo ISO 8601 en UTC | Sheets no las reinterpreta según la configuración regional. |
| D7 | Toda escritura usa `value_input_option="RAW"`; toda lectura usa `UNFORMATTED_VALUE` | Bloquea la inyección de fórmulas (`=IMPORTXML(...)` en una descripción) y los números llegan como números. |
| D8 | IDs de texto estables (`cta_daviplata`, `txn_01J…`), nunca el número de fila | Ordenar o borrar filas a mano en la hoja no rompe las referencias. |
| D9 | Lectura con un solo `batch_get` de todas las pestañas + caché en memoria con TTL corto | La API de Sheets limita a ~60 lecturas por minuto por usuario. |
| D10 | Nombres de pestañas y columnas en español, `snake_case`, sin tildes | Legibles al abrir la hoja a mano y seguros como claves en código. |

---

## 1. Árbol de directorios

```
orion/
├── README.md
├── .gitignore                      # secretos, entornos, builds (desde el primer commit)
├── .pre-commit-config.yaml         # gitleaks + ruff
├── brand/                          # fuente de verdad de la identidad
│   ├── orion-icon.svg
│   └── orion-logo.svg
├── docs/
│   └── ARQUITECTURA.md
│
├── backend/
│   ├── pyproject.toml              # dependencias y config de ruff/pytest
│   ├── .env.example                # nombres de variables, sin valores reales
│   ├── secrets/                    # IGNORADO por git; aquí vive el JSON de la cuenta de servicio en local
│   ├── app/
│   │   ├── main.py                 # crea la app FastAPI, CORS, routers
│   │   ├── core/
│   │   │   ├── config.py           # pydantic-settings: lee .env, valida, SecretStr
│   │   │   ├── google_auth.py      # ÚNICO módulo que construye credenciales
│   │   │   ├── auth.py             # identifica a Juan / Sofía en cada petición
│   │   │   ├── errors.py
│   │   │   └── logging.py          # filtro que redacta secretos y números de cuenta
│   │   ├── domain/                 # modelos Pydantic, sin I/O
│   │   │   ├── enums.py            # TipoCuenta, TipoTransaccion, Estado, Responsable…
│   │   │   ├── dinero.py           # tipo Dinero (entero + moneda), formateo
│   │   │   ├── cuenta.py
│   │   │   ├── tarjeta_deuda.py
│   │   │   ├── transaccion.py
│   │   │   ├── bolsillo_meta.py
│   │   │   ├── categoria.py
│   │   │   └── gasto_fijo.py
│   │   ├── repositories/           # ÚNICA capa que importa gspread
│   │   │   ├── sheets_client.py    # abre el libro por ID, batch_get, reintentos, caché TTL
│   │   │   ├── esquema.py          # pestañas y columnas como constantes (espejo de la sección 2)
│   │   │   ├── base.py             # fila ⇄ modelo, validación de encabezados
│   │   │   ├── cuentas.py
│   │   │   ├── tarjetas_deudas.py
│   │   │   ├── transacciones.py
│   │   │   ├── bolsillos_metas.py
│   │   │   ├── catalogos.py        # Categorias, Gastos_Fijos, Config
│   │   │   └── memoria.py          # repos falsos en memoria para pruebas y modo demo
│   │   ├── services/               # funciones puras: (modelos, hoy) -> resultado
│   │   │   ├── dinero_real.py
│   │   │   ├── motor_tarjetas.py
│   │   │   ├── proyeccion_metas.py
│   │   │   ├── presupuesto.py
│   │   │   ├── alertas.py
│   │   │   └── saldos.py           # recalcula saldo_actual desde transacciones
│   │   ├── importers/              # extractos CSV/Excel
│   │   │   ├── pipeline.py         # orquesta: validar → parsear → normalizar → deduplicar → previsualizar
│   │   │   ├── validacion.py       # tamaño, extensión, tipo real del archivo
│   │   │   ├── deteccion.py        # reconoce el banco por la firma de encabezados
│   │   │   ├── normalizacion.py    # fechas, montos con formato colombiano, signos
│   │   │   ├── saneamiento.py      # neutraliza fórmulas, recorta, enmascara
│   │   │   ├── deduplicacion.py    # huella por movimiento
│   │   │   └── parsers/
│   │   │       ├── base.py         # interfaz ParserExtracto
│   │   │       ├── davivienda.py
│   │   │       ├── daviplata.py
│   │   │       └── nubank.py
│   │   └── api/
│   │       ├── deps.py             # inyección de repos y usuario actual
│   │       ├── schemas/            # DTOs de entrada/salida
│   │       └── routers/
│   │           ├── dashboard.py    # GET /dashboard (todo lo que pinta la portada en una llamada)
│   │           ├── transacciones.py# POST /transacciones (captura rápida), GET, PATCH
│   │           ├── tarjetas.py     # GET /tarjetas/calendario
│   │           ├── metas.py
│   │           ├── alertas.py
│   │           ├── importacion.py  # POST /importacion/previsualizar, POST /importacion/confirmar
│   │           └── catalogos.py    # cuentas, categorías
│   ├── scripts/
│   │   ├── verificar_conexion.py   # Iteración 1: prueba de conexión
│   │   ├── crear_esquema.py        # crea pestañas y encabezados si no existen (idempotente)
│   │   └── sembrar_demo.py         # Iteración 2: datos simulados
│   └── tests/
│       ├── unit/                   # services e importers, sin red
│       ├── integration/            # contra una hoja de pruebas (opt-in)
│       └── fixtures/               # extractos de ejemplo anonimizados
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    ├── public/                     # favicon y manifest (PWA) generados desde brand/
    └── src/
        ├── main.tsx
        ├── app/                    # App, rutas, providers (query client, tema, sesión)
        ├── api/                    # cliente HTTP y hooks de datos
        ├── types/                  # tipos espejo de los DTO del backend
        ├── lib/                    # formato de moneda y fechas (es-CO)
        ├── styles/                 # tokens de diseño (color, tipografía, espaciado)
        ├── components/ui/          # primitivas: Card, Button, Sheet, Chip, CircularProgress, Toast
        ├── assets/
        │   ├── bancos/             # logos: daviplata, davivienda, nubank, efectivo
        │   └── metas/              # akt-tt-200-rally.webp
        └── features/
            ├── dashboard/
            ├── captura-rapida/
            ├── alertas/
            ├── tarjetas/
            ├── metas/
            └── importacion/
```

---

## 2. Arquitectura de datos (Google Sheets)

Un solo libro. Fila 1 = encabezados exactos (el backend los valida al arrancar y falla con un mensaje claro si no coinciden). Fila 1 congelada y protegida.

Convenciones de tipo: `texto` · `entero` (montos, sin separadores) · `decimal` · `fecha` (`YYYY-MM-DD`) · `marca_tiempo` (ISO 8601 UTC) · `booleano` (`TRUE`/`FALSE`) · `enum` (valores listados).

### 2.1 Pestaña `Cuentas`

| Col | Columna | Tipo | Req. | Descripción / valores |
|-----|---------|------|------|-----------------------|
| A | `id` | texto | sí | `cta_daviplata`, `cta_davivienda`, `cta_nubank`, `cta_efectivo` |
| B | `nombre` | texto | sí | Daviplata · Davivienda · Nubank · Efectivo |
| C | `tipo` | enum | sí | `ahorros` · `corriente` · `billetera` · `efectivo` |
| D | `institucion` | enum | sí | `daviplata` · `davivienda` · `nubank` · `efectivo` (clave del logo) |
| E | `titular` | enum | sí | `Juan` · `Sofía` · `Compartida` |
| F | `moneda` | texto | sí | ISO 4217, `COP` |
| G | `saldo_inicial` | entero | sí | Saldo en la fecha de corte inicial |
| H | `fecha_saldo_inicial` | fecha | sí | Las transacciones anteriores a esta fecha no afectan el saldo |
| I | `saldo_actual` | entero | caché | Lo escribe el backend; no editar a mano |
| J | `incluir_en_dinero_real` | booleano | sí | `FALSE` para cuentas que no deben contar como disponibles |
| K | `activa` | booleano | sí | Borrado lógico |
| L | `actualizado_en` | marca_tiempo | sí | |

### 2.2 Pestaña `Tarjetas_Deudas`

| Col | Columna | Tipo | Req. | Descripción / valores |
|-----|---------|------|------|-----------------------|
| A | `id` | texto | sí | `tdc_nubank`, `deu_moto_akt` |
| B | `nombre` | texto | sí | |
| C | `tipo` | enum | sí | `tarjeta_credito` · `credito` · `prestamo_personal` |
| D | `institucion` | texto | sí | |
| E | `titular` | enum | sí | `Juan` · `Sofía` · `Compartida` |
| F | `moneda` | texto | sí | `COP` |
| G | `cupo_total` | entero | tarjetas | Cupo aprobado |
| H | `saldo_pendiente` | entero | sí | Deuda total a hoy |
| I | `dia_corte` | entero 1–31 | tarjetas | Si el mes no tiene ese día, se usa el último día del mes |
| J | `dia_pago` | entero 1–31 | sí | Fecha límite de pago |
| K | `corte_inclusivo` | booleano | tarjetas | `TRUE` si la compra hecha el día de corte entra en ese corte |
| L | `pago_mes` | entero | sí | Lo que hay que pagar en el ciclo actual (pago total de la tarjeta o cuota del crédito) |
| M | `pago_minimo` | entero | no | |
| N | `pago_mes_realizado` | booleano | sí | Evita restar dos veces en Dinero Real |
| O | `cuota_manejo_mensual` | entero | sí | `0` si no aplica |
| P | `tasa_ea` | decimal | no | Tasa efectiva anual, `0.2985` = 29,85 % |
| Q | `monto_original` | entero | créditos | Valor financiado (base del % de avance) |
| R | `cuotas_totales` | entero | créditos | |
| S | `cuotas_pagadas` | entero | créditos | |
| T | `fecha_inicio` | fecha | créditos | |
| U | `cuenta_pago_id` | texto | no | → `Cuentas.id` desde donde se paga |
| V | `activa` | booleano | sí | |
| W | `actualizado_en` | marca_tiempo | sí | |

### 2.3 Pestaña `Transacciones`

Solo se agregan filas. Corregir = cambiar `estado` a `anulada` y crear una nueva.

| Col | Columna | Tipo | Req. | Descripción / valores |
|-----|---------|------|------|-----------------------|
| A | `id` | texto | sí | `txn_` + ULID (ordenable por tiempo) |
| B | `fecha` | fecha | sí | Fecha del movimiento |
| C | `monto` | entero | sí | Siempre positivo |
| D | `tipo` | enum | sí | `gasto` · `ingreso` · `transferencia` · `pago_tarjeta` · `aporte_bolsillo` |
| E | `responsable` | enum | sí | `Juan` · `Sofía` |
| F | `categoria_id` | texto | gasto/ingreso | → `Categorias.id` |
| G | `cuenta_id` | texto | sí | Origen: → `Cuentas.id` o → `Tarjetas_Deudas.id` |
| H | `cuenta_destino_id` | texto | transferencia / pago | Destino: cuenta, tarjeta o deuda |
| I | `bolsillo_id` | texto | aporte | → `Bolsillos_Metas.id` |
| J | `gasto_fijo_id` | texto | no | → `Gastos_Fijos.id`; marca ese gasto fijo como pagado en el mes |
| K | `descripcion` | texto | no | Máx. 140 caracteres, saneado |
| L | `cuotas` | entero | no | Número de cuotas si la compra es con tarjeta; por defecto `1` |
| M | `estado` | enum | sí | `pendiente` · `confirmada` · `anulada` |
| N | `origen` | enum | sí | `manual` · `importacion` · `recurrente` |
| O | `huella_importacion` | texto | importadas | SHA-256 para deduplicar |
| P | `creado_por` | enum | sí | `Juan` · `Sofía` (quién la registró; puede diferir del responsable) |
| Q | `creado_en` | marca_tiempo | sí | |
| R | `actualizado_en` | marca_tiempo | sí | |

### 2.4 Pestaña `Bolsillos_Metas`

| Col | Columna | Tipo | Req. | Descripción / valores |
|-----|---------|------|------|-----------------------|
| A | `id` | texto | sí | `bol_emergencia`, `meta_moto_akt` |
| B | `nombre` | texto | sí | |
| C | `tipo` | enum | sí | `fondo_emergencia` · `meta` · `bolsillo` |
| D | `modo_avance` | enum | sí | `ahorro` (avance = capital asignado) · `pago_deuda` (avance = deuda pagada) |
| E | `monto_objetivo` | entero | sí | |
| F | `monto_actual` | entero | caché | Capital asignado; lo recalcula el backend desde los aportes |
| G | `aporte_mensual` | entero | sí | Compromiso mensual; entra en Dinero Real como ahorro |
| H | `fecha_inicio` | fecha | sí | |
| I | `fecha_objetivo` | fecha | no | |
| J | `cuenta_id` | texto | no | → `Cuentas.id` donde está físicamente el dinero |
| K | `deuda_id` | texto | si `pago_deuda` | → `Tarjetas_Deudas.id` |
| L | `responsable` | enum | sí | `Juan` · `Sofía` · `Compartida` |
| M | `prioridad` | entero | sí | `1` = más alta |
| N | `imagen` | texto | no | Clave del recurso visual, p. ej. `akt-tt-200-rally` |
| O | `destacar_en_dashboard` | booleano | sí | `TRUE` para la tarjeta de la moto |
| P | `estado` | enum | sí | `activa` · `pausada` · `cumplida` |
| Q | `actualizado_en` | marca_tiempo | sí | |

### 2.5 Pestañas de soporte

Las cuatro capas pedidas no se pueden calcular sin estas; son pequeñas y casi estáticas.

**`Categorias`** — necesaria para las alertas de presupuesto.

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | `cat_mercado` |
| B | `nombre` | texto | |
| C | `tipo` | enum | `gasto` · `ingreso` |
| D | `grupo` | enum | `necesidades` · `gustos` · `ahorro_deuda` |
| E | `presupuesto_mensual` | entero | `0` = sin límite |
| F | `icono` | texto | Clave del icono |
| G | `color` | texto | Hex |
| H | `orden` | entero | Orden en la captura rápida |
| I | `activa` | booleano | |

**`Gastos_Fijos`** — necesaria para Dinero Real.

| Col | Columna | Tipo | Descripción |
|-----|---------|------|-------------|
| A | `id` | texto | `gf_arriendo` |
| B | `nombre` | texto | |
| C | `monto` | entero | |
| D | `dia_cobro` | entero 1–31 | |
| E | `frecuencia` | enum | `mensual` · `bimestral` · `anual` |
| F | `categoria_id` | texto | → `Categorias.id` |
| G | `cuenta_id` | texto | → `Cuentas.id` o tarjeta |
| H | `responsable` | enum | `Juan` · `Sofía` · `Compartida` |
| I | `activo` | booleano | |

**`Config`** — pares clave/valor.

| Col | Columna | Descripción |
|-----|---------|-------------|
| A | `clave` | `version_esquema`, `dias_alerta_pago`, `dias_zona_riesgo`, `umbral_presupuesto_aviso`, `zona_horaria` |
| B | `valor` | `1`, `5`, `5`, `0.8`, `America/Bogota` |

**`Importaciones`** — bitácora de auditoría (nunca guarda el archivo).

| Col | Columna | Descripción |
|-----|---------|-------------|
| A | `id` | |
| B | `fecha` | marca_tiempo |
| C | `responsable` | |
| D | `cuenta_id` | |
| E | `huella_archivo` | SHA-256 del archivo; impide importar dos veces el mismo extracto |
| F | `filas_leidas` | |
| G | `filas_nuevas` | |
| H | `filas_duplicadas` | |
| I | `filas_rechazadas` | |

---

## 3. Lógica de negocio (Python)

Regla común: cada servicio es una función pura que recibe modelos de dominio y `hoy: date`, y devuelve un resultado tipado. No lee la hoja ni el reloj.

### 3.1 `dinero_real.py`

```
dinero_real = saldo_bruto − (gastos_fijos_pendientes + pagos_deuda_pendientes + ahorro_comprometido)
```

| Término | Cómo se calcula |
|---------|-----------------|
| `saldo_bruto` | Σ `saldo_actual` de cuentas activas con `incluir_en_dinero_real` |
| `gastos_fijos_pendientes` | Σ `Gastos_Fijos.monto` que tocan este mes y **no** tienen una transacción confirmada del mes con su `gasto_fijo_id` |
| `pagos_deuda_pendientes` | Σ (`pago_mes` + `cuota_manejo_mensual`) de tarjetas y créditos con `pago_mes_realizado = FALSE` |
| `ahorro_comprometido` | Σ `aporte_mensual` aún no aportado este mes **+** Σ `monto_actual` de bolsillos cuyo `cuenta_id` es una cuenta incluida en el saldo bruto |

La regla de "pendiente" es lo que evita restar dos veces algo que ya salió del banco. Salida: `ResultadoDineroReal` con el total y el desglose línea por línea (el dashboard muestra el porqué del número), más una variante por responsable.

### 3.2 `motor_tarjetas.py`

Para cada tarjeta, dado `hoy`:

1. `resolver_fecha(dia, año, mes)`: ajusta días 29–31 al último día del mes.
2. `proximo_corte`, `proximo_pago`, `corte_anterior`.
3. `dias_de_financiacion(fecha_compra)`: días entre la compra y la fecha de pago del ciclo en que cae. Es máximo el día siguiente al corte y mínimo el día de corte.
4. Clasificación de cada día de los próximos 60:
   - **óptimo** — del día siguiente al corte hasta `corte + 5`
   - **neutro** — resto del ciclo
   - **riesgo** — los `dias_zona_riesgo` anteriores al corte (la compra se paga en pocos días) y cualquier día en que `uso_cupo > 80 %`
5. Comparador entre tarjetas: "hoy conviene pagar con X (N días de financiación)".

Salida: `CalendarioTarjeta` (lista de días con estado), `semaforo_hoy` y `mejor_tarjeta_hoy`. Días festivos y fines de semana se tratan como dato informativo; los bancos difieren en cómo corren el corte y por eso existe `corte_inclusivo`.

### 3.3 `proyeccion_metas.py`

| Cálculo | Fórmula |
|---------|---------|
| Avance (modo `ahorro`) | `monto_actual / monto_objetivo` |
| Avance (modo `pago_deuda`) | `(monto_original − saldo_pendiente) / monto_original` |
| Ritmo necesario | `(objetivo − actual) / meses hasta fecha_objetivo` |
| Fecha estimada | `hoy + (objetivo − actual) / aporte_mensual` meses |
| Estado | `en_ritmo` · `atrasada` · `adelantada` · `cumplida` |
| Fondo de emergencia | Además: `meses_cubiertos = monto_actual / Σ gastos fijos mensuales` |

### 3.4 `presupuesto.py` y `alertas.py`

`presupuesto.py` suma el gasto confirmado del mes por categoría contra `presupuesto_mensual`. `alertas.py` consume los resultados de los demás servicios y emite una lista ordenada por severidad:

| Tipo | Disparador | Severidad |
|------|------------|-----------|
| `presupuesto_excedido` | gasto ≥ 100 % del límite | crítica |
| `presupuesto_cerca` | gasto ≥ `umbral_presupuesto_aviso` | aviso |
| `pago_tarjeta_cercano` | faltan ≤ `dias_alerta_pago` y `pago_mes_realizado = FALSE` | crítica si ≤ 2 días |
| `pago_vencido` | pasó `dia_pago` sin pago | crítica |
| `dia_de_riesgo` | hoy está en zona de riesgo de una tarjeta | informativa |
| `meta_atrasada` | estado `atrasada` | aviso |
| `dinero_real_negativo` | resultado < 0 | crítica |

Cada alerta tiene un `id` determinista (tipo + entidad + periodo) para que el frontend pueda descartarla sin que reaparezca.

---

## 4. Frontend (React) — jerarquía de componentes

Dirección visual: oscuro, minimalista, cifras grandes, una acción principal por pantalla; inspirado en apps tipo Monai, con identidad propia de Orion (azul noche + naranja del logo).

```
<App>
└─ <Providers>                         sesión (Juan/Sofía), caché de datos, tema
   └─ <AppShell>
      ├─ <TopBar>                      logo · <FiltroResponsable> · <CampanaAlertas>
      ├─ <BannerAlertaCritica>         solo si hay alertas críticas
      │
      ├─ <DashboardPage>
      │  ├─ <DineroRealHero>           la cifra principal
      │  │  └─ <DesgloseDineroReal>    bruto − fijos − tarjetas − ahorro (expandible)
      │  ├─ <FilaResumen>
      │  │  └─ <TarjetaResumen> ×4     Saldo bruto · Comprometido · Deuda tarjetas · Ahorro
      │  ├─ <SeccionFlujo>
      │  │  ├─ <GraficoFlujoMensual>   ingresos vs. gastos por mes
      │  │  ├─ <GraficoCategorias>     gasto del mes por categoría, con límite
      │  │  └─ <SelectorPeriodo>
      │  ├─ <TarjetaMoto>              AKT TT 200 Rally
      │  │  ├─ <ProgresoCircular>      anillo SVG con % de avance
      │  │  │  └─ <ImagenMeta>         foto de la moto dentro del anillo
      │  │  └─ <DatosMoto>             pagado · restante · cuotas · fecha estimada
      │  ├─ <CarruselTarjetas>
      │  │  └─ <ChipSemaforoTarjeta>   óptimo / neutro / riesgo hoy
      │  ├─ <ListaMetas>
      │  │  └─ <FilaMeta>
      │  └─ <MovimientosRecientes>
      │     └─ <FilaTransaccion>
      │
      ├─ <BotonCapturaFlotante>        siempre visible
      ├─ <HojaCapturaRapida>           panel inferior
      │  ├─ <TecladoMonto>             abre enfocado, teclado numérico propio
      │  ├─ <SelectorBancoLogos>
      │  │  └─ <BotonBanco> ×4         Daviplata · Davivienda · Nubank · Efectivo
      │  ├─ <ChipsCategoria>           las 6 más usadas + "más"
      │  ├─ <ToggleResponsable>        por defecto, quien tiene la sesión
      │  ├─ <DetallesOpcionales>       fecha, nota, cuotas (plegado)
      │  └─ <BotonGuardar>
      │
      ├─ <CentroAlertas>               panel lateral
      │  └─ <ListaAlertas>
      │     └─ <ItemAlerta>            icono por tipo · severidad · acción · descartar
      └─ <AnfitrionToasts>             confirmación con "Deshacer"
```

**Presupuesto de 5 segundos de la captura rápida:** monto → banco → categoría → guardar. Tres toques más el monto. Lo logran los valores por defecto (fecha = hoy, responsable = sesión, estado = `confirmada`, banco = último usado preseleccionado), el guardado optimista (la UI no espera a Sheets) y un toast con "Deshacer" en lugar de un diálogo de confirmación.

**Recursos visuales:** los logos de los bancos y la foto de la AKT TT 200 Rally son archivos que se colocan en `assets/`; mientras no existan, los botones muestran color e inicial del banco y la tarjeta de la moto un marcador de posición.

---

## 5. Seguridad y sincronización

### 5.1 Credenciales de Google Cloud

| Medida | Implementación |
|--------|----------------|
| Nada de secretos en git | `.gitignore` cubre `secrets/`, `.env*`, `*service-account*.json` desde el primer commit; `gitleaks` en pre-commit |
| Un solo punto de carga | `core/config.py` (pydantic-settings) lee `GOOGLE_SERVICE_ACCOUNT_FILE` (ruta, en local) o `GOOGLE_SERVICE_ACCOUNT_JSON_B64` (variable, en despliegue). El resto del código recibe un cliente ya construido |
| Un solo punto de uso | Solo `core/google_auth.py` construye credenciales; solo `repositories/` usa el cliente |
| Mínimo privilegio | Alcance único `https://www.googleapis.com/auth/spreadsheets` (sin Drive); se abre el libro por ID. La cuenta de servicio es editora de **ese** libro y de nada más |
| Sin fugas en logs | Secretos como `SecretStr`; filtro de logging que redacta claves y números de cuenta; los errores hacia el cliente no incluyen trazas |
| Frontend sin secretos | El navegador solo conoce la URL del backend; CORS limitado al origen del frontend |
| Acceso de personas | `core/auth.py` autentica cada petición y la asocia a Juan o Sofía (mecanismo según la pregunta 3) |
| Rotación | Procedimiento documentado: crear clave nueva → actualizar variable → borrar la anterior |
| Arranque seguro | Si falta una variable o los encabezados no coinciden, la app no arranca y dice exactamente qué falta |

### 5.2 Importación de extractos CSV/Excel

Sin conexión a los bancos: la persona descarga el extracto desde la app de su banco y lo sube a Orion.

```
subir archivo
  → 1. validar      extensión permitida (.csv, .xlsx), tamaño máx. 5 MB, tipo real del contenido;
                    se rechazan .xls/.xlsm (macros) y archivos con contraseña
  → 2. leer         en memoria, nunca a disco; Excel en modo solo-lectura y solo-valores;
                    detección de codificación (UTF-8 / Latin-1)
  → 3. detectar     banco por firma de encabezados; si no se reconoce, se pide elegirlo
  → 4. parsear      adaptador por banco → MovimientoCrudo(fecha, descripcion, monto, signo)
  → 5. normalizar   fechas a ISO, montos "1.234.567,89" a entero, signo a tipo gasto/ingreso
  → 6. sanear       descripción recortada; prefijos = + - @ neutralizados; números de cuenta enmascarados
  → 7. deduplicar   huella = SHA-256(cuenta_id | fecha | monto | descripcion_normalizada | ordinal_del_dia)
                    comparada contra Transacciones.huella_importacion
                    y coincidencia difusa contra capturas manuales (misma cuenta, mismo monto, ±2 días)
  → 8. previsualizar  respuesta al frontend: nuevas / duplicadas / posibles duplicadas / rechazadas
  ── la persona revisa y confirma ──
  → 9. escribir     un solo append por lote, origen = importacion, estado = pendiente (por categorizar)
  → 10. registrar   fila en Importaciones; el archivo se descarta
```

Garantías: es **idempotente** (subir el mismo extracto dos veces no duplica nada), tiene **vista previa obligatoria** (nada se escribe sin confirmación) y **no persiste el archivo original**. Los adaptadores por banco se escriben contra extractos reales anonimizados guardados en `tests/fixtures/`.

### 5.3 Concurrencia con dos personas

- Altas: `append_rows`, que es atómico por llamada; no hay lectura-modificación-escritura.
- Ediciones: se localiza la fila por `id` en el momento de escribir, nunca por un índice guardado.
- Saldos y `monto_actual`: recalculados desde las transacciones, así que el orden de llegada no importa.
- Reintentos con espera exponencial ante el error 429 de cuota.

---

## 6. Plan de iteraciones

| Iteración | Entregable | Criterio de terminado |
|-----------|-----------|-----------------------|
| 1 | Entorno Python, `config.py`, `google_auth.py`, `verificar_conexion.py`, `crear_esquema.py` | El script lee el título del libro y crea las 8 pestañas con sus encabezados |
| 2 | `domain/`, `services/dinero_real.py`, `sembrar_demo.py`, pruebas unitarias | Dinero Real calculado sobre datos simulados y explicado línea por línea |
| 3 | Proyecto React, tokens de diseño, Dashboard con datos de ejemplo, tarjeta AKT TT 200 | Dashboard navegable en móvil y escritorio |
| 4 | API FastAPI, `POST /transacciones`, Captura Rápida conectada | Un gasto registrado en la UI aparece en la hoja en menos de 5 segundos de interacción |
