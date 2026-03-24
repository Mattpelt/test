import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import styles from './KioskPage.module.css'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatSpeed(bps) {
  if (!bps || bps <= 0) return null
  if (bps >= 1e6) return `${(bps / 1e6).toFixed(1)} Mo/s`
  if (bps >= 1e3) return `${(bps / 1e3).toFixed(0)} Ko/s`
  return `${bps} o/s`
}

const STATUS_LABEL = {
  CONNECTING:  'Connexion…',
  DETECTING:   'Identification…',
  DOWNLOADING: 'Téléchargement',
  COPYING:     'Copie',
  PROCESSING:  'Traitement…',
  DONE:        'Terminé',
  ERROR:       'Erreur',
  UNKNOWN:     'Caméra inconnue',
}

// ─── Anneau SVG de progression ──────────────────────────────────────────────

function ProgressRing({ pct }) {
  const size   = 150
  const stroke = 12
  const r      = (size - stroke) / 2
  const circ   = 2 * Math.PI * r
  const fill   = Math.max(0, Math.min(pct / 100, 1)) * circ
  const color  = pct >= 100 ? '#22c55e' : '#3b82f6'

  return (
    <svg width={size} height={size} className={styles.ring}>
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="#252525" strokeWidth={stroke}
      />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={`${fill} ${circ}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: 'stroke-dasharray 0.4s ease, stroke 0.3s' }}
      />
      <text
        x="50%" y="50%"
        textAnchor="middle" dy=".35em"
        className={styles.ringPct}
      >
        {pct}%
      </text>
    </svg>
  )
}

// ─── Card caméra ────────────────────────────────────────────────────────────

function CameraCard({ cam }) {
  const hasBytes  = cam.bytes_total > 0
  const pct       = hasBytes ? Math.min(100, Math.round((cam.bytes_done / cam.bytes_total) * 100)) : 0
  const isActive  = cam.status === 'DOWNLOADING' || cam.status === 'COPYING'
  const isWaiting = cam.status === 'CONNECTING' || cam.status === 'DETECTING' || cam.status === 'PROCESSING'
  const isDone    = cam.status === 'DONE'
  const isError   = cam.status === 'ERROR'
  const isUnknown = cam.status === 'UNKNOWN'

  const cardMod = isDone    ? styles.cardDone
                : isError   ? styles.cardError
                : isUnknown ? styles.cardUnknown
                : isActive  ? styles.cardActive
                : isWaiting ? styles.cardWaiting
                : ''

  const cameraLabel = [cam.make, cam.model].filter(Boolean).join(' ') || cam.serial

  return (
    <div className={`${styles.card} ${cardMod}`}>

      {/* En-tête : modèle caméra + pastille statut */}
      <div className={styles.cardTop}>
        <span className={styles.cameraLabel}>{cameraLabel}</span>
        <span className={`${styles.statusPill} ${styles[`pill${cam.status}`]}`}>
          {STATUS_LABEL[cam.status] ?? cam.status}
        </span>
      </div>

      {/* Nom propriétaire — info principale, très lisible de loin */}
      <div className={styles.ownerName}>
        {cam.owner_name
          ? cam.owner_name.toUpperCase()
          : <span className={styles.ownerPending}>{cam.serial}</span>
        }
      </div>

      {/* Zone centrale : animation selon état */}
      <div className={styles.centerZone}>
        {isWaiting && (
          <div className={styles.spinnerWrap}>
            <div className={styles.spinner} />
            <span className={styles.spinnerLabel}>{STATUS_LABEL[cam.status]}</span>
          </div>
        )}

        {isActive && (
          hasBytes
            ? <ProgressRing pct={pct} />
            : <div className={styles.spinnerWrap}>
                <div className={styles.spinner} />
                <span className={styles.spinnerLabel}>{STATUS_LABEL[cam.status]}…</span>
              </div>
        )}

        {isDone    && <div className={styles.iconDone}>✓</div>}
        {isError   && <div className={styles.iconError}>✗</div>}
        {isUnknown && <div className={styles.iconUnknown}>!</div>}
      </div>

      {/* Barre de progression fichiers */}
      {(isActive || isDone) && cam.video_total > 0 && (
        <div className={styles.fileProgress}>
          <div className={styles.fileBar}>
            <div
              className={styles.fileFill}
              style={{ width: `${isDone ? 100 : (cam.video_index / cam.video_total) * 100}%` }}
            />
          </div>
          <span className={styles.fileCount}>
            {isDone ? cam.video_total : cam.video_index}&nbsp;/&nbsp;{cam.video_total}&nbsp;vidéo{cam.video_total > 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Vitesse de transfert */}
      {isActive && formatSpeed(cam.speed_bps) && (
        <div className={styles.speed}>{formatSpeed(cam.speed_bps)}</div>
      )}

      {/* Rotations matchées */}
      {cam.rot_labels?.length > 0 && (
        <div className={styles.rotChips}>
          {cam.rot_labels.map(r => (
            <span key={r} className={styles.rotChip}>{r}</span>
          ))}
        </div>
      )}

      {/* Message d'erreur */}
      {isError && cam.error_msg && (
        <div className={styles.errorMsg}>{cam.error_msg}</div>
      )}

      {/* Caméra inconnue */}
      {isUnknown && (
        <div className={styles.unknownMsg}>Aucun compte associé à cette caméra — onboarding requis.</div>
      )}
    </div>
  )
}

// ─── Page principale ─────────────────────────────────────────────────────────

export default function KioskPage() {
  const [cameras, setCameras]     = useState([])
  const [lastUpdate, setLastUpdate] = useState(null)
  const [connError, setConnError]  = useState(false)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const r = await fetch('/api/cameras/live')
        if (!r.ok) throw new Error(r.status)
        const data = await r.json()
        if (!cancelled) {
          setCameras(data)
          setLastUpdate(new Date())
          setConnError(false)
        }
      } catch {
        if (!cancelled) setConnError(true)
      }
    }

    poll()
    const id = setInterval(poll, 1000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  return (
    <div className={styles.page}>

      <header className={styles.header}>
        <span className={styles.headerTitle}>SkyDive Media Hub</span>
        <span className={styles.headerRight}>
          {connError
            ? <span className={styles.connError}>Serveur inaccessible</span>
            : lastUpdate && `Actualisé à ${lastUpdate.toLocaleTimeString('fr-FR')}`
          }
        </span>
      </header>

      <main className={styles.main}>
        {cameras.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>⬡</div>
            <p className={styles.emptyTitle}>Aucune caméra connectée</p>
            <p className={styles.emptySub}>Branchez une caméra USB pour démarrer l'ingestion automatique</p>
          </div>
        ) : (
          <div className={styles.grid}>
            {cameras.map(cam => <CameraCard key={cam.serial} cam={cam} />)}
          </div>
        )}
      </main>

      <footer className={styles.footer}>
        <Link to="/login" className={styles.footerLink}>← Connexion</Link>
      </footer>

    </div>
  )
}
