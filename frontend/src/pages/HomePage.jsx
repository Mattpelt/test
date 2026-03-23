import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import styles from './HomePage.module.css'
import GestionTab from '../components/GestionTab'
import ProfileTab from '../components/ProfileTab'

export default function HomePage() {
  const [previewVideo, setPreviewVideo] = useState(null) // {id, file_name}
  const { user, logout } = useAuth()
  const tabs = [
    'Mes vidéos',
    'Mon compte',
    ...(user.is_admin ? ['Gestion', 'Paramètres'] : []),
  ]
  const [tab, setTab] = useState('Mes vidéos')

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.headerTitle}>SkyDive Media Hub</span>
        <div className={styles.headerRight}>
          <span className={styles.userName}>{user.first_name} {user.last_name}</span>
          <button className={styles.logoutBtn} onClick={logout}>Déconnexion</button>
        </div>
      </header>

      <div className={styles.tabs}>
        {tabs.map(t => (
          <button
            key={t}
            className={`${styles.tab} ${tab === t ? styles.tabActive : ''}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {previewVideo && (
        <VideoPlayerModal video={previewVideo} onClose={() => setPreviewVideo(null)} />
      )}

      <main className={styles.main}>
        {tab === 'Mes vidéos'  && <MyVideosTab onPreview={setPreviewVideo} />}
        {tab === 'Mon compte'  && <ProfileTab />}
        {tab === 'Gestion'     && <GestionTab />}
        {tab === 'Paramètres'  && <SettingsTab />}
      </main>
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Onglet Mes vidéos
───────────────────────────────────────────────── */
function MyVideosTab({ onPreview }) {
  const { user } = useAuth()
  const [rots, setRots] = useState([])
  const [videosByRot, setVideosByRot] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const { data: myRots } = await api.get('/rots/my')
        setRots(myRots)
        const entries = await Promise.all(
          myRots.map(async rot => {
            const { data } = await api.get(`/videos/rot/${rot.id}`)
            return [rot.id, data]
          })
        )
        setVideosByRot(Object.fromEntries(entries))
      } catch {
        setError('Impossible de charger vos données.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  function formatDate(dateStr) {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('fr-FR', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    })
  }

  function formatTime(timeStr) { return timeStr?.slice(0, 5) ?? '' }

  function formatSize(bytes) {
    if (!bytes) return ''
    if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} Go`
    return `${(bytes / 1e6).toFixed(0)} Mo`
  }

  if (loading) return <p className={styles.info}>Chargement…</p>
  if (error)   return <p className={styles.errorMsg}>{error}</p>

  if (rots.length === 0) {
    return (
      <div className={styles.empty}>
        <p>Aucune vidéo disponible pour le moment.</p>
        <p className={styles.emptyHint}>Vos vidéos apparaîtront ici après chaque saut.</p>
      </div>
    )
  }

  return (
    <div className={styles.videoContent}>
      {rots.map(rot => {
        const myParticipant = rot.participants.find(p => p.user_id === user.id)
        const myGroupId = myParticipant?.group_id
        const groupMembers = rot.participants
          .filter(p => p.group_id === myGroupId)
          .sort((a, b) => a.afifly_name.localeCompare(b.afifly_name))
        const rotVideos = videosByRot[rot.id] ?? []

        return (
          <section key={rot.id} className={styles.rotSection}>
            <div className={styles.rotHeader}>
              <h2 className={styles.rotTitle}>
                Rot n°{rot.rot_number}
                {rot.day_number ? ` — saut n°${rot.day_number}` : ''}
              </h2>
              <span className={styles.rotMeta}>
                {formatDate(rot.rot_date)} · {formatTime(rot.rot_time)}
                {rot.plane_registration ? ` · ${rot.plane_registration}` : ''}
              </span>
            </div>

            <div className={styles.membersGrid}>
              {groupMembers.map(member => {
                const memberVideos = rotVideos.filter(v => v.owner_id === member.user_id)
                return (
                  <div key={member.id} className={styles.memberCard}>
                    <div className={styles.memberName}>
                      {member.afifly_name}
                      {member.user_id === user.id && <span className={styles.meTag}>moi</span>}
                    </div>
                    {member.level && <span className={styles.memberLevel}>{member.level}</span>}
                    {memberVideos.length === 0 ? (
                      <p className={styles.noVideo}>Pas de vidéo</p>
                    ) : (
                      <ul className={styles.videoList}>
                        {memberVideos.map(video => (
                          <li key={video.id} className={styles.videoItem}>
                            {video.thumbnail_path && (
                              <img
                                src={`/api/videos/${video.id}/thumbnail?token=${encodeURIComponent(localStorage.getItem('token'))}`}
                                className={styles.videoThumb}
                                alt=""
                                onClick={() => onPreview(video)}
                              />
                            )}
                            <div className={styles.videoInfo}>
                              <span className={styles.videoName}>{video.file_name}</span>
                              <span className={styles.videoMeta}>
                                {video.file_format}
                                {video.file_size_bytes ? ` · ${formatSize(video.file_size_bytes)}` : ''}
                              </span>
                              <div className={styles.videoActions}>
                                <button
                                  className={styles.previewBtn}
                                  onClick={() => onPreview(video)}
                                >
                                  Aperçu
                                </button>
                                <button
                                  className={styles.downloadBtn}
                                  onClick={() => downloadVideo(video.id, video.file_name)}
                                >
                                  Télécharger
                                </button>
                              </div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )
              })}
            </div>
          </section>
        )
      })}
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
    setSaving(true); setSaved(false); setError('')
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

      <form className={styles.settingsForm} onSubmit={save}>
        <SettingField label="Rétention des vidéos" hint="Durée de conservation des vidéos après ingestion."
          value={settings.retention_days} unit="jours" onChange={set('retention_days')} />
        <SettingField label="Fenêtre de matching" hint="Écart max entre l'horodatage vidéo et l'heure du rot."
          value={settings.matching_window_minutes} unit="minutes" onChange={set('matching_window_minutes')} />
        <SettingField label="Delta cible saut" hint="Décalage horaire habituel entre le décollage et le saut."
          value={settings.jump_target_delta_min} unit="minutes" onChange={set('jump_target_delta_min')} />
        <SettingField label="Fenêtre de saut" hint="Plage de temps autour du delta cible pour la détection."
          value={settings.jump_window_hours} unit="heures" onChange={set('jump_window_hours')} />

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

        {[
          ['app_url', "URL de l'application", "Lien inclus dans l'email (ex: http://192.168.1.39).", 'http://192.168.1.39', 'text'],
          ['smtp_host', 'Serveur SMTP', 'Hôte du serveur d\'envoi (ex: smtp.gmail.com).', 'smtp.gmail.com', 'text'],
          ['smtp_user', 'Utilisateur SMTP', 'Adresse email utilisée pour l\'authentification.', 'expediteur@gmail.com', 'text'],
          ['smtp_password', 'Mot de passe SMTP', 'Laissez vide pour ne pas modifier le mot de passe.', '••••••••••••••••', 'password'],
          ['smtp_from', 'Adresse expéditeur', 'Adresse affichée dans le champ "De".', 'noreply@skydive.fr', 'text'],
        ].map(([field, label, hint, placeholder, type]) => (
          <div key={field} className={styles.settingRow}>
            <div>
              <div className={styles.settingLabel}>{label}</div>
              <div className={styles.settingHint}>{hint}</div>
            </div>
            <input className={styles.textInput} type={type} value={settings[field] ?? ''} onChange={setText(field)} placeholder={placeholder} />
          </div>
        ))}

        <div className={styles.settingRow}>
          <div>
            <div className={styles.settingLabel}>Port SMTP</div>
            <div className={styles.settingHint}>587 (STARTTLS) recommandé.</div>
          </div>
          <div className={styles.settingInput}>
            <input type="number" className={styles.numInput} value={settings.smtp_port ?? 587} onChange={set('smtp_port')} />
          </div>
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
        <input type="number" min={1} value={value} onChange={onChange} className={styles.numInput} />
        <span className={styles.unit}>{unit}</span>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Lecteur vidéo
───────────────────────────────────────────────── */
function VideoPlayerModal({ video, onClose }) {
  const token = localStorage.getItem('token')
  const videoRef = useRef(null)

  // Fermer avec Echap
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className={styles.playerOverlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={styles.playerModal}>
        <div className={styles.playerHeader}>
          <span className={styles.playerTitle}>{video.file_name}</span>
          <button className={styles.playerClose} onClick={onClose}>✕</button>
        </div>
        <video
          ref={videoRef}
          className={styles.playerVideo}
          src={`/api/videos/${video.id}/stream?token=${encodeURIComponent(token)}`}
          controls
          autoPlay
          playsInline
        />
      </div>
    </div>
  )
}

// Téléchargement : navigation directe avec token en query param
// Permet à nginx de streamer le fichier sans le charger en mémoire
function downloadVideo(videoId, fileName) {
  const token = localStorage.getItem('token')
  const a = document.createElement('a')
  a.href = `/api/videos/${videoId}/download?token=${encodeURIComponent(token)}`
  a.download = fileName
  a.click()
}
