"""lock_service.py — Gestion des verrous de fiches pour le mode multi-PC.

Chaque verrou est stocké dans la table ``verrous`` de la base SQLite locale.
Un verrou expire après 15 minutes et peut être renouvelé automatiquement par
le même utilisateur.
"""
from __future__ import annotations

import socket
from datetime import datetime, timedelta
from typing import Optional

from app.db.connection import db_session

_LOCK_DURATION_MINUTES = 15


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS verrous (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            table_cible         TEXT NOT NULL,
            id_enregistrement   TEXT NOT NULL,
            utilisateur         TEXT NOT NULL,
            pc_nom              TEXT NOT NULL,
            verrouille_depuis   TEXT NOT NULL,
            expire_a            TEXT NOT NULL,
            UNIQUE(table_cible, id_enregistrement)
        )
        """
    )


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _expire_iso() -> str:
    return (datetime.now() + timedelta(minutes=_LOCK_DURATION_MINUTES)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _pc_name() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "PC_INCONNU"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def acquire_lock(
    table_name: str,
    record_id: str,
    user_name: str,
    pc_name: Optional[str] = None,
) -> bool:
    """Tente d'acquérir un verrou sur (table_name, record_id) pour user_name.

    - Si le verrou n'existe pas → créé, retourne True.
    - Si le verrou appartient déjà à user_name → renouvelé, retourne True.
    - Si le verrou appartient à un autre utilisateur ET n'est pas expiré → retourne False.
    - Si le verrou est expiré (peu importe le propriétaire) → remplacé, retourne True.
    """
    if pc_name is None:
        pc_name = _pc_name()
    now = _now_iso()
    expire = _expire_iso()

    try:
        with db_session() as conn:
            _ensure_table(conn)

            row = conn.execute(
                "SELECT utilisateur, expire_a FROM verrous "
                "WHERE table_cible = ? AND id_enregistrement = ?",
                (table_name, str(record_id)),
            ).fetchone()

            if row is None:
                # Pas de verrou existant
                conn.execute(
                    """
                    INSERT INTO verrous
                        (table_cible, id_enregistrement, utilisateur, pc_nom,
                         verrouille_depuis, expire_a)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (table_name, str(record_id), user_name, pc_name, now, expire),
                )
                return True

            existing_owner = row["utilisateur"]
            existing_expire = row["expire_a"]

            is_expired = existing_expire < now

            if existing_owner == user_name or is_expired:
                # Renouvellement (même utilisateur ou verrou expiré)
                conn.execute(
                    """
                    UPDATE verrous
                    SET utilisateur = ?, pc_nom = ?, verrouille_depuis = ?, expire_a = ?
                    WHERE table_cible = ? AND id_enregistrement = ?
                    """,
                    (user_name, pc_name, now, expire, table_name, str(record_id)),
                )
                return True

            # Verrou actif appartenant à quelqu'un d'autre
            return False

    except Exception:
        return False


def release_lock(table_name: str, record_id: str, user_name: str) -> bool:
    """Libère le verrou si l'utilisateur en est bien le propriétaire."""
    try:
        with db_session() as conn:
            _ensure_table(conn)
            cursor = conn.execute(
                "DELETE FROM verrous "
                "WHERE table_cible = ? AND id_enregistrement = ? AND utilisateur = ?",
                (table_name, str(record_id), user_name),
            )
            return cursor.rowcount > 0
    except Exception:
        return False


def get_lock_info(table_name: str, record_id: str) -> Optional[dict]:
    """Retourne les infos du verrou actuel ou None si absent/expiré."""
    try:
        with db_session() as conn:
            _ensure_table(conn)
            now = _now_iso()
            row = conn.execute(
                "SELECT * FROM verrous "
                "WHERE table_cible = ? AND id_enregistrement = ? AND expire_a > ?",
                (table_name, str(record_id), now),
            ).fetchone()
            if row is None:
                return None
            return dict(row)
    except Exception:
        return None


def release_expired_locks() -> int:
    """Supprime tous les verrous expirés. Retourne le nombre supprimé."""
    try:
        with db_session() as conn:
            _ensure_table(conn)
            now = _now_iso()
            cursor = conn.execute(
                "DELETE FROM verrous WHERE expire_a <= ?", (now,)
            )
            return cursor.rowcount
    except Exception:
        return 0


def release_all_locks_for_user(user_name: str) -> int:
    """Libère tous les verrous appartenant à user_name (à appeler au logout)."""
    try:
        with db_session() as conn:
            _ensure_table(conn)
            cursor = conn.execute(
                "DELETE FROM verrous WHERE utilisateur = ?", (user_name,)
            )
            return cursor.rowcount
    except Exception:
        return 0


def list_active_locks() -> list[dict]:
    """Retourne la liste de tous les verrous non expirés."""
    try:
        with db_session() as conn:
            _ensure_table(conn)
            now = _now_iso()
            rows = conn.execute(
                "SELECT * FROM verrous WHERE expire_a > ? ORDER BY verrouille_depuis DESC",
                (now,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
