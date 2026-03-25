import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import styles from './KioskPage.module.css'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatSpeed(bps) {
  if (!bps || bps <= 0) return null
  if (bps >= 1e6) return `${(bps / 1e6).toFixed(1)} Mo/s`
  if (bps >= 1e3) return `${(bps / 1e3).toFixed(0)} Ko/s`
  return `${bps} o/s`
}

const STATUS_LABEL = {
  CONNECTING:   'Connexion…',
  IDENTIFYING:  'Identification',
  PROBING:      'Connexion',
  SCANNING:     'Analyse des vidéos',
  MATCHING:     'Matching',
  DOWNLOADING:  'Téléchargement',
  COPYING:      'Copie',
  PROCESSING:   'Traitement…',
  DONE:         'Terminé',
  ERROR:        'Erreur',
  UNKNOWN:      'Caméra inconnue',
}

// ─── Illustrations caméra ────────────────────────────────────────────────────

function GoProSVG({ className }) {
  return (
    <svg viewBox="0 0 160 106" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="gp-screen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e4a7a"/>
          <stop offset="100%" stopColor="#0d2040"/>
        </linearGradient>
        <radialGradient id="gp-lens" cx="38%" cy="33%">
          <stop offset="0%"   stopColor="#3a1060"/>
          <stop offset="50%"  stopColor="#1a0535"/>
          <stop offset="100%" stopColor="#0a0118"/>
        </radialGradient>
      </defs>

      {/* Corps — gris foncé lisible */}
      <rect x="2" y="2" width="156" height="102" rx="14" fill="#2c2e36" stroke="#5a5d68" strokeWidth="2"/>

      {/* Bande REC rouge en haut */}
      <rect x="16" y="3" width="56" height="8" rx="4" fill="#cc2222"/>
      <rect x="18" y="4" width="22" height="5" rx="2.5" fill="#ff4444" opacity="0.9"/>

      {/* Écran LCD gauche */}
      <rect x="8" y="16" width="68" height="56" rx="5" fill="#0e1520" stroke="#3a4a60" strokeWidth="1.5"/>
      <rect x="9" y="17" width="66" height="54" rx="4" fill="url(#gp-screen)"/>
      {/* Reflet écran */}
      <rect x="9" y="17" width="33" height="27" rx="4" fill="rgba(255,255,255,0.06)"/>

      {/* Boîtier objectif (squircle) */}
      <rect x="82" y="9" width="70" height="70" rx="18" fill="#1e2025" stroke="#4a4d58" strokeWidth="2"/>

      {/* Anneaux objectif */}
      <circle cx="117" cy="44" r="28" fill="#151618" stroke="#444750" strokeWidth="2"/>
      <circle cx="117" cy="44" r="23" fill="#111214" stroke="#3a3d48" strokeWidth="1.5"/>
      {/* Verre — violet bien visible */}
      <circle cx="117" cy="44" r="18" fill="url(#gp-lens)"/>
      {/* Iris central */}
      <circle cx="117" cy="44" r="9"  fill="#0a0215"/>
      {/* Reflets */}
      <ellipse cx="109" cy="36" rx="5.5" ry="3.5" fill="rgba(160,80,255,0.30)" transform="rotate(-25 109 36)"/>
      <circle  cx="107" cy="34" r="2.5" fill="rgba(255,255,255,0.20)"/>
      <circle  cx="125" cy="52" r="1.5" fill="rgba(180,100,255,0.15)"/>

      {/* Logo GoPro bleu */}
      <text x="11" y="81" fontFamily="Arial Black, Arial, sans-serif" fontSize="10" fontWeight="900" fill="#3ba3ff" letterSpacing="0.3">GoPro</text>
      {/* 4 carrés GoPro */}
      <rect x="12"  y="84" width="5.5" height="5.5" rx="0.5" fill="#3ba3ff"/>
      <rect x="19"  y="84" width="5.5" height="5.5" rx="0.5" fill="#3ba3ff"/>
      <rect x="12"  y="91" width="5.5" height="5.5" rx="0.5" fill="#3ba3ff"/>
      <rect x="19"  y="91" width="5.5" height="5.5" rx="0.5" fill="#3ba3ff"/>

      {/* Grille haut-parleur */}
      <circle cx="89"  cy="82" r="1.8" fill="#5a5e6a"/>
      <circle cx="96"  cy="82" r="1.8" fill="#5a5e6a"/>
      <circle cx="103" cy="82" r="1.8" fill="#5a5e6a"/>
      <circle cx="110" cy="82" r="1.8" fill="#5a5e6a"/>
      <circle cx="89"  cy="89" r="1.8" fill="#5a5e6a"/>
      <circle cx="96"  cy="89" r="1.8" fill="#5a5e6a"/>
      <circle cx="103" cy="89" r="1.8" fill="#5a5e6a"/>
      <circle cx="110" cy="89" r="1.8" fill="#5a5e6a"/>
      <circle cx="89"  cy="96" r="1.8" fill="#5a5e6a"/>
      <circle cx="96"  cy="96" r="1.8" fill="#5a5e6a"/>
      <circle cx="103" cy="96" r="1.8" fill="#5a5e6a"/>
      <circle cx="110" cy="96" r="1.8" fill="#5a5e6a"/>
    </svg>
  )
}

function Insta360SVG({ className }) {
  return (
    <svg viewBox="0 0 78 132" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="in-lens" cx="37%" cy="33%">
          <stop offset="0%"   stopColor="#1a6030"/>
          <stop offset="40%"  stopColor="#082818"/>
          <stop offset="100%" stopColor="#020e06"/>
        </radialGradient>
        <linearGradient id="in-screen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1a3a5c"/>
          <stop offset="100%" stopColor="#0a1828"/>
        </linearGradient>
      </defs>

      {/* Corps */}
      <rect x="5" y="10" width="68" height="118" rx="14" fill="#2c2e36" stroke="#5a5d68" strokeWidth="2"/>

      {/* Logement objectif fisheye (dépasse du corps) */}
      <circle cx="39" cy="28" r="22" fill="#1c1e22" stroke="#4a4d58" strokeWidth="2"/>
      {/* Anneaux concentriques */}
      <circle cx="39" cy="28" r="18.5" fill="#161820" stroke="#3a3d48" strokeWidth="1.5"/>
      <circle cx="39" cy="28" r="14.5" fill="#111318" stroke="#2a4030" strokeWidth="1.5"/>
      {/* Verre — teinte verte bien visible */}
      <circle cx="39" cy="28" r="11"   fill="url(#in-lens)"/>
      {/* Iris */}
      <circle cx="39" cy="28" r="5.5"  fill="#040e06"/>
      {/* Reflets verts */}
      <ellipse cx="33" cy="22" rx="4.5" ry="3" fill="rgba(40,200,80,0.30)" transform="rotate(-20 33 22)"/>
      <circle  cx="31" cy="20" r="2"   fill="rgba(255,255,255,0.22)"/>
      <circle  cx="45" cy="33" r="1.5" fill="rgba(60,200,90,0.18)"/>

      {/* Écran tactile */}
      <rect x="8"  y="53" width="62" height="60" rx="5" fill="#0e1520" stroke="#3a4a60" strokeWidth="1.5"/>
      <rect x="9"  y="54" width="60" height="58" rx="4" fill="url(#in-screen)"/>
      {/* Reflet écran */}
      <rect x="9"  y="54" width="30" height="29" rx="4" fill="rgba(255,255,255,0.06)"/>

      {/* Texte Insta360 */}
      <text x="39" y="49" fontFamily="Arial, sans-serif" fontSize="6.5" fontWeight="700" fill="#aabbcc" textAnchor="middle" letterSpacing="0.2">Insta360</text>

      {/* Deux boutons bas */}
      <circle cx="24" cy="122" r="5.5" fill="#3a3c45" stroke="#5a5d68" strokeWidth="1.5"/>
      <circle cx="24" cy="122" r="3.5" fill="#252830"/>
      <circle cx="54" cy="122" r="5.5" fill="#3a3c45" stroke="#5a5d68" strokeWidth="1.5"/>
      <circle cx="54" cy="122" r="3.5" fill="#252830"/>

      {/* LED bleue */}
      <circle cx="39" cy="122" r="2.5" fill="#0077ff"/>
      <circle cx="39" cy="122" r="1.2" fill="#55aaff"/>

      {/* Boutons latéraux */}
      <rect x="73" y="58" width="4" height="14" rx="2" fill="#3a3c45" stroke="#5a5d68" strokeWidth="1"/>
      <rect x="73" y="75" width="4" height="9"  rx="2" fill="#3a3c45" stroke="#5a5d68" strokeWidth="1"/>
    </svg>
  )
}

function GenericCameraSVG({ className }) {
  return (
    <svg viewBox="0 0 130 90" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="gen-lens" cx="38%" cy="33%">
          <stop offset="0%"   stopColor="#202035"/>
          <stop offset="100%" stopColor="#080810"/>
        </radialGradient>
      </defs>
      {/* Bosse viseur */}
      <rect x="36" y="3" width="46" height="15" rx="5" fill="#30323c" stroke="#5a5d68" strokeWidth="1.5"/>
      {/* Corps */}
      <rect x="5" y="16" width="120" height="68" rx="11" fill="#2c2e36" stroke="#5a5d68" strokeWidth="2"/>
      {/* Boîtier objectif */}
      <circle cx="75" cy="50" r="23" fill="#1e2025" stroke="#4a4d58" strokeWidth="2"/>
      <circle cx="75" cy="50" r="18" fill="#161820" stroke="#38404a" strokeWidth="1.5"/>
      <circle cx="75" cy="50" r="12" fill="url(#gen-lens)"/>
      <circle cx="75" cy="50" r="6"  fill="#0a0a14"/>
      <circle cx="67" cy="42" r="3.5" fill="rgba(255,255,255,0.18)"/>
      <circle cx="66" cy="41" r="1.5" fill="rgba(255,255,255,0.25)"/>
      {/* Bouton déclencheur */}
      <circle cx="110" cy="22" r="7"  fill="#3a3c45" stroke="#5a5d68" strokeWidth="1.5"/>
      <circle cx="110" cy="22" r="4.5" fill="#252830"/>
      {/* Flash */}
      <rect x="12" y="22" width="18" height="13" rx="3" fill="#28303a" stroke="#4a5060" strokeWidth="1"/>
      <rect x="13" y="23" width="16" height="11" rx="2" fill="#d0d8e0" opacity="0.6"/>
      {/* Viewfinder */}
      <rect x="40" y="6" width="10" height="9" rx="2" fill="#1a3050" stroke="#3a5070" strokeWidth="1"/>
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
  const navigate  = useNavigate()
  const hasBytes  = cam.bytes_total > 0
  const pct       = hasBytes ? Math.min(100, Math.round((cam.bytes_done / cam.bytes_total) * 100)) : 0
  const isActive  = cam.status === 'DOWNLOADING' || cam.status === 'COPYING'
  const isWaiting = ['CONNECTING', 'IDENTIFYING', 'PROBING', 'SCANNING', 'MATCHING', 'PROCESSING'].includes(cam.status)
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
    <div
      className={`${styles.card} ${cardMod}`}
      onClick={isUnknown ? () => navigate(`/onboarding?serial=${encodeURIComponent(cam.serial)}`) : undefined}
      role={isUnknown ? 'button' : undefined}
      tabIndex={isUnknown ? 0 : undefined}
      onKeyDown={isUnknown ? e => e.key === 'Enter' && navigate(`/onboarding?serial=${encodeURIComponent(cam.serial)}`) : undefined}
    >

      {/* En-tête : modèle caméra + pastille statut */}
      <div className={styles.cardTop}>
        <span className={styles.cameraLabel}>{cameraLabel}</span>
        <div className={styles.statusBlock}>
          <span className={`${styles.statusPill} ${styles[`pill${cam.status}`]}`}>
            {STATUS_LABEL[cam.status] ?? cam.status}
          </span>
          {cam.status_detail && (
            <span className={styles.statusDetail}>{cam.status_detail}</span>
          )}
        </div>
      </div>

      {/* Nom propriétaire — info principale, très lisible de loin */}
      <div className={styles.ownerName}>
        {isUnknown
          ? <span className={styles.ownerUnknown}>Qui est-ce&nbsp;?</span>
          : cam.owner_name
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

      {/* Caméra inconnue — CTA */}
      {isUnknown && (
        <div className={styles.unknownCta}>Toucher pour s'identifier →</div>
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
