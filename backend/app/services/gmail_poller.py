import base64
import logging
import os
import tempfile
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.database import SessionLocal
from app.models.settings import Settings
from app.services.pdf_parser import parse_afifly_pdf
from app.services.rot_service import upsert_rot

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_DIR = Path("/app/gmail_credentials")
TOKEN_FILE = CREDENTIALS_DIR / "token.json"
PARSING_ERROR_LABEL = "PARSING_ERRORS"


def _get_service():
    if not TOKEN_FILE.exists():
        logger.warning("Gmail : token.json introuvable — lancer scripts/gmail_auth.py")
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _get_or_create_label(service, name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == name:
            return label["id"]
    label = service.users().labels().create(
        userId="me",
        body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
    ).execute()
    return label["id"]


def _iter_parts(payload):
    yield payload
    for part in payload.get("parts", []):
        yield from _iter_parts(part)


def _mark_read(service, msg_id: str):
    service.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def check_new_rots():
    """
    Interroge Gmail pour les nouveaux emails contenant un PDF de rot.
    - Email parsé avec succès et rot inchangé → marqué lu, rien en base
    - Email parsé avec succès et rot nouveau/modifié → upsert en base, marqué lu
    - Email avec PDF invalide → label PARSING_ERRORS ajouté, email conservé non lu
    """
    db = SessionLocal()
    try:
        settings = db.query(Settings).first()
        sender = settings.gmail_sender_filter if settings else ""
        if not sender:
            logger.debug("gmail_sender_filter non configuré — polling ignoré")
            return

        service = _get_service()
        if not service:
            return

        query = f"from:{sender} is:unread has:attachment"
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        if not messages:
            return

        logger.info(f"Gmail : {len(messages)} email(s) non lu(s) de {sender}")
        error_label_id = None

        for msg_meta in messages:
            msg_id = msg_meta["id"]
            msg = service.users().messages().get(userId="me", id=msg_id).execute()

            pdf_parts = [
                p for p in _iter_parts(msg["payload"])
                if p.get("filename", "").lower().endswith(".pdf")
                or p.get("mimeType") == "application/pdf"
            ]

            if not pdf_parts:
                _mark_read(service, msg_id)
                continue

            message_ok = True
            for part in pdf_parts:
                attachment_id = part["body"].get("attachmentId")
                if not attachment_id:
                    continue

                attachment = service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=attachment_id
                ).execute()
                pdf_data = base64.urlsafe_b64decode(attachment["data"])

                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(pdf_data)
                        tmp_path = tmp.name

                    data = parse_afifly_pdf(tmp_path)
                    rot = upsert_rot(data, db, source_pdf_path=tmp_path)
                    logger.info(
                        f"Gmail : rot n°{data['rot_number']} du {data['rot_date']} "
                        f"— {part.get('filename', 'PDF')} traité (id={rot.id})"
                    )

                except Exception as e:
                    logger.error(
                        f"Gmail : erreur parsing {part.get('filename', 'PDF')} — {e}"
                    )
                    message_ok = False
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            if message_ok:
                _mark_read(service, msg_id)
            else:
                # Conserver non lu + ajouter label PARSING_ERRORS
                if error_label_id is None:
                    error_label_id = _get_or_create_label(service, PARSING_ERROR_LABEL)
                service.users().messages().modify(
                    userId="me", id=msg_id,
                    body={"addLabelIds": [error_label_id]},
                ).execute()
                logger.warning(f"Gmail : message {msg_id} conservé non lu → label {PARSING_ERROR_LABEL}")

    except Exception as e:
        logger.error(f"Gmail poller — erreur inattendue : {e}")
    finally:
        db.close()
