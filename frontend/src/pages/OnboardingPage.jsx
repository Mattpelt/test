import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import styles from './OnboardingPage.module.css'

export default function OnboardingPage() {
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const detectedSerial = searchParams.get('serial') || ''

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    afifly_name: '',
    email: '',
    pin: '',
    pinConfirm: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Si l'utilisateur arrive sans serial (bouton "Je suis nouveau"),
  // s'assurer qu'il n'y a plus de pending onboarding orphelin
  useEffect(() => {
    if (!detectedSerial) {
      api.delete('/internal/onboarding/pending').catch(() => {})
    }
  }, [detectedSerial])

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

    setLoading(true)
    try {
      const payload = {
        first_name: form.first_name,
        last_name: form.last_name,
        afifly_name: form.afifly_name || null,
        email: form.email || null,
        pin: form.pin,
        camera_serial: detectedSerial || null,
      }
      const { data } = await api.post('/users/onboard', payload)
      await loginWithToken(data.access_token)
      navigate('/', { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail ?? 'Erreur lors de la création du compte.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <button className={styles.back} onClick={() => navigate('/login')}>
          ← Retour
        </button>

        <h1 className={styles.title}>Créer mon compte</h1>
        <p className={styles.subtitle}>
          {detectedSerial
            ? `Caméra détectée — serial : ${detectedSerial}`
            : 'Votre caméra pourra être associée plus tard par l\'administrateur.'}
        </p>

        <form onSubmit={submit} className={styles.form}>
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
              <label className={styles.label}>
                Confirmer le PIN *
              </label>
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
