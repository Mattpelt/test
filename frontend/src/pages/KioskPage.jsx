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
    <svg viewBox="0 0 160 106" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="gp-screen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0d2a4a"/>
          <stop offset="100%" stopColor="#070f1a"/>
        </linearGradient>
        <radialGradient id="gp-lens" cx="38%" cy="33%">
          <stop offset="0%"   stopColor="#1a083a"/>
          <stop offset="40%"  stopColor="#080218"/>
          <stop offset="100%" stopColor="#030108"/>
        </radialGradient>
      </defs>

      {/* Corps — noir texturé */}
      <rect x="2" y="2" width="156" height="102" rx="14" fill="#18191e" stroke="#28292e" strokeWidth="1.5"/>

      {/* Bande REC rouge en haut */}
      <rect x="16" y="3" width="56" height="7" rx="3.5" fill="#bb0000"/>
      <rect x="18" y="4" width="20" height="5" rx="2.5" fill="#ff1a1a" opacity="0.85"/>

      {/* Écran LCD gauche */}
      <rect x="8" y="16" width="68" height="56" rx="5" fill="#08090f" stroke="#252830" strokeWidth="1"/>
      <rect x="9" y="17" width="66" height="54" rx="4" fill="url(#gp-screen)"/>
      {/* Reflet écran */}
      <rect x="9" y="17" width="33" height="27" rx="4" fill="rgba(255,255,255,0.025)"/>

      {/* Boîtier objectif (squircle) */}
      <rect x="82" y="9" width="70" height="70" rx="18" fill="#0d0d0d" stroke="#212121" strokeWidth="1.5"/>

      {/* Anneaux objectif */}
      <circle cx="117" cy="44" r="28" fill="#080808" stroke="#1c1c1c" strokeWidth="1.5"/>
      <circle cx="117" cy="44" r="23" fill="#060606" stroke="#252525" strokeWidth="1"/>
      {/* Verre — teinte violet/pourpre caractéristique GoPro */}
      <circle cx="117" cy="44" r="18" fill="url(#gp-lens)"/>
      {/* Iris central */}
      <circle cx="117" cy="44" r="9"  fill="#04020c"/>
      {/* Reflets */}
      <ellipse cx="109" cy="36" rx="5.5" ry="3.5" fill="rgba(140,70,220,0.13)" transform="rotate(-25 109 36)"/>
      <circle  cx="107" cy="34" r="2.5" fill="rgba(255,255,255,0.07)"/>
      <circle  cx="125" cy="52" r="1.5" fill="rgba(160,80,255,0.05)"/>

      {/* Logo GoPro bleu */}
      <text x="11" y="81" fontFamily="Arial Black, Arial, sans-serif" fontSize="10" fontWeight="900" fill="#1a8fff" letterSpacing="0.3">GoPro</text>
      {/* 4 carrés GoPro */}
      <rect x="12"  y="84" width="5.5" height="5.5" rx="0.5" fill="#1a8fff"/>
      <rect x="19"  y="84" width="5.5" height="5.5" rx="0.5" fill="#1a8fff"/>
      <rect x="12"  y="91" width="5.5" height="5.5" rx="0.5" fill="#1a8fff"/>
      <rect x="19"  y="91" width="5.5" height="5.5" rx="0.5" fill="#1a8fff"/>

      {/* Grille haut-parleur */}
      <circle cx="89"  cy="82" r="1.8" fill="#242424"/>
      <circle cx="96"  cy="82" r="1.8" fill="#242424"/>
      <circle cx="103" cy="82" r="1.8" fill="#242424"/>
      <circle cx="110" cy="82" r="1.8" fill="#242424"/>
      <circle cx="89"  cy="89" r="1.8" fill="#242424"/>
      <circle cx="96"  cy="89" r="1.8" fill="#242424"/>
      <circle cx="103" cy="89" r="1.8" fill="#242424"/>
      <circle cx="110" cy="89" r="1.8" fill="#242424"/>
      <circle cx="89"  cy="96" r="1.8" fill="#242424"/>
      <circle cx="96"  cy="96" r="1.8" fill="#242424"/>
      <circle cx="103" cy="96" r="1.8" fill="#242424"/>
      <circle cx="110" cy="96" r="1.8" fill="#242424"/>
    </svg>
  )
}

function Insta360SVG({ className }) {
  return (
    <svg viewBox="0 0 78 132" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="in-lens" cx="37%" cy="33%">
          <stop offset="0%"   stopColor="#082010"/>
          <stop offset="35%"  stopColor="#041208"/>
          <stop offset="100%" stopColor="#010804"/>
        </radialGradient>
        <linearGradient id="in-screen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0e2235"/>
          <stop offset="100%" stopColor="#060d18"/>
        </linearGradient>
      </defs>

      {/* Corps */}
      <rect x="5" y="10" width="68" height="118" rx="14" fill="#1e1f24" stroke="#2a2b30" strokeWidth="1.5"/>

      {/* Logement objectif fisheye (dépasse du corps) */}
      <circle cx="39" cy="28" r="22" fill="#111" stroke="#1e1e1e" strokeWidth="2"/>
      {/* Anneaux concentriques */}
      <circle cx="39" cy="28" r="18.5" fill="#0d0d0d" stroke="#252525" strokeWidth="1.5"/>
      <circle cx="39" cy="28" r="14.5" fill="#090909" stroke="#1e2818" strokeWidth="1"/>
      {/* Verre — teinte verte/teal caractéristique Insta360 */}
      <circle cx="39" cy="28" r="11"   fill="url(#in-lens)"/>
      {/* Iris */}
      <circle cx="39" cy="28" r="5.5"  fill="#020a04"/>
      {/* Reflets verts */}
      <ellipse cx="33" cy="22" rx="4.5" ry="3" fill="rgba(30,160,60,0.14)" transform="rotate(-20 33 22)"/>
      <circle  cx="31" cy="20" r="2"   fill="rgba(255,255,255,0.08)"/>
      <circle  cx="45" cy="33" r="1.5" fill="rgba(40,180,70,0.06)"/>

      {/* Écran tactile */}
      <rect x="8"  y="53" width="62" height="60" rx="5" fill="#070b12" stroke="#1e2330" strokeWidth="1"/>
      <rect x="9"  y="54" width="60" height="58" rx="4" fill="url(#in-screen)"/>
      {/* Reflet écran */}
      <rect x="9"  y="54" width="30" height="29" rx="4" fill="rgba(255,255,255,0.02)"/>

      {/* Texte Insta360 */}
      <text x="39" y="49" fontFamily="Arial, sans-serif" fontSize="6.5" fontWeight="600" fill="#777" textAnchor="middle" letterSpacing="0.2">Insta360</text>

      {/* Deux boutons bas */}
      <circle cx="24" cy="122" r="5.5" fill="#141418" stroke="#282830" strokeWidth="1"/>
      <circle cx="24" cy="122" r="3.5" fill="#0a0a0e"/>
      <circle cx="54" cy="122" r="5.5" fill="#141418" stroke="#282830" strokeWidth="1"/>
      <circle cx="54" cy="122" r="3.5" fill="#0a0a0e"/>

      {/* LED bleue */}
      <circle cx="39" cy="122" r="2.5" fill="#0055ee" opacity="0.9"/>
      <circle cx="39" cy="122" r="1.2" fill="#4499ff"/>

      {/* Boutons latéraux */}
      <rect x="73" y="58" width="4" height="14" rx="2" fill="#252528" stroke="#303035" strokeWidth="0.75"/>
      <rect x="73" y="75" width="4" height="9"  rx="2" fill="#252528" stroke="#303035" strokeWidth="0.75"/>
    </svg>
  )
}

function GenericCameraSVG({ className }) {
  return (
    <svg viewBox="0 0 130 90" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="gen-lens" cx="38%" cy="33%">
          <stop offset="0%"   stopColor="#101020"/>
          <stop offset="100%" stopColor="#030308"/>
        </radialGradient>
      </defs>
      {/* Bosse viseur */}
      <rect x="36" y="3" width="46" height="15" rx="5" fill="#1c1c22" stroke="#2e2e34" strokeWidth="1.5"/>
      {/* Corps */}
      <rect x="5" y="16" width="120" height="68" rx="11" fill="#1c1c22" stroke="#2e2e34" strokeWidth="1.5"/>
      {/* Boîtier objectif */}
      <circle cx="75" cy="50" r="23" fill="#0e0e14" stroke="#222228" strokeWidth="2"/>
      <circle cx="75" cy="50" r="18" fill="#090910" stroke="#252530" strokeWidth="1.5"/>
      <circle cx="75" cy="50" r="12" fill="url(#gen-lens)"/>
      <circle cx="75" cy="50" r="6"  fill="#030308"/>
      <circle cx="67" cy="42" r="3.5" fill="rgba(255,255,255,0.06)"/>
      <circle cx="66" cy="41" r="1.5" fill="rgba(255,255,255,0.1)"/>
      {/* Bouton déclencheur */}
      <circle cx="110" cy="22" r="7"  fill="#1e1e24" stroke="#2e2e34" strokeWidth="1"/>
      <circle cx="110" cy="22" r="4.5" fill="#141418"/>
      {/* Flash */}
      <rect x="12" y="22" width="18" height="13" rx="3" fill="#111116" stroke="#252530" strokeWidth="0.75"/>
      <rect x="13" y="23" width="16" height="11" rx="2" fill="#0a0a10" opacity="0.7"/>
      {/* Viewfinder */}
      <rect x="40" y="6" width="10" height="9" rx="2" fill="#0a0a10" stroke="#222" strokeWidth="0.75"/>
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
