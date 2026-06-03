from __future__ import annotations

from datetime import date
from typing import Any

from app.db.connection import db_session


def current_equipment_check_month() -> str:
    return date.today().strftime("%Y-%m")


def get_monthly_equipment_check_status(month: str | None = None) -> dict[str, Any]:
    target_month = month or current_equipment_check_month()
    with db_session() as connection:
        confirmation = connection.execute(
            """
            SELECT month, confirmed_by, confirmed_at, commentaire
            FROM equipment_monthly_checks
            WHERE month = ?
            """,
            (target_month,),
        ).fetchone()
        open_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM equipment_maintenance
            WHERE status IN ('planifiee', 'en_cours', 'en_retard')
            """
        ).fetchone()[0]
        due_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM equipment_maintenance
            WHERE status IN ('planifiee', 'en_cours', 'en_retard')
              AND (
                  (next_due_date IS NOT NULL AND next_due_date <= DATE('now'))
                  OR (next_due_odometer IS NOT NULL AND current_odometer IS NOT NULL AND current_odometer >= next_due_odometer)
                  OR status = 'en_retard'
              )
            """
        ).fetchone()[0]
    confirmed = confirmation is not None
    return {
        "month": target_month,
        "confirmed": confirmed,
        "confirmed_by": confirmation["confirmed_by"] if confirmation else "",
        "confirmed_at": confirmation["confirmed_at"] if confirmation else "",
        "commentaire": confirmation["commentaire"] if confirmation else "",
        "open_maintenance": int(open_count or 0),
        "due_maintenance": int(due_count or 0),
        "message": _monthly_check_message(target_month, int(open_count or 0), int(due_count or 0)),
    }


def confirm_monthly_equipment_check(
    month: str | None = None,
    confirmed_by: str = "system",
    commentaire: str = "",
) -> None:
    target_month = month or current_equipment_check_month()
    user = str(confirmed_by or "system").strip() or "system"
    note = str(commentaire or "").strip()
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO equipment_monthly_checks (month, confirmed_by, confirmed_at, commentaire)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(month) DO UPDATE SET
                confirmed_by = excluded.confirmed_by,
                confirmed_at = CURRENT_TIMESTAMP,
                commentaire = excluded.commentaire
            """,
            (target_month, user, note),
        )


def monthly_equipment_check_alert() -> dict[str, Any] | None:
    status = get_monthly_equipment_check_status()
    if status["confirmed"]:
        return None
    return {
        "id": f"equipment-monthly-check:{status['month']}",
        "source_key": "maintenance",
        "source": "Maintenance",
        "type_alerte": "Verification mensuelle des engins",
        "message": status["message"],
        "niveau": "critique" if status["due_maintenance"] else "haut",
        "niveau_label": "Critique" if status["due_maintenance"] else "Haut",
        "statut": "ouverte",
        "date_creation": f"{status['month']}-01",
        "reference_id": None,
        "reference_label": f"Maintenance {status['month']}",
        "action_hint": "Confirmer la verification mensuelle des engins",
        "can_close": False,
        "monthly_equipment_check": True,
    }


def _monthly_check_message(month: str, open_count: int, due_count: int) -> str:
    detail = f"{open_count} maintenance(s) ouverte(s)"
    if due_count:
        detail += f", dont {due_count} deja due(s)"
    return (
        f"Verification mensuelle des engins requise pour {month}. "
        f"Controle les equipements, compteurs, dates et echeances de maintenance ({detail}), "
        "puis confirme la verification du mois."
    )
