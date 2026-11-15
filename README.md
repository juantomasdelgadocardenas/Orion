<p align="center">
  <img src="brand/orion-logo.svg" alt="Orion" width="340">
</p>

Finanzas personales compartidas: dinero real disponible, tarjetas y compras a cuotas, metas y alertas.
Frontend en React (extensión de Chrome y app web), lógica en Python, datos en Google Sheets.

Diseño completo y columnas exactas de la hoja: [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## 1. Probarla con datos de ejemplo

Requisitos: [uv](https://docs.astral.sh/uv/) y Node 20 o superior.

```bash
cd frontend && npm install && npm run build
```

```bash
cd backend && cp .env.example .env
```

Abre `backend/.env` y escribe tu PIN en `ORION_PIN=`. Luego:

```bash
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Abre <http://localhost:8000>. Verás la etiqueta **Demo**: son datos inventados que se reinician al apagar el servidor.

## 2. Instalarla como extensión de Chrome

1. Con el servidor encendido, abre `chrome://extensions` y activa **Modo de desarrollador**.
2. **Cargar descomprimida** → elige la carpeta `frontend/dist`.
3. Fija el icono de Orion en la barra.

La extensión habla con `http://localhost:8000`, así que funciona en el computador donde corre el servidor.

## 3. Usarla en el iPhone

Chrome en iPhone no admite extensiones. La misma app se abre como página web, sin licencia de desarrollador de Apple:

1. iPhone y computador en la misma red Wi-Fi, servidor encendido.
2. En Safari abre `http://IP-DEL-COMPUTADOR:8000` (la IP se ve con `ipconfig` en Windows o `ipconfig getifaddr en0` en Mac).
3. Compartir → **Agregar a pantalla de inicio**.

## 4. Conectar tu Google Sheets

1. En <https://console.cloud.google.com> crea un proyecto.
2. **APIs y servicios → Biblioteca** → habilita **Google Sheets API**.
3. **APIs y servicios → Credenciales → Crear credenciales → Cuenta de servicio**. No necesita roles.
4. Entra a la cuenta de servicio → **Claves → Agregar clave → JSON**. Guarda el archivo como `backend/secrets/service-account.json`.
5. Crea un libro vacío en Google Sheets y compártelo como **Editor** con el correo de la cuenta de servicio (termina en `iam.gserviceaccount.com`).
6. En `backend/.env` pon `ORION_MODO=sheets` y en `ORION_SHEET_ID` el texto que va entre `/d/` y `/edit` en la URL del libro.

```bash
cd backend && uv run python -m scripts.verificar_conexion
```

```bash
cd backend && uv run python -m scripts.crear_esquema --categorias
```

El segundo comando crea las pestañas con sus encabezados y unas categorías sugeridas (`--demo` carga además todos los datos de ejemplo). Después arranca el servidor como en el paso 1 y configura personas, cuentas y tarjetas desde **Ajustes**.

## 5. Foto de la moto

Guarda la foto como `frontend/public/metas/akt-tt-200-rally.jpg` y vuelve a ejecutar `npm run build`. El nombre del archivo es el campo **Imagen** de la meta.

## Pruebas

```bash
cd backend && uv run pytest
```
