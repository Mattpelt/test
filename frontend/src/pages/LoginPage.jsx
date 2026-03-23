import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import styles from './LoginPage.module.css'

const MAX_PIN = 4

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const pollRef = useRef(null)

  // Polling : détecte une caméra inconnue et redirige vers l'onboarding
  useEffect(() => {
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get('/internal/onboarding/pending')
        if (data.cameras?.length > 0) {
          clearInterval(pollRef.current)
          navigate('/onboarding')
        }
      } catch {
        // silencieux
      }
    }, 2000)
    return () => clearInterval(pollRef.current)
  }, [navigate])

  async function handleLogin(currentPin) {
    setError('')
    setLoading(true)
    try {
      await login(currentPin)
      // Admin et sautant arrivent tous sur la même HomePage
      navigate('/', { replace: true })
    } catch {
      setError('PIN incorrect.')
      setPin('')
    } finally {
      setLoading(false)
    }
  }

  function pressKey(k) {
    if (loading || pin.length >= MAX_PIN) return
    const next = pin + k
    setPin(next)
    // Auto-submit dès que le PIN est complet
    if (next.length === MAX_PIN) handleLogin(next)
  }

  function backspace() {
    setPin(p => p.slice(0, -1))
  }

  // Support clavier physique
  useEffect(() => {
    function onKey(e) {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (/^[0-9]$/.test(e.key)) pressKey(e.key)
      else if (e.key === 'Backspace') backspace()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <h1 className={styles.title}>SkyDive Media Hub</h1>

        {/* Indicateur de saisie */}
        <div className={styles.dots}>
          {Array.from({ length: MAX_PIN }).map((_, i) => (
            <span
              key={i}
              className={`${styles.dot} ${i < pin.length ? styles.dotFilled : ''}`}
            />
          ))}
        </div>

        {error && <p className={styles.error}>{error}</p>}

        {/* Pavé numérique */}
        <div className={styles.numpad}>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => (
            <button
              key={n}
              className={styles.key}
              onClick={() => pressKey(String(n))}
              disabled={loading}
            >
              {n}
            </button>
          ))}
          {/* Rangée du bas : effacer · 0 · (vide) */}
          <button
            className={styles.keyBack}
            onClick={backspace}
            disabled={loading || pin.length === 0}
            aria-label="Effacer"
          >
            ⌫
          </button>
          <button
            className={styles.key}
            onClick={() => pressKey('0')}
            disabled={loading}
          >
            0
          </button>
          <div />
        </div>

        <button
          className={styles.newUserBtn}
          onClick={() => navigate('/onboarding')}
        >
          Nouveau ? Créer mon compte
        </button>
      </div>
    </div>
  )
}
