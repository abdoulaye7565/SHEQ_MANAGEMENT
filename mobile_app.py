from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import flet as ft


# ─── Config ───────────────────────────────────────────────────────────────────

def resolve_mobile_dir() -> Path:
    app_storage = str(os.getenv("FLET_APP_STORAGE_DATA") or "").strip()
    if app_storage:
        return Path(app_storage) / "OREZONE_QHSE_MOBILE"
    try:
        return Path.home() / "OREZONE_QHSE_MOBILE"
    except RuntimeError:
        return Path.cwd() / "OREZONE_QHSE_MOBILE"


MOBILE_DIR = resolve_mobile_dir()
MOBILE_DB  = MOBILE_DIR / "mobile_offline.db"

def _u(ctrl) -> None:
    """Safe update — no-op if control is not yet attached to a page."""
    try:
        ctrl.update()
    except (RuntimeError, AssertionError):
        pass


# ─── Design Tokens ────────────────────────────────────────────────────────────

# Login / dark
L_BG     = "#0A1929"
L_CARD   = "#132337"
L_BORDER = "#1E3A5F"
L_TEXT   = "#E2E8F0"
L_MUTED  = "#64748B"

# App / light
A_BG     = "#F4F7FB"
A_CARD   = "#FFFFFF"
A_BORDER = "#E2E8F0"
A_MUTED  = "#64748B"
A_TEXT   = "#0F172A"
A_TEXT2  = "#334155"
A_PRIMARY = "#2563EB"
A_PRIMARY_SOFT = "#EFF6FF"

# Status
OK      = "#16A34A"
WARN    = "#D97706"
DANGER  = "#DC2626"
INFO    = "#0891B2"
PURPLE  = "#7C3AED"

OK_BG   = "#DCFCE7"
WARN_BG = "#FEF3C7"
DNG_BG  = "#FEE2E2"
INF_BG  = "#E0F2FE"

# Equipment icons by keyword
_EQUIP_ICONS: dict[str, str] = {
    "truck": ft.Icons.LOCAL_SHIPPING_OUTLINED,
    "water": ft.Icons.WATER_DROP_OUTLINED,
    "excavat": ft.Icons.AGRICULTURE_OUTLINED,
    "foreuse": ft.Icons.CONSTRUCTION_OUTLINED,
    "bulldoz": ft.Icons.CONSTRUCTION_OUTLINED,
    "vehicle": ft.Icons.DIRECTIONS_CAR_OUTLINED,
    "gen": ft.Icons.ELECTRICAL_SERVICES_OUTLINED,
    "pompe": ft.Icons.WATER_OUTLINED,
    "crane": ft.Icons.PRECISION_MANUFACTURING_OUTLINED,
}

def _equip_icon(label: str) -> str:
    low = label.lower()
    for kw, ico in _EQUIP_ICONS.items():
        if kw in low:
            return ico
    return ft.Icons.BUILD_OUTLINED

# PPE catalogue
PPE_CATALOGUE = [
    ("Casque",          ft.Icons.SAFETY_CHECK_OUTLINED,       OK),
    ("Gants",           ft.Icons.BACK_HAND_OUTLINED,          A_PRIMARY),
    ("Lunettes",        ft.Icons.VISIBILITY_OUTLINED,         WARN),
    ("Chaussures",      ft.Icons.HIKING_OUTLINED,             PURPLE),
    ("Gilet HV",        ft.Icons.CHECKROOM_OUTLINED,          INFO),
    ("Harnais",         ft.Icons.AIRLINE_SEAT_RECLINE_NORMAL_OUTLINED, DANGER),
    ("Masque",          ft.Icons.MASKS_OUTLINED,              A_TEXT2),
    ("Protection aud.", ft.Icons.HEARING_OUTLINED,             WARN),
]

INSPECTION_ITEMS = [
    "Pneus", "Freins", "Feux", "Huile moteur", "Fuite",
    "Batterie", "Climatisation", "Extincteur", "Triangle",
]

GRAVITE_COLORS  = {"benin": OK, "mineur": A_PRIMARY, "majeur": WARN, "grave": DANGER, "fatal": PURPLE}
GRAVITE_LABELS  = {"benin": "Bénin", "mineur": "Mineur", "majeur": "Majeur", "grave": "Grave", "fatal": "Fatal"}
TYPE_INC_COLORS = {"accident": DANGER, "presqu_accident": WARN, "situation_dangereuse": WARN}
TYPE_INC_LABELS = {"accident": "Accident", "presqu_accident": "Presqu'accident", "situation_dangereuse": "Situation dangereuse"}
OBS_COLORS      = {"acte_unsafe": DANGER, "condition_unsafe": WARN, "bonne_pratique": OK, "presqu_accident": WARN}
OBS_LABELS      = {"acte_unsafe": "Acte dangereux", "condition_unsafe": "Condition dangereuse", "bonne_pratique": "Bonne pratique", "presqu_accident": "Presqu'accident"}
PRIO_COLORS     = {"basse": OK, "moyenne": WARN, "haute": DANGER, "critique": PURPLE}
PRIO_LABELS     = {"basse": "Basse", "moyenne": "Moyenne", "haute": "Haute", "critique": "Critique"}

# ── GMAO Maintenance — labels/icons only (no dark-theme colors here) ──────────
TYPE_PANNE_LABELS = {
    "mecanique":  "Mécanique",   "electrique":  "Électrique",
    "hydraulique":"Hydraulique", "pneumatique": "Pneumatique",
    "moteur":     "Moteur/Trans.","operateur":  "Opérateur",
    "structure":  "Structure",   "autre":       "Autre",
}
TYPE_PANNE_ICONS = {
    "mecanique":  ft.Icons.SETTINGS_ROUNDED,       "electrique":  ft.Icons.BOLT_ROUNDED,
    "hydraulique":ft.Icons.WATER_DROP_ROUNDED,     "pneumatique": ft.Icons.AIR_ROUNDED,
    "moteur":     ft.Icons.DIRECTIONS_CAR_ROUNDED, "operateur":   ft.Icons.PERSON_ROUNDED,
    "structure":  ft.Icons.FOUNDATION_ROUNDED,     "autre":       ft.Icons.HELP_OUTLINE_ROUNDED,
}
IMPACT_PRIO = {"arret_total":"critique","partiel":"haute","degrade":"moyenne","aucun":"basse"}
STATUT_OT_LABELS = {
    "ouvert":"Ouvert","en_cours":"En cours",
    "attente_pieces":"Attente pièces","termine":"Terminé",
}
CAUSE_RACINE_OPTS = [
    "Usure normale","Défaut fabrication","Maintenance insuffisante","Surcharge",
    "Mauvaise utilisation","Corrosion/Oxydation","Choc/Impact","Défaut lubrification",
    "Surchauffe","Panne électrique","Panne hydraulique","Cause inconnue",
]

# ── OT Workflow ────────────────────────────────────────────────────────────────
OT_WORKFLOW = [
    ("signale",        "Signalé",        "#06B6D4", ft.Icons.NOTIFICATIONS_ROUNDED),
    ("ouvert",         "Ouvert",         "#3B82F6", ft.Icons.ASSIGNMENT_ROUNDED),
    ("en_cours",       "En cours",       "#F59E0B", ft.Icons.BUILD_ROUNDED),
    ("attente_pieces", "Attente pièces", "#8B5CF6", ft.Icons.INVENTORY_2_ROUNDED),
    ("termine",        "Terminé",        "#10B981", ft.Icons.CHECK_CIRCLE_ROUNDED),
    ("verifie",        "Vérifié",        "#16A34A", ft.Icons.VERIFIED_ROUNDED),
]
OT_WF_DICT   = {k: (l, c, i) for k, l, c, i in OT_WORKFLOW}
OT_TRANSITIONS = {
    "signale":        ["ouvert"],
    "ouvert":         ["en_cours", "attente_pieces"],
    "en_cours":       ["attente_pieces", "termine"],
    "attente_pieces": ["en_cours", "termine"],
    "termine":        ["verifie", "en_cours"],
    "verifie":        [],
}
# Délai critique par priorité (heures)
OT_DELAI_H   = {"critique": 4, "haute": 24, "moyenne": 72, "basse": 168}
PPE_ITEMS = [
    ("Casque de sécurité",      ft.Icons.SAFETY_CHECK_OUTLINED),
    ("Lunettes de protection",  ft.Icons.VISIBILITY_OUTLINED),
    ("Gants de protection",     ft.Icons.BACK_HAND_OUTLINED),
    ("Chaussures de sécurité", ft.Icons.HIKING_OUTLINED),
    ("Gilet haute visibilité",  ft.Icons.CHECKROOM_OUTLINED),
    ("Harnais antichute",       ft.Icons.AIRLINE_SEAT_RECLINE_NORMAL_OUTLINED),
    ("Masque / respirateur",    ft.Icons.MASKS_OUTLINED),
    ("Protection auditive",     ft.Icons.HEARING_OUTLINED),
]


# ─── DB Schema ────────────────────────────────────────────────────────────────

def normalize_server_url(value: Any) -> str:
    return "".join(str(value or "").split()).rstrip("/")


def get_mobile_connection() -> "sqlite3.Connection":
    import sqlite3 as sqlite3  # lazy import — sqlite3 may not be available at module level on Android
    MOBILE_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(MOBILE_DB), timeout=15)
    con.row_factory = sqlite3.Row
    con.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS employees (
            id_employe INTEGER PRIMARY KEY, nom TEXT, prenom TEXT, nom_complet TEXT,
            fonction TEXT, site TEXT, groupe TEXT, numero_badge TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pending_attendance (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL, employee_name TEXT,
            date_presence TEXT NOT NULL, status TEXT NOT NULL,
            heure_entree TEXT, heure_sortie TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS toolbox_cache (
            date_theme TEXT PRIMARY KEY, theme TEXT, facilitator TEXT, site_id INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS maintenance_cache (
            id_maintenance INTEGER PRIMARY KEY, equipment_label TEXT, site TEXT,
            priority TEXT, status TEXT, planned_date TEXT, next_due_date TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pending_toolbox (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            date_theme TEXT NOT NULL, theme TEXT, facilitator TEXT, site_id INTEGER,
            attendees_count INTEGER NOT NULL DEFAULT 0, comments TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pending_maintenance (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_date TEXT NOT NULL, equipment_label TEXT NOT NULL,
            site_id INTEGER, priority TEXT NOT NULL DEFAULT 'moyenne',
            observation TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pending_incidents (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            type_evenement TEXT, date_heure TEXT NOT NULL, lieu TEXT,
            description TEXT NOT NULL, gravite TEXT, employe_name TEXT,
            employe_id INTEGER, action_immediate TEXT, temoins TEXT, materiel_endommage TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_ppe_checks (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            check_date TEXT NOT NULL, employe_name TEXT, employe_id INTEGER,
            resultats_json TEXT, statut_global TEXT, observations TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_observations (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            obs_date TEXT NOT NULL, lieu TEXT, type_obs TEXT,
            description TEXT NOT NULL, priorite TEXT,
            action_requise INTEGER DEFAULT 0, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_ppe_assign (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            assign_date TEXT NOT NULL,
            employe_name TEXT, employe_id INTEGER,
            items_json TEXT NOT NULL,
            taille TEXT, observations TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_panne (
            id_pending INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            panne_date TEXT NOT NULL,
            panne_heure TEXT NOT NULL,
            equipment_label TEXT NOT NULL,
            site_id INTEGER,
            type_panne TEXT NOT NULL DEFAULT 'autre',
            symptomes TEXT NOT NULL,
            impact_production TEXT NOT NULL DEFAULT 'aucun',
            duree_arret_min INTEGER DEFAULT 0,
            priorite TEXT NOT NULL DEFAULT 'haute',
            statut TEXT NOT NULL DEFAULT 'signale',
            technicien TEXT,
            cause_racine TEXT,
            actions_correctives TEXT
        );
        CREATE TABLE IF NOT EXISTS ot_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ot_id INTEGER NOT NULL,
            statut TEXT NOT NULL,
            note TEXT,
            technicien TEXT,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS synced_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            nom TEXT, prenom TEXT,
            date_presence TEXT NOT NULL,
            status TEXT,
            heure_entree TEXT, heure_sortie TEXT,
            heures REAL DEFAULT 0,
            fonction TEXT, numero_badge TEXT,
            type_employe TEXT, shift TEXT,
            sync_month TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS synced_toolbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_theme TEXT NOT NULL,
            theme TEXT, facilitator TEXT,
            attendees_count INTEGER DEFAULT 0,
            comments TEXT,
            sync_month TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS saved_timesheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            format TEXT NOT NULL,
            filepath TEXT NOT NULL,
            filesize INTEGER DEFAULT 0,
            downloaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(month, format)
        );
        CREATE TABLE IF NOT EXISTS drilling_equipment_cache (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            unit TEXT NOT NULL DEFAULT 'Litre'
        );
        CREATE TABLE IF NOT EXISTS pending_drilling (
            id_pending        INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid              TEXT NOT NULL UNIQUE,
            created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            shift             TEXT NOT NULL DEFAULT 'DAY',
            report_date       TEXT NOT NULL,
            rig_type          TEXT,
            rig_number        TEXT,
            contract_location TEXT,
            hole_number       TEXT,
            angle             REAL,
            client            TEXT,
            total_advance     REAL DEFAULT 0,
            diesel_json       TEXT,
            refueler_name     TEXT,
            operator_name     TEXT,
            supervisor_name   TEXT,
            entries_json      TEXT,
            status            TEXT NOT NULL DEFAULT 'draft'
        );
    """)
    # Migrate pending_maintenance with new GMAO columns (safe — ignores if exists)
    for _col, _def in [("statut_ot","TEXT DEFAULT 'ouvert'"),("cause_racine","TEXT"),
                        ("duree_heures","REAL DEFAULT 0"),("technicien","TEXT"),
                        ("type_intervention","TEXT DEFAULT 'corrective'"),
                        ("duree_estimee","REAL DEFAULT 0"),("assigned_to","TEXT"),
                        ("date_debut","TEXT"),("date_fin","TEXT"),
                        ("statut_changed_at","TEXT")]:
        try: con.execute(f"ALTER TABLE pending_maintenance ADD COLUMN {_col} {_def}")
        except Exception: pass
    return con


# ─── Settings ─────────────────────────────────────────────────────────────────

def load_settings() -> dict[str, str]:
    try:
        with get_mobile_connection() as c:
            return {r["key"]: r["value"] for r in c.execute("SELECT key, value FROM settings").fetchall()}
    except Exception:
        return {}

def get_setting(key: str) -> str:
    try:
        with get_mobile_connection() as c:
            row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else ""
    except Exception:
        return ""

def save_setting(key: str, value: Any) -> None:
    with get_mobile_connection() as c:
        if value is None or str(value) == "":
            c.execute("DELETE FROM settings WHERE key=?", (key,))
        else:
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))


# ─── Employees ────────────────────────────────────────────────────────────────

def save_employees(rows: list[dict[str, Any]]) -> None:
    with get_mobile_connection() as c:
        c.execute("DELETE FROM employees")
        for r in rows:
            c.execute(
                "INSERT OR REPLACE INTO employees (id_employe,nom,prenom,nom_complet,fonction,site,groupe,numero_badge) VALUES (?,?,?,?,?,?,?,?)",
                (r.get("id_employe") or r.get("id"), r.get("nom"), r.get("prenom"),
                 r.get("nom_complet") or f"{r.get('nom') or ''} {r.get('prenom') or ''}".strip(),
                 r.get("fonction"), r.get("site"), r.get("groupe"), r.get("numero_badge")),
            )

def list_employees() -> list[sqlite3.Row]:
    return get_mobile_connection().execute("SELECT * FROM employees ORDER BY site, nom, prenom").fetchall()

def get_employee(eid: int) -> sqlite3.Row | None:
    return get_mobile_connection().execute("SELECT * FROM employees WHERE id_employe=?", (eid,)).fetchone()

def employee_name(row: sqlite3.Row | dict[str, Any]) -> str:
    return f"{row['nom'] or row['nom_complet'] or '-'} {row['prenom'] or ''}".strip()


# ─── Cache Helpers ────────────────────────────────────────────────────────────

def save_toolbox_topic(row: dict[str, Any]) -> None:
    if not row: return
    with get_mobile_connection() as c:
        c.execute(
            "INSERT INTO toolbox_cache(date_theme,theme,facilitator,site_id) VALUES(?,?,?,?) "
            "ON CONFLICT(date_theme) DO UPDATE SET theme=excluded.theme, "
            "facilitator=excluded.facilitator, site_id=excluded.site_id, updated_at=CURRENT_TIMESTAMP",
            (row.get("date_theme"), row.get("theme"),
             row.get("facilitateur") or row.get("facilitator"), row.get("site_id")),
        )

def save_maintenance_items(rows: list[dict[str, Any]]) -> None:
    with get_mobile_connection() as c:
        c.execute("DELETE FROM maintenance_cache")
        for r in rows:
            code  = str(r.get("equipment_code") or "").strip()
            name  = str(r.get("equipment_name") or "-").strip()
            label = f"{code} - {name}" if code else name
            c.execute(
                "INSERT INTO maintenance_cache(id_maintenance,equipment_label,site,priority,status,planned_date,next_due_date) VALUES(?,?,?,?,?,?,?)",
                (r.get("id_maintenance"), label, r.get("site"), r.get("priority"),
                 r.get("status"), r.get("planned_date"), r.get("next_due_date")),
            )

def get_toolbox_cache(dt: str) -> sqlite3.Row | None:
    return get_mobile_connection().execute("SELECT * FROM toolbox_cache WHERE date_theme=?", (dt,)).fetchone()

def list_toolbox_history(limit: int = 7) -> list[sqlite3.Row]:
    return get_mobile_connection().execute(
        "SELECT * FROM toolbox_cache ORDER BY date_theme DESC LIMIT ?", (limit,)
    ).fetchall()

def list_maintenance_cache() -> list[sqlite3.Row]:
    return get_mobile_connection().execute(
        "SELECT * FROM maintenance_cache ORDER BY priority DESC, planned_date, equipment_label"
    ).fetchall()


# ─── Pending Queues ───────────────────────────────────────────────────────────

def list_pending() -> list[sqlite3.Row]:
    return get_mobile_connection().execute("SELECT * FROM pending_attendance ORDER BY created_at, id_pending").fetchall()

def list_pending_toolbox() -> list[sqlite3.Row]:
    return get_mobile_connection().execute("SELECT * FROM pending_toolbox ORDER BY created_at, id_pending").fetchall()

def list_pending_maintenance() -> list[sqlite3.Row]:
    return get_mobile_connection().execute("SELECT * FROM pending_maintenance ORDER BY created_at, id_pending").fetchall()

def list_pending_incidents() -> list[dict[str, Any]]:
    return [dict(r) for r in get_mobile_connection().execute("SELECT * FROM pending_incidents ORDER BY id_pending DESC").fetchall()]

def list_pending_ppe_checks() -> list[dict[str, Any]]:
    return [dict(r) for r in get_mobile_connection().execute("SELECT * FROM pending_ppe_checks ORDER BY id_pending DESC").fetchall()]

def list_pending_observations() -> list[dict[str, Any]]:
    return [dict(r) for r in get_mobile_connection().execute("SELECT * FROM pending_observations ORDER BY id_pending DESC").fetchall()]

def save_pending_incident(data: dict[str, Any]) -> int:
    with get_mobile_connection() as c:
        cur = c.execute(
            "INSERT INTO pending_incidents(type_evenement,date_heure,lieu,description,gravite,employe_name,employe_id,action_immediate,temoins,materiel_endommage) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (data.get("type_evenement"), data.get("date_heure"), data.get("lieu"),
             data.get("description"), data.get("gravite"), data.get("employe_name"),
             data.get("employe_id"), data.get("action_immediate"), data.get("temoins"),
             data.get("materiel_endommage")),
        )
        return cur.lastrowid or 0

def save_pending_ppe_check(data: dict[str, Any]) -> int:
    with get_mobile_connection() as c:
        cur = c.execute(
            "INSERT INTO pending_ppe_checks(check_date,employe_name,employe_id,resultats_json,statut_global,observations) VALUES(?,?,?,?,?,?)",
            (data.get("check_date"), data.get("employe_name"), data.get("employe_id"),
             json.dumps(data.get("resultats") or {}, ensure_ascii=False),
             data.get("statut_global"), data.get("observations")),
        )
        return cur.lastrowid or 0

def save_pending_observation(data: dict[str, Any]) -> int:
    with get_mobile_connection() as c:
        cur = c.execute(
            "INSERT INTO pending_observations(obs_date,lieu,type_obs,description,priorite,action_requise,notes) VALUES(?,?,?,?,?,?,?)",
            (data.get("obs_date"), data.get("lieu"), data.get("type_obs"),
             data.get("description"), data.get("priorite"),
             1 if data.get("action_requise") else 0, data.get("notes")),
        )
        return cur.lastrowid or 0

def clear_pending() -> None:
    with get_mobile_connection() as c: c.execute("DELETE FROM pending_attendance")

def clear_pending_toolbox() -> None:
    with get_mobile_connection() as c: c.execute("DELETE FROM pending_toolbox")

def clear_pending_maintenance() -> None:
    with get_mobile_connection() as c: c.execute("DELETE FROM pending_maintenance")

def clear_pending_ids(kind: str, ids: list[Any]) -> None:
    table = {"attendance":"pending_attendance","toolbox":"pending_toolbox","maintenance":"pending_maintenance",
             "incidents":"pending_incidents","ppe_checks":"pending_ppe_checks","observations":"pending_observations",
             "panne":"pending_panne"}.get(kind)
    clean = [int(v) for v in (ids or []) if str(v).strip().isdigit()]
    if not table or not clean: return
    ph = ",".join("?" * len(clean))
    with get_mobile_connection() as c:
        c.execute(f"DELETE FROM {table} WHERE id_pending IN ({ph})", clean)  # noqa: S608

def list_pending_panne() -> list[dict]:
    try:
        return [dict(r) for r in get_mobile_connection().execute(
            "SELECT * FROM pending_panne ORDER BY created_at DESC").fetchall()]
    except Exception: return []

# ─── Drilling helpers ──────────────────────────────────────────────────────────

def save_drilling_report(data: dict) -> str:
    import uuid as _uuid, json as _json
    report_uuid = data.get("uuid") or str(_uuid.uuid4())
    with get_mobile_connection() as c:
        c.execute(
            """INSERT OR REPLACE INTO pending_drilling
               (uuid, shift, report_date, rig_type, rig_number, contract_location,
                hole_number, angle, client, total_advance, diesel_json, refueler_name,
                operator_name, supervisor_name, entries_json, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                report_uuid,
                str(data.get("shift") or "DAY"),
                str(data.get("report_date") or ""),
                data.get("rig_type") or None,
                data.get("rig_number") or None,
                data.get("contract_location") or None,
                data.get("hole_number") or None,
                data.get("angle"),
                data.get("client") or None,
                data.get("total_advance") or 0,
                _json.dumps(data.get("diesel") or {}),
                data.get("refueler_name") or None,
                data.get("operator_name") or None,
                data.get("supervisor_name") or None,
                _json.dumps(data.get("entries") or []),
                str(data.get("status") or "draft"),
            ),
        )
    return report_uuid

def list_pending_drilling() -> list[dict]:
    import json as _json
    try:
        rows = get_mobile_connection().execute(
            "SELECT * FROM pending_drilling ORDER BY report_date DESC, id_pending DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["diesel"]  = _json.loads(d.get("diesel_json") or "{}")
            d["entries"] = _json.loads(d.get("entries_json") or "[]")
            result.append(d)
        return result
    except Exception: return []

def delete_pending_drilling(report_uuid: str) -> None:
    with get_mobile_connection() as c:
        c.execute("DELETE FROM pending_drilling WHERE uuid=?", (report_uuid,))

def submit_drilling_report(report_uuid: str) -> None:
    with get_mobile_connection() as c:
        c.execute("UPDATE pending_drilling SET status='submitted' WHERE uuid=?", (report_uuid,))

def validate_drilling_report_mobile(report_uuid: str, supervisor_name: str) -> None:
    with get_mobile_connection() as c:
        c.execute(
            "UPDATE pending_drilling SET status='validated', supervisor_name=? WHERE uuid=?",
            (supervisor_name, report_uuid),
        )

def cache_drilling_equipment(equipment_list: list[dict]) -> None:
    with get_mobile_connection() as c:
        c.execute("DELETE FROM drilling_equipment_cache")
        c.executemany(
            "INSERT OR REPLACE INTO drilling_equipment_cache(id, name, code, unit) VALUES (?,?,?,?)",
            [(e.get("id", 0), e["name"], e["code"], e.get("unit", "Litre")) for e in equipment_list],
        )

def get_drilling_equipment_cached() -> list[dict]:
    try:
        return [dict(r) for r in get_mobile_connection().execute(
            "SELECT * FROM drilling_equipment_cache ORDER BY id").fetchall()]
    except Exception:
        return [
            {"id": 1, "name": "RIG – SDMA 01",             "code": "SDMA01", "unit": "Litre"},
            {"id": 2, "name": "COMPRESSOR – SDMC 01",       "code": "SDMC01", "unit": "Litre"},
            {"id": 3, "name": "MOROOKA – OZMD 05",          "code": "OZMD05", "unit": "Litre"},
            {"id": 4, "name": "MOROOKA (CRANE) – OZMD 06",  "code": "OZMD06", "unit": "Litre"},
        ]

def save_pending_panne(data: dict) -> int:
    with get_mobile_connection() as c:
        cur = c.execute(
            "INSERT INTO pending_panne(panne_date,panne_heure,equipment_label,site_id,"
            "type_panne,symptomes,impact_production,duree_arret_min,priorite,statut,"
            "technicien,cause_racine,actions_correctives) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (data.get("panne_date"), data.get("panne_heure"), data.get("equipment_label"),
             data.get("site_id"), data.get("type_panne","autre"), data.get("symptomes"),
             data.get("impact_production","aucun"), data.get("duree_arret_min",0),
             data.get("priorite","haute"), data.get("statut","signale"),
             data.get("technicien"), data.get("cause_racine"), data.get("actions_correctives")))
        return cur.lastrowid or 0

def list_ot_history(ot_id: int) -> list[dict]:
    try:
        return [dict(r) for r in get_mobile_connection().execute(
            "SELECT * FROM ot_history WHERE ot_id=? ORDER BY changed_at ASC",
            (ot_id,)).fetchall()]
    except Exception: return []

def save_ot_history(ot_id: int, statut: str, note: str = "", technicien: str = "") -> None:
    from datetime import datetime as _dt
    with get_mobile_connection() as c:
        c.execute("INSERT INTO ot_history(ot_id,statut,note,technicien,changed_at) VALUES(?,?,?,?,?)",
                  (ot_id, statut, note or "", technicien or "",
                   _dt.now().strftime("%Y-%m-%d %H:%M:%S")))

def update_ot_statut(ot_id: int, new_statut: str, note: str = "", technicien: str = "") -> None:
    from datetime import datetime as _dt
    now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    extra = {}
    if new_statut == "en_cours":
        extra["date_debut"] = now
    elif new_statut in ("termine", "verifie"):
        extra["date_fin"] = now
    set_clause = "statut_ot=?, statut_changed_at=?" + (
        "".join(f", {k}=?" for k in extra))
    vals = [new_statut, now] + list(extra.values()) + [ot_id]
    with get_mobile_connection() as c:
        c.execute(f"UPDATE pending_maintenance SET {set_clause} WHERE id_pending=?", vals)  # noqa: S608
    save_ot_history(ot_id, new_statut, note, technicien)

def get_ot(ot_id: int) -> dict | None:
    try:
        r = get_mobile_connection().execute(
            "SELECT * FROM pending_maintenance WHERE id_pending=?", (ot_id,)).fetchone()
        return dict(r) if r else None
    except Exception: return None

def list_pending_ppe_assigns() -> list[dict]:
    return [dict(r) for r in get_mobile_connection().execute(
        "SELECT * FROM pending_ppe_assign ORDER BY id_pending DESC").fetchall()]

def save_pending_ppe_assign(data: dict) -> int:
    import json as _json
    with get_mobile_connection() as c:
        cur = c.execute(
            "INSERT INTO pending_ppe_assign(assign_date,employe_name,employe_id,"
            "items_json,taille,observations) VALUES(?,?,?,?,?,?)",
            (data["assign_date"], data.get("employe_name",""), data.get("employe_id"),
             _json.dumps(data.get("items",[]), ensure_ascii=False),
             data.get("taille",""), data.get("observations","")))
        return cur.lastrowid

def total_pending() -> int:
    return (len(list_pending()) + len(list_pending_toolbox()) + len(list_pending_maintenance())
            + len(list_pending_incidents()) + len(list_pending_ppe_checks())
            + len(list_pending_observations()) + len(list_pending_ppe_assigns())
            + len(list_pending_panne()))


def save_synced_month_data(month: str, attendance: list[dict], toolbox: list[dict]) -> None:
    with get_mobile_connection() as c:
        c.execute("DELETE FROM synced_attendance WHERE sync_month=?", (month,))
        c.execute("DELETE FROM synced_toolbox WHERE sync_month=?", (month,))
        for r in attendance:
            c.execute(
                "INSERT INTO synced_attendance(employee_id,nom,prenom,date_presence,status,"
                "heure_entree,heure_sortie,heures,fonction,numero_badge,type_employe,shift,sync_month)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r.get("employee_id"), r.get("nom",""), r.get("prenom",""),
                 r.get("date_presence"), r.get("status"),
                 r.get("heure_entree"), r.get("heure_sortie"), r.get("heures",0),
                 r.get("fonction",""), r.get("numero_badge",""),
                 r.get("type_employe","national"), r.get("shift",""),
                 month))
        for r in toolbox:
            c.execute(
                "INSERT INTO synced_toolbox(date_theme,theme,facilitator,attendees_count,comments,sync_month)"
                " VALUES(?,?,?,?,?,?)",
                (r.get("date_theme"), r.get("theme",""), r.get("facilitator",""),
                 r.get("attendees_count",0), r.get("comments",""), month))


def list_synced_attendance(month_prefix: str) -> list[dict]:
    return [dict(r) for r in get_mobile_connection().execute(
        "SELECT * FROM synced_attendance WHERE date_presence LIKE ? ORDER BY date_presence, nom",
        (f"{month_prefix}%",)).fetchall()]


def list_synced_toolbox(month_prefix: str) -> list[dict]:
    return [dict(r) for r in get_mobile_connection().execute(
        "SELECT * FROM synced_toolbox WHERE date_theme LIKE ? ORDER BY date_theme",
        (f"{month_prefix}%",)).fetchall()]


def save_timesheet_record(month: str, fmt: str, filepath: str, filesize: int) -> None:
    with get_mobile_connection() as c:
        c.execute(
            "INSERT OR REPLACE INTO saved_timesheets(month, format, filepath, filesize, downloaded_at)"
            " VALUES(?,?,?,?,CURRENT_TIMESTAMP)",
            (month, fmt, filepath, filesize))


def list_saved_timesheets() -> list[dict]:
    return [dict(r) for r in get_mobile_connection().execute(
        "SELECT * FROM saved_timesheets ORDER BY month DESC, format").fetchall()]


def delete_saved_timesheet(ts_id: int) -> None:
    with get_mobile_connection() as c:
        c.execute("DELETE FROM saved_timesheets WHERE id=?", (ts_id,))


# ─── Network ──────────────────────────────────────────────────────────────────

def _open_json(req: urllib.request.Request, timeout: int) -> dict[str, Any]:
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = ""
        try: body = exc.read().decode()[:200]
        except Exception: pass
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}. {body}") from exc

def _headers(token: str) -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        h["X-OREZONE-Mobile-Token"] = token
        h["Authorization"] = f"Bearer {token}"
    device_id = get_setting("device_id")
    if not device_id:
        from uuid import uuid4
        device_id = str(uuid4())
        save_setting("device_id", device_id)
    h["X-OREZONE-Device-Id"] = device_id
    h["X-OREZONE-Device-Name"] = get_setting("device_name") or "OREZONE Mobile"
    session = get_setting("mobile_session")
    if session:
        h["X-OREZONE-Mobile-Session"] = session
    return h

def request_json(url: str, token: str, timeout: int = 15) -> dict[str, Any]:
    return _open_json(urllib.request.Request(url, headers=_headers(token)), timeout)

def post_json(url: str, token: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode()
    return _open_json(urllib.request.Request(url, data=data, headers=_headers(token), method="POST"), timeout)

def _friendly_network_error(exc: Exception) -> str:
    msg = str(exc)
    if "10060" in msg or "timed out" in msg.lower() or "time out" in msg.lower():
        return "Délai dépassé — l'application principale ne répond pas. Vérifiez qu'elle est démarrée et que le serveur de synchronisation est actif (icône dans la barre d'état)."
    if "10061" in msg or "Connection refused" in msg or "refused" in msg.lower():
        return "Connexion refusée — le serveur de synchronisation n'est pas démarré. Ouvrez l'application principale et activez la synchronisation mobile."
    if "11001" in msg or "getaddrinfo" in msg.lower() or "Name or service" in msg.lower():
        return "Adresse introuvable — vérifiez l'URL du serveur dans Paramètres."
    if "10051" in msg or "Network is unreachable" in msg.lower():
        return "Réseau inaccessible — vérifiez votre connexion Wi-Fi ou réseau local."
    return f"Erreur réseau : {msg[:180]}"


def request_bytes(url: str, token: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers=_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Erreur serveur {exc.code}: {exc.read().decode('utf-8','replace')[:200]}")
    except Exception as exc:
        raise ValueError(_friendly_network_error(exc))


def ping_server(addr: str, token: str, timeout: int = 4) -> bool:
    """Returns True if the sync server responds to /api/mobile/ping within timeout seconds."""
    try:
        request_bytes(f"{addr.rstrip('/')}/api/mobile/ping", token, timeout=timeout)
        return True
    except ValueError as exc:
        # 4xx/5xx means server is alive (just error response)
        s = str(exc)
        return any(code in s for code in ("401","403","404","500"))
    except Exception:
        return False


# ─── App ──────────────────────────────────────────────────────────────────────

def build_mobile_page(page: ft.Page) -> None:  # noqa: PLR0914,PLR0915

    page.title       = "OREZONE QHSE"
    page.theme_mode  = ft.ThemeMode.DARK
    page.bgcolor     = "#071321"
    page.padding     = 0
    page.theme       = ft.Theme(color_scheme_seed="#3B82F6", use_material3=True,
                                visual_density=ft.VisualDensity.COMFORTABLE)

    # ── Palette ───────────────────────────────────────────────────────────────
    NAV  = "#091828"; BLUE = "#3B82F6"; BG   = "#071321"
    CARD = "#0F2336"; BRD  = "#1A3550"; TXT  = "#E2E8F0"; MUT  = "#7A9BB5"
    OK   = "#10B981"; WARN = "#F59E0B"; DNG  = "#EF4444"
    INFO = "#06B6D4"; PURP = "#8B5CF6"

    # ── GMAO color tables (need dark-theme palette) ────────────────────────────
    TYPE_PANNE_COLORS = {
        "mecanique": WARN,  "electrique": DNG,   "hydraulique": INFO,
        "pneumatique": BLUE,"moteur": PURP,       "operateur": OK,
        "structure": "#F97316", "autre": MUT,
    }
    IMPACT_PROD_ITEMS = [
        ("arret_total","Arrêt total",    DNG,  ft.Icons.BLOCK_ROUNDED),
        ("partiel",    "Arrêt partiel",  WARN, ft.Icons.WARNING_AMBER_ROUNDED),
        ("degrade",    "Dégradé",        INFO, ft.Icons.SPEED_ROUNDED),
        ("aucun",      "Sans impact",    OK,   ft.Icons.CHECK_CIRCLE_ROUNDED),
    ]
    STATUT_OT_COLORS = {
        "ouvert": INFO, "en_cours": WARN, "attente_pieces": PURP, "termine": OK,
    }

    GRAD = ft.LinearGradient(begin=ft.Alignment(-1,-1), end=ft.Alignment(1,0.8),
                             colors=["#071E3D","#0D3A6B"])

    def P(l=0,t=0,r=0,b=0): return ft.Padding(left=l,top=t,right=r,bottom=b)
    def AL(x=0,y=0):         return ft.Alignment(x,y)
    def SH(blur=8,op="10"):
        return ft.BoxShadow(blur_radius=blur,spread_radius=0,
                            color=f"#{op}000000",offset=ft.Offset(0,3))

    # ── Atoms ─────────────────────────────────────────────────────────────────
    def _badge(label, color, bg=""):
        return ft.Container(bgcolor=bg or f"{color}18",border_radius=20,
            border=ft.Border.all(1,f"{color}44"),padding=P(10,3,10,3),
            content=ft.Text(label,size=11,color=color,weight=ft.FontWeight.W_700))

    def _dot(c,s=7): return ft.Container(width=s,height=s,bgcolor=c,border_radius=s)

    def _ava(init,size=44,color=None):
        c=color or BLUE
        return ft.Container(width=size,height=size,border_radius=size//2,
            gradient=ft.LinearGradient(begin=AL(-1,-1),end=AL(1,1),colors=[c,f"{c}99"]),
            alignment=AL(0,0),shadow=SH(6,"22"),
            content=ft.Text(init,size=max(11,size//3),weight=ft.FontWeight.BOLD,color="#FFFFFF"))

    def _box(icon,color,size=40,ico=20):
        return ft.Container(width=size,height=size,border_radius=size//2,
            bgcolor=f"{color}18",alignment=AL(0,0),
            content=ft.Icon(icon,color=color,size=ico))

    def _card(content,pad=P(14,14,14,14),radius=14,accent=None):
        return ft.Container(bgcolor=CARD,border_radius=radius,shadow=SH(),
            border=ft.Border.all(1,f"{accent}22" if accent else BRD),
            padding=pad,content=content)

    def _ac(content,color):
        return ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(),
            content=ft.Row([ft.Container(width=5,bgcolor=color,border_radius=14),
                ft.Container(expand=True,padding=P(12,14,14,14),content=content)],
                spacing=0,tight=True))

    def _sec(label,icon="",count=-1):
        row=[]
        if icon: row+=[ft.Container(width=3,height=16,bgcolor=BLUE,border_radius=2),
                        ft.Icon(icon,color=BLUE,size=16)]
        row.append(ft.Text(label,size=14,weight=ft.FontWeight.BOLD,color=TXT,expand=True))
        if count>=0: row.append(_badge(str(count),BLUE))
        return ft.Row(row,spacing=8,tight=True)

    def _div(): return ft.Divider(height=1,color=BRD)

    def _kpi(label,value,color,icon):
        return ft.Container(bgcolor=CARD,border_radius=14,padding=P(14,14,14,14),expand=True,
            shadow=SH(),border=ft.Border.all(1,f"{color}22"),
            content=ft.Column([
                ft.Row([_box(icon,color,38,19),ft.Container(expand=True),_dot(color,8)]),
                ft.Container(height=4),
                ft.Text(value,size=28,weight=ft.FontWeight.BOLD,color=color),
                ft.Text(label,size=11,color=MUT,weight=ft.FontWeight.W_500),
            ],spacing=3,tight=True))

    def _mstat(val,label,color="#FFFFFF"):
        return ft.Container(expand=True,content=ft.Column([
            ft.Text(val,size=20,weight=ft.FontWeight.BOLD,color=color,
                    text_align=ft.TextAlign.CENTER),
            ft.Text(label,size=10,color=f"{color}BB",text_align=ft.TextAlign.CENTER),
        ],spacing=2,tight=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    def _btn(label,icon,color,handler,height=50):
        return ft.Container(bgcolor=color,border_radius=12,height=height,
            ink=True,on_click=handler,alignment=AL(0,0),
            content=ft.Row([ft.Icon(icon,color="#FFFFFF",size=18),
                ft.Text(label,color="#FFFFFF",size=14,weight=ft.FontWeight.W_600)],
                alignment=ft.MainAxisAlignment.CENTER,spacing=8,tight=True))

    def _gbtn(label,icon,color,handler,height=46):
        return ft.Container(border=ft.Border.all(1.5,color),border_radius=12,height=height,
            ink=True,on_click=handler,alignment=AL(0,0),
            content=ft.Row([ft.Icon(icon,color=color,size=17),
                ft.Text(label,color=color,size=13,weight=ft.FontWeight.W_600)],
                alignment=ft.MainAxisAlignment.CENTER,spacing=7,tight=True))

    def _tile(label,icon,sub,color,handler,red=False):
        return ft.Container(bgcolor=CARD,border_radius=12,shadow=SH(4,"06"),
            ink=True,on_click=handler,padding=P(14,12,14,12),
            content=ft.Row([_box(icon,color,40,20),
                ft.Column([ft.Text(label,size=13,weight=ft.FontWeight.W_600,
                        color=DNG if red else TXT),
                    ft.Text(sub,size=11,color=MUT) if sub else ft.Container()],
                    spacing=1,expand=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT_OUTLINED,color=BRD,size=20)],spacing=12))

    def _sbadge(status):
        s=(status or "").lower()
        if s in ("en_retard","overdue","retard"): return _badge("● Retard",DNG,"#FEE2E2")
        if s in ("a_surveiller","warning","bientot"): return _badge("● À surveiller",WARN,"#FEF3C7")
        if s in ("ok","normal","conforme"): return _badge("● OK",OK,"#DCFCE7")
        return _badge(status.replace("_"," ").title(),MUT)

    def _hdr(title,back=None,right_icon="",right_fn=None):
        L=(ft.Container(width=38,height=38,border_radius=19,bgcolor="#18FFFFFF",
               alignment=AL(0,0),ink=True,on_click=lambda e:go_to(back),
               content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,color="#FFFFFF",size=18))
           if back else ft.Container(width=38))
        R=(ft.Container(width=38,height=38,border_radius=19,bgcolor="#18FFFFFF",
               alignment=AL(0,0),ink=True,on_click=right_fn,
               content=ft.Icon(right_icon,color="#FFFFFF",size=18))
           if right_icon else ft.Container(width=38))
        return ft.Container(gradient=GRAD,padding=P(14,16,14,18),shadow=SH(10,"18"),
            content=ft.Row([L,ft.Text(title,size=17,weight=ft.FontWeight.BOLD,
                color="#FFFFFF",expand=True,text_align=ft.TextAlign.CENTER),R],spacing=8))

    def _body(*ctrls,pad=P(14,14,14,80)):
        return ft.Container(expand=True,padding=pad,
            content=ft.Column(list(ctrls),spacing=12,
                scroll=ft.ScrollMode.AUTO,expand=True))

    def _tf(label,hint="",pw=False,ml=False,lines=3,kb=None,val=""):
        kw={}
        if kb: kw["keyboard_type"]=kb
        return ft.TextField(label=label,hint_text=hint,password=pw,value=val,
            can_reveal_password=pw,multiline=ml,
            min_lines=lines if ml else None,max_lines=lines+2 if ml else None,
            border_radius=10,border_color=BRD,focused_border_color=BLUE,
            bgcolor=CARD,color=TXT,cursor_color=BLUE,
            label_style=ft.TextStyle(color=MUT),**kw)

    def _dd(label,opts=None):
        return ft.Dropdown(label=label,options=opts or [],
            border_radius=10,border_color=BRD,focused_border_color=BLUE,
            bgcolor=CARD,color=TXT)

    # ── Form Controls ─────────────────────────────────────────────────────────
    APP_VERSION = "2.0.0"

    def _dark_tf(label,hint="",pw=False,val="",prefix_icon=None,on_submit=None):
        return ft.TextField(label=label,hint_text=hint,password=pw,
            can_reveal_password=pw,value=val,border_radius=10,
            border_color="#1E3A5F",focused_border_color=BLUE,
            bgcolor="#132337",color="#E2E8F0",
            label_style=ft.TextStyle(color="#64748B"),
            prefix_icon=prefix_icon,
            on_submit=on_submit)

    srv_url    = _dark_tf("Serveur PC","http://192.168.1.x:8765",val=get_setting("server_url") or "")
    srv_token  = _dark_tf("Token d'appairage",pw=True,val=get_setting("token") or "")
    srv_device = _dark_tf("Nom appareil",val=get_setting("device_name") or "Telephone terrain")
    lgn_user   = _dark_tf("Nom d'utilisateur",val=get_setting("identity_username") or "",
                           prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED)
    lgn_pass   = _dark_tf("Mot de passe",pw=True,
                           prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
                           on_submit=lambda e: do_login())
    lgn_rem    = ft.Switch(value=bool(get_setting("identity_username")),active_color=BLUE)
    lgn_status = ft.Text("",size=12,color=DNG,text_align=ft.TextAlign.CENTER)
    _pair_code_tf = _dark_tf("Coller le code d'appairage ici…")

    att_emp  = _dd("Rechercher un employé...")
    att_date = _tf("Date",val=date.today().isoformat())
    att_stat = ft.Dropdown(label="Présence",value="present",border_radius=10,
        options=[ft.dropdown.Option("present","Présent"),ft.dropdown.Option("absent","Absent"),
                 ft.dropdown.Option("mission","Mission"),ft.dropdown.Option("maladie","Maladie"),
                 ft.dropdown.Option("conge","Congé")])
    att_in   = _tf("Heure entrée",val="06:00",kb=ft.KeyboardType.DATETIME)
    att_out  = _tf("Heure sortie",val="14:00",kb=ft.KeyboardType.DATETIME)
    att_obs  = _tf("Note / Motif (optionnel)",ml=True,lines=2)
    ATT: dict = {"status":"present","emp_name":"","emp_role":"","emp_site":""}

    mi_eq    = _dd("Équipement *")
    mi_type  = ft.Dropdown(label="Type",value="preventive",border_radius=10,
        border_color=BRD,focused_border_color=BLUE,
        options=[ft.dropdown.Option("preventive","Préventive"),
                 ft.dropdown.Option("corrective","Corrective"),
                 ft.dropdown.Option("inspection","Inspection"),
                 ft.dropdown.Option("vidange","Vidange")])
    mi_prio  = ft.Dropdown(label="Priorité",value="haute",border_radius=10,
        border_color=BRD,focused_border_color=BLUE,
        options=[ft.dropdown.Option("basse","Basse"),ft.dropdown.Option("moyenne","Moyenne"),
                 ft.dropdown.Option("haute","Haute"),ft.dropdown.Option("critique","Critique")])
    mi_date  = _tf("Date prévue",val=date.today().isoformat())
    mi_km    = _tf("Compteur (km)",kb=ft.KeyboardType.NUMBER)
    mi_obs   = _tf("Description *",ml=True,lines=3)
    mi_statut_ot = ft.Dropdown(label="Statut OT",value="ouvert",border_radius=10,
        border_color=BRD,focused_border_color=BLUE,
        options=[ft.dropdown.Option("ouvert","Ouvert"),
                 ft.dropdown.Option("en_cours","En cours"),
                 ft.dropdown.Option("attente_pieces","Attente pièces"),
                 ft.dropdown.Option("termine","Terminé")])
    mi_cause = ft.Dropdown(label="Cause racine",border_radius=10,
        border_color=BRD,focused_border_color=BLUE,
        options=[ft.dropdown.Option(c,c) for c in CAUSE_RACINE_OPTS])
    mi_duree = _tf("Durée (heures)",kb=ft.KeyboardType.NUMBER)
    mi_tech  = _tf("Technicien responsable")

    ins_eq   = _dd("Équipement *")
    ins_sign = _tf("Signature (Prénom Nom)")
    ins_chk: dict[str,bool] = {it:False for it in INSPECTION_ITEMS}
    ins_col  = ft.Column(spacing=6)

    tb_cmt   = _tf("Commentaire",ml=True,lines=2)

    inc_lieu = _tf("Lieu / Zone *")
    inc_desc = _tf("Description *",ml=True,lines=3)
    inc_act  = _tf("Action immédiate",ml=True,lines=2)
    inc_emp  = _dd("Employé impliqué")
    inc_date = _tf("Date / Heure",val=datetime.now().strftime("%Y-%m-%d %H:%M"))

    ppe_emp  = _dd("Employé *")
    ppe_obs  = _tf("Observations",ml=True,lines=2)
    ppe_col  = ft.Column(spacing=6)

    # Dotation EPI
    ppa_emp  = _dd("Employé bénéficiaire *")
    ppa_obs  = _tf("Observations / Remarques",ml=True,lines=2)
    ppa_tail = _tf("Taille (S/M/L/XL…)",hint="ex: L")

    # Dynamic
    h_stats  = ft.Container()          # compact 4-stat strip
    h_kpi1   = ft.Row(spacing=10)     # kept for compat (not shown on home)
    h_kpi2   = ft.Row(spacing=10)
    h_tb     = ft.Container(visible=False)
    h_alr    = ft.Column(spacing=8)
    m_col    = ft.Column(spacing=8)
    m_search = ft.TextField(label="Rechercher un équipement...",
        prefix_icon=ft.Icons.SEARCH_OUTLINED,
        border_radius=12,border_color=BRD,focused_border_color=BLUE,height=46,
        bgcolor=CARD,color=TXT,label_style=ft.TextStyle(color=MUT))
    tb_today = ft.Column(spacing=8)
    tb_hist  = ft.Column(spacing=6)
    al_col   = ft.Column(spacing=8)
    ep_col   = ft.Column(spacing=8)
    pr_col   = ft.Column(spacing=8)
    inc_tr   = ft.Row(spacing=6,wrap=True)
    inc_gr   = ft.Row(spacing=6,wrap=True)

    ST: dict = {"screen":"login","nav":["home","securite","maintenance","personnel","profile"],
                "alerts_tab":"all","attendees":0,
                "inc_type":"accident","inc_grav":"mineur",
                "ppe":{lbl:"na" for lbl,_ in PPE_ITEMS},
                "ot_id": None}

    srv_dot   = ft.Container(width=9,height=9,bgcolor=WARN,border_radius=5)
    _navref: list = []
    area      = ft.Container(expand=True)
    _ov_msg   = ft.Text("Chargement...",color=TXT,size=13,weight=ft.FontWeight.W_600)
    overlay   = ft.Container(visible=False,expand=True,bgcolor="#D0000000",alignment=AL(0,0),
        content=ft.Container(bgcolor=CARD,border_radius=20,padding=P(32,28,32,28),
            shadow=ft.BoxShadow(blur_radius=40,spread_radius=0,color="#50000000",offset=ft.Offset(0,8)),
            content=ft.Column([
                ft.ProgressRing(color=BLUE,width=40,height=40,stroke_width=3),
                ft.Container(height=4),
                _ov_msg,
            ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=14,tight=True)))

    def notify(msg, color=MUT):
        icon_map={OK:ft.Icons.CHECK_CIRCLE_ROUNDED,DNG:ft.Icons.ERROR_ROUNDED,
                  WARN:ft.Icons.WARNING_AMBER_ROUNDED,INFO:ft.Icons.INFO_ROUNDED,
                  BLUE:ft.Icons.INFO_ROUNDED}
        icon=icon_map.get(color,ft.Icons.NOTIFICATIONS_ROUNDED)
        sb = ft.SnackBar(
            content=ft.Row([
                ft.Icon(icon,color="#FFFFFF",size=16),
                ft.Text(msg,color="#FFFFFF",size=13,weight=ft.FontWeight.W_500,expand=True),
            ],spacing=10,tight=True),
            bgcolor=color if color!=MUT else "#1E3A56",
            duration=3800,
            show_close_icon=True,
            close_icon_color="#FFFFFF88",
        )
        page.show_dialog(sb)

    def confirm(title, msg, on_yes, danger=False, yes_lbl="Confirmer", no_lbl="Annuler"):
        btn_color = DNG if danger else BLUE
        icon = ft.Icons.WARNING_AMBER_ROUNDED if danger else ft.Icons.HELP_OUTLINE_ROUNDED
        icon_color = DNG if danger else BLUE
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD,
            title=ft.Row([
                ft.Container(
                    bgcolor=f"{icon_color}18", border_radius=8,
                    padding=ft.Padding(left=8,top=8,right=8,bottom=8),
                    content=ft.Icon(icon, color=icon_color, size=22)),
                ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=TXT, expand=True),
            ], spacing=10, tight=True),
            content=ft.Container(
                padding=ft.Padding(left=0,top=4,right=0,bottom=0),
                content=ft.Text(msg, size=13, color=MUT)),
            actions=[
                ft.TextButton(no_lbl,
                    style=ft.ButtonStyle(color=MUT),
                    on_click=lambda e: page.pop_dialog()),
                ft.FilledButton(yes_lbl,
                    bgcolor=btn_color, color="#FFFFFF",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=lambda e: [page.pop_dialog(), on_yes(e)]),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    def busy(on, msg="Chargement..."):
        _ov_msg.value=msg; overlay.visible=on; page.update()

    def go_to(key):
        ST["screen"]=key; area.content=_build(key)
        if _navref and key in ST["nav"]: _navref[0].selected_index=ST["nav"].index(key)
        page.update()

    def go_to_ot(ot_id: int):
        ST["ot_id"] = ot_id
        area.content = _s_ot_detail(ot_id)
        page.update()

    def _nav_ch(e): go_to(ST["nav"][int(e.control.selected_index or 0)])

    def validate_url():
        addr=normalize_server_url(srv_url.value)
        if not addr: raise ValueError("Adresse serveur obligatoire.")
        p=urllib.parse.urlparse(addr)
        if p.scheme not in {"http","https"} or not p.hostname:
            raise ValueError("URL invalide. ex: http://192.168.1.5:8765")
        if p.hostname in {"127.0.0.1","localhost","::1"}:
            raise ValueError("127.0.0.1 = ce téléphone, pas le PC.")
        srv_url.value=addr; return addr

    def req_sess():
        if not get_setting("mobile_session"): raise ValueError("Connexion requise. Profil > Paramètres.")

    def cj(key,default=None):
        try: return json.loads(get_setting(key) or "")
        except Exception: return default if default is not None else {}

    def _toggle(row,sk,opts,colors):
        def _b(k,lbl,c):
            active=ST[sk]==k
            return ft.Container(bgcolor=c if active else f"{c}18",border_radius=8,
                padding=P(12,8,12,8),ink=True,
                border=ft.Border.all(1,c if active else f"{c}44"),
                on_click=lambda e,kk=k:[ST.__setitem__(sk,kk),_toggle(row,sk,opts,colors)],
                content=ft.Text(lbl,size=12,
                    color="#FFFFFF" if active else c,
                    weight=ft.FontWeight.W_600))
        row.controls=[_b(k,opts[k],colors[k]) for k in opts]
        try: row.update()
        except Exception: pass

    def _rebuild_ppe():
        res=ST["ppe"]
        def _b(il,val,text,c):
            active=res.get(il)==val
            return ft.Container(bgcolor=c if active else f"{c}18",border_radius=6,
                padding=P(8,5,8,5),ink=True,border=ft.Border.all(1,c if active else f"{c}44"),
                on_click=lambda e,i=il,v=val:[ST["ppe"].__setitem__(i,v),_rebuild_ppe()],
                content=ft.Text(text,size=11,color="#FFFFFF" if active else c,
                                weight=ft.FontWeight.W_600))
        def _row(lbl,ico):
            cur=res.get(lbl,"na")
            sc=OK if cur=="ok" else(DNG if cur=="nok" else MUT)
            return ft.Container(bgcolor=CARD,border=ft.Border.all(1,sc if cur!="na" else BRD),
                border_radius=10,padding=P(12,10,12,10),
                content=ft.Row([_box(ico,sc,32,16),ft.Text(lbl,expand=True,size=12,color=TXT),
                    _b(lbl,"ok","OK",OK),_b(lbl,"nok","NOK",DNG),_b(lbl,"na","N/A",MUT)],spacing=6))
        ppe_col.controls=[_row(l,i) for l,i in PPE_ITEMS]
        try: ppe_col.update()
        except Exception: pass

    def _rebuild_ins():
        def _row(item):
            checked=ins_chk.get(item,False)
            def _tog(e,it=item): ins_chk[it]=e.control.value; _rebuild_ins()
            return ft.Container(bgcolor=CARD,border=ft.Border.all(1,OK if checked else BRD),
                border_radius=10,padding=P(12,10,12,10),
                content=ft.Row([ft.Checkbox(value=checked,active_color=OK,on_change=_tog),
                    ft.Text(item,expand=True,size=13,color=TXT),
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED if checked
                            else ft.Icons.RADIO_BUTTON_UNCHECKED_OUTLINED,
                            color=OK if checked else BRD,size=18)],spacing=8))
        ins_col.controls=[_row(it) for it in INSPECTION_ITEMS]
        try: ins_col.update()
        except Exception: pass

    # ── Auth ──────────────────────────────────────────────────────────────────
    def do_login(e=None):
        busy(True, "Connexion en cours..."); lgn_status.value=""
        try:
            if not str(lgn_user.value or "").strip(): raise ValueError("Identifiant obligatoire.")
            if not str(lgn_pass.value or "").strip(): raise ValueError("Mot de passe obligatoire.")
            addr=validate_url()
            save_setting("server_url",srv_url.value); save_setting("token",srv_token.value)
            save_setting("device_name",srv_device.value)
            if not get_setting("device_id"): save_setting("device_id",str(uuid4()))
            data=post_json(f"{addr}/api/mobile/login",srv_token.value,
                           {"username":lgn_user.value,"password":lgn_pass.value})
            u=data.get("user") or {}
            save_setting("mobile_session",data.get("session_token") or "")
            if lgn_rem.value:
                save_setting("identity_username",u.get("username") or "")
            else:
                save_setting("identity_username","")
            save_setting("identity_role",u.get("role") or "")
            save_setting("profile_label",u.get("label") or u.get("role") or "")
            lgn_pass.value=""
            _boot(addr); _enter_app()
        except ValueError as exc:
            lgn_status.value=str(exc)
            lgn_status.color=DNG; page.update()
        except Exception as exc:
            raw=str(exc)
            if "10060" in raw or "timed out" in raw.lower():
                lgn_status.value="Serveur inaccessible — démarrez l'app QHSE sur le PC."
            elif "refused" in raw.lower() or "10061" in raw:
                lgn_status.value="Connexion refusée — serveur non démarré sur ce port."
            elif "urlopen" in raw.lower():
                lgn_status.value=f"Réseau : {raw.split('urlopen error')[-1].strip('<> ')}"
            elif "401" in raw or "403" in raw or "unauthorized" in raw.lower():
                lgn_status.value="Identifiants incorrects — vérifiez nom d'utilisateur et mot de passe."
            elif "400" in raw:
                import re as _re
                m=_re.search(r'"error"\s*:\s*"([^"]+)"',raw)
                lgn_status.value=m.group(1) if m else "Token invalide ou identifiants incorrects."
            else:
                lgn_status.value=raw[:300]
            lgn_status.color=DNG; page.update()
        finally: busy(False)

    def do_logout(e=None):
        _stop_bg_sync()
        for k in ("mobile_session","identity_username","identity_role"): save_setting(k,"")
        page.navigation_bar=None; page.bgcolor="#0A1929"; go_to("login")

    def _read_pairing_code() -> str:
        """Read pairing code written by the main QHSE app (file-based, most reliable)."""
        # Candidate locations matching app/config.py DATA_DIR logic
        candidates = [
            # Dev mode: script runs from project root
            Path(__file__).parent / "data" / "mobile_pairing_code.txt",
            # Frozen/installed mode: APPDATA
            Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
            / "OREZONE_QHSE" / "data" / "mobile_pairing_code.txt",
        ]
        for p in candidates:
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8").strip()
                    if content:
                        return content
                except Exception:
                    pass
        # Fallback: Windows clipboard via ctypes
        try:
            import ctypes
            CF_UNICODETEXT = 13
            ctypes.windll.user32.OpenClipboard(0)
            try:
                h = ctypes.windll.user32.GetClipboardData(CF_UNICODETEXT)
                if h:
                    return ctypes.cast(h, ctypes.c_wchar_p).value or ""
            finally:
                ctypes.windll.user32.CloseClipboard()
        except Exception:
            pass
        return ""

    def _parse_pairing_code(raw: str) -> tuple[str, str]:
        import base64 as _b64
        raw = raw.strip()
        if not raw:
            raise ValueError("Presse-papiers vide ou code non reconnu.")
        decoded = _b64.b64decode(raw.encode()).decode()
        data = json.loads(decoded)
        url = str(data.get("u") or data.get("url") or "").strip()
        tk  = str(data.get("t") or data.get("token") or "").strip()
        if not url or not tk:
            raise ValueError("URL ou token manquant dans le code.")
        return url, tk

    def _apply_pairing(url: str, tk: str) -> None:
        srv_url.value = url; srv_token.value = tk
        save_setting("server_url", url); save_setting("token", tk)
        lgn_status.value = "Configuration appliquée — entrez vos identifiants."
        lgn_status.color = OK
        try: page.update()
        except Exception: pass

    def show_pairing_dialog(e=None):
        msg_ctrl = ft.Text("", size=12, color=MUT)

        def _try_apply(ev=None):
            try:
                raw = _read_pairing_code()
                url, tk = _parse_pairing_code(raw)
                page.pop_dialog()
                _apply_pairing(url, tk)
            except Exception as exc:
                msg_ctrl.value = f"Presse-papiers invalide : {exc}\nCopiez le code sur le PC, puis réessayez."
                msg_ctrl.color = DNG
                try: msg_ctrl.update()
                except Exception: pass

        def _cancel(ev=None):
            page.pop_dialog()

        # Try immediately on first open
        initial_err = ""
        initial_url = ""
        try:
            raw = _read_pairing_code()
            url, tk = _parse_pairing_code(raw)
            initial_url = url
            msg_ctrl.value = f"Code détecté — Serveur : {url}"
            msg_ctrl.color = OK
        except Exception as exc:
            initial_err = str(exc)
            msg_ctrl.value = (
                "Code introuvable.\n"
                "1. Sur le PC → Paramètres → Mobile\n"
                "2. Cliquer « Copier le code d'appairage »\n"
                "3. Revenir ici et cliquer « Réessayer »"
            )
            msg_ctrl.color = MUT

        pairing_dlg = ft.AlertDialog(
            modal=True, bgcolor=CARD,
            title=ft.Row([
                ft.Icon(ft.Icons.LINK_ROUNDED, color=BLUE, size=20),
                ft.Text("Appairage PC → Mobile", size=15, weight=ft.FontWeight.BOLD, color=TXT),
            ], spacing=8, tight=True),
            content=ft.Column([
                ft.Container(
                    bgcolor=f"#12{BLUE[1:]}", border_radius=10, padding=14,
                    border=ft.Border.all(1, f"#30{BLUE[1:]}"),
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.COMPUTER_OUTLINED, color=BLUE, size=16),
                                ft.Text("Étapes :", size=13, weight=ft.FontWeight.BOLD, color=TXT)],
                               spacing=6),
                        ft.Text("① Sur l'app principale (PC) :", size=12, weight=ft.FontWeight.W_600, color=TXT),
                        ft.Text("   Paramètres › Mobile\n   → « Copier le code d'appairage »", size=12, color=MUT),
                        ft.Container(height=4),
                        ft.Text("② Revenir ici et cliquer « Réessayer »", size=12, weight=ft.FontWeight.W_600, color=TXT),
                        ft.Text("   La configuration s'applique automatiquement.", size=12, color=MUT),
                    ], spacing=4, tight=True)),
                ft.Container(height=8),
                msg_ctrl,
            ], spacing=6, tight=True, width=400),
            actions=[
                ft.TextButton("Annuler", on_click=_cancel,
                              style=ft.ButtonStyle(color=MUT)),
                ft.FilledButton(
                    "Réessayer / Appliquer",
                    icon=ft.Icons.REFRESH_ROUNDED,
                    on_click=_try_apply,
                    bgcolor=BLUE, color="#FFFFFF",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # If code was already detected, apply directly
        if initial_url:
            try:
                url2, tk2 = _parse_pairing_code(_read_pairing_code())
                _apply_pairing(url2, tk2)
                return
            except Exception:
                pass
        page.show_dialog(pairing_dlg)

    def _boot(addr):
        tk=get_setting("token") or srv_token.value
        # Bootstrap
        try:
            data=request_json(f"{addr}/api/mobile/bootstrap?date={date.today().isoformat()}",tk)
            save_employees(data.get("employees") or [])
            save_toolbox_topic(data.get("toolbox_topic") or {})
            save_maintenance_items(data.get("maintenance_items") or [])
            for k in ("dashboard","maintenance_plan","timesheet"):
                save_setting(k,json.dumps(data.get(k) or {},ensure_ascii=False))
            save_setting("alerts",json.dumps(data.get("alerts") or [],ensure_ascii=False))
            p=data.get("profile") or {}
            if p.get("label"): save_setting("profile_label",p["label"])
            if data.get("drilling_equipment"):
                cache_drilling_equipment(data["drilling_equipment"])
        except Exception: pass
        # Sync attendance + toolbox for last 3 months
        from datetime import timedelta
        months=[]
        d=date.today().replace(day=1)
        for _ in range(3):
            months.append(d.strftime("%Y-%m"))
            d=(d-timedelta(days=1)).replace(day=1)
        for m in months:
            try:
                md=request_json(f"{addr}/api/mobile/data?month={m}",tk)
                save_synced_month_data(m,md.get("attendance") or [],md.get("toolbox") or [])
            except Exception: pass
        save_setting("last_sync",json.dumps({"at":datetime.now().isoformat(timespec="seconds")},ensure_ascii=False))
        # Auto-download timesheets (xlsx + pdf) for last 3 months
        ts_dir=MOBILE_DIR/"timesheets"
        ts_dir.mkdir(parents=True,exist_ok=True)
        for m in months:
            for fmt in ("xlsx","pdf"):
                existing=[r for r in list_saved_timesheets() if r["month"]==m and r["format"]==fmt]
                if existing and Path(existing[0]["filepath"]).exists():
                    continue
                try:
                    data_bytes=request_bytes(f"{addr}/api/mobile/timesheet/export?month={m}&format={fmt}",tk,timeout=60)
                    fpath=ts_dir/f"timesheet_{m}.{fmt}"
                    fpath.write_bytes(data_bytes)
                    save_timesheet_record(m,fmt,str(fpath),len(data_bytes))
                except Exception: pass

    def _enter_app():
        page.bgcolor=BG
        nb=ft.NavigationBar(selected_index=0,bgcolor=NAV,indicator_color=f"#40{BLUE[1:]}",elevation=0,shadow_color="#00000066",
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD_ROUNDED,label="Accueil"),
                ft.NavigationBarDestination(icon=ft.Icons.HEALTH_AND_SAFETY_OUTLINED,
                    selected_icon=ft.Icons.HEALTH_AND_SAFETY_ROUNDED,label="Sécurité"),
                ft.NavigationBarDestination(icon=ft.Icons.HANDYMAN_OUTLINED,
                    selected_icon=ft.Icons.HANDYMAN_ROUNDED,label="Maintenance"),
                ft.NavigationBarDestination(icon=ft.Icons.GROUPS_OUTLINED,
                    selected_icon=ft.Icons.GROUPS_ROUNDED,label="Personnel"),
                ft.NavigationBarDestination(icon=ft.Icons.PERSON_OUTLINE,
                    selected_icon=ft.Icons.PERSON_ROUNDED,label="Profil"),
            ],on_change=_nav_ch)
        page.navigation_bar=nb
        if _navref: _navref[0]=nb
        else: _navref.append(nb)
        _refresh_all(); go_to("home")
        _start_bg_sync()

    def _offline(e=None): _enter_app(); page.update()

    # ── Background auto-sync (silent, every 5 min) ────────────────────────────
    _bg_sync_active = [False]

    def _bg_sync_loop():
        import time as _time
        while _bg_sync_active[0]:
            _time.sleep(270)  # ~4.5 min — stays within Flet cache window
            if not _bg_sync_active[0]: break
            try:
                addr=get_setting("server_url")
                tk=get_setting("token")
                sess=get_setting("mobile_session")
                if not addr or not tk or not sess: continue
                addr=addr.rstrip("/")
                # Upload pending records
                pending_a=list(list_pending())
                pending_t=list(list_pending_toolbox())
                pending_m=list(list_pending_maintenance())
                if pending_a or pending_t or pending_m:
                    payload={
                        "device_id":get_setting("device_id") or "",
                        "device_name":get_setting("device_name") or "Terrain",
                        "attendances":[{"local_id":r["id_pending"],"employee_id":r["employee_id"],
                            "employee_name":r["employee_name"],"date_presence":r["date_presence"],
                            "status":r["status"],"heure_entree":r["heure_entree"],
                            "heure_sortie":r["heure_sortie"]} for r in pending_a],
                        "toolbox_confirmations":[{"local_id":r["id_pending"],"date_theme":r["date_theme"],
                            "theme":r["theme"],"facilitator":r["facilitator"],"site_id":r["site_id"],
                            "attendees_count":r["attendees_count"],"comments":r["comments"]} for r in pending_t],
                        "maintenance_observations":[{"local_id":r["id_pending"],
                            "observation_date":r["observation_date"],"equipment_label":r["equipment_label"],
                            "site_id":r["site_id"],"priority":r["priority"],"observation":r["observation"]}
                            for r in pending_m],
                        "incidents":[],"ppe_checks":[],"observations":[],
                    }
                    result=post_json(f"{addr}/api/mobile/sync",tk,payload,timeout=20)
                    accepted=result.get("accepted") or {}
                    if accepted.get("attendances"): clear_pending(list(accepted["attendances"]),"pending_attendance")
                    if accepted.get("toolbox"): clear_pending(list(accepted["toolbox"]),"pending_toolbox")
                    if accepted.get("maintenance"): clear_pending(list(accepted["maintenance"]),"pending_maintenance")
                # Download month data
                month=date.today().strftime("%Y-%m")
                md=request_json(f"{addr}/api/mobile/data?month={month}",tk,timeout=20)
                save_synced_month_data(month,md.get("attendance") or [],md.get("toolbox") or [])
                save_setting("last_sync",json.dumps({"month":month,"at":datetime.now().isoformat(timespec="seconds")},ensure_ascii=False))
                _refresh_all()
                try: page.update()
                except Exception: pass
            except Exception:
                pass  # silent — offline is normal

    def _start_bg_sync():
        import threading as _thr
        if _bg_sync_active[0]: return
        _bg_sync_active[0]=True
        t=_thr.Thread(target=_bg_sync_loop,daemon=True)
        t.start()

    def _stop_bg_sync():
        _bg_sync_active[0]=False

    def do_sync(e=None):
        busy(True, "Synchronisation en cours...")
        try:
            req_sess(); addr=validate_url()
            ra=list(list_pending()); rt=list(list_pending_toolbox())
            rm=list(list_pending_maintenance()); ri=list_pending_incidents()
            rp=list_pending_ppe_checks(); ro=list_pending_observations()
            if not(len(ra)+len(rt)+len(rm)+len(ri)+len(rp)+len(ro)):
                notify("Aucun élément en attente.",MUT); return
            payload={
                "device_id":get_setting("device_id") or str(uuid4()),
                "device_name":srv_device.value,
                "attendances":[{"local_id":r["id_pending"],"employee_id":r["employee_id"],
                    "employee_name":r["employee_name"],"date_presence":r["date_presence"],
                    "status":r["status"],"heure_entree":r["heure_entree"],
                    "heure_sortie":r["heure_sortie"]} for r in ra],
                "toolbox_confirmations":[{"local_id":r["id_pending"],"date_theme":r["date_theme"],
                    "theme":r["theme"],"facilitator":r["facilitator"],"site_id":r["site_id"],
                    "attendees_count":r["attendees_count"],"comments":r["comments"]} for r in rt],
                "maintenance_observations":[{"local_id":r["id_pending"],
                    "observation_date":r["observation_date"],"equipment_label":r["equipment_label"],
                    "site_id":r["site_id"],"priority":r["priority"],"observation":r["observation"]}
                    for r in rm],
                "incidents":[{"local_id":r["id_pending"],"type_evenement":r["type_evenement"],
                    "date_heure":r["date_heure"],"lieu":r["lieu"],"description":r["description"],
                    "gravite":r["gravite"],"employe_name":r["employe_name"],
                    "employe_id":r["employe_id"],"action_immediate":r["action_immediate"]} for r in ri],
                "ppe_checks":[{"local_id":r["id_pending"],"check_date":r["check_date"],
                    "employe_name":r["employe_name"],"employe_id":r["employe_id"],
                    "resultats":json.loads(r["resultats_json"] or "{}"),"statut_global":r["statut_global"],
                    "observations":r["observations"]} for r in rp],
                "observations":[{"local_id":r["id_pending"],"obs_date":r["obs_date"],
                    "lieu":r["lieu"],"type_obs":r["type_obs"],"description":r["description"],
                    "priorite":r["priorite"],"action_requise":bool(r["action_requise"]),
                    "notes":r["notes"]} for r in ro],
                "drilling_reports":[{
                    "uuid": r["uuid"], "shift": r["shift"], "report_date": r["report_date"],
                    "rig_type": r["rig_type"], "rig_number": r["rig_number"],
                    "contract_location": r["contract_location"], "hole_number": r["hole_number"],
                    "angle": r["angle"], "client": r["client"],
                    "total_advance": r["total_advance"],
                    "diesel": r["diesel"], "refueler_name": r["refueler_name"],
                    "operator_name": r["operator_name"], "supervisor_name": r["supervisor_name"],
                    "entries": r["entries"], "status": r["status"],
                } for r in list_pending_drilling() if r.get("status") == "validated"],
            }
            data=post_json(f"{addr}/api/mobile/sync",get_setting("token") or srv_token.value,payload)
            acc=data.get("accepted") or {}
            # Clear synced drilling reports by UUID
            for synced_uuid in (acc.get("drilling_reports") or []):
                delete_pending_drilling(synced_uuid)
            if acc:
                for k,v in [("attendance",ra),("toolbox",rt),("maintenance",rm),
                            ("incidents",ri),("ppe_checks",rp),("observations",ro)]:
                    clear_pending_ids(k,acc.get(k) or [])
            elif data.get("status")=="applied":
                clear_pending(); clear_pending_toolbox(); clear_pending_maintenance()
                for k,rr in [("incidents",ri),("ppe_checks",rp),("observations",ro)]:
                    clear_pending_ids(k,[r["id_pending"] for r in rr])
            notify(f"Sync : {data.get('applied',0)} appliqué(s).",OK)
        except Exception as exc: notify(f"Sync : {exc}",DNG)
        finally: _refresh_all(); busy(False)

    # ── Save Offline ──────────────────────────────────────────────────────────
    def save_att(e=None, go_next=False):
        try:
            eid=int(att_emp.value or 0); emp=get_employee(eid)
            if not emp: raise ValueError("Sélectionne un employé.")
            status=ATT.get("status","present")
            name=employee_name(emp); dt=att_date.value
            existing=get_mobile_connection().execute(
                "SELECT id_pending FROM pending_attendance WHERE employee_id=? AND date_presence=?",
                (eid,dt)).fetchone()
            def do_save(_=None):
                with get_mobile_connection() as c:
                    if existing:
                        c.execute("DELETE FROM pending_attendance WHERE employee_id=? AND date_presence=?",
                                  (eid,dt))
                    c.execute("INSERT INTO pending_attendance(employee_id,employee_name,"
                        "date_presence,status,heure_entree,heure_sortie) VALUES(?,?,?,?,?,?)",
                        (eid,name,dt,status,
                         att_in.value if status=="present" else None,
                         att_out.value if status=="present" else None))
                att_stat.value=status
                notify(f"{name} — {status.replace('_',' ').title()} enregistré.",OK)
                _refresh_all()
                if go_next:
                    att_emp.value=None; ATT["status"]="present"
                    ATT["emp_name"]=""; go_to("attendance")
                else:
                    go_to("home")
            if existing:
                confirm(
                    "Pointage déjà existant",
                    f"Un pointage existe déjà pour {name} le {dt}.\nRemplacer par « {status.replace('_',' ').title()} » ?",
                    do_save, danger=True, yes_lbl="Remplacer"
                )
            else:
                confirm(
                    "Confirmer le pointage",
                    f"Enregistrer « {status.replace('_',' ').title()} » pour {name} le {dt} ?",
                    do_save, yes_lbl="Enregistrer"
                )
        except Exception as exc: notify(str(exc),DNG)

    def save_tb(e=None):
        try:
            today=date.today().isoformat(); topic=get_toolbox_cache(today)
            if not topic: raise ValueError("Aucune donnée Toolbox pour aujourd'hui.")
            n=ST.get("attendees",0)
            theme_lbl=str(topic["theme"] or "—").split(" / ")[0].strip()
            def do_save(_=None):
                with get_mobile_connection() as c:
                    c.execute("INSERT INTO pending_toolbox(date_theme,theme,facilitator,"
                        "site_id,attendees_count,comments) VALUES(?,?,?,?,?,?)",
                        (today,topic["theme"],topic["facilitator"],topic["site_id"],
                         n,tb_cmt.value))
                tb_cmt.value=""; ST["attendees"]=0
                notify("Toolbox confirmé offline.",OK); _refresh_all()
            confirm("Confirmer la session Toolbox",
                    f"Thème : {theme_lbl}\n{n} participant(s) enregistré(s)",
                    do_save, yes_lbl="Confirmer")
        except Exception as exc: notify(str(exc),DNG)

    def save_mi(e=None):
        try:
            equip=str(mi_eq.value or "").strip(); obs=str(mi_obs.value or "").strip()
            if not equip: raise ValueError("Sélectionnez un équipement.")
            if not obs:   raise ValueError("La description est obligatoire.")
            tp=mi_type.value or "corrective"; prio=mi_prio.value or "haute"
            statut=mi_statut_ot.value or "ouvert"; cause=mi_cause.value or None
            tech=str(mi_tech.value or "").strip() or None
            try: duree=float(mi_duree.value or 0)
            except ValueError: duree=0.0
            type_lbl={"preventive":"Préventive","corrective":"Corrective",
                      "inspection":"Inspection","vidange":"Vidange",
                      "ameliorative":"Améliorative"}.get(tp,tp.title())
            km_part=(f" | Compteur : {mi_km.value.strip()} km" if str(mi_km.value or "").strip() else "")
            full_obs=f"[{type_lbl}] {obs}{km_part}"
            site_id_val=cj("dashboard",{}).get("site_id") or None
            obs_date=str(mi_date.value or date.today().isoformat()).strip() or date.today().isoformat()
            stat_lbl=STATUT_OT_LABELS.get(statut,"Ouvert")
            def do_save(_=None):
                with get_mobile_connection() as c:
                    cur = c.execute(
                        "INSERT INTO pending_maintenance(observation_date,equipment_label,"
                        "site_id,priority,observation,type_intervention,"
                        "statut_ot,cause_racine,duree_heures,technicien) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (obs_date,equip,site_id_val,prio,full_obs,tp,
                         statut,cause,duree,tech))
                    new_id = cur.lastrowid or 0
                save_ot_history(new_id, statut,
                                f"OT créé — {type_lbl}", tech or "")
                mi_obs.value=""; mi_km.value=""; mi_duree.value=""; mi_tech.value=""
                mi_date.value=date.today().isoformat(); mi_eq.value=None
                mi_statut_ot.value="ouvert"; mi_cause.value=None
                notify("Intervention enregistrée offline.",OK)
                _refresh_all(); go_to("maintenance")
            confirm("Confirmer l'intervention",
                    f"[{type_lbl}] {prio.title()} | {stat_lbl} | {equip}",
                    do_save, yes_lbl="Enregistrer")
        except Exception as exc: notify(str(exc),DNG)

    def save_ins(e=None):
        try:
            equip=str(ins_eq.value or "").strip()
            if not equip: raise ValueError("Sélectionne un équipement.")
            ok_items=[it for it,v in ins_chk.items() if v]
            obs=f"Inspection {equip}. OK: {', '.join(ok_items) or 'Aucun'}"
            with get_mobile_connection() as c:
                c.execute("INSERT INTO pending_maintenance(observation_date,equipment_label,"
                    "site_id,priority,observation) VALUES(?,?,NULL,'haute',?)",
                    (date.today().isoformat(),equip,obs))
            notify("Inspection enregistrée offline.",OK); go_to("maintenance")
        except Exception as exc: notify(str(exc),DNG)

    def save_inc(e=None):
        try:
            desc=str(inc_desc.value or "").strip()
            lieu=str(inc_lieu.value or "").strip()
            if not desc: raise ValueError("Description obligatoire.")
            if not lieu: raise ValueError("Lieu / Zone obligatoire.")
            eid=inc_emp.value; enm=""
            if eid:
                emp=get_employee(int(eid)); enm=employee_name(emp) if emp else ""
            type_lbl=TYPE_INC_LABELS.get(ST["inc_type"],ST["inc_type"])
            grav_lbl=GRAVITE_LABELS.get(ST["inc_grav"],ST["inc_grav"])
            def do_save(_=None):
                save_pending_incident({"type_evenement":ST["inc_type"],"date_heure":inc_date.value,
                    "lieu":lieu,"description":desc,"gravite":ST["inc_grav"],
                    "employe_name":enm,"employe_id":int(eid) if eid else None,
                    "action_immediate":str(inc_act.value or "").strip()})
                inc_desc.value=""; inc_lieu.value=""; inc_act.value=""
                inc_emp.value=None; inc_date.value=datetime.now().strftime("%Y-%m-%d %H:%M")
                ST["inc_type"]="accident"; ST["inc_grav"]="mineur"
                _toggle(inc_tr,"inc_type",TYPE_INC_LABELS,TYPE_INC_COLORS)
                _toggle(inc_gr,"inc_grav",GRAVITE_LABELS,GRAVITE_COLORS)
                notify("Incident enregistré offline.",OK); go_to("alerts")
            confirm("Enregistrer l'incident",
                    f"Type : {type_lbl} · Gravité : {grav_lbl}\nLieu : {lieu}",
                    do_save, danger=True, yes_lbl="Enregistrer")
        except Exception as exc: notify(str(exc),DNG)

    def save_ppe(e=None):
        try:
            eid=ppe_emp.value
            if not eid: raise ValueError("Sélectionne un employé.")
            emp=get_employee(int(eid)); enm=employee_name(emp) if emp else ""
            res=dict(ST["ppe"])
            nok=[lbl for lbl,v in res.items() if v=="nok"]
            ok_=[lbl for lbl,v in res.items() if v=="ok"]
            statut="non_conforme" if nok else "conforme"
            def do_save(_=None):
                save_pending_ppe_check({"check_date":date.today().isoformat(),"employe_name":enm,
                    "employe_id":int(eid),"resultats":res,"statut_global":statut,
                    "observations":ppe_obs.value})
                ppe_emp.value=None; ppe_obs.value=""
                ST["ppe"]={lbl:"na" for lbl,_ in PPE_ITEMS}; _rebuild_ppe()
                color=DNG if nok else OK
                msg=(f"Non conforme : {', '.join(nok)}" if nok
                     else f"Conforme — {len(ok_)} EPI vérifiés")
                notify(msg,color); go_to("profile")
            confirm("Enregistrer la vérification EPI",
                    f"Employé : {enm}\n{len(ok_)} OK · {len(nok)} NOK",
                    do_save, danger=bool(nok),
                    yes_lbl="Enregistrer")
        except Exception as exc: notify(str(exc),DNG)

    def save_ppe_assign(items_sel: dict, e=None):
        try:
            eid=ppa_emp.value
            if not eid: raise ValueError("Sélectionnez un employé.")
            chosen=[lbl for lbl,sel in items_sel.items() if sel]
            if not chosen: raise ValueError("Sélectionnez au moins un équipement.")
            emp=get_employee(int(eid)); enm=employee_name(emp) if emp else ""
            taille=ppa_tail.value or ""; obs=ppa_obs.value or ""
            def do_assign(_=None):
                save_pending_ppe_assign({
                    "assign_date": date.today().isoformat(),
                    "employe_name": enm, "employe_id": int(eid),
                    "items": chosen, "taille": taille, "observations": obs,
                })
                ppa_emp.value=None; ppa_obs.value=""; ppa_tail.value=""
                notify(f"Dotation enregistrée pour {enm} ({len(chosen)} EPI).",OK)
                go_to("home")
            items_txt=", ".join(chosen[:3])+("…" if len(chosen)>3 else "")
            confirm("Confirmer la dotation EPI",
                    f"Attribuer {len(chosen)} EPI à {enm} ?\n{items_txt}",
                    do_assign, yes_lbl="Attribuer")
        except Exception as exc: notify(str(exc),DNG)

    # ── Render ────────────────────────────────────────────────────────────────
    def _r_home():
        dash=cj("dashboard"); tot=total_pending()
        today=date.today().isoformat(); topic=get_toolbox_cache(today)
        def _kv(k): v=dash.get(k); return str(v) if v is not None else "–"
        eq=_kv("equipment_active")
        iv=_kv("interventions_open")
        rt=_kv("en_retard")
        al=_kv("alertes_ouvertes")
        def _stat(val,lbl,color,icon):
            # Compact stat: icon + bold number + small label, vertically centered
            return ft.Container(expand=True,padding=P(4,0,4,0),
                content=ft.Column([
                    ft.Row([ft.Icon(icon,color=color,size=15)],
                           alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text(val,size=20,weight=ft.FontWeight.BOLD,color=color,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(lbl,size=9,color=MUT,text_align=ft.TextAlign.CENTER,
                            weight=ft.FontWeight.W_500),
                ],spacing=3,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))
        def _sep():
            return ft.Container(width=1,height=36,bgcolor=BRD)
        h_stats.content=ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(),
            border=ft.Border.all(1,BRD),padding=P(12,14,12,14),
            content=ft.Row([
                _stat(eq,"Équipements",BLUE,ft.Icons.HANDYMAN_OUTLINED),_sep(),
                _stat(iv,"Interventions",WARN,ft.Icons.BUILD_CIRCLE_OUTLINED),_sep(),
                _stat(rt,"En retard",DNG,ft.Icons.WARNING_AMBER_OUTLINED),_sep(),
                _stat(al,"Alertes",INFO,ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            ],spacing=0))
        if topic:
            raw=str(topic["theme"] or ""); nom=raw.split(" / ")[0].strip() if " / " in raw else raw
            done=any(r["date_theme"]==today for r in list_pending_toolbox())
            h_tb.visible=True
            h_tb.content=ft.Container(
                gradient=ft.LinearGradient(begin=AL(-1,-1),end=AL(1,1),
                    colors=["#EFF6FF","#DBEAFE"]),
                border=ft.Border.all(1,f"#30{BLUE[1:]}"),border_radius=16,padding=P(14,14,14,14),
                ink=True,on_click=lambda e:go_to("toolbox"),
                content=ft.Row([
                    ft.Container(bgcolor=BLUE,border_radius=12,width=48,height=48,
                        alignment=AL(0,0),
                        content=ft.Icon(ft.Icons.RECORD_VOICE_OVER_ROUNDED,color="#FFFFFF",size=24)),
                    ft.Column([
                        ft.Text("Toolbox du jour",size=11,color=BLUE,weight=ft.FontWeight.W_600),
                        ft.Text(nom,size=13,weight=ft.FontWeight.BOLD,color=TXT,
                                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([_dot(OK if done else WARN,6),
                            ft.Text("Confirmé" if done else f"Facil. : {topic['facilitator'] or '-'}",
                                    size=11,color=OK if done else MUT)],spacing=5),
                    ],spacing=2,expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,color=BLUE,size=20),
                ],spacing=12))
        else: h_tb.visible=False
        all_a=cj("alerts",[])
        if not isinstance(all_a,list): all_a=[]
        crit=[a for a in all_a if a.get("niveau") in {"critique","haut"}][:3]
        h_alr.controls=([_ac_alert(a) for a in crit] or [
            ft.Container(bgcolor="#F0FDF4",border_radius=12,padding=P(14,12,14,12),
                border=ft.Border.all(1,f"#33{OK[1:]}"),
                content=ft.Row([_box(ft.Icons.CHECK_CIRCLE_OUTLINE_OUTLINED,OK,32,16),
                    ft.Text("Aucune alerte critique",size=13,color=OK,expand=True)],spacing=10))])

    def _r_maint():
        emps=list_employees()
        opts=[ft.dropdown.Option(str(e["id_employe"]),
              f"{employee_name(e)} — {e['site'] or '-'}") for e in emps]
        for dd in (att_emp,inc_emp,ppe_emp,ppa_emp): dd.options=opts
        items=list_maintenance_cache()
        mi_eq.options=[ft.dropdown.Option(str(i["equipment_label"]),str(i["equipment_label"])) for i in items]
        ins_eq.options=mi_eq.options
        m_col.controls=([_eq_card(i) for i in items] or [
            ft.Container(bgcolor=CARD,border_radius=14,padding=P(24,24,24,24),shadow=SH(),
                content=ft.Column([_box(ft.Icons.HANDYMAN_OUTLINED,MUT,48,24),
                    ft.Text("Aucun équipement disponible",size=14,color=MUT,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text("Télécharge les données depuis Profil > Paramètres",
                            size=12,color=MUT,text_align=ft.TextAlign.CENTER)],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=8,tight=True))])

    def _r_toolbox():
        today=date.today().isoformat(); topic=get_toolbox_cache(today); n=ST.get("attendees",0)
        if topic:
            raw=str(topic["theme"] or ""); nom=raw.split(" / ")[0].strip() if " / " in raw else raw
            done=any(r["date_theme"]==today for r in list_pending_toolbox())
            def _cnt(d): ST["attendees"]=max(0,int(ST.get("attendees",0))+d); _r_toolbox(); go_to("toolbox")
            tb_today.controls=[_card(ft.Column([
                ft.Row([_box(ft.Icons.RECORD_VOICE_OVER_OUTLINED,BLUE,48,24),
                    ft.Column([ft.Text("Thème du jour",size=11,color=MUT),
                        ft.Text(nom,size=16,weight=ft.FontWeight.BOLD,color=TXT),
                        ft.Text(f"Facilitateur : {topic['facilitator'] or '-'}",size=12,color=MUT)],
                        spacing=2,expand=True)],spacing=12),
                _div(),
                ft.Row([
                    ft.Container(expand=True,content=ft.Column([
                        ft.Text("Participants",size=11,color=MUT,text_align=ft.TextAlign.CENTER),
                        ft.Text(str(n),size=32,weight=ft.FontWeight.BOLD,color=BLUE,
                                text_align=ft.TextAlign.CENTER),
                        ft.Row([
                            ft.Container(bgcolor=f"#18{DNG[1:]}",border_radius=8,padding=P(12,6,12,6),
                                ink=True,on_click=lambda e:_cnt(-1),
                                content=ft.Icon(ft.Icons.REMOVE,color=DNG,size=18)),
                            ft.Container(bgcolor=f"#18{OK[1:]}",border_radius=8,padding=P(12,6,12,6),
                                ink=True,on_click=lambda e:_cnt(1),
                                content=ft.Icon(ft.Icons.ADD,color=OK,size=18)),
                        ],spacing=8,alignment=ft.MainAxisAlignment.CENTER)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=4,tight=True)),
                    ft.Container(width=1,height=70,bgcolor=BRD),
                    ft.Container(expand=True,content=ft.Column([
                        ft.Text("Statut",size=11,color=MUT,text_align=ft.TextAlign.CENTER),
                        ft.Container(bgcolor=f"#18{OK[1:]}" if done else f"#18{WARN[1:]}",
                            border_radius=10,padding=P(8,6,8,6),
                            content=ft.Text("Validé ✓" if done else "En cours",
                                size=13,weight=ft.FontWeight.BOLD,
                                color=OK if done else WARN,
                                text_align=ft.TextAlign.CENTER))],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=6,tight=True)),
                ],spacing=16),
                tb_cmt,
                _btn("Confirmer la session" if not done else "✓ Déjà confirmé",
                     ft.Icons.CHECK_CIRCLE_OUTLINED if not done else ft.Icons.DONE_ALL_OUTLINED,
                     OK if not done else MUT, save_tb if not done else None,48),
            ],spacing=14),P(16,16,16,16))]
        else:
            tb_today.controls=[_card(ft.Column([_box(ft.Icons.INFO_OUTLINE,MUT,48,24),
                ft.Text("Aucun thème pour aujourd'hui",size=14,color=MUT,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Profil > Télécharger les données",size=12,color=MUT,
                        text_align=ft.TextAlign.CENTER)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=8,tight=True),P(24,24,24,24))]
        hist=list_toolbox_history(7)
        tb_hist.controls=[_tb_hrow(r) for r in hist if r["date_theme"]!=today] or [
            ft.Text("Aucun historique.",size=12,color=MUT)]

    def _r_alerts():
        tab=ST.get("alerts_tab","all"); all_a=cj("alerts",[])
        if not isinstance(all_a,list): all_a=[]
        filtered={"all":all_a,"critique":[a for a in all_a if a.get("niveau") in {"critique","haut"}],
                  "urgent":[a for a in all_a if a.get("niveau") in {"urgent","moyen"}],
                  "info":[a for a in all_a if a.get("niveau") in {"info","bas"}]}.get(tab,all_a)
        al_col.controls=([_ac_alert(a) for a in filtered[:25]] or [
            ft.Container(bgcolor=f"#0C{OK[1:]}",border_radius=14,padding=P(20,20,20,20),
                border=ft.Border.all(1,f"#33{OK[1:]}"),
                content=ft.Row([_box(ft.Icons.NOTIFICATIONS_NONE_OUTLINED,OK,36,18),
                    ft.Text("Aucune alerte dans cette catégorie.",size=13,color=OK,expand=True)],spacing=10))])
        try: al_col.update()
        except Exception: pass

    def _r_ppe(): ep_col.controls=[_ppe_row(nm,ic,cl) for nm,ic,cl in PPE_CATALOGUE]

    def _r_profile():
        srv=bool(get_setting("server_url") and get_setting("token")); tot=total_pending()
        last=cj("last_sync")
        last_lbl=("Sync auto — "+last.get("at","?")[:16].replace("T"," ") if last
                  else "Jamais synchronisé")
        def _ask_logout(e=None):
            confirm("Déconnexion","Vous serez déconnecté. Les données non synchronisées restent en attente.",
                    do_logout,danger=True,yes_lbl="Déconnecter")
        pr_col.controls=[
            _tile("Paramètres serveur",ft.Icons.SETTINGS_ETHERNET_OUTLINED,
                  "Configuré" if srv else "Non configuré",BLUE if srv else DNG,
                  lambda e:go_to("settings")),
            _tile(f"Sync ({tot} en attente)" if tot else "Synchronisation",ft.Icons.CLOUD_SYNC_OUTLINED,
                  (f"{tot} élément(s) en attente — appuyer pour envoyer" if tot else last_lbl),
                  WARN if tot else OK,do_sync),
            _tile("Pointage",ft.Icons.HOW_TO_REG_OUTLINED,"Enregistrer une présence",OK,
                  lambda e:go_to("attendance")),
            _tile("Vérification EPI",ft.Icons.SAFETY_CHECK_OUTLINED,
                  "Contrôler un employé sur le terrain",INFO,lambda e:go_to("ppe_check")),
            _tile("Déclarer un incident",ft.Icons.WARNING_AMBER_OUTLINED,
                  "Accident / Presqu'accident / Observation",DNG,lambda e:go_to("incident")),
            _div(),
            _tile("Déconnexion",ft.Icons.LOGOUT_OUTLINED,"Terminer la session en cours",DNG,
                  _ask_logout,red=True)]

    def _refresh_all():
        _r_home(); _r_maint(); _r_toolbox(); _r_alerts(); _r_ppe(); _r_profile()
        _rebuild_ppe(); _rebuild_ins()
        _toggle(inc_tr,"inc_type",TYPE_INC_LABELS,TYPE_INC_COLORS)
        _toggle(inc_gr,"inc_grav",GRAVITE_LABELS,GRAVITE_COLORS)

    # ── Card Builders ─────────────────────────────────────────────────────────
    def _eq_card(item):
        label=str(item["equipment_label"] or "—"); prio=str(item["priority"] or "")
        status=str(item["status"] or "ok"); plan=str(item["planned_date"] or "—")
        ico=_equip_icon(label); s=status.lower()
        sc=(DNG if s in ("en_retard","overdue","retard") else
            WARN if s in ("a_surveiller","warning","bientot") else OK)
        pc=PRIO_COLORS.get(prio,MUT)
        return ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(6,"0A"),
            ink=True,on_click=lambda e,l=label:[mi_eq.__setattr__("value",l),go_to("intervention")],
            content=ft.Row([
                ft.Container(width=5,bgcolor=sc,border_radius=14),
                ft.Container(expand=True,padding=P(12,14,14,14),
                    content=ft.Row([
                        _box(ico,pc,46,23),
                        ft.Column([
                            ft.Text(label,size=13,weight=ft.FontWeight.BOLD,color=TXT,
                                    max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row([_box(ft.Icons.CALENDAR_TODAY_OUTLINED,MUT,16,12),
                                    ft.Text(f"Prévu : {plan}",size=11,color=MUT)],spacing=4),
                            ft.Row([_dot(pc,6),ft.Text(f"Priorité {prio or '—'}",size=11,
                                    color=pc,weight=ft.FontWeight.W_600)],spacing=6)],
                            spacing=3,expand=True),
                        ft.Column([_sbadge(status),
                            _box(ft.Icons.CHEVRON_RIGHT_OUTLINED,BRD,26,16)],
                            spacing=4,horizontal_alignment=ft.CrossAxisAlignment.END)],spacing=10))],
                spacing=0,tight=True))

    def _ac_alert(a):
        niv=str(a.get("niveau") or "info")
        color=(DNG if niv in {"critique","haut"} else WARN if niv in {"urgent","moyen"} else INFO)
        ico=(ft.Icons.ERROR_OUTLINE if niv in {"critique","haut"} else
             ft.Icons.WARNING_AMBER_OUTLINED if niv in {"urgent","moyen"} else ft.Icons.INFO_OUTLINE)
        niv_l={"critique":"Critique","haut":"Élevée","urgent":"Urgent",
               "moyen":"Moyen","info":"Info","bas":"Bas"}.get(niv,niv.title())
        src=str(a.get("source") or a.get("type_alerte") or "Alerte")
        msg=str(a.get("message") or "—")
        def _show(e):
            page.show_dialog(ft.AlertDialog(
                modal=True, bgcolor=CARD,
                title=ft.Row([ft.Icon(ico,color=color,size=20),
                    ft.Text(f"{src} — {niv_l}",size=14,weight=ft.FontWeight.BOLD,color=TXT)],
                    spacing=8,tight=True),
                content=ft.Text(msg,size=13,color=MUT),
                actions=[ft.FilledButton("Fermer",on_click=lambda _:page.pop_dialog(),
                    bgcolor=color,color="#FFFFFF",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))],
                actions_alignment=ft.MainAxisAlignment.END))
        return ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(5,"08"),
            ink=True,on_click=_show,
            content=ft.Row([
                ft.Container(width=5,bgcolor=color,border_radius=14),
                ft.Container(expand=True,padding=P(12,12,14,12),
                    content=ft.Row([_box(ico,color,38,18),
                        ft.Column([ft.Text(src,size=13,weight=ft.FontWeight.BOLD,color=TXT),
                            ft.Text(msg,size=11,color=MUT,
                                    max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
                            _badge(niv_l,color)],spacing=4,expand=True),
                        _box(ft.Icons.CHEVRON_RIGHT_OUTLINED,BRD,26,16)],spacing=10))],
                spacing=0,tight=True))

    def _tb_hrow(r):
        raw=str(r["theme"] or ""); nom=raw.split(" / ")[0].strip() if " / " in raw else raw
        done=any(p["date_theme"]==r["date_theme"] for p in list_pending_toolbox())
        return ft.Container(bgcolor=CARD,border_radius=10,shadow=SH(3,"06"),padding=P(12,10,12,10),
            content=ft.Row([ft.Container(width=54,content=ft.Text(str(r["date_theme"] or "—"),
                    size=10,color=MUT,weight=ft.FontWeight.W_600)),
                ft.Text(nom,size=12,color=TXT,expand=True,max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS),
                _box(ft.Icons.CHECK_CIRCLE_OUTLINED if done
                     else ft.Icons.RADIO_BUTTON_UNCHECKED_OUTLINED,
                     OK if done else BRD,24,14)],spacing=8))

    def _ppe_row(name,ico,color):
        return ft.Container(bgcolor=CARD,border_radius=12,shadow=SH(4,"07"),padding=P(14,12,14,12),
            content=ft.Row([_box(ico,color,44,22),
                ft.Column([ft.Text(name,size=13,weight=ft.FontWeight.W_600,color=TXT),
                    ft.Text("Disponible sur site",size=11,color=MUT)],spacing=2,expand=True),
                _box(ft.Icons.CHEVRON_RIGHT_OUTLINED,BRD,26,16)],spacing=12))

    # ── Screens ───────────────────────────────────────────────────────────────
    def _s_login():
        srv_panel=ft.Column([srv_url,srv_token,srv_device],spacing=10,tight=True,visible=False)

        def toggle_srv(e=None):
            srv_panel.visible=not srv_panel.visible
            srv_lbl.value="▲ Masquer la configuration" if srv_panel.visible else "⚙ Configuration serveur"
            try: srv_panel.update(); srv_lbl.update()
            except Exception: page.update()

        srv_lbl=ft.Text("⚙ Configuration serveur",size=12,color="#64748B",
                         weight=ft.FontWeight.W_600)

        site_name=get_setting("server_url") and "SYAMA Mining" or "OREZONE Mining"

        return ft.Container(bgcolor="#0A1929",expand=True,padding=P(20,0,20,0),
            content=ft.Column([
                ft.Container(height=48),
                # ── Logo ──────────────────────────────────────────────────────
                ft.Row([
                    ft.Container(width=96,height=96,border_radius=24,
                        bgcolor="#F59E0B",alignment=AL(0,0),shadow=SH(16,"40"),
                        content=ft.Text("O",size=46,weight=ft.FontWeight.BOLD,color="#FFFFFF")),
                ],alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=10),
                ft.Row([ft.Text("OREZONE QHSE",size=26,weight=ft.FontWeight.W_800,color="#E2E8F0")],
                    alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([ft.Text(f"Plateforme QHSE Mobile · {site_name}",size=12,color="#475569")],
                    alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                # ── Identifiants ───────────────────────────────────────────────
                ft.Container(bgcolor="#132337",border_radius=18,
                    border=ft.Border.all(1,"#1E3A5F"),padding=P(20,18,20,18),shadow=SH(16,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(bgcolor="#1E3A5F",border_radius=8,width=32,height=32,
                                alignment=AL(0,0),
                                content=ft.Icon(ft.Icons.PERSON_ROUNDED,color="#93C5FD",size=16)),
                            ft.Text("Connexion",size=14,weight=ft.FontWeight.BOLD,color="#E2E8F0"),
                        ],spacing=10),
                        ft.Container(height=6),
                        lgn_user,lgn_pass,
                        ft.Row([lgn_rem,
                            ft.Text("Se souvenir de moi",color="#64748B",size=12)],spacing=8),
                        lgn_status,
                        ft.Container(height=4),
                        # Se connecter
                        ft.Container(bgcolor=BLUE,border_radius=12,height=52,
                            ink=True,on_click=do_login,alignment=AL(0,0),shadow=SH(10,"35"),
                            content=ft.Row([
                                ft.Icon(ft.Icons.LOGIN_ROUNDED,color="#FFFFFF",size=20),
                                ft.Text("Se connecter",color="#FFFFFF",size=15,
                                        weight=ft.FontWeight.BOLD),
                            ],alignment=ft.MainAxisAlignment.CENTER,spacing=8,tight=True)),
                        # Appairage
                        ft.Container(bgcolor="#1E3A5F",border_radius=12,height=46,
                            ink=True,on_click=show_pairing_dialog,alignment=AL(0,0),
                            border=ft.Border.all(1,"#2563EB55"),
                            content=ft.Row([
                                ft.Icon(ft.Icons.LINK_ROUNDED,color="#93C5FD",size=18),
                                ft.Text("Appairage automatique PC → Mobile",color="#93C5FD",
                                        size=13,weight=ft.FontWeight.W_600),
                            ],alignment=ft.MainAxisAlignment.CENTER,spacing=8,tight=True)),
                        # Mode hors-ligne
                        ft.Container(alignment=AL(0,0),ink=True,on_click=_offline,
                            padding=P(0,6,0,0),
                            content=ft.Text("Continuer hors connexion →",size=12,
                                            color="#475569",text_align=ft.TextAlign.CENTER)),
                    ],spacing=10,tight=True)),
                ft.Container(height=10),
                # ── Config serveur (repliée par défaut) ───────────────────────
                ft.Container(bgcolor="#132337",border_radius=14,
                    border=ft.Border.all(1,"#1E3A5F"),
                    content=ft.Column([
                        ft.Container(
                            ink=True,on_click=toggle_srv,padding=P(16,14,16,14),
                            content=ft.Row([
                                ft.Icon(ft.Icons.SETTINGS_OUTLINED,color="#64748B",size=16),
                                srv_lbl,
                            ],spacing=8)),
                        ft.Container(padding=P(16,0,16,14),content=srv_panel,
                                     visible=True),
                    ],spacing=0,tight=True)),
                ft.Container(height=20),
                ft.Row([ft.Text(f"OREZONE Mining  ·  v{APP_VERSION}",size=11,color="#1E3A5F")],
                    alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=28),
            ],scroll=ft.ScrollMode.AUTO,expand=True,
             horizontal_alignment=ft.CrossAxisAlignment.STRETCH,spacing=0))

    def _s_home():
        MO=["Janv","Févr","Mars","Avr","Mai","Juin","Juil","Août","Sep","Oct","Nov","Déc"]
        JO=["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
        d=date.today()
        date_long=f"{JO[d.weekday()]} {d.day} {MO[d.month-1]} {d.year}"
        dash=cj("dashboard"); site=dash.get("site") or "SYAMA"
        uname=get_setting("identity_username") or ""
        display_name=uname if uname and uname not in ("—","") else "Agent"
        urole=get_setting("profile_label") or "Agent HSE"
        inits="".join(w[0].upper() for w in display_name.split() if w)[:2] or "AG"
        tot=total_pending(); online=bool(get_setting("mobile_session"))

        # ── Sidebar drawer ────────────────────────────────────────────────────
        DRW={"open":False}
        drw_bg   =ft.Container(expand=True,bgcolor="#00000060",visible=False,ink=True)
        drw_panel=ft.Container(visible=False,bgcolor=NAV,width=275,shadow=SH(32,"55"))

        def open_drawer(e=None):
            DRW["open"]=True; drw_bg.visible=True; drw_panel.visible=True
            try: drw_bg.update(); drw_panel.update()
            except Exception: pass
        def close_drawer(e=None):
            DRW["open"]=False; drw_bg.visible=False; drw_panel.visible=False
            try: drw_bg.update(); drw_panel.update()
            except Exception: pass
        drw_bg.on_click=close_drawer

        def _nav_grp(label):
            return ft.Container(padding=P(16,12,16,6),
                content=ft.Text(label,size=9,weight=ft.FontWeight.W_700,
                                color="#3D6B99"))
        def _nav_item(label,icon,color,key):
            def click(e,k=key): close_drawer(); go_to(k)
            return ft.Container(border_radius=10,margin=ft.Margin.symmetric(horizontal=8,vertical=1),
                ink=True,on_click=click,padding=P(10,10,10,10),
                content=ft.Row([
                    ft.Container(bgcolor=f"{color}20",border_radius=8,width=32,height=32,
                        alignment=AL(0,0),content=ft.Icon(icon,color=color,size=16)),
                    ft.Text(label,size=13,weight=ft.FontWeight.W_500,color="#CBD5E1"),
                ],spacing=10))

        drw_panel.content=ft.Column([
            ft.Container(gradient=GRAD,padding=P(20,28,20,18),
                content=ft.Column([
                    ft.Row([
                        ft.Container(bgcolor="#20FFFFFF",border_radius=28,padding=ft.Padding.all(2),
                            content=_ava(inits,48)),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text(display_name,size=15,weight=ft.FontWeight.BOLD,color="#FFFFFF",
                                    max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(urole,size=11,color="#93C5FD"),
                            ft.Row([ft.Icon(ft.Icons.LOCATION_ON_ROUNDED,color="#60A5FA",size=11),
                                    ft.Text(site,size=10,color="#60A5FA")],spacing=3),
                        ],spacing=3,expand=True),
                    ],spacing=0),
                    ft.Container(height=8),
                    ft.Container(bgcolor="#12FFFFFF",border_radius=10,padding=P(10,6,10,6),
                        content=ft.Row([
                            ft.Container(width=8,height=8,bgcolor=OK if online else DNG,border_radius=4),
                            ft.Text(f"{'Connecté' if online else 'Hors-ligne'} · {tot} en attente",
                                    size=11,color="#93C5FD",expand=True),
                        ],spacing=8)),
                ],spacing=0,tight=True)),
            ft.Container(expand=True,
                content=ft.Column([
                    _nav_grp("ACCUEIL"),
                    _nav_item("Tableau de bord",ft.Icons.DASHBOARD_ROUNDED,"#60A5FA","home"),
                    _nav_grp("SÉCURITÉ HSE"),
                    _nav_item("Alertes",ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED,DNG,"alerts"),
                    _nav_item("Incidents",ft.Icons.WARNING_ROUNDED,DNG,"incident"),
                    _nav_item("Vérification EPI",ft.Icons.SAFETY_CHECK_OUTLINED,WARN,"ppe_check"),
                    _nav_item("Dotation EPI",ft.Icons.ASSIGNMENT_TURNED_IN_ROUNDED,OK,"ppe_assign"),
                    _nav_item("Toolbox Talk",ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP,"toolbox"),
                    _nav_item("Inspection véhicule",ft.Icons.FACT_CHECK_ROUNDED,INFO,"inspection"),
                    _nav_grp("MAINTENANCE GMAO"),
                    _nav_item("Tableau maintenance",ft.Icons.HANDYMAN_ROUNDED,BLUE,"maintenance"),
                    _nav_item("Créer un OT",ft.Icons.BUILD_ROUNDED,BLUE,"intervention"),
                    _nav_item("Déclarer une panne",ft.Icons.REPORT_PROBLEM_ROUNDED,DNG,"panne"),
                    _nav_grp("DRILLING"),
                    _nav_item("Drilling Reports",ft.Icons.HARDWARE_OUTLINED,"#1E3A8A","drilling"),
                    _nav_grp("PERSONNEL & RH"),
                    _nav_item("Pointage terrain",ft.Icons.HOW_TO_REG_ROUNDED,OK,"attendance"),
                    _nav_item("Timesheets & Exports",ft.Icons.ARTICLE_OUTLINED,INFO,"timesheet"),
                    _nav_grp("MON COMPTE"),
                    _nav_item("Mon profil",ft.Icons.MANAGE_ACCOUNTS_OUTLINED,INFO,"profile"),
                    _nav_item("Paramètres",ft.Icons.SETTINGS_OUTLINED,MUT,"settings"),
                ],spacing=0,scroll=ft.ScrollMode.AUTO)),
            ft.Container(padding=P(16,8,16,12),
                content=ft.Text("OREZONE QHSE Mobile · v2.0",size=10,color="#2D4A6F",
                                text_align=ft.TextAlign.CENTER)),
        ],spacing=0,expand=True)

        # ── Dashboard KPI data ────────────────────────────────────────────────
        dsh=cj("dashboard")
        def _dkv(k): v=dsh.get(k); return str(v) if v is not None else "—"
        eq  =_dkv("equipment_active")
        iv  =_dkv("interventions_open")
        rt  =_dkv("en_retard")
        al  =_dkv("alertes_ouvertes")

        # ── KPI card ──────────────────────────────────────────────────────────
        def _kpi(val,lbl,color,icon,on_click=None):
            no_data = val in ("—","–","")
            return ft.Container(expand=True,
                gradient=ft.LinearGradient(begin=AL(-1,-1),end=AL(1,1),
                    colors=[CARD,f"{color}18"]),
                border_radius=18,
                shadow=SH(10,"35"),border=ft.border.all(1,f"{color}40"),
                ink=bool(on_click),on_click=on_click,
                padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Row([
                        ft.Container(bgcolor=f"{color}25",border_radius=12,width=38,height=38,
                            alignment=AL(0,0),
                            content=ft.Icon(icon,color=color,size=19)),
                        ft.Container(expand=True),
                        ft.Container(width=8,height=8,
                            bgcolor=MUT if no_data else color,
                            border_radius=4,opacity=0.9),
                    ],spacing=4),
                    ft.Container(height=8),
                    ft.Text(val,size=30,weight=ft.FontWeight.BOLD,
                            color=MUT if no_data else color),
                    ft.Text(lbl,size=10,color=MUT,weight=ft.FontWeight.W_600),
                ],spacing=0,tight=True))

        # ── Module tile (2-col grid) ───────────────────────────────────────────
        def _mod(label,sub,icon,color,key):
            def click(e): go_to(key)
            return ft.Container(expand=True,
                gradient=ft.LinearGradient(begin=AL(-1,-1),end=AL(1,1),
                    colors=[CARD,f"{color}12"]),
                border_radius=16,
                shadow=SH(8,"28"),border=ft.border.all(1,f"{color}38"),
                ink=True,on_click=click,padding=P(16,14,16,14),
                content=ft.Column([
                    ft.Container(bgcolor=f"{color}20",border_radius=12,width=46,height=46,
                        alignment=AL(0,0),
                        content=ft.Icon(icon,color=color,size=23)),
                    ft.Container(height=10),
                    ft.Text(label,size=13,weight=ft.FontWeight.W_700,color=TXT,
                            max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(sub,size=10,color=MUT,max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ],spacing=2,tight=True))

        # ── Domain hub card (large 2-col tile) ────────────────────────────────
        def _domain_card(label, sub, icon, color, key):
            def click(e): go_to(key)
            return ft.Container(expand=True,
                gradient=ft.LinearGradient(begin=AL(-1,-1),end=AL(1,1),
                    colors=[CARD, f"{color}20"]),
                border_radius=18,
                shadow=SH(10,"35"), ink=True, on_click=click,
                border=ft.border.all(1.5, f"{color}45"),
                padding=P(16,14,16,14),
                content=ft.Column([
                    ft.Row([
                        ft.Container(bgcolor=color, border_radius=14,
                            width=48, height=48, alignment=AL(0,0),
                            shadow=SH(8,"30"),
                            content=ft.Icon(icon, color="#FFFFFF", size=24)),
                        ft.Container(expand=True),
                        ft.Container(bgcolor=f"{color}20",border_radius=8,
                            padding=P(6,4,6,4),
                            content=ft.Icon(ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                                            color=color,size=12)),
                    ],spacing=8),
                    ft.Container(height=12),
                    ft.Text(label, size=14, weight=ft.FontWeight.BOLD, color=TXT),
                    ft.Text(sub, size=10, color=MUT, max_lines=2),
                ], spacing=2, tight=True))

        # ── Alert card ─────────────────────────────────────────────────────────
        def _ac_alert(a):
            niv=str(a.get("niveau","") or "").lower()
            c=DNG if niv in ("critique","haut") else WARN if niv in ("urgent","moyen") else INFO
            titre=str(a.get("titre") or a.get("type_alerte") or a.get("source") or "Alerte")
            msg=str(a.get("description") or a.get("message") or "")[:60]
            niv_l={"critique":"Critique","haut":"Élevée","urgent":"Urgent",
                   "moyen":"Moyen","info":"Info","bas":"Bas"}.get(niv,niv.upper() or "?")
            return ft.Container(bgcolor=CARD,border_radius=14,
                border=ft.Border.all(1,f"{c}25"),padding=P(12,10,12,10),
                content=ft.Row([
                    ft.Container(width=4,height=36,bgcolor=c,border_radius=3),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(titre,size=12,
                                weight=ft.FontWeight.W_600,color=TXT,
                                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(msg,size=10,color=MUT,max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ],spacing=2,expand=True),
                    ft.Container(bgcolor=f"{c}15",border_radius=8,padding=P(6,3,6,3),
                        content=ft.Text(niv_l,size=9,color=c,
                                        weight=ft.FontWeight.W_700)),
                ],spacing=0))

        all_a=cj("alerts",[]);
        if not isinstance(all_a,list): all_a=[]
        crit=[a for a in all_a if a.get("niveau") in {"critique","haut"}][:3]

        main_content=ft.Column([
            # ── HEADER ────────────────────────────────────────────────────────
            ft.Container(gradient=GRAD,padding=P(16,18,16,20),shadow=SH(14,"25"),
                content=ft.Column([
                    ft.Row([
                        ft.Container(width=38,height=38,border_radius=12,bgcolor="#18FFFFFF",
                            alignment=AL(0,0),ink=True,on_click=open_drawer,
                            content=ft.Icon(ft.Icons.MENU_ROUNDED,color="#FFFFFF",size=21)),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Text("OREZONE QHSE",size=15,weight=ft.FontWeight.W_800,
                                    color="#FFFFFF"),
                            ft.Text(site,size=10,color="#93C5FD"),
                        ],spacing=0,expand=True),
                        # Status dot
                        ft.Container(bgcolor="#18FFFFFF",border_radius=20,
                            padding=P(8,6,8,6),
                            content=ft.Row([
                                ft.Container(width=6,height=6,bgcolor=OK if online else DNG,
                                    border_radius=3),
                                ft.Text("Online" if online else "Offline",
                                        size=10,color="#FFFFFF",weight=ft.FontWeight.W_600),
                            ],spacing=5,tight=True)),
                        ft.Container(width=6),
                        ft.Container(width=36,height=36,border_radius=18,bgcolor="#1AFFFFFF",
                            alignment=AL(0,0),ink=True,on_click=lambda e:go_to("alerts"),
                            content=ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED,color="#FFFFFF",size=18)),
                        ft.Container(width=6),
                        ft.Container(ink=True,border_radius=20,on_click=lambda e:go_to("profile"),
                            content=_ava(inits,36)),
                    ],spacing=4),
                    ft.Container(height=14),
                    # User greeting block
                    ft.Container(bgcolor="#10FFFFFF",border_radius=16,padding=P(14,12,14,12),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"Bonjour, {display_name} 👋",size=18,
                                        weight=ft.FontWeight.BOLD,color="#FFFFFF"),
                                ft.Container(height=4),
                                ft.Row([
                                    ft.Icon(ft.Icons.CALENDAR_TODAY_ROUNDED,color="#93C5FD",size=12),
                                    ft.Text(date_long,size=11,color="#93C5FD"),
                                ],spacing=5),
                                ft.Row([
                                    ft.Icon(ft.Icons.LOCATION_ON_ROUNDED,color="#60A5FA",size=12),
                                    ft.Text(f"{site} · {urole}",size=11,color="#60A5FA"),
                                ],spacing=5),
                            ],spacing=3,expand=True),
                            ft.Container(
                                bgcolor="#18FFFFFF",border_radius=14,
                                padding=P(10,10,10,10),
                                content=ft.Column([
                                    ft.Text(str(d.day),size=24,weight=ft.FontWeight.BOLD,
                                            color="#FFFFFF",text_align=ft.TextAlign.CENTER),
                                    ft.Text(MO[d.month-1].upper(),size=9,color="#93C5FD",
                                            text_align=ft.TextAlign.CENTER,
                                            weight=ft.FontWeight.W_700),
                                    ft.Text(str(d.year),size=9,color="#7AADDE",
                                            text_align=ft.TextAlign.CENTER),
                                ],spacing=1,horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                tight=True)),
                        ],spacing=12)),
                    # Sync banner (inside header)
                    ft.Container(visible=tot>0,height=0 if tot==0 else None,
                        margin=ft.Margin.only(top=8),
                        content=ft.Container(bgcolor=f"#18{WARN[1:]}",border_radius=10,
                            border=ft.Border.all(1,f"#30{WARN[1:]}"),
                            padding=P(10,7,10,7),
                            content=ft.Row([
                                ft.Icon(ft.Icons.CLOUD_UPLOAD_ROUNDED,color=WARN,size=15),
                                ft.Text(f"{tot} élément(s) en attente de synchronisation",
                                        size=11,color=WARN,expand=True),
                                ft.Container(bgcolor=WARN,border_radius=8,padding=P(8,4,8,4),
                                    ink=True,on_click=do_sync,
                                    content=ft.Text("Sync",size=10,color="#FFFFFF",
                                                    weight=ft.FontWeight.W_700)),
                            ],spacing=8))),
                ],spacing=0,tight=True)),

            # ── BODY ──────────────────────────────────────────────────────────
            ft.Container(expand=True,padding=P(12,14,12,0),
                content=ft.Column([
                    # KPI row (4 cards horizontal)
                    ft.Row([
                        _kpi(eq,"Équipements",BLUE,ft.Icons.HANDYMAN_ROUNDED,
                             lambda e:go_to("maintenance")),
                        _kpi(iv,"Interventions",WARN,ft.Icons.BUILD_CIRCLE_OUTLINED,
                             lambda e:go_to("intervention")),
                        _kpi(rt,"En retard",DNG,ft.Icons.WARNING_AMBER_ROUNDED,
                             lambda e:go_to("maintenance")),
                        _kpi(al,"Alertes",INFO,ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED,
                             lambda e:go_to("alerts")),
                    ],spacing=10),

                    # Toolbox banner (if topic for today)
                    h_tb,

                    # ── DOMAINES MÉTIER ───────────────────────────────────────
                    ft.Row([
                        ft.Container(width=3,height=16,bgcolor=BLUE,border_radius=2),
                        ft.Text("Domaines",size=12,weight=ft.FontWeight.W_700,color=TXT),
                        ft.Container(expand=True),
                    ],spacing=8),
                    ft.Row([
                        _domain_card("Sécurité HSE","Incidents · EPI · Alertes",
                            ft.Icons.HEALTH_AND_SAFETY_ROUNDED,DNG,"securite"),
                        _domain_card("Maintenance","OT · Pannes · Équipements",
                            ft.Icons.HANDYMAN_ROUNDED,BLUE,"maintenance"),
                    ],spacing=10),
                    ft.Row([
                        _domain_card("Personnel","Pointage · Timesheets",
                            ft.Icons.GROUPS_ROUNDED,OK,"personnel"),
                        _domain_card("Toolbox Talk","Causerie du jour",
                            ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP,"toolbox"),
                    ],spacing=10),

                    # ── ALERTES CRITIQUES ─────────────────────────────────────
                    ft.Row([
                        ft.Container(width=3,height=16,bgcolor=DNG,border_radius=2),
                        ft.Text("Alertes critiques",size=12,weight=ft.FontWeight.W_700,
                                color=TXT,expand=True),
                        ft.Container(bgcolor=f"{DNG}18",border_radius=8,padding=P(8,4,8,4),
                            ink=True,on_click=lambda e:go_to("alerts"),
                            content=ft.Text("Voir tout",size=10,color=DNG,
                                            weight=ft.FontWeight.W_600)),
                    ],spacing=8),
                    *(
                        [_ac_alert(a) for a in crit] or [
                            ft.Container(bgcolor=f"#08{OK[1:]}",border_radius=14,
                                border=ft.Border.all(1,f"#25{OK[1:]}"),padding=P(14,12,14,12),
                                content=ft.Row([
                                    ft.Container(bgcolor=f"#18{OK[1:]}",border_radius=10,
                                        width=36,height=36,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                                                        color=OK,size=20)),
                                    ft.Column([
                                        ft.Text("Aucune alerte critique",size=13,
                                                weight=ft.FontWeight.W_600,color=OK),
                                        ft.Text("Situation sous contrôle",size=11,color=MUT),
                                    ],spacing=2,expand=True),
                                ],spacing=10))
                        ]
                    ),
                    ft.Container(height=80),
                ],spacing=12,scroll=ft.ScrollMode.AUTO,expand=True)),
        ],spacing=0,expand=True)

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Stack([
                main_content,
                drw_bg,
                drw_panel,
            ]))

    # ─────────────────────────────────────────────────────────────────────────────
    def _s_securite():
        alerts  = cj("alerts", [])
        if not isinstance(alerts, list): alerts = []
        crits   = [a for a in alerts if str(a.get("niveau","")).lower() in ("critique","haut")]
        n_inc   = len(list_pending_incidents())
        n_ppe   = len(list_pending_ppe_checks())
        n_al    = len(alerts)

        tab_state = {"tab": 0}
        tab_bar   = ft.Row(spacing=4)
        body_col  = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        TABS = [
            ("Alertes",    ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, DNG),
            ("Incidents",  ft.Icons.WARNING_ROUNDED,              WARN),
            ("EPI",        ft.Icons.SAFETY_CHECK_ROUNDED,         OK),
            ("Formation",  ft.Icons.RECORD_VOICE_OVER_ROUNDED,    PURP),
        ]

        def _sec_action(label, sub, icon, color, key):
            return ft.Container(expand=True, bgcolor=CARD, border_radius=16,
                shadow=SH(5,"0A"), ink=True, on_click=lambda e: go_to(key),
                border=ft.Border.all(1, f"#22{color[1:]}"), padding=P(16,14,16,14),
                content=ft.Column([
                    ft.Container(bgcolor=color, border_radius=14,
                        width=48, height=48, alignment=AL(0,0),
                        content=ft.Icon(icon, color="#FFFFFF", size=24)),
                    ft.Container(height=10),
                    ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color=TXT),
                    ft.Text(sub, size=10, color=MUT, max_lines=2),
                ], spacing=2, tight=True))

        def _al_card(a):
            niv = str(a.get("niveau","") or "").lower()
            c   = DNG if niv in ("critique","haut") else WARN if "urgent" in niv else INFO
            src = str(a.get("titre") or a.get("source") or a.get("type_alerte") or "Alerte")
            msg = str(a.get("description") or a.get("message") or "")
            niv_l = {"critique":"Critique","haut":"Élevée","urgent":"Urgent",
                     "moyen":"Moyen","info":"Info","bas":"Bas"}.get(niv, niv.title() or "?")
            ico = (ft.Icons.PRIORITY_HIGH_ROUNDED if niv in ("critique","haut")
                   else ft.Icons.WARNING_AMBER_ROUNDED if "urgent" in niv
                   else ft.Icons.INFO_OUTLINE_ROUNDED)
            def _show(e):
                page.show_dialog(ft.AlertDialog(
                    modal=True, bgcolor=CARD,
                    title=ft.Row([ft.Icon(ico,color=c,size=20),
                        ft.Text(f"{src} — {niv_l}",size=14,
                                weight=ft.FontWeight.BOLD,color=TXT)],spacing=8,tight=True),
                    content=ft.Text(msg, size=13, color=MUT),
                    actions=[ft.FilledButton("Fermer",
                        on_click=lambda _: page.pop_dialog(),
                        bgcolor=c, color="#FFFFFF",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))],
                    actions_alignment=ft.MainAxisAlignment.END))
            return ft.Container(bgcolor=CARD, border_radius=14, shadow=SH(4,"08"),
                border=ft.Border.all(1, f"#25{c[1:]}"), ink=True, on_click=_show,
                padding=P(0,0,0,0),
                content=ft.Row([
                    ft.Container(width=5, bgcolor=c, border_radius=14),
                    ft.Container(expand=True, padding=P(12,12,12,12),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ico, color=c, size=14),
                                ft.Text(src, size=13, weight=ft.FontWeight.BOLD, color=TXT,
                                        expand=True, max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Container(bgcolor=f"#18{c[1:]}", border_radius=8,
                                    padding=P(6,2,6,2),
                                    content=ft.Text(niv_l, size=10, color=c,
                                                    weight=ft.FontWeight.W_700)),
                            ], spacing=6),
                            ft.Text(msg[:80]+("…" if len(msg)>80 else ""),
                                    size=11, color=MUT, max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                        ], spacing=4, tight=True)),
                ], spacing=0, tight=True))

        def _inc_row(r):
            tp  = str(r.get("type_evenement") or "incident")
            grav= str(r.get("gravite") or "mineur")
            lieu= str(r.get("lieu") or "—")
            desc= str(r.get("description") or "")
            dt  = str(r.get("date_heure") or r.get("created_at") or "")[:16]
            gc  = {"grave":DNG,"majeur":DNG,"serieux":WARN,"mineur":OK}.get(grav,MUT)
            gl  = {"grave":"Grave","majeur":"Majeur","serieux":"Sérieux","mineur":"Mineur"}.get(grav,grav.title())
            return ft.Container(bgcolor=CARD, border_radius=14, shadow=SH(4,"08"),
                border=ft.Border.all(1, f"#22{gc[1:]}"), padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Row([
                        ft.Container(bgcolor=f"#18{gc[1:]}", border_radius=8, padding=P(6,2,6,2),
                            content=ft.Text(gl, size=10, color=gc, weight=ft.FontWeight.W_700)),
                        ft.Container(expand=True),
                        ft.Text(dt, size=10, color=MUT),
                    ], spacing=6),
                    ft.Text(desc[:80]+("…" if len(desc)>80 else ""),
                            size=12, color=TXT, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row([ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, color=MUT, size=11),
                            ft.Text(lieu, size=10, color=MUT)], spacing=4),
                ], spacing=5, tight=True))

        def _rebuild_tabs():
            def _t(lbl, ico, c, idx):
                active = tab_state["tab"] == idx
                badge = [n_al, n_inc, n_ppe, 0][idx]
                def click(e, i=idx):
                    tab_state["tab"] = i; _rebuild_tabs(); _rebuild_body()
                return ft.Container(expand=True, border_radius=10,
                    bgcolor=c if active else f"#12{c[1:]}",
                    padding=P(6,8,6,8), ink=True, on_click=click,
                    content=ft.Column([
                        ft.Stack([
                            ft.Icon(ico, color="#FFFFFF" if active else MUT, size=18),
                            *([] if not badge else [ft.Container(
                                width=14, height=14, border_radius=7,
                                bgcolor=DNG, right=0, top=0,
                                alignment=ft.Alignment(0,0),
                                content=ft.Text(str(badge), size=8,
                                    color="#FFFFFF", weight=ft.FontWeight.W_700))]),
                        ]),
                        ft.Text(lbl, size=9, color="#FFFFFF" if active else MUT,
                                weight=ft.FontWeight.W_700,
                                text_align=ft.TextAlign.CENTER),
                    ], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True))
            tab_bar.controls=[_t(l,i,c,idx) for idx,(l,i,c) in enumerate(TABS)]
            try: tab_bar.update()
            except Exception: pass

        def _rebuild_body():
            tab = tab_state["tab"]
            if tab == 0:  # Alertes
                items = ([_al_card(a) for a in alerts] or
                         [ft.Container(bgcolor=f"#0A{OK[1:]}", border_radius=14,
                              border=ft.Border.all(1, f"#25{OK[1:]}"),
                              padding=P(20,16,20,16),
                              content=ft.Column([
                                  ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, color=OK, size=40),
                                  ft.Text("Aucune alerte active", size=14, color=OK,
                                          text_align=ft.TextAlign.CENTER,
                                          weight=ft.FontWeight.W_600),
                                  ft.Text("Situation sous contrôle", size=11, color=MUT,
                                          text_align=ft.TextAlign.CENTER),
                              ], spacing=8, tight=True,
                               horizontal_alignment=ft.CrossAxisAlignment.CENTER))])
            elif tab == 1:  # Incidents
                incs = list_pending_incidents()
                items = ([
                    ft.Container(bgcolor=f"#10{DNG[1:]}", border_radius=14,
                        border=ft.Border.all(1,f"#30{DNG[1:]}"),
                        padding=P(14,12,14,12), ink=True,
                        on_click=lambda e: go_to("incident"),
                        content=ft.Row([
                            ft.Icon(ft.Icons.ADD_CIRCLE_ROUNDED, color=DNG, size=22),
                            ft.Text("Déclarer un nouvel incident", size=13,
                                    color=DNG, weight=ft.FontWeight.W_700),
                        ], spacing=10, tight=True)),
                ] + ([_inc_row(dict(r)) for r in incs] or [
                    ft.Container(bgcolor=f"#0A{MUT[1:]}", border_radius=14,
                        padding=P(20,16,20,16),
                        content=ft.Text("Aucun incident enregistré", size=13,
                                        color=MUT, text_align=ft.TextAlign.CENTER))]))
            elif tab == 2:  # EPI
                items = [
                    ft.Row([
                        _sec_action("Vérification", "Contrôle EPI terrain",
                            ft.Icons.SAFETY_CHECK_ROUNDED, WARN, "ppe_check"),
                        _sec_action("Dotation", "Distribuer les EPI",
                            ft.Icons.ASSIGNMENT_TURNED_IN_ROUNDED, OK, "ppe_assign"),
                    ], spacing=10),
                ]
                checks = list_pending_ppe_checks()
                if checks:
                    items += [ft.Text(f"{len(checks)} vérification(s) en attente de sync",
                                     size=11, color=WARN)]
                    items += [ft.Container(bgcolor=CARD, border_radius=12,
                        border=ft.Border.all(1,BRD), padding=P(12,10,12,10),
                        content=ft.Row([
                            ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED, color=MUT, size=16),
                            ft.Text(str(dict(c).get("employe_name") or "—"),
                                    size=12, color=TXT, expand=True),
                            ft.Text(str(dict(c).get("check_date",""))[:10],
                                    size=10, color=MUT),
                        ], spacing=8)) for c in checks[:5]]
            else:  # Formation / Toolbox
                items = [
                    _sec_action("Toolbox Talk","Causerie sécurité du jour",
                        ft.Icons.RECORD_VOICE_OVER_ROUNDED, PURP, "toolbox"),
                    _sec_action("Inspection","Check-list véhicule",
                        ft.Icons.FACT_CHECK_ROUNDED, INFO, "inspection"),
                ]
            body_col.controls = items + [ft.Container(height=80)]
            try: body_col.update()
            except Exception: pass

        _rebuild_tabs(); _rebuild_body()

        return ft.Container(bgcolor=BG, expand=True,
            content=ft.Column([
                # ── Header ──────────────────────────────────────────────────────
                ft.Container(
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1,-1), end=ft.Alignment(1,0.8),
                        colors=["#3B0A0A","#7F1D1D"]),
                    padding=P(16,18,16,14), shadow=SH(10,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(bgcolor="#18FFFFFF", border_radius=12,
                                padding=P(10,8,10,8),
                                content=ft.Icon(ft.Icons.HEALTH_AND_SAFETY_ROUNDED,
                                                color="#FFFFFF", size=22)),
                            ft.Column([
                                ft.Text("Sécurité HSE",size=18,
                                        weight=ft.FontWeight.BOLD,color="#FFFFFF"),
                                ft.Text(f"Site {cj('dashboard',{}).get('site') or 'SYAMA'}",
                                        size=11, color="#FCA5A5"),
                            ], spacing=2, expand=True),
                        ], spacing=12),
                        ft.Container(height=12),
                        ft.Container(bgcolor="#12FFFFFF", border_radius=12,
                            padding=P(0,8,0,8),
                            content=ft.Row([
                                _mstat(str(n_al), "Alertes", "#FCA5A5"),
                                ft.Container(width=1,height=28,bgcolor="#22FFFFFF"),
                                _mstat(str(n_inc), "Incidents", "#FCD34D"),
                                ft.Container(width=1,height=28,bgcolor="#22FFFFFF"),
                                _mstat(str(len(crits)), "Critiques", "#FCA5A5"),
                                ft.Container(width=1,height=28,bgcolor="#22FFFFFF"),
                                _mstat(str(n_ppe), "EPI vérif.", "#86EFAC"),
                            ], spacing=0, expand=True)),
                    ], spacing=0, tight=True)),
                # ── Tab bar ─────────────────────────────────────────────────────
                ft.Container(bgcolor=CARD, padding=P(10,8,10,8),
                    border=ft.Border.all(1,BRD), content=tab_bar),
                # ── Body ────────────────────────────────────────────────────────
                ft.Container(expand=True, padding=P(12,10,12,0),
                    content=body_col),
            ], spacing=0))

    # ─────────────────────────────────────────────────────────────────────────────
    def _s_personnel():
        n_att  = len(list_pending())
        today  = date.today().isoformat()

        tab_state = {"tab": 0}
        tab_bar   = ft.Row(spacing=4)
        body_col  = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        TABS = [
            ("Pointage",   ft.Icons.HOW_TO_REG_ROUNDED,  OK),
            ("Timesheets", ft.Icons.ARTICLE_ROUNDED,      BLUE),
            ("Toolbox",    ft.Icons.RECORD_VOICE_OVER_ROUNDED, PURP),
        ]

        def _att_row(r):
            r = dict(r) if not isinstance(r, dict) else r
            emp  = (str(r.get("employe_name","")) or
                    str(r.get("nom",""))+" "+str(r.get("prenom",""))).strip() or "—"
            stat = str(r.get("status","")).lower()
            dt   = str(r.get("date_presence") or r.get("created_at",""))[:10]
            sc   = {"present":OK,"absent":DNG,"retard":WARN}.get(stat,MUT)
            sl   = {"present":"Présent","absent":"Absent","retard":"Retard"}.get(stat,stat.title() or "—")
            return ft.Container(bgcolor=CARD, border_radius=12, shadow=SH(3,"06"),
                border=ft.Border.all(1, f"#20{sc[1:]}"), padding=P(12,10,12,10),
                content=ft.Row([
                    ft.Container(width=36, height=36, border_radius=18,
                        bgcolor=f"#18{sc[1:]}", alignment=AL(0,0),
                        content=ft.Icon(ft.Icons.PERSON_ROUNDED, color=sc, size=18)),
                    ft.Column([
                        ft.Text(emp, size=13, weight=ft.FontWeight.W_600, color=TXT,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(dt, size=10, color=MUT),
                    ], spacing=2, expand=True),
                    ft.Container(bgcolor=f"#18{sc[1:]}", border_radius=8, padding=P(8,3,8,3),
                        content=ft.Text(sl, size=10, color=sc, weight=ft.FontWeight.W_700)),
                ], spacing=10))

        def _rebuild_tabs():
            def _t(lbl, ico, c, idx):
                active = tab_state["tab"] == idx
                def click(e, i=idx):
                    tab_state["tab"] = i; _rebuild_tabs(); _rebuild_body()
                return ft.Container(expand=True, border_radius=10,
                    bgcolor=c if active else f"#12{c[1:]}",
                    padding=P(8,8,8,8), ink=True, on_click=click,
                    content=ft.Row([
                        ft.Icon(ico, color="#FFFFFF" if active else MUT, size=15),
                        ft.Text(lbl, size=12, color="#FFFFFF" if active else MUT,
                                weight=ft.FontWeight.W_700),
                    ], spacing=5, tight=True,
                     alignment=ft.MainAxisAlignment.CENTER))
            tab_bar.controls=[_t(l,i,c,idx) for idx,(l,i,c) in enumerate(TABS)]
            try: tab_bar.update()
            except Exception: pass

        def _rebuild_body():
            tab = tab_state["tab"]
            if tab == 0:  # Pointage
                atts = list_pending()
                items = [
                    ft.Container(bgcolor=f"#10{OK[1:]}", border_radius=14,
                        border=ft.Border.all(1, f"#30{OK[1:]}"),
                        padding=P(14,12,14,12), ink=True,
                        on_click=lambda e: go_to("attendance"),
                        content=ft.Row([
                            ft.Icon(ft.Icons.ADD_CIRCLE_ROUNDED, color=OK, size=22),
                            ft.Text("Enregistrer un pointage", size=13,
                                    color=OK, weight=ft.FontWeight.W_700),
                        ], spacing=10, tight=True)),
                ] + ([_att_row(r) for r in atts[:10]] or [
                    ft.Container(bgcolor=f"#0A{MUT[1:]}", border_radius=14,
                        padding=P(20,16,20,16),
                        content=ft.Text("Aucun pointage enregistré aujourd'hui",
                                        size=13, color=MUT,
                                        text_align=ft.TextAlign.CENTER))])
            elif tab == 1:  # Timesheets
                items = [
                    ft.Container(bgcolor=CARD, border_radius=16,
                        border=ft.Border.all(1, f"#22{BLUE[1:]}"),
                        shadow=SH(5,"0A"), ink=True,
                        on_click=lambda e: go_to("timesheet"),
                        padding=P(18,16,18,16),
                        content=ft.Row([
                            ft.Container(bgcolor=BLUE, border_radius=14,
                                width=50, height=50, alignment=AL(0,0),
                                content=ft.Icon(ft.Icons.ARTICLE_ROUNDED,
                                                color="#FFFFFF", size=26)),
                            ft.Column([
                                ft.Text("Timesheets & Exports", size=14,
                                        weight=ft.FontWeight.BOLD, color=TXT),
                                ft.Text("Télécharger · Exporter · Partager",
                                        size=11, color=MUT),
                            ], spacing=4, expand=True),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                    color=MUT, size=20),
                        ], spacing=14)),
                ]
            else:  # Toolbox
                tb = get_toolbox_cache(today) or {}
                theme = str(tb.get("theme") or "Aucune causerie programmée aujourd'hui")
                items = [
                    ft.Container(bgcolor=CARD, border_radius=16,
                        border=ft.Border.all(1, f"#22{PURP[1:]}"),
                        shadow=SH(5,"0A"), ink=True,
                        on_click=lambda e: go_to("toolbox"),
                        padding=P(18,16,18,16),
                        content=ft.Column([
                            ft.Row([
                                ft.Container(bgcolor=PURP, border_radius=14,
                                    width=50, height=50, alignment=AL(0,0),
                                    content=ft.Icon(ft.Icons.RECORD_VOICE_OVER_ROUNDED,
                                                    color="#FFFFFF", size=26)),
                                ft.Column([
                                    ft.Text("Toolbox Talk du jour", size=14,
                                            weight=ft.FontWeight.BOLD, color=TXT),
                                    ft.Text("Causerie sécurité",size=11,color=MUT),
                                ], spacing=4, expand=True),
                            ], spacing=14),
                            ft.Container(height=10),
                            ft.Container(bgcolor=f"#10{PURP[1:]}", border_radius=10,
                                padding=P(12,10,12,10),
                                border=ft.Border.all(1, f"#30{PURP[1:]}"),
                                content=ft.Text(theme, size=12, color=TXT,
                                                max_lines=3,
                                                overflow=ft.TextOverflow.ELLIPSIS)),
                        ], spacing=0, tight=True)),
                ]
            body_col.controls = items + [ft.Container(height=80)]
            try: body_col.update()
            except Exception: pass

        _rebuild_tabs(); _rebuild_body()

        return ft.Container(bgcolor=BG, expand=True,
            content=ft.Column([
                # ── Header ──────────────────────────────────────────────────────
                ft.Container(
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1,-1), end=ft.Alignment(1,0.8),
                        colors=["#052E16","#14532D"]),
                    padding=P(16,18,16,14), shadow=SH(10,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(bgcolor="#18FFFFFF", border_radius=12,
                                padding=P(10,8,10,8),
                                content=ft.Icon(ft.Icons.GROUPS_ROUNDED,
                                                color="#FFFFFF", size=22)),
                            ft.Column([
                                ft.Text("Personnel & RH", size=18,
                                        weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                ft.Text(f"Site {cj('dashboard',{}).get('site') or 'SYAMA'}",
                                        size=11, color="#86EFAC"),
                            ], spacing=2, expand=True),
                        ], spacing=12),
                        ft.Container(height=12),
                        ft.Container(bgcolor="#12FFFFFF", border_radius=12,
                            padding=P(0,8,0,8),
                            content=ft.Row([
                                _mstat(str(n_att), "En attente sync", "#86EFAC"),
                                ft.Container(width=1, height=28, bgcolor="#22FFFFFF"),
                                _mstat(date.today().strftime("%d/%m"), "Aujourd'hui", "#86EFAC"),
                                ft.Container(width=1, height=28, bgcolor="#22FFFFFF"),
                                _mstat(str(len(list_pending_toolbox())), "Toolbox", "#C4B5FD"),
                            ], spacing=0, expand=True)),
                    ], spacing=0, tight=True)),
                # ── Tab bar ─────────────────────────────────────────────────────
                ft.Container(bgcolor=CARD, padding=P(10,8,10,8),
                    border=ft.Border.all(1,BRD), content=tab_bar),
                # ── Body ────────────────────────────────────────────────────────
                ft.Container(expand=True, padding=P(12,10,12,0),
                    content=body_col),
            ], spacing=0))

    def _s_maint():
        # ── Local state ──────────────────────────────────────────────────────────
        ST2={"tab":0,"q":"","filtre":"all"}  # tab: 0=Équipements, 1=OT, 2=Pannes

        # ── Shared display columns ────────────────────────────────────────────────
        kpi_row   = ft.Row(spacing=0,expand=True)
        tab_bar   = ft.Row(spacing=4)
        body_col  = ft.Column(spacing=8,scroll=ft.ScrollMode.AUTO,expand=True)
        chip_row  = ft.Row(spacing=6,wrap=True)
        srch      = ft.TextField(
            hint_text="Rechercher...",prefix_icon=ft.Icons.SEARCH_OUTLINED,
            border_radius=12,border_color=BRD,focused_border_color=BLUE,height=46,
            bgcolor=CARD,color=TXT,hint_style=ft.TextStyle(color=MUT),dense=True,
            on_change=lambda e:[ST2.__setitem__("q",e.control.value or ""),_rebuild_body()])

        # ── Helpers ───────────────────────────────────────────────────────────────
        def _is_retard(i): return str(i["status"]or"").lower() in ("en_retard","overdue","retard")
        def _is_surv(i):   return str(i["status"]or"").lower() in ("a_surveiller","warning","bientot")

        def _kpi(val,lbl,c):
            return ft.Container(expand=True,
                content=ft.Column([
                    ft.Text(str(val),size=22,weight=ft.FontWeight.BOLD,
                            color=c,text_align=ft.TextAlign.CENTER),
                    ft.Text(lbl,size=9,color="#99FFFFFF",
                            text_align=ft.TextAlign.CENTER),
                ],spacing=1,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))

        def _sep(): return ft.Container(width=1,height=36,bgcolor="#22FFFFFF")

        def _elapsed_str(created_at_str):
            """Returns human-readable elapsed time and color based on urgency."""
            try:
                from datetime import datetime as _dt2
                created = _dt2.strptime(str(created_at_str)[:19], "%Y-%m-%d %H:%M:%S")
                delta   = _dt2.now() - created
                h = int(delta.total_seconds() // 3600)
                m = int((delta.total_seconds() % 3600) // 60)
                if h >= 72:  return f"{h//24}j {h%24}h", DNG,  True
                if h >= 24:  return f"{h//24}j {h%24}h", WARN, h >= 48
                if h >= 1:   return f"{h}h {m:02d}m",    WARN if h>=4 else OK, False
                return f"{m}m", OK, False
            except Exception: return "—", MUT, False

        def _ot_card(r, on_click_fn=None):
            obs   = str(r.get("observation") or "")
            tp    = str(r.get("type_intervention") or "corrective")
            prio  = str(r.get("priority") or r.get("priorite") or "moyenne")
            equip = str(r.get("equipment_label") or "—")
            dt    = str(r.get("observation_date") or "")
            stat  = str(r.get("statut_ot") or "ouvert")
            ot_id = r.get("id_pending", 0)
            created= str(r.get("created_at") or dt+" 00:00:00")
            delai_h= OT_DELAI_H.get(prio, 72)

            wf_lbl, wf_color, _ = OT_WF_DICT.get(stat, (STATUT_OT_LABELS.get(stat,"?"), INFO, None))
            sc   = wf_color
            pc   = PRIO_COLORS.get(prio, MUT)
            tl   = {"preventive":"Préventive","corrective":"Corrective","inspection":"Inspection",
                    "vidange":"Vidange","ameliorative":"Améliorative"}.get(tp, tp.title())
            tc   = {"preventive":BLUE,"corrective":DNG,"inspection":INFO,
                    "vidange":WARN,"ameliorative":PURP}.get(tp, MUT)
            elapsed, e_color, is_retard = _elapsed_str(created)

            def _mini_step(k):
                idx_k   = next((i for i,(kk,*_) in enumerate(OT_WORKFLOW) if kk==k),0)
                idx_cur = next((i for i,(kk,*_) in enumerate(OT_WORKFLOW) if kk==stat),0)
                done    = idx_k <= idx_cur
                c2      = OT_WF_DICT.get(k,(None,"#555555",None))[1]
                return ft.Container(
                    width=22, height=22, border_radius=11,
                    bgcolor=c2 if done else f"#22{c2[1:]}",
                    border=ft.Border.all(1.5, c2 if done else f"#44{c2[1:]}"),
                    alignment=ft.Alignment(0,0),
                    content=ft.Icon(
                        OT_WF_DICT.get(k,(None,None,ft.Icons.CIRCLE_OUTLINED))[2],
                        color="#FFFFFF" if done else f"#88{c2[1:]}",
                        size=12))

            progress_steps = ft.Row(
                [_mini_step(k) for k,*_ in OT_WORKFLOW],
                spacing=4, tight=True)

            def _open(e):
                if on_click_fn: on_click_fn(ot_id)
                else: go_to_ot(ot_id)

            return ft.Container(
                bgcolor=CARD, border_radius=14, shadow=SH(6,"0A"),
                border=ft.Border.all(1.5 if is_retard else 1,
                                     DNG if is_retard else f"#30{pc[1:]}"),
                ink=True, on_click=_open, padding=P(0,0,0,0),
                content=ft.Row([
                    ft.Container(width=5, bgcolor=pc, border_radius=14),
                    ft.Container(expand=True, padding=P(12,12,12,12),
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    bgcolor=f"#18{tc[1:]}",border_radius=8,padding=P(6,2,6,2),
                                    content=ft.Text(tl,size=10,color=tc,weight=ft.FontWeight.W_700)),
                                ft.Container(expand=True),
                                *([ ft.Container(
                                    bgcolor=f"#18{DNG[1:]}",border_radius=8,padding=P(6,2,6,2),
                                    content=ft.Row([
                                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                                                color=DNG,size=10),
                                        ft.Text("EN RETARD",size=9,color=DNG,
                                                weight=ft.FontWeight.W_800),
                                    ],spacing=3,tight=True)) ] if is_retard else []),
                                ft.Container(
                                    bgcolor=f"#18{sc[1:]}",border_radius=8,padding=P(6,2,6,2),
                                    content=ft.Text(wf_lbl,size=10,color=sc,
                                                    weight=ft.FontWeight.W_700)),
                            ],spacing=5),
                            ft.Text(equip,size=13,weight=ft.FontWeight.BOLD,color=TXT,
                                    max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(obs[:72]+("…" if len(obs)>72 else ""),
                                    size=11,color=MUT,max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row([
                                progress_steps,
                                ft.Container(expand=True),
                                ft.Icon(ft.Icons.TIMER_OUTLINED,color=e_color,size=12),
                                ft.Text(elapsed,size=10,color=e_color,
                                        weight=ft.FontWeight.W_600),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,color=MUT,size=14),
                            ],spacing=4),
                        ],spacing=6,tight=True)),
                ],spacing=0,tight=True))

        def _panne_card(r):
            tp=r.get("type_panne","autre"); imp=r.get("impact_production","aucun")
            equip=str(r.get("equipment_label") or "—")
            symp=str(r.get("symptomes") or "—")
            dt=str(r.get("panne_date") or ""); hr=str(r.get("panne_heure") or "")
            stat=str(r.get("statut") or "signale")
            prio=str(r.get("priorite") or "haute")
            tc=TYPE_PANNE_COLORS.get(tp,"#888888")
            tl=TYPE_PANNE_LABELS.get(tp,"Autre")
            ico=TYPE_PANNE_ICONS.get(tp,ft.Icons.HELP_OUTLINE_ROUNDED)
            imp_c={"arret_total":DNG,"partiel":WARN,"degrade":INFO,"aucun":OK}.get(imp,MUT)
            imp_l={"arret_total":"Arrêt total","partiel":"Arrêt partiel",
                   "degrade":"Dégradé","aucun":"Sans impact"}.get(imp,"—")
            pc=PRIO_COLORS.get(prio,MUT)
            stat_lbl={"signale":"Signalé","en_cours":"En cours","termine":"Résolu"}.get(stat,stat)
            stat_c={"signale":WARN,"en_cours":INFO,"termine":OK}.get(stat,MUT)
            return ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                border=ft.Border.all(1,f"{tc}30"),padding=P(0,0,0,0),
                content=ft.Row([
                    ft.Container(width=5,bgcolor=pc,border_radius=14),
                    ft.Container(expand=True,padding=P(12,12,12,12),
                        content=ft.Column([
                            ft.Row([
                                _box(ico,tc,28,14),
                                ft.Text(tl,size=12,weight=ft.FontWeight.BOLD,color=tc,expand=True),
                                ft.Container(bgcolor=f"{stat_c}18",border_radius=8,padding=P(6,2,6,2),
                                    content=ft.Text(stat_lbl,size=10,color=stat_c,
                                                    weight=ft.FontWeight.W_700)),
                            ],spacing=6),
                            ft.Text(equip,size=13,weight=ft.FontWeight.BOLD,color=TXT,
                                    max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(symp,size=11,color=MUT,max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row([
                                ft.Container(bgcolor=f"{imp_c}18",border_radius=6,
                                    padding=P(6,2,6,2),
                                    content=ft.Text(imp_l,size=10,color=imp_c,
                                                    weight=ft.FontWeight.W_600)),
                                ft.Container(expand=True),
                                ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED,color=MUT,size=11),
                                ft.Text(f"{dt} {hr}".strip(),size=10,color=MUT),
                            ],spacing=4),
                        ],spacing=4,tight=True)),
                ],spacing=0,tight=True))

        def _empty(msg,sub=""):
            return ft.Container(bgcolor=f"#08{MUT[1:]}",border_radius=14,
                border=ft.Border.all(1,BRD),padding=P(24,24,24,24),
                content=ft.Column([
                    ft.Icon(ft.Icons.INBOX_ROUNDED,color=MUT,size=44),
                    ft.Text(msg,size=14,color=MUT,text_align=ft.TextAlign.CENTER),
                    *([] if not sub else [ft.Text(sub,size=11,color=MUT,
                                                  text_align=ft.TextAlign.CENTER)]),
                ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=6,tight=True))

        # ── KPI refresh ───────────────────────────────────────────────────────────
        def _rebuild_kpi():
            eqs=list_maintenance_cache()
            ots=list_pending_maintenance()
            pns=list_pending_panne()
            nr=sum(1 for i in eqs if _is_retard(i))
            ns=sum(1 for i in eqs if _is_surv(i))
            kpi_row.controls=[
                _kpi(len(ots),"OT ouverts",WARN if ots else OK),
                _sep(),
                _kpi(len(pns),"Pannes",DNG if pns else OK),
                _sep(),
                _kpi(nr,"En retard",DNG if nr else OK),
                _sep(),
                _kpi(ns,"À surveiller",WARN if ns else OK),
            ]
            try: kpi_row.update()
            except Exception: pass

        # ── Tab bar ───────────────────────────────────────────────────────────────
        def _rebuild_tabs():
            TABS=[("Équipements",ft.Icons.HANDYMAN_OUTLINED),
                  ("OT",ft.Icons.ASSIGNMENT_ROUNDED),
                  ("Pannes",ft.Icons.REPORT_PROBLEM_ROUNDED)]
            def _t(lbl,ico,idx):
                active=ST2["tab"]==idx
                def click(e,i=idx): ST2["tab"]=i; _rebuild_tabs(); _rebuild_chips(); _rebuild_body()
                return ft.Container(expand=True,border_radius=10,
                    bgcolor=BLUE if active else f"#12{BLUE[1:]}",
                    padding=P(8,8,8,8),ink=True,on_click=click,
                    content=ft.Row([ft.Icon(ico,color="#FFFFFF" if active else MUT,size=14),
                        ft.Text(lbl,size=12,color="#FFFFFF" if active else MUT,
                                weight=ft.FontWeight.W_700)],
                        spacing=5,tight=True,alignment=ft.MainAxisAlignment.CENTER))
            tab_bar.controls=[_t(l,i,idx) for idx,(l,i) in enumerate(TABS)]
            try: tab_bar.update()
            except Exception: pass

        # ── Chips per tab ─────────────────────────────────────────────────────────
        def _rebuild_chips():
            tab=ST2["tab"]
            if tab==0:
                eqs=list_maintenance_cache()
                nr=sum(1 for i in eqs if _is_retard(i))
                ns=sum(1 for i in eqs if _is_surv(i))
                chips=[("all","Tous",MUT),("retard",f"En retard ({nr})",DNG),
                       ("surv",f"À surveiller ({ns})",WARN)]
            elif tab==1:
                ots=[dict(r) for r in list_pending_maintenance()]
                tp_counts={}
                for r in ots: tp_counts[r.get("type_intervention","corrective")]=tp_counts.get(r.get("type_intervention","corrective"),0)+1
                chips=[("all","Tous",MUT),("preventive",f"Préventif ({tp_counts.get('preventive',0)})",BLUE),
                       ("corrective",f"Correctif ({tp_counts.get('corrective',0)})",DNG),
                       ("inspection",f"Inspection ({tp_counts.get('inspection',0)})",INFO)]
            else:
                pns=list_pending_panne()
                ni=sum(1 for p in pns if p.get("impact_production")=="arret_total")
                np_=sum(1 for p in pns if p.get("statut")=="signale")
                chips=[("all","Tous",MUT),("arret_total",f"Arrêt total ({ni})",DNG),
                       ("signale",f"Non traités ({np_})",WARN)]
            def _chip(k,lbl,c):
                active=ST2["filtre"]==k
                def click(e,kk=k): ST2["filtre"]=kk; _rebuild_chips(); _rebuild_body()
                return ft.Container(border_radius=20,
                    bgcolor=f"{c}22" if active else f"{c}10",
                    border=ft.Border.all(1,c if active else f"{c}30"),
                    padding=P(12,5,12,5),ink=True,on_click=click,
                    content=ft.Text(lbl,size=11,
                        color=c if active else MUT,
                        weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400))
            chip_row.controls=[_chip(k,l,c) for k,l,c in chips]
            try: chip_row.update()
            except Exception: pass

        # ── Body per tab ─────────────────────────────────────────────────────────
        def _rebuild_body():
            q=ST2["q"].strip().lower(); f=ST2["filtre"]; tab=ST2["tab"]
            if tab==0:
                src=list_maintenance_cache()
                if f=="retard": src=[i for i in src if _is_retard(i)]
                elif f=="surv": src=[i for i in src if _is_surv(i)]
                if q: src=[i for i in src if q in (i["equipment_label"]or"").lower()
                            or q in (i["site"]or"").lower()]
                items=[_eq_card(i) for i in src] or [_empty("Aucun équipement",
                    "Synchronisez depuis Profil")]
            elif tab==1:
                ots=[dict(r) for r in list_pending_maintenance()]
                if f!="all": ots=[r for r in ots if r.get("type_intervention","corrective")==f]
                if q: ots=[r for r in ots if q in (r.get("equipment_label","")).lower()
                            or q in (r.get("observation","")).lower()]
                items=[_ot_card(r) for r in ots] or [_empty("Aucun ordre de travail",
                    "Créez un OT via + Intervention")]
            else:
                pns=list_pending_panne()
                if f=="arret_total": pns=[p for p in pns if p.get("impact_production")=="arret_total"]
                elif f=="signale":   pns=[p for p in pns if p.get("statut")=="signale"]
                if q: pns=[p for p in pns if q in (p.get("equipment_label","")).lower()
                            or q in (p.get("symptomes","")).lower()]
                items=[_panne_card(p) for p in pns] or [_empty("Aucune panne déclarée",
                    "Déclarez une panne via + Panne")]
            body_col.controls=items+[ft.Container(height=100)]
            try: body_col.update()
            except Exception: pass

        _rebuild_kpi(); _rebuild_tabs(); _rebuild_chips(); _rebuild_body()

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Stack([
                ft.Column([
                    # ── Header + KPIs ───────────────────────────────────────────
                    ft.Container(gradient=GRAD,padding=P(16,18,16,16),shadow=SH(10,"20"),
                        content=ft.Column([
                            ft.Row([
                                _box(ft.Icons.HANDYMAN_ROUNDED,"#FFFFFF",28,16),
                                ft.Text("Maintenance GMAO",size=17,
                                        weight=ft.FontWeight.BOLD,color="#FFFFFF",expand=True),
                                ft.Container(width=34,height=34,border_radius=17,
                                    bgcolor="#18FFFFFF",alignment=AL(0,0),ink=True,
                                    on_click=lambda e:[_rebuild_kpi(),_rebuild_body()],
                                    content=ft.Icon(ft.Icons.REFRESH_ROUNDED,
                                                    color="#FFFFFF",size=17)),
                            ],spacing=8),
                            ft.Container(height=10),
                            ft.Container(bgcolor="#12FFFFFF",border_radius=12,
                                padding=P(0,10,0,10),content=kpi_row),
                        ],spacing=0,tight=True)),
                    # ── Tabs ────────────────────────────────────────────────────
                    ft.Container(bgcolor=CARD,padding=P(10,8,10,8),
                        border=ft.Border.all(1,BRD),
                        content=tab_bar),
                    # ── Body ────────────────────────────────────────────────────
                    ft.Container(expand=True,padding=P(12,10,12,0),
                        content=ft.Column([
                            srch,
                            chip_row,
                            body_col,
                        ],spacing=8,expand=True)),
                ],spacing=0,expand=True),
                # ── FABs ────────────────────────────────────────────────────────
                ft.Column([
                    ft.Container(bgcolor=DNG,border_radius=14,shadow=SH(10,"28"),
                        padding=P(14,12,14,12),ink=True,
                        on_click=lambda e:go_to("panne"),
                        content=ft.Row([ft.Icon(ft.Icons.REPORT_PROBLEM_ROUNDED,
                                                color="#FFFFFF",size=18),
                            ft.Text("Panne",color="#FFFFFF",size=12,
                                    weight=ft.FontWeight.W_700)],spacing=6,tight=True)),
                    ft.Container(height=8),
                    ft.Container(bgcolor=BLUE,border_radius=14,shadow=SH(10,"28"),
                        padding=P(14,12,14,12),ink=True,
                        on_click=lambda e:go_to("intervention"),
                        content=ft.Row([ft.Icon(ft.Icons.ADD_ROUNDED,
                                                color="#FFFFFF",size=18),
                            ft.Text("OT",color="#FFFFFF",size=12,
                                    weight=ft.FontWeight.W_700)],spacing=6,tight=True)),
                ],right=16,bottom=28,spacing=0,tight=True),
            ]))

    def _s_interv():
        TYPES=[
            ("preventive","Préventive", ft.Icons.SETTINGS_SUGGEST_OUTLINED, BLUE),
            ("corrective","Corrective", ft.Icons.BUILD_ROUNDED,             DNG),
            ("inspection","Inspection", ft.Icons.FACT_CHECK_ROUNDED,        INFO),
            ("vidange",   "Vidange",    ft.Icons.OIL_BARREL_OUTLINED,       WARN),
        ]
        PRIOS=[
            ("basse",    "Basse",    OK),
            ("moyenne",  "Moyenne",  INFO),
            ("haute",    "Haute",    WARN),
            ("critique", "Critique", DNG),
        ]
        type_row  = ft.Row(spacing=8)
        prio_row  = ft.Row(spacing=6)

        def _rebuild_type():
            def _tc(k,lbl,ico,c):
                active=mi_type.value==k
                def click(e,kk=k): mi_type.value=kk; _rebuild_type()
                return ft.Container(expand=True,border_radius=14,
                    bgcolor=c if active else CARD,
                    border=ft.Border.all(1.5 if active else 1,c if active else BRD),
                    ink=True,on_click=click,padding=P(8,10,8,10),
                    content=ft.Column([
                        ft.Container(bgcolor="#25FFFFFF" if active else f"{c}18",
                            border_radius=10,width=34,height=34,alignment=AL(0,0),
                            content=ft.Icon(ico,color="#FFFFFF" if active else c,size=17)),
                        ft.Text(lbl,size=11,weight=ft.FontWeight.W_700,
                                color="#FFFFFF" if active else MUT,
                                text_align=ft.TextAlign.CENTER),
                    ],spacing=6,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))
            type_row.controls=[_tc(k,l,i,c) for k,l,i,c in TYPES]
            try: type_row.update()
            except Exception: pass

        def _rebuild_prio():
            def _pc(k,lbl,c):
                active=mi_prio.value==k
                def click(e,kk=k): mi_prio.value=kk; _rebuild_prio()
                return ft.Container(expand=True,border_radius=12,height=46,
                    bgcolor=c if active else CARD,
                    border=ft.Border.all(1.5 if active else 1,c if active else BRD),
                    alignment=AL(0,0),ink=True,on_click=click,
                    content=ft.Column([
                        ft.Container(width=8,height=8,border_radius=4,
                            bgcolor="#FFFFFF" if active else c),
                        ft.Text(lbl,size=11,weight=ft.FontWeight.W_700,
                                color="#FFFFFF" if active else c,
                                text_align=ft.TextAlign.CENTER),
                    ],spacing=4,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))
            prio_row.controls=[_pc(k,l,c) for k,l,c in PRIOS]
            try: prio_row.update()
            except Exception: pass

        _rebuild_type(); _rebuild_prio()

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                # ── Header ────────────────────────────────────────────────────
                ft.Container(gradient=GRAD,padding=P(16,16,16,18),shadow=SH(12,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#18FFFFFF",
                                alignment=AL(0,0),ink=True,on_click=lambda e:go_to("maintenance"),
                                content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,
                                                color="#FFFFFF",size=17)),
                            ft.Text("Nouvelle intervention",size=17,weight=ft.FontWeight.BOLD,
                                    color="#FFFFFF",expand=True,text_align=ft.TextAlign.CENTER),
                            ft.Container(width=36,height=36),
                        ],spacing=8),
                        ft.Container(height=8),
                        ft.Row([
                            ft.Icon(ft.Icons.BUILD_CIRCLE_OUTLINED,color="#93C5FD",size=13),
                            ft.Text(f"Maintenance terrain · {cj('dashboard',{}).get('site') or 'SYAMA'}",
                                    size=11,color="#93C5FD"),
                        ],spacing=6),
                    ],spacing=0,tight=True)),
                # ── Scrollable body ────────────────────────────────────────────
                ft.Container(expand=True,padding=P(12,14,12,0),
                    content=ft.Column([
                        # ── Équipement ─────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{BLUE[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.HANDYMAN_OUTLINED,color=BLUE,size=17)),
                                    ft.Text("Équipement",size=14,weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                mi_eq,
                                *([] if mi_eq.options else [
                                    ft.Row([
                                        ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED,color=WARN,size=14),
                                        ft.Text("Aucun équipement disponible — synchronisez depuis Profil",
                                                size=11,color=WARN),
                                    ],spacing=6)
                                ]),
                            ],spacing=10)),
                        # ── Type d'intervention ────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{PURP[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.CATEGORY_OUTLINED,color=PURP,size=17)),
                                    ft.Text("Type d'intervention",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                type_row,
                            ],spacing=12)),
                        # ── Priorité ───────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{WARN[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.FLAG_ROUNDED,color=WARN,size=17)),
                                    ft.Text("Niveau de priorité",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT,expand=True),
                                ],spacing=10),
                                prio_row,
                                ft.Row([mi_date,mi_km],spacing=8),
                            ],spacing=12)),
                        # ── Description ────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{INFO[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED,color=INFO,size=17)),
                                    ft.Text("Description & Observations",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                mi_obs,
                            ],spacing=12)),
                        # ── Cycle de vie OT ────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{INFO[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.ASSIGNMENT_TURNED_IN_ROUNDED,
                                                        color=INFO,size=17)),
                                    ft.Text("Cycle de vie OT",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                ft.Row([mi_statut_ot,mi_duree],spacing=8,expand=True),
                                mi_tech,
                            ],spacing=10)),
                        # ── Cause racine (corrective uniquement) ────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,f"#44{DNG[1:]}"),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{DNG[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.MANAGE_SEARCH_ROUNDED,
                                                        color=DNG,size=17)),
                                    ft.Text("Analyse cause racine",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                    ft.Container(bgcolor=f"#18{DNG[1:]}",border_radius=6,
                                        padding=P(6,2,6,2),
                                        content=ft.Text("Corrective",size=9,color=DNG,
                                                        weight=ft.FontWeight.W_700)),
                                ],spacing=8),
                                mi_cause,
                            ],spacing=10)),
                        # ── Photo / Signature ──────────────────────────────────
                        ft.Row([
                            ft.Container(bgcolor=f"#10{INFO[1:]}",border_radius=14,
                                border=ft.Border.all(1,f"#44{INFO[1:]}"),expand=True,height=48,
                                ink=True,alignment=AL(0,0),
                                on_click=lambda e:notify("Photo — disponible prochainement.",INFO),
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED,color=INFO,size=18),
                                    ft.Text("Photo",color=INFO,size=12,weight=ft.FontWeight.W_700),
                                ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                            ft.Container(bgcolor=f"#10{PURP[1:]}",border_radius=14,
                                border=ft.Border.all(1,f"#44{PURP[1:]}"),expand=True,height=48,
                                ink=True,alignment=AL(0,0),
                                on_click=lambda e:notify("Signature — disponible prochainement.",PURP),
                                content=ft.Row([
                                    ft.Icon(ft.Icons.DRAW_OUTLINED,color=PURP,size=18),
                                    ft.Text("Signature",color=PURP,size=12,weight=ft.FontWeight.W_700),
                                ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                        ],spacing=10),
                        # ── Submit ─────────────────────────────────────────────
                        ft.Container(bgcolor=BLUE,border_radius=16,height=52,
                            ink=True,alignment=AL(0,0),shadow=SH(8,"22"),
                            on_click=save_mi,
                            content=ft.Row([
                                ft.Icon(ft.Icons.SAVE_ROUNDED,color="#FFFFFF",size=20),
                                ft.Text("Enregistrer l'OT",color="#FFFFFF",
                                        size=14,weight=ft.FontWeight.W_700),
                            ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                        ft.Container(height=80),
                    ],spacing=10,scroll=ft.ScrollMode.AUTO,expand=True)),
            ],spacing=0))

    # ─────────────────────────────────────────────────────────────────────────────
    def _s_ot_detail(ot_id: int):
        from datetime import datetime as _dt3

        ot = get_ot(ot_id) or {}
        equip   = str(ot.get("equipment_label") or "—")
        tp      = str(ot.get("type_intervention") or "corrective")
        prio    = str(ot.get("priority") or ot.get("priorite") or "moyenne")
        obs     = str(ot.get("observation") or "—")
        created = str(ot.get("created_at") or "")
        stat    = str(ot.get("statut_ot") or "ouvert")
        tech    = str(ot.get("technicien") or "Non assigné")
        cause   = str(ot.get("cause_racine") or "")
        duree_r = float(ot.get("duree_heures") or 0)
        duree_e = float(ot.get("duree_estimee") or 0)
        date_d  = str(ot.get("date_debut") or "")
        date_f  = str(ot.get("date_fin") or "")

        tl  = {"preventive":"Préventive","corrective":"Corrective","inspection":"Inspection",
               "vidange":"Vidange","ameliorative":"Améliorative"}.get(tp, tp.title())
        tc  = {"preventive":BLUE,"corrective":DNG,"inspection":INFO,
               "vidange":WARN,"ameliorative":PURP}.get(tp, MUT)
        pc  = PRIO_COLORS.get(prio, MUT)
        wf_lbl, wf_color, _ = OT_WF_DICT.get(stat, ("?", MUT, None))

        # ── Timer ──────────────────────────────────────────────────────────────────
        try:
            cr = _dt3.strptime(created[:19], "%Y-%m-%d %H:%M:%S")
            delta = _dt3.now() - cr
            h_tot = int(delta.total_seconds() // 3600)
            m_tot = int((delta.total_seconds() % 3600) // 60)
            elapsed_str = (f"{h_tot//24}j {h_tot%24}h" if h_tot>=24
                           else f"{h_tot}h {m_tot:02d}m" if h_tot>=1 else f"{m_tot}m")
            delai_h = OT_DELAI_H.get(prio, 72)
            retard  = h_tot > delai_h and stat not in ("termine","verifie")
            timer_c = DNG if retard else (WARN if h_tot > delai_h*0.7 else OK)
        except Exception:
            elapsed_str = "—"; retard = False; timer_c = MUT; delai_h = 72

        # ── Live timeline ──────────────────────────────────────────────────────────
        history   = list_ot_history(ot_id)
        hist_col  = ft.Column(spacing=0)
        note_tf   = ft.TextField(
            label="Note (optionnelle)", border_radius=10,
            border_color=BRD, focused_border_color=BLUE,
            bgcolor=CARD, color=TXT, label_style=ft.TextStyle(color=MUT),
            multiline=True, min_lines=2, max_lines=4)
        status_area = ft.Column(spacing=8)

        def _fmt_dt(s):
            try:
                d = _dt3.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S")
                return d.strftime("%d/%m %H:%M")
            except Exception: return str(s)[:16]

        def _build_history():
            if not history:
                hist_col.controls = [ft.Container(
                    bgcolor=f"#0A{MUT[1:]}",border_radius=10,padding=P(14,10,14,10),
                    content=ft.Text("Aucune entrée d'historique",size=12,color=MUT,
                                    text_align=ft.TextAlign.CENTER))]
                return

            items = []
            for i, h in enumerate(history):
                hstat = str(h.get("statut",""))
                htime = _fmt_dt(h.get("changed_at",""))
                hnote = str(h.get("note") or "")
                htech = str(h.get("technicien") or "")
                _, hc, hi = OT_WF_DICT.get(hstat, ("?", MUT, ft.Icons.CIRCLE_OUTLINED))
                is_last = i == len(history)-1

                items.append(ft.Row([
                    ft.Column([
                        ft.Container(width=32,height=32,border_radius=16,
                            bgcolor=hc if is_last else f"#22{hc[1:]}",
                            border=ft.Border.all(2,hc),alignment=ft.Alignment(0,0),
                            content=ft.Icon(hi,color="#FFFFFF" if is_last else hc,size=16)),
                        *([] if i==len(history)-1 else [
                            ft.Container(width=2,height=36,bgcolor=f"#22{hc[1:]}",
                                         margin=ft.Margin(left=15,top=0,right=0,bottom=0))]),
                    ],spacing=0,tight=True,
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(expand=True,
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    bgcolor=hc if is_last else f"#18{hc[1:]}",
                                    border_radius=8,padding=P(6,2,6,2),
                                    content=ft.Text(
                                        OT_WF_DICT.get(hstat,("?",None,None))[0],
                                        size=11,color="#FFFFFF" if is_last else hc,
                                        weight=ft.FontWeight.W_700)),
                                ft.Container(expand=True),
                                ft.Text(htime,size=10,color=MUT),
                            ],spacing=6),
                            *([] if not hnote else [
                                ft.Text(hnote,size=11,color=MUT,max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS)]),
                            *([] if not htech else [
                                ft.Row([ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED,
                                               color=MUT,size=12),
                                        ft.Text(htech,size=10,color=MUT)],spacing=4)]),
                        ],spacing=3,tight=True)),
                ],spacing=12,vertical_alignment=ft.CrossAxisAlignment.START))
            hist_col.controls = items
            try: hist_col.update()
            except Exception: pass

        def _build_actions():
            transitions = OT_TRANSITIONS.get(stat, [])
            if not transitions:
                status_area.controls = [
                    ft.Container(bgcolor=f"#18{OK[1:]}",border_radius=12,padding=P(14,12,14,12),
                        border=ft.Border.all(1,f"#44{OK[1:]}"),
                        content=ft.Row([
                            ft.Icon(ft.Icons.VERIFIED_ROUNDED,color=OK,size=20),
                            ft.Text("OT clôturé — aucune action disponible",
                                    color=OK,size=13,weight=ft.FontWeight.W_600),
                        ],spacing=10,tight=True))]
                return

            btn_row = ft.Row(spacing=8, wrap=True)
            for next_stat in transitions:
                _, nc, ni = OT_WF_DICT.get(next_stat, ("?", MUT, ft.Icons.CIRCLE))
                lbl       = OT_WF_DICT.get(next_stat, ("?",None,None))[0]
                def _do_change(e, ns=next_stat, nc2=nc):
                    note_val = str(note_tf.value or "").strip()
                    tech_val = str(ot.get("technicien") or "")
                    wf_lbl2  = OT_WF_DICT.get(ns, ("?",None,None))[0]
                    def do(_=None):
                        update_ot_statut(ot_id, ns, note_val, tech_val)
                        go_to_ot(ot_id)
                    confirm(f"Changer le statut vers « {wf_lbl2} »",
                            f"OT #{ot_id} — {equip}\n{note_val or 'Aucune note'}",
                            do, yes_lbl="Confirmer", danger=ns in ("termine","verifie"))
                btn_row.controls.append(
                    ft.FilledButton(
                        lbl, icon=ni,
                        bgcolor=nc, color="#FFFFFF",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            elevation=2),
                        on_click=_do_change))

            status_area.controls = [
                note_tf,
                ft.Container(height=4),
                btn_row,
            ]
            try: status_area.update()
            except Exception: pass

        # ── Métriques ─────────────────────────────────────────────────────────────
        def _metric(val, lbl, c):
            return ft.Container(expand=True,
                bgcolor=f"#10{c[1:]}",border_radius=12,
                padding=P(10,10,10,10),
                border=ft.Border.all(1,f"#30{c[1:]}"),
                content=ft.Column([
                    ft.Text(str(val),size=18,weight=ft.FontWeight.BOLD,
                            color=c,text_align=ft.TextAlign.CENTER),
                    ft.Text(lbl,size=9,color=MUT,text_align=ft.TextAlign.CENTER),
                ],spacing=2,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))

        eff = ""
        if duree_r and duree_e:
            ratio = duree_r / duree_e
            eff   = f"{ratio*100:.0f}%"

        _build_history()
        _build_actions()

        header_color = DNG if retard else wf_color

        return ft.Container(bgcolor=BG, expand=True,
            content=ft.Column([
                # ── Header ──────────────────────────────────────────────────────
                ft.Container(
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1,-1), end=ft.Alignment(1,0.8),
                        colors=[f"#18{header_color[1:]}", f"#08{header_color[1:]}"]),
                    border=ft.Border.all(0,BRD),
                    padding=P(16,16,16,16), shadow=SH(10,"20"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=36,height=36,border_radius=18,
                                bgcolor="#18FFFFFF",alignment=ft.Alignment(0,0),ink=True,
                                on_click=lambda e:go_to("maintenance"),
                                content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                                                color="#FFFFFF",size=17)),
                            ft.Column([
                                ft.Text(f"OT #{ot_id}",size=12,color="#99FFFFFF",
                                        weight=ft.FontWeight.W_500),
                                ft.Text(equip,size=16,weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF",max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                            ],spacing=1,expand=True,tight=True),
                            ft.Container(
                                bgcolor=f"#25{header_color[1:]}",border_radius=10,
                                padding=P(8,6,8,6),
                                border=ft.Border.all(1,f"#44{header_color[1:]}"),
                                content=ft.Column([
                                    ft.Text(elapsed_str,size=14,
                                            weight=ft.FontWeight.BOLD,color=timer_c,
                                            text_align=ft.TextAlign.CENTER),
                                    ft.Text("Écoulé",size=9,color="#88FFFFFF",
                                            text_align=ft.TextAlign.CENTER),
                                ],spacing=0,tight=True,
                                 horizontal_alignment=ft.CrossAxisAlignment.CENTER)),
                        ],spacing=10),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Container(
                                bgcolor=f"#18{tc[1:]}",border_radius=8,padding=P(8,4,8,4),
                                content=ft.Text(tl,size=11,color=tc,weight=ft.FontWeight.W_700)),
                            ft.Container(
                                bgcolor=f"#18{pc[1:]}",border_radius=8,padding=P(8,4,8,4),
                                content=ft.Text(prio.title(),size=11,color=pc,
                                                weight=ft.FontWeight.W_700)),
                            ft.Container(expand=True),
                            *([ ft.Container(
                                bgcolor=f"#22{DNG[1:]}",border_radius=8,padding=P(8,4,8,4),
                                border=ft.Border.all(1,DNG),
                                content=ft.Row([
                                    ft.Icon(ft.Icons.WARNING_ROUNDED,color=DNG,size=12),
                                    ft.Text("EN RETARD",size=10,color=DNG,
                                            weight=ft.FontWeight.W_800),
                                ],spacing=4,tight=True)) ] if retard else []),
                            ft.Container(
                                bgcolor=f"#22{wf_color[1:]}",border_radius=8,padding=P(8,4,8,4),
                                border=ft.Border.all(1,wf_color),
                                content=ft.Text(wf_lbl,size=11,color=wf_color,
                                                weight=ft.FontWeight.W_700)),
                        ],spacing=6),
                    ],spacing=0,tight=True)),
                # ── Corps scrollable ─────────────────────────────────────────────
                ft.Container(expand=True,padding=P(12,12,12,0),
                    content=ft.Column([
                        # ── KPI métriques ──────────────────────────────────────
                        ft.Row([
                            _metric(elapsed_str,"Temps ouvert",timer_c),
                            _metric(f"{duree_r:.1f}h" if duree_r else "—",
                                    "Durée réelle",OK),
                            _metric(f"{duree_e:.1f}h" if duree_e else "—",
                                    "Estimé",INFO),
                            _metric(eff or "—","Efficacité",PURP),
                        ],spacing=8),
                        # ── Détails OT ─────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                            border=ft.Border.all(1,BRD),padding=P(14,14,14,14),
                            content=ft.Column([
                                ft.Row([
                                    _box(ft.Icons.ASSIGNMENT_ROUNDED,BLUE,30,14),
                                    ft.Text("Détails",size=13,weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=8),
                                ft.Divider(height=1,color=f"#18{BRD[1:]}"),
                                ft.Row([
                                    ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED,color=MUT,size=14),
                                    ft.Text("Technicien :",size=12,color=MUT),
                                    ft.Text(tech,size=12,color=TXT,weight=ft.FontWeight.W_600),
                                ],spacing=6),
                                *([] if not cause else [
                                    ft.Row([
                                        ft.Icon(ft.Icons.MANAGE_SEARCH_ROUNDED,color=MUT,size=14),
                                        ft.Text("Cause racine :",size=12,color=MUT),
                                        ft.Text(cause,size=12,color=TXT,
                                                weight=ft.FontWeight.W_600),
                                    ],spacing=6)]),
                                *([] if not date_d else [
                                    ft.Row([
                                        ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED,color=OK,size=14),
                                        ft.Text("Début :",size=12,color=MUT),
                                        ft.Text(_fmt_dt(date_d),size=12,color=TXT),
                                    ],spacing=6)]),
                                *([] if not date_f else [
                                    ft.Row([
                                        ft.Icon(ft.Icons.STOP_ROUNDED,color=DNG,size=14),
                                        ft.Text("Fin :",size=12,color=MUT),
                                        ft.Text(_fmt_dt(date_f),size=12,color=TXT),
                                    ],spacing=6)]),
                                ft.Container(bgcolor=f"#0A{BLUE[1:]}",border_radius=8,
                                    padding=P(10,8,10,8),
                                    border=ft.Border.all(1,f"#22{BLUE[1:]}"),
                                    content=ft.Text(obs,size=12,color=TXT)),
                            ],spacing=8,tight=True)),
                        # ── Changer statut ─────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                            border=ft.Border.all(1,f"#30{wf_color[1:]}"),
                            padding=P(14,14,14,14),
                            content=ft.Column([
                                ft.Row([
                                    _box(ft.Icons.SWAP_HORIZ_ROUNDED,wf_color,30,14),
                                    ft.Text("Avancer le statut OT",size=13,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=8),
                                ft.Divider(height=1,color=f"#18{BRD[1:]}"),
                                status_area,
                            ],spacing=8,tight=True)),
                        # ── Timeline historique ────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                            border=ft.Border.all(1,BRD),padding=P(14,14,14,14),
                            content=ft.Column([
                                ft.Row([
                                    _box(ft.Icons.TIMELINE_ROUNDED,PURP,30,14),
                                    ft.Text("Historique des statuts",size=13,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                    ft.Container(expand=True),
                                    ft.Container(
                                        bgcolor=f"#18{PURP[1:]}",border_radius=8,
                                        padding=P(8,3,8,3),
                                        content=ft.Text(f"{len(history)} entrée(s)",
                                            size=10,color=PURP,weight=ft.FontWeight.W_600)),
                                ],spacing=8),
                                ft.Divider(height=1,color=f"#18{BRD[1:]}"),
                                hist_col,
                            ],spacing=8,tight=True)),
                        ft.Container(height=80),
                    ],spacing=10,scroll=ft.ScrollMode.AUTO,expand=True)),
            ],spacing=0))

    # ─────────────────────────────────────────────────────────────────────────────
    def _s_panne():
        ST3={"type_panne":"mecanique","impact":"aucun","prio":"basse"}
        type_grid  = ft.Row(wrap=True,spacing=8)
        impact_row = ft.Row(spacing=6)
        prio_badge = ft.Container()
        equip_opts=[ft.dropdown.Option(r["equipment_label"],r["equipment_label"])
                    for r in list_maintenance_cache()] or \
                   [ft.dropdown.Option("Équipement non listé","Équipement non listé")]
        eq_dd   = ft.Dropdown(label="Équipement concerné *",border_radius=10,
                              options=equip_opts,border_color=BRD,focused_border_color=DNG)
        symp_tf = _tf("Symptômes / Observations *",ml=True,lines=3)
        dur_tf  = _tf("Durée arrêt (minutes)",kb=ft.KeyboardType.NUMBER)
        tech_tf = _tf("Technicien alerté (optionnel)")

        # ── Type de panne grid ────────────────────────────────────────────────────
        def _rebuild_type_grid():
            def _btn(k):
                active=ST3["type_panne"]==k
                c=TYPE_PANNE_COLORS.get(k,MUT); ico=TYPE_PANNE_ICONS.get(k,ft.Icons.HELP_OUTLINE_ROUNDED)
                lbl=TYPE_PANNE_LABELS.get(k,k)
                def click(e,kk=k):
                    ST3["type_panne"]=kk; _rebuild_type_grid()
                return ft.Container(width=82,border_radius=12,
                    bgcolor=c if active else f"{c}14",
                    border=ft.Border.all(1.5 if active else 1,c if active else f"{c}44"),
                    ink=True,on_click=click,padding=P(8,10,8,10),
                    content=ft.Column([
                        ft.Container(bgcolor="#25FFFFFF" if active else f"{c}18",
                            border_radius=8,width=30,height=30,alignment=AL(0,0),
                            content=ft.Icon(ico,color="#FFFFFF" if active else c,size=15)),
                        ft.Text(lbl,size=10,weight=ft.FontWeight.W_700,
                                color="#FFFFFF" if active else c,
                                text_align=ft.TextAlign.CENTER,max_lines=2),
                    ],spacing=5,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))
            type_grid.controls=[_btn(k) for k in TYPE_PANNE_LABELS]
            try: type_grid.update()
            except Exception: pass

        # ── Impact production ─────────────────────────────────────────────────────
        def _rebuild_impact():
            def _imp(k,lbl,c,ico):
                active=ST3["impact"]==k
                def click(e,kk=k):
                    ST3["impact"]=kk
                    ST3["prio"]=IMPACT_PRIO.get(kk,"haute")
                    _rebuild_impact(); _rebuild_prio()
                return ft.Container(expand=True,border_radius=12,
                    bgcolor=c if active else f"{c}14",
                    border=ft.Border.all(1.5 if active else 1,c if active else f"{c}44"),
                    ink=True,on_click=click,padding=P(6,8,6,8),
                    content=ft.Column([
                        ft.Icon(ico,color="#FFFFFF" if active else c,size=18),
                        ft.Text(lbl,size=10,weight=ft.FontWeight.W_700,
                                color="#FFFFFF" if active else c,
                                text_align=ft.TextAlign.CENTER,max_lines=2),
                    ],spacing=4,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))
            impact_row.controls=[_imp(k,l,c,i) for k,l,c,i in IMPACT_PROD_ITEMS]
            try: impact_row.update()
            except Exception: pass

        def _rebuild_prio():
            prio=ST3["prio"]
            pc={"critique":DNG,"haute":WARN,"moyenne":INFO,"basse":OK}.get(prio,MUT)
            pl={"critique":"Critique","haute":"Haute","moyenne":"Moyenne","basse":"Basse"}.get(prio,"?")
            pi={"critique":ft.Icons.PRIORITY_HIGH_ROUNDED,"haute":ft.Icons.ARROW_UPWARD_ROUNDED,
                "moyenne":ft.Icons.REMOVE_ROUNDED,"basse":ft.Icons.ARROW_DOWNWARD_ROUNDED}.get(prio,ft.Icons.HELP_OUTLINE_ROUNDED)
            prio_badge.bgcolor=f"{pc}18"; prio_badge.border=ft.Border.all(1,f"{pc}44")
            prio_badge.border_radius=10; prio_badge.padding=P(14,10,14,10)
            prio_badge.content=ft.Row([
                ft.Icon(pi,color=pc,size=16),
                ft.Text(f"Priorité auto : {pl}",size=13,color=pc,weight=ft.FontWeight.W_700),
            ],spacing=8,tight=True)
            try: prio_badge.update()
            except Exception: pass

        def save_panne(e=None):
            try:
                equip=str(eq_dd.value or "").strip()
                symp=str(symp_tf.value or "").strip()
                if not equip: raise ValueError("Sélectionnez un équipement.")
                if not symp:  raise ValueError("Décrivez les symptômes observés.")
                try: dur=int(dur_tf.value or 0)
                except ValueError: dur=0
                tech=str(tech_tf.value or "").strip() or None
                imp=ST3["impact"]; prio=ST3["prio"]; tp=ST3["type_panne"]
                imp_lbl={"arret_total":"Arrêt total","partiel":"Arrêt partiel",
                         "degrade":"Dégradé","aucun":"Sans impact"}.get(imp,"?")
                site_id_val=cj("dashboard",{}).get("site_id") or None
                now=datetime.now()
                def do_save(_=None):
                    save_pending_panne({
                        "panne_date":now.strftime("%Y-%m-%d"),
                        "panne_heure":now.strftime("%H:%M"),
                        "equipment_label":equip,"site_id":site_id_val,
                        "type_panne":tp,"symptomes":symp,
                        "impact_production":imp,"duree_arret_min":dur,
                        "priorite":prio,"statut":"signale",
                        "technicien":tech,"cause_racine":None,"actions_correctives":None,
                    })
                    eq_dd.value=None; symp_tf.value=""; dur_tf.value=""; tech_tf.value=""
                    ST3["type_panne"]="mecanique"; ST3["impact"]="aucun"; ST3["prio"]="basse"
                    _rebuild_type_grid(); _rebuild_impact(); _rebuild_prio()
                    notify("Panne déclarée offline.",DNG)
                    go_to("maintenance")
                confirm("Déclarer la panne",
                        f"Équipement : {equip}\nImpact : {imp_lbl} | Priorité : {prio.title()}"
                        +(f"\nArrêt : {dur} min" if dur else ""),
                        do_save,danger=True,yes_lbl="Déclarer")
            except Exception as exc: notify(str(exc),DNG)

        _rebuild_type_grid(); _rebuild_impact(); _rebuild_prio()

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                # ── Header ────────────────────────────────────────────────────
                ft.Container(
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1,-1),end=ft.Alignment(1,0.8),
                        colors=["#3B0A0A","#7F1D1D"]),
                    padding=P(16,16,16,18),shadow=SH(12,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=36,height=36,border_radius=18,
                                bgcolor="#18FFFFFF",alignment=AL(0,0),ink=True,
                                on_click=lambda e:go_to("maintenance"),
                                content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,
                                                color="#FFFFFF",size=17)),
                            ft.Text("Déclarer une Panne",size=17,
                                    weight=ft.FontWeight.BOLD,color="#FFFFFF",
                                    expand=True,text_align=ft.TextAlign.CENTER),
                            ft.Container(width=36,height=36),
                        ],spacing=8),
                        ft.Container(height=8),
                        ft.Row([
                            ft.Icon(ft.Icons.REPORT_PROBLEM_ROUNDED,color="#FCA5A5",size=13),
                            ft.Text("Signalement terrain — enregistré offline",
                                    size=11,color="#FCA5A5"),
                        ],spacing=6),
                    ],spacing=0,tight=True)),
                # ── Body ──────────────────────────────────────────────────────
                ft.Container(expand=True,padding=P(12,14,12,0),
                    content=ft.Column([
                        # ── Équipement ─────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,f"#33{DNG[1:]}"),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{DNG[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.HANDYMAN_ROUNDED,
                                                        color=DNG,size=17)),
                                    ft.Text("Équipement en panne",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                eq_dd,
                            ],spacing=10)),
                        # ── Type de panne ──────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{WARN[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.CATEGORY_ROUNDED,
                                                        color=WARN,size=17)),
                                    ft.Text("Type de défaillance",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                type_grid,
                            ],spacing=12)),
                        # ── Impact production ──────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{DNG[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.FACTORY_ROUNDED,
                                                        color=DNG,size=17)),
                                    ft.Text("Impact production",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                impact_row,
                                prio_badge,
                            ],spacing=10)),
                        # ── Symptômes ──────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{INFO[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED,
                                                        color=INFO,size=17)),
                                    ft.Text("Symptômes observés",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                symp_tf,
                                ft.Row([dur_tf,tech_tf],spacing=8),
                            ],spacing=10)),
                        # ── Submit ─────────────────────────────────────────────
                        ft.Container(bgcolor=DNG,border_radius=16,height=52,
                            ink=True,alignment=AL(0,0),shadow=SH(8,"22"),
                            on_click=save_panne,
                            content=ft.Row([
                                ft.Icon(ft.Icons.REPORT_PROBLEM_ROUNDED,
                                        color="#FFFFFF",size=20),
                                ft.Text("Déclarer la panne",color="#FFFFFF",
                                        size=14,weight=ft.FontWeight.W_700),
                            ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                        ft.Container(height=80),
                    ],spacing=10,scroll=ft.ScrollMode.AUTO,expand=True)),
            ],spacing=0))

    def _s_inspect():
        chk=dict(ins_chk)  # local copy — shared dict reset after save
        checklist_col=ft.Column(spacing=6)
        count_ok =ft.Text("0",size=20,weight=ft.FontWeight.BOLD,color=OK,text_align=ft.TextAlign.CENTER)
        count_nok=ft.Text("0",size=20,weight=ft.FontWeight.BOLD,color=DNG,text_align=ft.TextAlign.CENTER)
        count_tot=ft.Text(f"/ {len(INSPECTION_ITEMS)}",size=11,color=MUT,text_align=ft.TextAlign.CENTER)

        def _build():
            ok=sum(1 for v in chk.values() if v)
            nok=len(chk)-ok
            count_ok.value=str(ok); count_nok.value=str(nok)
            def _row(item):
                checked=chk.get(item,False)
                def _tog(e,it=item):
                    chk[it]=e.control.value; ins_chk[it]=e.control.value; _build()
                return ft.Container(
                    bgcolor=f"#0A{OK[1:]}" if checked else f"#06{DNG[1:]}",
                    border=ft.Border.all(1,f"#40{OK[1:]}" if checked else f"#20{DNG[1:]}"),
                    border_radius=10,padding=P(12,10,12,10),
                    content=ft.Row([
                        ft.Checkbox(value=checked,active_color=OK,on_change=_tog),
                        ft.Text(item,expand=True,size=13,color=TXT),
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if checked
                                else ft.Icons.CANCEL_OUTLINED,
                                color=OK if checked else DNG,size=18),
                    ],spacing=8))
            checklist_col.controls=[_row(it) for it in INSPECTION_ITEMS]
            try: checklist_col.update(); count_ok.update(); count_nok.update()
            except Exception: pass

        def on_save(e=None):
            equip=str(ins_eq.value or "").strip()
            if not equip: notify("Sélectionnez un équipement.",DNG); return
            ok_items =[it for it,v in chk.items() if v]
            nok_items=[it for it,v in chk.items() if not v]
            n_nok=len(nok_items)
            prio=("critique" if n_nok>=5 else "haute" if n_nok>=3
                  else "moyenne" if n_nok>=1 else "basse")
            sign=str(ins_sign.value or "").strip()
            obs=(f"[Inspection] {equip} | OK: {', '.join(ok_items) or 'Aucun'}"
                 f" | NOK: {', '.join(nok_items) or 'Aucun'}"
                 + (f" | Sig: {sign}" if sign else ""))
            site_id_val=cj("dashboard",{}).get("site_id") or None
            def do_save(_=None):
                with get_mobile_connection() as c:
                    c.execute("INSERT INTO pending_maintenance(observation_date,equipment_label,"
                        "site_id,priority,observation) VALUES(?,?,?,?,?)",
                        (date.today().isoformat(),equip,site_id_val,prio,obs))
                for it in chk: chk[it]=False; ins_chk[it]=False
                ins_eq.value=None; ins_sign.value=""
                notify("Inspection enregistrée offline.",OK)
                go_to("maintenance")
            confirm("Valider l'inspection",
                    f"{equip} — {sum(chk.values())}/{len(chk)} points OK — Priorité : {prio.title()}",
                    do_save, yes_lbl="Valider")

        _build()
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                _hdr("Inspection véhicule","maintenance"),
                ft.Container(expand=True,padding=P(14,14,14,14),
                    content=ft.Column([
                        # ── Équipement ─────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                            border=ft.Border.all(1,BRD),padding=P(14,12,14,14),
                            content=ft.Column([
                                ft.Row([_box(ft.Icons.DIRECTIONS_CAR_ROUNDED,BLUE,32,16),
                                    ft.Text("Équipement à inspecter",size=13,
                                            weight=ft.FontWeight.BOLD,color=TXT)],spacing=8),
                                ins_eq,
                            ],spacing=10)),
                        # ── Score ──────────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                            border=ft.Border.all(1,BRD),padding=P(14,12,14,14),
                            content=ft.Row([
                                ft.Column([count_ok,
                                    ft.Text("Conformes",size=10,color=OK,
                                            text_align=ft.TextAlign.CENTER)],
                                    spacing=2,expand=True,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                ft.Container(width=1,height=40,bgcolor=BRD),
                                ft.Column([count_nok,
                                    ft.Text("Non conformes",size=10,color=DNG,
                                            text_align=ft.TextAlign.CENTER)],
                                    spacing=2,expand=True,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                ft.Container(width=1,height=40,bgcolor=BRD),
                                ft.Column([count_tot,
                                    ft.Text("Total points",size=10,color=MUT,
                                            text_align=ft.TextAlign.CENTER)],
                                    spacing=2,expand=True,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            ],spacing=12)),
                        # ── Checklist ──────────────────────────────────────────
                        ft.Row([
                            ft.Icon(ft.Icons.CHECKLIST_ROUNDED,color=BLUE,size=14),
                            ft.Text("Checklist",size=13,weight=ft.FontWeight.W_700,
                                    color=TXT,expand=True),
                        ],spacing=8),
                        checklist_col,
                        # ── Photo + Signature ───────────────────────────────────
                        ft.Row([
                            ft.Container(bgcolor=f"#10{INFO[1:]}",border_radius=12,
                                border=ft.Border.all(1,f"#44{INFO[1:]}"),expand=True,height=46,
                                ink=True,alignment=AL(0,0),
                                on_click=lambda e:notify(
                                    "Fonctionnalité photo disponible prochainement.",INFO),
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED,color=INFO,size=18),
                                    ft.Text("Photo",color=INFO,size=12,
                                            weight=ft.FontWeight.W_700),
                                ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                        ],spacing=10),
                        ins_sign,
                        # ── Submit ─────────────────────────────────────────────
                        _btn("Valider l'inspection",ft.Icons.CHECK_CIRCLE_ROUNDED,OK,on_save),
                        ft.Container(height=20),
                    ],spacing=10,scroll=ft.ScrollMode.AUTO,expand=True)),
            ],spacing=0))

    def _s_toolbox():
        _r_toolbox()
        today=date.today().isoformat(); topic=get_toolbox_cache(today)
        theme_name=""
        if topic:
            raw=str(topic["theme"] or ""); theme_name=raw.split(" / ")[0].strip() if " / " in raw else raw
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(16,18,16,22),shadow=SH(10,"20"),
                    content=ft.Column([
                        ft.Row([_box(ft.Icons.RECORD_VOICE_OVER_OUTLINED,"#FFFFFF",26,16),
                            ft.Text("Toolbox Talk",size=18,weight=ft.FontWeight.BOLD,color="#FFFFFF",expand=True),
                            ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED,color="#93C5FD",size=20)],spacing=8),
                        ft.Container(height=8),
                        ft.Text(f"Aujourd'hui · {date.today().strftime('%d %B %Y')}",size=11,color="#93C5FD"),
                        ft.Text(theme_name or "Aucun thème disponible",size=15,
                                weight=ft.FontWeight.BOLD,color="#FFFFFF")],spacing=4,tight=True)),
                ft.Container(expand=True,padding=P(12,14,12,12),
                    content=ft.Column([_sec("Session du jour",ft.Icons.TODAY_OUTLINED),
                        *tb_today.controls,
                        _sec("Historique récent",ft.Icons.HISTORY_OUTLINED),
                        *tb_hist.controls,ft.Container(height=70)],
                        scroll=ft.ScrollMode.AUTO,expand=True,spacing=12))],spacing=0))

    def _s_alerts():
        _r_alerts()
        tab=ST.get("alerts_tab","all"); all_a=cj("alerts",[])
        if not isinstance(all_a,list): all_a=[]
        counts={"all":len(all_a),
                "critique":sum(1 for a in all_a if a.get("niveau") in {"critique","haut"}),
                "urgent":  sum(1 for a in all_a if a.get("niveau") in {"urgent","moyen"}),
                "info":    sum(1 for a in all_a if a.get("niveau") in {"info","bas"})}
        tabs=[("all","Toutes",BLUE),("critique","Critiques",DNG),("urgent","Urgentes",WARN),("info","Info",INFO)]
        def _pill(k,lbl,c):
            active=tab==k
            return ft.Container(
                bgcolor=c if active else f"{c}18",
                border=ft.Border.all(1,c if active else f"{c}40"),
                border_radius=20,padding=P(12,7,12,7),ink=True,
                on_click=lambda e,kk=k:[ST.__setitem__("alerts_tab",kk),go_to("alerts")],
                content=ft.Row([
                    ft.Text(lbl,size=12,weight=ft.FontWeight.W_600,
                            color="#FFFFFF" if active else c),
                    ft.Container(bgcolor="#44FFFFFF" if active else f"{c}30",border_radius=10,
                        padding=P(5,1,5,1),
                        content=ft.Text(str(counts[k]),size=10,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF" if active else c))],
                    spacing=5,tight=True))
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(16,18,16,22),shadow=SH(10,"20"),
                    content=ft.Column([
                        ft.Row([_box(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,"#FFFFFF",26,16),
                            ft.Text("Alertes",size=18,weight=ft.FontWeight.BOLD,color="#FFFFFF",expand=True),
                            _badge(str(counts["all"]),"#FFFFFF","#30FFFFFF")],spacing=8),
                        ft.Container(height=10),
                        ft.Row([_pill(k,l,c) for k,l,c in tabs],spacing=8,scroll=ft.ScrollMode.HIDDEN)],
                        spacing=0,tight=True)),
                ft.Container(expand=True,padding=P(12,14,12,12),
                    content=ft.Column([al_col,_div(),
                        _btn("Déclarer un incident",ft.Icons.ADD_ALERT_OUTLINED,DNG,
                             lambda e:go_to("incident"),48),
                        ft.Container(height=70)],
                        scroll=ft.ScrollMode.AUTO,expand=True,spacing=12))],spacing=0))

    def _s_incident():
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([_hdr("Déclarer un incident","alerts"),
                _body(
                    _card(ft.Column([_sec("Type d'évènement",ft.Icons.CATEGORY_OUTLINED),inc_tr],spacing=8),P(14,14,14,14)),
                    _card(ft.Column([_sec("Gravité",ft.Icons.THERMOSTAT_OUTLINED),inc_gr],spacing=8),P(14,14,14,14)),
                    _card(ft.Column([_sec("Détails",ft.Icons.DESCRIPTION_OUTLINED),
                        inc_date,inc_lieu,inc_emp],spacing=10),P(14,14,14,14)),
                    _card(ft.Column([_sec("Description & Actions",ft.Icons.EDIT_NOTE_OUTLINED),
                        inc_desc,inc_act],spacing=10),P(14,14,14,14)),
                    _btn("Enregistrer offline",ft.Icons.SAVE_ALT_OUTLINED,DNG,save_inc))],spacing=0))

    def _s_profile():
        _r_profile()
        uname=get_setting("identity_username") or "—"
        urole=get_setting("profile_label") or "Terrain"
        site=cj("dashboard",{}).get("site") or "SYAMA"
        tot=total_pending(); srv=bool(get_setting("server_url") and get_setting("token"))
        inits="".join(w[0].upper() for w in uname.split() if w)[:2] or "?"
        role_short=(urole[:8] if len(urole)>8 else urole)
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(20,28,20,28),shadow=SH(12,"22"),
                    content=ft.Column([
                        ft.Row([_ava(inits,64),ft.Container(width=16),
                            ft.Column([
                                ft.Text(uname.upper(),size=17,weight=ft.FontWeight.BOLD,color="#FFFFFF"),
                                ft.Container(bgcolor="#22FFFFFF",border_radius=12,padding=P(10,3,10,3),
                                    content=ft.Text(urole,size=11,color="#FFFFFF",weight=ft.FontWeight.W_600)),
                                ft.Row([ft.Icon(ft.Icons.LOCATION_ON_OUTLINED,color="#93C5FD",size=13),
                                    ft.Text(site,size=12,color="#93C5FD")],spacing=4)],
                                spacing=6,expand=True)],spacing=0),
                        ft.Container(height=16),
                        ft.Container(bgcolor="#12FFFFFF",border_radius=14,padding=P(0,8,0,8),
                            content=ft.Row([
                                _mstat(str(tot) if tot else "0","En attente"),
                                ft.Container(width=1,height=30,bgcolor="#33FFFFFF"),
                                _mstat("✓" if srv else "✗","Serveur"),
                                ft.Container(width=1,height=30,bgcolor="#33FFFFFF"),
                                _mstat(role_short,"Rôle"),
                            ],spacing=0)),
                    ],spacing=0,tight=True)),
                ft.Container(expand=True,padding=P(12,14,12,12),
                    content=ft.Column([
                        _sec("Mon compte",ft.Icons.MANAGE_ACCOUNTS_OUTLINED),
                        pr_col,
                        ft.Container(height=20),
                        ft.Text(f"OREZONE QHSE Mobile v{APP_VERSION}",
                                size=10,color=MUT,text_align=ft.TextAlign.CENTER),
                        ft.Container(height=70),
                    ],scroll=ft.ScrollMode.AUTO,expand=True,spacing=10))],spacing=0))

    def _s_ppe_assign():
        SEL={lbl:False for lbl,_ in PPE_ITEMS}
        chk_col=ft.Column(spacing=8)
        n_sel_txt=ft.Text("0 article(s) sélectionné(s)",size=12,color=MUT)

        def rebuild_list():
            n=sum(1 for v in SEL.values() if v)
            n_sel_txt.value=f"{n} article(s) sélectionné(s)"
            try: n_sel_txt.update()
            except Exception: pass
            def _item(lbl,ico):
                sel=SEL[lbl]
                def tog(e,k=lbl):
                    SEL[k]=not SEL[k]; rebuild_list()
                c=OK if sel else MUT
                return ft.Container(bgcolor=f"#0A{c[1:]}" if sel else CARD,
                    border_radius=14,padding=P(14,12,14,12),
                    border=ft.Border.all(1.5 if sel else 1, f"#44{c[1:]}" if sel else BRD),
                    ink=True,on_click=tog,
                    content=ft.Row([
                        ft.Container(bgcolor=f"#18{c[1:]}",border_radius=10,
                            width=38,height=38,alignment=AL(0,0),
                            content=ft.Icon(ico,color=c,size=19)),
                        ft.Text(lbl,size=13,weight=ft.FontWeight.W_600,
                                color=TXT if not sel else OK,expand=True),
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if sel
                                else ft.Icons.RADIO_BUTTON_UNCHECKED_OUTLINED,
                                color=OK if sel else BRD,size=22),
                    ],spacing=12))
            chk_col.controls=[_item(l,i) for l,i in PPE_ITEMS]
            try: chk_col.update()
            except Exception: pass

        rebuild_list()

        def _on_save(e=None):
            save_ppe_assign(SEL,e)

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(16,16,16,18),shadow=SH(12,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#18FFFFFF",
                                alignment=AL(0,0),ink=True,on_click=lambda e:go_to("profile"),
                                content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,
                                                color="#FFFFFF",size=17)),
                            ft.Text("Dotation EPI",size=17,weight=ft.FontWeight.BOLD,
                                    color="#FFFFFF",expand=True,text_align=ft.TextAlign.CENTER),
                            ft.Container(width=36,height=36),
                        ],spacing=8),
                        ft.Container(height=6),
                        ft.Row([
                            ft.Icon(ft.Icons.SAFETY_CHECK_OUTLINED,color="#93C5FD",size=13),
                            ft.Text("Équipements de protection individuelle",size=11,color="#93C5FD"),
                        ],spacing=6),
                    ],spacing=0,tight=True)),
                ft.Container(expand=True,padding=P(12,14,12,0),
                    content=ft.Column([
                        # Section employé
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{BLUE[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.PERSON_OUTLINED,color=BLUE,size=17)),
                                    ft.Text("Bénéficiaire",size=14,weight=ft.FontWeight.BOLD,color=TXT,expand=True),
                                ],spacing=10),
                                ppa_emp,
                                ft.Row([ppa_tail],spacing=8),
                            ],spacing=12)),
                        # Section articles EPI
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{OK[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.SAFETY_CHECK_OUTLINED,color=OK,size=17)),
                                    ft.Text("Articles à remettre",size=14,weight=ft.FontWeight.BOLD,color=TXT,expand=True),
                                    n_sel_txt,
                                ],spacing=10),
                                chk_col,
                            ],spacing=12)),
                        # Observations
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.Border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{INFO[1:]}",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED,color=INFO,size=17)),
                                    ft.Text("Observations",size=14,weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                ppa_obs,
                            ],spacing=12)),
                        ft.Container(bgcolor=OK,border_radius=16,height=52,
                            ink=True,alignment=AL(0,0),shadow=SH(8,"22"),
                            on_click=_on_save,
                            content=ft.Row([
                                ft.Icon(ft.Icons.ASSIGNMENT_TURNED_IN_ROUNDED,color="#FFFFFF",size=20),
                                ft.Text("Enregistrer la dotation",color="#FFFFFF",size=14,
                                        weight=ft.FontWeight.W_700),
                            ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                        ft.Container(height=80),
                    ],spacing=10,scroll=ft.ScrollMode.AUTO,expand=True)),
            ],spacing=0))

    def _s_ppe_check():
        _rebuild_ppe()
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([_hdr("Vérification EPI","profile"),
                _body(ppe_emp,_sec("Équipements de protection",ft.Icons.SAFETY_CHECK_OUTLINED),
                    ft.Text("Sélectionnez OK / NOK / N/A pour chaque équipement.",size=11,color=MUT),
                    ppe_col,ppe_obs,_btn("Enregistrer la vérification",ft.Icons.SAVE_OUTLINED,INFO,save_ppe))],spacing=0))

    def _s_attendance():
        today_iso = date.today().isoformat()
        MONTHS=["Janv","Févr","Mars","Avr","Mai","Juin","Juil","Août","Sep","Oct","Nov","Déc"]
        DAYS=["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
        d=date.today()
        day_lbl=f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month-1]}"

        STATUSES=[
            ("present","Présent",  ft.Icons.CHECK_CIRCLE_ROUNDED,    OK),
            ("absent", "Absent",   ft.Icons.CANCEL_ROUNDED,          DNG),
            ("mission","Mission",  ft.Icons.FLIGHT_TAKEOFF_OUTLINED, PURP),
            ("maladie","Maladie",  ft.Icons.LOCAL_HOSPITAL_OUTLINED, WARN),
            ("conge",  "Congé",    ft.Icons.BEACH_ACCESS_OUTLINED,   INFO),
        ]
        SCOL={k:c for k,_,_,c in STATUSES}
        SLBL={k:l for k,l,_,_ in STATUSES}

        # ── Local state ────────────────────────────────────────────────────────
        SEL: set[int] = set()
        ACT = {"status":"present"}
        SRC = {"q":""}
        SHOW_BAR = {"v": False}

        # ── Reusable components ────────────────────────────────────────────────
        list_col  = ft.Column(spacing=6, expand=True)
        hdr_count = ft.Text("0/0",size=16,weight=ft.FontWeight.BOLD,color="#FFFFFF",
                            text_align=ft.TextAlign.CENTER)
        hdr_lbl   = ft.Text("pointés",size=10,color="#93C5FD",
                            text_align=ft.TextAlign.CENTER)
        sel_lbl   = ft.Text("0 sélectionné(s)",size=13,weight=ft.FontWeight.W_700,
                            color=BLUE,expand=True)
        bar_col   = ft.Column(spacing=10,tight=True)
        bar_wrap  = ft.Container(visible=False,bgcolor=CARD,border_radius=16,
                                 shadow=SH(20,"30"),padding=P(14,12,14,16),
                                 border=ft.Border.all(1,BRD),
                                 content=bar_col)
        pill_row  = ft.Row(spacing=6,scroll=ft.ScrollMode.AUTO)
        time_row  = ft.Row(spacing=8,visible=True)
        date_fld  = ft.TextField(label="Date",value=today_iso,border_radius=10,
                                  border_color=BRD,focused_border_color=BLUE,
                                  dense=True)
        t_in  = ft.TextField(label="Entrée",value="06:00",border_radius=10,
                              border_color=BRD,focused_border_color=OK,dense=True,expand=True)
        t_out = ft.TextField(label="Sortie",value="14:00",border_radius=10,
                              border_color=BRD,focused_border_color=DNG,dense=True,expand=True)
        srch  = ft.TextField(hint_text="Rechercher un employé...",
                              prefix_icon=ft.Icons.SEARCH_OUTLINED,
                              border_radius=12,border_color=BRD,
                              focused_border_color=BLUE,dense=True,
                              on_change=lambda e:[SRC.__setitem__("q",e.control.value or ""),rebuild()])

        def _get_rec():
            try:
                return {r["employee_id"]:r["status"]
                        for r in list_pending() if r["date_presence"]==today_iso}
            except Exception: return {}

        def _badge(status):
            c=SCOL.get(status,MUT); l=SLBL.get(status,status)
            return ft.Container(bgcolor=f"{c}18",border_radius=8,
                padding=P(8,3,8,3),border=ft.Border.all(1,f"{c}40"),
                content=ft.Text(l,size=10,color=c,weight=ft.FontWeight.W_700))

        def _row(emp,is_sel,done_status=None):
            eid=emp["id_employe"]; nm=employee_name(emp)
            role=str(emp["fonction"] or "—"); site_s=str(emp["site"] or "")
            inits="".join(w[0].upper() for w in nm.split() if w)[:2] or "?"
            done=done_status is not None
            sc=SCOL.get(done_status,OK) if done else (BLUE if is_sel else MUT)
            bg=f"#14{BLUE[1:]}" if is_sel else (f"{sc}08" if done else CARD)
            br=BLUE if is_sel else (f"{sc}40" if done else BRD)
            bw=1.5 if is_sel else 1
            def toggle(e,ei=eid):
                if ei in SEL: SEL.discard(ei)
                else: SEL.add(ei)
                rebuild()
            return ft.Container(bgcolor=bg,border_radius=14,
                border=ft.Border.all(bw,br),padding=P(10,10,12,10),
                ink=not done,
                on_click=None if done else (lambda e,ei=eid:toggle(e,ei)),
                content=ft.Row([
                    (ft.Checkbox(value=is_sel,active_color=BLUE,on_change=toggle)
                     if not done else
                     ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED,color=sc,size=22)),
                    _ava(inits,40,sc),
                    ft.Column([
                        ft.Text(nm,size=13,weight=ft.FontWeight.W_700,
                                color=BLUE if is_sel else TXT,
                                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([
                            ft.Container(bgcolor=f"{sc}18",border_radius=4,
                                padding=P(5,2,5,2),
                                content=ft.Text(role,size=10,color=sc,
                                                weight=ft.FontWeight.W_600)),
                            ft.Text(site_s,size=10,color=MUT),
                        ],spacing=4),
                    ],spacing=2,expand=True),
                    _badge(done_status) if done else
                    ft.Icon(ft.Icons.CHECK_BOX_ROUNDED if is_sel
                            else ft.Icons.CHECK_BOX_OUTLINE_BLANK_OUTLINED,
                            color=BLUE if is_sel else BRD,size=20),
                ],spacing=10))

        def _rebuild_pills():
            def _pill(k,lbl,ico,c):
                active=ACT["status"]==k
                def _click(e,kk=k):
                    ACT["status"]=kk
                    time_row.visible=(kk=="present")
                    try: time_row.update()
                    except Exception: pass
                    _rebuild_pills()
                return ft.Container(border_radius=20,padding=P(14,7,14,7),
                    bgcolor=c if active else f"{c}18",
                    border=ft.Border.all(1.5,c if active else f"{c}44"),
                    ink=True,on_click=_click,
                    content=ft.Row([
                        ft.Icon(ico,color="#FFFFFF" if active else c,size=15),
                        ft.Text(lbl,size=11,weight=ft.FontWeight.W_700,
                                color="#FFFFFF" if active else c),
                    ],spacing=5,tight=True))
            pill_row.controls=[_pill(k,l,i,c) for k,l,i,c in STATUSES]
            try: pill_row.update()
            except Exception: pass

        def rebuild():
            try:
                rec=_get_rec()
                q=SRC["q"].strip().lower()
                all_emps=list_employees()
                pending=[e for e in all_emps if e["id_employe"] not in rec]
                done_emps=[e for e in all_emps if e["id_employe"] in rec]
                if q:
                    flt=lambda e:(q in employee_name(e).lower() or
                                  q in str(e["fonction"] or "").lower() or
                                  q in str(e["site"] or "").lower())
                    pending=[e for e in pending if flt(e)]
                    done_emps=[e for e in done_emps if flt(e)]

                all_ids={e["id_employe"] for e in pending}
                n_pending=len(pending); n_done=len(rec)
                n_total=len(all_emps); n_sel=len(SEL)
                all_sel=bool(all_ids) and all_ids.issubset(SEL)

                rows=[]
                if pending:
                    rows.append(ft.Container(bgcolor=CARD,border_radius=12,
                        padding=P(12,10,14,10),border=ft.Border.all(1,BRD),
                        content=ft.Row([
                            ft.Checkbox(value=all_sel,active_color=BLUE,
                                on_change=lambda e:[
                                    SEL.update(all_ids) if e.control.value
                                    else SEL.difference_update(all_ids),
                                    rebuild()]),
                            ft.Text("Tout sélectionner",size=13,
                                    weight=ft.FontWeight.W_600,color=TXT,expand=True),
                            ft.Text(f"{n_pending} restants",size=11,color=MUT),
                        ],spacing=8)))
                    for emp in pending:
                        rows.append(_row(emp, emp["id_employe"] in SEL))
                if done_emps:
                    rows.append(ft.Container(height=4))
                    rows.append(ft.Container(bgcolor=f"#0A{OK[1:]}",border_radius=10,
                        padding=P(12,8,12,8),border=ft.Border.all(1,f"#30{OK[1:]}"),
                        content=ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED,color=OK,size=15),
                            ft.Text(f"Pointés aujourd'hui ({len(done_emps)})",
                                    size=12,weight=ft.FontWeight.W_600,color=OK,expand=True),
                        ],spacing=8)))
                    for emp in done_emps:
                        rows.append(_row(emp,False,rec.get(emp["id_employe"])))
                if not rows:
                    rows.append(ft.Container(padding=P(0,40,0,0),
                        content=ft.Column([
                            ft.Icon(ft.Icons.PEOPLE_OUTLINE,color=BRD,size=52),
                            ft.Text("Aucun employé trouvé",size=14,color=MUT,
                                    text_align=ft.TextAlign.CENTER),
                        ],spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER)))

                list_col.controls=rows
                hdr_count.value=f"{n_done}/{n_total}"
                bar_wrap.visible=n_sel>0
                sel_lbl.value=f"{n_sel} employé(s) sélectionné(s)"
                for ctrl in [list_col,hdr_count,bar_wrap,sel_lbl]:
                    try: ctrl.update()
                    except Exception: pass
            except Exception as exc:
                list_col.controls=[ft.Text(f"Erreur: {exc}",color=DNG,size=12)]
                try: list_col.update()
                except Exception: pass

        def apply_status(e=None):
            if not SEL: return
            status=ACT["status"]; n=len(SEL); lbl=SLBL.get(status,status)
            time_info=""
            if status=="present" and t_in.value:
                time_info=f"\nEntrée {t_in.value}" + (f" — Sortie {t_out.value}" if t_out.value else "")
            def do_apply(_=None):
                try:
                    with get_mobile_connection() as c:
                        for eid in list(SEL):
                            emp=get_employee(eid)
                            if not emp: continue
                            c.execute("DELETE FROM pending_attendance WHERE employee_id=? AND date_presence=?",
                                      (eid,today_iso))
                            c.execute(
                                "INSERT INTO pending_attendance(employee_id,employee_name,"
                                "date_presence,status,heure_entree,heure_sortie)"
                                " VALUES(?,?,?,?,?,?)",
                                (eid,employee_name(emp),today_iso,status,
                                 t_in.value if status=="present" else None,
                                 t_out.value if status=="present" else None))
                    notify(f"{n} pointage(s) « {lbl} » enregistrés.",OK)
                    SEL.clear(); rebuild()
                except Exception as exc: notify(f"Erreur : {exc}",DNG)
            confirm("Appliquer le statut",
                    f"Marquer {n} employé(s) comme « {lbl} » ?\nDate : {today_iso}{time_info}",
                    do_apply, yes_lbl="Appliquer")

        # ── Assemble compact action bar ────────────────────────────────────────
        time_row.controls=[
            ft.Container(expand=True,content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.ARROW_UPWARD_OUTLINED,color=OK,size=12),
                        ft.Text("Entrée",size=10,color=OK,weight=ft.FontWeight.W_600)],
                       spacing=3),
                t_in,
            ],spacing=3)),
            ft.Container(width=8),
            ft.Container(expand=True,content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.ARROW_DOWNWARD_OUTLINED,color=DNG,size=12),
                        ft.Text("Sortie",size=10,color=DNG,weight=ft.FontWeight.W_600)],
                       spacing=3),
                t_out,
            ],spacing=3)),
        ]
        bar_col.controls=[
            # ── Top: selection info + clear ──────────────────────────────────
            ft.Row([
                ft.Container(bgcolor=f"#15{BLUE[1:]}",border_radius=8,width=30,height=30,
                    alignment=AL(0,0),
                    content=ft.Icon(ft.Icons.PEOPLE_ALT_OUTLINED,color=BLUE,size=16)),
                sel_lbl,
                ft.Container(border_radius=8,padding=P(8,5,8,5),
                    bgcolor=f"#12{DNG[1:]}",border=ft.Border.all(1,f"#30{DNG[1:]}"),
                    ink=True,on_click=lambda e:[SEL.clear(),rebuild()],
                    content=ft.Row([
                        ft.Icon(ft.Icons.CLOSE_ROUNDED,color=DNG,size=13),
                        ft.Text("Effacer",size=11,color=DNG,weight=ft.FontWeight.W_700),
                    ],spacing=4,tight=True)),
            ],spacing=8),
            # ── Status pills ─────────────────────────────────────────────────
            pill_row,
            # ── Time row (Présent only) ───────────────────────────────────────
            time_row,
            # ── Apply button ─────────────────────────────────────────────────
            ft.Container(bgcolor=BLUE,border_radius=14,height=46,
                ink=True,alignment=AL(0,0),shadow=SH(6,"20"),
                on_click=apply_status,
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_ROUNDED,color="#FFFFFF",size=20),
                    ft.Text("Appliquer",color="#FFFFFF",size=14,
                            weight=ft.FontWeight.W_700),
                ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
        ]
        _rebuild_pills()
        rebuild()

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Stack([
                # ── Main column ───────────────────────────────────────────────
                ft.Column([
                    # Header
                    ft.Container(gradient=GRAD,padding=P(16,16,16,18),shadow=SH(12,"22"),
                        content=ft.Column([
                            ft.Row([
                                ft.Container(width=36,height=36,border_radius=18,
                                    bgcolor="#18FFFFFF",alignment=AL(0,0),
                                    ink=True,on_click=lambda e:go_to("home"),
                                    content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,
                                                    color="#FFFFFF",size=17)),
                                ft.Text("Pointage terrain",size=17,weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF",expand=True,
                                        text_align=ft.TextAlign.CENTER),
                                ft.Container(width=36,height=36,border_radius=18,
                                    bgcolor="#18FFFFFF",alignment=AL(0,0),
                                    ink=True,on_click=lambda e:rebuild(),
                                    content=ft.Icon(ft.Icons.REFRESH_OUTLINED,
                                                    color="#FFFFFF",size=18)),
                            ],spacing=8),
                            ft.Container(height=8),
                            ft.Row([
                                ft.Column([
                                    ft.Text(day_lbl,size=12,color="#93C5FD"),
                                    ft.Text(f"{len(list_employees())} employés · SYAMA",
                                            size=11,color="#60A5FA"),
                                ],spacing=2,expand=True),
                                ft.Container(bgcolor="#18FFFFFF",border_radius=12,
                                    padding=P(14,8,14,8),
                                    content=ft.Column([hdr_count,hdr_lbl],spacing=1,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        tight=True)),
                            ],spacing=10),
                        ],spacing=0,tight=True)),
                    # Search
                    ft.Container(bgcolor=CARD,shadow=SH(4,"06"),
                        padding=P(12,8,12,8),content=srch),
                    # List (extra bottom padding so action bar doesn't cover last item)
                    ft.Container(expand=True,padding=P(10,6,10,6),
                        content=ft.Column([list_col,ft.Container(height=260)],
                            spacing=0,scroll=ft.ScrollMode.AUTO,expand=True)),
                ],spacing=0,expand=True),
                # ── Floating action bar (only when selection active) ───────────
                ft.Container(bottom=0,left=0,right=0,padding=P(8,0,8,10),
                    content=bar_wrap),
            ]))

    def _s_timesheet():
        import os as _os, csv as _csv
        from pathlib import Path
        from datetime import timedelta as _td

        MONTHS_FR=["Janvier","Février","Mars","Avril","Mai","Juin",
                   "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
        MONTHS_SHORT=["Jan","Fév","Mar","Avr","Mai","Jun",
                      "Jul","Aoû","Sep","Oct","Nov","Déc"]
        d=date.today()
        TS={"month":d.month,"year":d.year,"ts_type":"1_25","dl_status":"","dl_color":""}

        def get_exports_dir():
            p=MOBILE_DIR/"exports"
            p.mkdir(parents=True,exist_ok=True); return p
        def get_ts_dir():
            p=MOBILE_DIR/"timesheets"
            p.mkdir(parents=True,exist_ok=True); return p
        def open_file(p):
            try: _os.startfile(str(p))
            except Exception: pass
        def month_prefix(): return f"{TS['year']}-{TS['month']:02d}"

        def get_period_range():
            yr,mo,tp=TS["year"],TS["month"],TS["ts_type"]
            if tp=="1_25":
                start=date(yr,mo,1); end=date(yr,mo,25)
            else:
                nm=mo+1 if mo<12 else 1; ny=yr if mo<12 else yr+1
                start=date(yr,mo,21); end=date(ny,nm,20)
            days=[]; cur=start
            while cur<=end: days.append(cur); cur+=_td(days=1)
            return start,end,days

        def _period_months():
            start,end,_=get_period_range()
            pfxs=set(); cur=date(start.year,start.month,1)
            stop=date(end.year,end.month,1)
            while cur<=stop:
                pfxs.add(cur.strftime("%Y-%m"))
                cur=date(cur.year+(1 if cur.month==12 else 0),(cur.month%12)+1,1)
            return sorted(pfxs)

        def period_label():
            start,end,_=get_period_range()
            if start.year==end.year and start.month==end.month:
                return f"{start.day:02d} au {end.day:02d} {MONTHS_SHORT[start.month-1]} {start.year}"
            return f"{start.day:02d} {MONTHS_SHORT[start.month-1]} → {end.day:02d} {MONTHS_SHORT[end.month-1]} {end.year}"

        def get_att_period():
            start,end,_=get_period_range()
            ss,es=start.isoformat(),end.isoformat()
            recs={}
            for pfx in _period_months():
                for r in list_pending():
                    r=dict(r); dp=str(r.get("date_presence",""))
                    if dp.startswith(pfx) and ss<=dp<=es:
                        recs[(r.get("employee_id"),dp)]=r
                for r in list_synced_attendance(pfx):
                    r=dict(r)
                    r.setdefault("employee_name",(f"{r.get('nom','')} {r.get('prenom','')}").strip())
                    dp=str(r.get("date_presence",""))
                    if ss<=dp<=es:
                        k=(r.get("employee_id"),dp)
                        if k not in recs: recs[k]=r
            return sorted(recs.values(),key=lambda x:(x.get("employee_name",""),x.get("date_presence","")))

        def get_att():
            pfx=month_prefix()
            pending=[dict(r) for r in list_pending() if str(r["date_presence"]).startswith(pfx)]
            pending_keys={(r["employee_id"],r["date_presence"]) for r in pending}
            synced=list_synced_attendance(pfx)
            for r in synced:
                r.setdefault("employee_name",(f"{r.get('nom','')} {r.get('prenom','')}").strip())
            merged=pending+[r for r in synced if (r.get("employee_id"),r.get("date_presence")) not in pending_keys]
            return sorted(merged,key=lambda x:(x.get("date_presence",""),x.get("employee_name","")))

        def get_tb():
            pfx=month_prefix()
            pending=[dict(r) for r in list_pending_toolbox() if str(r["date_theme"]).startswith(pfx)]
            pending_dates={r["date_theme"] for r in pending}
            synced=[r for r in list_synced_toolbox(pfx) if r.get("date_theme") not in pending_dates]
            return sorted(pending+synced,key=lambda x:x.get("date_theme",""))

        STATUS_COLORS={"present":OK,"absent":DNG,"mission":PURP,"maladie":WARN,"conge":INFO,"retard":"#F97316"}
        STATUS_LABELS={"present":"P","absent":"A","mission":"Ms","maladie":"Ml","conge":"Cg","retard":"R"}
        STATUS_FULL={"present":"Présent","absent":"Absent","mission":"Mission","maladie":"Maladie","conge":"Congé","retard":"Retard"}

        # widgets
        month_lbl = ft.Text("",size=18,weight=ft.FontWeight.BOLD,color=TXT,text_align=ft.TextAlign.CENTER)
        stats_row = ft.Row(spacing=6,expand=True)
        ts_list_col= ft.Column(spacing=8)
        tab_bar   = ft.Row(spacing=4)
        tab_idx   = [0]

        TABS=[("Aperçu",ft.Icons.TABLE_VIEW_ROUNDED,BLUE),
              ("Télécharger",ft.Icons.DOWNLOAD_ROUNDED,OK),
              ("Pointages",ft.Icons.HOW_TO_REG_ROUNDED,INFO),
              ("Toolbox",ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP)]

        def _rebuild_tabs():
            def _t(lbl,ico,c,idx):
                active=tab_idx[0]==idx
                def click(e,i=idx): tab_idx[0]=i; _rebuild_tabs(); rebuild()
                return ft.Container(expand=True,border_radius=10,
                    bgcolor=c if active else f"#12{c[1:]}",
                    padding=P(6,8,6,8),ink=True,on_click=click,
                    content=ft.Column([
                        ft.Icon(ico,color="#FFFFFF" if active else MUT,size=15),
                        ft.Text(lbl,size=9,color="#FFFFFF" if active else MUT,
                                weight=ft.FontWeight.W_700,text_align=ft.TextAlign.CENTER),
                    ],spacing=2,tight=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER))
            tab_bar.controls=[_t(l,i,c,idx) for idx,(l,i,c) in enumerate(TABS)]
            try: tab_bar.update()
            except Exception: pass
        _rebuild_tabs()

        def _period_selector():
            def _pb(key,lbl):
                active=TS["ts_type"]==key
                def click(e,k=key): TS["ts_type"]=k; rebuild()
                return ft.Container(expand=True,
                    bgcolor=BLUE if active else f"#10{BLUE[1:]}",border_radius=10,
                    padding=P(10,8,10,8),ink=True,on_click=click,
                    border=ft.Border.all(1,BLUE if active else f"#30{BLUE[1:]}"),
                    content=ft.Text(lbl,size=12,color="#FFFFFF" if active else MUT,
                                    weight=ft.FontWeight.W_600,text_align=ft.TextAlign.CENTER))
            return ft.Container(bgcolor=f"#08{BLUE[1:]}",border_radius=10,padding=P(4,4,4,4),
                content=ft.Row([_pb("1_25","01 – 25"),ft.Container(width=4),_pb("21_20","21 – 20")],spacing=0))

        def _build_apercu():
            recs=get_att_period(); _,_,days=get_period_range()
            emp_map={}
            for r in recs:
                eid=r.get("employee_id") or r.get("employee_name") or "?"
                name=(r.get("employee_name") or
                      (r.get("nom","")+" "+r.get("prenom","")).strip() or str(eid))
                if eid not in emp_map: emp_map[eid]={"name":name,"days":{}}
                emp_map[eid]["days"][str(r.get("date_presence",""))]=str(r.get("status",""))
            if not emp_map:
                return [ft.Container(bgcolor=CARD,border_radius=14,padding=P(32,24,32,24),
                    content=ft.Column([
                        ft.Icon(ft.Icons.TABLE_VIEW_OUTLINED,color=BRD,size=52),
                        ft.Text("Aucune donnée pour cette période",size=14,color=MUT,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("Synchronisez d'abord via l'onglet Pointages",
                                size=11,color=MUT,text_align=ft.TextAlign.CENTER),
                    ],spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER))]
            n_p=sum(sum(1 for s in e["days"].values() if s=="present") for e in emp_map.values())
            n_a=sum(sum(1 for s in e["days"].values() if s=="absent") for e in emp_map.values())
            n_tot=sum(len(e["days"]) for e in emp_map.values())

            def _emp_card(name,emp_days):
                np2=sum(1 for s in emp_days.values() if s=="present")
                na=sum(1 for s in emp_days.values() if s=="absent")
                nm=len(emp_days)-np2-na
                nX=len(days)-len(emp_days)
                rows_of_5=[]; row=[]
                for i,d in enumerate(days):
                    ds=d.isoformat(); status=emp_days.get(ds)
                    c=STATUS_COLORS.get(status) if status else None
                    lbl=STATUS_LABELS.get(status,"") if status else ""
                    is_we=d.weekday()>=5
                    bg=c if c else (f"#0C{DNG[1:]}" if is_we else f"#0A{BRD[1:]}")
                    brd=c if c else (f"#18{DNG[1:]}" if is_we else BRD)
                    cell=ft.Container(width=38,height=34,border_radius=6,
                        bgcolor=bg,border=ft.Border.all(1,brd),alignment=AL(0,0),
                        content=ft.Column([
                            ft.Text(str(d.day),size=7,color="#60FFFFFF" if c else MUT,
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(lbl,size=9,color="#FFFFFF" if c else MUT,
                                    weight=ft.FontWeight.W_700 if c else ft.FontWeight.W_400,
                                    text_align=ft.TextAlign.CENTER),
                        ],spacing=0,tight=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER))
                    row.append(cell)
                    if len(row)==5 or i==len(days)-1:
                        while len(row)<5: row.append(ft.Container(width=38,height=34))
                        rows_of_5.append(ft.Row(row[:],spacing=4)); row=[]
                return ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                    border=ft.Border.all(1,BRD),padding=P(14,12,14,12),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=36,height=36,border_radius=18,
                                bgcolor=f"#18{BLUE[1:]}",alignment=AL(0,0),
                                content=ft.Text((name[0] if name else "?").upper(),
                                                size=15,color=BLUE,weight=ft.FontWeight.W_700)),
                            ft.Column([
                                ft.Text(name,size=13,weight=ft.FontWeight.W_600,color=TXT,
                                        max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Row([
                                    ft.Container(bgcolor=f"#18{OK[1:]}",border_radius=6,padding=P(6,2,6,2),
                                        content=ft.Text(f"P:{np2}",size=10,color=OK,weight=ft.FontWeight.W_700)),
                                    ft.Container(bgcolor=f"#18{DNG[1:]}",border_radius=6,padding=P(6,2,6,2),
                                        content=ft.Text(f"A:{na}",size=10,color=DNG,weight=ft.FontWeight.W_700)),
                                    ft.Container(bgcolor=f"#18{WARN[1:]}",border_radius=6,padding=P(6,2,6,2),
                                        content=ft.Text(f"Aut:{nm}",size=10,color=WARN,weight=ft.FontWeight.W_700)),
                                    ft.Container(bgcolor=f"#14{MUT[1:]}",border_radius=6,padding=P(6,2,6,2),
                                        content=ft.Text(f"—:{nX}",size=10,color=MUT,weight=ft.FontWeight.W_600)),
                                ],spacing=4),
                            ],spacing=3,expand=True),
                        ],spacing=10),
                        ft.Container(height=6),
                        *rows_of_5,
                    ],spacing=4,tight=True))

            legend=ft.Row([
                *[ft.Container(bgcolor=f"#18{c[1:]}",border_radius=6,padding=P(6,2,6,2),
                    content=ft.Row([ft.Container(width=8,height=8,border_radius=4,bgcolor=c),
                        ft.Text(l,size=9,color=c,weight=ft.FontWeight.W_600)],spacing=3,tight=True))
                  for l,c in [("Présent",OK),("Absent",DNG),("Mission",PURP),("Maladie",WARN),("Congé",INFO)]],
                ft.Container(bgcolor=f"#14{MUT[1:]}",border_radius=6,padding=P(6,2,6,2),
                    content=ft.Row([ft.Container(width=8,height=8,border_radius=4,bgcolor=MUT),
                        ft.Text("—",size=9,color=MUT,weight=ft.FontWeight.W_600)],spacing=3,tight=True)),
            ],spacing=4,wrap=True)

            emp_cards=[_emp_card(data["name"],data["days"])
                       for _,data in sorted(emp_map.items(),key=lambda x:x[1]["name"])]

            return [
                ft.Row([_chip(str(len(emp_map)),"Employés",BLUE),_chip(str(n_p),"Présences",OK),
                        _chip(str(n_a),"Absences",DNG),_chip(str(n_tot-n_p-n_a),"Autres",WARN)],spacing=6),
                ft.Container(bgcolor=CARD,border_radius=10,padding=P(10,8,10,8),
                    border=ft.Border.all(1,BRD),content=legend),
                ft.Container(bgcolor=f"#08{BLUE[1:]}",border_radius=8,padding=P(10,6,10,6),
                    content=ft.Row([
                        ft.Icon(ft.Icons.GRID_ON_ROUNDED,color=BLUE,size=14),
                        ft.Text("Légende: Sem=week-end grisé · Chiffre=jour · Lettre=statut",
                                size=10,color=MUT),
                    ],spacing=6,tight=True)),
                *emp_cards,
                ft.Container(height=6),
                ft.Row([
                    ft.Container(expand=True,bgcolor=CARD,border_radius=10,
                        border=ft.Border.all(1,f"#25{DNG[1:]}"),ink=True,
                        on_click=lambda e:_export_period_pdf(),padding=P(12,10,12,10),
                        content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,color=DNG,size=18),
                            ft.Column([ft.Text("Exporter PDF",size=12,color=DNG,weight=ft.FontWeight.W_700),
                                       ft.Text("Hors-ligne",size=9,color=MUT)],spacing=1,expand=True)],spacing=8,tight=True)),
                    ft.Container(expand=True,bgcolor=CARD,border_radius=10,
                        border=ft.Border.all(1,f"#25{OK[1:]}"),ink=True,
                        on_click=lambda e:_export_period_csv(),padding=P(12,10,12,10),
                        content=ft.Row([ft.Icon(ft.Icons.TABLE_CHART_OUTLINED,color=OK,size=18),
                            ft.Column([ft.Text("Exporter CSV",size=12,color=OK,weight=ft.FontWeight.W_700),
                                       ft.Text("Compatible Excel",size=9,color=MUT)],spacing=1,expand=True)],spacing=8,tight=True)),
                ],spacing=8),
            ]

        def _sec2(txt,ico,color=BLUE):
            return ft.Row([ft.Icon(ico,color=color,size=14),
                           ft.Text(txt,size=11,weight=ft.FontWeight.W_700,color=color,expand=True)],spacing=6)

        def _chip(val,lbl,color):
            return ft.Container(expand=True,bgcolor=f"#10{color[1:]}",border_radius=12,
                padding=P(10,8,10,8),border=ft.Border.all(1,f"#25{color[1:]}"),
                content=ft.Column([
                    ft.Text(val,size=20,weight=ft.FontWeight.BOLD,color=color,text_align=ft.TextAlign.CENTER),
                    ft.Text(lbl,size=9,color=MUT,text_align=ft.TextAlign.CENTER),
                ],spacing=2,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))

        def _fmt_badge(fmt):
            c=OK if fmt=="xlsx" else DNG
            ico=ft.Icons.TABLE_VIEW_ROUNDED if fmt=="xlsx" else ft.Icons.PICTURE_AS_PDF_ROUNDED
            return ft.Container(bgcolor=f"{c}15",border_radius=8,padding=P(8,4,8,4),
                border=ft.Border.all(1,f"{c}30"),
                content=ft.Row([ft.Icon(ico,color=c,size=14),
                    ft.Text(fmt.upper(),size=11,color=c,weight=ft.FontWeight.W_700)],spacing=4,tight=True))

        def _ts_card(rec):
            m=rec["month"]; fmt=rec["format"]
            fpath=Path(rec["filepath"]); exists=fpath.exists()
            sz=rec["filesize"]; sz_lbl=f"{sz//1024} Ko" if sz>0 else "—"
            mo_idx=int(m.split("-")[1])-1; yr=m.split("-")[0]
            mlbl=f"{MONTHS_FR[mo_idx]} {yr}"
            def _open(e): open_file(fpath)
            def _del(e,rid=rec["id"]):
                delete_saved_timesheet(rid)
                try:
                    if fpath.exists(): fpath.unlink()
                except Exception: pass
                rebuild()
            return ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(4,"08"),
                border=ft.Border.all(1,BRD if exists else f"#22{DNG[1:]}"),padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Row([_fmt_badge(fmt),
                            ft.Container(expand=True,content=ft.Text(mlbl,size=13,weight=ft.FontWeight.BOLD,color=TXT)),
                            ft.Container(bgcolor=f"#12{OK[1:]}" if exists else f"#12{DNG[1:]}",border_radius=8,padding=P(6,3,6,3),
                                content=ft.Text("Disponible" if exists else "Manquant",
                                    size=10,color=OK if exists else DNG,weight=ft.FontWeight.W_600))],spacing=8),
                    ft.Container(height=4),
                    ft.Row([ft.Icon(ft.Icons.SCHEDULE_OUTLINED,color=MUT,size=12),
                            ft.Text(str(rec.get("downloaded_at",""))[:16],size=10,color=MUT,expand=True),
                            ft.Text(sz_lbl,size=10,color=MUT)],spacing=6),
                    ft.Container(height=6),
                    ft.Row([
                        ft.Container(expand=True,bgcolor=f"#12{BLUE[1:]}",border_radius=10,
                            border=ft.Border.all(1,f"#25{BLUE[1:]}"),padding=P(10,8,10,8),
                            ink=True,on_click=_open if exists else None,
                            content=ft.Row([ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED,color=BLUE if exists else MUT,size=16),
                                ft.Text("Ouvrir",size=12,color=BLUE if exists else MUT,weight=ft.FontWeight.W_600)],
                                spacing=6,tight=True)),
                        ft.Container(width=8),
                        ft.Container(bgcolor=f"#10{DNG[1:]}",border_radius=10,
                            border=ft.Border.all(1,f"#20{DNG[1:]}"),padding=P(10,8,10,8),ink=True,on_click=_del,
                            content=ft.Icon(ft.Icons.DELETE_OUTLINE_ROUNDED,color=DNG,size=18)),
                    ],spacing=0),
                ],spacing=0,tight=True))

        def _att_row(r):
            sc={"present":OK,"absent":DNG,"mission":PURP,"maladie":WARN,"conge":INFO}.get(r.get("status",""),MUT)
            h_txt=f"{r['heure_entree']} → {r['heure_sortie']}" if r.get("heure_entree") and r.get("heure_sortie") else r.get("heure_entree","")
            return ft.Container(bgcolor=CARD,border_radius=12,border=ft.Border.all(1,BRD),padding=P(12,10,12,10),
                content=ft.Row([
                    ft.Container(width=4,height=40,bgcolor=sc,border_radius=4),
                    ft.Container(width=8),
                    ft.Column([
                        ft.Text(r.get("employee_name","—"),size=12,weight=ft.FontWeight.W_600,color=TXT,
                                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(r.get("date_presence",""))+(f" — {h_txt}" if h_txt else ""),size=10,color=MUT),
                    ],spacing=2,expand=True),
                    ft.Container(bgcolor=f"{sc}15",border_radius=8,padding=P(8,4,8,4),
                        content=ft.Text((r.get("status","—") or "—").title(),size=10,color=sc,weight=ft.FontWeight.W_700)),
                ],spacing=0))

        def _tb_row(r):
            return ft.Container(bgcolor=CARD,border_radius=12,border=ft.Border.all(1,f"#22{PURP[1:]}"),padding=P(12,10,12,10),
                content=ft.Row([
                    ft.Container(bgcolor=f"#15{PURP[1:]}",border_radius=8,width=36,height=36,alignment=AL(0,0),
                        content=ft.Icon(ft.Icons.RECORD_VOICE_OVER_ROUNDED,color=PURP,size=18)),
                    ft.Column([
                        ft.Text(str(r.get("theme","—") or "—"),size=12,weight=ft.FontWeight.W_600,color=TXT,
                                max_lines=2,overflow=ft.TextOverflow.ELLIPSIS,expand=True),
                        ft.Text(f"{r.get('date_theme','')} · {r.get('facilitator','') or '—'}",size=10,color=MUT),
                    ],spacing=2,expand=True),
                    ft.Container(bgcolor=f"#15{OK[1:]}",border_radius=8,padding=P(8,4,8,4),
                        content=ft.Text(f"{r.get('attendees_count',0)} pers.",size=10,color=OK,weight=ft.FontWeight.W_700)),
                ],spacing=8))

        def _export_period_pdf(e=None):
            try:
                import io
                from reportlab.lib import colors as rlc
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.lib.units import mm
                from reportlab.lib.enums import TA_CENTER, TA_LEFT
                from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

                recs = get_att_period()
                _, __, days_list = get_period_range()
                if not recs:
                    notify("Aucun pointage pour cette periode.", WARN); return

                def _sf(s):
                    return (str(s or "").replace("—","--").replace("–","-").replace("→","->")
                            .encode("latin-1","replace").decode("latin-1"))

                STATUS_MAP = {
                    "present": ("P",  rlc.HexColor("#DCFCE7")),
                    "absent":  ("A",  rlc.HexColor("#FEE2E2")),
                    "mission": ("Ms", rlc.HexColor("#E0E7FF")),
                    "maladie": ("Ml", rlc.HexColor("#FEE2E2")),
                    "conge":   ("Cg", rlc.HexColor("#EDE9FE")),
                    "retard":  ("R",  rlc.HexColor("#FEF3C7")),
                }

                emp_map: dict = {}
                for r in recs:
                    name = _sf(r.get("employee_name") or "---")
                    dp   = str(r.get("date_presence") or "")
                    st   = str(r.get("status") or "").lower()
                    if name not in emp_map:
                        emp_map[name] = {}
                    emp_map[name][dp] = STATUS_MAP.get(st, ("", None))

                TIT = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=16, leading=19,
                                     textColor=rlc.white, alignment=TA_CENTER)
                SUB = ParagraphStyle("S", fontName="Helvetica", fontSize=8, leading=10,
                                     textColor=rlc.HexColor("#475569"), alignment=TA_CENTER)
                SML = ParagraphStyle("M", fontName="Helvetica", fontSize=7, leading=8.5, alignment=TA_LEFT)
                HDR = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=7, leading=8.5,
                                     textColor=rlc.white, alignment=TA_CENTER)

                buf = io.BytesIO()
                doc = SimpleDocTemplate(str(buf), pagesize=landscape(A4),
                    leftMargin=9*mm, rightMargin=9*mm, topMargin=9*mm, bottomMargin=10*mm)
                story: list = []
                p_lbl      = _sf(period_label())
                gen_at     = datetime.now().strftime("%Y-%m-%d %H:%M")

                # ── Header ─────────────────────────────────────────────────────
                hdr_tbl = Table([
                    [Paragraph("OREZONE", TIT), Paragraph("OREZONE MONTHLY TIMESHEET", TIT)],
                    ["", Paragraph(p_lbl, SUB)],
                    ["", Paragraph(f"Generated: {gen_at} | Orezone QHSE | Site SYAMA", SUB)],
                ], colWidths=[38*mm, 239*mm])
                hdr_tbl.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,0),  rlc.HexColor("#1E3A8A")),
                    ("BACKGROUND",    (0,1), (0,2),   rlc.HexColor("#1E3A8A")),
                    ("SPAN",          (0,0), (0,2)),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                    ("BACKGROUND",    (1,1), (1,2),   rlc.HexColor("#EFF6FF")),
                    ("BOX",           (0,0), (-1,-1), 0.8,  rlc.HexColor("#1E3A8A")),
                    ("INNERGRID",     (0,0), (-1,-1), 0.25, rlc.HexColor("#BFDBFE")),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
                    ("TOPPADDING",    (0,0), (-1,-1), 7),
                ]))
                story.extend([hdr_tbl, Spacer(1, 4*mm)])

                # ── KPI metrics ────────────────────────────────────────────────
                n_p = sum(1 for r in recs if r.get("status") == "present")
                n_a = sum(1 for r in recs if r.get("status") == "absent")
                n_o = len(recs) - n_p - n_a
                met = Table([[
                    Paragraph(f"<b>Employes</b><br/>{len(emp_map)}", SUB),
                    Paragraph(f"<b>Presences</b><br/>{n_p}", SUB),
                    Paragraph(f"<b>Absences</b><br/>{n_a}", SUB),
                    Paragraph(f"<b>Autres</b><br/>{n_o}", SUB),
                    Paragraph(f"<b>Total releves</b><br/>{len(recs)}", SUB),
                ]], colWidths=[55.4*mm]*5)
                met.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (0,0),   rlc.HexColor("#DBEAFE")),
                    ("BACKGROUND",    (1,0), (1,0),   rlc.HexColor("#DCFCE7")),
                    ("BACKGROUND",    (2,0), (2,0),   rlc.HexColor("#FEE2E2")),
                    ("BACKGROUND",    (3,0), (3,0),   rlc.HexColor("#FEF3C7")),
                    ("BACKGROUND",    (4,0), (4,0),   rlc.HexColor("#EFF6FF")),
                    ("BOX",           (0,0), (-1,-1), 0.6,  rlc.HexColor("#CBD5E1")),
                    ("INNERGRID",     (0,0), (-1,-1), 0.3,  rlc.HexColor("#CBD5E1")),
                    ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("TOPPADDING",    (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ]))
                story.extend([met, Spacer(1, 4*mm)])

                # ── Employee × day matrix ──────────────────────────────────────
                n_days = len(days_list)
                day_w  = max(5.0, (279 - 40 - 4*9) / max(n_days, 1))
                col_widths = [40*mm] + [day_w*mm]*n_days + [9*mm]*4
                day_labels = [str(d.day) for d in days_list]
                td = [[Paragraph(lbl, HDR) for lbl in ["Employe"] + day_labels + ["P","A","Au","-"]]]
                tbl_styles = [
                    ("BACKGROUND",    (0,0), (-1,0),  rlc.HexColor("#1E3A8A")),
                    ("TEXTCOLOR",     (0,0), (-1,0),  rlc.white),
                    ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0), (-1,-1), 6.5),
                    ("GRID",          (0,0), (-1,-1), 0.2,  rlc.HexColor("#CBD5E1")),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                    ("ALIGN",         (0,0), (0,-1),  "LEFT"),
                    ("ROWBACKGROUNDS",(0,1), (-1,-1), [rlc.white, rlc.HexColor("#F8FAFC")]),
                    ("TOPPADDING",    (0,0), (-1,-1), 2),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 2),
                ]
                for ri, (emp_name, day_data) in enumerate(sorted(emp_map.items()), start=1):
                    cnt_p = cnt_a = cnt_au = cnt_x = 0
                    row_cells = []
                    for ci, d in enumerate(days_list):
                        di = d.isoformat()
                        if di in day_data:
                            lbl, bg = day_data[di]
                            row_cells.append(lbl or "")
                            if   lbl == "P":                      cnt_p  += 1
                            elif lbl == "A":                      cnt_a  += 1
                            elif lbl in ("Ms","Ml","Cg","R"):    cnt_au += 1
                            if bg:
                                tbl_styles.append(("BACKGROUND", (1+ci, ri), (1+ci, ri), bg))
                        else:
                            row_cells.append(""); cnt_x += 1
                    td.append([Paragraph(emp_name[:32], SML)] + row_cells +
                               [str(cnt_p), str(cnt_a), str(cnt_au), str(cnt_x)])

                att_tbl = Table(td, colWidths=col_widths, repeatRows=1)
                att_tbl.setStyle(TableStyle(tbl_styles))
                story.extend([att_tbl, Spacer(1, 5*mm)])

                # ── Signature block ────────────────────────────────────────────
                sig = Table([
                    ["Prepared by", "Checked by", "Approved by", "QHSE comments"],
                    ["Name / Date / Signature", "Name / Date / Signature", "Name / Date / Signature", ""],
                ], colWidths=[55*mm, 55*mm, 55*mm, 112*mm], rowHeights=[8*mm, 17*mm])
                sig.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0),  rlc.HexColor("#EFF6FF")),
                    ("FONTNAME",   (0,0), (-1,0),  "Helvetica-Bold"),
                    ("FONTSIZE",   (0,0), (-1,-1), 7.5),
                    ("ALIGN",      (0,0), (-1,-1), "CENTER"),
                    ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
                    ("GRID",       (0,0), (-1,-1), 0.4, rlc.HexColor("#CBD5E1")),
                ]))
                story.append(sig)

                def _footer(canvas, doc_obj):
                    canvas.saveState()
                    canvas.setFont("Helvetica", 7)
                    canvas.setFillColor(rlc.HexColor("#64748B"))
                    canvas.drawString(9*mm, 6*mm, "OREZONE QHSE - Monthly Timesheet")
                    canvas.drawRightString(288*mm, 6*mm, f"Page {doc_obj.page}")
                    canvas.restoreState()

                doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
                out = get_exports_dir() / f"timesheet_{month_prefix()}_{TS['ts_type']}.pdf"
                out.write_bytes(buf.getvalue())
                open_file(out)
                notify(f"PDF exporte : {out.name}", OK)
            except Exception as exc:
                notify(f"Erreur PDF : {exc}", DNG)

        def _export_period_csv(e=None):
            try:
                recs=get_att_period()
                if not recs: notify("Aucun pointage pour cette période.",WARN); return
                out=get_exports_dir()/f"timesheet_{month_prefix()}_{TS['ts_type']}.csv"
                with open(out,"w",newline="",encoding="utf-8-sig") as f:
                    w=_csv.writer(f,delimiter=";")
                    w.writerow(["Employé","Date","Statut","Entrée","Sortie"])
                    for r in recs:
                        w.writerow([r.get("employee_name",""),r.get("date_presence",""),
                                    r.get("status",""),r.get("heure_entree","") or "",r.get("heure_sortie","") or ""])
                open_file(out); notify(f"CSV exporté ({len(recs)} lignes)",OK)
            except Exception as exc: notify(f"Erreur CSV : {exc}",DNG)

        def _build_url(month, fmt, ts_type=None, emp_id=None):
            addr=get_setting("server_url") or ""
            t=ts_type or TS["ts_type"]
            u=f"{addr.rstrip('/')}/api/mobile/timesheet/export?month={month}&format={fmt}&type={t}"
            if emp_id: u+=f"&employee_id={emp_id}"
            return u

        def _set_dl_status(msg, color):
            TS["dl_status"]=msg; TS["dl_color"]=color
            try: ts_list_col.update()
            except Exception: pass

        def _download_ts(fmt, ts_type=None, emp_id=None, e=None):
            addr=get_setting("server_url") or ""; tk=get_setting("token") or ""
            if not addr:
                _set_dl_status("Serveur non configuré. Allez dans Paramètres pour configurer l'URL.",DNG)
                notify("Serveur non configuré.",DNG); rebuild(); return
            pfx=month_prefix(); t=ts_type or TS["ts_type"]
            period_lbl="01-25" if t=="1_25" else "21-20"
            emp_lbl=f" - Employe #{emp_id}" if emp_id else ""
            _set_dl_status(f"Connexion au serveur {addr.split('//')[-1].split('/')[0]}...",MUT)
            rebuild()
            if not ping_server(addr,tk,timeout=4):
                _set_dl_status(
                    "Serveur inaccessible — vérifiez que l'application principale est démarrée "
                    "et que le serveur de synchronisation est actif.",DNG)
                rebuild(); return
            _set_dl_status(f"Téléchargement {fmt.upper()} {period_lbl}{emp_lbl}...",MUT)
            rebuild()
            try:
                data=request_bytes(_build_url(pfx,fmt,t,emp_id),tk,timeout=30)
                fname=f"timesheet_{pfx}_{t}"+(f"_emp{emp_id}" if emp_id else "")+f".{fmt}"
                fpath=get_ts_dir()/fname
                fpath.write_bytes(data)
                save_timesheet_record(f"{pfx}_{t}"+(f"_e{emp_id}" if emp_id else ""),fmt,str(fpath),len(data))
                _set_dl_status(f"Téléchargé ({len(data)//1024} Ko) : {fname}",OK)
                rebuild(); notify(f"Téléchargé : {fname}",OK)
            except Exception as exc:
                _set_dl_status(str(exc),DNG)
                rebuild(); notify("Erreur téléchargement",DNG)

        def _dl_all_months(e=None):
            addr=get_setting("server_url") or ""; tk=get_setting("token") or ""
            if not addr:
                _set_dl_status("Serveur non configuré. Allez dans Paramètres.",DNG)
                notify("Serveur non configuré.",DNG); rebuild(); return
            _set_dl_status("Vérification connexion...",MUT); rebuild()
            if not ping_server(addr,tk,timeout=4):
                _set_dl_status("Serveur inaccessible — vérifiez que l'application principale est démarrée.",DNG)
                rebuild(); return
            _set_dl_status("Téléchargement — 6 mois × 2 périodes × 2 formats...",MUT); rebuild()
            from datetime import timedelta
            months=[]; d2=date.today().replace(day=1)
            for _ in range(6):
                months.append(d2.strftime("%Y-%m"))
                d2=(d2-timedelta(days=1)).replace(day=1)
            ts_dir=get_ts_dir(); ok=0; fail=0
            for m in months:
                for t in ("1_25","21_20"):
                    for fmt in ("xlsx","pdf"):
                        try:
                            data=request_bytes(_build_url(m,fmt,t),tk,timeout=20)
                            fname=f"timesheet_{m}_{t}.{fmt}"
                            fpath=ts_dir/fname; fpath.write_bytes(data)
                            save_timesheet_record(f"{m}_{t}",fmt,str(fpath),len(data)); ok+=1
                        except Exception: fail+=1
            msg=f"Terminé : {ok} fichiers OK, {fail} erreur(s)"
            _set_dl_status(msg,OK if fail==0 else WARN)
            rebuild(); notify(msg,OK if fail==0 else WARN)

        def _dl_individual(e=None):
            emps=list_employees()
            if not emps: notify("Aucun employé en cache. Synchronisez d'abord.",WARN); return
            addr=get_setting("server_url") or ""; tk=get_setting("token") or ""
            if not addr:
                _set_dl_status("Serveur non configuré. Allez dans Paramètres.",DNG)
                notify("Serveur non configuré.",DNG); rebuild(); return
            pfx=month_prefix(); t=TS["ts_type"]; ok=0; fail=0
            _set_dl_status("Vérification connexion...",MUT); rebuild()
            if not ping_server(addr,tk,timeout=4):
                _set_dl_status("Serveur inaccessible — vérifiez que l'application principale est démarrée.",DNG)
                rebuild(); return
            _set_dl_status(f"Téléchargement feuilles ({len(emps)} employés)...",MUT); rebuild()
            ts_dir=get_ts_dir()
            for emp in emps:
                emp=dict(emp)
                eid=emp.get("id_employe"); ename=(emp.get("nom","")+" "+emp.get("prenom","")).strip() or f"emp{eid}"
                try:
                    data=request_bytes(_build_url(pfx,"pdf",t,eid),tk,timeout=20)
                    safe=ename.replace(" ","_").replace("/","_")[:40]
                    fpath=ts_dir/f"ts_{pfx}_{t}_{safe}.pdf"
                    fpath.write_bytes(data)
                    save_timesheet_record(f"{pfx}_{t}_e{eid}","pdf",str(fpath),len(data)); ok+=1
                except Exception: fail+=1
            msg=f"Feuilles : {ok} OK, {fail} erreur(s)"
            _set_dl_status(msg,OK if fail==0 else WARN)
            rebuild(); notify(msg,OK if fail==0 else WARN)

        def _sync_month(e=None):
            addr=get_setting("server_url") or ""; tk=get_setting("token") or ""
            if not addr: notify("Serveur non configuré.",DNG); return
            pfx=month_prefix()
            try:
                md=request_json(f"{addr.rstrip('/')}/api/mobile/data?month={pfx}",tk,timeout=30)
                save_synced_month_data(pfx,md.get("attendance") or [],md.get("toolbox") or [])
                rebuild()
                notify(f"Synchro {MONTHS_FR[TS['month']-1]} : {len(md.get('attendance') or [])} présences, {len(md.get('toolbox') or [])} toolbox",OK)
            except Exception as exc: notify(f"Erreur sync : {exc}",DNG)

        def _export_tb_pdf(e=None):
            try:
                from reportlab.lib import colors as rlc
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                recs=get_tb(); pfx=month_prefix()
                if not recs: notify("Aucune session Toolbox ce mois.",WARN); return
                out=get_exports_dir()/f"toolbox_{pfx}.pdf"
                doc=SimpleDocTemplate(str(out),pagesize=A4,leftMargin=20,rightMargin=20,topMargin=20,bottomMargin=20)
                sty=getSampleStyleSheet()
                data=[["Date","Thème","Animateur","Participants","Commentaires"]]
                for r in recs:
                    data.append([str(r.get("date_theme","")),str(r.get("theme","") or "—"),
                                 str(r.get("facilitator","") or "—"),str(r.get("attendees_count",0)),str(r.get("comments","") or "")])
                tbl=Table(data,colWidths=[65,175,105,70,85])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,0),rlc.HexColor("#7C3AED")),("TEXTCOLOR",(0,0),(-1,0),rlc.white),
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[rlc.white,rlc.HexColor("#F5F3FF")]),
                    ("GRID",(0,0),(-1,-1),0.3,rlc.HexColor("#DDD6FE")),
                    ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ]))
                doc.build([Paragraph(f"<b>Toolbox Talk — {MONTHS_FR[TS['month']-1]} {TS['year']} | OREZONE QHSE</b>",sty["Title"]),Spacer(1,12),tbl])
                open_file(out); notify(f"PDF Toolbox exporté : {out.name}",OK)
            except Exception as exc: notify(f"Erreur PDF Toolbox : {exc}",DNG)

        def prev_m(e=None):
            m=TS["month"]-1
            if m<1: m=12; TS["year"]-=1
            TS["month"]=m; rebuild()
        def next_m(e=None):
            m=TS["month"]+1
            if m>12: m=1; TS["year"]+=1
            TS["month"]=m; rebuild()

        def rebuild():
            mlbl=f"{MONTHS_FR[TS['month']-1]} {TS['year']}"
            month_lbl.value=mlbl
            recs_m=get_att(); recs_p=get_att_period()
            np2=sum(1 for r in recs_p if r.get("status")=="present")
            na=sum(1 for r in recs_p if r.get("status")=="absent")
            stats_row.controls=[_chip(str(len(recs_p)),"Enreg.",BLUE),_chip(str(np2),"Présents",OK),
                                 _chip(str(na),"Absents",DNG),_chip(str(len(recs_p)-np2-na),"Autres",WARN)]
            t_lbl=period_label()
            if tab_idx[0]==0:   # ── Aperçu
                ts_list_col.controls=[
                    _period_selector(),
                    ft.Container(bgcolor=f"#08{BLUE[1:]}",border_radius=8,padding=P(10,6,10,6),
                        content=ft.Row([ft.Icon(ft.Icons.DATE_RANGE_ROUNDED,color=BLUE,size=14),
                            ft.Text(f"Période : {t_lbl}",size=11,color=BLUE,weight=ft.FontWeight.W_600)],spacing=6,tight=True)),
                    *_build_apercu(),
                    ft.Container(height=80),
                ]
            elif tab_idx[0]==1: # ── Télécharger
                all_saved=list_saved_timesheets()
                ts_list_col.controls=[
                    _period_selector(),
                    ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(5,"09"),
                        border=ft.Border.all(1,f"#20{BLUE[1:]}"),padding=P(14,14,14,14),
                        content=ft.Column([
                            _sec2(f"Télécharger depuis le serveur — {mlbl}",ft.Icons.DOWNLOAD_ROUNDED),
                            ft.Container(bgcolor=f"#06{BLUE[1:]}",border_radius=8,padding=P(8,6,8,6),
                                content=ft.Text(f"Période sélectionnée : {t_lbl}",size=10,color=BLUE)),
                            ft.Container(height=6),
                            ft.Row([
                                ft.Container(expand=True,bgcolor=f"#12{OK[1:]}",border_radius=10,
                                    border=ft.Border.all(1,f"#30{OK[1:]}"),padding=P(12,10,12,10),ink=True,
                                    on_click=lambda e:_download_ts("xlsx"),
                                    content=ft.Column([
                                        ft.Row([ft.Icon(ft.Icons.TABLE_VIEW_ROUNDED,color=OK,size=20),
                                               ft.Text("Excel",size=12,weight=ft.FontWeight.W_700,color=OK)],spacing=6,tight=True),
                                        ft.Text("Tableau officiel",size=10,color=MUT)],spacing=4,tight=True)),
                                ft.Container(width=10),
                                ft.Container(expand=True,bgcolor=f"#12{DNG[1:]}",border_radius=10,
                                    border=ft.Border.all(1,f"#30{DNG[1:]}"),padding=P(12,10,12,10),ink=True,
                                    on_click=lambda e:_download_ts("pdf"),
                                    content=ft.Column([
                                        ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,color=DNG,size=20),
                                               ft.Text("PDF",size=12,weight=ft.FontWeight.W_700,color=DNG)],spacing=6,tight=True),
                                        ft.Text("Version imprimable",size=10,color=MUT)],spacing=4,tight=True)),
                            ],spacing=0),
                            ft.Container(height=8),
                            ft.Container(bgcolor=f"#10{PURP[1:]}",border_radius=10,
                                border=ft.Border.all(1,f"#30{PURP[1:]}"),padding=P(12,10,12,10),ink=True,
                                on_click=_dl_individual,
                                content=ft.Row([ft.Icon(ft.Icons.PERSON_OUTLINED,color=PURP,size=20),
                                    ft.Column([ft.Text("Feuilles individuelles — PDF",size=12,weight=ft.FontWeight.W_700,color=PURP),
                                               ft.Text("Une feuille PDF par employé",size=10,color=MUT)],
                                        spacing=2,expand=True)],spacing=10)),
                            ft.Container(height=6),
                            ft.Container(bgcolor=f"#10{INFO[1:]}",border_radius=10,
                                border=ft.Border.all(1,f"#30{INFO[1:]}"),padding=P(12,10,12,10),ink=True,
                                on_click=_dl_all_months,
                                content=ft.Row([ft.Icon(ft.Icons.CLOUD_SYNC_ROUNDED,color=INFO,size=20),
                                    ft.Column([ft.Text("Tout télécharger — 6 mois × 2 périodes",size=12,weight=ft.FontWeight.W_700,color=INFO),
                                               ft.Text("XLSX + PDF · Hors-ligne complet",size=10,color=MUT)],
                                        spacing=2,expand=True)],spacing=10)),
                        ]+([ft.Container(
                            bgcolor=f"#10{(TS['dl_color'] or MUT)[1:]}",border_radius=8,padding=P(10,8,10,8),
                            content=ft.Row([
                                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED,color=TS['dl_color'] or MUT,size=14),
                                ft.Text(TS['dl_status'],size=11,color=TS['dl_color'] or MUT,expand=True,
                                    no_wrap=False,max_lines=3)],spacing=8,tight=True))
                        ] if TS.get("dl_status") else [])+[
                        ],spacing=6,tight=True)),
                    _sec2(f"Fichiers enregistrés ({len(all_saved)})",ft.Icons.FOLDER_OPEN_ROUNDED),
                ]+([_ts_card(r) for r in all_saved] or [
                    ft.Container(bgcolor=CARD,border_radius=14,padding=P(28,24,28,24),
                        content=ft.Column([ft.Icon(ft.Icons.INBOX_OUTLINED,color=BRD,size=48),
                            ft.Text("Aucun timesheet téléchargé",size=14,color=MUT,text_align=ft.TextAlign.CENTER),
                            ft.Text("Sélectionnez la période ci-dessus et téléchargez",size=11,color=MUT,text_align=ft.TextAlign.CENTER)],
                            spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER))])+[ft.Container(height=80)]
            elif tab_idx[0]==2: # ── Pointages
                ts_list_col.controls=[
                    ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(5,"09"),
                        border=ft.Border.all(1,f"#20{INFO[1:]}"),padding=P(14,12,14,12),ink=True,on_click=_sync_month,
                        content=ft.Row([
                            ft.Container(bgcolor=f"#15{INFO[1:]}",border_radius=10,width=40,height=40,alignment=AL(0,0),
                                content=ft.Icon(ft.Icons.SYNC_ROUNDED,color=INFO,size=20)),
                            ft.Column([ft.Text("Synchroniser ce mois",size=13,weight=ft.FontWeight.W_700,color=TXT),
                                       ft.Text("Récupère les présences depuis le serveur",size=11,color=MUT)],spacing=2,expand=True),
                            ft.Icon(ft.Icons.REFRESH_ROUNDED,color=INFO,size=18)],spacing=10)),
                    stats_row,
                    _sec2(f"Pointages — {mlbl} ({len(recs_m)})",ft.Icons.HOW_TO_REG_ROUNDED,INFO),
                ]+([_att_row(r) for r in recs_m] or [
                    ft.Container(bgcolor=CARD,border_radius=14,padding=P(28,24,28,24),
                        content=ft.Column([ft.Icon(ft.Icons.HOW_TO_REG_OUTLINED,color=BRD,size=48),
                            ft.Text(f"Aucun pointage — {mlbl}",size=14,color=MUT,text_align=ft.TextAlign.CENTER)],
                            spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER))])+[
                    ft.Container(height=6),
                    _sec2("Exports locaux (données hors-ligne)",ft.Icons.DOWNLOAD_ROUNDED),
                    ft.Row([
                        ft.Container(expand=True,bgcolor=CARD,border_radius=12,border=ft.Border.all(1,f"#20{DNG[1:]}"),
                            ink=True,on_click=_export_period_pdf,padding=P(12,10,12,10),
                            content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,color=DNG,size=18),
                                ft.Text("PDF",size=12,weight=ft.FontWeight.W_700,color=DNG)],spacing=6,tight=True)),
                        ft.Container(width=8),
                        ft.Container(expand=True,bgcolor=CARD,border_radius=12,border=ft.Border.all(1,f"#20{OK[1:]}"),
                            ink=True,on_click=_export_period_csv,padding=P(12,10,12,10),
                            content=ft.Row([ft.Icon(ft.Icons.TABLE_CHART_OUTLINED,color=OK,size=18),
                                ft.Text("CSV",size=12,weight=ft.FontWeight.W_700,color=OK)],spacing=6,tight=True)),
                    ],spacing=0),
                    ft.Container(height=80),
                ]
            else:               # ── Toolbox
                tbs=get_tb()
                ts_list_col.controls=[
                    _sec2(f"Toolbox Talk — {mlbl} ({len(tbs)} sessions)",ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP),
                ]+([_tb_row(r) for r in tbs] or [
                    ft.Container(bgcolor=CARD,border_radius=14,padding=P(28,24,28,24),
                        content=ft.Column([ft.Icon(ft.Icons.RECORD_VOICE_OVER_OUTLINED,color=BRD,size=48),
                            ft.Text(f"Aucune session — {mlbl}",size=14,color=MUT,text_align=ft.TextAlign.CENTER)],
                            spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER))])+[
                    ft.Container(height=6),
                    ft.Container(bgcolor=CARD,border_radius=12,border=ft.Border.all(1,f"#20{PURP[1:]}"),ink=True,
                        on_click=_export_tb_pdf,padding=P(12,10,12,10),
                        content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,color=PURP,size=18),
                            ft.Text("Exporter Toolbox en PDF",size=12,weight=ft.FontWeight.W_700,color=PURP)],spacing=6,tight=True)),
                    ft.Container(height=80),
                ]
            try: ts_list_col.update()
            except Exception: pass
            try: stats_row.update()
            except Exception: pass
            try: month_lbl.update()
            except Exception: pass

        rebuild()
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(16,16,16,16),shadow=SH(12,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#18FFFFFF",
                                alignment=AL(0,0),ink=True,on_click=lambda e:go_to("personnel"),
                                content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,color="#FFFFFF",size=17)),
                            ft.Column([
                                ft.Text("Timesheets & Exports",size=17,weight=ft.FontWeight.BOLD,color="#FFFFFF",text_align=ft.TextAlign.CENTER),
                                ft.Text("OREZONE QHSE — Données terrain",size=10,color="#93C5FD",text_align=ft.TextAlign.CENTER),
                            ],spacing=1,expand=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#18FFFFFF",
                                alignment=AL(0,0),ink=True,on_click=lambda e:rebuild(),
                                content=ft.Icon(ft.Icons.REFRESH_ROUNDED,color="#FFFFFF",size=17)),
                        ],spacing=8),
                        ft.Container(height=10),
                        ft.Container(bgcolor="#12FFFFFF",border_radius=14,padding=P(8,10,8,10),
                            content=ft.Row([
                                ft.Container(width=34,height=34,border_radius=17,bgcolor="#15FFFFFF",
                                    alignment=AL(0,0),ink=True,on_click=prev_m,
                                    content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED,color="#FFFFFF",size=22)),
                                ft.Column([month_lbl,
                                    ft.Text("Sélection du mois",size=9,color="#93C5FD",text_align=ft.TextAlign.CENTER)],
                                    spacing=1,expand=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                ft.Container(width=34,height=34,border_radius=17,bgcolor="#15FFFFFF",
                                    alignment=AL(0,0),ink=True,on_click=next_m,
                                    content=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,color="#FFFFFF",size=22)),
                            ],spacing=8)),
                    ],spacing=0,tight=True)),
                ft.Container(bgcolor=CARD,padding=P(8,8,8,8),
                    shadow=ft.BoxShadow(blur_radius=4,offset=ft.Offset(0,2),color="#00000010"),
                    content=tab_bar),
                ft.Container(expand=True,padding=P(12,14,12,0),
                    content=ft.Column([ts_list_col,ft.Container(height=80)],
                        scroll=ft.ScrollMode.AUTO,expand=True,spacing=10)),
            ],spacing=0))


    # ══════════════════════════════════════════════════════════════════════════
    # DRILLING REPORTS
    # ══════════════════════════════════════════════════════════════════════════
    def _s_drilling():
        import json as _json, uuid as _uuid
        from datetime import date as _date

        DRILL_BG   = "#071321"
        DRILL_CARD = "#0F2336"
        DRILL_CARD2= "#10243A"
        DRILL_BRD  = "#1E3A56"
        DRILL_TXT  = "#FFFFFF"
        DRILL_MUT  = "#9DB0C5"
        DRILL_NAV  = "#1E3A8A"

        STATUS_COLOR = {"draft": MUT, "submitted": WARN, "validated": OK}
        STATUS_LABEL = {"draft": "Brouillon", "submitted": "Soumis", "validated": "Validé"}

        ds: dict = {"view": "list"}  # list | new | detail
        list_col  = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        form_col  = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        msg_txt   = ft.Text("", size=12, color=OK)
        content   = ft.Column([list_col], expand=True, scroll=ft.ScrollMode.AUTO)

        equipment = get_drilling_equipment_cached()

        # ── Helpers ──────────────────────────────────────────────────────────
        def _lbl(t): return ft.Text(t, size=11, color=DRILL_MUT)
        def _val(t): return ft.Text(str(t or "—"), size=13, color=DRILL_TXT)

        def _inp(hint="", val="", w=None):
            tf = ft.TextField(
                value=str(val), hint_text=hint,
                border_color=DRILL_BRD, focused_border_color=BLUE,
                color=DRILL_TXT, hint_style=ft.TextStyle(color=DRILL_MUT),
                bgcolor=DRILL_CARD2, border_radius=8, height=44, text_size=13,
                content_padding=P(12, 8, 12, 8),
            )
            if w: tf.width = w
            return tf

        def _dd(opts, val=None):
            return ft.Dropdown(
                value=val or opts[0],
                options=[ft.dropdown.Option(o) for o in opts],
                border_color=DRILL_BRD, focused_border_color=BLUE,
                color=DRILL_TXT, bgcolor=DRILL_CARD2,
                border_radius=8, height=44, text_size=13,
                content_padding=P(12, 0, 12, 0),
            )

        def _field_row(lbl, ctrl):
            return ft.Column([_lbl(lbl), ctrl], spacing=4)

        def _chip(lbl, color):
            return ft.Container(
                ft.Text(lbl, size=10, color=color, weight=ft.FontWeight.BOLD),
                padding=P(6, 2, 6, 2), border_radius=10, border=ft.border.all(1, color),
            )

        # ── Log entry line ────────────────────────────────────────────────────
        class DrillRow:
            def __init__(self, data=None, on_del=None):
                d = data or {}
                self.f_bh   = _inp("BGC 000000", d.get("bh_number",""), 110)
                self.f_from = _inp("0", d.get("depth_from",""), 60)
                self.f_to   = _inp("0", d.get("depth_to",""),   60)
                self.f_adv  = _inp("0", d.get("advance",""),    60)
                self.f_time = _inp("0", d.get("time_hours",""), 55)
                self.f_comm = _inp("Commentaire", d.get("comments",""))
                self.widget = ft.Column([
                    ft.Row([
                        ft.Column([_lbl("B/H"), self.f_bh], spacing=2),
                        ft.Column([_lbl("De(m)"), self.f_from], spacing=2),
                        ft.Column([_lbl("À(m)"), self.f_to], spacing=2),
                        ft.Column([_lbl("Avance"), self.f_adv], spacing=2),
                        ft.Column([_lbl("Temps(h)"), self.f_time], spacing=2),
                    ], spacing=6, wrap=True),
                    ft.Row([
                        ft.Column([_lbl("Commentaires"), self.f_comm], spacing=2, expand=True),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DNG, icon_size=20,
                                      on_click=lambda _: on_del(self) if on_del else None),
                    ], spacing=6),
                    ft.Container(height=1, bgcolor=DRILL_BRD),
                ], spacing=6)

            def to_dict(self):
                def _f(v):
                    try: return float(v) if str(v).strip() else None
                    except: return None
                df, dt = _f(self.f_from.value), _f(self.f_to.value)
                run = round(dt - df, 2) if df is not None and dt is not None else None
                return {"bh_number": self.f_bh.value or None, "depth_from": df,
                        "depth_to": dt, "run": run, "advance": _f(self.f_adv.value),
                        "time_hours": _f(self.f_time.value), "comments": self.f_comm.value or None}

        # ── List view ─────────────────────────────────────────────────────────
        def _refresh_list():
            list_col.controls.clear()
            reports = list_pending_drilling()
            if not reports:
                list_col.controls.append(ft.Container(
                    ft.Column([
                        ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=48, color=DRILL_MUT),
                        ft.Text("Aucun rapport", size=14, color=DRILL_MUT),
                        ft.Text("Créez votre premier rapport de forage", size=12, color=DRILL_MUT),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(0, 0), expand=True, padding=P(40,40,40,40),
                ))
            for rep in reports:
                sc = STATUS_COLOR.get(rep["status"], MUT)
                sl = STATUS_LABEL.get(rep["status"], rep["status"])
                list_col.controls.append(ft.Container(
                    bgcolor=DRILL_CARD, border=ft.border.all(1, DRILL_BRD), border_radius=12,
                    padding=P(14, 12, 14, 12), ink=True,
                    on_click=lambda _, r=rep: _show_detail(r),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.HARDWARE_OUTLINED, color=DRILL_NAV, size=20),
                            ft.Column([
                                ft.Text(f"Rapport du {rep.get('report_date','')}",
                                        size=13, color=DRILL_TXT, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Shift {rep.get('shift','')} · {rep.get('contract_location') or '—'}",
                                        size=11, color=DRILL_MUT),
                            ], spacing=2, expand=True),
                            _chip(sl, sc),
                        ], spacing=10),
                        ft.Row([
                            ft.Text(f"Rig: {rep.get('rig_type','')} {rep.get('rig_number','')}".strip() or "—",
                                    size=12, color=DRILL_MUT),
                            ft.Container(expand=True),
                            ft.Text(f"Avance: {rep.get('total_advance',0)} m",
                                    size=12, color=BLUE, weight=ft.FontWeight.BOLD),
                        ]),
                    ], spacing=6),
                ))
            _u(list_col)

        # ── Detail view ───────────────────────────────────────────────────────
        def _show_detail(rep):
            ds["current"] = rep
            form_col.controls.clear()
            status = rep.get("status", "draft")
            sc = STATUS_COLOR.get(status, MUT)
            sl = STATUS_LABEL.get(status, status)
            diesel = rep.get("diesel") or {}

            def _row2(lbl, val):
                return ft.Row([
                    ft.Text(lbl + ":", size=12, color=DRILL_MUT, width=130),
                    ft.Text(str(val or "—"), size=12, color=DRILL_TXT),
                ], spacing=8)

            entry_widgets = []
            for e in rep.get("entries") or []:
                entry_widgets.append(ft.Container(
                    bgcolor=DRILL_CARD2, border_radius=8, padding=P(10,8,10,8),
                    content=ft.Column([
                        ft.Row([
                            ft.Text(str(e.get("bh_number") or "—"), size=12, color=DRILL_TXT, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.Text(f"Avance: {e.get('advance') or '—'} m", size=11, color=BLUE),
                        ]),
                        ft.Row([
                            ft.Text(f"De: {e.get('depth_from','')}m", size=11, color=DRILL_MUT),
                            ft.Text(f"À: {e.get('depth_to','')}m", size=11, color=DRILL_MUT),
                            ft.Text(f"Run: {e.get('run','')}m", size=11, color=DRILL_MUT),
                            ft.Text(f"Temps: {e.get('time_hours','')}h", size=11, color=DRILL_MUT),
                        ], spacing=8, wrap=True),
                        ft.Text(str(e.get("comments") or ""), size=11, color=DRILL_MUT),
                    ], spacing=4),
                ))

            diesel_widgets = []
            for eq in equipment:
                v = diesel.get(eq["code"])
                if v:
                    diesel_widgets.append(ft.Row([
                        ft.Text(eq["name"], size=12, color=DRILL_TXT, expand=True),
                        ft.Text(f"{v} {eq['unit']}", size=12, color=BLUE, weight=ft.FontWeight.BOLD),
                    ]))

            # Action buttons based on status
            action_btns = []
            if status == "draft":
                sup_name = _inp("Nom du superviseur")
                action_btns = [
                    _btn("Modifier", ft.Icons.EDIT_OUTLINED, BLUE,
                         lambda _: _show_form(rep), 44),
                    _btn("Soumettre", ft.Icons.SEND_ROUNDED, OK,
                         lambda _: _do_submit(rep["uuid"]), 44),
                    _btn("Supprimer", ft.Icons.DELETE_OUTLINE, DNG,
                         lambda _: _do_delete(rep["uuid"]), 44),
                ]
            elif status == "submitted":
                sup_inp = _inp("Votre nom (superviseur)")
                action_btns = [
                    sup_inp,
                    _btn("Valider le rapport", ft.Icons.CHECK_CIRCLE_OUTLINED, OK,
                         lambda _: _do_validate(rep["uuid"], sup_inp.value), 44),
                    _btn("Annuler soumission", ft.Icons.UNDO_ROUNDED, WARN,
                         lambda _: _do_unsubmit(rep["uuid"]), 44),
                ]
            elif status == "validated":
                action_btns = [
                    ft.Container(
                        ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=OK, size=20),
                            ft.Text("Validé — prêt à synchroniser", size=13, color=OK),
                        ], spacing=8),
                        bgcolor="#0A2A0A", border=ft.border.all(1, OK), border_radius=8, padding=P(12,10,12,10),
                    ),
                    _btn("Synchroniser maintenant", ft.Icons.SYNC_ROUNDED, BLUE,
                         lambda _: go_to("settings"), 44),
                ]

            form_col.controls = [
                _hdr("Détail rapport", "drilling"),
                ft.Container(
                    ft.Column([
                        ft.Row([_chip(sl, sc),
                                ft.Text(f"{rep.get('report_date','')} · Shift {rep.get('shift','')}",
                                        size=12, color=DRILL_MUT)], spacing=10),
                        ft.Divider(color=DRILL_BRD),
                        _row2("Rig", f"{rep.get('rig_type','')} {rep.get('rig_number','')}".strip()),
                        _row2("Localisation", rep.get("contract_location")),
                        _row2("N° Trou", rep.get("hole_number")),
                        _row2("Angle", f"{rep.get('angle','')}°" if rep.get("angle") else "—"),
                        _row2("Client", rep.get("client")),
                        _row2("Opérateur", rep.get("operator_name")),
                        _row2("Superviseur", rep.get("supervisor_name")),
                        _row2("Avance totale", f"{rep.get('total_advance',0)} m"),
                    ], spacing=6),
                    bgcolor=DRILL_CARD, border=ft.border.all(1, DRILL_BRD), border_radius=12, padding=P(14,12,14,12),
                ),
                ft.Text("TABLEAU DE FORAGE", size=11, color=DRILL_MUT, weight=ft.FontWeight.BOLD),
                *(entry_widgets or [ft.Text("Aucune entrée", size=12, color=DRILL_MUT)]),
                ft.Text("DIESEL RE-FUELING", size=11, color=DRILL_MUT, weight=ft.FontWeight.BOLD),
                *(diesel_widgets or [ft.Text("Aucun carburant", size=12, color=DRILL_MUT)]),
                ft.Divider(color=DRILL_BRD),
                *action_btns,
                ft.Container(height=80),
            ]
            ds["view"] = "detail"
            content.controls = [form_col]
            _u(content)

        # ── Form (create / edit) ──────────────────────────────────────────────
        def _show_form(existing=None):
            r = existing or {}
            log_rows: list[DrillRow] = []
            rows_col  = ft.Column(spacing=4)
            form_msg  = ft.Text("", size=12, color=DNG)

            f_shift  = _dd(["DAY", "NIGHT"], r.get("shift","DAY"))
            f_date   = _inp("YYYY-MM-DD", r.get("report_date") or str(_date.today()))
            f_rtype  = _inp("AC/RC", r.get("rig_type",""))
            f_rnum   = _inp("001",   r.get("rig_number",""))
            f_loc    = _inp("Folona", r.get("contract_location",""))
            f_hole   = _inp("",      r.get("hole_number",""))
            f_angle  = _inp("60",    str(r.get("angle") or ""))
            f_client = _inp("SOMISY", r.get("client",""))
            f_oper   = _inp("Nom opérateur", r.get("operator_name",""))
            f_rfuel  = _inp("Ravitailleur", r.get("refueler_name",""))

            diesel_fields: dict[str, ft.TextField] = {}
            diesel_widgets_form = []
            existing_diesel = r.get("diesel") or {}
            for eq in equipment:
                tf = _inp("0", str(existing_diesel.get(eq["code"]) or ""), 100)
                diesel_fields[eq["code"]] = tf
                diesel_widgets_form.append(ft.Row([
                    ft.Text(eq["name"], size=12, color=DRILL_TXT, expand=True),
                    tf,
                    ft.Text(eq.get("unit","L"), size=11, color=DRILL_MUT),
                ], spacing=8))

            def _del_row(lr):
                log_rows.remove(lr)
                rows_col.controls.remove(lr.widget)
                _u(rows_col)

            def _add_row(data=None):
                lr = DrillRow(data, on_del=_del_row)
                log_rows.append(lr)
                rows_col.controls.append(lr.widget)
                _u(rows_col)

            for e in r.get("entries") or [{}]:
                _add_row(e)
            if not log_rows:
                _add_row()

            def _save(_):
                try:
                    adv = sum(
                        float(lr.f_adv.value or 0)
                        for lr in log_rows if lr.f_adv.value
                    )
                    diesel = {}
                    for code, tf in diesel_fields.items():
                        try:
                            v = float(tf.value or 0)
                            if v: diesel[code] = v
                        except: pass
                    data = {
                        "uuid":             r.get("uuid"),
                        "shift":            f_shift.value,
                        "report_date":      f_date.value,
                        "rig_type":         f_rtype.value or None,
                        "rig_number":       f_rnum.value or None,
                        "contract_location": f_loc.value or None,
                        "hole_number":      f_hole.value or None,
                        "angle":            float(f_angle.value) if f_angle.value else None,
                        "client":           f_client.value or None,
                        "total_advance":    round(adv, 2),
                        "diesel":           diesel,
                        "refueler_name":    f_rfuel.value or None,
                        "operator_name":    f_oper.value or None,
                        "entries":          [lr.to_dict() for lr in log_rows],
                        "status":           r.get("status") or "draft",
                    }
                    save_drilling_report(data)
                    msg_txt.value = "Rapport enregistré."
                    msg_txt.color = OK
                    ds["view"] = "list"
                    _refresh_list()
                    content.controls = [list_col]
                    page.update()
                except Exception as exc:
                    form_msg.value = str(exc)
                    _u(form_msg)

            form_col.controls = [
                _hdr("Nouveau rapport" if not r else "Modifier rapport", "drilling"),
                ft.Container(
                    ft.Column([
                        ft.Text("INFORMATIONS GÉNÉRALES", size=11, color=DRILL_MUT, weight=ft.FontWeight.BOLD),
                        ft.Row([_field_row("Shift", f_shift), _field_row("Date", f_date)], spacing=10),
                        ft.Row([_field_row("Type Rig", f_rtype), _field_row("N° Rig", f_rnum)], spacing=10),
                        ft.Row([_field_row("Localisation", f_loc), _field_row("Angle°", f_angle)], spacing=10),
                        ft.Row([_field_row("N° Trou", f_hole), _field_row("Client", f_client)], spacing=10),
                        ft.Row([_field_row("Opérateur", f_oper), _field_row("Ravitailleur", f_rfuel)], spacing=10),
                    ], spacing=10),
                    bgcolor=DRILL_CARD, border=ft.border.all(1, DRILL_BRD), border_radius=12, padding=P(14,12,14,12),
                ),
                ft.Container(
                    ft.Column([
                        ft.Text("TABLEAU DE FORAGE", size=11, color=DRILL_MUT, weight=ft.FontWeight.BOLD),
                        rows_col,
                        ft.TextButton(
                            content=ft.Row([ft.Icon(ft.Icons.ADD, size=16, color=BLUE),
                                            ft.Text("Ajouter ligne", color=BLUE, size=12)], tight=True, spacing=4),
                            on_click=lambda _: _add_row(),
                        ),
                    ], spacing=8),
                    bgcolor=DRILL_CARD, border=ft.border.all(1, DRILL_BRD), border_radius=12, padding=P(14,12,14,12),
                ),
                ft.Container(
                    ft.Column([
                        ft.Text("DIESEL RE-FUELING", size=11, color=DRILL_MUT, weight=ft.FontWeight.BOLD),
                        *diesel_widgets_form,
                    ], spacing=8),
                    bgcolor=DRILL_CARD, border=ft.border.all(1, DRILL_BRD), border_radius=12, padding=P(14,12,14,12),
                ),
                form_msg,
                ft.Row([
                    ft.ElevatedButton("Annuler", bgcolor=DRILL_CARD2, color=DRILL_MUT,
                                      on_click=lambda _: _go_list()),
                    ft.ElevatedButton("Enregistrer", bgcolor=BLUE, color=DRILL_TXT,
                                      on_click=_save),
                ], spacing=12),
                ft.Container(height=80),
            ]
            ds["view"] = "form"
            content.controls = [form_col]
            _u(content)

        # ── Actions ───────────────────────────────────────────────────────────
        def _go_list():
            ds["view"] = "list"
            _refresh_list()
            content.controls = [list_col]
            _u(content)

        def _do_submit(uid):
            submit_drilling_report(uid)
            notify("Rapport soumis — en attente de validation.", OK)
            _go_list()

        def _do_validate(uid, sup_name):
            if not sup_name.strip():
                notify("Saisissez votre nom avant de valider.", WARN)
                return
            validate_drilling_report_mobile(uid, sup_name.strip())
            notify("Rapport validé — prêt à synchroniser.", OK)
            _go_list()

        def _do_unsubmit(uid):
            with get_mobile_connection() as c:
                c.execute("UPDATE pending_drilling SET status='draft' WHERE uuid=?", (uid,))
            notify("Soumission annulée.", WARN)
            _go_list()

        def _do_delete(uid):
            delete_pending_drilling(uid)
            notify("Rapport supprimé.", DNG)
            _go_list()

        # ── Wire sync: include drilling in payload ────────────────────────────
        # This is hooked into the existing sync button via the wiring below

        # ── Initial render ────────────────────────────────────────────────────
        _refresh_list()
        msg_txt_row = ft.Row([msg_txt], alignment=ft.MainAxisAlignment.CENTER)

        return _scaffold(
            ft.Column([
                _hdr("Drilling Reports", "drilling"),
                msg_txt_row,
                ft.Row([
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "Nouveau rapport",
                        icon=ft.Icons.ADD,
                        bgcolor=DRILL_NAV,
                        color=DRILL_TXT,
                        on_click=lambda _: _show_form(),
                    ),
                ], alignment=ft.MainAxisAlignment.END),
                ft.Container(
                    content=content,
                    expand=True,
                ),
            ], spacing=10, expand=True),
        )

    def _s_settings():
        # ── State controls ─────────────────────────────────────────────────────
        cfg     = ft.Text("", size=12, weight=ft.FontWeight.W_500)
        srv_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=MUT)
        srv_lbl = ft.Text("Non vérifié", size=11, color=MUT, weight=ft.FontWeight.W_500)

        def _set_srv(ok: bool):
            srv_dot.bgcolor = OK if ok else DNG
            srv_lbl.value   = "En ligne" if ok else "Hors ligne"
            srv_lbl.color   = OK if ok else DNG

        def _notify(msg, color):
            cfg.value = msg; cfg.color = color; page.update()

        # ── Handlers ──────────────────────────────────────────────────────────
        def do_save(e=None):
            try:
                validate_url()
                save_setting("server_url",  srv_url.value)
                save_setting("token",       srv_token.value)
                save_setting("device_name", srv_device.value)
                if not get_setting("device_id"):
                    save_setting("device_id", str(uuid4()))
                _notify("Configuration enregistrée.", OK)
            except Exception as exc:
                _notify(str(exc), DNG)

        def do_test(e=None):
            busy(True, "Test de connexion...")
            try:
                addr = validate_url()
                data = request_json(f"{addr}/api/mobile/ping", srv_token.value)
                _set_srv(True)
                _notify(f"Serveur OK · {data.get('server','–')} · {(data.get('time',''))[:16]}", OK)
            except Exception as exc:
                _set_srv(False); _notify(str(exc)[:200], DNG)
            finally:
                busy(False); page.update()

        def do_dl(e=None):
            busy(True, "Téléchargement des données...")
            try:
                if not get_setting("mobile_session"):
                    _notify("Connectez-vous d'abord (section Compte ci-dessous).", DNG)
                    busy(False); return
                addr = validate_url(); _boot(addr)
                _notify("Données téléchargées avec succès.", OK); _refresh_all()
            except Exception as exc:
                _notify(str(exc)[:200], DNG)
            finally:
                busy(False); page.update()

        # ── Last sync label ────────────────────────────────────────────────────
        try:
            ls = json.loads(get_setting("last_sync") or "{}")
            at = ls.get("at","")
            sync_lbl = datetime.fromisoformat(at).strftime("%d/%m/%Y à %H:%M") if at else "Jamais"
        except Exception:
            sync_lbl = "Jamais"

        # ── Session info ───────────────────────────────────────────────────────
        is_logged = bool(get_setting("mobile_session"))
        uname     = get_setting("identity_username") or ""
        urole     = get_setting("profile_label") or get_setting("identity_role") or "Agent"
        initials  = (uname[:2] if uname else "?").upper()

        # ── Icon box helper ────────────────────────────────────────────────────
        def _ibox(icon, color):
            return ft.Container(width=38,height=38,border_radius=10,
                bgcolor=f"{color}20",alignment=AL(0,0),
                content=ft.Icon(icon,color=color,size=19))

        # ── Card 1 · Serveur PC ────────────────────────────────────────────────
        server_card = _card(ft.Column([
            ft.Row([
                _ibox(ft.Icons.ROUTER_ROUNDED, BLUE),
                ft.Container(width=10),
                ft.Column([
                    ft.Text("Serveur PC", size=14,
                            weight=ft.FontWeight.BOLD, color=TXT),
                    ft.Row([srv_dot, ft.Container(width=4), srv_lbl],
                           tight=True),
                ], spacing=2, tight=True, expand=True),
            ], tight=True),
            _div(),
            srv_url, srv_token, srv_device,
            ft.Container(
                bgcolor=BG, border_radius=8,
                padding=P(10,8,10,8),
                content=cfg,
            ),
            ft.Row([
                _btn("Enregistrer", ft.Icons.SAVE_ROUNDED,
                     BLUE, do_save, 44),
                ft.Container(width=10),
                _gbtn("Tester", ft.Icons.WIFI_TETHERING_OUTLINED,
                      BLUE, do_test, 44),
            ]),
        ], spacing=12, tight=True), P(16,16,16,16))

        # ── Card 2 · Synchronisation ───────────────────────────────────────────
        sync_card = _card(ft.Column([
            ft.Row([
                _ibox(ft.Icons.SYNC_ROUNDED, INFO),
                ft.Container(width=10),
                ft.Column([
                    ft.Text("Synchronisation", size=14,
                            weight=ft.FontWeight.BOLD, color=TXT),
                    ft.Row([
                        ft.Icon(ft.Icons.ACCESS_TIME_OUTLINED,
                                size=12, color=MUT),
                        ft.Container(width=4),
                        ft.Text(f"Dernière : {sync_lbl}",
                                size=11, color=MUT),
                    ], tight=True),
                ], spacing=2, tight=True, expand=True),
            ], tight=True),
            _div(),
            _btn("Télécharger les données",
                 ft.Icons.CLOUD_DOWNLOAD_ROUNDED, INFO, do_dl, 46),
        ], spacing=12, tight=True), P(16,16,16,16))

        # ── Card 3 · Compte ───────────────────────────────────────────────────
        if is_logged:
            acct_body = ft.Column([
                ft.Row([
                    _ibox(ft.Icons.VERIFIED_USER_OUTLINED, OK),
                    ft.Container(width=10),
                    ft.Text("Compte", size=14,
                            weight=ft.FontWeight.BOLD, color=TXT),
                ], tight=True),
                _div(),
                ft.Row([
                    ft.Container(
                        width=50, height=50, border_radius=25,
                        bgcolor=BLUE, alignment=AL(0,0),
                        content=ft.Text(initials, size=19,
                                        weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF"),
                    ),
                    ft.Container(width=12),
                    ft.Column([
                        ft.Text(uname or "—", size=15,
                                weight=ft.FontWeight.BOLD, color=TXT),
                        ft.Text(urole, size=12, color=MUT),
                        ft.Container(
                            padding=P(8,3,8,3), border_radius=12,
                            bgcolor=f"{OK}22",
                            content=ft.Text("Session active", size=11,
                                            color=OK,
                                            weight=ft.FontWeight.W_600),
                        ),
                    ], spacing=4, tight=True, expand=True),
                ], tight=True),
                _gbtn("Se déconnecter",
                      ft.Icons.LOGOUT_ROUNDED, DNG, do_logout, 42),
            ], spacing=12, tight=True)
        else:
            acct_body = ft.Column([
                ft.Row([
                    _ibox(ft.Icons.LOCK_OPEN_OUTLINED, BLUE),
                    ft.Container(width=10),
                    ft.Text("Connexion", size=14,
                            weight=ft.FontWeight.BOLD, color=TXT),
                ], tight=True),
                _div(),
                lgn_user, lgn_pass,
                lgn_status,
                _btn("Se connecter", ft.Icons.LOGIN_ROUNDED,
                     BLUE, do_login, 44),
            ], spacing=12, tight=True)

        acct_card = _card(acct_body, P(16,16,16,16))

        # ── Footer · version ──────────────────────────────────────────────────
        footer = ft.Row([
            ft.Icon(ft.Icons.VERIFIED_OUTLINED, size=12, color=MUT),
            ft.Text("OREZONE QHSE Mobile  ·  v2.0.0",
                    size=11, color=MUT),
        ], spacing=6, tight=True,
           alignment=ft.MainAxisAlignment.CENTER)

        return ft.Container(bgcolor=BG, expand=True,
            content=ft.Column([
                _hdr("Paramètres", "profile"),
                ft.Container(
                    expand=True,
                    padding=P(14,12,14,80),
                    content=ft.Column([
                        server_card,
                        sync_card,
                        acct_card,
                        ft.Container(height=4),
                        footer,
                    ], spacing=14, scroll=ft.ScrollMode.AUTO),
                ),
            ], spacing=0))

    def _build(key):
        if key=="login":       return _s_login()
        if key=="home":        return _s_home()
        # ── Domaines métier (onglets principaux)
        if key=="securite":    return _s_securite()
        if key=="maintenance": return _s_maint()
        if key=="personnel":   return _s_personnel()
        # ── Sous-modules Sécurité
        if key=="alerts":      return _s_alerts()
        if key=="incident":    return _s_incident()
        if key=="ppe_check":   return _s_ppe_check()
        if key=="ppe_assign":  return _s_ppe_assign()
        if key=="toolbox":     return _s_toolbox()
        if key=="inspection":  return _s_inspect()
        # ── Sous-modules Maintenance
        if key=="intervention":return _s_interv()
        if key=="panne":       return _s_panne()
        # ── Sous-modules Personnel
        if key=="attendance":  return _s_attendance()
        if key=="timesheet":   return _s_timesheet()
        if key=="drilling":    return _s_drilling()
        # ── Profil & paramètres
        if key=="profile":     return _s_profile()
        if key=="settings":    return _s_settings()
        return _s_home()

    # ── Bootstrap ─────────────────────────────────────────────────────────────
    _rebuild_ppe(); _rebuild_ins()
    _toggle(inc_tr,"inc_type",TYPE_INC_LABELS,TYPE_INC_COLORS)
    _toggle(inc_gr,"inc_grav",GRAVITE_LABELS,GRAVITE_COLORS)
    page.appbar=None; page.navigation_bar=None
    page.add(ft.Stack([ft.Container(content=area,expand=True),overlay],expand=True))
    if get_setting("mobile_session") and get_setting("identity_username"):
        _enter_app()
    else:
        area.content=_build("login"); page.update()


def main(page: ft.Page) -> None:
    # ── Splash screen immédiat ─────────────────────────────────────────────────
    page.bgcolor = "#071321"
    page.padding = 0
    page.add(ft.Container(
        expand=True,
        alignment=ft.Alignment(0, 0),
        bgcolor="#071321",
        content=ft.Column([
            ft.Image(
                src="assets/orezone_qhse_icon.png",
                width=90, height=90,
                error_content=ft.Icon(ft.Icons.SHIELD_OUTLINED, size=72, color="#3B82F6"),
            ),
            ft.Container(height=28),
            ft.ProgressRing(color="#3B82F6", width=46, height=46, stroke_width=3),
            ft.Container(height=18),
            ft.Text("OREZONE QHSE", size=18,
                    weight=ft.FontWeight.BOLD, color="#E2E8F0"),
            ft.Text("Chargement en cours…", size=12, color="#7A9BB5"),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=4, tight=True),
    ))
    page.update()

    # ── Paramètres fenêtre (desktop uniquement) ────────────────────────────────
    try:
        _is_mobile = page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
    except Exception:
        _is_mobile = False

    if not _is_mobile:
        try:
            page.window.width        = 430
            page.window.height       = 900
            page.window.min_width    = 360
            page.window.min_height   = 600
            page.window.resizable    = True
            page.window.title_bar_hidden = False
        except Exception:
            pass

    # ── Construction de l'interface ────────────────────────────────────────────
    page.controls.clear()
    try:
        build_mobile_page(page)
    except Exception as exc:
        page.controls.clear()
        page.add(ft.Container(
            expand=True, alignment=ft.Alignment(0, 0), padding=24,
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE, color="#EF4444", size=52),
                ft.Text("Erreur au d\xe9marrage", size=16,
                        weight=ft.FontWeight.BOLD, color="#EF4444"),
                ft.Text(str(exc)[:400], size=11, color="#94A3B8",
                        no_wrap=False, max_lines=12),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=14),
        ))
        page.update()


if __name__ == "__main__":
    ft.run(main)
