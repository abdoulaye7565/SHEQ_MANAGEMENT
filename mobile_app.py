from __future__ import annotations

import json
import os
import sqlite3
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


def get_mobile_connection() -> sqlite3.Connection:
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
    """)
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
             "incidents":"pending_incidents","ppe_checks":"pending_ppe_checks","observations":"pending_observations"}.get(kind)
    clean = [int(v) for v in (ids or []) if str(v).strip().isdigit()]
    if not table or not clean: return
    ph = ",".join("?" * len(clean))
    with get_mobile_connection() as c:
        c.execute(f"DELETE FROM {table} WHERE id_pending IN ({ph})", clean)  # noqa: S608

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
            + len(list_pending_observations()) + len(list_pending_ppe_assigns()))


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

def request_bytes(url: str, token: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Erreur serveur {exc.code}: {exc.read().decode('utf-8','replace')[:200]}")
    except Exception as exc:
        raise ValueError(f"Erreur réseau: {exc}")


# ─── App ──────────────────────────────────────────────────────────────────────

def build_mobile_page(page: ft.Page) -> None:  # noqa: PLR0914,PLR0915

    page.title       = "OREZONE QHSE"
    page.theme_mode  = ft.ThemeMode.LIGHT
    page.bgcolor     = "#0A1929"
    page.padding     = 0
    page.theme       = ft.Theme(color_scheme_seed="#2563EB", use_material3=True,
                                visual_density=ft.VisualDensity.COMFORTABLE)

    # ── Palette ───────────────────────────────────────────────────────────────
    NAV  = "#0F2E4C"; BLUE = "#2563EB"; BG   = "#F4F7FB"
    CARD = "#FFFFFF"; BRD  = "#E2E8F0"; TXT  = "#0F172A"; MUT  = "#64748B"
    OK   = "#16A34A"; WARN = "#D97706"; DNG  = "#DC2626"
    INFO = "#0891B2"; PURP = "#7C3AED"

    GRAD = ft.LinearGradient(begin=ft.Alignment(-1,-1), end=ft.Alignment(1,0.8),
                             colors=[NAV,"#1E56A0"])

    def P(l=0,t=0,r=0,b=0): return ft.Padding(left=l,top=t,right=r,bottom=b)
    def AL(x=0,y=0):         return ft.Alignment(x,y)
    def SH(blur=8,op="10"):
        return ft.BoxShadow(blur_radius=blur,spread_radius=0,
                            color=f"#{op}000000",offset=ft.Offset(0,3))

    # ── Atoms ─────────────────────────────────────────────────────────────────
    def _badge(label, color, bg=""):
        return ft.Container(bgcolor=bg or f"{color}18",border_radius=20,
            border=ft.border.all(1,f"{color}44"),padding=P(10,3,10,3),
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
            border=ft.border.all(1,f"{accent}22" if accent else BRD),
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
            shadow=SH(),border=ft.border.all(1,f"{color}22"),
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
        return ft.Container(border=ft.border.all(1.5,color),border_radius=12,height=height,
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
        L=(ft.Container(width=38,height=38,border_radius=19,bgcolor="#FFFFFF18",
               alignment=AL(0,0),ink=True,on_click=lambda e:go_to(back),
               content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,color="#FFFFFF",size=18))
           if back else ft.Container(width=38))
        R=(ft.Container(width=38,height=38,border_radius=19,bgcolor="#FFFFFF18",
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
            border_radius=10,border_color=BRD,focused_border_color=BLUE,**kw)

    def _dd(label,opts=None):
        return ft.Dropdown(label=label,options=opts or [],
            border_radius=10,border_color=BRD,focused_border_color=BLUE)

    # ── Form Controls ─────────────────────────────────────────────────────────
    def _dark_tf(label,hint="",pw=False,val=""):
        return ft.TextField(label=label,hint_text=hint,password=pw,
            can_reveal_password=pw,value=val,border_radius=10,
            border_color="#1E3A5F",focused_border_color=BLUE,
            bgcolor="#132337",color="#E2E8F0",
            label_style=ft.TextStyle(color="#64748B"))

    srv_url    = _dark_tf("Serveur PC","http://192.168.1.x:8765",val=get_setting("server_url") or "")
    srv_token  = _dark_tf("Token d'appairage",pw=True,val=get_setting("token") or "")
    srv_device = _dark_tf("Nom appareil",val=get_setting("device_name") or "Telephone terrain")
    lgn_user   = _dark_tf("Nom d'utilisateur",val=get_setting("identity_username") or "")
    lgn_pass   = _dark_tf("Mot de passe",pw=True)
    lgn_rem    = ft.Switch(value=True,active_color=BLUE)
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
        border_radius=12,border_color=BRD,focused_border_color=BLUE,height=46)
    tb_today = ft.Column(spacing=8)
    tb_hist  = ft.Column(spacing=6)
    al_col   = ft.Column(spacing=8)
    ep_col   = ft.Column(spacing=8)
    pr_col   = ft.Column(spacing=8)
    inc_tr   = ft.Row(spacing=6,wrap=True)
    inc_gr   = ft.Row(spacing=6,wrap=True)

    ST: dict = {"screen":"login","nav":["home","maintenance","toolbox","alerts","profile"],
                "alerts_tab":"all","attendees":0,
                "inc_type":"accident","inc_grav":"mineur",
                "ppe":{lbl:"na" for lbl,_ in PPE_ITEMS}}

    srv_dot   = ft.Container(width=9,height=9,bgcolor=WARN,border_radius=5)
    _navref: list = []
    area      = ft.Container(expand=True)
    overlay   = ft.Container(visible=False,expand=True,bgcolor="#CC000000",alignment=AL(0,0),
        content=ft.Container(bgcolor=CARD,border_radius=16,padding=P(28,28,28,28),
            content=ft.Column([ft.ProgressRing(color=BLUE,width=36,height=36),
                ft.Text("Chargement...",color=TXT,size=14,weight=ft.FontWeight.BOLD)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=16,tight=True)))

    def notify(msg,color=MUT):
        page.snack_bar=ft.SnackBar(ft.Text(msg,color="#FFFFFF",size=13),bgcolor=color,duration=3500)
        page.snack_bar.open=True

    def confirm(title, msg, on_yes, danger=False, yes_lbl="Confirmer", no_lbl="Annuler"):
        btn_color=DNG if danger else BLUE
        def _yes(e):
            page.dialog.open=False; page.update(); on_yes(e)
        def _no(e):
            page.dialog.open=False; page.update()
        icon=ft.Icons.WARNING_AMBER_ROUNDED if danger else ft.Icons.HELP_OUTLINE_ROUNDED
        icon_color=DNG if danger else WARN
        page.dialog=ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(icon,color=icon_color,size=20),
                ft.Text(title,size=15,weight=ft.FontWeight.BOLD,color=TXT),
            ],spacing=8,tight=True),
            content=ft.Text(msg,size=13,color=MUT),
            actions=[
                ft.TextButton(no_lbl,on_click=_no,
                    style=ft.ButtonStyle(color=MUT)),
                ft.ElevatedButton(yes_lbl,on_click=_yes,
                    bgcolor=btn_color,color="#FFFFFF",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog.open=True; page.update()

    def busy(on): overlay.visible=on; page.update()

    def go_to(key):
        ST["screen"]=key; area.content=_build(key)
        if _navref and key in ST["nav"]: _navref[0].selected_index=ST["nav"].index(key)
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
            return ft.Container(bgcolor=c if active else "#F1F5F9",border_radius=8,
                padding=P(12,8,12,8),ink=True,
                border=ft.border.all(1,c if active else BRD),
                on_click=lambda e,kk=k:[ST.__setitem__(sk,kk),_toggle(row,sk,opts,colors)],
                content=ft.Text(lbl,size=12,color="#FFFFFF" if active else MUT,
                                weight=ft.FontWeight.W_600))
        row.controls=[_b(k,opts[k],colors[k]) for k in opts]
        try: row.update()
        except Exception: pass

    def _rebuild_ppe():
        res=ST["ppe"]
        def _b(il,val,text,c):
            active=res.get(il)==val
            return ft.Container(bgcolor=c if active else "#F1F5F9",border_radius=6,
                padding=P(8,5,8,5),ink=True,border=ft.border.all(1,c if active else BRD),
                on_click=lambda e,i=il,v=val:[ST["ppe"].__setitem__(i,v),_rebuild_ppe()],
                content=ft.Text(text,size=11,color="#FFFFFF" if active else MUT,
                                weight=ft.FontWeight.W_600))
        def _row(lbl,ico):
            cur=res.get(lbl,"na")
            sc=OK if cur=="ok" else(DNG if cur=="nok" else MUT)
            return ft.Container(bgcolor=CARD,border=ft.border.all(1,sc if cur!="na" else BRD),
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
            return ft.Container(bgcolor=CARD,border=ft.border.all(1,OK if checked else BRD),
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
        busy(True); lgn_status.value=""
        try:
            if not str(lgn_user.value or "").strip(): raise ValueError("Identifiant obligatoire.")
            addr=validate_url()
            save_setting("server_url",srv_url.value); save_setting("token",srv_token.value)
            save_setting("device_name",srv_device.value)
            if not get_setting("device_id"): save_setting("device_id",str(uuid4()))
            data=post_json(f"{addr}/api/mobile/login",srv_token.value,
                           {"username":lgn_user.value,"password":lgn_pass.value})
            u=data.get("user") or {}
            save_setting("mobile_session",data.get("session_token") or "")
            save_setting("identity_username",u.get("username") or "")
            save_setting("identity_role",u.get("role") or "")
            save_setting("profile_label",u.get("label") or u.get("role") or "")
            lgn_pass.value=""
            _boot(addr); _enter_app()
        except Exception as exc:
            raw=str(exc)
            if "10060" in raw or "timed out" in raw.lower():
                lgn_status.value="Serveur inaccessible — démarrez l'app QHSE sur le PC."
            elif "refused" in raw.lower() or "10061" in raw:
                lgn_status.value="Connexion refusée — serveur non démarré sur ce port."
            elif "urlopen" in raw.lower():
                lgn_status.value=f"Réseau : {raw.split('urlopen error')[-1].strip('<> ')}"
            else: lgn_status.value=raw
            page.update()
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
                page.dialog.open = False; page.update()
                _apply_pairing(url, tk)
            except Exception as exc:
                msg_ctrl.value = f"Presse-papiers invalide : {exc}\nCopiez le code sur le PC, puis réessayez."
                msg_ctrl.color = DNG
                try: page.update()
                except Exception: pass

        def _cancel(ev=None):
            page.dialog.open = False; page.update()

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

        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.LINK_ROUNDED, color=BLUE, size=20),
                ft.Text("Appairage PC → Mobile", size=15, weight=ft.FontWeight.BOLD, color=TXT),
            ], spacing=8, tight=True),
            content=ft.Column([
                ft.Container(
                    bgcolor=f"{BLUE}12", border_radius=10, padding=14,
                    border=ft.border.all(1, f"{BLUE}30"),
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
                ft.ElevatedButton(
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
        page.dialog.open = True; page.update()

    def _boot(addr):
        tk=get_setting("token") or srv_token.value
        # Bootstrap
        try:
            data=request_json(f"{addr}/api/mobile/bootstrap?date={date.today().isoformat()}",tk)
            save_employees(data.get("employees") or [])
            save_toolbox_topic(data.get("toolbox_topic") or {})
            save_maintenance_items(data.get("maintenance_items") or [])
            for k in ("dashboard","alerts","maintenance_plan","timesheet"):
                save_setting(k,json.dumps(data.get(k) or {},ensure_ascii=False))
            p=data.get("profile") or {}
            if p.get("label"): save_setting("profile_label",p["label"])
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
        ts_dir=Path.home()/"Documents"/"OREZONE_QHSE"/"timesheets"
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
        nb=ft.NavigationBar(selected_index=0,bgcolor=CARD,indicator_color=f"{BLUE}18",
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME_ROUNDED,label="Accueil"),
                ft.NavigationBarDestination(icon=ft.Icons.HANDYMAN_OUTLINED,
                    selected_icon=ft.Icons.HANDYMAN_ROUNDED,label="Maintenance"),
                ft.NavigationBarDestination(icon=ft.Icons.RECORD_VOICE_OVER_OUTLINED,
                    selected_icon=ft.Icons.RECORD_VOICE_OVER_ROUNDED,label="Toolbox"),
                ft.NavigationBarDestination(icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                    selected_icon=ft.Icons.NOTIFICATIONS_ROUNDED,label="Alertes"),
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
        busy(True)
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
            }
            data=post_json(f"{addr}/api/mobile/sync",get_setting("token") or srv_token.value,payload)
            acc=data.get("accepted") or {}
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
            if not topic: raise ValueError("Aucune donnée Toolbox.")
            with get_mobile_connection() as c:
                c.execute("INSERT INTO pending_toolbox(date_theme,theme,facilitator,"
                    "site_id,attendees_count,comments) VALUES(?,?,?,?,?,?)",
                    (today,topic["theme"],topic["facilitator"],topic["site_id"],
                     ST.get("attendees",0),tb_cmt.value))
            notify("Toolbox confirmé offline.",OK); _refresh_all()
        except Exception as exc: notify(str(exc),DNG)

    def save_mi(e=None):
        try:
            equip=str(mi_eq.value or "").strip(); obs=str(mi_obs.value or "").strip()
            if not equip: raise ValueError("Sélectionnez un équipement.")
            if not obs: raise ValueError("La description est obligatoire.")
            prio=mi_prio.value or "moyenne"
            def do_save(_=None):
                with get_mobile_connection() as c:
                    c.execute("INSERT INTO pending_maintenance(observation_date,equipment_label,"
                        "site_id,priority,observation) VALUES(?,?,NULL,?,?)",
                        (mi_date.value,equip,prio,obs))
                mi_obs.value=""; notify("Intervention enregistrée offline.",OK)
                _refresh_all(); go_to("maintenance")
            confirm("Confirmer l'intervention",
                    f"Créer une intervention priorité « {prio.title()} » sur {equip} ?",
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
            if not str(inc_desc.value or "").strip(): raise ValueError("Description obligatoire.")
            if not str(inc_lieu.value or "").strip(): raise ValueError("Lieu obligatoire.")
            eid=inc_emp.value; enm=""
            if eid:
                emp=get_employee(int(eid)); enm=employee_name(emp) if emp else ""
            save_pending_incident({"type_evenement":ST["inc_type"],"date_heure":inc_date.value,
                "lieu":inc_lieu.value,"description":inc_desc.value,"gravite":ST["inc_grav"],
                "employe_name":enm,"employe_id":int(eid) if eid else None,
                "action_immediate":inc_act.value})
            inc_desc.value=""; inc_lieu.value=""; inc_act.value=""
            notify("Incident enregistré offline.",OK); go_to("alerts")
        except Exception as exc: notify(str(exc),DNG)

    def save_ppe(e=None):
        try:
            eid=ppe_emp.value
            if not eid: raise ValueError("Sélectionne un employé.")
            emp=get_employee(int(eid)); enm=employee_name(emp) if emp else ""
            res=dict(ST["ppe"])
            statut="non_conforme" if any(v=="nok" for v in res.values()) else "conforme"
            save_pending_ppe_check({"check_date":date.today().isoformat(),"employe_name":enm,
                "employe_id":int(eid),"resultats":res,"statut_global":statut,
                "observations":ppe_obs.value})
            ppe_emp.value=None; ppe_obs.value=""
            ST["ppe"]={lbl:"na" for lbl,_ in PPE_ITEMS}; _rebuild_ppe()
            notify(f"EPI {statut.replace('_',' ')}.",OK); go_to("profile")
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
        eq=str(dash.get("equipment_active") or "–")
        iv=str(dash.get("interventions_open") or "–")
        rt=str(dash.get("en_retard") or "–")
        al=str(dash.get("alertes_ouvertes") or "–")
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
            border=ft.border.all(1,BRD),padding=P(12,14,12,14),
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
                border=ft.border.all(1,f"{BLUE}30"),border_radius=16,padding=P(14,14,14,14),
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
                border=ft.border.all(1,f"{OK}33"),
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
                            ft.Container(bgcolor=f"{DNG}18",border_radius=8,padding=P(12,6,12,6),
                                ink=True,on_click=lambda e:_cnt(-1),
                                content=ft.Icon(ft.Icons.REMOVE,color=DNG,size=18)),
                            ft.Container(bgcolor=f"{OK}18",border_radius=8,padding=P(12,6,12,6),
                                ink=True,on_click=lambda e:_cnt(1),
                                content=ft.Icon(ft.Icons.ADD,color=OK,size=18)),
                        ],spacing=8,alignment=ft.MainAxisAlignment.CENTER)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=4,tight=True)),
                    ft.Container(width=1,height=70,bgcolor=BRD),
                    ft.Container(expand=True,content=ft.Column([
                        ft.Text("Taux présence",size=11,color=MUT,text_align=ft.TextAlign.CENTER),
                        ft.Text("92%",size=32,weight=ft.FontWeight.BOLD,color=OK,
                                text_align=ft.TextAlign.CENTER),
                        ft.ProgressBar(value=0.92,color=OK,bgcolor=f"{OK}22",height=6)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=4,tight=True)),
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
            ft.Container(bgcolor=f"{OK}0C",border_radius=14,padding=P(20,20,20,20),
                border=ft.border.all(1,f"{OK}33"),
                content=ft.Row([_box(ft.Icons.NOTIFICATIONS_NONE_OUTLINED,OK,36,18),
                    ft.Text("Aucune alerte dans cette catégorie.",size=13,color=OK,expand=True)],spacing=10))])
        try: al_col.update()
        except Exception: pass

    def _r_ppe(): ep_col.controls=[_ppe_row(nm,ic,cl) for nm,ic,cl in PPE_CATALOGUE]

    def _r_profile():
        srv=bool(get_setting("server_url") and get_setting("token")); tot=total_pending()
        pr_col.controls=[
            _tile("Paramètres serveur",ft.Icons.SETTINGS_ETHERNET_OUTLINED,
                  "Configuré" if srv else "Non configuré",BLUE if srv else DNG,
                  lambda e:go_to("settings")),
            _tile(f"Sync ({tot} en attente)" if tot else "Synchronisation",ft.Icons.CLOUD_SYNC_OUTLINED,
                  (f"{tot} élément(s) — cliquer pour envoyer" if tot
                   else ("Sync auto active — " + (cj("last_sync").get("at","?")[:16].replace("T"," ") if cj("last_sync") else "jamais synchronisé"))),
                  WARN if tot else OK,do_sync),
            _tile("Pointage",ft.Icons.HOW_TO_REG_OUTLINED,"Enregistrer une présence",OK,
                  lambda e:go_to("attendance")),
            _tile("Vérification EPI",ft.Icons.SAFETY_CHECK_OUTLINED,
                  "Contrôler un employé sur le terrain",INFO,lambda e:go_to("ppe_check")),
            _tile("Déclarer un incident",ft.Icons.WARNING_AMBER_OUTLINED,
                  "Accident / Presqu'accident / Observation",DNG,lambda e:go_to("incident")),
            _div(),
            _tile("Déconnexion",ft.Icons.LOGOUT_OUTLINED,"",DNG,do_logout,red=True)]

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
        return ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(5,"08"),
            content=ft.Row([
                ft.Container(width=5,bgcolor=color,border_radius=14),
                ft.Container(expand=True,padding=P(12,12,14,12),
                    content=ft.Row([_box(ico,color,38,18),
                        ft.Column([ft.Text(str(a.get("source") or "Alerte"),size=13,
                                weight=ft.FontWeight.BOLD,color=TXT),
                            ft.Text(str(a.get("message") or "—"),size=11,color=MUT,
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
        return ft.Container(bgcolor="#0A1929",expand=True,padding=P(20,0,20,0),
            content=ft.Column([
                ft.Container(height=40),
                ft.Row([ft.Container(width=88,height=88,border_radius=22,bgcolor="#F59E0B",
                    alignment=AL(0,0),shadow=SH(12,"30"),
                    content=ft.Text("O",size=42,weight=ft.FontWeight.BOLD,color="#FFFFFF"))],
                    alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=6),
                ft.Row([ft.Text("OREZONE QHSE",size=26,weight=ft.FontWeight.BOLD,color="#E2E8F0")],
                    alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([ft.Text("Plateforme QHSE — SYAMA Mining",size=12,color="#475569")],
                    alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=16),
                ft.Container(bgcolor="#132337",border_radius=18,
                    border=ft.border.all(1,"#1E3A5F"),padding=P(20,18,20,18),shadow=SH(16,"22"),
                    content=ft.Column([
                        ft.Text("Identifiants",size=14,weight=ft.FontWeight.BOLD,color="#E2E8F0"),
                        ft.Container(height=4),lgn_user,lgn_pass,
                        ft.Row([lgn_rem,ft.Text("Se souvenir de moi",color="#64748B",size=12)],spacing=6),
                        lgn_status,ft.Container(height=4),
                        ft.Container(bgcolor=BLUE,border_radius=12,height=50,
                            ink=True,on_click=do_login,alignment=AL(0,0),shadow=SH(8,"30"),
                            content=ft.Row([ft.Icon(ft.Icons.LOGIN_OUTLINED,color="#FFFFFF",size=20),
                                ft.Text("Se connecter",color="#FFFFFF",size=15,weight=ft.FontWeight.BOLD)],
                                alignment=ft.MainAxisAlignment.CENTER,spacing=8,tight=True)),
                        ft.Container(
                            bgcolor="#1E3A5F",border_radius=12,height=44,
                            ink=True,on_click=show_pairing_dialog,alignment=AL(0,0),
                            border=ft.border.all(1,"#2563EB55"),
                            content=ft.Row([ft.Icon(ft.Icons.LINK_ROUNDED,color="#93C5FD",size=18),
                                ft.Text("Appairage automatique PC → Mobile",color="#93C5FD",size=13,weight=ft.FontWeight.W_600)],
                                alignment=ft.MainAxisAlignment.CENTER,spacing=8,tight=True)),
                        ft.Container(alignment=AL(0,0),ink=True,on_click=_offline,padding=P(0,6,0,0),
                            content=ft.Text("Mode hors connexion →",size=12,color="#64748B",
                                            text_align=ft.TextAlign.CENTER)),
                    ],spacing=10,tight=True)),
                ft.Container(height=10),
                ft.Container(bgcolor="#132337",border_radius=18,
                    border=ft.border.all(1,"#1E3A5F"),padding=P(20,18,20,18),
                    content=ft.Column([
                        ft.Text("Configuration serveur",size=14,weight=ft.FontWeight.BOLD,color="#E2E8F0"),
                        ft.Container(height=4),srv_url,srv_token,srv_device],spacing=10,tight=True)),
                ft.Container(height=16),
                ft.Row([ft.Text("SYAMA  •  OREZONE Mining  •  v 2.0.0",size=11,color="#334155")],
                    alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=24),
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
            return ft.Container(border_radius=10,margin=ft.margin.symmetric(horizontal=8,vertical=1),
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
                        ft.Container(bgcolor="#FFFFFF20",border_radius=28,padding=ft.padding.all(2),
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
                    ft.Container(bgcolor="#FFFFFF12",border_radius=10,padding=P(10,6,10,6),
                        content=ft.Row([
                            ft.Container(width=8,height=8,bgcolor=OK if online else DNG,border_radius=4),
                            ft.Text(f"{'Connecté' if online else 'Hors-ligne'} · {tot} en attente",
                                    size=11,color="#93C5FD",expand=True),
                        ],spacing=8)),
                ],spacing=0,tight=True)),
            ft.Container(expand=True,
                content=ft.Column([
                    _nav_grp("TABLEAU DE BORD"),
                    _nav_item("Accueil",ft.Icons.HOME_ROUNDED,"#60A5FA","home"),
                    _nav_grp("MAINTENANCE"),
                    _nav_item("Interventions",ft.Icons.BUILD_ROUNDED,BLUE,"intervention"),
                    _nav_item("Inspections",ft.Icons.FACT_CHECK_ROUNDED,INFO,"inspection"),
                    _nav_item("Équipements",ft.Icons.HANDYMAN_OUTLINED,BLUE,"maintenance"),
                    _nav_grp("SÉCURITÉ"),
                    _nav_item("Pointage terrain",ft.Icons.HOW_TO_REG_ROUNDED,OK,"attendance"),
                    _nav_item("Vérification EPI",ft.Icons.SAFETY_CHECK_OUTLINED,WARN,"ppe_check"),
                    _nav_item("Dotation EPI",ft.Icons.ASSIGNMENT_TURNED_IN_ROUNDED,OK,"ppe_assign"),
                    _nav_item("Incidents",ft.Icons.WARNING_ROUNDED,DNG,"incident"),
                    _nav_item("Alertes",ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,DNG,"alerts"),
                    _nav_grp("FORMATION"),
                    _nav_item("Toolbox Talk",ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP,"toolbox"),
                    _nav_grp("DOCUMENTS"),
                    _nav_item("Timesheets & Exports",ft.Icons.ARTICLE_OUTLINED,BLUE,"timesheet"),
                    _nav_grp("COMPTE"),
                    _nav_item("Mon profil",ft.Icons.MANAGE_ACCOUNTS_OUTLINED,INFO,"profile"),
                    _nav_item("Paramètres",ft.Icons.SETTINGS_OUTLINED,MUT,"settings"),
                ],spacing=0,scroll=ft.ScrollMode.AUTO)),
            ft.Container(padding=P(16,8,16,12),
                content=ft.Text("OREZONE QHSE Mobile · v2.0",size=10,color="#2D4A6F",
                                text_align=ft.TextAlign.CENTER)),
        ],spacing=0,expand=True)

        # ── Dashboard KPI data ────────────────────────────────────────────────
        dsh=cj("dashboard")
        eq  =str(dsh.get("equipment_active") or "—")
        iv  =str(dsh.get("interventions_open") or "—")
        rt  =str(dsh.get("en_retard") or "—")
        al  =str(dsh.get("alertes_ouvertes") or "—")

        # ── KPI card ──────────────────────────────────────────────────────────
        def _kpi(val,lbl,color,icon,on_click=None):
            return ft.Container(expand=True,bgcolor=CARD,border_radius=18,
                shadow=SH(6,"10"),border=ft.border.all(1,f"{color}18"),
                ink=bool(on_click),on_click=on_click,
                padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Row([
                        ft.Container(bgcolor=f"{color}18",border_radius=12,width=36,height=36,
                            alignment=AL(0,0),
                            content=ft.Icon(icon,color=color,size=18)),
                        ft.Container(expand=True),
                        ft.Container(width=8,height=8,bgcolor=color,border_radius=4,
                            opacity=0.7),
                    ],spacing=4),
                    ft.Container(height=8),
                    ft.Text(val,size=28,weight=ft.FontWeight.BOLD,color=color),
                    ft.Text(lbl,size=10,color=MUT,weight=ft.FontWeight.W_500),
                ],spacing=0,tight=True))

        # ── Module tile (2-col grid) ───────────────────────────────────────────
        def _mod(label,sub,icon,color,key):
            def click(e): go_to(key)
            return ft.Container(expand=True,bgcolor=CARD,border_radius=16,
                shadow=SH(4,"08"),border=ft.border.all(1,f"{color}18"),
                ink=True,on_click=click,padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Container(bgcolor=f"{color}15",border_radius=12,width=44,height=44,
                        alignment=AL(0,0),
                        content=ft.Icon(icon,color=color,size=22)),
                    ft.Container(height=8),
                    ft.Text(label,size=13,weight=ft.FontWeight.W_700,color=TXT,
                            max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(sub,size=10,color=MUT,max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ],spacing=2,tight=True))

        # ── Alert card ─────────────────────────────────────────────────────────
        def _ac_alert(a):
            niv=str(a.get("niveau","") or "").lower()
            c=DNG if niv in ("critique","haut") else WARN if niv=="moyen" else INFO
            return ft.Container(bgcolor=CARD,border_radius=14,
                border=ft.border.all(1,f"{c}25"),padding=P(12,10,12,10),
                content=ft.Row([
                    ft.Container(width=4,height=36,bgcolor=c,border_radius=3),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(str(a.get("titre","Alerte") or "Alerte"),size=12,
                                weight=ft.FontWeight.W_600,color=TXT,
                                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(a.get("description","") or "")[:60],
                                size=10,color=MUT,max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ],spacing=2,expand=True),
                    ft.Container(bgcolor=f"{c}15",border_radius=8,padding=P(6,3,6,3),
                        content=ft.Text(niv.upper() or "?",size=9,color=c,
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
                        ft.Container(width=38,height=38,border_radius=12,bgcolor="#FFFFFF18",
                            alignment=AL(0,0),ink=True,on_click=open_drawer,
                            content=ft.Icon(ft.Icons.MENU_ROUNDED,color="#FFFFFF",size=21)),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Text("OREZONE QHSE",size=15,weight=ft.FontWeight.W_800,
                                    color="#FFFFFF"),
                            ft.Text("SYAMA Mining",size=10,color="#93C5FD"),
                        ],spacing=0,expand=True),
                        # Status dot
                        ft.Container(bgcolor="#FFFFFF18",border_radius=20,
                            padding=P(8,6,8,6),
                            content=ft.Row([
                                ft.Container(width=6,height=6,bgcolor=OK if online else DNG,
                                    border_radius=3),
                                ft.Text("Online" if online else "Offline",
                                        size=10,color="#FFFFFF",weight=ft.FontWeight.W_600),
                            ],spacing=5,tight=True)),
                        ft.Container(width=6),
                        ft.Container(width=36,height=36,border_radius=18,bgcolor="#FFFFFF1A",
                            alignment=AL(0,0),ink=True,on_click=lambda e:go_to("alerts"),
                            content=ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED,color="#FFFFFF",size=18)),
                        ft.Container(width=6),
                        ft.Container(ink=True,border_radius=20,on_click=lambda e:go_to("profile"),
                            content=_ava(inits,36)),
                    ],spacing=4),
                    ft.Container(height=14),
                    # User greeting block
                    ft.Container(bgcolor="#FFFFFF10",border_radius=16,padding=P(14,12,14,12),
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
                                bgcolor="#FFFFFF18",border_radius=14,
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
                        margin=ft.margin.only(top=8),
                        content=ft.Container(bgcolor="#FFFBEB",border_radius=10,
                            padding=P(10,7,10,7),
                            content=ft.Row([
                                ft.Icon(ft.Icons.CLOUD_UPLOAD_ROUNDED,color=WARN,size=15),
                                ft.Text(f"{tot} élément(s) en attente de synchronisation",
                                        size=11,color="#92400E",expand=True),
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

                    # ── MODULES GRID ─────────────────────────────────────────
                    ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(4,"08"),
                        border=ft.border.all(1,BRD),padding=P(14,12,14,14),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.GRID_VIEW_ROUNDED,color=BLUE,size=14),
                                ft.Text("Modules",size=12,weight=ft.FontWeight.W_700,
                                        color=BLUE,expand=True),
                                ft.Container(bgcolor=f"{BLUE}10",border_radius=8,
                                    padding=P(6,3,6,3),ink=True,
                                    on_click=lambda e:go_to("attendance"),
                                    content=ft.Text("Tout voir",size=10,color=BLUE,
                                                    weight=ft.FontWeight.W_600)),
                            ],spacing=8),
                            ft.Container(height=10),
                            ft.Row([
                                _mod("Pointage","Présence terrain",
                                     ft.Icons.HOW_TO_REG_ROUNDED,OK,"attendance"),
                                ft.Container(width=10),
                                _mod("Intervention","Maintenance corrective",
                                     ft.Icons.BUILD_ROUNDED,BLUE,"intervention"),
                            ],spacing=0),
                            ft.Container(height=10),
                            ft.Row([
                                _mod("EPI","Vérification & dotation",
                                     ft.Icons.SAFETY_CHECK_ROUNDED,WARN,"ppe_check"),
                                ft.Container(width=10),
                                _mod("Toolbox","Causerie sécurité",
                                     ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP,"toolbox"),
                            ],spacing=0),
                            ft.Container(height=10),
                            ft.Row([
                                _mod("Incident","Déclarer un événement",
                                     ft.Icons.WARNING_ROUNDED,DNG,"incident"),
                                ft.Container(width=10),
                                _mod("Timesheets","Télécharger & exporter",
                                     ft.Icons.ARTICLE_OUTLINED,INFO,"timesheet"),
                            ],spacing=0),
                        ],spacing=0,tight=True)),

                    # ── ALERTES CRITIQUES ─────────────────────────────────────
                    ft.Row([
                        ft.Icon(ft.Icons.PRIORITY_HIGH_ROUNDED,color=DNG,size=14),
                        ft.Text("Alertes critiques",size=12,weight=ft.FontWeight.W_700,
                                color=DNG,expand=True),
                        ft.Container(bgcolor=f"{DNG}10",border_radius=8,padding=P(6,3,6,3),
                            ink=True,on_click=lambda e:go_to("alerts"),
                            content=ft.Text("Voir tout",size=10,color=DNG,
                                            weight=ft.FontWeight.W_600)),
                    ],spacing=8),
                    *(
                        [_ac_alert(a) for a in crit] or [
                            ft.Container(bgcolor=f"{OK}08",border_radius=14,
                                border=ft.border.all(1,f"{OK}25"),padding=P(14,12,14,12),
                                content=ft.Row([
                                    ft.Container(bgcolor=f"{OK}18",border_radius=10,
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

    def _s_maint():
        items=list_maintenance_cache()
        n_ret=sum(1 for i in items if str(i["status"]or"").lower() in ("en_retard","overdue","retard"))
        n_sur=sum(1 for i in items if str(i["status"]or"").lower() in ("a_surveiller","warning","bientot"))
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Stack([
                ft.Column([
                    ft.Container(gradient=GRAD,padding=P(16,18,16,22),shadow=SH(10,"20"),
                        content=ft.Column([
                            ft.Row([_box(ft.Icons.HANDYMAN_OUTLINED,"#FFFFFF",26,16),
                                ft.Text("Maintenance",size=18,weight=ft.FontWeight.BOLD,color="#FFFFFF",expand=True),
                                ft.Container(width=36,height=36,border_radius=18,bgcolor="#FFFFFF22",
                                    alignment=AL(0,0),ink=True,
                                    on_click=lambda e:[_r_maint(),page.update()],
                                    content=ft.Icon(ft.Icons.REFRESH_OUTLINED,color="#FFFFFF",size=18))],spacing=8),
                            ft.Container(height=10),
                            ft.Row([_mstat(str(len(items)),"Équipements"),
                                ft.Container(width=1,height=28,bgcolor="#FFFFFF33"),
                                _mstat(str(n_ret),"En retard","#FFCCCC"),
                                ft.Container(width=1,height=28,bgcolor="#FFFFFF33"),
                                _mstat(str(n_sur),"À surveiller","#FDE68A")],spacing=0)],
                            spacing=0,tight=True)),
                    ft.Container(expand=True,padding=P(12,12,12,12),
                        content=ft.Column([m_search,m_col,ft.Container(height=80)],
                            spacing=10,scroll=ft.ScrollMode.AUTO,expand=True))],spacing=0,expand=True),
                ft.Container(right=16,bottom=24,
                    content=ft.Container(bgcolor=BLUE,border_radius=16,shadow=SH(12,"30"),
                        padding=P(16,14,16,14),ink=True,on_click=lambda e:go_to("intervention"),
                        content=ft.Row([ft.Icon(ft.Icons.ADD,color="#FFFFFF",size=20),
                            ft.Text("Nouvelle intervention",color="#FFFFFF",size=13,weight=ft.FontWeight.W_600)],
                            spacing=8,tight=True)))]))

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
                    border=ft.border.all(1.5 if active else 1,c if active else BRD),
                    ink=True,on_click=click,padding=P(8,10,8,10),
                    content=ft.Column([
                        ft.Container(bgcolor="#FFFFFF25" if active else f"{c}18",
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
                    border=ft.border.all(1.5 if active else 1,c if active else BRD),
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
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#FFFFFF18",
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
                            ft.Text("Maintenance terrain · SYAMA",size=11,color="#93C5FD"),
                        ],spacing=6),
                    ],spacing=0,tight=True)),
                # ── Scrollable body ────────────────────────────────────────────
                ft.Container(expand=True,padding=P(12,14,12,0),
                    content=ft.Column([
                        # ── Équipement ─────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"{BLUE}18",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.HANDYMAN_OUTLINED,color=BLUE,size=17)),
                                    ft.Text("Équipement",size=14,weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                mi_eq,
                            ],spacing=12)),
                        # ── Type d'intervention ────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"{PURP}18",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.CATEGORY_OUTLINED,color=PURP,size=17)),
                                    ft.Text("Type d'intervention",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                type_row,
                            ],spacing=12)),
                        # ── Priorité ───────────────────────────────────────────
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"{WARN}18",border_radius=10,
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
                            border=ft.border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"{INFO}18",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED,color=INFO,size=17)),
                                    ft.Text("Description & Observations",size=14,
                                            weight=ft.FontWeight.BOLD,color=TXT),
                                ],spacing=10),
                                mi_obs,
                            ],spacing=12)),
                        # ── Photo / Signature ──────────────────────────────────
                        ft.Row([
                            ft.Container(bgcolor=f"{INFO}10",border_radius=14,
                                border=ft.border.all(1,f"{INFO}44"),expand=True,height=48,
                                ink=True,alignment=AL(0,0),
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED,color=INFO,size=18),
                                    ft.Text("Photo",color=INFO,size=12,weight=ft.FontWeight.W_700),
                                ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                            ft.Container(bgcolor=f"{PURP}10",border_radius=14,
                                border=ft.border.all(1,f"{PURP}44"),expand=True,height=48,
                                ink=True,alignment=AL(0,0),
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
                                ft.Text("Enregistrer l'intervention",color="#FFFFFF",
                                        size=14,weight=ft.FontWeight.W_700),
                            ],alignment=ft.MainAxisAlignment.CENTER,spacing=8)),
                        ft.Container(height=80),
                    ],spacing=10,scroll=ft.ScrollMode.AUTO,expand=True)),
            ],spacing=0))

    def _s_inspect():
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([_hdr("Inspection véhicule","maintenance"),
                _body(ins_eq,_sec("Checklist",ft.Icons.CHECKLIST_OUTLINED,sum(ins_chk.values())),
                    ins_col,
                    ft.Container(bgcolor=f"{INFO}18",border_radius=12,
                        border=ft.border.all(1,f"{INFO}44"),height=46,ink=True,alignment=AL(0,0),
                        content=ft.Row([ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED,color=INFO,size=18),
                            ft.Text("Ajouter une photo",color=INFO,size=13,weight=ft.FontWeight.W_600)],
                            alignment=ft.MainAxisAlignment.CENTER,spacing=8,tight=True)),
                    ins_sign,_btn("Valider l'inspection",ft.Icons.CHECK_CIRCLE_OUTLINED,OK,save_ins))],spacing=0))

    def _s_toolbox():
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
        tab=ST.get("alerts_tab","all"); all_a=cj("alerts",[])
        if not isinstance(all_a,list): all_a=[]
        counts={"all":len(all_a),
                "critique":sum(1 for a in all_a if a.get("niveau") in {"critique","haut"}),
                "urgent":  sum(1 for a in all_a if a.get("niveau") in {"urgent","moyen"}),
                "info":    sum(1 for a in all_a if a.get("niveau") in {"info","bas"})}
        tabs=[("all","Toutes",BLUE),("critique","Critiques",DNG),("urgent","Urgentes",WARN),("info","Info",INFO)]
        def _pill(k,lbl,c):
            active=tab==k
            return ft.Container(bgcolor=c if active else "#F1F5F9",border_radius=20,
                padding=P(12,7,12,7),ink=True,
                on_click=lambda e,kk=k:[ST.__setitem__("alerts_tab",kk),_r_alerts(),go_to("alerts")],
                content=ft.Row([ft.Text(lbl,size=12,weight=ft.FontWeight.W_600,
                    color="#FFFFFF" if active else MUT),
                    ft.Container(bgcolor="#FFFFFF44" if active else f"{c}22",border_radius=10,
                        padding=P(5,1,5,1),content=ft.Text(str(counts[k]),size=10,
                        weight=ft.FontWeight.BOLD,color="#FFFFFF" if active else c))],
                    spacing=5,tight=True))
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(16,18,16,22),shadow=SH(10,"20"),
                    content=ft.Column([
                        ft.Row([_box(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,"#FFFFFF",26,16),
                            ft.Text("Alertes",size=18,weight=ft.FontWeight.BOLD,color="#FFFFFF",expand=True),
                            _badge(str(counts["all"]),"#FFFFFF","#FFFFFF30")],spacing=8),
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
        uname=get_setting("identity_username") or "—"
        urole=get_setting("profile_label") or "Terrain"
        site=cj("dashboard",{}).get("site") or "SYAMA"
        tot=total_pending(); srv=bool(get_setting("server_url") and get_setting("token"))
        inits="".join(w[0].upper() for w in uname.split() if w)[:2] or "?"
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(20,28,20,28),shadow=SH(12,"22"),
                    content=ft.Column([
                        ft.Row([_ava(inits,64),ft.Container(width=16),
                            ft.Column([ft.Text(uname.upper(),size=17,weight=ft.FontWeight.BOLD,color="#FFFFFF"),
                                ft.Container(bgcolor="#FFFFFF22",border_radius=12,padding=P(10,3,10,3),
                                    content=ft.Text(urole,size=11,color="#FFFFFF",weight=ft.FontWeight.W_600)),
                                ft.Row([ft.Icon(ft.Icons.LOCATION_ON_OUTLINED,color="#93C5FD",size=13),
                                    ft.Text(site,size=12,color="#93C5FD")],spacing=4)],
                                spacing=6,expand=True)],spacing=0),
                        ft.Container(height=16),
                        ft.Container(bgcolor="#FFFFFF12",border_radius=14,padding=P(0,8,0,8),
                            content=ft.Row([_mstat(str(tot) if tot else "0","En attente"),
                                ft.Container(width=1,height=30,bgcolor="#FFFFFF33"),
                                _mstat("✓" if srv else "✗","Serveur"),
                                ft.Container(width=1,height=30,bgcolor="#FFFFFF33"),
                                _mstat("HSE","Rôle")],spacing=0))],spacing=0,tight=True)),
                ft.Container(expand=True,padding=P(12,14,12,12),
                    content=ft.Column([_sec("Mon compte",ft.Icons.MANAGE_ACCOUNTS_OUTLINED),
                        pr_col,ft.Container(height=70)],
                        scroll=ft.ScrollMode.AUTO,expand=True,spacing=10))],spacing=0))

    def _s_ppe_assign():
        SEL={lbl:False for lbl,_ in PPE_ITEMS}
        chk_col=ft.Column(spacing=8)

        def rebuild_list():
            def _item(lbl,ico):
                sel=SEL[lbl]
                def tog(e,k=lbl):
                    SEL[k]=not SEL[k]; rebuild_list()
                c=OK if sel else MUT
                return ft.Container(bgcolor=f"{c}0A" if sel else CARD,
                    border_radius=14,padding=P(14,12,14,12),
                    border=ft.border.all(1.5 if sel else 1, f"{c}44" if sel else BRD),
                    ink=True,on_click=tog,
                    content=ft.Row([
                        ft.Container(bgcolor=f"{c}18",border_radius=10,
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
        n_sel_txt=ft.Text("0 article(s) sélectionné(s)",size=12,color=MUT)

        def _on_save(e=None):
            n=sum(1 for v in SEL.values() if v)
            n_sel_txt.value=f"{n} article(s) sélectionné(s)"
            try: n_sel_txt.update()
            except Exception: pass
            save_ppe_assign(SEL,e)

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([
                ft.Container(gradient=GRAD,padding=P(16,16,16,18),shadow=SH(12,"22"),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#FFFFFF18",
                                alignment=AL(0,0),ink=True,on_click=lambda e:go_to("home"),
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
                            border=ft.border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"{BLUE}18",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.PERSON_OUTLINED,color=BLUE,size=17)),
                                    ft.Text("Bénéficiaire",size=14,weight=ft.FontWeight.BOLD,color=TXT,expand=True),
                                ],spacing=10),
                                ppa_emp,
                                ft.Row([ppa_tail],spacing=8),
                            ],spacing=12)),
                        # Section articles EPI
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"{OK}18",border_radius=10,
                                        width=34,height=34,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.SAFETY_CHECK_OUTLINED,color=OK,size=17)),
                                    ft.Text("Articles à remettre",size=14,weight=ft.FontWeight.BOLD,color=TXT,expand=True),
                                    n_sel_txt,
                                ],spacing=10),
                                chk_col,
                            ],spacing=12)),
                        # Observations
                        ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(5,"08"),
                            border=ft.border.all(1,BRD),padding=P(16,14,16,16),
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(bgcolor=f"{INFO}18",border_radius=10,
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
                                 border=ft.border.all(1,BRD),
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
                padding=P(8,3,8,3),border=ft.border.all(1,f"{c}40"),
                content=ft.Text(l,size=10,color=c,weight=ft.FontWeight.W_700))

        def _row(emp,is_sel,done_status=None):
            eid=emp["id_employe"]; nm=employee_name(emp)
            role=str(emp["fonction"] or "—"); site_s=str(emp["site"] or "")
            inits="".join(w[0].upper() for w in nm.split() if w)[:2] or "?"
            done=done_status is not None
            sc=SCOL.get(done_status,OK) if done else (BLUE if is_sel else MUT)
            bg="#EFF6FF" if is_sel else (f"{sc}08" if done else CARD)
            br=BLUE if is_sel else (f"{sc}40" if done else BRD)
            bw=1.5 if is_sel else 1
            def toggle(e,ei=eid):
                if ei in SEL: SEL.discard(ei)
                else: SEL.add(ei)
                rebuild()
            return ft.Container(bgcolor=bg,border_radius=14,
                border=ft.border.all(bw,br),padding=P(10,10,12,10),
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
                    bgcolor=c if active else "#F1F5F9",
                    border=ft.border.all(1.5,c if active else BRD),
                    ink=True,on_click=_click,
                    content=ft.Row([
                        ft.Icon(ico,color="#FFFFFF" if active else c,size=15),
                        ft.Text(lbl,size=11,weight=ft.FontWeight.W_700,
                                color="#FFFFFF" if active else MUT),
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
                        padding=P(12,10,14,10),border=ft.border.all(1,BRD),
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
                    rows.append(ft.Container(bgcolor=f"{OK}0A",border_radius=10,
                        padding=P(12,8,12,8),border=ft.border.all(1,f"{OK}30"),
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
                ft.Container(bgcolor=f"{BLUE}15",border_radius=8,width=30,height=30,
                    alignment=AL(0,0),
                    content=ft.Icon(ft.Icons.PEOPLE_ALT_OUTLINED,color=BLUE,size=16)),
                sel_lbl,
                ft.Container(border_radius=8,padding=P(8,5,8,5),
                    bgcolor=f"{DNG}12",border=ft.border.all(1,f"{DNG}30"),
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
                                    bgcolor="#FFFFFF18",alignment=AL(0,0),
                                    ink=True,on_click=lambda e:go_to("home"),
                                    content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,
                                                    color="#FFFFFF",size=17)),
                                ft.Text("Pointage terrain",size=17,weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF",expand=True,
                                        text_align=ft.TextAlign.CENTER),
                                ft.Container(width=36,height=36,border_radius=18,
                                    bgcolor="#FFFFFF18",alignment=AL(0,0),
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
                                ft.Container(bgcolor="#FFFFFF18",border_radius=12,
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

        MONTHS_FR=["Janvier","Février","Mars","Avril","Mai","Juin",
                   "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
        d=date.today()
        TS={"month":d.month,"year":d.year,"ts_type":"1_25"}

        def get_exports_dir():
            p=Path.home()/"Documents"/"OREZONE_QHSE"/"exports"
            p.mkdir(parents=True,exist_ok=True); return p
        def get_ts_dir():
            p=Path.home()/"Documents"/"OREZONE_QHSE"/"timesheets"
            p.mkdir(parents=True,exist_ok=True); return p
        def open_file(p):
            try: _os.startfile(str(p))
            except Exception: pass
        def month_prefix(): return f"{TS['year']}-{TS['month']:02d}"

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

        # widgets
        month_lbl = ft.Text("",size=18,weight=ft.FontWeight.BOLD,color=TXT,text_align=ft.TextAlign.CENTER)
        stats_row = ft.Row(spacing=8,expand=True)
        ts_list_col= ft.Column(spacing=10)
        tab_bar   = ft.Row(spacing=0)
        tab_idx   = [0]

        def _tab_btn(label,idx):
            def click(e,i=idx): tab_idx[0]=i; _rebuild_tabs(); rebuild()
            active=tab_idx[0]==idx
            return ft.Container(expand=True,
                border_radius=10,bgcolor=BLUE if active else f"{BLUE}12",
                padding=P(10,8,10,8),ink=True,on_click=click,
                content=ft.Text(label,size=12,color="#FFFFFF" if active else MUT,
                                weight=ft.FontWeight.W_600,text_align=ft.TextAlign.CENTER))

        def _rebuild_tabs():
            tab_bar.controls=[_tab_btn(l,i) for i,l in enumerate(["Timesheets","Pointages","Toolbox"])]
            try: tab_bar.update()
            except Exception: pass
        _rebuild_tabs()

        def _sec2(txt,ico):
            return ft.Row([ft.Icon(ico,color=BLUE,size=14),
                           ft.Text(txt,size=11,weight=ft.FontWeight.W_700,color=BLUE,expand=True)],spacing=6)

        def _chip(val,lbl,color):
            return ft.Container(expand=True,bgcolor=f"{color}10",border_radius=12,
                padding=P(10,8,10,8),border=ft.border.all(1,f"{color}25"),
                content=ft.Column([
                    ft.Text(val,size=20,weight=ft.FontWeight.BOLD,color=color,text_align=ft.TextAlign.CENTER),
                    ft.Text(lbl,size=9,color=MUT,text_align=ft.TextAlign.CENTER),
                ],spacing=2,horizontal_alignment=ft.CrossAxisAlignment.CENTER,tight=True))

        def _fmt_badge(fmt):
            c=OK if fmt=="xlsx" else DNG
            ico=ft.Icons.TABLE_VIEW_ROUNDED if fmt=="xlsx" else ft.Icons.PICTURE_AS_PDF_ROUNDED
            return ft.Container(bgcolor=f"{c}15",border_radius=8,padding=P(8,4,8,4),
                border=ft.border.all(1,f"{c}30"),
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
                border=ft.border.all(1,BRD if exists else f"{DNG}22"),padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Row([_fmt_badge(fmt),
                            ft.Container(expand=True,content=ft.Text(mlbl,size=13,weight=ft.FontWeight.BOLD,color=TXT)),
                            ft.Container(bgcolor=f"{OK}12" if exists else f"{DNG}12",border_radius=8,padding=P(6,3,6,3),
                                content=ft.Text("Disponible" if exists else "Manquant",
                                    size=10,color=OK if exists else DNG,weight=ft.FontWeight.W_600))],spacing=8),
                    ft.Container(height=4),
                    ft.Row([ft.Icon(ft.Icons.SCHEDULE_OUTLINED,color=MUT,size=12),
                            ft.Text(str(rec.get("downloaded_at",""))[:16],size=10,color=MUT,expand=True),
                            ft.Text(sz_lbl,size=10,color=MUT)],spacing=6),
                    ft.Container(height=6),
                    ft.Row([
                        ft.Container(expand=True,bgcolor=f"{BLUE}12",border_radius=10,
                            border=ft.border.all(1,f"{BLUE}25"),padding=P(10,8,10,8),
                            ink=True,on_click=_open if exists else None,
                            content=ft.Row([ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED,color=BLUE if exists else MUT,size=16),
                                ft.Text("Ouvrir",size=12,color=BLUE if exists else MUT,weight=ft.FontWeight.W_600)],
                                spacing=6,tight=True)),
                        ft.Container(width=8),
                        ft.Container(bgcolor=f"{DNG}10",border_radius=10,
                            border=ft.border.all(1,f"{DNG}20"),padding=P(10,8,10,8),ink=True,on_click=_del,
                            content=ft.Icon(ft.Icons.DELETE_OUTLINE_ROUNDED,color=DNG,size=18)),
                    ],spacing=0),
                ],spacing=0,tight=True))

        def _att_row(r):
            sc={"present":OK,"absent":DNG,"mission":PURP,"maladie":WARN,"conge":INFO}.get(r.get("status",""),MUT)
            h_txt=f"{r['heure_entree']} → {r['heure_sortie']}" if r.get("heure_entree") and r.get("heure_sortie") else r.get("heure_entree","")
            return ft.Container(bgcolor=CARD,border_radius=12,border=ft.border.all(1,BRD),padding=P(12,10,12,10),
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
            return ft.Container(bgcolor=CARD,border_radius=12,border=ft.border.all(1,f"{PURP}22"),padding=P(12,10,12,10),
                content=ft.Row([
                    ft.Container(bgcolor=f"{PURP}15",border_radius=8,width=36,height=36,alignment=AL(0,0),
                        content=ft.Icon(ft.Icons.RECORD_VOICE_OVER_ROUNDED,color=PURP,size=18)),
                    ft.Column([
                        ft.Text(str(r.get("theme","—") or "—"),size=12,weight=ft.FontWeight.W_600,color=TXT,
                                max_lines=2,overflow=ft.TextOverflow.ELLIPSIS,expand=True),
                        ft.Text(f"{r.get('date_theme','')} · {r.get('facilitator','') or '—'}",size=10,color=MUT),
                    ],spacing=2,expand=True),
                    ft.Container(bgcolor=f"{OK}15",border_radius=8,padding=P(8,4,8,4),
                        content=ft.Text(f"{r.get('attendees_count',0)} pers.",size=10,color=OK,weight=ft.FontWeight.W_700)),
                ],spacing=8))

        def _build_url(month, fmt, ts_type=None, emp_id=None):
            addr=get_setting("server_url") or ""
            t=ts_type or TS["ts_type"]
            u=f"{addr.rstrip('/')}/api/mobile/timesheet/export?month={month}&format={fmt}&type={t}"
            if emp_id: u+=f"&employee_id={emp_id}"
            return u

        def _download_ts(fmt, ts_type=None, emp_id=None, e=None):
            addr=get_setting("server_url") or ""; tk=get_setting("token") or ""
            if not addr: notify("Serveur non configuré.",DNG); return
            pfx=month_prefix(); t=ts_type or TS["ts_type"]
            period_lbl="01–25" if t=="1_25" else "21–20"
            emp_lbl=f" — Employé #{emp_id}" if emp_id else ""
            notify(f"Téléchargement {fmt.upper()} {period_lbl}{emp_lbl}…",MUT)
            try:
                data=request_bytes(_build_url(pfx,fmt,t,emp_id),tk,timeout=60)
                fname=f"timesheet_{pfx}_{t}"+(f"_emp{emp_id}" if emp_id else "")+f".{fmt}"
                fpath=get_ts_dir()/fname
                fpath.write_bytes(data)
                save_timesheet_record(f"{pfx}_{t}"+(f"_e{emp_id}" if emp_id else ""),fmt,str(fpath),len(data))
                rebuild(); notify(f"Téléchargé ({len(data)//1024} Ko) : {fname}",OK)
            except Exception as exc: notify(f"Erreur : {exc}",DNG)

        def _dl_all_months(e=None):
            addr=get_setting("server_url") or ""; tk=get_setting("token") or ""
            if not addr: notify("Serveur non configuré.",DNG); return
            notify("Téléchargement — 6 mois × 2 périodes × 2 formats…",MUT)
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
                            data=request_bytes(_build_url(m,fmt,t),tk,timeout=60)
                            fname=f"timesheet_{m}_{t}.{fmt}"
                            fpath=ts_dir/fname; fpath.write_bytes(data)
                            save_timesheet_record(f"{m}_{t}",fmt,str(fpath),len(data)); ok+=1
                        except Exception: fail+=1
            rebuild(); notify(f"Terminé : {ok} fichiers OK, {fail} erreur(s)",OK if fail==0 else WARN)

        def _dl_individual(e=None):
            emps=list_employees()
            if not emps: notify("Aucun employé en cache. Synchronisez d'abord.",WARN); return
            addr=get_setting("server_url") or ""; tk=get_setting("token") or ""
            if not addr: notify("Serveur non configuré.",DNG); return
            pfx=month_prefix(); t=TS["ts_type"]; ok=0; fail=0
            notify(f"Téléchargement feuilles individuelles ({len(emps)} employés)…",MUT)
            ts_dir=get_ts_dir()
            for emp in emps:
                eid=emp.get("id_employe"); ename=(emp.get("nom","")+" "+emp.get("prenom","")).strip() or f"emp{eid}"
                try:
                    data=request_bytes(_build_url(pfx,"pdf",t,eid),tk,timeout=30)
                    safe=ename.replace(" ","_").replace("/","_")[:40]
                    fpath=ts_dir/f"ts_{pfx}_{t}_{safe}.pdf"
                    fpath.write_bytes(data)
                    save_timesheet_record(f"{pfx}_{t}_e{eid}","pdf",str(fpath),len(data)); ok+=1
                except Exception: fail+=1
            rebuild(); notify(f"Feuilles individuelles : {ok} OK, {fail} erreur(s)",OK if fail==0 else WARN)

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

        def _export_att_pdf(e=None):
            try:
                from reportlab.lib import colors as rlc
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                recs=get_att(); pfx=month_prefix()
                if not recs: notify("Aucun pointage pour ce mois.",WARN); return
                out=get_exports_dir()/f"pointage_{pfx}.pdf"
                doc=SimpleDocTemplate(str(out),pagesize=landscape(A4),leftMargin=15,rightMargin=15,topMargin=20,bottomMargin=20)
                sty=getSampleStyleSheet()
                data=[["Employé","Date","Statut","Entrée","Sortie"]]
                for r in recs:
                    data.append([r.get("employee_name",""),r.get("date_presence",""),
                                 (r.get("status","") or "").title(),r.get("heure_entree","") or "—",r.get("heure_sortie","") or "—"])
                tbl=Table(data,colWidths=[200,80,70,60,60])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,0),rlc.HexColor("#1E3A5F")),("TEXTCOLOR",(0,0),(-1,0),rlc.white),
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[rlc.white,rlc.HexColor("#F0F4F8")]),
                    ("GRID",(0,0),(-1,-1),0.3,rlc.HexColor("#CBD5E1")),
                    ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ]))
                doc.build([Paragraph(f"<b>Pointage — {MONTHS_FR[TS['month']-1]} {TS['year']} | OREZONE QHSE</b>",sty["Title"]),Spacer(1,12),tbl])
                open_file(out); notify(f"PDF exporté : {out.name}",OK)
            except Exception as exc: notify(f"Erreur PDF : {exc}",DNG)

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

        def _export_csv(e=None):
            try:
                recs=get_att(); pfx=month_prefix()
                out=get_exports_dir()/f"pointage_{pfx}.csv"
                with open(out,"w",newline="",encoding="utf-8-sig") as f:
                    w=_csv.writer(f,delimiter=";")
                    w.writerow(["Employé","Date","Statut","Entrée","Sortie"])
                    for r in recs:
                        w.writerow([r.get("employee_name",""),r.get("date_presence",""),r.get("status",""),
                                    r.get("heure_entree","") or "",r.get("heure_sortie","") or ""])
                open_file(out); notify(f"CSV exporté ({len(recs)} lignes)",OK)
            except Exception as exc: notify(f"Erreur CSV : {exc}",DNG)

        def prev_m(e=None):
            m=TS["month"]-1
            if m<1: m=12; TS["year"]-=1
            TS["month"]=m; rebuild()
        def next_m(e=None):
            m=TS["month"]+1
            if m>12: m=1; TS["year"]+=1
            TS["month"]=m; rebuild()

        def rebuild():
            pfx=month_prefix(); mlbl=f"{MONTHS_FR[TS['month']-1]} {TS['year']}"
            month_lbl.value=mlbl
            recs=get_att()
            np2=sum(1 for r in recs if r.get("status")=="present")
            na=sum(1 for r in recs if r.get("status")=="absent")
            stats_row.controls=[_chip(str(len(recs)),"Total",BLUE),_chip(str(np2),"Présents",OK),
                                 _chip(str(na),"Absents",DNG),_chip(str(len(recs)-np2-na),"Autres",WARN)]
            if tab_idx[0]==0:
                all_saved=list_saved_timesheets()
                t=TS["ts_type"]; t_lbl="01 au 25" if t=="1_25" else "21 au 20"
                def _period_btn(key,lbl):
                    active=TS["ts_type"]==key
                    def click(e,k=key): TS["ts_type"]=k; rebuild()
                    return ft.Container(expand=True,bgcolor=BLUE if active else f"{BLUE}10",
                        border_radius=10,padding=P(10,8,10,8),ink=True,on_click=click,
                        border=ft.border.all(1,BLUE if active else f"{BLUE}30"),
                        content=ft.Text(lbl,size=12,color="#FFFFFF" if active else MUT,
                                        weight=ft.FontWeight.W_600,text_align=ft.TextAlign.CENTER))
                ts_list_col.controls=[
                    ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(5,"09"),
                        border=ft.border.all(1,f"{BLUE}20"),padding=P(14,14,14,14),
                        content=ft.Column([
                            _sec2(f"Télécharger — {mlbl}",ft.Icons.DOWNLOAD_ROUNDED),
                            ft.Container(height=6),
                            # Period selector
                            ft.Container(bgcolor=f"{BLUE}08",border_radius=10,padding=P(4,4,4,4),
                                content=ft.Row([
                                    _period_btn("1_25","Période 01–25"),
                                    ft.Container(width=6),
                                    _period_btn("21_20","Période 21–20"),
                                ],spacing=0)),
                            ft.Container(height=8),
                            ft.Text(f"Période sélectionnée : {t_lbl}",size=10,color=MUT),
                            ft.Container(height=6),
                            # Format buttons
                            ft.Row([
                                ft.Container(expand=True,bgcolor=f"{OK}12",border_radius=10,
                                    border=ft.border.all(1,f"{OK}30"),padding=P(12,10,12,10),ink=True,
                                    on_click=lambda e:_download_ts("xlsx"),
                                    content=ft.Column([
                                        ft.Row([ft.Icon(ft.Icons.TABLE_VIEW_ROUNDED,color=OK,size=20),
                                               ft.Text("Excel",size=12,weight=ft.FontWeight.W_700,color=OK)],spacing=6,tight=True),
                                        ft.Text("Tableau officiel 10H",size=10,color=MUT)],spacing=4,tight=True)),
                                ft.Container(width=10),
                                ft.Container(expand=True,bgcolor=f"{DNG}12",border_radius=10,
                                    border=ft.border.all(1,f"{DNG}30"),padding=P(12,10,12,10),ink=True,
                                    on_click=lambda e:_download_ts("pdf"),
                                    content=ft.Column([
                                        ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,color=DNG,size=20),
                                               ft.Text("PDF",size=12,weight=ft.FontWeight.W_700,color=DNG)],spacing=6,tight=True),
                                        ft.Text("Version imprimable",size=10,color=MUT)],spacing=4,tight=True)),
                            ],spacing=0),
                            ft.Container(height=8),
                            # Individual employee sheets
                            ft.Container(bgcolor=f"{PURP}10",border_radius=10,
                                border=ft.border.all(1,f"{PURP}30"),padding=P(12,10,12,10),ink=True,
                                on_click=_dl_individual,
                                content=ft.Row([ft.Icon(ft.Icons.PERSON_OUTLINED,color=PURP,size=20),
                                    ft.Column([
                                        ft.Text("Feuilles individuelles — PDF",size=12,weight=ft.FontWeight.W_700,color=PURP),
                                        ft.Text("Une feuille PDF par employé (tous les agents)",size=10,color=MUT),
                                    ],spacing=2,expand=True)],spacing=10)),
                            ft.Container(height=6),
                            # Bulk download
                            ft.Container(bgcolor=f"{INFO}10",border_radius=10,
                                border=ft.border.all(1,f"{INFO}30"),padding=P(12,10,12,10),ink=True,
                                on_click=_dl_all_months,
                                content=ft.Row([ft.Icon(ft.Icons.CLOUD_SYNC_ROUNDED,color=INFO,size=20),
                                    ft.Column([
                                        ft.Text("Tout télécharger — 6 mois × 2 périodes",size=12,weight=ft.FontWeight.W_700,color=INFO),
                                        ft.Text("XLSX + PDF · Hors-ligne complet",size=10,color=MUT),
                                    ],spacing=2,expand=True)],spacing=10)),
                        ],spacing=0,tight=True)),
                    ft.Container(height=4),
                    _sec2(f"Timesheets enregistrés ({len(all_saved)})",ft.Icons.FOLDER_OPEN_ROUNDED),
                ]+([_ts_card(r) for r in all_saved] or [
                    ft.Container(bgcolor=CARD,border_radius=14,padding=P(28,24,28,24),
                        content=ft.Column([ft.Icon(ft.Icons.INBOX_OUTLINED,color=BRD,size=48),
                            ft.Text("Aucun timesheet téléchargé",size=14,color=MUT,text_align=ft.TextAlign.CENTER),
                            ft.Text("Sélectionnez la période et cliquez Télécharger",size=11,color=MUT,text_align=ft.TextAlign.CENTER)],
                            spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER))])
            elif tab_idx[0]==1:
                ts_list_col.controls=[
                    ft.Container(bgcolor=CARD,border_radius=14,shadow=SH(5,"09"),
                        border=ft.border.all(1,f"{INFO}20"),padding=P(14,12,14,12),ink=True,on_click=_sync_month,
                        content=ft.Row([
                            ft.Container(bgcolor=f"{INFO}15",border_radius=10,width=40,height=40,alignment=AL(0,0),
                                content=ft.Icon(ft.Icons.SYNC_ROUNDED,color=INFO,size=20)),
                            ft.Column([ft.Text("Synchroniser ce mois",size=13,weight=ft.FontWeight.W_700,color=TXT),
                                       ft.Text("Récupère les présences depuis le serveur",size=11,color=MUT)],spacing=2,expand=True),
                            ft.Icon(ft.Icons.REFRESH_ROUNDED,color=INFO,size=18)],spacing=10)),
                    stats_row,
                    _sec2(f"Pointages — {mlbl} ({len(recs)})",ft.Icons.HOW_TO_REG_ROUNDED),
                ]+([_att_row(r) for r in recs] or [
                    ft.Container(bgcolor=CARD,border_radius=14,padding=P(28,24,28,24),
                        content=ft.Column([ft.Icon(ft.Icons.HOW_TO_REG_OUTLINED,color=BRD,size=48),
                            ft.Text(f"Aucun pointage — {mlbl}",size=14,color=MUT,text_align=ft.TextAlign.CENTER)],
                            spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER))])+[
                    ft.Container(height=6),_sec2("Exports locaux",ft.Icons.DOWNLOAD_ROUNDED),
                    ft.Row([
                        ft.Container(expand=True,bgcolor=CARD,border_radius=12,border=ft.border.all(1,f"{BLUE}20"),
                            ink=True,on_click=_export_att_pdf,padding=P(12,10,12,10),
                            content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,color=BLUE,size=18),
                                ft.Text("PDF",size=12,weight=ft.FontWeight.W_700,color=BLUE)],spacing=6,tight=True)),
                        ft.Container(width=8),
                        ft.Container(expand=True,bgcolor=CARD,border_radius=12,border=ft.border.all(1,f"{OK}20"),
                            ink=True,on_click=_export_csv,padding=P(12,10,12,10),
                            content=ft.Row([ft.Icon(ft.Icons.TABLE_CHART_OUTLINED,color=OK,size=18),
                                ft.Text("CSV",size=12,weight=ft.FontWeight.W_700,color=OK)],spacing=6,tight=True)),
                    ],spacing=0)]
            else:
                tbs=get_tb()
                ts_list_col.controls=[
                    _sec2(f"Toolbox Talk — {mlbl} ({len(tbs)} sessions)",ft.Icons.RECORD_VOICE_OVER_ROUNDED),
                ]+([_tb_row(r) for r in tbs] or [
                    ft.Container(bgcolor=CARD,border_radius=14,padding=P(28,24,28,24),
                        content=ft.Column([ft.Icon(ft.Icons.RECORD_VOICE_OVER_OUTLINED,color=BRD,size=48),
                            ft.Text(f"Aucune session — {mlbl}",size=14,color=MUT,text_align=ft.TextAlign.CENTER)],
                            spacing=8,horizontal_alignment=ft.CrossAxisAlignment.CENTER))])+[
                    ft.Container(height=6),
                    ft.Container(bgcolor=CARD,border_radius=12,border=ft.border.all(1,f"{PURP}20"),ink=True,
                        on_click=_export_tb_pdf,padding=P(12,10,12,10),
                        content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,color=PURP,size=18),
                            ft.Text("Exporter Toolbox en PDF",size=12,weight=ft.FontWeight.W_700,color=PURP)],spacing=6,tight=True)),
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
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#FFFFFF18",
                                alignment=AL(0,0),ink=True,on_click=lambda e:go_to("home"),
                                content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_OUTLINED,color="#FFFFFF",size=17)),
                            ft.Column([
                                ft.Text("Timesheets & Exports",size=17,weight=ft.FontWeight.BOLD,color="#FFFFFF",text_align=ft.TextAlign.CENTER),
                                ft.Text("OREZONE QHSE — Données terrain",size=10,color="#93C5FD",text_align=ft.TextAlign.CENTER),
                            ],spacing=1,expand=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Container(width=36,height=36,border_radius=18,bgcolor="#FFFFFF18",
                                alignment=AL(0,0),ink=True,on_click=lambda e:rebuild(),
                                content=ft.Icon(ft.Icons.REFRESH_ROUNDED,color="#FFFFFF",size=17)),
                        ],spacing=8),
                        ft.Container(height=10),
                        ft.Container(bgcolor="#FFFFFF12",border_radius=14,padding=P(8,10,8,10),
                            content=ft.Row([
                                ft.Container(width=34,height=34,border_radius=17,bgcolor="#FFFFFF15",
                                    alignment=AL(0,0),ink=True,on_click=prev_m,
                                    content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED,color="#FFFFFF",size=22)),
                                ft.Column([month_lbl,
                                    ft.Text("Sélection du mois",size=9,color="#93C5FD",text_align=ft.TextAlign.CENTER)],
                                    spacing=1,expand=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                ft.Container(width=34,height=34,border_radius=17,bgcolor="#FFFFFF15",
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


    def _s_settings():
        cfg=ft.Text("",size=12)
        def do_save(e=None):
            try:
                validate_url(); save_setting("server_url",srv_url.value)
                save_setting("token",srv_token.value); save_setting("device_name",srv_device.value)
                if not get_setting("device_id"): save_setting("device_id",str(uuid4()))
                cfg.value="Configuration enregistrée."; cfg.color=OK; page.update()
            except Exception as exc: cfg.value=str(exc); cfg.color=DNG; page.update()
        def do_test(e=None):
            busy(True)
            try:
                addr=validate_url(); data=request_json(f"{addr}/api/mobile/ping","")
                cfg.value=f"Serveur OK : {data.get('server','–')} {data.get('time','')}"; cfg.color=OK
            except Exception as exc: cfg.value=str(exc); cfg.color=DNG
            finally: busy(False); page.update()
        def do_dl(e=None):
            busy(True)
            try:
                req_sess(); addr=validate_url(); _boot(addr)
                cfg.value="Données téléchargées."; cfg.color=OK; _refresh_all()
            except Exception as exc: cfg.value=str(exc); cfg.color=DNG
            finally: busy(False); page.update()
        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Column([_hdr("Paramètres","profile"),
                _body(
                    _card(ft.Column([_sec("Connexion serveur",ft.Icons.ROUTER_OUTLINED),
                        srv_url,srv_token,srv_device,cfg,
                        ft.Row([_btn("Enregistrer",ft.Icons.SAVE_OUTLINED,BLUE,do_save,44),
                            ft.Container(width=8),
                            _gbtn("Tester",ft.Icons.WIFI_TETHERING_OUTLINED,BLUE,do_test,44)])],
                        spacing=10),P(16,14,16,14)),
                    _btn("Télécharger les données",ft.Icons.CLOUD_DOWNLOAD_OUTLINED,INFO,do_dl,46),
                    _div(),
                    _card(ft.Column([_sec("Connexion",ft.Icons.PERSON_OUTLINED),
                        lgn_user,lgn_pass,_btn("Se connecter",ft.Icons.LOGIN_OUTLINED,BLUE,do_login,44)],
                        spacing=10),P(16,14,16,14)))],spacing=0))

    def _build(key):
        if key=="login":       return _s_login()
        if key=="home":        return _s_home()
        if key=="maintenance": return _s_maint()
        if key=="intervention":return _s_interv()
        if key=="inspection":  return _s_inspect()
        if key=="toolbox":     return _s_toolbox()
        if key=="alerts":      return _s_alerts()
        if key=="incident":    return _s_incident()
        if key=="profile":     return _s_profile()
        if key=="ppe_check":   return _s_ppe_check()
        if key=="ppe_assign":  return _s_ppe_assign()
        if key=="attendance":  return _s_attendance()
        if key=="timesheet":   return _s_timesheet()
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
    build_mobile_page(page)


if __name__ == "__main__":
    ft.app(target=main)
