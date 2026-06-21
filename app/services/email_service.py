from __future__ import annotations

import json
import mimetypes
import os
import smtplib
import subprocess
import tempfile
import urllib.parse
import webbrowser
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from app.config import DATA_DIR
from app.services.app_logger import get_logger
from app.services.audit_service import record_system_audit
from app.services.secure_config import is_protected_secret, protect_secret, secret_source_label, unprotect_secret


EMAIL_CONFIG_PATH = DATA_DIR / "email_config.json"
DEFAULT_SMTP_PORT = 587
LOGGER = get_logger(__name__)


class EmailConfigurationError(ValueError):
    pass


def get_email_settings() -> dict[str, Any]:
    config = _read_email_config()
    _migrate_local_password(config)
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
        "manager_whatsapp": str(config.get("manager_whatsapp") or ""),
        "somisy_whatsapp": str(config.get("somisy_whatsapp") or ""),
        "whatsapp_group_link": str(config.get("whatsapp_group_link") or ""),
        "password_configured": bool(password),
        "password_source": secret_source_label(config.get("password"), "OREZONE_EMAIL_PASSWORD"),
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
    manager_whatsapp = _clean_phone(values.get("manager_whatsapp", current.get("manager_whatsapp", "")))
    somisy_whatsapp = _clean_phone(values.get("somisy_whatsapp", current.get("somisy_whatsapp", "")))
    whatsapp_group_link = str(values.get("whatsapp_group_link", current.get("whatsapp_group_link", "")) or "").strip()
    password = values.get("password")
    clear_password = bool(values.get("clear_password"))
    changed = any(
        [
            smtp_host != str(current.get("smtp_host") or ""),
            sender_email != str(current.get("sender_email") or ""),
            manager_email != str(current.get("manager_email") or ""),
            somisy_email != str(current.get("somisy_email") or ""),
            manager_whatsapp != str(current.get("manager_whatsapp") or ""),
            somisy_whatsapp != str(current.get("somisy_whatsapp") or ""),
            whatsapp_group_link != str(current.get("whatsapp_group_link") or ""),
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
        "manager_whatsapp": manager_whatsapp,
        "somisy_whatsapp": somisy_whatsapp,
        "whatsapp_group_link": whatsapp_group_link,
        "last_test_status": "not_tested" if changed else str(current.get("last_test_status") or "not_tested"),
        "last_test_message": "" if changed else str(current.get("last_test_message") or ""),
        "last_test_at": "" if changed else str(current.get("last_test_at") or ""),
    }
    if clear_password:
        payload["password"] = ""
    elif password is not None and str(password).strip():
        payload["password"] = protect_secret(password)
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
    LOGGER.info("Timesheet email sent | type=%s month=%s site=%s recipients=%s attachment=%s", timesheet_type, month, site_label or "-", ",".join(recipients), attachment.name)
    record_system_audit("send_timesheet_email", "communication", f"{timesheet_type}:{month}", f"recipients={','.join(recipients)};attachment={attachment.name};site={site_label or '-'}")
    return {"recipients": recipients, "attachment": str(attachment)}


def prepare_timesheet_outlook_draft(timesheet_type: str, month: str, attachment_path: Path | str, site_label: str | None = None) -> dict[str, Any]:
    settings = get_email_settings()
    recipients = _configured_recipients(settings)
    if not recipients:
        raise EmailConfigurationError("Configure au moins l'email du manager ou de SOMISY dans Parametres.")
    attachment = Path(attachment_path)
    if not attachment.exists():
        raise EmailConfigurationError(f"Fichier introuvable: {attachment}")
    subject = f"OREZONE QHSE - {timesheet_type} - {month}"
    if site_label:
        subject = f"{subject} - {site_label}"
    body = (
        "Bonjour,\r\n\r\n"
        f"Veuillez trouver ci-joint le {timesheet_type} du mois {month}.\r\n\r\n"
        "Ce fichier a ete genere automatiquement depuis l'application OREZONE QHSE.\r\n"
        "Merci de verifier et confirmer la reception.\r\n\r\n"
        "Cordialement,\r\nOREZONE QHSE"
    )
    _open_outlook_draft(recipients, subject, body, attachment)
    LOGGER.info("Outlook draft prepared | type=%s month=%s site=%s recipients=%s attachment=%s", timesheet_type, month, site_label or "-", ",".join(recipients), attachment.name)
    record_system_audit("prepare_outlook_draft", "communication", f"{timesheet_type}:{month}", f"recipients={','.join(recipients)};attachment={attachment.name};site={site_label or '-'}")
    return {"recipients": recipients, "attachment": str(attachment)}


def prepare_timesheet_whatsapp_share(timesheet_type: str, month: str, attachment_path: Path | str, site_label: str | None = None) -> dict[str, Any]:
    settings = get_email_settings()
    attachment = Path(attachment_path)
    if not attachment.exists():
        raise EmailConfigurationError(f"Fichier introuvable: {attachment}")
    targets = _configured_whatsapp_targets(settings)
    if not targets:
        raise EmailConfigurationError("Configure au moins un numero WhatsApp ou un lien groupe WhatsApp dans Parametres.")
    message = (
        f"Bonjour, le {timesheet_type} du mois {month}"
        f"{' - ' + site_label if site_label else ''} est pret.\n\n"
        f"Fichier Excel genere: {attachment.name}\n\n"
        "Merci de verifier et confirmer la reception. Le fichier doit etre joint manuellement depuis le dossier exports."
    )
    urls = _open_whatsapp_targets(targets, message)
    LOGGER.info("WhatsApp share opened | type=%s month=%s site=%s targets=%s attachment=%s", timesheet_type, month, site_label or "-", ",".join(targets), attachment.name)
    record_system_audit("open_whatsapp_share", "communication", f"{timesheet_type}:{month}", f"targets={','.join(targets)};attachment={attachment.name};site={site_label or '-'}")
    return {"targets": targets, "attachment": str(attachment), "urls": urls}


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


def _open_outlook_draft(recipients: list[str], subject: str, body: str, attachment: Path) -> None:
    # Arguments are serialized to a JSON file so no user-controlled value ever
    # reaches the PowerShell CLI, preventing metacharacter injection.
    script = """
param([string]$ParamsFile)
$ErrorActionPreference = 'Stop'
$params = Get-Content -LiteralPath $ParamsFile -Raw | ConvertFrom-Json
Remove-Item -LiteralPath $ParamsFile -Force -ErrorAction SilentlyContinue
$outlook = $null
$mail = $null
try {
    $outlook = New-Object -ComObject Outlook.Application
    $mail = $outlook.CreateItem(0)
    $mail.To = $params.To
    $mail.Subject = $params.Subject
    $mail.Body = $params.Body
    $null = $mail.Attachments.Add($params.AttachmentPath)
    $mail.Display($false)
    Start-Sleep -Milliseconds 800
}
finally {
    if ($mail -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($mail)
    }
    if ($outlook -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($outlook)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
}
"""
    script_path: Path | None = None
    params_path: Path | None = None
    try:
        params = {
            "To": "; ".join(recipients),
            "Subject": subject,
            "Body": body,
            "AttachmentPath": str(attachment.resolve()),
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as pf:
            json.dump(params, pf, ensure_ascii=False)
            params_path = Path(pf.name)
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as handle:
            handle.write(script)
            script_path = Path(handle.name)
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(params_path),
            ],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        if params_path is not None:
            params_path.unlink(missing_ok=True)
        if script_path is not None:
            script_path.unlink(missing_ok=True)
        raise EmailConfigurationError(f"Impossible d'ouvrir Outlook: {exc}") from exc


def _open_smtp(settings: dict[str, Any]) -> smtplib.SMTP:
    try:
        smtp = smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"]), timeout=25)
        if settings["use_tls"]:
            smtp.starttls()
        smtp.login(settings["sender_email"], _resolve_password(_read_email_config()))
        return smtp
    except (OSError, smtplib.SMTPException) as exc:
        LOGGER.warning("SMTP connection failed: %s", exc)
        raise EmailConfigurationError(_friendly_smtp_error(exc)) from exc


def _attach_file(message: EmailMessage, path: Path) -> None:
    mime_type, _ = mimetypes.guess_type(path.name)
    maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
    message.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)


def _configured_recipients(settings: dict[str, Any]) -> list[str]:
    return _dedupe_recipients(_parse_recipients(settings.get("manager_email")) + _parse_recipients(settings.get("somisy_email")))


def _configured_whatsapp_targets(settings: dict[str, Any]) -> list[str]:
    values = [
        str(settings.get("manager_whatsapp") or "").strip(),
        str(settings.get("somisy_whatsapp") or "").strip(),
        str(settings.get("whatsapp_group_link") or "").strip(),
    ]
    return _dedupe_recipients([value for value in values if value])


def _open_whatsapp_targets(targets: list[str], message: str) -> list[str]:
    urls: list[str] = []
    encoded = urllib.parse.quote(message)
    for target in targets:
        if target.startswith(("http://", "https://")):
            separator = "&" if "?" in target else "?"
            url = f"{target}{separator}text={encoded}" if "wa.me" in target or "api.whatsapp.com" in target else target
        else:
            url = f"https://wa.me/{_clean_phone(target)}?text={encoded}"
        webbrowser.open(url)
        urls.append(url)
    return urls


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


def _is_valid_email(address: str) -> bool:
    at = address.rfind("@")
    if at <= 0:
        return False
    domain = address[at + 1:]
    return bool(domain) and "." in domain and not domain.startswith(".")


def _parse_recipients(value: Any) -> list[str]:
    candidates = [item.strip() for item in str(value or "").replace(";", ",").split(",") if item.strip()]
    valid = [addr for addr in candidates if _is_valid_email(addr)]
    invalid = [addr for addr in candidates if addr not in valid]
    if invalid:
        LOGGER.warning("Invalid email addresses skipped: %s", invalid)
    return valid


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
            "manager_whatsapp": "",
            "somisy_whatsapp": "",
            "whatsapp_group_link": "",
            "password": "",
        }
    try:
        return json.loads(EMAIL_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _resolve_password(config: dict[str, Any]) -> str:
    env_password = os.getenv("OREZONE_EMAIL_PASSWORD")
    if env_password:
        return env_password.strip()
    return unprotect_secret(config.get("password"))


def _migrate_local_password(config: dict[str, Any]) -> None:
    raw_password = str(config.get("password") or "").strip()
    if not raw_password or is_protected_secret(raw_password):
        return
    try:
        config["password"] = protect_secret(raw_password)
        EMAIL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        EMAIL_CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
    except OSError as exc:
        LOGGER.warning("Email password migration failed: %s", exc)


def _as_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Port SMTP invalide.") from exc
    if port <= 0 or port > 65535:
        raise ValueError("Port SMTP invalide.")
    return port


def _clean_phone(value: Any) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def _friendly_smtp_error(exc: BaseException) -> str:
    text = str(exc)
    lowered = text.lower()
    if "authentication unsuccessful" in lowered or "535" in lowered:
        return (
            "Authentification email refusee. Pour Gmail, utilise un mot de passe d'application. "
            "Pour Outlook/Office 365, verifie que SMTP AUTH est autorise ou utilise le bouton Outlook."
        )
    if "timed out" in lowered or "timeout" in lowered:
        return "Connexion email trop lente ou bloquee. Verifie internet, le serveur SMTP et le pare-feu."
    if "name or service" in lowered or "getaddrinfo" in lowered:
        return "Serveur SMTP introuvable. Verifie l'adresse du serveur dans Parametres."
    return "Connexion email impossible. Le detail technique a ete enregistre dans les journaux."
