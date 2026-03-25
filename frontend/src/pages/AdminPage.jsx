import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import styles from './AdminPage.module.css'

const TABS = ['Sautants', 'Rotations', 'Paramètres']

export default function AdminPage() {
  const { user, logout } = useAuth()
  const [tab, setTab] = useState('Sautants')

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.headerTitle}>SkyDive Media Hub — Admin</span>
        <div className={styles.headerRight}>
          <span className={styles.userName}>{user.first_name} {user.last_name}</span>
          <a href="/" className={styles.linkBtn}>Vue sautant</a>
          <button className={styles.logoutBtn} onClick={logout}>Déconnexion</button>
        </div>
      </header>

      <div className={styles.tabs}>
        {TABS.map(t => (
          <button
            key={t}
            className={`${styles.tab} ${tab === t ? styles.tabActive : ''}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <main className={styles.main}>
        {tab === 'Sautants'    && <UsersTab />}
        {tab === 'Rotations'   && <RotsTab />}
        {tab === 'Paramètres'  && <SettingsTab />}
      </main>
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Onglet Sautants
───────────────────────────────────────────────── */
function UsersTab() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/users')
      setUsers(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function deactivate(id, name) {
    if (!confirm(`Désactiver le compte de ${name} ?`)) return
    await api.delete(`/users/${id}`)
    load()
  }

  return (
    <div className={styles.tabContent}>
      <div className={styles.tabBar}>
        <h2 className={styles.tabTitle}>Sautants ({users.length})</h2>
        <button className={styles.primaryBtn} onClick={() => setShowForm(true)}>
          + Nouveau sautant
        </button>
      </div>

      {showForm && (
        <CreateUserForm onSuccess={() => { setShowForm(false); load() }} onCancel={() => setShowForm(false)} />
      )}

      {loading ? (
        <p className={styles.info}>Chargement…</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Email</th>
              <th>Nom Afifly</th>
              <th>Caméras</th>
              <th>Rôle</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.first_name} {u.last_name}</td>
                <td className={styles.muted}>{u.email}</td>
                <td className={styles.muted}>{u.afifly_name ?? '—'}</td>
                <td className={styles.muted}>{u.camera_serials.join(', ') || '—'}</td>
                <td>
                  <span className={u.is_admin ? styles.badgeAdmin : styles.badgeUser}>
                    {u.is_admin ? 'Admin' : 'Sautant'}
                  </span>
                </td>
                <td>
                  <button
                    className={styles.dangerBtn}
                    onClick={() => deactivate(u.id, `${u.first_name} ${u.last_name}`)}
                  >
                    Désactiver
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function CreateUserForm({ onSuccess, onCancel }) {
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', afifly_name: '',
    pin: '', pin_confirm: '', is_admin: false,
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    const pinLen = form.is_admin ? 6 : 4
    if (!/^\d+$/.test(form.pin) || form.pin.length !== pinLen) {
      setError(`Le PIN doit contenir exactement ${pinLen} chiffres.`)
      return
    }
    if (form.pin !== form.pin_confirm) {
      setError('Les deux PIN ne correspondent pas.')
      return
    }
    setLoading(true)
    try {
      await api.post('/users', {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email || null,
        afifly_name: form.afifly_name || null,
        pin: form.pin,
        is_admin: form.is_admin,
      })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur lors de la création.')
    } finally {
      setLoading(false)
    }
  }

  const pinLen = form.is_admin ? 6 : 4

  return (
    <form className={styles.inlineForm} onSubmit={submit}>
      <h3 className={styles.formTitle}>Nouveau sautant</h3>
      <div className={styles.formGrid}>
        <input className={styles.input} placeholder="Prénom *" value={form.first_name} onChange={set('first_name')} required />
        <input className={styles.input} placeholder="Nom *" value={form.last_name} onChange={set('last_name')} required />
        <input className={styles.input} placeholder="Email (optionnel)" type="email" value={form.email} onChange={set('email')} />
        <input className={styles.input} placeholder="Nom Afifly *" value={form.afifly_name} onChange={set('afifly_name')} required />
        <input
          className={styles.input}
          placeholder={`PIN * (${pinLen} chiffres)`}
          type="password"
          inputMode="numeric"
          maxLength={pinLen}
          value={form.pin}
          onChange={set('pin')}
          required
        />
        <input
          className={styles.input}
          placeholder="Confirmer PIN *"
          type="password"
          inputMode="numeric"
          maxLength={pinLen}
          value={form.pin_confirm}
          onChange={set('pin_confirm')}
          required
        />
        <label className={styles.checkLabel}>
          <input type="checkbox" checked={form.is_admin} onChange={set('is_admin')} />
          Administrateur (PIN 6 chiffres)
        </label>
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.formActions}>
        <button type="submit" className={styles.primaryBtn} disabled={loading}>
          {loading ? 'Création…' : 'Créer'}
        </button>
        <button type="button" className={styles.secondaryBtn} onClick={onCancel}>Annuler</button>
      </div>
    </form>
  )
}

/* ─────────────────────────────────────────────────
   Onglet Rotations
───────────────────────────────────────────────── */
function RotsTab() {
  const [rots, setRots] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/rots').then(({ data }) => setRots(data)).finally(() => setLoading(false))
  }, [])

  function formatDate(d) {
    return new Date(d + 'T00:00:00').toLocaleDateString('fr-FR')
  }

  return (
    <div className={styles.tabContent}>
      <div className={styles.tabBar}>
        <h2 className={styles.tabTitle}>Rotations ({rots.length})</h2>
      </div>

      {loading ? (
        <p className={styles.info}>Chargement…</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>N°</th>
              <th>Date</th>
              <th>Heure</th>
              <th>Avion</th>
              <th>Pilote</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {rots.map(rot => (
              <tr key={rot.id}>
                <td>#{rot.rot_number}</td>
                <td>{formatDate(rot.rot_date)}</td>
                <td>{rot.rot_time?.slice(0, 5)}</td>
                <td className={styles.muted}>{rot.plane_registration ?? '—'}</td>
                <td className={styles.muted}>{rot.pilot ?? '—'}</td>
                <td>
                  <span className={rot.parse_status === 'OK' ? styles.badgeOk : styles.badgeErr}>
                    {rot.parse_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Section Logo
───────────────────────────────────────────────── */
function LogoSection() {
  const [hasLogo, setHasLogo] = useState(false)
  const [logoKey, setLogoKey] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [msg, setMsg] = useState('')
  const fileRef = useRef(null)

  async function handleFile(e) {
    const file = e.target.files[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    setUploading(true)
    setMsg('')
    try {
      await api.post('/settings/logo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setLogoKey(k => k + 1)
      setHasLogo(true)
      setMsg('Logo mis à jour.')
    } catch {
      setMsg('Erreur lors de l\'upload.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function handleDelete() {
    try {
      await api.delete('/settings/logo')
      setHasLogo(false)
      setMsg('Logo supprimé.')
    } catch {
      setMsg('Erreur lors de la suppression.')
    }
  }

  return (
    <div className={styles.logoSection}>
      <h3 className={styles.sectionTitle}>Logo du centre</h3>
      <div className={styles.logoRow}>
        <div className={styles.logoPreview}>
          {hasLogo
            ? <img key={logoKey} src={`/api/settings/logo?t=${logoKey}`} alt="Logo" className={styles.logoImg} onError={() => setHasLogo(false)} />
            : <span className={styles.logoPlaceholder}>Aucun logo</span>
          }
          <img key={`probe-${logoKey}`} src="/api/settings/logo" alt="" style={{ display: 'none' }} onLoad={() => setHasLogo(true)} onError={() => setHasLogo(false)} />
        </div>
        <div className={styles.logoActions}>
          <input type="file" ref={fileRef} accept="image/png,image/jpeg,image/webp" onChange={handleFile} style={{ display: 'none' }} />
          <button className={styles.primaryBtn} onClick={() => fileRef.current.click()} disabled={uploading}>
            {uploading ? 'Upload…' : hasLogo ? 'Remplacer' : 'Choisir un logo'}
          </button>
          {hasLogo && (
            <button className={styles.dangerBtn} onClick={handleDelete}>Supprimer</button>
          )}
          <p className={styles.logoHint}>PNG, JPEG ou WebP. La hauteur s'adapte automatiquement au header.</p>
          {msg && <p className={msg.includes('Erreur') ? styles.error : styles.success}>{msg}</p>}
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Onglet Paramètres
───────────────────────────────────────────────── */
function SettingsTab() {
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/settings').then(({ data }) => setSettings(data)).finally(() => setLoading(false))
  }, [])

  function set(field) {
    return e => setSettings(s => ({ ...s, [field]: Number(e.target.value) }))
  }

  function setText(field) {
    return e => setSettings(s => ({ ...s, [field]: e.target.value }))
  }

  function setToggle(field) {
    return e => setSettings(s => ({ ...s, [field]: e.target.checked }))
  }

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      const { data } = await api.patch('/settings', settings)
      setSettings(data)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError('Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className={styles.info}>Chargement…</p>

  return (
    <div className={styles.tabContent}>
      <div className={styles.tabBar}>
        <h2 className={styles.tabTitle}>Paramètres</h2>
      </div>

      <LogoSection />

      <form className={styles.settingsForm} onSubmit={save}>
        <SettingField
          label="Rétention des vidéos"
          hint="Durée de conservation des vidéos après ingestion."
          value={settings.retention_days}
          unit="jours"
          onChange={set('retention_days')}
        />
        <SettingField
          label="Fenêtre de matching"
          hint="Écart max entre l'horodatage vidéo et l'heure du rot pour un matching automatique."
          value={settings.matching_window_minutes}
          unit="minutes"
          onChange={set('matching_window_minutes')}
        />
        <SettingField
          label="Delta cible saut"
          hint="Décalage horaire habituel entre le décollage et le saut."
          value={settings.jump_target_delta_min}
          unit="minutes"
          onChange={set('jump_target_delta_min')}
        />
        <SettingField
          label="Fenêtre de saut"
          hint="Plage de temps autour du delta cible pour la détection du saut."
          value={settings.jump_window_hours}
          unit="heures"
          onChange={set('jump_window_hours')}
        />

        <hr className={styles.divider} />
        <h3 className={styles.sectionTitle}>Notifications email</h3>

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>Activer les notifications</div>
            <div className={styles.settingHint}>Envoie un email au sautant quand ses vidéos sont prêtes.</div>
          </div>
          <label className={styles.toggle}>
            <input type="checkbox" checked={!!settings.notifications_enabled} onChange={setToggle('notifications_enabled')} />
            <span className={styles.toggleSlider} />
          </label>
        </div>

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>URL de l'application</div>
            <div className={styles.settingHint}>Lien inclus dans l'email (ex: http://192.168.1.39).</div>
          </div>
          <input className={styles.textInput} value={settings.app_url ?? ''} onChange={setText('app_url')} placeholder="http://192.168.1.39" />
        </div>

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>Serveur SMTP</div>
            <div className={styles.settingHint}>Hôte du serveur d'envoi (ex: smtp.gmail.com).</div>
          </div>
          <input className={styles.textInput} value={settings.smtp_host ?? ''} onChange={setText('smtp_host')} placeholder="smtp.gmail.com" />
        </div>

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>Port SMTP</div>
            <div className={styles.settingHint}>587 (STARTTLS) recommandé.</div>
          </div>
          <div className={styles.settingInput}>
            <input type="number" className={styles.numInput} value={settings.smtp_port ?? 587} onChange={set('smtp_port')} />
          </div>
        </div>

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>Utilisateur SMTP</div>
            <div className={styles.settingHint}>Adresse email utilisée pour l'authentification.</div>
          </div>
          <input className={styles.textInput} value={settings.smtp_user ?? ''} onChange={setText('smtp_user')} placeholder="expediteur@gmail.com" />
        </div>

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>Mot de passe SMTP</div>
            <div className={styles.settingHint}>Laissez vide pour ne pas modifier le mot de passe enregistré.</div>
          </div>
          <input className={styles.textInput} type="password" value={settings.smtp_password ?? ''} onChange={setText('smtp_password')} placeholder="••••••••••••••••" />
        </div>

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>Adresse expéditeur</div>
            <div className={styles.settingHint}>Adresse affichée dans le champ "De" de l'email.</div>
          </div>
          <input className={styles.textInput} value={settings.smtp_from ?? ''} onChange={setText('smtp_from')} placeholder="noreply@skydive.fr" />
        </div>

        {error  && <p className={styles.error}>{error}</p>}
        {saved  && <p className={styles.success}>Paramètres sauvegardés.</p>}

        <button type="submit" className={styles.primaryBtn} disabled={saving}>
          {saving ? 'Sauvegarde…' : 'Sauvegarder'}
        </button>
      </form>
    </div>
  )
}

function SettingField({ label, hint, value, unit, onChange }) {
  return (
    <div className={styles.settingRow}>
      <div>
        <div className={styles.settingLabel}>{label}</div>
        <div className={styles.settingHint}>{hint}</div>
      </div>
      <div className={styles.settingInput}>
        <input
          type="number"
          min={1}
          value={value}
          onChange={onChange}
          className={styles.numInput}
        />
        <span className={styles.unit}>{unit}</span>
      </div>
    </div>
  )
}
