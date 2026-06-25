from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import socket
import ssl
import subprocess
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.config import DATA_DIR
from app.config import EXPORTS_DIR
from app.db.connection import db_session
from app.services.app_logger import get_logger
from app.services.admin_service import authenticate_user
from app.services.attendance_service import save_attendance_day
from app.services.alert_service import get_alert_summary, list_alerts
from app.services.dashboard_service import get_dashboard_summary
from app.services.maintenance_action_service import get_maintenance_action_summary, list_equipment_maintenance
from app.services.monthly_timesheet_service import current_monthly_timesheet_month, get_monthly_10h_timesheet
from app.services.toolbox_talk_service import get_toolbox_topic_for_date
from app.services.accident_service import create_accident
from app.services.secure_config import protect_secret, secret_source_label, unprotect_secret


MOBILE_SYNC_CONFIG_PATH = DATA_DIR / "mobile_sync_config.json"
DEFAULT_PORT = 8765
MAX_REQUEST_BYTES = 1_000_000
MOBILE_SESSION_DAYS = 30
_MAX_LOGIN_ATTEMPTS = 10
_LOGIN_WINDOW = 300.0  # secondes (fenetre glissante)

_LOGIN_FAILURES: dict[str, list[float]] = {}
_LOGIN_LOCK = threading.Lock()
MOBILE_ROLES = {
    "hse": {
        "label": "Officier HSE",
        "capabilities": ["dashboard", "attendance", "toolbox", "maintenance", "alerts", "declare"],
    },
    "supervisor": {
        "label": "Superviseur terrain",
        "capabilities": ["dashboard", "attendance", "toolbox", "maintenance", "alerts", "declare"],
    },
    "attendance": {
        "label": "Agent pointage",
        "capabilities": ["attendance"],
    },
    "maintenance": {
        "label": "Technicien maintenance",
        "capabilities": ["dashboard", "maintenance", "alerts"],
    },
}
LOGGER = get_logger(__name__)

_SERVER: ThreadingHTTPServer | None = None
_SERVER_THREAD: threading.Thread | None = None


class MobileSyncConfigurationError(ValueError):
    pass


def get_mobile_sync_settings() -> dict[str, Any]:
    config = _read_config()
    token = _resolve_token(config)
    host = str(config.get("host") or "0.0.0.0")
    port = _as_port(config.get("port") or DEFAULT_PORT)
    enabled = bool(config.get("enabled", False))
    use_tls = bool(config.get("use_tls", False))
    running = is_mobile_sync_server_running()
    return {
        "enabled": enabled,
        "host": host,
        "port": port,
        "use_tls": use_tls,
        "token_configured": bool(token),
        "token_source": secret_source_label(config.get("token"), "OREZONE_MOBILE_SYNC_TOKEN") if token else "-",
        "running": running,
        "server_url": _server_url(host, port, use_tls) if running or enabled else "",
        "server_urls": _server_urls(host, port, use_tls) if running or enabled else [],
        "config_path": str(MOBILE_SYNC_CONFIG_PATH),
    }


def save_mobile_sync_settings(values: dict[str, Any]) -> dict[str, Any]:
    current = _read_config()
    token = values.get("token")
    generate_token = bool(values.get("generate_token"))
    clear_token = bool(values.get("clear_token"))
    payload = {
        "enabled": bool(values.get("enabled", current.get("enabled", False))),
        "host": str(values.get("host", current.get("host", "0.0.0.0")) or "0.0.0.0").strip(),
        "port": _as_port(values.get("port", current.get("port", DEFAULT_PORT))),
        "use_tls": bool(values.get("use_tls", current.get("use_tls", False))),
        "token": str(current.get("token") or ""),
    }
    if clear_token:
        payload["token"] = ""
    elif generate_token:
        payload["token"] = protect_secret(secrets.token_urlsafe(24))
    elif token is not None and str(token).strip():
        payload["token"] = protect_secret(token)
    MOBILE_SYNC_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    MOBILE_SYNC_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    if payload["enabled"]:
        ensure_mobile_sync_server()
    else:
        stop_mobile_sync_server()
    return get_mobile_sync_settings()


def generate_mobile_pairing_token() -> str:
    token = secrets.token_urlsafe(24)
    save_mobile_sync_settings({"token": token, "enabled": get_mobile_sync_settings()["enabled"]})
    return token


PAIRING_FILE = DATA_DIR / "mobile_pairing_code.txt"


def get_mobile_token_raw() -> str | None:
    """Return the plain token string (for display / sharing). None if not set."""
    token = _resolve_token(_read_config())
    return token if token else None


def get_pairing_compact_code() -> str | None:
    """Return compact base64 JSON pairing code for QR/manual entry."""
    import base64
    settings = get_mobile_sync_settings()
    token = _resolve_token(_read_config())
    url = settings.get("server_url") or ""
    if not token or not url:
        return None
    payload = json.dumps({"u": url, "t": token}, separators=(",", ":"))
    return base64.b64encode(payload.encode()).decode()


def write_pairing_file() -> str | None:
    """Write pairing code to shared file. Both apps on same PC can access it."""
    code = get_pairing_compact_code()
    if not code:
        return None
    PAIRING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PAIRING_FILE.write_text(code, encoding="utf-8")
    return str(PAIRING_FILE)


def generate_pairing_qr_path() -> str | None:
    """Generate QR code PNG saved to disk. Returns absolute path or None."""
    code = get_pairing_compact_code()
    if not code:
        return None
    try:
        import qrcode
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=7,
            border=2,
        )
        qr.add_data(code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0F2E4C", back_color="white")
        out = EXPORTS_DIR / "mobile_pairing_qr.png"
        img.save(str(out))
        return str(out)
    except Exception:
        return None


def create_mobile_pairing_package() -> dict[str, Any]:
    settings = get_mobile_sync_settings()
    token = _resolve_token(_read_config())
    if not token:
        token = generate_mobile_pairing_token()
        settings = get_mobile_sync_settings()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output = EXPORTS_DIR / "orezone_mobile_pairing.json"
    payload = {
        "application": "OREZONE QHSE Mobile",
        "server_url": settings["server_url"],
        "server_urls": settings["server_urls"],
        "token": token,
        "instructions": [
            "Demarrer le serveur mobile dans OREZONE QHSE Admin.",
            "Connecter le telephone au meme Wi-Fi que le PC administrateur.",
            "Entrer server_url et token dans OREZONE QHSE Mobile.",
            "Cliquer Telecharger, puis travailler offline et Synchroniser plus tard.",
        ],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat(timespec="seconds"),
        "security_notice": "Fichier sensible: supprimer apres appairage du telephone.",
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(output), **payload}


def ensure_mobile_sync_server() -> dict[str, Any]:
    settings = get_mobile_sync_settings()
    if not settings["enabled"]:
        return settings
    if not settings["token_configured"]:
        save_mobile_sync_settings({"enabled": True, "generate_token": True})
        settings = get_mobile_sync_settings()
    if is_mobile_sync_server_running():
        return settings
    start_mobile_sync_server()
    return get_mobile_sync_settings()


def start_mobile_sync_server() -> dict[str, Any]:
    global _SERVER, _SERVER_THREAD
    settings = get_mobile_sync_settings()
    if not settings["token_configured"]:
        raise MobileSyncConfigurationError("Genere un token d'appairage avant de demarrer le serveur mobile.")
    if is_mobile_sync_server_running():
        return get_mobile_sync_settings()
    try:
        server = ThreadingHTTPServer((settings["host"], int(settings["port"])), _MobileSyncHandler)
        server.daemon_threads = True
    except OSError as exc:
        raise MobileSyncConfigurationError(f"Impossible de demarrer le serveur mobile: {exc}") from exc
    if settings.get("use_tls"):
        cert = _generate_tls_cert()
        if cert is not None:
            cert_file, key_file = cert
            try:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
                server.socket = ctx.wrap_socket(server.socket, server_side=True)
                LOGGER.info("Mobile sync TLS enabled (self-signed cert)")
            except ssl.SSLError as exc:
                LOGGER.warning("TLS wrapping failed — running without TLS: %s", exc)
        else:
            LOGGER.warning("Mobile sync running without TLS (openssl not available)")
    else:
        LOGGER.warning(
            "Mobile sync server started without TLS on %s:%s — enable 'use_tls' in settings for encryption",
            settings["host"], settings["port"],
        )
    _SERVER = server
    _SERVER_THREAD = threading.Thread(target=server.serve_forever, name="orezone-mobile-sync", daemon=True)
    _SERVER_THREAD.start()
    LOGGER.info("Mobile sync server started on %s:%s", settings["host"], settings["port"])
    return get_mobile_sync_settings()


def stop_mobile_sync_server() -> dict[str, Any]:
    global _SERVER, _SERVER_THREAD
    if _SERVER is not None:
        _SERVER.shutdown()
        _SERVER.server_close()
    _SERVER = None
    _SERVER_THREAD = None
    LOGGER.info("Mobile sync server stopped")
    return get_mobile_sync_settings()


def is_mobile_sync_server_running() -> bool:
    return _SERVER is not None and _SERVER_THREAD is not None and _SERVER_THREAD.is_alive()


def get_mobile_bootstrap(
    date_presence: str | None = None,
    device_id: str | None = None,
    user_role: str | None = None,
) -> dict[str, Any]:
    target_date = str(date_presence or datetime.now().date().isoformat())
    profile = get_mobile_device_profile(device_id)
    if str(user_role or "") == "Administrateur":
        profile = {
            "role": "admin",
            "label": "Administrateur mobile",
            "capabilities": ["dashboard", "attendance", "toolbox", "maintenance", "timesheet", "alerts"],
        }
    capabilities = set(profile["capabilities"])
    with db_session() as connection:
        sites = connection.execute(
            """
            SELECT s.id_site, s.nom, s.localisation, d.nom AS departement
            FROM sites s
            LEFT JOIN departments d ON d.id_department = s.department_id
            WHERE s.actif = 1
            ORDER BY s.nom
            """
        ).fetchall()
        employees = connection.execute(
            """
            SELECT
                e.id_employe,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                e.nom_complet,
                e.type_employe,
                e.site_id,
                s.nom AS site,
                COALESCE(g.nom, '-') AS groupe,
                f.nom AS fonction,
                sh.code AS shift_code,
                b.numero_badge
            FROM employes e
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            JOIN sites s ON s.id_site = e.site_id
            LEFT JOIN groupes g ON g.id_groupe = e.groupe_id
            JOIN shifts sh ON sh.id_shift = e.shift_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
            ORDER BY s.nom, nom, prenom, e.nom_complet
            """
        ).fetchall()
        shifts = connection.execute(
            """
            SELECT shift_code, libelle, heure_entree, heure_sortie
            FROM shift_templates
            WHERE actif = 1
            ORDER BY id_template
            """
        ).fetchall()
        maintenance = connection.execute(
            """
            SELECT
                em.id_maintenance,
                em.equipment_code,
                em.equipment_name,
                em.category,
                em.priority,
                em.status,
                em.planned_date,
                em.next_due_date,
                em.current_odometer,
                em.next_due_odometer,
                s.nom AS site
            FROM equipment_maintenance em
            LEFT JOIN sites s ON s.id_site = em.site_id
            WHERE em.status IN ('planifiee', 'en_cours', 'en_retard')
            ORDER BY
                CASE em.priority WHEN 'critique' THEN 0 WHEN 'haute' THEN 1 WHEN 'moyenne' THEN 2 ELSE 3 END,
                em.planned_date
            LIMIT 100
            """
        ).fetchall()
    try:
        toolbox_topic = get_toolbox_topic_for_date(target_date, auto_assign=True)
    except ValueError:
        toolbox_topic = None
    dashboard = get_dashboard_summary() if "dashboard" in capabilities else {}
    all_open_alerts = list_alerts(statut="ouverte") if "alerts" in capabilities else []
    alerts = all_open_alerts[:20]
    maintenance_plan = list_equipment_maintenance(limit=100) if "maintenance" in capabilities else []
    maintenance_summary = get_maintenance_action_summary() if "maintenance" in capabilities else {}
    timesheet = _mobile_timesheet_summary() if "timesheet" in capabilities else {}
    return {
        "server": "OREZONE QHSE",
        "server_time": datetime.now().isoformat(timespec="seconds"),
        "date_presence": target_date,
        "profile": profile,
        "sites": [dict(row) for row in sites],
        "employees": [dict(row) for row in employees] if "attendance" in capabilities else [],
        "shift_templates": [dict(row) for row in shifts] if "attendance" in capabilities else [],
        "toolbox_topic": (toolbox_topic or {}) if "toolbox" in capabilities else {},
        "maintenance_items": [dict(row) for row in maintenance] if "maintenance" in capabilities else [],
        "maintenance_plan": maintenance_plan,
        "maintenance_summary": maintenance_summary,
        "dashboard": dashboard,
        "alerts": alerts,
        "alert_summary": get_alert_summary(all_open_alerts) if all_open_alerts else {},
        "timesheet": timesheet,
        "drilling_equipment": _drilling_equipment_for_mobile(),
        "offline_rules": {
            "attendance_statuses": ["present", "absent"],
            "maintenance_priorities": ["basse", "moyenne", "haute", "critique"],
            "time_format": "HH:MM",
            "sync_strategy": "Les donnees sont conservees sur telephone puis envoyees au serveur admin.",
        },
    }


def _mobile_timesheet_summary() -> dict[str, Any]:
    data = get_monthly_10h_timesheet(current_monthly_timesheet_month())
    return {
        "period": data["period"],
        "summary": data["summary"],
        "employees": [
            {
                "id_employe": row["employee"]["id_employe"],
                "name": f"{row['employee'].get('nom') or ''} {row['employee'].get('prenom') or ''}".strip(),
                "fonction": row["employee"].get("fonction"),
                "site": row["employee"].get("site"),
                "worked_days": row["worked_days"],
                "unfilled_days": row["unfilled_days"],
                "hours": row["hours"],
            }
            for row in data["rows"][:100]
        ],
    }


def _drilling_equipment_for_mobile() -> list[dict[str, Any]]:
    try:
        from app.services.drilling_service import list_equipment
        return list_equipment(active_only=True)
    except Exception:
        return []


def _apply_drilling_reports(
    device_id: str,
    reports: list[Any],
    operator: str,
    errors: list[str],
) -> tuple[int, list[str]]:
    from app.services.drilling_service import upsert_from_mobile
    applied = 0
    accepted_uuids: list[str] = []
    for item in reports:
        if not isinstance(item, dict):
            continue
        try:
            rep_uuid = str(item.get("uuid") or "")
            if not rep_uuid:
                errors.append("Rapport drilling sans UUID ignoré.")
                continue
            item["created_by"] = operator
            upsert_from_mobile(item)
            applied += 1
            accepted_uuids.append(rep_uuid)
        except Exception as exc:
            errors.append(f"Drilling {item.get('uuid', '?')}: {exc}")
    return applied, accepted_uuids


def apply_mobile_sync_payload(payload: dict[str, Any]) -> dict[str, Any]:
    device_id = _required_text(payload.get("device_id"), "device_id")
    device_name = str(payload.get("device_name") or device_id).strip()[:120]
    attendances = payload.get("attendances") or []
    toolbox_confirmations = payload.get("toolbox_confirmations") or []
    maintenance_observations = payload.get("maintenance_observations") or []
    incidents = payload.get("incidents") or []
    ppe_checks = payload.get("ppe_checks") or []
    observations = payload.get("observations") or []
    drilling_reports = payload.get("drilling_reports") or []
    if not isinstance(attendances, list):
        raise MobileSyncConfigurationError("Le champ attendances doit etre une liste.")
    if not isinstance(toolbox_confirmations, list):
        raise MobileSyncConfigurationError("Le champ toolbox_confirmations doit etre une liste.")
    if not isinstance(maintenance_observations, list):
        raise MobileSyncConfigurationError("Le champ maintenance_observations doit etre une liste.")
    if not isinstance(drilling_reports, list):
        raise MobileSyncConfigurationError("Le champ drilling_reports doit etre une liste.")
    if _device_is_blocked(device_id):
        _record_sync_event(
            device_id,
            "mobile_sync",
            _payload_hash(payload),
            0,
            "rejected",
            "Appareil mobile bloque.",
            str(payload.get("operator") or ""),
        )
        raise MobileSyncConfigurationError("Cet appareil mobile est bloque par l'administrateur.")
    _upsert_device(device_id, device_name)
    capabilities = set(get_mobile_device_profile(device_id)["capabilities"])
    if attendances and "attendance" not in capabilities:
        raise MobileSyncConfigurationError("Ce profil mobile ne peut pas enregistrer les presences.")
    if toolbox_confirmations and "toolbox" not in capabilities:
        raise MobileSyncConfigurationError("Ce profil mobile ne peut pas confirmer les Toolbox Talks.")
    if maintenance_observations and "maintenance" not in capabilities:
        raise MobileSyncConfigurationError("Ce profil mobile ne peut pas creer des observations maintenance.")
    attendance_items: list[dict[str, Any]] = []
    for item in attendances:
        if not isinstance(item, dict):
            continue
        date_presence = _required_text(item.get("date_presence"), "date_presence")
        employee_id = int(item.get("employee_id") or 0)
        if not employee_id:
            raise MobileSyncConfigurationError("employee_id obligatoire dans chaque pointage.")
        attendance_items.append(
            {
                "date_presence": date_presence,
                "employee_id": employee_id,
                "employee_name": str(item.get("employee_name") or "").strip(),
                "local_id": _optional_int(item.get("local_id")),
                "values": {
                    "statut_presence": _attendance_status(item.get("status") or item.get("statut_presence")),
                    "heure_entree": item.get("heure_entree"),
                    "heure_sortie": item.get("heure_sortie"),
                },
            },
        )
    applied = 0
    errors: list[str] = []
    accepted = {"attendance": [], "toolbox": [], "maintenance": []}
    for item in attendance_items:
        try:
            save_attendance_day(
                str(item["date_presence"]),
                {int(item["employee_id"]): item["values"]},
            )
            applied += 1
            if item["local_id"] is not None:
                accepted["attendance"].append(int(item["local_id"]))
        except ValueError as exc:
            label = item["employee_name"] or f"employe #{item['employee_id']}"
            errors.append(f"{item['date_presence']} - {label}: {exc}")
    toolbox_applied, accepted["toolbox"] = _apply_toolbox_confirmations(device_id, toolbox_confirmations, errors)
    maintenance_applied, accepted["maintenance"] = _apply_maintenance_observations(device_id, maintenance_observations, errors)
    incidents_applied, accepted["incidents"] = _apply_mobile_incidents(incidents, payload.get("operator") or "", errors)
    ppe_applied, accepted["ppe_checks"] = _apply_mobile_ppe_checks(ppe_checks, errors)
    obs_applied, accepted["observations"] = _apply_mobile_observations(observations, errors)
    drilling_applied, accepted["drilling_reports"] = _apply_drilling_reports(
        device_id, drilling_reports, str(payload.get("operator") or ""), errors
    )
    status = "applied" if not errors else "error"
    message = "; ".join(errors) if errors else "Synchronisation appliquee."
    records_count = (len(attendances) + len(toolbox_confirmations) + len(maintenance_observations)
                     + len(incidents) + len(ppe_checks) + len(observations) + len(drilling_reports))
    _record_sync_event(
        device_id,
        "mobile_sync",
        _payload_hash(payload),
        records_count,
        status,
        message,
        str(payload.get("operator") or ""),
    )
    return {
        "status": status,
        "applied": applied + toolbox_applied + maintenance_applied + incidents_applied + ppe_applied + obs_applied + drilling_applied,
        "drilling_applied": drilling_applied,
        "attendance_applied": applied,
        "toolbox_applied": toolbox_applied,
        "maintenance_applied": maintenance_applied,
        "incidents_applied": incidents_applied,
        "ppe_checks_applied": ppe_applied,
        "observations_applied": obs_applied,
        "received": records_count,
        "accepted": accepted,
        "errors": errors,
        "server_time": datetime.now().isoformat(timespec="seconds"),
    }


def list_mobile_sync_events(limit: int = 20) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT e.id_event, e.device_id, d.device_name, e.operator_username, e.event_type, e.records_count,
                   e.status, e.message, e.created_at
            FROM mobile_sync_events e
            LEFT JOIN mobile_sync_devices d ON d.device_id = e.device_id
            ORDER BY e.created_at DESC, e.id_event DESC
            LIMIT ?
            """,
            (int(limit or 20),),
        ).fetchall()
    return [dict(row) for row in rows]


def list_mobile_devices(limit: int = 50) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                d.device_id,
                d.device_name,
                d.last_seen_at,
                d.status,
                d.mobile_role,
                d.created_at,
                COUNT(e.id_event) AS sync_count,
                MAX(e.created_at) AS last_sync_at
            FROM mobile_sync_devices d
            LEFT JOIN mobile_sync_events e ON e.device_id = d.device_id
            GROUP BY d.device_id, d.device_name, d.last_seen_at, d.status, d.mobile_role, d.created_at
            ORDER BY COALESCE(d.last_seen_at, d.created_at) DESC
            LIMIT ?
            """,
            (int(limit or 50),),
        ).fetchall()
    return [dict(row) for row in rows]


def update_mobile_device_status(device_id: str, status: str) -> None:
    selected_status = str(status or "").strip()
    if selected_status not in {"active", "blocked"}:
        raise MobileSyncConfigurationError("Statut appareil mobile invalide.")
    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE mobile_sync_devices
            SET status = ?
            WHERE device_id = ?
            """,
            (selected_status, str(device_id or "").strip()),
        )
        if not cursor.rowcount:
            raise MobileSyncConfigurationError("Appareil mobile introuvable.")


def update_mobile_device_role(device_id: str, mobile_role: str) -> None:
    selected_role = str(mobile_role or "").strip()
    if selected_role not in MOBILE_ROLES:
        raise MobileSyncConfigurationError("Role mobile invalide.")
    with db_session() as connection:
        cursor = connection.execute(
            "UPDATE mobile_sync_devices SET mobile_role = ? WHERE device_id = ?",
            (selected_role, str(device_id or "").strip()),
        )
        if not cursor.rowcount:
            raise MobileSyncConfigurationError("Appareil mobile introuvable.")


def get_mobile_device_profile(device_id: str | None) -> dict[str, Any]:
    role = "hse"
    if device_id:
        with db_session() as connection:
            row = connection.execute(
                "SELECT mobile_role FROM mobile_sync_devices WHERE device_id = ?",
                (str(device_id).strip(),),
            ).fetchone()
        if row and str(row["mobile_role"] or "") in MOBILE_ROLES:
            role = str(row["mobile_role"])
    profile = MOBILE_ROLES[role]
    return {"role": role, "label": profile["label"], "capabilities": list(profile["capabilities"])}


def authenticate_mobile_user(device_id: str, username: str, password: str) -> dict[str, Any]:
    clean_device_id = _required_text(device_id, "device_id")[:120]
    user = authenticate_user(username, password)
    if not user:
        raise MobileSyncConfigurationError("Identifiant ou mot de passe incorrect.")
    raw_token = secrets.token_urlsafe(32)
    token_hash = _session_token_hash(raw_token)
    expires_at = datetime.now() + timedelta(days=MOBILE_SESSION_DAYS)
    with db_session() as connection:
        connection.execute(
            "DELETE FROM mobile_user_sessions WHERE device_id = ? OR expires_at <= CURRENT_TIMESTAMP",
            (clean_device_id,),
        )
        connection.execute(
            """
            INSERT INTO mobile_user_sessions(device_id, user_id, token_hash, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (clean_device_id, int(user["id_user"]), token_hash, expires_at.isoformat(timespec="seconds")),
        )
    return {
        "session_token": raw_token,
        "expires_at": expires_at.isoformat(timespec="seconds"),
        "user": {
            "id_user": int(user["id_user"]),
            "username": str(user["username"]),
            "role": str(user["role"]),
        },
    }


def get_mobile_session_identity(device_id: str, session_token: str) -> dict[str, Any]:
    token_hash = _session_token_hash(_required_text(session_token, "session mobile"))
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT u.id_user, u.username, r.nom AS role, s.expires_at
            FROM mobile_user_sessions s
            JOIN utilisateurs u ON u.id_user = s.user_id
            JOIN roles r ON r.id_role = u.role_id
            WHERE s.device_id = ?
              AND s.token_hash = ?
              AND s.expires_at > CURRENT_TIMESTAMP
              AND u.statut = 'actif'
            """,
            (str(device_id or "").strip(), token_hash),
        ).fetchone()
        if row is None:
            raise MobileSyncConfigurationError("Session mobile expiree. Identifie-toi a nouveau.")
        connection.execute(
            "UPDATE mobile_user_sessions SET last_used_at = CURRENT_TIMESTAMP WHERE token_hash = ?",
            (token_hash,),
        )
    return dict(row)


def _generate_tls_cert() -> tuple[Any, Any] | None:
    """Génère un certificat auto-signé via openssl si disponible, retourne (cert, key) paths."""
    cert_dir = DATA_DIR / "ssl"
    cert_file = cert_dir / "server.crt"
    key_file = cert_dir / "server.key"
    if cert_file.exists() and key_file.exists():
        return cert_file, key_file
    try:
        cert_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(key_file),
                "-out", str(cert_file),
                "-days", "3650", "-nodes",
                "-subj", "/CN=OREZONE-QHSE-Mobile/O=OREZONE/C=GN",
            ],
            check=True, capture_output=True, timeout=30,
        )
        LOGGER.info("TLS certificate generated at %s", cert_dir)
        return cert_file, key_file
    except Exception as exc:
        LOGGER.warning("TLS cert generation failed (openssl required) — falling back to HTTP: %s", exc)
        return None


def _is_login_rate_limited(device_id: str) -> bool:
    now = time.monotonic()
    with _LOGIN_LOCK:
        recent = [t for t in _LOGIN_FAILURES.get(device_id, []) if now - t < _LOGIN_WINDOW]
        _LOGIN_FAILURES[device_id] = recent
        return len(recent) >= _MAX_LOGIN_ATTEMPTS


def _record_login_failure(device_id: str) -> None:
    with _LOGIN_LOCK:
        _LOGIN_FAILURES.setdefault(device_id, []).append(time.monotonic())


def _clear_login_failures(device_id: str) -> None:
    with _LOGIN_LOCK:
        _LOGIN_FAILURES.pop(device_id, None)


class _MobileSyncHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/mobile/ping":
                self._send_json({"status": "ok", "server": "OREZONE QHSE", "time": datetime.now().isoformat(timespec="seconds")})
                return
            self._require_token()
            device_id = self._require_device()
            if parsed.path == "/api/mobile/bootstrap":
                identity = self._require_identity(device_id)
                query = parse_qs(parsed.query)
                self._send_json(
                    get_mobile_bootstrap(
                        (query.get("date") or [""])[0] or None,
                        device_id=device_id,
                        user_role=str(identity["role"]),
                    )
                )
                return
            if parsed.path == "/api/mobile/data":
                self._require_identity(device_id)
                query = parse_qs(parsed.query)
                month = (query.get("month") or [""])[0] or datetime.now().strftime("%Y-%m")
                self._send_json(_get_mobile_month_data(month))
                return
            if parsed.path == "/api/mobile/timesheet/export":
                self._require_identity(device_id)
                query = parse_qs(parsed.query)
                month = (query.get("month") or [""])[0] or current_monthly_timesheet_month()
                fmt = (query.get("format") or ["xlsx"])[0].lower()
                ts_type = (query.get("type") or ["1_25"])[0].lower()
                employee_id_raw = (query.get("employee_id") or [""])[0].strip()
                employee_id = int(employee_id_raw) if employee_id_raw.isdigit() else None
                if fmt not in {"xlsx", "pdf"}:
                    self._send_json({"error": "Format non supporte. Utilisez xlsx ou pdf."}, status=400)
                    return
                if ts_type not in {"1_25", "21_20"}:
                    ts_type = "1_25"
                file_bytes, filename = _generate_timesheet_export_bytes(month, fmt, ts_type, employee_id)  # noqa: SLF001
                self._send_file(file_bytes, fmt, filename)
                return
            self._send_json({"error": "Endpoint introuvable."}, status=404)
        except MobileSyncConfigurationError as exc:
            self._send_json({"error": str(exc)}, status=401)
        except Exception as exc:
            LOGGER.exception("Mobile GET failed: %s", exc)
            self._send_json({"error": "Erreur serveur mobile."}, status=500)

    def do_POST(self) -> None:
        try:
            self._require_token()
            device_id = self._require_device()
            parsed = urlparse(self.path)
            if parsed.path == "/api/mobile/login":
                if _is_login_rate_limited(device_id):
                    self._send_json(
                        {"error": "Trop de tentatives de connexion. Patientez 5 minutes."},
                        status=429,
                    )
                    return
                payload = self._read_payload()
                try:
                    result = authenticate_mobile_user(
                        device_id,
                        str(payload.get("username") or ""),
                        str(payload.get("password") or ""),
                    )
                    _clear_login_failures(device_id)
                    self._send_json(result)
                except MobileSyncConfigurationError:
                    _record_login_failure(device_id)
                    raise
                return
            if parsed.path != "/api/mobile/sync":
                self._send_json({"error": "Endpoint introuvable."}, status=404)
                return
            identity = self._require_identity(device_id)
            payload = self._read_payload()
            if str(payload.get("device_id") or "").strip() != device_id:
                raise MobileSyncConfigurationError("Identite appareil incoherente.")
            payload["operator"] = identity["username"]
            self._send_json(apply_mobile_sync_payload(payload))
        except (json.JSONDecodeError, MobileSyncConfigurationError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            LOGGER.exception("Mobile POST failed: %s", exc)
            self._send_json({"error": "Erreur serveur mobile."}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("Mobile sync HTTP | " + format, *args)

    def _require_token(self) -> None:
        token = _resolve_token(_read_config())
        provided = self.headers.get("X-OREZONE-Mobile-Token") or ""
        if not token or not hmac.compare_digest(token, provided):
            raise MobileSyncConfigurationError("Token mobile invalide.")

    def _require_device(self) -> str:
        device_id = _required_text(self.headers.get("X-OREZONE-Device-Id"), "X-OREZONE-Device-Id")[:120]
        device_name = str(self.headers.get("X-OREZONE-Device-Name") or device_id).strip()[:120]
        if _device_is_blocked(device_id):
            raise MobileSyncConfigurationError("Cet appareil mobile est bloque par l'administrateur.")
        _upsert_device(device_id, device_name)
        return device_id

    def _require_identity(self, device_id: str) -> dict[str, Any]:
        return get_mobile_session_identity(
            device_id,
            str(self.headers.get("X-OREZONE-Mobile-Session") or ""),
        )

    def _read_payload(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length") or 0)
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            raise MobileSyncConfigurationError("Taille de requete mobile invalide.")
        payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise MobileSyncConfigurationError("Format de requete mobile invalide.")
        return payload

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, data: bytes, fmt: str, filename: str) -> None:
        if fmt == "xlsx":
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            mime = "application/pdf"
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def _get_mobile_month_data(month: str) -> dict[str, Any]:
    with db_session() as conn:
        attendance = conn.execute(
            """
            SELECT
                e.id_employe AS employee_id,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                p.date_presence,
                p.statut_presence AS status,
                p.heure_entree,
                p.heure_sortie,
                ROUND(p.heures_travaillees, 2) AS heures,
                f.nom AS fonction,
                b.numero_badge,
                e.type_employe,
                sh.code AS shift
            FROM presences p
            JOIN employes e ON e.id_employe = p.employe_id
            LEFT JOIN fonctions f ON f.id_fonction = e.fonction_id
            LEFT JOIN shifts sh ON sh.id_shift = p.shift_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE p.date_presence LIKE ?
            ORDER BY p.date_presence, e.nom, e.prenom
            """,
            (f"{month}%",),
        ).fetchall()
        toolbox = conn.execute(
            """
            SELECT date_theme, theme, facilitateur AS facilitator,
                   nb_participants AS attendees_count, commentaires AS comments
            FROM themes_securite
            WHERE date_theme LIKE ?
            ORDER BY date_theme
            """,
            (f"{month}%",),
        ).fetchall()
    return {
        "month": month,
        "attendance": [dict(r) for r in attendance],
        "toolbox": [dict(r) for r in toolbox],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _generate_timesheet_export_bytes(
    month: str,
    fmt: str,
    ts_type: str = "1_25",
    employee_id: int | None = None,
) -> tuple[bytes, str]:
    suffix = f"_emp{employee_id}" if employee_id else ""
    type_tag = "21_20" if ts_type == "21_20" else "1_25"
    filename = f"timesheet_{month}_{type_tag}{suffix}.{fmt}"
    if fmt == "xlsx":
        from app.services.attendance_export_service import export_monthly_10h_timesheet_xlsx
        path = export_monthly_10h_timesheet_xlsx(month, ts_type=ts_type, employee_id=employee_id)
        return path.read_bytes(), filename
    else:
        return build_timesheet_pdf_bytes(month, ts_type=ts_type, employee_id=employee_id), filename


def build_timesheet_pdf_bytes(month: str, ts_type: str = "1_25", employee_id: int | None = None) -> bytes:
    import io
    from app.services.monthly_timesheet_service import get_monthly_10h_timesheet
    from app.services.timesheet_period_service import TIMESHEET_1_25, TIMESHEET_21_20
    period_type = TIMESHEET_21_20 if ts_type == "21_20" else TIMESHEET_1_25
    try:
        from reportlab.lib import colors as rlc
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        raise ValueError("reportlab non disponible sur le serveur.")

    data_nat = get_monthly_10h_timesheet(month, employee_type="national", ts_type=period_type)
    data_exp = get_monthly_10h_timesheet(month, employee_type="expatriate", ts_type=period_type)
    period = data_nat.get("period") or {}
    summary: dict[str, Any] = {}
    for k in (data_nat.get("summary") or {}):
        summary[k] = (data_nat["summary"].get(k) or 0) + (data_exp.get("summary",{}).get(k) or 0)
    days = data_nat.get("days") or []
    all_rows = (data_nat.get("rows") or []) + (data_exp.get("rows") or [])
    # Filter by employee if requested
    if employee_id:
        rows = [r for r in all_rows if int(r.get("employee",{}).get("id_employe",0)) == employee_id]
    else:
        rows = all_rows
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    buf = io.BytesIO()
    TIT = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=16, leading=19,
                         textColor=rlc.white, alignment=TA_CENTER)
    SUB = ParagraphStyle("S", fontName="Helvetica", fontSize=8, leading=10,
                         textColor=rlc.HexColor("#475569"), alignment=TA_CENTER)
    SML = ParagraphStyle("M", fontName="Helvetica", fontSize=7, leading=8.5,
                         alignment=TA_LEFT)
    HDR = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=7, leading=8.5,
                         textColor=rlc.white, alignment=TA_CENTER)

    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
        leftMargin=9*mm, rightMargin=9*mm, topMargin=9*mm, bottomMargin=10*mm)
    story: list[Any] = []

    hdr_tbl = Table([
        [Paragraph("OREZONE", TIT), Paragraph("OREZONE MONTHLY TIMESHEET", TIT)],
        ["", Paragraph(f"{period.get('label','')} | {period.get('start','')} — {period.get('end','')}", SUB)],
        ["", Paragraph(f"Generated: {generated_at} | Orezone QHSE | Site SYAMA", SUB)],
    ], colWidths=[38*mm, 239*mm])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), rlc.HexColor("#1E3A8A")),
        ("BACKGROUND", (0,1), (0,2), rlc.HexColor("#1E3A8A")),
        ("SPAN", (0,0), (0,2)),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BACKGROUND", (1,1), (1,2), rlc.HexColor("#EFF6FF")),
        ("BOX", (0,0), (-1,-1), 0.8, rlc.HexColor("#1E3A8A")),
        ("INNERGRID", (0,0), (-1,-1), 0.25, rlc.HexColor("#BFDBFE")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 7),
    ]))
    story.extend([hdr_tbl, Spacer(1, 4*mm)])

    met = Table([[
        Paragraph(f"<b>Employés</b><br/>{summary.get('employees',0)}", SUB),
        Paragraph(f"<b>Jours travaillés</b><br/>{summary.get('worked_days',0)}", SUB),
        Paragraph(f"<b>Repos</b><br/>{summary.get('rest_days',0)}", SUB),
        Paragraph(f"<b>Break</b><br/>{summary.get('normal_break_days',0)}", SUB),
        Paragraph(f"<b>Heures totales</b><br/>{summary.get('hours',0)}", SUB),
    ]], colWidths=[55.4*mm]*5)
    met.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), rlc.HexColor("#DBEAFE")),
        ("BACKGROUND", (1,0), (1,0), rlc.HexColor("#DCFCE7")),
        ("BACKGROUND", (2,0), (2,0), rlc.HexColor("#FEF3C7")),
        ("BACKGROUND", (3,0), (3,0), rlc.HexColor("#FEF3C7")),
        ("BACKGROUND", (4,0), (4,0), rlc.HexColor("#EFF6FF")),
        ("BOX", (0,0), (-1,-1), 0.6, rlc.HexColor("#CBD5E1")),
        ("INNERGRID", (0,0), (-1,-1), 0.3, rlc.HexColor("#CBD5E1")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.extend([met, Spacer(1, 4*mm)])

    STATUS_COLORS = {
        "worked": rlc.HexColor("#DCFCE7"),
        "rest": rlc.HexColor("#FEE2E2"),
        "normal_break": rlc.HexColor("#FEF3C7"),
        "absent": rlc.HexColor("#FEE2E2"),
        "permission": rlc.HexColor("#E0E7FF"),
        "sick": rlc.HexColor("#FEE2E2"),
        "annual_break": rlc.HexColor("#EDE9FE"),
        "unfilled": rlc.HexColor("#F1F5F9"),
    }
    day_labels = [str(d.get("day","")) for d in days]
    col_widths = [30*mm, 35*mm] + [max(5*mm, 271*mm/max(len(days),1))]*len(days) + [12*mm]*5
    td = [[Paragraph(lbl, HDR) for lbl in ["MLE", "Employé"] + day_labels + ["T","R","B","A","H"]]]
    tbl_styles = [
        ("BACKGROUND", (0,0), (-1,0), rlc.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0,0), (-1,0), rlc.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 6.5),
        ("GRID", (0,0), (-1,-1), 0.2, rlc.HexColor("#CBD5E1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("ALIGN", (1,0), (1,-1), "LEFT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [rlc.white, rlc.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]
    for ri, row in enumerate(rows, start=1):
        emp = row["employee"]
        name = f"{emp.get('nom') or ''} {emp.get('prenom') or ''}".strip() or str(emp.get("nom_complet") or "-")
        badge = str(emp.get("numero_badge") or emp.get("matricule") or "-")
        cells = row.get("cells") or []
        cell_vals = []
        for ci, cell in enumerate(cells):
            status = str(cell.get("status") or "")
            label = str(cell.get("label") or "")
            cell_vals.append(label or "")
            bg = STATUS_COLORS.get(status.replace("worked_drilling","worked").replace("worked_standard","worked"))
            if bg:
                col_idx = 2 + ci
                tbl_styles.append(("BACKGROUND", (col_idx, ri), (col_idx, ri), bg))
        td.append([badge, Paragraph(name[:28], SML)] + cell_vals + [
            str(row.get("worked_days", 0)),
            str(row.get("rest_days", 0)),
            str(row.get("normal_break_days", 0)),
            str(row.get("absent_days", 0)),
            str(row.get("hours", 0)),
        ])
    att_tbl = Table(td, colWidths=col_widths, repeatRows=1)
    att_tbl.setStyle(TableStyle(tbl_styles))
    story.append(att_tbl)
    story.append(Spacer(1, 5*mm))

    sig = Table([
        ["Prepared by", "Checked by", "Approved by", "QHSE comments"],
        ["Name / Date / Signature", "Name / Date / Signature", "Name / Date / Signature", ""],
    ], colWidths=[55*mm, 55*mm, 55*mm, 112*mm], rowHeights=[8*mm, 17*mm])
    sig.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), rlc.HexColor("#EFF6FF")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.5),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.4, rlc.HexColor("#CBD5E1")),
    ]))
    story.append(sig)

    def _footer(canvas: Any, doc_obj: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(rlc.HexColor("#64748B"))
        canvas.drawString(9*mm, 6*mm, "OREZONE QHSE - Monthly Timesheet")
        canvas.drawRightString(288*mm, 6*mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _upsert_device(device_id: str, device_name: str) -> None:
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO mobile_sync_devices(device_id, device_name, last_seen_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                device_name = excluded.device_name,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (device_id, device_name),
        )


def _device_is_blocked(device_id: str) -> bool:
    with db_session() as connection:
        row = connection.execute(
            "SELECT status FROM mobile_sync_devices WHERE device_id = ?",
            (device_id,),
        ).fetchone()
    return bool(row and row["status"] == "blocked")


def _record_sync_event(
    device_id: str,
    event_type: str,
    payload_hash: str,
    records_count: int,
    status: str,
    message: str,
    operator_username: str = "",
) -> None:
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO mobile_sync_events(
                device_id, operator_username, event_type, payload_hash, records_count, status, message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                str(operator_username or "")[:120] or None,
                event_type,
                payload_hash,
                int(records_count),
                status,
                message[:500],
            ),
        )


def _apply_toolbox_confirmations(device_id: str, rows: list[Any], errors: list[str]) -> tuple[int, list[int]]:
    applied = 0
    accepted_ids: list[int] = []
    with db_session() as connection:
        for item in rows:
            if not isinstance(item, dict):
                continue
            try:
                date_theme = _required_text(item.get("date_theme"), "date_theme")
                theme = str(item.get("theme") or "")[:500]
                facilitator = str(item.get("facilitator") or item.get("facilitateur") or "")[:160]
                site_id = _optional_int(item.get("site_id"))
                attendees_count = max(0, int(item.get("attendees_count") or 0))
                comments = str(item.get("comments") or "")[:1000] or None
                duplicate = connection.execute(
                    """
                    SELECT id_confirmation
                    FROM mobile_toolbox_confirmations
                    WHERE device_id = ?
                      AND date_theme = ?
                      AND COALESCE(theme, '') = ?
                      AND COALESCE(comments, '') = COALESCE(?, '')
                    LIMIT 1
                    """,
                    (device_id, date_theme, theme, comments),
                )
                if duplicate.fetchone() is None:
                    connection.execute(
                        """
                        INSERT INTO mobile_toolbox_confirmations (
                            device_id, date_theme, theme, facilitator, site_id, attendees_count, comments
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (device_id, date_theme, theme, facilitator, site_id, attendees_count, comments),
                    )
                applied += 1
                local_id = _optional_int(item.get("local_id"))
                if local_id is not None:
                    accepted_ids.append(local_id)
            except (ValueError, MobileSyncConfigurationError) as exc:
                errors.append(f"Toolbox: {exc}")
    return applied, accepted_ids


def _apply_maintenance_observations(device_id: str, rows: list[Any], errors: list[str]) -> tuple[int, list[int]]:
    applied = 0
    accepted_ids: list[int] = []
    with db_session() as connection:
        for item in rows:
            if not isinstance(item, dict):
                continue
            try:
                observation_date = _required_text(item.get("observation_date"), "observation_date")
                equipment_label = _required_text(item.get("equipment_label"), "equipment_label")
                observation = _required_text(item.get("observation"), "observation")
                priority = _priority(item.get("priority"))
                site_id = _optional_int(item.get("site_id"))
                duplicate = connection.execute(
                    """
                    SELECT id_observation
                    FROM mobile_maintenance_observations
                    WHERE device_id = ?
                      AND observation_date = ?
                      AND equipment_label = ?
                      AND observation = ?
                    LIMIT 1
                    """,
                    (device_id, observation_date, equipment_label, observation),
                )
                if duplicate.fetchone() is None:
                    action_id = _create_mobile_maintenance_action(
                        connection,
                        observation_date,
                        equipment_label,
                        observation,
                        priority,
                        site_id,
                    )
                    connection.execute(
                        """
                        INSERT INTO mobile_maintenance_observations (
                            device_id, observation_date, equipment_label, site_id, priority, observation, action_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (device_id, observation_date, equipment_label[:180], site_id, priority, observation[:1000], action_id),
                    )
                applied += 1
                local_id = _optional_int(item.get("local_id"))
                if local_id is not None:
                    accepted_ids.append(local_id)
            except (ValueError, MobileSyncConfigurationError) as exc:
                errors.append(f"Maintenance: {exc}")
    return applied, accepted_ids


def _apply_mobile_incidents(
    items: list[dict[str, Any]],
    operator: str,
    errors: list[str],
) -> tuple[int, list[int]]:
    applied = 0
    accepted_ids: list[int] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            date_heure = str(item.get("date_heure") or datetime.now().isoformat(timespec="minutes"))
            date_ev = date_heure[:10] if len(date_heure) >= 10 else datetime.now().date().isoformat()
            heure_ev = date_heure[11:16] if len(date_heure) >= 16 else None
            description = str(item.get("description") or "").strip()
            if not description:
                raise ValueError("description obligatoire.")
            acc_id = create_accident({
                "type_evenement": str(item.get("type_evenement") or "presquaccident"),
                "date_evenement": date_ev,
                "heure_evenement": heure_ev,
                "lieu": str(item.get("lieu") or "")[:200],
                "description": description[:2000],
                "gravite": str(item.get("gravite") or "benin"),
                "employe_id": int(item["employe_id"]) if item.get("employe_id") else None,
                "statut": "ouvert",
                "created_by": operator or "mobile",
            })
            if item.get("action_immediate"):
                from app.services.accident_service import add_action
                add_action(acc_id, {
                    "description": str(item["action_immediate"])[:500],
                    "responsable": operator or "mobile",
                    "statut": "en_cours",
                })
            applied += 1
            local_id = _optional_int(item.get("local_id"))
            if local_id is not None:
                accepted_ids.append(local_id)
        except Exception as exc:
            errors.append(f"Incident mobile: {exc}")
    return applied, accepted_ids


def _apply_mobile_ppe_checks(
    items: list[dict[str, Any]],
    errors: list[str],
) -> tuple[int, list[int]]:
    applied = 0
    accepted_ids: list[int] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            with db_session() as connection:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO mobile_ppe_checks
                    (check_date, employe_name, employe_id, resultats_json, statut_global, observations)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(item.get("check_date") or datetime.now().date().isoformat()),
                        str(item.get("employe_name") or "")[:120],
                        int(item["employe_id"]) if item.get("employe_id") else None,
                        json.dumps(item.get("resultats") or {}, ensure_ascii=False),
                        str(item.get("statut_global") or "conforme"),
                        str(item.get("observations") or "")[:500],
                    ),
                )
            applied += 1
            local_id = _optional_int(item.get("local_id"))
            if local_id is not None:
                accepted_ids.append(local_id)
        except Exception as exc:
            errors.append(f"EPI check mobile: {exc}")
    return applied, accepted_ids


def _apply_mobile_observations(
    items: list[dict[str, Any]],
    errors: list[str],
) -> tuple[int, list[int]]:
    applied = 0
    accepted_ids: list[int] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            description = str(item.get("description") or "").strip()
            if not description:
                raise ValueError("description obligatoire.")
            with db_session() as connection:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO mobile_field_observations
                    (obs_date, lieu, type_obs, description, priorite, action_requise, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(item.get("obs_date") or datetime.now().date().isoformat()),
                        str(item.get("lieu") or "")[:200],
                        str(item.get("type_obs") or "condition_unsafe"),
                        description[:2000],
                        str(item.get("priorite") or "moyenne"),
                        1 if item.get("action_requise") else 0,
                        str(item.get("notes") or "")[:500],
                    ),
                )
            applied += 1
            local_id = _optional_int(item.get("local_id"))
            if local_id is not None:
                accepted_ids.append(local_id)
        except Exception as exc:
            errors.append(f"Observation terrain mobile: {exc}")
    return applied, accepted_ids


def _create_mobile_maintenance_action(
    connection: Any,
    observation_date: str,
    equipment_label: str,
    observation: str,
    priority: str,
    site_id: int | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO action_tracker (
            source, title, description, site_id, priority, status, due_date, progress
        ) VALUES ('Mobile Maintenance', ?, ?, ?, ?, 'ouverte', ?, 0)
        """,
        (
            f"Observation mobile - {equipment_label}"[:180],
            observation[:1000],
            site_id,
            priority,
            observation_date,
        ),
    )
    return int(cursor.lastrowid)


def _read_config() -> dict[str, Any]:
    if not MOBILE_SYNC_CONFIG_PATH.exists():
        return {"enabled": False, "host": "0.0.0.0", "port": DEFAULT_PORT, "token": ""}
    try:
        return json.loads(MOBILE_SYNC_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "host": "0.0.0.0", "port": DEFAULT_PORT, "token": ""}


def _resolve_token(config: dict[str, Any]) -> str:
    import os

    env_token = os.getenv("OREZONE_MOBILE_SYNC_TOKEN")
    if env_token:
        return env_token.strip()
    return unprotect_secret(config.get("token"))


def _server_url(host: str, port: int, use_tls: bool = False) -> str:
    scheme = "https" if use_tls else "http"
    display_host = _local_ip_address() if host in {"0.0.0.0", ""} else host
    return f"{scheme}://{display_host}:{port}"


def _server_urls(host: str, port: int, use_tls: bool = False) -> list[str]:
    scheme = "https" if use_tls else "http"
    if host not in {"0.0.0.0", ""}:
        return [f"{scheme}://{host}:{port}"]
    urls = []
    for ip_address in _local_ip_candidates():
        url = f"{scheme}://{ip_address}:{port}"
        if url not in urls:
            urls.append(url)
    return urls or [f"{scheme}://127.0.0.1:{port}"]


def _local_ip_address() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def _local_ip_candidates() -> list[str]:
    candidates: list[str] = []
    primary = _local_ip_address()
    if primary:
        candidates.append(primary)
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            address = str(info[4][0])
            if address and not address.startswith("127.") and address not in candidates:
                candidates.append(address)
    except OSError:
        pass
    if "127.0.0.1" not in candidates:
        candidates.append("127.0.0.1")
    return candidates


def _as_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Port serveur mobile invalide.") from exc
    if port <= 0 or port > 65535:
        raise ValueError("Port serveur mobile invalide.")
    return port


def _required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise MobileSyncConfigurationError(f"Champ obligatoire: {label}")
    return text


def _attendance_status(value: Any) -> str:
    status = str(value or "").strip()
    if status not in {"present", "absent"}:
        raise MobileSyncConfigurationError("Statut presence mobile invalide.")
    return status


def _priority(value: Any) -> str:
    priority = str(value or "moyenne").strip()
    if priority not in {"basse", "moyenne", "haute", "critique"}:
        raise MobileSyncConfigurationError("Priorite maintenance mobile invalide.")
    return priority


def _optional_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    return int(value)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _session_token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()
