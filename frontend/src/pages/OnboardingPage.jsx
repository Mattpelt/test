import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import styles from './OnboardingPage.module.css'

export default function OnboardingPage() {
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Serial passé en URL (arrivée automatique depuis LoginPage)
  const urlSerial = searchParams.get('serial') || ''

  // Serial détecté (URL ou polling en cours de formulaire)
  const [cameraSerial, setCameraSerial] = useState(urlSerial)
  // 'waiting' | 'detected' | 'skipped'
  const [cameraState, setCameraState] = useState(urlSerial ? 'detected' : 'waiting')

  const [form, setForm] = useState({
    first_name: '', last_name: '', afifly_name: '', email: '',
    pin: '', pinConfirm: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const pollRef = useRef(null)

  // Polling caméra — uniquement si on est en mode 'waiting'
  useEffect(() => {
    if (cameraState !== 'waiting') return

    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get('/internal/onboarding/pending')
        if (data?.serial) {
          setCameraSerial(data.serial)
          setCameraState('detected')
        }
      } catch { /* silencieux */ }
    }, 2000)

    return () => clearInterval(pollRef.current)
  }, [cameraState])

  function skipCamera() {
    clearInterval(pollRef.current)
    api.delete('/internal/onboarding/pending').catch(() => {})
    setCameraSerial('')
    setCameraState('skipped')
  }

  function removeCamera() {
    api.delete('/internal/onboarding/pending').catch(() => {})
    setCameraSerial('')
    setCameraState('waiting')
  }

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function submit(e) {
    e.preventDefault()
    setError('')

    if (!/^\d{4}$/.test(form.pin)) {
      setError('Le PIN doit contenir exactement 4 chiffres.')
      return
    }
    if (form.pin !== form.pinConfirm) {
      setError('Les deux PIN ne correspondent pas.')
      return
    }

    clearInterval(pollRef.current)
    setLoading(true)
    try {
      const payload = {
        first_name:    form.first_name,
        last_name:     form.last_name,
        afifly_name:   form.afifly_name || null,
        email:         form.email || null,
        pin:           form.pin,
        camera_serial: cameraSerial || null,
      }
      const { data } = await api.post('/users/onboard', payload)
      await loginWithToken(data.access_token)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur lors de la création du compte.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <button className={styles.back} onClick={() => navigate('/login')}>← Retour</button>

        <h1 className={styles.title}>Créer mon compte</h1>

        <form onSubmit={submit} className={styles.form}>
          {/* Identité */}
          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Prénom *</label>
              <input className={styles.input} value={form.first_name} onChange={set('first_name')} required />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Nom *</label>
              <input className={styles.input} value={form.last_name} onChange={set('last_name')} required />
            </div>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>
              Nom Afifly *
              <span className={styles.hint}>Tel qu'il apparaît sur les feuilles de rotation (ex : DUPONT Julien)</span>
            </label>
            <input
              className={styles.input}
              value={form.afifly_name}
              onChange={set('afifly_name')}
              placeholder="NOM Prénom"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>
              Email <span className={styles.optional}>(optionnel — pour recevoir les notifications)</span>
            </label>
            <input className={styles.input} type="email" value={form.email} onChange={set('email')} />
          </div>

          <div className={styles.divider} />

          {/* Détection caméra */}
          <div className={styles.cameraSection}>
            <div className={styles.cameraLabel}>Caméra</div>

            {cameraState === 'waiting' && (
              <div className={styles.cameraWaiting}>
                <span className={styles.pulse} />
                <div>
                  <div className={styles.cameraWaitingText}>En attente de connexion…</div>
                  <div className={styles.cameraWaitingHint}>
                    Branchez votre caméra via USB pour l'associer à votre compte.
                  </div>
                </div>
                <button type="button" className={styles.skipBtn} onClick={skipCamera}>
                  Passer cette étape →
                </button>
              </div>
            )}

            {cameraState === 'detected' && (
              <div className={styles.cameraDetected}>
                <span className={styles.cameraIcon}>✓</span>
                <div>
                  <div className={styles.cameraDetectedText}>Caméra détectée</div>
                  <div className={styles.cameraSerial}>{cameraSerial}</div>
                </div>
                <button type="button" className={styles.removeBtn} onClick={removeCamera}>Retirer</button>
              </div>
            )}

            {cameraState === 'skipped' && (
              <div className={styles.cameraSkipped}>
                <span className={styles.cameraSkippedText}>Aucune caméra associée</span>
                <button type="button" className={styles.skipBtn} onClick={() => setCameraState('waiting')}>
                  ↺ Détecter
                </button>
              </div>
            )}
          </div>

          <div className={styles.divider} />

          {/* PIN */}
          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>
                PIN *
                <span className={styles.hint}>4 chiffres</span>
              </label>
              <input
                className={styles.input}
                type="password"
                inputMode="numeric"
                maxLength={4}
                value={form.pin}
                onChange={set('pin')}
                placeholder="••••"
                required
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Confirmer le PIN *</label>
              <input
                className={styles.input}
                type="password"
                inputMode="numeric"
                maxLength={4}
                value={form.pinConfirm}
                onChange={set('pinConfirm')}
                placeholder="••••"
                required
              />
            </div>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <button type="submit" className={styles.button} disabled={loading}>
            {loading ? 'Création…' : 'Créer mon compte'}
          </button>
        </form>
      </div>
    </div>
  )
}
