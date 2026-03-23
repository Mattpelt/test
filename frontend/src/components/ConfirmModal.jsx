import { useEffect } from 'react'
import styles from './ConfirmModal.module.css'

/**
 * Modal de confirmation générique — remplace window.confirm().
 *
 * Props :
 *   title        — titre du modal (optionnel)
 *   message      — texte de la question
 *   confirmLabel — libellé du bouton de validation (défaut : "Confirmer")
 *   cancelLabel  — libellé du bouton d'annulation (défaut : "Annuler")
 *   danger       — bouton de confirmation rouge (défaut : true)
 *   onConfirm    — callback appelé si l'utilisateur confirme
 *   onCancel     — callback appelé si l'utilisateur annule
 */
export default function ConfirmModal({
  title,
  message,
  confirmLabel = 'Confirmer',
  cancelLabel = 'Annuler',
  danger = true,
  onConfirm,
  onCancel,
}) {
  // Fermeture via Échap
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onCancel() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onCancel])

  return (
    <div
      className={styles.overlay}
      onClick={e => e.target === e.currentTarget && onCancel()}
    >
      <div className={styles.modal} role="dialog" aria-modal="true">
        {title && <h3 className={styles.title}>{title}</h3>}
        <p className={styles.message}>{message}</p>
        <div className={styles.actions}>
          <button
            className={danger ? styles.dangerBtn : styles.primaryBtn}
            onClick={onConfirm}
            autoFocus
          >
            {confirmLabel}
          </button>
          <button className={styles.cancelBtn} onClick={onCancel}>
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
