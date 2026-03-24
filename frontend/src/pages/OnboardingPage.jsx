import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import styles from './OnboardingPage.module.css'

export default function OnboardingPage() {
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const serialParam = searchParams.get('serial') || ''

  // Étape 0 : choix du parcours
  const [mode, setMode] = useState(null) // null | 'new' | 'existing'

  // ── Parcours "utilisateur existant" (email + mot de passe) ─────────────
  const [loginForm, setLoginForm]   = useState({ email: '', password: '' })
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  function setLoginField(field) {
    return e => setLoginForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function submitLogin(e) {
    e.preventDefault()
    setLoginError('')
    setLoginLoading(true)
    try {
      const { data } = await api.post('/auth/login', {
        email:    loginForm.email,
        password: loginForm.password,
      })
      const token = data.access_token
      if (serialParam) {
        await api.post(
          '/users/me/cameras/claim',
          { serial: serialParam },
          { headers: { Authorization: `Bearer ${token}` } },
        )
      }
      await loginWithToken(token)
      navigate('/kiosk', { replace: true })
    } catch (err) {
      setLoginError(err.response?.data?.detail ?? 'Email ou mot de passe incorrect.')
    } finally {
      setLoginLoading(false)
    }
  }

  // ── Parcours "nouveau compte" ────────────────────────────────────────────
  const [cameras, setCameras]   = useState([])
  const [selected, setSelected] = useState(() => serialParam ? new Set([serialParam]) : new Set())
  const [form, setForm]         = useState({
    first_name: '', last_name: '', afifly_name: '', email: '',
    password: '', passwordConfirm: '',
  })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)
  const pollRef = useRef(null)

  // Polling caméras en attente (uniquement sur le parcours "nouveau")
  useEffect(() => {
    if (mode !== 'new') return
    async function fetchCameras() {
      try {
        const { data } = await api.get('/internal/onboarding/pending')
        setCameras(data.cameras ?? [])
      } catch { /* silencieux */ }
    }
    fetchCameras()
    pollRef.current = setInterval(fetchCameras, 2000)
    return () => clearInterval(pollRef.current)
  }, [mode])

  function toggleCamera(serial) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(serial) ? next.delete(serial) : next.add(serial)
      return next
    })
  }

  function setField(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function submitNew(e) {
    e.preventDefault()
    setError('')
    if (form.password.length < 8) { setError('Le mot de passe doit contenir au moins 8 caractères.'); return }
    if (form.password !== form.passwordConfirm) { setError('Les deux mots de passe ne correspondent pas.'); return }
    clearInterval(pollRef.current)
    setLoading(true)
    try {
      const payload = {
        first_name:     form.first_name,
        last_name:      form.last_name,
        afifly_name:    form.afifly_name || null,
        email:          form.email || null,
        password:       form.password,
        camera_serials: [...selected],
      }
      const { data } = await api.post('/users/onboard', payload)
      await loginWithToken(data.access_token)
      navigate('/kiosk', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur lors de la création du compte.')
    } finally {
      setLoading(false)
    }
  }

  // ── Rendu : étape 0 — choix ──────────────────────────────────────────────
  if (mode === null) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.card}>
          <button className={styles.back} onClick={() => navigate('/kiosk')}>← Retour</button>
          <h1 className={styles.title}>Identification</h1>
          <p className={styles.subtitle}>
            {serialParam
              ? 'Cette caméra n\'est pas encore associée à un compte.'
              : 'Bienvenue — commençons par vérifier si vous avez déjà un compte.'}
          </p>
          <div className={styles.choiceGrid}>
            <button className={styles.choiceBtn} onClick={() => setMode('existing')}>
              <div className={styles.choiceBadge}>→</div>
              <div className={styles.choiceLabel}>J'ai déjà un compte</div>
              <div className={styles.choiceDesc}>Associer cette caméra à mon compte existant</div>
            </button>
            <button className={styles.choiceBtn} onClick={() => setMode('new')}>
              <div className={styles.choiceBadge}>+</div>
              <div className={styles.choiceLabel}>Créer mon compte</div>
              <div className={styles.choiceDesc}>Première utilisation du système</div>
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Rendu : parcours existant — email + mot de passe ───────────────────
  if (mode === 'existing') {
    return (
      <div className={styles.wrapper}>
        <div className={styles.card}>
          <button className={styles.back} onClick={() => setMode(null)}>← Retour</button>
          <h1 className={styles.title}>Connexion</h1>
          <p className={styles.subtitle}>
            Connectez-vous pour associer cette caméra à votre compte.
          </p>
          <form onSubmit={submitLogin} className={styles.form}>
            <div className={styles.field}>
              <label className={styles.label}>Email</label>
              <input
                className={styles.input}
                type="email"
                value={loginForm.email}
                onChange={setLoginField('email')}
                autoFocus
                required
                autoComplete="email"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Mot de passe</label>
              <input
                className={styles.input}
                type="password"
                value={loginForm.password}
                onChange={setLoginField('password')}
                required
                autoComplete="current-password"
              />
            </div>
            {loginError && <p className={styles.error}>{loginError}</p>}
            <button type="submit" className={styles.button} disabled={loginLoading}>
              {loginLoading ? 'Connexion…' : 'Se connecter et associer la caméra'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  // ── Rendu : parcours nouveau compte ─────────────────────────────────────
  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <button className={styles.back} onClick={() => setMode(null)}>← Retour</button>
        <h1 className={styles.title}>Créer mon compte</h1>

        <form onSubmit={submitNew} className={styles.form}>
          {/* Identité */}
          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Prénom *</label>
              <input className={styles.input} value={form.first_name} onChange={setField('first_name')} required />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Nom *</label>
              <input className={styles.input} value={form.last_name} onChange={setField('last_name')} required />
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
              onChange={setField('afifly_name')}
              placeholder="NOM Prénom"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Email *</label>
            <input className={styles.input} type="email" value={form.email} onChange={setField('email')} required autoComplete="email" />
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
                <div className={styles.cameraMoreHint}>
                  <span className={styles.pulseSmall} />
                  <span>En attente d'autres caméras…</span>
                </div>
              </div>
            )}
          </div>

          <div className={styles.divider} />

          {/* Mot de passe */}
          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>
                Mot de passe *
                <span className={styles.hint}>8 caractères minimum</span>
              </label>
              <input
                className={styles.input}
                type="password"
                value={form.password}
                onChange={setField('password')}
                autoComplete="new-password"
                required
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Confirmer *</label>
              <input
                className={styles.input}
                type="password"
                value={form.passwordConfirm}
                onChange={setField('passwordConfirm')}
                autoComplete="new-password"
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
   Carte caméra individuelle (parcours nouveau compte)
───────────────────────────────────────────────── */
function CameraCard({ camera, selected, onToggle }) {
  const [elapsed, setElapsed] = useState(getElapsed(camera.connected_at))

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
  if (diff < 60)   return 'Branché à l\'instant'
  if (diff < 120)  return 'Branché depuis 1 minute'
  if (diff < 3600) return `Branché depuis ${Math.floor(diff / 60)} minutes`
  return `Branché depuis ${Math.floor(diff / 3600)}h`
}
