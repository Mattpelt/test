import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import App from './App'
import './index.css'

// Applique le thème sauvegardé avant le premier rendu (évite le flash)
;(function () {
  const saved = localStorage.getItem('colorMode')
  if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light')
})()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
