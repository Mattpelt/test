import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import styles from './LoginPage.module.css'

const MAX_PIN = 6

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
        if (data.serial) {
          clearInterval(pollRef.current)
          navigate(`/onboarding?serial=${encodeURIComponent(data.serial)}`)
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
      const user = await login(currentPin)
      navigate(user.is_admin ? '/admin' : '/', { replace: true })
    } catch {
      setError('PIN incorrect.')
      setPin('')
    } finally {
      setLoading(false)
    }
  }

  function pressKey(k) {
    if (loading || pin.length >= MAX_PIN) return
    setPin(p => p + k)
  }

  function backspace() {
    setPin(p => p.slice(0, -1))
  }

  function confirm() {
    if (pin.length >= 4) handleLogin(pin)
  }

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
          <button
            className={`${styles.key} ${styles.keyConfirm} ${pin.length >= 4 ? styles.keyConfirmActive : ''}`}
            onClick={confirm}
            disabled={loading || pin.length < 4}
          >
            ✓
          </button>
          <button
            className={styles.key}
            onClick={() => pressKey('0')}
            disabled={loading}
          >
            0
          </button>
          <button
            className={styles.keyBack}
            onClick={backspace}
            disabled={loading || pin.length === 0}
          >
            ⌫
          </button>
        </div>

        <button
          className={styles.newUserBtn}
          onClick={() => navigate('/onboarding')}
        >
          Je suis nouveau →
        </button>
      </div>
    </div>
  )
}
