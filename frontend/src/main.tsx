import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './estilos.css'

// Dentro de la extensión de Chrome la app vive en una ventana emergente de tamaño fijo.
if (location.protocol === 'chrome-extension:') document.documentElement.classList.add('extension')

createRoot(document.getElementById('raiz')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
