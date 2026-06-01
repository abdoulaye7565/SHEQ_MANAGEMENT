from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.db.connection import db_session
from app.services.attendance_export_service import export_rows_xlsx


MAINTENANCE_TYPES = {"preventive", "corrective", "inspection", "calibration"}
MAINTENANCE_STATUSES = {"planifiee", "en_cours", "terminee", "annulee", "en_retard"}
ACTION_STATUSES = {"ouverte", "en_cours", "terminee", "annulee", "en_retard"}
PRIORITIES = {"basse", "moyenne", "haute", "critique"}


def get_maintenance_action_summary() -> dict[str, int | float]:
    today = date.today().isoformat()
    with db_session() as connection:
        maintenance = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('planifiee', 'en_cours') THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status IN ('planifiee', 'en_cours') AND planned_date < ? THEN 1 ELSE 0 END) AS late_count,
                SUM(CASE WHEN priority = 'critique' AND status NOT IN ('terminee', 'annulee') THEN 1 ELSE 0 END) AS critical_count,
                COALESCE(SUM(cost), 0) AS cost_total
            FROM equipment_maintenance
            """,
            (today,),
        ).fetchone()
        actions = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('ouverte', 'en_cours') THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status IN ('ouverte', 'en_cours') AND due_date < ? THEN 1 ELSE 0 END) AS late_count,
                SUM(CASE WHEN priority = 'critique' AND status NOT IN ('terminee', 'annulee') THEN 1 ELSE 0 END) AS critical_count
            FROM action_tracker
            """,
            (today,),
        ).fetchone()
    return {
        "maintenance_total": int(maintenance["total"] or 0),
        "maintenance_open": int(maintenance["open_count"] or 0),
        "maintenance_late": int(maintenance["late_count"] or 0),
        "maintenance_critical": int(maintenance["critical_count"] or 0),
        "maintenance_cost": round(float(maintenance["cost_total"] or 0), 2),
        "actions_total": int(actions["total"] or 0),
        "actions_open": int(actions["open_count"] or 0),
        "actions_late": int(actions["late_count"] or 0),
        "actions_critical": int(actions["critical_count"] or 0),
    }


def get_maintenance_action_options() -> dict[str, list[dict[str, Any]]]:
    with db_session() as connection:
        sites = connection.execute(
            """
            SELECT id_site AS value, nom AS label
            FROM sites
            WHERE actif = 1
            ORDER BY CASE WHEN nom = 'SYAMA' THEN 0 ELSE 1 END, nom
            """
        ).fetchall()
        employees = connection.execute(
            """
            SELECT e.id_employe AS value,
                   COALESCE(e.nom, e.nom_complet) || ' ' || COALESCE(e.prenom, '') AS label
            FROM employes e
            WHERE e.statut = 'actif'
            ORDER BY label
            """
        ).fetchall()
    return {"sites": [dict(row) for row in sites], "employees": [dict(row) for row in employees]}


def list_maintenance_action_alerts() -> dict[str, list[dict[str, Any]]]:
    today = date.today().isoformat()
    with db_session() as connection:
        maintenance_rows = connection.execute(
            """
            SELECT
                em.id_maintenance,
                em.equipment_code,
                em.equipment_name,
                em.priority,
                em.status,
                em.planned_date,
                s.nom AS site
            FROM equipment_maintenance em
            LEFT JOIN sites s ON s.id_site = em.site_id
            WHERE em.status IN ('planifiee', 'en_cours')
              AND (
                  em.planned_date < ?
                  OR em.priority = 'critique'
              )
            ORDER BY em.planned_date, em.priority
            """,
            (today,),
        ).fetchall()
        action_rows = connection.execute(
            """
            SELECT
                a.id_action,
                a.source,
                a.title,
                a.priority,
                a.status,
                a.due_date,
                s.nom AS site
            FROM action_tracker a
            LEFT JOIN sites s ON s.id_site = a.site_id
            WHERE a.status IN ('ouverte', 'en_cours')
              AND (
                  a.due_date < ?
                  OR a.priority = 'critique'
              )
            ORDER BY a.due_date, a.priority
            """,
            (today,),
        ).fetchall()
    return {
        "maintenance": [dict(row) for row in maintenance_rows],
        "actions": [dict(row) for row in action_rows],
    }


def list_equipment_maintenance(
    search: str = "",
    status: str = "all",
    limit: int = 200,
) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    where = []
    params: list[Any] = []
    if search.strip():
        pattern = f"%{search.strip()}%"
        where.append(
            """
            (em.equipment_name LIKE ? OR COALESCE(em.equipment_code, '') LIKE ?
             OR COALESCE(em.category, '') LIKE ? OR COALESCE(em.observations, '') LIKE ?)
            """
        )
        params.extend([pattern, pattern, pattern, pattern])
    if status != "all":
        where.append("em.status = ?")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                em.id_maintenance,
                em.equipment_code,
                em.equipment_name,
                em.category,
                em.site_id,
                s.nom AS site,
                em.responsible_employee_id,
                COALESCE(e.nom, e.nom_complet) AS responsable_nom,
                COALESCE(e.prenom, '') AS responsable_prenom,
                em.maintenance_type,
                em.priority,
                CASE
                    WHEN em.status IN ('planifiee', 'en_cours') AND em.planned_date < ? THEN 'en_retard'
                    ELSE em.status
                END AS status,
                em.planned_date,
                em.completed_date,
                em.next_due_date,
                em.cost,
                em.observations
            FROM equipment_maintenance em
            LEFT JOIN sites s ON s.id_site = em.site_id
            LEFT JOIN employes e ON e.id_employe = em.responsible_employee_id
            {where_sql}
            ORDER BY
                CASE em.priority WHEN 'critique' THEN 0 WHEN 'haute' THEN 1 WHEN 'moyenne' THEN 2 ELSE 3 END,
                em.planned_date,
                em.id_maintenance DESC
            LIMIT ?
            """,
            (today, *params),
        ).fetchall()
    return [dict(row) for row in rows]


def create_equipment_maintenance(values: dict[str, Any]) -> int:
    payload = _clean_maintenance_payload(values)
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO equipment_maintenance (
                equipment_code, equipment_name, category, site_id, responsible_employee_id,
                maintenance_type, priority, status, planned_date, completed_date,
                next_due_date, cost, observations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["equipment_code"],
                payload["equipment_name"],
                payload["category"],
                payload["site_id"],
                payload["responsible_employee_id"],
                payload["maintenance_type"],
                payload["priority"],
                payload["status"],
                payload["planned_date"],
                payload["completed_date"],
                payload["next_due_date"],
                payload["cost"],
                payload["observations"],
            ),
        )
        return int(cursor.lastrowid)


def update_equipment_maintenance(maintenance_id: int, values: dict[str, Any]) -> None:
    payload = _clean_maintenance_payload(values)
    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE equipment_maintenance
            SET equipment_code = ?, equipment_name = ?, category = ?, site_id = ?,
                responsible_employee_id = ?, maintenance_type = ?, priority = ?,
                status = ?, planned_date = ?, completed_date = ?, next_due_date = ?,
                cost = ?, observations = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id_maintenance = ?
            """,
            (
                payload["equipment_code"],
                payload["equipment_name"],
                payload["category"],
                payload["site_id"],
                payload["responsible_employee_id"],
                payload["maintenance_type"],
                payload["priority"],
                payload["status"],
                payload["planned_date"],
                payload["completed_date"],
                payload["next_due_date"],
                payload["cost"],
                payload["observations"],
                maintenance_id,
            ),
        )
        if not cursor.rowcount:
            raise ValueError("Maintenance introuvable.")


def delete_equipment_maintenance(maintenance_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute("DELETE FROM equipment_maintenance WHERE id_maintenance = ?", (maintenance_id,))
        if not cursor.rowcount:
            raise ValueError("Maintenance introuvable.")


def list_action_tracker(search: str = "", status: str = "all", limit: int = 200) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    where = []
    params: list[Any] = []
    if search.strip():
        pattern = f"%{search.strip()}%"
        where.append(
            """
            (a.title LIKE ? OR COALESCE(a.description, '') LIKE ? OR COALESCE(a.source, '') LIKE ?)
            """
        )
        params.extend([pattern, pattern, pattern])
    if status != "all":
        where.append("a.status = ?")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                a.id_action,
                a.source,
                a.title,
                a.description,
                a.site_id,
                s.nom AS site,
                a.owner_employee_id,
                COALESCE(e.nom, e.nom_complet) AS owner_nom,
                COALESCE(e.prenom, '') AS owner_prenom,
                a.priority,
                CASE
                    WHEN a.status IN ('ouverte', 'en_cours') AND a.due_date < ? THEN 'en_retard'
                    ELSE a.status
                END AS status,
                a.due_date,
                a.closed_date,
                a.progress
            FROM action_tracker a
            LEFT JOIN sites s ON s.id_site = a.site_id
            LEFT JOIN employes e ON e.id_employe = a.owner_employee_id
            {where_sql}
            ORDER BY
                CASE a.priority WHEN 'critique' THEN 0 WHEN 'haute' THEN 1 WHEN 'moyenne' THEN 2 ELSE 3 END,
                a.due_date,
                a.id_action DESC
            LIMIT ?
            """,
            (today, *params),
        ).fetchall()
    return [dict(row) for row in rows]


def create_action(values: dict[str, Any]) -> int:
    payload = _clean_action_payload(values)
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO action_tracker (
                source, title, description, site_id, owner_employee_id, priority,
                status, due_date, closed_date, progress
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["source"],
                payload["title"],
                payload["description"],
                payload["site_id"],
                payload["owner_employee_id"],
                payload["priority"],
                payload["status"],
                payload["due_date"],
                payload["closed_date"],
                payload["progress"],
            ),
        )
        return int(cursor.lastrowid)


def update_action(action_id: int, values: dict[str, Any]) -> None:
    payload = _clean_action_payload(values)
    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE action_tracker
            SET source = ?, title = ?, description = ?, site_id = ?, owner_employee_id = ?,
                priority = ?, status = ?, due_date = ?, closed_date = ?, progress = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_action = ?
            """,
            (
                payload["source"],
                payload["title"],
                payload["description"],
                payload["site_id"],
                payload["owner_employee_id"],
                payload["priority"],
                payload["status"],
                payload["due_date"],
                payload["closed_date"],
                payload["progress"],
                action_id,
            ),
        )
        if not cursor.rowcount:
            raise ValueError("Action introuvable.")


def delete_action(action_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute("DELETE FROM action_tracker WHERE id_action = ?", (action_id,))
        if not cursor.rowcount:
            raise ValueError("Action introuvable.")


def export_equipment_maintenance_xlsx() -> Path:
    rows = list_equipment_maintenance(limit=1000)
    return export_rows_xlsx(
        "maintenance_equipements.xlsx",
        "Maintenance equipements",
        [
            "Code",
            "Equipement",
            "Categorie",
            "Site",
            "Responsable",
            "Type",
            "Priorite",
            "Statut",
            "Date planifiee",
            "Date terminee",
            "Prochaine echeance",
            "Cout",
            "Observations",
        ],
        [
            [
                row.get("equipment_code") or "",
                row.get("equipment_name") or "",
                row.get("category") or "",
                row.get("site") or "",
                _person_name(row, "responsable_nom", "responsable_prenom"),
                row.get("maintenance_type") or "",
                row.get("priority") or "",
                row.get("status") or "",
                row.get("planned_date") or "",
                row.get("completed_date") or "",
                row.get("next_due_date") or "",
                row.get("cost") or 0,
                row.get("observations") or "",
            ]
            for row in rows
        ],
    )


def export_action_tracker_xlsx() -> Path:
    rows = list_action_tracker(limit=1000)
    return export_rows_xlsx(
        "action_tracker.xlsx",
        "Action tracker",
        ["Source", "Action", "Description", "Site", "Responsable", "Priorite", "Statut", "Echeance", "Cloture", "Avancement"],
        [
            [
                row.get("source") or "",
                row.get("title") or "",
                row.get("description") or "",
                row.get("site") or "",
                _person_name(row, "owner_nom", "owner_prenom"),
                row.get("priority") or "",
                row.get("status") or "",
                row.get("due_date") or "",
                row.get("closed_date") or "",
                f"{row.get('progress') or 0}%",
            ]
            for row in rows
        ],
    )


def _clean_maintenance_payload(values: dict[str, Any]) -> dict[str, Any]:
    maintenance_type = _required_text(values.get("maintenance_type") or "preventive", "Type maintenance")
    status = _required_text(values.get("status") or "planifiee", "Statut")
    priority = _required_text(values.get("priority") or "moyenne", "Priorite")
    if maintenance_type not in MAINTENANCE_TYPES:
        raise ValueError("Type maintenance invalide.")
    if status not in MAINTENANCE_STATUSES:
        raise ValueError("Statut maintenance invalide.")
    if priority not in PRIORITIES:
        raise ValueError("Priorite invalide.")
    return {
        "equipment_code": _optional_text(values.get("equipment_code")),
        "equipment_name": _required_text(values.get("equipment_name"), "Equipement"),
        "category": _optional_text(values.get("category")),
        "site_id": _optional_int(values.get("site_id")),
        "responsible_employee_id": _optional_int(values.get("responsible_employee_id")),
        "maintenance_type": maintenance_type,
        "priority": priority,
        "status": status,
        "planned_date": _date_text(values.get("planned_date"), "Date planifiee"),
        "completed_date": _optional_date(values.get("completed_date"), "Date terminee"),
        "next_due_date": _optional_date(values.get("next_due_date"), "Prochaine echeance"),
        "cost": _optional_float(values.get("cost")) or 0,
        "observations": _optional_text(values.get("observations")),
    }


def _clean_action_payload(values: dict[str, Any]) -> dict[str, Any]:
    status = _required_text(values.get("status") or "ouverte", "Statut")
    priority = _required_text(values.get("priority") or "moyenne", "Priorite")
    if status not in ACTION_STATUSES:
        raise ValueError("Statut action invalide.")
    if priority not in PRIORITIES:
        raise ValueError("Priorite invalide.")
    progress = _optional_int(values.get("progress")) or 0
    if progress < 0 or progress > 100:
        raise ValueError("Avancement invalide: utilise une valeur entre 0 et 100.")
    if status == "terminee" and progress < 100:
        progress = 100
    return {
        "source": _required_text(values.get("source") or "HSE", "Source"),
        "title": _required_text(values.get("title"), "Action"),
        "description": _optional_text(values.get("description")),
        "site_id": _optional_int(values.get("site_id")),
        "owner_employee_id": _optional_int(values.get("owner_employee_id")),
        "priority": priority,
        "status": status,
        "due_date": _date_text(values.get("due_date"), "Echeance"),
        "closed_date": _optional_date(values.get("closed_date"), "Date cloture"),
        "progress": progress,
    }


def _required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Champ obligatoire: {label}")
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    return float(value)


def _date_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{label}: format invalide AAAA-MM-JJ.") from exc
    return text


def _optional_date(value: Any, label: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _date_text(text, label)


def _person_name(row: dict[str, Any], last_key: str, first_key: str) -> str:
    return f"{row.get(last_key) or ''} {row.get(first_key) or ''}".strip()
