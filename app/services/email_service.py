from __future__ import annotations

import json
import mimetypes
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from app.config import DATA_DIR


EMAIL_CONFIG_PATH = DATA_DIR / "email_config.json"
DEFAULT_SMTP_PORT = 587


class EmailConfigurationError(ValueError):
    pass


def get_email_settings() -> dict[str, Any]:
    config = _read_email_config()
    password = _resolve_password(config)
    recipients = _parse_recipients(config.get("manager_email")) + _parse_recipients(config.get("somisy_email"))
    ready = bool(config.get("enabled")) and bool(config.get("smtp_host")) and bool(config.get("sender_email")) and bool(password) and bool(recipients)
    last_test_status = str(config.get("last_test_status") or "not_tested")
    return {
        "enabled": bool(config.get("enabled", False)),
        "smtp_host": str(config.get("smtp_host") or ""),
        "smtp_port": int(config.get("smtp_port") or DEFAULT_SMTP_PORT),
        "use_tls": bool(config.get("use_tls", True)),
        "sender_email": str(config.get("sender_email") or ""),
        "sender_name": str(config.get("sender_name") or "OREZONE QHSE"),
        "manager_email": str(config.get("manager_email") or ""),
        "somisy_email": str(config.get("somisy_email") or ""),
        "password_configured": bool(password),
        "password_source": "Variable OREZONE_EMAIL_PASSWORD" if os.getenv("OREZONE_EMAIL_PASSWORD") else "Fichier local",
        "ready": ready,
        "operational": ready and last_test_status == "ok",
        "last_test_status": last_test_status,
        "last_test_message": str(config.get("last_test_message") or ""),
        "last_test_at": str(config.get("last_test_at") or ""),
        "config_path": str(EMAIL_CONFIG_PATH),
    }


def save_email_settings(values: dict[str, Any]) -> dict[str, Any]:
    current = _read_email_config()
    smtp_host = str(values.get("smtp_host", current.get("smtp_host", "")) or "").strip()
    sender_email = str(values.get("sender_email", current.get("sender_email", "")) or "").strip()
    manager_email = str(values.get("manager_email", current.get("manager_email", "")) or "").strip()
    somisy_email = str(values.get("somisy_email", current.get("somisy_email", "")) or "").strip()
    password = values.get("password")
    clear_password = bool(values.get("clear_password"))
    changed = any(
        [
            smtp_host != str(current.get("smtp_host") or ""),
            sender_email != str(current.get("sender_email") or ""),
            manager_email != str(current.get("manager_email") or ""),
            somisy_email != str(current.get("somisy_email") or ""),
            clear_password,
            password is not None and bool(str(password).strip()),
        ]
    )
    payload = {
        "enabled": bool(values.get("enabled", current.get("enabled", False))),
        "smtp_host": smtp_host,
        "smtp_port": _as_port(values.get("smtp_port", current.get("smtp_port", DEFAULT_SMTP_PORT))),
        "use_tls": bool(values.get("use_tls", current.get("use_tls", True))),
        "sender_email": sender_email,
        "sender_name": str(values.get("sender_name", current.get("sender_name", "OREZONE QHSE")) or "OREZONE QHSE").strip(),
        "manager_email": manager_email,
        "somisy_email": somisy_email,
        "last_test_status": "not_tested" if changed else str(current.get("last_test_status") or "not_tested"),
        "last_test_message": "" if changed else str(current.get("last_test_message") or ""),
        "last_test_at": "" if changed else str(current.get("last_test_at") or ""),
    }
    if clear_password:
        payload["password"] = ""
    elif password is not None and str(password).strip():
        payload["password"] = str(password).strip()
    else:
        payload["password"] = str(current.get("password") or "")
    EMAIL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    EMAIL_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return get_email_settings()


def record_email_test_status(status: str, message: str) -> dict[str, Any]:
    config = _read_email_config()
    config["last_test_status"] = str(status or "error")
    config["last_test_message"] = str(message or "")[:500]
    config["last_test_at"] = datetime.now().isoformat(timespec="seconds")
    EMAIL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    EMAIL_CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
    return get_email_settings()


def test_email_connection() -> str:
    settings = get_email_settings()
    _validate_ready(settings)
    _open_smtp(settings).quit()
    return "Connexion email operationnelle."


def send_timesheet_email(timesheet_type: str, month: str, attachment_path: Path | str, site_label: str | None = None) -> dict[str, Any]:
    settings = get_email_settings()
    _validate_ready(settings)
    attachment = Path(attachment_path)
    if not attachment.exists():
        raise EmailConfigurationError(f"Fichier introuvable: {attachment}")
    recipients = _configured_recipients(settings)
    subject = f"OREZONE QHSE - {timesheet_type} - {month}"
    if site_label:
        subject = f"{subject} - {site_label}"
    body = (
        "Bonjour,\n\n"
        f"Veuillez trouver ci-joint le {timesheet_type} du mois {month}.\n\n"
        "Ce fichier a ete genere automatiquement depuis l'application OREZONE QHSE.\n"
        "Merci de verifier et confirmer la reception.\n\n"
        "Cordialement,\nOREZONE QHSE"
    )
    send_email_with_attachments(subject, body, recipients, [attachment])
    return {"recipients": recipients, "attachment": str(attachment)}


def send_email_with_attachments(subject: str, body: str, recipients: list[str], attachments: list[Path]) -> None:
    settings = get_email_settings()
    _validate_ready(settings)
    clean_recipients = _dedupe_recipients(recipients)
    if not clean_recipients:
        raise EmailConfigurationError("Aucun destinataire email configure.")
    message = EmailMessage()
    sender_name = settings["sender_name"]
    sender_email = settings["sender_email"]
    message["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
    message["To"] = ", ".join(clean_recipients)
    message["Subject"] = subject
    message.set_content(body)
    for attachment in attachments:
        _attach_file(message, attachment)
    smtp = _open_smtp(settings)
    try:
        smtp.send_message(message)
    finally:
        smtp.quit()


def _open_smtp(settings: dict[str, Any]) -> smtplib.SMTP:
    try:
        smtp = smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"]), timeout=25)
        if settings["use_tls"]:
            smtp.starttls()
        smtp.login(settings["sender_email"], _resolve_password(_read_email_config()))
        return smtp
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailConfigurationError(f"Connexion email impossible: {exc}") from exc


def _attach_file(message: EmailMessage, path: Path) -> None:
    mime_type, _ = mimetypes.guess_type(path.name)
    maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
    message.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)


def _configured_recipients(settings: dict[str, Any]) -> list[str]:
    return _dedupe_recipients(_parse_recipients(settings.get("manager_email")) + _parse_recipients(settings.get("somisy_email")))


def _dedupe_recipients(recipients: list[str]) -> list[str]:
    seen: set[str] = set()
    clean: list[str] = []
    for recipient in recipients:
        lowered = recipient.strip().lower()
        if not lowered or lowered in seen:
            continue
        seen.add(lowered)
        clean.append(recipient.strip())
    return clean


def _parse_recipients(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(";", ",").split(",") if item.strip()]


def _validate_ready(settings: dict[str, Any]) -> None:
    if not settings["enabled"]:
        raise EmailConfigurationError("Active l'envoi email dans Parametres.")
    if not settings["smtp_host"] or not settings["sender_email"]:
        raise EmailConfigurationError("Configure le serveur SMTP et l'email expediteur.")
    if not settings["password_configured"]:
        raise EmailConfigurationError("Configure le mot de passe email ou app password.")
    if not _configured_recipients(settings):
        raise EmailConfigurationError("Configure au moins l'email du manager ou de SOMISY.")


def _read_email_config() -> dict[str, Any]:
    if not EMAIL_CONFIG_PATH.exists():
        return {
            "enabled": False,
            "smtp_host": "",
            "smtp_port": DEFAULT_SMTP_PORT,
            "use_tls": True,
            "sender_email": "",
            "sender_name": "OREZONE QHSE",
            "manager_email": "",
            "somisy_email": "",
            "password": "",
        }
    try:
        return json.loads(EMAIL_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _resolve_password(config: dict[str, Any]) -> str:
    return str(os.getenv("OREZONE_EMAIL_PASSWORD") or config.get("password") or "").strip()


def _as_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Port SMTP invalide.") from exc
    if port <= 0 or port > 65535:
        raise ValueError("Port SMTP invalide.")
    return port
