from __future__ import annotations

import logging
from typing import Any

from app.db.connection import db_session

_LOGGER = logging.getLogger(__name__)


def _try_create_risk_alert(title: str, score: int, owner: str = "") -> None:
    try:
        from app.services.alert_service import create_manual_alert
        create_manual_alert({
            "source": "Analyse des Risques",
            "level": "critique",
            "message": f"Risque CRITIQUE détecté: {title} (Score={score})",
            "recommended_action": f"Mettre en place les mesures de maîtrise immédiatement. Responsable: {owner or 'Non défini'}",
            "status": "open",
        })
    except Exception as _exc:
        _LOGGER.warning("Impossible de créer l'alerte pour risque critique '%s': %s", title, _exc)


def _risk_level(score: int) -> str:
    if score >= 15:
        return "critique"
    if score >= 10:
        return "eleve"
    if score >= 5:
        return "moyen"
    return "faible"


def create_risk(data: dict[str, Any]) -> int:
    prob = max(1, min(5, int(data.get("probability") or 1)))
    sev = max(1, min(5, int(data.get("severity") or 1)))
    score = prob * sev
    res_prob = max(1, min(5, int(data.get("residual_probability") or prob)))
    res_sev = max(1, min(5, int(data.get("residual_severity") or sev)))
    res_score = res_prob * res_sev
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO risk_register (
                title, activity, location, zone, hazard_type, affected_people,
                source_of_danger, probability, severity, risk_score, risk_level,
                existing_controls, residual_probability, residual_severity,
                residual_score, residual_level, status, owner, review_date, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(data.get("title") or ""), data.get("activity"), data.get("location"),
                data.get("zone"), str(data.get("hazard_type") or "physique"),
                data.get("affected_people"), data.get("source_of_danger"),
                prob, sev, score, _risk_level(score),
                data.get("existing_controls"),
                res_prob, res_sev, res_score, _risk_level(res_score),
                str(data.get("status") or "ouvert"), data.get("owner"),
                data.get("review_date"), data.get("created_by"),
            ),
        )
        new_id = cursor.lastrowid or 0
    log_risk_action(new_id, "Création", f"Titre: {data.get('title')}, Score: {score}, Niveau: {_risk_level(score)}")
    if score >= 15:
        _try_create_risk_alert(str(data.get("title") or ""), score, str(data.get("owner") or ""))
    return new_id


def update_risk(risk_id: int, data: dict[str, Any]) -> None:
    prob = max(1, min(5, int(data.get("probability") or 1)))
    sev = max(1, min(5, int(data.get("severity") or 1)))
    score = prob * sev
    res_prob = max(1, min(5, int(data.get("residual_probability") or prob)))
    res_sev = max(1, min(5, int(data.get("residual_severity") or sev)))
    res_score = res_prob * res_sev
    with db_session() as conn:
        conn.execute(
            """
            UPDATE risk_register SET
                title=?, activity=?, location=?, zone=?, hazard_type=?,
                affected_people=?, source_of_danger=?, probability=?, severity=?,
                risk_score=?, risk_level=?, existing_controls=?,
                residual_probability=?, residual_severity=?, residual_score=?,
                residual_level=?, status=?, owner=?, review_date=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                str(data.get("title") or ""), data.get("activity"), data.get("location"),
                data.get("zone"), str(data.get("hazard_type") or "physique"),
                data.get("affected_people"), data.get("source_of_danger"),
                prob, sev, score, _risk_level(score),
                data.get("existing_controls"),
                res_prob, res_sev, res_score, _risk_level(res_score),
                str(data.get("status") or "ouvert"), data.get("owner"),
                data.get("review_date"), risk_id,
            ),
        )
    log_risk_action(risk_id, "Modification", f"Score: {score}, Niveau: {_risk_level(score)}")
    if score >= 15:
        _try_create_risk_alert(str(data.get("title") or ""), score, str(data.get("owner") or ""))


def delete_risk(risk_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM risk_register WHERE id=?", (risk_id,))
    log_risk_action(risk_id, "Suppression", "Risque supprimé")


def get_risk(risk_id: int) -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM risk_register WHERE id=?", (risk_id,)).fetchone()
        return dict(row) if row else None


def list_risks(
    status: str | None = None,
    level: str | None = None,
    hazard_type: str | None = None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if status and status != "tous":
        conditions.append("status=?")
        params.append(status)
    if level and level != "tous":
        conditions.append("risk_level=?")
        params.append(level)
    if hazard_type and hazard_type != "tous":
        conditions.append("LOWER(hazard_type)=LOWER(?)")
        params.append(hazard_type)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with db_session() as conn:
        rows = conn.execute(
            f"SELECT * FROM risk_register {where} ORDER BY risk_score DESC, created_at DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_risk_summary() -> dict[str, Any]:
    with db_session() as conn:
        rows = conn.execute("SELECT risk_level, status FROM risk_register").fetchall()
    total = len(rows)
    return {
        "total": total,
        "critique": sum(1 for r in rows if r["risk_level"] == "critique"),
        "eleve": sum(1 for r in rows if r["risk_level"] == "eleve"),
        "moyen": sum(1 for r in rows if r["risk_level"] == "moyen"),
        "faible": sum(1 for r in rows if r["risk_level"] == "faible"),
        "ouvert": sum(1 for r in rows if r["status"] == "ouvert"),
        "en_cours": sum(1 for r in rows if r["status"] == "en_cours"),
        "clos": sum(1 for r in rows if r["status"] == "clos"),
    }


def get_risk_heatmap() -> dict[tuple[int, int], int]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT probability, severity, COUNT(*) as cnt FROM risk_register GROUP BY probability, severity"
        ).fetchall()
    return {(int(r["probability"]), int(r["severity"])): int(r["cnt"]) for r in rows}


def list_controls(risk_id: int) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM risk_controls WHERE risk_id=? ORDER BY control_type, created_at",
            (risk_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_control(data: dict[str, Any]) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO risk_controls (risk_id, control_type, description, responsible, target_date, status, effectiveness)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data.get("risk_id") or 0),
                str(data.get("control_type") or "administratif"),
                str(data.get("description") or ""),
                data.get("responsible"),
                data.get("target_date"),
                str(data.get("status") or "planifie"),
                data.get("effectiveness"),
            ),
        )
        return cursor.lastrowid or 0


def update_control(control_id: int, data: dict[str, Any]) -> None:
    with db_session() as conn:
        conn.execute(
            """
            UPDATE risk_controls
            SET control_type=?, description=?, responsible=?, target_date=?, status=?, effectiveness=?
            WHERE id=?
            """,
            (
                str(data.get("control_type") or "administratif"),
                str(data.get("description") or ""),
                data.get("responsible"),
                data.get("target_date"),
                str(data.get("status") or "planifie"),
                data.get("effectiveness"),
                control_id,
            ),
        )


def delete_control(control_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM risk_controls WHERE id=?", (control_id,))


def get_risk_filter_options() -> dict[str, list[str]]:
    with db_session() as conn:
        hazards = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT hazard_type FROM risk_register WHERE hazard_type IS NOT NULL ORDER BY hazard_type"
            ).fetchall()
        ]
        owners = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT owner FROM risk_register WHERE owner IS NOT NULL AND owner != '' ORDER BY owner"
            ).fetchall()
        ]
    return {"hazard_types": hazards, "owners": owners}


def log_risk_action(risk_id: int, action: str, details: str = "", changed_by: str = "") -> None:
    with db_session() as conn:
        conn.execute(
            "INSERT INTO risk_audit_log (risk_id, action, details, changed_by) VALUES (?, ?, ?, ?)",
            (risk_id, action, details or "", changed_by or ""),
        )


def get_risk_history(risk_id: int) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM risk_audit_log WHERE risk_id=? ORDER BY changed_at DESC LIMIT 50",
            (risk_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_risk_links(risk_id: int) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM risk_links WHERE risk_id=? ORDER BY link_type, created_at",
            (risk_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_risk_link(risk_id: int, link_type: str, linked_label: str, linked_id: int | None = None) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO risk_links (risk_id, link_type, linked_label, linked_id) VALUES (?, ?, ?, ?)",
            (risk_id, link_type, linked_label, linked_id),
        )
        return cursor.lastrowid or 0


def delete_risk_link(link_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM risk_links WHERE id=?", (link_id,))


def get_overdue_reviews() -> list[dict[str, Any]]:
    """Return risks whose review_date has passed and status is not clos."""
    from datetime import date
    today = date.today().isoformat()
    with db_session() as conn:
        rows = conn.execute(
            """SELECT id, title, risk_level, owner, review_date
               FROM risk_register
               WHERE review_date IS NOT NULL AND review_date != ''
                 AND review_date < ? AND status != 'clos'
               ORDER BY review_date ASC""",
            (today,),
        ).fetchall()
        return [dict(r) for r in rows]
