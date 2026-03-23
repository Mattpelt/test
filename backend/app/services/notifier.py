import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.models.rot import Rot
from app.models.settings import Settings
from app.models.user import User

logger = logging.getLogger(__name__)


def notify_videos_ready(user: User, rot_ids: list[int], db: Session) -> None:
    """
    Envoie un email récapitulatif au sautant listant les rots dont les vidéos sont prêtes.
    Ne fait rien si les notifications sont désactivées ou si la config SMTP est incomplète.
    """
    settings = db.query(Settings).first()

    if not getattr(user, 'notifications_enabled', True):
        return
    if not settings or not settings.smtp_host or not settings.smtp_from:
        logger.warning("[NOTIF] Notifications activées mais config SMTP incomplète — email non envoyé.")
        return
    if not user.email:
        logger.warning(f"[NOTIF] Pas d'email pour {user.first_name} {user.last_name} — notification ignorée.")
        return

    rots = db.query(Rot).filter(Rot.id.in_(rot_ids)).order_by(Rot.rot_date, Rot.rot_time).all()
    if not rots:
        return

    app_url = settings.app_url or "http://192.168.1.39"
    subject = "Vos vidéos de saut sont disponibles — SkyDive Media Hub"

    # Corps du mail en texte
    rot_lines = "\n".join(
        f"  • Rotation n°{r.rot_number} — {r.rot_date.strftime('%d/%m/%Y')} à {str(r.rot_time)[:5]}"
        for r in rots
    )
    body_text = (
        f"Bonjour {user.first_name},\n\n"
        f"Vos vidéos de saut sont prêtes pour les rotations suivantes :\n\n"
        f"{rot_lines}\n\n"
        f"Connectez-vous pour les télécharger :\n{app_url}\n\n"
        f"— SkyDive Media Hub"
    )

    # Corps du mail en HTML
    rot_html = "".join(
        f"<li>Rotation n°<strong>{r.rot_number}</strong> — "
        f"{r.rot_date.strftime('%d/%m/%Y')} à {str(r.rot_time)[:5]}</li>"
        for r in rots
    )
    body_html = f"""
<html><body style="font-family:sans-serif;color:#222;max-width:480px;margin:auto">
  <h2 style="color:#1a6fba">SkyDive Media Hub</h2>
  <p>Bonjour <strong>{user.first_name}</strong>,</p>
  <p>Vos vidéos de saut sont prêtes pour les rotations suivantes&nbsp;:</p>
  <ul>{rot_html}</ul>
  <p>
    <a href="{app_url}" style="display:inline-block;padding:10px 20px;background:#1a6fba;
       color:#fff;text-decoration:none;border-radius:5px">
      Accéder à mes vidéos
    </a>
  </p>
  <p style="color:#888;font-size:12px">SkyDive Media Hub — système automatique</p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = user.email
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.smtp_from, user.email, msg.as_string())
        rot_nums = ", ".join(f"#{r.rot_number}" for r in rots)
        logger.info(f"[NOTIF] ✔ Email envoyé à {user.email} — rotations {rot_nums}")
    except Exception as e:
        logger.error(f"[NOTIF] Échec envoi email à {user.email} : {e}")
