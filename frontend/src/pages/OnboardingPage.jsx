import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import styles from './OnboardingPage.module.css'

export default function OnboardingPage() {
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()

  // Liste des caméras détectées (en attente d'onboarding)
  const [cameras, setCameras] = useState([])
  // Serials sélectionnés par l'utilisateur
  const [selected, setSelected] = useState(new Set())

  const [form, setForm] = useState({
    first_name: '', last_name: '', afifly_name: '', email: '',
    pin: '', pinConfirm: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const pollRef = useRef(null)

  // Polling : mise à jour de la liste des caméras toutes les 2s
  useEffect(() => {
    async function fetchCameras() {
      try {
        const { data } = await api.get('/internal/onboarding/pending')
        setCameras(data.cameras ?? [])
      } catch { /* silencieux */ }
    }

    fetchCameras() // appel immédiat au montage
    pollRef.current = setInterval(fetchCameras, 2000)
    return () => clearInterval(pollRef.current)
  }, [])

  function toggleCamera(serial) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(serial) ? next.delete(serial) : next.add(serial)
      return next
    })
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
        first_name:     form.first_name,
        last_name:      form.last_name,
        afifly_name:    form.afifly_name || null,
        email:          form.email || null,
        pin:            form.pin,
        camera_serials: [...selected],
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

          {/* Section caméras */}
          <div className={styles.cameraSection}>
            <div className={styles.cameraHeader}>
              <span className={styles.cameraLabel}>Mes caméras</span>
              <span className={styles.cameraHint}>
                {selected.size > 0
                  ? `${selected.size} sélectionnée${selected.size > 1 ? 's' : ''}`
                  : 'Cliquez sur vos caméras pour les associer à votre compte'}
              </span>
            </div>

            {cameras.length === 0 ? (
              <div className={styles.cameraWaiting}>
                <span className={styles.pulse} />
                <div>
                  <div className={styles.cameraWaitingText}>En attente de connexion…</div>
                  <div className={styles.cameraWaitingHint}>
                    Branchez vos caméras USB. Elles apparaîtront ici automatiquement.
                  </div>
                </div>
              </div>
            ) : (
              <div className={styles.cameraList}>
                {cameras.map(cam => (
                  <CameraCard
                    key={cam.serial}
                    camera={cam}
                    selected={selected.has(cam.serial)}
                    onToggle={() => toggleCamera(cam.serial)}
                  />
                ))}
                {/* Indicateur "en attente d'autres caméras" */}
                <div className={styles.cameraMoreHint}>
                  <span className={styles.pulseSmall} />
                  <span>En attente d'autres caméras…</span>
                </div>
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

/* ─────────────────────────────────────────────────
   Carte caméra individuelle
───────────────────────────────────────────────── */
function CameraCard({ camera, selected, onToggle }) {
  const [elapsed, setElapsed] = useState(getElapsed(camera.connected_at))

  // Met à jour l'affichage "branché depuis X min" chaque minute
  useEffect(() => {
    const id = setInterval(() => setElapsed(getElapsed(camera.connected_at)), 30000)
    return () => clearInterval(id)
  }, [camera.connected_at])

  return (
    <button
      type="button"
      className={`${styles.cameraCard} ${selected ? styles.cameraCardSelected : ''}`}
      onClick={onToggle}
    >
      <div className={styles.cameraCardIcon}>
        {selected ? '✓' : '○'}
      </div>
      <div className={styles.cameraCardBody}>
        <div className={styles.cameraCardModel}>{camera.model_name}</div>
        <div className={styles.cameraCardSerial}>Série : {camera.serial}</div>
        <div className={styles.cameraCardTime}>{elapsed}</div>
      </div>
      <div className={styles.cameraCardLed} />
    </button>
  )
}

function getElapsed(isoDate) {
  if (!isoDate) return ''
  const diff = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000)
  if (diff < 60)  return 'Branché à l\'instant'
  if (diff < 120) return 'Branché depuis 1 minute'
  if (diff < 3600) return `Branché depuis ${Math.floor(diff / 60)} minutes`
  return `Branché depuis ${Math.floor(diff / 3600)}h`
}
