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

// ─── Illustrations caméra ────────────────────────────────────────────────────

function GoProSVG({ className }) {
  return (
    <svg viewBox="0 0 120 80" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Corps */}
      <rect x="4" y="8" width="112" height="64" rx="12" fill="#1c1c1c" stroke="#3a3a3a" strokeWidth="1.5"/>
      {/* Rail latéral gauche */}
      <rect x="4" y="22" width="7" height="36" rx="3.5" fill="#131313" stroke="#2a2a2a" strokeWidth="1"/>
      {/* Boîtier objectif */}
      <circle cx="60" cy="40" r="23" fill="#0f0f0f" stroke="#2a2a2a" strokeWidth="2"/>
      {/* Anneau bague */}
      <circle cx="60" cy="40" r="19" fill="#0a0a0a" stroke="#3d3d3d" strokeWidth="1.5"/>
      {/* Objectif */}
      <circle cx="60" cy="40" r="13" fill="#060606" stroke="#3b82f6" strokeWidth="1.2"/>
      {/* Iris */}
      <circle cx="60" cy="40" r="7" fill="#0c0c0c"/>
      {/* Reflet */}
      <circle cx="54" cy="34" r="3.5" fill="rgba(255,255,255,0.06)"/>
      <circle cx="53" cy="33" r="1.6" fill="rgba(255,255,255,0.11)"/>
      {/* Bouton REC */}
      <circle cx="101" cy="19" r="7" fill="#1a0000" stroke="#500" strokeWidth="1"/>
      <circle cx="101" cy="19" r="4.5" fill="#cc0000"/>
      {/* Encart logo (bas gauche) */}
      <rect x="10" y="56" width="22" height="10" rx="3" fill="#111" stroke="#252525" strokeWidth="0.75"/>
      {/* Ports USB bas */}
      <rect x="44" y="68" width="32" height="3" rx="1.5" fill="#111" stroke="#2a2a2a" strokeWidth="0.75"/>
    </svg>
  )
}

function Insta360SVG({ className }) {
  return (
    <svg viewBox="0 0 80 130" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Corps */}
      <rect x="10" y="5" width="60" height="120" rx="16" fill="#1c1c1c" stroke="#3a3a3a" strokeWidth="1.5"/>
      {/* Objectif haut */}
      <circle cx="40" cy="30" r="19" fill="#0f0f0f" stroke="#2a2a2a" strokeWidth="2"/>
      <circle cx="40" cy="30" r="15" fill="#0a0a0a" stroke="#3d3d3d" strokeWidth="1.5"/>
      <circle cx="40" cy="30" r="10" fill="#060606" stroke="#8b5cf6" strokeWidth="1.2"/>
      <circle cx="40" cy="30" r="5.5" fill="#0c0c0c"/>
      <circle cx="34" cy="24" r="3" fill="rgba(255,255,255,0.06)"/>
      <circle cx="33" cy="23" r="1.3" fill="rgba(255,255,255,0.11)"/>
      {/* Objectif bas */}
      <circle cx="40" cy="100" r="19" fill="#0f0f0f" stroke="#2a2a2a" strokeWidth="2"/>
      <circle cx="40" cy="100" r="15" fill="#0a0a0a" stroke="#3d3d3d" strokeWidth="1.5"/>
      <circle cx="40" cy="100" r="10" fill="#060606" stroke="#8b5cf6" strokeWidth="1.2"/>
      <circle cx="40" cy="100" r="5.5" fill="#0c0c0c"/>
      <circle cx="34" cy="94" r="3" fill="rgba(255,255,255,0.06)"/>
      <circle cx="33" cy="93" r="1.3" fill="rgba(255,255,255,0.11)"/>
      {/* Bouton latéral */}
      <rect x="70" y="58" width="4" height="14" rx="2" fill="#252525" stroke="#333" strokeWidth="0.75"/>
      {/* Port USB bas */}
      <rect x="30" y="122" width="20" height="2.5" rx="1.25" fill="#111" stroke="#2a2a2a" strokeWidth="0.75"/>
    </svg>
  )
}

function GenericCameraSVG({ className }) {
  return (
    <svg viewBox="0 0 110 82" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Bosse viseur */}
      <rect x="34" y="4" width="42" height="14" rx="5" fill="#1c1c1c" stroke="#3a3a3a" strokeWidth="1.5"/>
      {/* Corps */}
      <rect x="6" y="16" width="98" height="60" rx="11" fill="#1c1c1c" stroke="#3a3a3a" strokeWidth="1.5"/>
      {/* Boîtier objectif */}
      <circle cx="55" cy="46" r="22" fill="#0f0f0f" stroke="#2a2a2a" strokeWidth="2"/>
      <circle cx="55" cy="46" r="17" fill="#0a0a0a" stroke="#3d3d3d" strokeWidth="1.5"/>
      <circle cx="55" cy="46" r="11" fill="#060606" stroke="#555" strokeWidth="1"/>
      <circle cx="55" cy="46" r="5.5" fill="#0c0c0c"/>
      <circle cx="48" cy="39" r="3.5" fill="rgba(255,255,255,0.06)"/>
      <circle cx="47" cy="38" r="1.5" fill="rgba(255,255,255,0.11)"/>
      {/* Bouton déclencheur */}
      <circle cx="89" cy="21" r="6" fill="#252525" stroke="#333" strokeWidth="1"/>
      <circle cx="89" cy="21" r="3.5" fill="#1e1e1e"/>
      {/* Flash */}
      <rect x="12" y="20" width="14" height="10" rx="3" fill="#111" stroke="#2a2a2a" strokeWidth="0.75"/>
    </svg>
  )
}

function CameraVisual({ make, className }) {
  const m = (make || '').toLowerCase()
  if (m.includes('gopro'))  return <GoProSVG className={className} />
  if (m.includes('insta'))  return <Insta360SVG className={className} />
  return <GenericCameraSVG className={className} />
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

      {/* Zone centrale : visuel caméra + indicateur statut */}
      <div className={styles.centerZone}>

        {/* Illustration caméra — toujours visible */}
        <div className={styles.cameraVisualWrap}>
          <CameraVisual make={cam.make} className={styles.cameraVisualSvg} />
          {isDone    && <span className={styles.badgeDone}>✓</span>}
          {isError   && <span className={styles.badgeError}>✗</span>}
          {isUnknown && <span className={styles.badgeUnknown}>!</span>}
        </div>

        {/* Spinner (attente) */}
        {isWaiting && (
          <div className={styles.spinnerWrap}>
            <div className={styles.spinner} />
            <span className={styles.spinnerLabel}>{STATUS_LABEL[cam.status]}</span>
          </div>
        )}

        {/* Anneau de progression (transfert actif) */}
        {isActive && (
          hasBytes
            ? <ProgressRing pct={pct} />
            : <div className={styles.spinnerWrap}>
                <div className={styles.spinner} />
                <span className={styles.spinnerLabel}>{STATUS_LABEL[cam.status]}…</span>
              </div>
        )}

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
