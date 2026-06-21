from __future__ import annotations
from datetime import date
from typing import Any

from app.db.connection import db_session
from app.services.app_logger import get_logger

LOGGER = get_logger(__name__)

PRIORITES: dict[str, str] = {
    "critique": "#EF4444",
    "urgent":   "#F59E0B",
    "info":     "#3B82F6",
    "succes":   "#10B981",
}

SOURCE_LABELS: dict[str, str] = {
    "risques":   "Risques",
    "accidents": "Accidents",
    "permis":    "Permis",
    "epi":       "EPI",
    "formation": "Formation",
    "general":   "Général",
}


def list_notifications(
    statut: str | None = None,
    priorite: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    wheres: list[str] = []
    params: list[Any] = []
    if statut:
        wheres.append("statut=?"); params.append(statut)
    if priorite:
        wheres.append("priorite=?"); params.append(priorite)
    if source:
        wheres.append("source=?"); params.append(source)
    where_sql = f"WHERE {' AND '.join(wheres)}" if wheres else ""
    priority_order = "CASE priorite WHEN 'critique' THEN 0 WHEN 'urgent' THEN 1 WHEN 'info' THEN 2 ELSE 3 END"
    with db_session() as conn:
        rows = conn.execute(
            f"SELECT * FROM notifications_qhse {where_sql} ORDER BY {priority_order}, created_at DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def acknowledge_notification(notif_id: int, acknowledged_by: str = "Utilisateur") -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE notifications_qhse SET statut='traite', acknowledged_at=CURRENT_TIMESTAMP, acknowledged_by=? WHERE id=?",
            (acknowledged_by, notif_id),
        )


def dismiss_notification(notif_id: int) -> None:
    with db_session() as conn:
        conn.execute("UPDATE notifications_qhse SET statut='ignore' WHERE id=?", (notif_id,))


def create_notification(
    source: str,
    titre: str,
    message: str = "",
    priorite: str = "info",
    source_id: str = "",
) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO notifications_qhse (source, source_id, priorite, titre, message) VALUES (?,?,?,?,?)",
            (source, source_id or None, priorite, titre.strip(), message.strip() or None),
        )
        return int(cursor.lastrowid)


def count_new_notifications() -> int:
    with db_session() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM notifications_qhse WHERE statut='nouveau'"
        ).fetchone()
    return int(row[0] or 0)


def clear_handled() -> int:
    with db_session() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM notifications_qhse WHERE statut IN ('traite','ignore')"
        ).fetchone()
        count = int(row[0] or 0)
        conn.execute("DELETE FROM notifications_qhse WHERE statut IN ('traite','ignore')")
    return count


def sync_module_alerts() -> int:
    """Pull live alerts from all modules and insert as notifications (de-duplicated by source_id)."""
    count = 0

    def _ensure(source: str, source_id: str, titre: str, message: str, priorite: str) -> None:
        nonlocal count
        with db_session() as conn:
            existing = conn.execute(
                "SELECT id FROM notifications_qhse WHERE source=? AND source_id=? AND statut='nouveau'",
                (source, source_id),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO notifications_qhse (source, source_id, priorite, titre, message) VALUES (?,?,?,?,?)",
                    (source, source_id, priorite, titre, message),
                )
                count += 1

    try:
        from app.services.risk_service import get_overdue_reviews
        for r in get_overdue_reviews():
            desc = str(r.get("activity") or r.get("title") or "Risque")[:50]
            _ensure(
                "risques", f"risk-overdue-{r['id']}",
                f"Révision en retard : {desc}",
                f"Prévue le {r.get('review_date', '?')} — Statut: {r.get('status', '?')}",
                "urgent",
            )
    except Exception as _exc:
        LOGGER.warning("Notification sync error: %s", _exc)

    try:
        from app.services.accident_service import list_accidents
        for a in list_accidents(statut="ouvert"):
            _ensure(
                "accidents", f"acc-open-{a['id']}",
                f"Accident ouvert : {a.get('numero', '?')} ({a.get('gravite', '?').title()})",
                f"Le {a.get('date_evenement', '?')} à {a.get('lieu', '?')}",
                "critique" if a.get("gravite") in ("grave", "fatal") else "urgent",
            )
    except Exception as _exc:
        LOGGER.warning("Notification sync error: %s", _exc)

    try:
        from app.services.permit_service import get_expiring_permits
        for p in get_expiring_permits(2):
            _ensure(
                "permis", f"permit-exp-{p['id']}",
                f"Permis expirant : {p.get('numero', '?')} — {str(p.get('titre', '?'))[:40]}",
                f"Expire le {p.get('date_fin', '?')} — {p.get('lieu', '?')}",
                "urgent",
            )
    except Exception as _exc:
        LOGGER.warning("Notification sync error: %s", _exc)

    try:
        from app.services.ppe_service import get_expiring_assigned_ppe
        for e in get_expiring_assigned_ppe(15):
            emp = f"{e.get('nom', '?')} {e.get('prenom', '')}".strip()
            jours = int(e.get("jours_restants") or 99)
            _ensure(
                "epi", f"epi-exp-{e['id_affectation']}",
                f"EPI expirant : {e.get('epi_nom', '?')} — {emp}",
                f"Expire le {e.get('date_expiration', '?')} (J-{jours})",
                "critique" if jours <= 7 else "urgent",
            )
    except Exception as _exc:
        LOGGER.warning("Notification sync error: %s", _exc)

    return count
