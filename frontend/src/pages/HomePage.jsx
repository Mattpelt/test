import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import styles from './HomePage.module.css'

export default function HomePage() {
  const { user, logout } = useAuth()
  const [rots, setRots] = useState([])
  const [videosByRot, setVideosByRot] = useState({}) // rotId → [video]
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const { data: myRots } = await api.get('/rots/my')
        setRots(myRots)

        // Charger les vidéos de chaque rot en parallèle
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

  function formatTime(timeStr) {
    return timeStr?.slice(0, 5) ?? ''
  }

  function formatSize(bytes) {
    if (!bytes) return ''
    if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} Go`
    return `${(bytes / 1e6).toFixed(0)} Mo`
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.headerTitle}>SkyDive Media Hub</span>
        <div className={styles.headerRight}>
          <span className={styles.userName}>{user.first_name} {user.last_name}</span>
          <button className={styles.logoutBtn} onClick={logout}>Déconnexion</button>
        </div>
      </header>

      <main className={styles.main}>
        {loading && <p className={styles.info}>Chargement…</p>}
        {error  && <p className={styles.errorMsg}>{error}</p>}

        {!loading && !error && rots.length === 0 && (
          <div className={styles.empty}>
            <p>Aucune vidéo disponible pour le moment.</p>
            <p className={styles.emptyHint}>Vos vidéos apparaîtront ici après chaque saut.</p>
          </div>
        )}

        {rots.map(rot => {
          // Trouver le group_id de l'utilisateur dans ce rot
          const myParticipant = rot.participants.find(p => p.user_id === user.id)
          const myGroupId = myParticipant?.group_id

          // Participants du même groupe, triés par nom
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
                        {member.user_id === user.id && (
                          <span className={styles.meTag}>moi</span>
                        )}
                      </div>
                      {member.level && (
                        <span className={styles.memberLevel}>{member.level}</span>
                      )}

                      {memberVideos.length === 0 ? (
                        <p className={styles.noVideo}>Pas de vidéo</p>
                      ) : (
                        <ul className={styles.videoList}>
                          {memberVideos.map(video => (
                            <li key={video.id} className={styles.videoItem}>
                              <span className={styles.videoName}>
                                {video.file_name}
                              </span>
                              <span className={styles.videoMeta}>
                                {video.file_format}
                                {video.file_size_bytes
                                  ? ` · ${formatSize(video.file_size_bytes)}`
                                  : ''}
                              </span>
                              <a
                                href={`/api/videos/${video.id}/download`}
                                className={styles.downloadBtn}
                                download
                                onClick={e => {
                                  // Injecter le token dans l'URL via fetch au lieu de l'ancre directe
                                  e.preventDefault()
                                  downloadVideo(video.id, video.file_name)
                                }}
                              >
                                Télécharger
                              </a>
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
      </main>
    </div>
  )
}

// Téléchargement avec Bearer token (fetch + blob)
async function downloadVideo(videoId, fileName) {
  const token = localStorage.getItem('token')
  const res = await fetch(`/api/videos/${videoId}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}
