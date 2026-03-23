import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import styles from '../pages/HomePage.module.css'
import pStyles from './ProfileTab.module.css'
import ConfirmModal from './ConfirmModal'

export default function ProfileTab() {
  const { user, setUser } = useAuth()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  async function reload() {
    try {
      const { data } = await api.get('/users/me')
      setProfile(data)
      setUser(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, [])

  if (loading) return <p className={styles.info}>Chargement…</p>

  return (
    <div className={pStyles.page}>
      <ProfileForm profile={profile} onSaved={reload} />
      <CameraManager profile={profile} onChanged={reload} />
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Formulaire profil
───────────────────────────────────────────────── */
function ProfileForm({ profile, onSaved }) {
  const [form, setForm] = useState({
    first_name:            profile.first_name,
    last_name:             profile.last_name,
    email:                 profile.email ?? '',
    afifly_name:           profile.afifly_name ?? '',
    pin:                   '',
    pinConfirm:            '',
    notifications_enabled: profile.notifications_enabled ?? true,
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)
  const [error, setError]   = useState('')

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function submit(e) {
    e.preventDefault()
    setError(''); setSaved(false)

    if (form.pin) {
      const pinLen = profile.is_admin ? 6 : 4
      if (!/^\d+$/.test(form.pin) || form.pin.length !== pinLen) {
        setError(`Le nouveau PIN doit contenir exactement ${pinLen} chiffres.`)
        return
      }
      if (form.pin !== form.pinConfirm) {
        setError('Les deux PIN ne correspondent pas.')
        return
      }
    }

    setSaving(true)
    try {
      const payload = {
        first_name:            form.first_name  || undefined,
        last_name:             form.last_name   || undefined,
        email:                 form.email       || null,
        afifly_name:           form.afifly_name || null,
        notifications_enabled: form.notifications_enabled,
      }
      if (form.pin) payload.pin = form.pin
      await api.patch('/users/me', payload)
      setSaved(true)
      setForm(f => ({ ...f, pin: '', pinConfirm: '' }))
      setTimeout(() => setSaved(false), 3000)
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  const pinLen = profile.is_admin ? 6 : 4

  return (
    <section className={pStyles.card}>
      <h2 className={pStyles.cardTitle}>Informations personnelles</h2>
      <form onSubmit={submit} className={pStyles.form}>
        <div className={pStyles.grid2}>
          <div className={pStyles.field}>
            <label className={pStyles.label}>Prénom</label>
            <input className={pStyles.input} value={form.first_name} onChange={set('first_name')} required />
          </div>
          <div className={pStyles.field}>
            <label className={pStyles.label}>Nom</label>
            <input className={pStyles.input} value={form.last_name} onChange={set('last_name')} required />
          </div>
        </div>

        <div className={pStyles.field}>
          <label className={pStyles.label}>
            Nom Afifly
            <span className={pStyles.hint}>Tel qu'il apparaît sur les feuilles de rotation</span>
          </label>
          <input className={pStyles.input} value={form.afifly_name} onChange={set('afifly_name')} placeholder="NOM Prénom" />
        </div>

        <div className={pStyles.field}>
          <label className={pStyles.label}>Email <span className={pStyles.optional}>(optionnel)</span></label>
          <input className={pStyles.input} type="email" value={form.email} onChange={set('email')} placeholder="votre@email.fr" />
        </div>

        <div className={pStyles.divider} />
        <div className={pStyles.sectionLabel}>Changer le PIN <span className={pStyles.optional}>(laisser vide pour conserver l'actuel)</span></div>

        <div className={pStyles.grid2}>
          <div className={pStyles.field}>
            <label className={pStyles.label}>Nouveau PIN <span className={pStyles.hint}>{pinLen} chiffres</span></label>
            <input
              className={pStyles.input}
              type="password"
              inputMode="numeric"
              maxLength={pinLen}
              value={form.pin}
              onChange={set('pin')}
              placeholder={'•'.repeat(pinLen)}
              autoComplete="new-password"
            />
          </div>
          <div className={pStyles.field}>
            <label className={pStyles.label}>Confirmer le PIN</label>
            <input
              className={pStyles.input}
              type="password"
              inputMode="numeric"
              maxLength={pinLen}
              value={form.pinConfirm}
              onChange={set('pinConfirm')}
              placeholder={'•'.repeat(pinLen)}
              autoComplete="new-password"
            />
          </div>
        </div>

        <div className={pStyles.divider} />

        <div className={pStyles.notifRow}>
          <div className={pStyles.notifLabel}>
            <span className={pStyles.notifTitle}>Notifications email</span>
            <span className={pStyles.notifHint}>Recevoir un email quand vos vidéos sont prêtes</span>
          </div>
          <label className={pStyles.toggle}>
            <input
              type="checkbox"
              checked={form.notifications_enabled}
              onChange={e => setForm(f => ({ ...f, notifications_enabled: e.target.checked }))}
            />
            <span className={pStyles.toggleSlider} />
          </label>
        </div>

        {error && <p className={pStyles.error}>{error}</p>}
        {saved && <p className={pStyles.success}>Modifications enregistrées.</p>}

        <button type="submit" className={pStyles.primaryBtn} disabled={saving}>
          {saving ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </form>
    </section>
  )
}

/* ─────────────────────────────────────────────────
   Gestion des caméras
───────────────────────────────────────────────── */
function CameraManager({ profile, onChanged }) {
  const [myCameras, setMyCameras]           = useState([]) // [{serial, make, model}]
  const [pendingCameras, setPendingCameras] = useState([])
  const [manualSerial, setManualSerial]     = useState('')
  const [error, setError]                   = useState('')
  const [claiming, setClaiming]             = useState(null) // serial en cours
  const [confirmDialog, setConfirmDialog]   = useState(null)
  const pollRef = useRef(null)

  // Charger les caméras enrichies
  async function loadMyCameras() {
    try {
      const { data } = await api.get('/users/me/cameras')
      setMyCameras(data)
    } catch { /* silencieux */ }
  }

  useEffect(() => { loadMyCameras() }, [profile.camera_serials])

  // Polling des caméras détectées
  useEffect(() => {
    async function fetchPending() {
      try {
        const { data } = await api.get('/internal/onboarding/pending')
        // Exclure les caméras déjà associées au profil
        const mine = new Set(profile.camera_serials)
        setPendingCameras((data.cameras ?? []).filter(c => !mine.has(c.serial)))
      } catch { /* silencieux */ }
    }
    fetchPending()
    pollRef.current = setInterval(fetchPending, 2000)
    return () => clearInterval(pollRef.current)
  }, [profile.camera_serials])

  async function claim(serial) {
    setError('')
    setClaiming(serial)
    try {
      await api.post('/users/me/cameras/claim', { serial })
      onChanged()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur.')
    } finally {
      setClaiming(null)
    }
  }

  async function addManual() {
    const serial = manualSerial.trim()
    if (!serial) return
    setError('')
    setClaiming('manual')
    try {
      await api.post('/users/me/cameras/claim', { serial, manual: true })
      setManualSerial('')
      onChanged()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur.')
    } finally {
      setClaiming(null)
    }
  }

  function remove(serial) {
    setConfirmDialog({
      serial,
      onConfirm: async () => {
        setConfirmDialog(null)
        setError('')
        try {
          await api.delete(`/users/me/cameras/${encodeURIComponent(serial)}`)
          onChanged()
        } catch (err) {
          setError(err.response?.data?.detail ?? 'Erreur.')
        }
      },
    })
  }

  return (
    <section className={pStyles.card}>
      {confirmDialog && (
        <ConfirmModal
          title="Retirer la caméra"
          message={`Retirer la caméra ${confirmDialog.serial} de votre compte ?`}
          confirmLabel="Retirer"
          onConfirm={confirmDialog.onConfirm}
          onCancel={() => setConfirmDialog(null)}
        />
      )}
      <h2 className={pStyles.cardTitle}>Mes caméras</h2>

      {/* Caméras associées */}
      {profile.camera_serials.length === 0 ? (
        <p className={pStyles.empty}>Aucune caméra associée à votre compte.</p>
      ) : (
        <ul className={pStyles.cameraList}>
          {myCameras.length > 0
            ? myCameras.map(cam => (
                <li key={cam.serial} className={pStyles.cameraItem}>
                  <span className={pStyles.cameraInfo}>
                    {cam.make || cam.model
                      ? <span className={pStyles.cameraModel}>{[cam.make, cam.model].filter(Boolean).join(' ')}</span>
                      : null}
                    <span className={pStyles.cameraSerial}>{cam.serial}</span>
                  </span>
                  <button className={pStyles.removeBtn} onClick={() => remove(cam.serial)}>Retirer</button>
                </li>
              ))
            : profile.camera_serials.map(serial => (
                <li key={serial} className={pStyles.cameraItem}>
                  <span className={pStyles.cameraInfo}>
                    <span className={pStyles.cameraSerial}>{serial}</span>
                  </span>
                  <button className={pStyles.removeBtn} onClick={() => remove(serial)}>Retirer</button>
                </li>
              ))
          }
        </ul>
      )}

      {error && <p className={pStyles.error}>{error}</p>}

      <div className={pStyles.divider} />
      <div className={pStyles.sectionLabel}>Ajouter une caméra</div>

      {/* Caméras détectées (non encore associées) */}
      {pendingCameras.length > 0 && (
        <div className={pStyles.detected}>
          <div className={pStyles.detectedLabel}>Caméras détectées — cliquez pour associer</div>
          {pendingCameras.map(cam => (
            <button
              key={cam.serial}
              className={pStyles.pendingCard}
              onClick={() => claim(cam.serial)}
              disabled={claiming === cam.serial}
            >
              <div className={pStyles.pendingLed} />
              <div className={pStyles.pendingBody}>
                <div className={pStyles.pendingModel}>{cam.model_name}</div>
                <div className={pStyles.pendingSerial}>{cam.serial}</div>
                <div className={pStyles.pendingTime}>{getElapsed(cam.connected_at)}</div>
              </div>
              <span className={pStyles.pendingAction}>
                {claiming === cam.serial ? '…' : 'Associer →'}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Saisie manuelle */}
      <div className={pStyles.manualRow}>
        <div className={pStyles.manualPulse}>
          <span className={pStyles.pulseSmall} />
          <span className={pStyles.manualHint}>En attente de connexion USB…</span>
        </div>
        <div className={pStyles.manualInput}>
          <input
            className={pStyles.input}
            placeholder="Saisir un serial manuellement"
            value={manualSerial}
            onChange={e => setManualSerial(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addManual())}
          />
          <button
            className={pStyles.addBtn}
            onClick={addManual}
            disabled={!manualSerial.trim() || claiming === 'manual'}
            type="button"
          >
            {claiming === 'manual' ? '…' : 'Ajouter'}
          </button>
        </div>
      </div>
    </section>
  )
}

function getElapsed(isoDate) {
  if (!isoDate) return ''
  const diff = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000)
  if (diff < 60)   return 'Branché à l\'instant'
  if (diff < 120)  return 'Branché depuis 1 minute'
  if (diff < 3600) return `Branché depuis ${Math.floor(diff / 60)} min`
  return `Branché depuis ${Math.floor(diff / 3600)}h`
}
