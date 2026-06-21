from __future__ import annotations

from app.db.connection import db_session
from app.services.app_logger import get_logger


LOGGER = get_logger(__name__)


def record_system_audit(
    action: str,
    target_type: str,
    target_id: str,
    details: str,
    changed_by: str = "system",
) -> None:
    try:
        with db_session() as connection:
            connection.execute(
                """
                INSERT INTO admin_audit (
                    action, cible_type, cible_id, ancienne_valeur,
                    nouvelle_valeur, changed_by, commentaire
                ) VALUES (?, ?, ?, '', ?, ?, ?)
                """,
                (
                    str(action or "system_action")[:80],
                    str(target_type or "system")[:80],
                    str(target_id or "-")[:120],
                    str(details or "")[:1000],
                    str(changed_by or "system")[:80],
                    "Audit operationnel automatique",
                ),
            )
    except Exception as exc:  # pragma: no cover - audit must never block operations.
        LOGGER.warning("Audit write failed for %s/%s: %s", action, target_type, exc)
