from __future__ import annotations

import hashlib
import hmac
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.db import connection as db_connection
from app.db.connection import db_session


USER_STATUSES = ["actif", "inactif"]
HASH_NAME = "pbkdf2_sha256"
HASH_ITERATIONS = 260_000
BACKUPS_DIR = BASE_DIR / "backups"
ADMIN_ROLE_NAME = "Administrateur"

ALL_MODULES = [
    "Dashboard",
    "Referentials",
    "EmployeeManagement",
    "TrainingManagement",
    "ToolboxTalk",
    "TimeSheet",
    "MonthlyTimesheet",
    "Ppe",
    "MaintenanceActions",
    "Alerts",
    "Reports",
    "Settings",
    "Admin",
]

ROLE_MODULES = {
    "Administrateur": [
        "Dashboard",
        "Referentials",
        "EmployeeManagement",
        "TrainingManagement",
        "ToolboxTalk",
        "TimeSheet",
        "MonthlyTimesheet",
        "Ppe",
        "MaintenanceActions",
        "Alerts",
        "Reports",
        "Settings",
        "Admin",
    ],
    "Officier HSE": ["Dashboard", "TrainingManagement", "ToolboxTalk", "MaintenanceActions", "Alerts", "Reports"],
    "Superviseur": ["Dashboard", "EmployeeManagement", "ToolboxTalk", "TimeSheet", "MonthlyTimesheet", "MaintenanceActions", "Alerts", "Reports"],
    "Responsable stock": ["Dashboard", "Ppe", "MaintenanceActions", "Alerts", "Reports"],
    "Direction": ["Dashboard", "MaintenanceActions", "Alerts", "Reports"],
}


def get_admin_summary() -> dict[str, int]:
    with db_session() as connection:
        users = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN statut = 'actif' THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN statut = 'inactif' THEN 1 ELSE 0 END) AS inactive
            FROM utilisateurs
            """
        ).fetchone()
        roles = connection.execute("SELECT COUNT(*) AS total FROM roles").fetchone()
        audit = connection.execute("SELECT COUNT(*) AS total FROM admin_audit").fetchone()
    return {
        "users": int(users["total"] or 0),
        "active_users": int(users["active"] or 0),
        "inactive_users": int(users["inactive"] or 0),
        "roles": int(roles["total"] or 0),
        "backups": len(list_backups()),
        "audit": int(audit["total"] or 0),
    }


def has_users() -> bool:
    with db_session() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM utilisateurs").fetchone()
    return int(row["total"] or 0) > 0


def get_role_modules(role: str) -> list[str]:
    role_name = str(role or "")
    ensure_default_role_permissions()
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT rpm.module_key
            FROM role_module_permissions rpm
            JOIN roles r ON r.id_role = rpm.role_id
            WHERE r.nom = ?
            ORDER BY rpm.module_key
            """,
            (role_name,),
        ).fetchall()
    if rows:
        configured = [str(row["module_key"]) for row in rows if str(row["module_key"]) in ALL_MODULES]
        if role_name == ADMIN_ROLE_NAME:
            for mandatory_module in ("ToolboxTalk", "TimeSheet", "MonthlyTimesheet", "MaintenanceActions", "Settings", "Admin"):
                if mandatory_module not in configured:
                    configured.append(mandatory_module)
        return _ordered_modules(configured)
    return ROLE_MODULES.get(role_name, ["Dashboard"])


def list_roles() -> list[dict[str, Any]]:
    ensure_default_role_permissions()
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id_role, nom, description
            FROM roles
            ORDER BY nom
            """
        ).fetchall()
    return [dict(row) for row in rows]


def ensure_default_role_permissions() -> None:
    with db_session() as connection:
        for role_name, modules in ROLE_MODULES.items():
            role = connection.execute(
                "SELECT id_role FROM roles WHERE nom = ?",
                (role_name,),
            ).fetchone()
            if role is None:
                continue
            existing = connection.execute(
                "SELECT COUNT(*) AS total FROM role_module_permissions WHERE role_id = ?",
                (role["id_role"],),
            ).fetchone()
            if role_name != ADMIN_ROLE_NAME and int(existing["total"] or 0):
                continue
            for module in modules:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO role_module_permissions(role_id, module_key)
                    VALUES (?, ?)
                    """,
                    (role["id_role"], module),
                )


def list_role_permissions() -> list[dict[str, Any]]:
    ensure_default_role_permissions()
    roles = list_roles()
    return [
        {
            **role,
            "modules": get_role_modules(str(role["nom"])),
        }
        for role in roles
    ]


def update_role_modules(
    role_id: int,
    modules: list[str],
    changed_by: str = "system",
    commentaire: str | None = None,
) -> None:
    selected = _ordered_modules([str(module) for module in modules if str(module) in ALL_MODULES])
    if "Dashboard" not in selected:
        selected.insert(0, "Dashboard")
    with db_session() as connection:
        role = connection.execute(
            "SELECT id_role, nom FROM roles WHERE id_role = ?",
            (int(role_id),),
        ).fetchone()
        if role is None:
            raise ValueError("Role introuvable.")
        if role["nom"] == ADMIN_ROLE_NAME and "Admin" not in selected:
            raise ValueError("Le role Administrateur doit conserver le module Administration.")
        previous = [
            str(row["module_key"])
            for row in connection.execute(
                "SELECT module_key FROM role_module_permissions WHERE role_id = ? ORDER BY module_key",
                (int(role_id),),
            ).fetchall()
        ]
        connection.execute("DELETE FROM role_module_permissions WHERE role_id = ?", (int(role_id),))
        for module in selected:
            connection.execute(
                """
                INSERT OR IGNORE INTO role_module_permissions(role_id, module_key)
                VALUES (?, ?)
                """,
                (int(role_id), module),
            )
        _insert_admin_audit(
            connection,
            "role_modules",
            "role",
            str(role_id),
            ",".join(_ordered_modules(previous)),
            ",".join(selected),
            changed_by,
            commentaire,
        )


def list_users(search: str = "") -> list[dict[str, Any]]:
    pattern = f"%{str(search or '').strip()}%"
    where = ""
    params: tuple[Any, ...] = ()
    if str(search or "").strip():
        where = "WHERE u.username LIKE ? OR r.nom LIKE ?"
        params = (pattern, pattern)
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                u.id_user,
                u.username,
                u.role_id,
                r.nom AS role,
                r.description AS role_description,
                u.statut,
                u.created_at,
                u.updated_at
            FROM utilisateurs u
            JOIN roles r ON r.id_role = u.role_id
            {where}
            ORDER BY u.username
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def create_user(values: dict[str, Any], changed_by: str = "system") -> int:
    payload = _clean_user_payload(values, require_password=True)
    with db_session() as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO utilisateurs (username, password_hash, role_id, statut)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload["username"],
                    hash_password(payload["password"]),
                    payload["role_id"],
                    payload["statut"],
                ),
            )
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise ValueError("Creation impossible: ce nom utilisateur existe deja.") from exc
            raise
        user_id = int(cursor.lastrowid)
        _insert_admin_audit(
            connection,
            "create_user",
            "user",
            str(user_id),
            "",
            _user_audit_value(payload),
            changed_by,
        )
        return user_id


def update_user(user_id: int, values: dict[str, Any], changed_by: str = "system") -> None:
    payload = _clean_user_payload(values, require_password=False)
    with db_session() as connection:
        _ensure_not_removing_last_active_admin(
            connection,
            int(user_id),
            int(payload["role_id"]),
            str(payload["statut"]),
        )
        previous = connection.execute(
            """
            SELECT u.username, u.role_id, r.nom AS role, u.statut
            FROM utilisateurs u
            JOIN roles r ON r.id_role = u.role_id
            WHERE u.id_user = ?
            """,
            (int(user_id),),
        ).fetchone()
        if previous is None:
            raise ValueError("Utilisateur introuvable.")
        try:
            cursor = connection.execute(
                """
                UPDATE utilisateurs
                SET username = ?,
                    role_id = ?,
                    statut = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_user = ?
                """,
                (payload["username"], payload["role_id"], payload["statut"], int(user_id)),
            )
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise ValueError("Modification impossible: ce nom utilisateur existe deja.") from exc
            raise
        if not cursor.rowcount:
            raise ValueError("Utilisateur introuvable.")
        _insert_admin_audit(
            connection,
            "update_user",
            "user",
            str(user_id),
            _row_audit_value(previous),
            _user_audit_value(payload),
            changed_by,
        )


def reset_user_password(user_id: int, new_password: str, changed_by: str = "system") -> None:
    password = _clean_password(new_password)
    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE utilisateurs
            SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id_user = ?
            """,
            (hash_password(password), int(user_id)),
        )
        if not cursor.rowcount:
            raise ValueError("Utilisateur introuvable.")
        _insert_admin_audit(
            connection,
            "reset_password",
            "user",
            str(user_id),
            "password_hash",
            "password_reset",
            changed_by,
        )


def update_user_status(user_id: int, statut: str, changed_by: str = "system") -> None:
    status = str(statut or "").strip()
    if status not in USER_STATUSES:
        raise ValueError("Statut utilisateur invalide.")
    with db_session() as connection:
        current = connection.execute(
            "SELECT role_id, statut FROM utilisateurs WHERE id_user = ?",
            (int(user_id),),
        ).fetchone()
        if current is None:
            raise ValueError("Utilisateur introuvable.")
        _ensure_not_removing_last_active_admin(
            connection,
            int(user_id),
            int(current["role_id"]),
            status,
        )
        cursor = connection.execute(
            """
            UPDATE utilisateurs
            SET statut = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id_user = ?
            """,
            (status, int(user_id)),
        )
        if not cursor.rowcount:
            raise ValueError("Utilisateur introuvable.")
        _insert_admin_audit(
            connection,
            "update_status",
            "user",
            str(user_id),
            str(current["statut"]),
            status,
            changed_by,
        )


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    user_name = str(username or "").strip()
    if not user_name or not password:
        raise ValueError("Nom utilisateur et mot de passe obligatoires.")
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT
                u.id_user,
                u.username,
                u.password_hash,
                u.statut,
                r.nom AS role
            FROM utilisateurs u
            JOIN roles r ON r.id_role = u.role_id
            WHERE u.username = ?
            """,
            (user_name,),
        ).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        raise ValueError("Identifiants invalides.")
    if row["statut"] != "actif":
        raise ValueError("Utilisateur inactif.")
    return {
        "id_user": int(row["id_user"]),
        "username": row["username"],
        "role": row["role"],
        "statut": row["statut"],
    }


def create_database_backup(label: str | None = None, changed_by: str = "system") -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    if not db_connection.DATABASE_PATH.exists():
        raise ValueError("Base de donnees introuvable.")
    suffix = _safe_backup_label(label)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = BACKUPS_DIR / f"orezone_backup_{timestamp}{suffix}.db"
    shutil.copy2(db_connection.DATABASE_PATH, output)
    with db_session() as connection:
        _insert_admin_audit(
            connection,
            "create_backup",
            "backup",
            output.name,
            "",
            str(output),
            changed_by,
            label,
        )
    return output


def restore_database_backup(backup_name: str, changed_by: str = "system") -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    source = _resolve_backup_path(backup_name)
    if not source.exists():
        raise ValueError("Sauvegarde introuvable.")
    if not db_connection.DATABASE_PATH.exists():
        raise ValueError("Base de donnees introuvable.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety_copy = BACKUPS_DIR / f"orezone_backup_{timestamp}_avant_restauration.db"
    shutil.copy2(db_connection.DATABASE_PATH, safety_copy)
    shutil.copy2(source, db_connection.DATABASE_PATH)
    db_connection.initialize_database()
    with db_session() as connection:
        _insert_admin_audit(
            connection,
            "restore_backup",
            "backup",
            source.name,
            str(safety_copy),
            str(source),
            changed_by,
            "Restauration avec sauvegarde automatique avant remplacement.",
        )
    return safety_copy


def list_backups() -> list[dict[str, Any]]:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(BACKUPS_DIR.glob("*.db"), key=lambda item: item.stat().st_mtime, reverse=True):
        stat = path.stat()
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return rows


def list_admin_audit(limit: int = 100) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id_audit, action, cible_type, cible_id, ancienne_valeur,
                   nouvelle_valeur, changed_by, changed_at, commentaire
            FROM admin_audit
            ORDER BY changed_at DESC, id_audit DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def hash_password(password: str) -> str:
    clean = _clean_password(password)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        clean.encode("utf-8"),
        salt.encode("ascii"),
        HASH_ITERATIONS,
    ).hex()
    return f"{HASH_NAME}${HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        name, iterations_text, salt, expected = str(stored_hash).split("$", 3)
        if name != HASH_NAME:
            return False
        iterations = int(iterations_text)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt.encode("ascii"),
            iterations,
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def _clean_user_payload(values: dict[str, Any], require_password: bool) -> dict[str, Any]:
    username = str(values.get("username") or "").strip()
    if not username:
        raise ValueError("Nom utilisateur obligatoire.")
    if len(username) < 3:
        raise ValueError("Nom utilisateur trop court.")
    role_id = int(values.get("role_id") or 0)
    if not role_id:
        raise ValueError("Role obligatoire.")
    status = str(values.get("statut") or "actif").strip()
    if status not in USER_STATUSES:
        raise ValueError("Statut utilisateur invalide.")
    payload: dict[str, Any] = {"username": username, "role_id": role_id, "statut": status}
    if require_password:
        payload["password"] = _clean_password(str(values.get("password") or ""))
    return payload


def _clean_password(password: str) -> str:
    clean = str(password or "")
    if len(clean) < 8:
        raise ValueError("Mot de passe trop court: minimum 8 caracteres.")
    return clean


def _ensure_not_removing_last_active_admin(
    connection: Any,
    user_id: int,
    new_role_id: int,
    new_status: str,
) -> None:
    current = connection.execute(
        """
        SELECT u.id_user, u.statut, r.nom AS role
        FROM utilisateurs u
        JOIN roles r ON r.id_role = u.role_id
        WHERE u.id_user = ?
        """,
        (user_id,),
    ).fetchone()
    if current is None:
        raise ValueError("Utilisateur introuvable.")
    if current["role"] != ADMIN_ROLE_NAME or current["statut"] != "actif":
        return

    new_role = connection.execute(
        "SELECT nom FROM roles WHERE id_role = ?",
        (new_role_id,),
    ).fetchone()
    if new_role is None:
        raise ValueError("Role introuvable.")
    if new_role["nom"] == ADMIN_ROLE_NAME and new_status == "actif":
        return

    active_admins = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM utilisateurs u
        JOIN roles r ON r.id_role = u.role_id
        WHERE r.nom = ? AND u.statut = 'actif'
        """,
        (ADMIN_ROLE_NAME,),
    ).fetchone()
    if int(active_admins["total"] or 0) <= 1:
        raise ValueError("Operation impossible: conserve au moins un administrateur actif.")


def _safe_backup_label(label: str | None) -> str:
    text = str(label or "").strip()
    if not text:
        return ""
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in text)
    return f"_{safe[:40]}"


def _resolve_backup_path(backup_name: str) -> Path:
    raw = Path(str(backup_name or "").strip())
    candidate = raw if raw.is_absolute() else BACKUPS_DIR / raw.name
    resolved_backups = BACKUPS_DIR.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_backups not in [resolved_candidate, *resolved_candidate.parents]:
        raise ValueError("Sauvegarde invalide.")
    return resolved_candidate


def _insert_admin_audit(
    connection: Any,
    action: str,
    target_type: str,
    target_id: str,
    old_value: str,
    new_value: str,
    changed_by: str,
    commentaire: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO admin_audit (
            action, cible_type, cible_id, ancienne_valeur,
            nouvelle_valeur, changed_by, commentaire
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action,
            target_type,
            target_id,
            old_value,
            new_value,
            str(changed_by or "system").strip() or "system",
            str(commentaire or "").strip() or None,
        ),
    )


def _ordered_modules(modules: list[str]) -> list[str]:
    selected = set(modules)
    return [module for module in ALL_MODULES if module in selected]


def _user_audit_value(payload: dict[str, Any]) -> str:
    return f"username={payload.get('username')};role_id={payload.get('role_id')};statut={payload.get('statut')}"


def _row_audit_value(row: Any) -> str:
    return f"username={row['username']};role_id={row['role_id']};statut={row['statut']}"
