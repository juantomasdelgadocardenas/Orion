import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// base relativa: el mismo build sirve como extensión de Chrome, como web y detrás del backend.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  build: { modulePreload: { polyfill: false } },
})
