import { useEffect, useState } from 'react'
import { api } from '../api/client'
import styles from '../pages/HomePage.module.css'

const SUB_TABS = ['Utilisateurs', 'Rotations', 'Vidéos']

export default function GestionTab() {
  const [sub, setSub] = useState('Utilisateurs')

  return (
    <div className={styles.tabContent}>
      <div className={styles.subTabs}>
        {SUB_TABS.map(t => (
          <button
            key={t}
            className={`${styles.subTab} ${sub === t ? styles.subTabActive : ''}`}
            onClick={() => setSub(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {sub === 'Utilisateurs' && <UsersSubTab />}
      {sub === 'Rotations'    && <RotsSubTab />}
      {sub === 'Vidéos'       && <VideosSubTab />}
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Sous-onglet Utilisateurs
───────────────────────────────────────────────── */
function UsersSubTab() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editUser, setEditUser] = useState(null)

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

  async function reactivate(id) {
    await api.patch(`/users/${id}`, { is_active: true })
    load()
  }

  async function hardDelete(id, name) {
    const confirmed = confirm(
      `⚠️ SUPPRESSION DÉFINITIVE\n\n` +
      `Supprimer le compte de ${name} ainsi que TOUTES ses vidéos ?\n\n` +
      `Cette action est irréversible.`
    )
    if (!confirmed) return
    await api.delete(`/users/${id}/hard`)
    load()
  }

  return (
    <div>
      <div className={styles.tabBar}>
        <h2 className={styles.tabTitle}>Utilisateurs ({users.length})</h2>
        <button className={styles.primaryBtn} onClick={() => setShowCreate(true)}>+ Nouveau</button>
      </div>

      {showCreate && (
        <UserForm
          onSuccess={() => { setShowCreate(false); load() }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {editUser && (
        <UserForm
          user={editUser}
          onSuccess={() => { setEditUser(null); load() }}
          onCancel={() => setEditUser(null)}
        />
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
              <th>Statut</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.first_name} {u.last_name}</td>
                <td className={styles.muted}>{u.email ?? '—'}</td>
                <td className={styles.muted}>{u.afifly_name ?? '—'}</td>
                <td className={styles.muted}>{u.camera_serials.join(', ') || '—'}</td>
                <td>
                  <span className={u.is_admin ? styles.badgeAdmin : styles.badgeUser}>
                    {u.is_admin ? 'Admin' : 'Sautant'}
                  </span>
                </td>
                <td>
                  <span className={u.is_active ? styles.badgeOk : styles.badgeErr}>
                    {u.is_active ? 'Actif' : 'Inactif'}
                  </span>
                </td>
                <td className={styles.actions}>
                  <button className={styles.editBtn} onClick={() => setEditUser(u)}>Modifier</button>
                  {u.is_active
                    ? <button className={styles.dangerBtn} onClick={() => deactivate(u.id, `${u.first_name} ${u.last_name}`)}>Désactiver</button>
                    : <button className={styles.secondaryBtn} onClick={() => reactivate(u.id)}>Réactiver</button>
                  }
                  <button className={styles.hardDeleteBtn} onClick={() => hardDelete(u.id, `${u.first_name} ${u.last_name}`)}>Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function UserForm({ user, onSuccess, onCancel }) {
  const isEdit = !!user
  const [form, setForm] = useState({
    first_name:     user?.first_name ?? '',
    last_name:      user?.last_name ?? '',
    email:          user?.email ?? '',
    afifly_name:    user?.afifly_name ?? '',
    camera_serials: user?.camera_serials?.join(', ') ?? '',
    pin:            '',
    pin_confirm:    '',
    is_admin:       user?.is_admin ?? false,
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))
  }

  async function submit(e) {
    e.preventDefault()
    setError('')

    if (!isEdit || form.pin) {
      const pinLen = form.is_admin ? 6 : 4
      if (!/^\d+$/.test(form.pin) || form.pin.length !== pinLen) {
        setError(`Le PIN doit contenir exactement ${pinLen} chiffres.`)
        return
      }
      if (form.pin !== form.pin_confirm) {
        setError('Les deux PIN ne correspondent pas.')
        return
      }
    }

    const payload = {
      first_name:     form.first_name,
      last_name:      form.last_name,
      email:          form.email || null,
      afifly_name:    form.afifly_name || null,
      camera_serials: form.camera_serials ? form.camera_serials.split(',').map(s => s.trim()).filter(Boolean) : [],
      is_admin:       form.is_admin,
    }
    if (form.pin) payload.pin = form.pin

    setLoading(true)
    try {
      if (isEdit) {
        await api.patch(`/users/${user.id}`, payload)
      } else {
        if (!form.pin) { setError('Le PIN est obligatoire.'); return }
        await api.post('/users', { ...payload, pin: form.pin })
      }
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur.')
    } finally {
      setLoading(false)
    }
  }

  const pinLen = form.is_admin ? 6 : 4

  return (
    <form className={styles.inlineForm} onSubmit={submit}>
      <h3 className={styles.formTitle}>{isEdit ? 'Modifier le compte' : 'Nouveau compte'}</h3>
      <div className={styles.formGrid}>
        <input className={styles.input} placeholder="Prénom *" value={form.first_name} onChange={set('first_name')} required />
        <input className={styles.input} placeholder="Nom *" value={form.last_name} onChange={set('last_name')} required />
        <input className={styles.input} placeholder="Email" type="email" value={form.email} onChange={set('email')} />
        <input className={styles.input} placeholder="Nom Afifly" value={form.afifly_name} onChange={set('afifly_name')} />
        <input className={styles.input} placeholder="Caméras (serials séparés par virgule)" value={form.camera_serials} onChange={set('camera_serials')} />
        <input
          className={styles.input}
          placeholder={isEdit ? `Nouveau PIN (${pinLen} chiffres, laisser vide pour ne pas changer)` : `PIN * (${pinLen} chiffres)`}
          type="password"
          inputMode="numeric"
          maxLength={pinLen}
          value={form.pin}
          onChange={set('pin')}
          required={!isEdit}
        />
        <input
          className={styles.input}
          placeholder="Confirmer PIN"
          type="password"
          inputMode="numeric"
          maxLength={pinLen}
          value={form.pin_confirm}
          onChange={set('pin_confirm')}
          required={!isEdit}
        />
        <label className={styles.checkLabel}>
          <input type="checkbox" checked={form.is_admin} onChange={set('is_admin')} />
          Administrateur (PIN 6 chiffres)
        </label>
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.formActions}>
        <button type="submit" className={styles.primaryBtn} disabled={loading}>
          {loading ? '…' : (isEdit ? 'Enregistrer' : 'Créer')}
        </button>
        <button type="button" className={styles.secondaryBtn} onClick={onCancel}>Annuler</button>
      </div>
    </form>
  )
}

/* ─────────────────────────────────────────────────
   Sous-onglet Rotations
───────────────────────────────────────────────── */
function RotsSubTab() {
  const [rots, setRots] = useState([])
  const [loading, setLoading] = useState(true)
  const [editRot, setEditRot] = useState(null)
  const [showAdd, setShowAdd] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/rots')
      setRots(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function deleteRot(id, num) {
    if (!confirm(`Supprimer la rotation n°${num} ? Les vidéos associées seront déliées.`)) return
    await api.delete(`/rots/${id}`)
    load()
  }

  function formatDate(d) {
    return new Date(d + 'T00:00:00').toLocaleDateString('fr-FR')
  }

  return (
    <div>
      <div className={styles.tabBar}>
        <h2 className={styles.tabTitle}>Rotations ({rots.length})</h2>
        <button className={styles.primaryBtn} onClick={() => setShowAdd(true)}>+ Ajouter une rotation</button>
      </div>

      {showAdd && (
        <AddRotModal
          onSuccess={() => { setShowAdd(false); load() }}
          onCancel={() => setShowAdd(false)}
        />
      )}

      {editRot && (
        <RotForm
          rot={editRot}
          onSuccess={() => { setEditRot(null); load() }}
          onCancel={() => setEditRot(null)}
        />
      )}

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
              <th></th>
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
                <td className={styles.actions}>
                  <button className={styles.editBtn} onClick={() => setEditRot(rot)}>Modifier</button>
                  <button className={styles.dangerBtn} onClick={() => deleteRot(rot.id, rot.rot_number)}>Supprimer</button>
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
   Modale Ajouter une rotation (PDF ou JSON)
───────────────────────────────────────────────── */
function AddRotModal({ onSuccess, onCancel }) {
  const [mode, setMode] = useState('pdf') // 'pdf' | 'json'

  return (
    <div className={styles.modalOverlay} onClick={e => e.target === e.currentTarget && onCancel()}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h3 className={styles.modalTitle}>Ajouter une rotation</h3>
          <button className={styles.modalClose} onClick={onCancel}>✕</button>
        </div>

        <div className={styles.modeTabs}>
          <button
            className={`${styles.modeTab} ${mode === 'pdf' ? styles.modeTabActive : ''}`}
            onClick={() => setMode('pdf')}
          >
            PDF Afifly
          </button>
          <button
            className={`${styles.modeTab} ${mode === 'json' ? styles.modeTabActive : ''}`}
            onClick={() => setMode('json')}
          >
            Saisie manuelle
          </button>
        </div>

        {mode === 'pdf'  && <PdfImportForm  onSuccess={onSuccess} onCancel={onCancel} />}
        {mode === 'json' && <JsonImportForm onSuccess={onSuccess} onCancel={onCancel} />}
      </div>
    </div>
  )
}

function PdfImportForm({ onSuccess, onCancel }) {
  const [file, setFile]       = useState(null)
  const [preview, setPreview] = useState(null) // données parsées
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  async function handlePreview() {
    if (!file) return
    setError(''); setLoading(true); setPreview(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await api.post('/rots/parse-preview', fd)
      setPreview(data)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur de parsing.')
    } finally {
      setLoading(false)
    }
  }

  async function handleImport() {
    if (!file) return
    setError(''); setLoading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      await api.post('/rots', fd)
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur lors de l\'import.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.modalBody}>
      <p className={styles.modeHint}>
        Importez la feuille de rotation Afifly au format PDF.
        Utilisez "Aperçu" pour vérifier les données avant de valider.
      </p>

      <label className={styles.fileZone}>
        <input
          type="file"
          accept=".pdf"
          className={styles.fileInput}
          onChange={e => { setFile(e.target.files[0]); setPreview(null); setError('') }}
        />
        {file
          ? <span className={styles.fileName}>📄 {file.name}</span>
          : <span className={styles.filePlaceholder}>Cliquez ou déposez un PDF ici</span>
        }
      </label>

      {error && <p className={styles.error}>{error}</p>}

      {preview && (
        <div className={styles.preview}>
          <div className={styles.previewRow}>
            <span className={styles.previewLabel}>Rotation</span>
            <span>n°{preview.rot_number} — {preview.rot_date} à {preview.rot_time?.slice(0,5)}</span>
          </div>
          {preview.plane_registration && (
            <div className={styles.previewRow}>
              <span className={styles.previewLabel}>Avion</span>
              <span>{preview.plane_registration}</span>
            </div>
          )}
          {preview.pilot && (
            <div className={styles.previewRow}>
              <span className={styles.previewLabel}>Pilote</span>
              <span>{preview.pilot}</span>
            </div>
          )}
          <div className={styles.previewRow}>
            <span className={styles.previewLabel}>Participants</span>
            <span>{preview.participants?.length ?? 0}</span>
          </div>
          {preview.participants?.length > 0 && (
            <ul className={styles.previewList}>
              {preview.participants.map((p, i) => (
                <li key={i} className={styles.previewItem}>
                  <span className={styles.previewGroup}>G{p.group_id}</span>
                  {p.afifly_name}
                  {p.level && <span className={styles.previewLevel}>{p.level}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className={styles.formActions}>
        {preview
          ? <button className={styles.primaryBtn} onClick={handleImport} disabled={loading}>
              {loading ? 'Import…' : 'Confirmer l\'import'}
            </button>
          : <button className={styles.primaryBtn} onClick={handlePreview} disabled={!file || loading}>
              {loading ? 'Analyse…' : 'Aperçu'}
            </button>
        }
        {preview && (
          <button className={styles.secondaryBtn} onClick={() => setPreview(null)} disabled={loading}>
            Rechoisir
          </button>
        )}
        <button className={styles.secondaryBtn} onClick={onCancel} disabled={loading}>Annuler</button>
      </div>
    </div>
  )
}

function JsonImportForm({ onSuccess, onCancel }) {
  const today = new Date().toISOString().slice(0, 10)
  const [form, setForm] = useState({
    rot_number: '',
    rot_date: today,
    rot_time: '09:00',
    plane_registration: '',
    pilot: '',
    chef_avion: '',
  })
  const [participants, setParticipants] = useState([
    { afifly_name: '', level: '', group_id: 1 },
  ])
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  function setF(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  function setP(i, field) {
    return e => setParticipants(ps => ps.map((p, j) => j === i ? { ...p, [field]: e.target.value } : p))
  }

  function addParticipant() {
    setParticipants(ps => [...ps, { afifly_name: '', level: '', group_id: ps.length > 0 ? ps[ps.length-1].group_id : 1 }])
  }

  function removeParticipant(i) {
    setParticipants(ps => ps.filter((_, j) => j !== i))
  }

  async function submit(e) {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      await api.post('/rots/json', {
        rot_number:         Number(form.rot_number),
        rot_date:           form.rot_date,
        rot_time:           form.rot_time,
        plane_registration: form.plane_registration || null,
        pilot:              form.pilot || null,
        chef_avion:         form.chef_avion || null,
        participants: participants
          .filter(p => p.afifly_name.trim())
          .map(p => ({
            afifly_name: p.afifly_name.trim(),
            level:       p.level || null,
            group_id:    Number(p.group_id) || 1,
          })),
      })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className={styles.modalBody} onSubmit={submit}>
      <div className={styles.jsonGrid}>
        <input className={styles.input} placeholder="N° rotation *" type="number" value={form.rot_number} onChange={setF('rot_number')} required />
        <input className={styles.input} type="date" value={form.rot_date} onChange={setF('rot_date')} required />
        <input className={styles.input} type="time" value={form.rot_time} onChange={setF('rot_time')} required />
        <input className={styles.input} placeholder="Immatriculation avion" value={form.plane_registration} onChange={setF('plane_registration')} />
        <input className={styles.input} placeholder="Pilote" value={form.pilot} onChange={setF('pilot')} />
        <input className={styles.input} placeholder="Chef avion" value={form.chef_avion} onChange={setF('chef_avion')} />
      </div>

      <div className={styles.participantsHeader}>
        <span className={styles.participantsLabel}>Participants</span>
        <button type="button" className={styles.addParticipantBtn} onClick={addParticipant}>+ Ajouter</button>
      </div>

      <div className={styles.participantList}>
        {participants.map((p, i) => (
          <div key={i} className={styles.participantRow}>
            <input
              className={styles.input}
              placeholder="Nom Afifly *"
              value={p.afifly_name}
              onChange={setP(i, 'afifly_name')}
            />
            <input
              className={styles.inputSm}
              placeholder="Niveau"
              value={p.level}
              onChange={setP(i, 'level')}
            />
            <input
              className={styles.inputSm}
              placeholder="Groupe"
              type="number"
              min="1"
              value={p.group_id}
              onChange={setP(i, 'group_id')}
            />
            <button type="button" className={styles.removeParticipantBtn} onClick={() => removeParticipant(i)}>✕</button>
          </div>
        ))}
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.formActions}>
        <button type="submit" className={styles.primaryBtn} disabled={loading}>
          {loading ? 'Création…' : 'Créer la rotation'}
        </button>
        <button type="button" className={styles.secondaryBtn} onClick={onCancel}>Annuler</button>
      </div>
    </form>
  )
}

function RotForm({ rot, onSuccess, onCancel }) {
  const [form, setForm] = useState({
    rot_number:         rot.rot_number,
    rot_date:           rot.rot_date,
    rot_time:           rot.rot_time?.slice(0, 5) ?? '',
    plane_registration: rot.plane_registration ?? '',
    pilot:              rot.pilot ?? '',
    chef_avion:         rot.chef_avion ?? '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const payload = {
        rot_number:         Number(form.rot_number),
        rot_date:           form.rot_date,
        rot_time:           form.rot_time,
        plane_registration: form.plane_registration || null,
        pilot:              form.pilot || null,
        chef_avion:         form.chef_avion || null,
      }
      await api.patch(`/rots/${rot.id}`, payload)
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className={styles.inlineForm} onSubmit={submit}>
      <h3 className={styles.formTitle}>Modifier la rotation</h3>
      <div className={styles.formGrid}>
        <input className={styles.input} placeholder="N° rot *" type="number" value={form.rot_number} onChange={set('rot_number')} required />
        <input className={styles.input} placeholder="Date *" type="date" value={form.rot_date} onChange={set('rot_date')} required />
        <input className={styles.input} placeholder="Heure *" type="time" value={form.rot_time} onChange={set('rot_time')} required />
        <input className={styles.input} placeholder="Immatriculation avion" value={form.plane_registration} onChange={set('plane_registration')} />
        <input className={styles.input} placeholder="Pilote" value={form.pilot} onChange={set('pilot')} />
        <input className={styles.input} placeholder="Chef avion" value={form.chef_avion} onChange={set('chef_avion')} />
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.formActions}>
        <button type="submit" className={styles.primaryBtn} disabled={loading}>{loading ? '…' : 'Enregistrer'}</button>
        <button type="button" className={styles.secondaryBtn} onClick={onCancel}>Annuler</button>
      </div>
    </form>
  )
}

/* ─────────────────────────────────────────────────
   Sous-onglet Vidéos
───────────────────────────────────────────────── */
function VideosSubTab() {
  const [videos, setVideos] = useState([])
  const [users, setUsers] = useState([])
  const [rots, setRots] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterUser, setFilterUser] = useState('')
  const [filterRot, setFilterRot] = useState('')
  const [assignVideo, setAssignVideo] = useState(null)

  async function load() {
    setLoading(true)
    try {
      const params = {}
      if (filterUser) params.user_id = filterUser
      if (filterRot)  params.rot_id  = filterRot
      const [vRes, uRes, rRes] = await Promise.all([
        api.get('/videos', { params }),
        api.get('/users'),
        api.get('/rots'),
      ])
      setVideos(vRes.data)
      setUsers(uRes.data)
      setRots(rRes.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filterUser, filterRot])

  async function deleteVideo(id, name) {
    if (!confirm(`Supprimer la vidéo ${name} ?`)) return
    await api.delete(`/videos/${id}`)
    load()
  }

  function formatSize(bytes) {
    if (!bytes) return '—'
    if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} Go`
    return `${(bytes / 1e6).toFixed(0)} Mo`
  }

  function formatDate(d) {
    return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
  }

  function userName(id) {
    const u = users.find(u => u.id === id)
    return u ? `${u.first_name} ${u.last_name}` : `#${id}`
  }

  function rotLabel(id) {
    const r = rots.find(r => r.id === id)
    return r ? `Rot ${r.rot_number} (${r.rot_date})` : `#${id}`
  }

  return (
    <div>
      <div className={styles.tabBar}>
        <h2 className={styles.tabTitle}>Vidéos ({videos.length})</h2>
        <div className={styles.filters}>
          <select className={styles.select} value={filterUser} onChange={e => setFilterUser(e.target.value)}>
            <option value="">Tous les sautants</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.first_name} {u.last_name}</option>)}
          </select>
          <select className={styles.select} value={filterRot} onChange={e => setFilterRot(e.target.value)}>
            <option value="">Toutes les rotations</option>
            {rots.map(r => <option key={r.id} value={r.id}>Rot {r.rot_number} — {r.rot_date}</option>)}
          </select>
        </div>
      </div>

      {assignVideo && (
        <AssignVideoForm
          video={assignVideo}
          users={users}
          rots={rots}
          onSuccess={() => { setAssignVideo(null); load() }}
          onCancel={() => setAssignVideo(null)}
        />
      )}

      {loading ? (
        <p className={styles.info}>Chargement…</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Taille</th>
              <th>Date caméra</th>
              <th>Propriétaire</th>
              <th>Rotation</th>
              <th>Statut</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {videos.map(v => (
              <tr key={v.id}>
                <td className={styles.videoFileName}>{v.file_name}</td>
                <td className={styles.muted}>{formatSize(v.file_size_bytes)}</td>
                <td className={styles.muted}>{formatDate(v.camera_timestamp)}</td>
                <td className={styles.muted}>{v.owner_id ? userName(v.owner_id) : '—'}</td>
                <td className={styles.muted}>{v.rot_id ? rotLabel(v.rot_id) : '—'}</td>
                <td>
                  <span className={v.matching_status === 'MATCHED' ? styles.badgeOk : styles.badgeErr}>
                    {v.matching_status}
                  </span>
                </td>
                <td className={styles.actions}>
                  <button className={styles.editBtn} onClick={() => setAssignVideo(v)}>Attribuer</button>
                  <button className={styles.dangerBtn} onClick={() => deleteVideo(v.id, v.file_name)}>Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function AssignVideoForm({ video, users, rots, onSuccess, onCancel }) {
  const [ownerId, setOwnerId]  = useState(video.owner_id ?? '')
  const [rotId, setRotId]      = useState(video.rot_id ?? '')
  const [error, setError]      = useState('')
  const [loading, setLoading]  = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.patch(`/videos/${video.id}`, {
        owner_id: ownerId ? Number(ownerId) : null,
        rot_id:   rotId   ? Number(rotId)   : null,
      })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className={styles.inlineForm} onSubmit={submit}>
      <h3 className={styles.formTitle}>Attribuer — {video.file_name}</h3>
      <div className={styles.formGrid}>
        <select className={styles.input} value={ownerId} onChange={e => setOwnerId(e.target.value)}>
          <option value="">Sans propriétaire</option>
          {users.map(u => <option key={u.id} value={u.id}>{u.first_name} {u.last_name}</option>)}
        </select>
        <select className={styles.input} value={rotId} onChange={e => setRotId(e.target.value)}>
          <option value="">Sans rotation</option>
          {rots.map(r => <option key={r.id} value={r.id}>Rot {r.rot_number} — {r.rot_date}</option>)}
        </select>
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.formActions}>
        <button type="submit" className={styles.primaryBtn} disabled={loading}>{loading ? '…' : 'Attribuer'}</button>
        <button type="button" className={styles.secondaryBtn} onClick={onCancel}>Annuler</button>
      </div>
    </form>
  )
}
