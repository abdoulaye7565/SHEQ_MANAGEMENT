from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.app_logger import get_logger
from app.services.audit_service import record_system_audit
from app.services.email_service import (
    EmailConfigurationError,
    _configured_recipients,
    _configured_whatsapp_targets,
    _open_outlook_draft,
    _open_whatsapp_targets,
    get_email_settings,
    send_email_with_attachments,
)

_LOGGER = get_logger(__name__)


def get_share_channels() -> dict[str, Any]:
    """Return availability and default targets for each sharing channel."""
    settings = get_email_settings()
    email_recips = _configured_recipients(settings)
    wa_targets = _configured_whatsapp_targets(settings)
    return {
        "email": {
            "available": settings["ready"],
            "recipients": email_recips,
            "hint": "" if settings["ready"] else "Configurer SMTP dans Paramètres → Email",
        },
        "outlook": {
            "available": bool(email_recips),
            "recipients": email_recips,
            "hint": "" if email_recips else "Configurer un destinataire email dans Paramètres",
        },
        "whatsapp": {
            "available": bool(wa_targets),
            "targets": wa_targets,
            "hint": "" if wa_targets else "Configurer un numéro WhatsApp dans Paramètres",
        },
    }


def share_document_email(
    file_path: Path | str,
    subject: str,
    body: str,
    recipients: list[str] | None = None,
) -> dict[str, Any]:
    """Send any document as SMTP email attachment."""
    path = Path(file_path)
    if not path.exists():
        raise EmailConfigurationError(f"Fichier introuvable : {path.name}")
    settings = get_email_settings()
    used = recipients if recipients is not None else _configured_recipients(settings)
    if not used:
        raise EmailConfigurationError("Aucun destinataire email configuré (voir Paramètres).")
    send_email_with_attachments(subject, body, used, [path])
    _LOGGER.info("share_document_email file=%s recipients=%s", path.name, ",".join(used))
    record_system_audit(
        "share_document_email", "communication", path.name,
        f"recipients={','.join(used)};subject={subject}",
    )
    return {"channel": "email", "recipients": used, "attachment": str(path)}


def share_document_outlook(
    file_path: Path | str,
    subject: str,
    body: str,
    recipients: list[str] | None = None,
) -> dict[str, Any]:
    """Open an Outlook draft with any document pre-attached."""
    path = Path(file_path)
    if not path.exists():
        raise EmailConfigurationError(f"Fichier introuvable : {path.name}")
    settings = get_email_settings()
    used = recipients if recipients is not None else _configured_recipients(settings)
    if not used:
        raise EmailConfigurationError("Aucun destinataire email configuré (voir Paramètres).")
    _open_outlook_draft(used, subject, body, path)
    _LOGGER.info("share_document_outlook file=%s recipients=%s", path.name, ",".join(used))
    record_system_audit(
        "share_document_outlook", "communication", path.name,
        f"recipients={','.join(used)};subject={subject}",
    )
    return {"channel": "outlook", "recipients": used, "attachment": str(path)}


def share_document_whatsapp(
    file_path: Path | str,
    message: str,
    targets: list[str] | None = None,
) -> dict[str, Any]:
    """Open WhatsApp Web with a pre-filled message for any document."""
    path = Path(file_path)
    if not path.exists():
        raise EmailConfigurationError(f"Fichier introuvable : {path.name}")
    settings = get_email_settings()
    used = targets if targets is not None else _configured_whatsapp_targets(settings)
    if not used:
        raise EmailConfigurationError(
            "Aucun numéro ou lien groupe WhatsApp configuré (voir Paramètres)."
        )
    urls = _open_whatsapp_targets(used, message)
    _LOGGER.info("share_document_whatsapp file=%s targets=%s", path.name, ",".join(used))
    record_system_audit(
        "share_document_whatsapp", "communication", path.name,
        f"targets={','.join(used)};file={path.name}",
    )
    return {"channel": "whatsapp", "targets": used, "attachment": str(path), "urls": urls}
