from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.db.connection import db_session
from app.config import EXPORTS_DIR
from app.services.attendance_export_service import _unique_export_path, export_rows_xlsx, export_styled_rows_xlsx
from app.services.xlsx_service import write_equipment_maintenance_xlsx


MAINTENANCE_TYPES = {"preventive", "corrective", "inspection", "calibration", "oil_change"}
MAINTENANCE_STATUSES = {"planifiee", "en_cours", "terminee", "annulee", "en_retard"}
ACTION_STATUSES = {"ouverte", "en_cours", "terminee", "annulee", "en_retard"}
PRIORITIES = {"basse", "moyenne", "haute", "critique"}
RISK_STATUSES = {"open", "in_progress", "controlled", "closed"}
CONTROL_HIERARCHY = {"elimination", "substitution", "engineering", "administrative", "ppe"}


def get_maintenance_action_summary() -> dict[str, int | float]:
    today = date.today().isoformat()
    with db_session() as connection:
        maintenance = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('planifiee', 'en_cours') THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status IN ('planifiee', 'en_cours') AND (planned_date < ? OR (next_due_date IS NOT NULL AND next_due_date <= ?) OR (next_due_odometer IS NOT NULL AND current_odometer IS NOT NULL AND current_odometer >= next_due_odometer)) THEN 1 ELSE 0 END) AS late_count,
                SUM(CASE WHEN status IN ('planifiee', 'en_cours') AND next_due_odometer IS NOT NULL AND current_odometer IS NOT NULL AND current_odometer >= next_due_odometer THEN 1 ELSE 0 END) AS odometer_due_count,
                SUM(CASE WHEN priority = 'critique' AND status NOT IN ('terminee', 'annulee') THEN 1 ELSE 0 END) AS critical_count,
                COALESCE(SUM(cost), 0) AS cost_total
            FROM equipment_maintenance
            """,
            (today, today),
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
        risks = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status NOT IN ('controlled', 'closed') THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN level_initial IN ('high', 'critical') THEN 1 ELSE 0 END) AS high_initial,
                SUM(CASE WHEN level_residual IN ('high', 'critical') AND status NOT IN ('closed') THEN 1 ELSE 0 END) AS high_residual,
                SUM(CASE WHEN status NOT IN ('controlled', 'closed') AND due_date IS NOT NULL AND due_date < ? THEN 1 ELSE 0 END) AS late_count
            FROM risk_assessments
            """,
            (today,),
        ).fetchone()
    return {
        "maintenance_total": int(maintenance["total"] or 0),
        "maintenance_open": int(maintenance["open_count"] or 0),
        "maintenance_late": int(maintenance["late_count"] or 0),
        "maintenance_odometer_due": int(maintenance["odometer_due_count"] or 0),
        "maintenance_critical": int(maintenance["critical_count"] or 0),
        "maintenance_cost": round(float(maintenance["cost_total"] or 0), 2),
        "actions_total": int(actions["total"] or 0),
        "actions_open": int(actions["open_count"] or 0),
        "actions_late": int(actions["late_count"] or 0),
        "actions_critical": int(actions["critical_count"] or 0),
        "risks_total": int(risks["total"] or 0),
        "risks_open": int(risks["open_count"] or 0),
        "risks_high_initial": int(risks["high_initial"] or 0),
        "risks_high_residual": int(risks["high_residual"] or 0),
        "risks_late": int(risks["late_count"] or 0),
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
                em.next_due_date,
                em.current_odometer,
                em.next_due_odometer,
                s.nom AS site
            FROM equipment_maintenance em
            LEFT JOIN sites s ON s.id_site = em.site_id
            WHERE em.status IN ('planifiee', 'en_cours')
              AND (
                  em.planned_date < ?
                  OR (em.next_due_date IS NOT NULL AND em.next_due_date <= ?)
                  OR (em.next_due_odometer IS NOT NULL AND em.current_odometer IS NOT NULL AND em.current_odometer >= em.next_due_odometer)
                  OR em.priority = 'critique'
              )
            ORDER BY em.planned_date, em.priority
            """,
            (today, today),
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
    if status == "en_retard":
        where.append(
            """
            (em.status = 'en_retard'
             OR (em.status IN ('planifiee', 'en_cours')
                 AND (em.planned_date < ?
                      OR (em.next_due_date IS NOT NULL AND em.next_due_date <= ?)
                      OR (em.next_due_odometer IS NOT NULL AND em.current_odometer IS NOT NULL AND em.current_odometer >= em.next_due_odometer))))
            """
        )
        params.extend([today, today])
    elif status != "all":
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
                    WHEN em.status IN ('planifiee', 'en_cours') AND (em.planned_date < ? OR (em.next_due_date IS NOT NULL AND em.next_due_date <= ?) OR (em.next_due_odometer IS NOT NULL AND em.current_odometer IS NOT NULL AND em.current_odometer >= em.next_due_odometer)) THEN 'en_retard'
                    ELSE em.status
                END AS status,
                CASE
                    WHEN em.next_due_odometer IS NOT NULL AND em.current_odometer IS NOT NULL THEN em.next_due_odometer - em.current_odometer
                    ELSE NULL
                END AS remaining_km,
                em.planned_date,
                em.completed_date,
                em.next_due_date,
                em.current_odometer,
                em.last_service_odometer,
                em.service_interval_km,
                em.next_due_odometer,
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
            (today, today, *params),
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
                next_due_date, current_odometer, last_service_odometer, service_interval_km,
                next_due_odometer, cost, observations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                payload["current_odometer"],
                payload["last_service_odometer"],
                payload["service_interval_km"],
                payload["next_due_odometer"],
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
                current_odometer = ?, last_service_odometer = ?, service_interval_km = ?,
                next_due_odometer = ?, cost = ?, observations = ?, updated_at = CURRENT_TIMESTAMP
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
                payload["current_odometer"],
                payload["last_service_odometer"],
                payload["service_interval_km"],
                payload["next_due_odometer"],
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


def list_risk_assessments(search: str = "", status: str = "all", limit: int = 200) -> list[dict[str, Any]]:
    where = []
    params: list[Any] = []
    if search.strip():
        pattern = f"%{search.strip()}%"
        where.append(
            """
            (ra.activity LIKE ? OR COALESCE(ra.task, '') LIKE ? OR ra.hazard LIKE ?
             OR ra.risk_event LIKE ? OR ra.consequences LIKE ? OR COALESCE(ra.additional_controls, '') LIKE ?)
            """
        )
        params.extend([pattern, pattern, pattern, pattern, pattern, pattern])
    if status != "all":
        where.append("ra.status = ?")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                ra.*,
                s.nom AS site,
                COALESCE(e.nom, e.nom_complet) AS owner_nom,
                COALESCE(e.prenom, '') AS owner_prenom
            FROM risk_assessments ra
            LEFT JOIN sites s ON s.id_site = ra.site_id
            LEFT JOIN employes e ON e.id_employe = ra.owner_employee_id
            {where_sql}
            ORDER BY
                CASE ra.level_residual WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                CASE ra.level_initial WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                COALESCE(ra.review_date, ra.due_date, ra.created_at),
                ra.id_risk DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def create_risk_assessment(values: dict[str, Any]) -> int:
    payload = _clean_risk_payload(values)
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO risk_assessments (
                activity, task, hazard, risk_event, consequences, existing_controls,
                site_id, owner_employee_id, probability_initial, severity_initial,
                risk_initial, level_initial, hierarchy_control, additional_controls,
                probability_residual, severity_residual, risk_residual, level_residual,
                status, due_date, review_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _risk_payload_tuple(payload),
        )
        return int(cursor.lastrowid)


def update_risk_assessment(risk_id: int, values: dict[str, Any]) -> None:
    payload = _clean_risk_payload(values)
    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE risk_assessments
            SET activity = ?, task = ?, hazard = ?, risk_event = ?, consequences = ?,
                existing_controls = ?, site_id = ?, owner_employee_id = ?,
                probability_initial = ?, severity_initial = ?, risk_initial = ?,
                level_initial = ?, hierarchy_control = ?, additional_controls = ?,
                probability_residual = ?, severity_residual = ?, risk_residual = ?,
                level_residual = ?, status = ?, due_date = ?, review_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_risk = ?
            """,
            (*_risk_payload_tuple(payload), int(risk_id)),
        )
        if not cursor.rowcount:
            raise ValueError("Evaluation des risques introuvable.")


def delete_risk_assessment(risk_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute("DELETE FROM risk_assessments WHERE id_risk = ?", (int(risk_id),))
        if not cursor.rowcount:
            raise ValueError("Evaluation des risques introuvable.")


def export_equipment_maintenance_xlsx() -> Path:
    rows = list_equipment_maintenance(limit=1000)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("maintenance_equipements_orezone.xlsx")
    workbook_rows = [
        {
            **row,
            "responsible": _person_name(row, "responsable_nom", "responsable_prenom"),
        }
        for row in rows
    ]
    summary = {
        "total": len(rows),
        "open": sum(1 for row in rows if row.get("status") in ("planifiee", "en_cours", "en_retard")),
        "late": sum(1 for row in rows if row.get("status") == "en_retard"),
        "odometer_due": sum(
            1
            for row in rows
            if row.get("current_odometer") is not None
            and row.get("next_due_odometer") is not None
            and float(row.get("current_odometer") or 0) >= float(row.get("next_due_odometer") or 0)
        ),
        "critical": sum(1 for row in rows if row.get("priority") == "critique" and row.get("status") not in ("terminee", "annulee")),
        "cost": round(sum(float(row.get("cost") or 0) for row in rows), 2),
    }
    try:
        write_equipment_maintenance_xlsx(output_path, workbook_rows, datetime.now().strftime("%Y-%m-%d %H:%M"), summary)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("maintenance_equipements_orezone_nouveau.xlsx")
        write_equipment_maintenance_xlsx(fallback, workbook_rows, datetime.now().strftime("%Y-%m-%d %H:%M"), summary)
        return fallback


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


def export_risk_assessments_xlsx() -> Path:
    rows = list_risk_assessments(limit=1000)
    headers = [
        "Activite",
        "Tache",
        "Danger",
        "Evenement redoute",
        "Consequences",
        "Controles existants",
        "Site",
        "Responsable",
        "P init.",
        "G init.",
        "Score init.",
        "Niveau init.",
        "Hierarchie controle",
        "Mesures complementaires",
        "P resid.",
        "G resid.",
        "Score resid.",
        "Niveau resid.",
        "Statut",
        "Echeance",
        "Revue",
    ]
    data_rows: list[list[Any]] = []
    styles: list[list[str | None]] = []
    summary = _risk_export_summary(rows)
    data_rows.extend(
        [
            [
                "Risk assessment summary",
                f"Total: {summary['total']}",
                f"Critical initial: {summary['critical_initial']}",
                f"High initial: {summary['high_initial']}",
                f"Critical residual: {summary['critical_residual']}",
                f"High residual: {summary['high_residual']}",
                f"Open: {summary['open']}",
                f"Controlled/closed: {summary['controlled']}",
            ],
            [],
            ["Legend", "Low", "Medium", "High", "Critical", "Controlled", "ISO hierarchy: Elimination > Substitution > Engineering > Administrative > PPE"],
            [],
        ]
    )
    styles.extend(
        [
            ["section", "done", "danger", "soon", "danger", "soon", "section", "done"],
            [],
            ["section", "done", "standard", "soon", "danger", "done", "section"],
            [],
        ]
    )
    for row in rows:
        data_rows.append(
            [
                row.get("activity") or "",
                row.get("task") or "",
                row.get("hazard") or "",
                row.get("risk_event") or "",
                row.get("consequences") or "",
                row.get("existing_controls") or "",
                row.get("site") or "",
                _person_name(row, "owner_nom", "owner_prenom"),
                row.get("probability_initial") or 0,
                row.get("severity_initial") or 0,
                row.get("risk_initial") or 0,
                _risk_level_label(row.get("level_initial")),
                _control_label(row.get("hierarchy_control")),
                row.get("additional_controls") or "",
                row.get("probability_residual") or 0,
                row.get("severity_residual") or 0,
                row.get("risk_residual") or 0,
                _risk_level_label(row.get("level_residual")),
                _risk_status_label(row.get("status")),
                row.get("due_date") or "",
                row.get("review_date") or "",
            ]
        )
        styles.append(
            [
                None,
                None,
                _risk_level_style(row.get("level_initial")),
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                _risk_level_style(row.get("level_initial")),
                _risk_level_style(row.get("level_initial")),
                _control_style(row.get("hierarchy_control")),
                None,
                None,
                None,
                _risk_level_style(row.get("level_residual")),
                _risk_level_style(row.get("level_residual")),
                _risk_status_style(row.get("status")),
                None,
                None,
            ]
        )
    return export_styled_rows_xlsx(
        "evaluation_risques_iso.xlsx",
        "OREZONE Risk Register",
        headers,
        data_rows,
        styles,
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
    current_odometer = _optional_float(values.get("current_odometer"))
    last_service_odometer = _optional_float(values.get("last_service_odometer"))
    service_interval_km = _optional_float(values.get("service_interval_km"))
    next_due_odometer = _optional_float(values.get("next_due_odometer"))
    for label, number in (
        ("Compteur actuel", current_odometer),
        ("Derniere maintenance km", last_service_odometer),
        ("Intervalle km", service_interval_km),
        ("Prochaine maintenance km", next_due_odometer),
    ):
        if number is not None and number < 0:
            raise ValueError(f"{label}: utilise une valeur positive.")
    if next_due_odometer is None and last_service_odometer is not None and service_interval_km is not None:
        next_due_odometer = last_service_odometer + service_interval_km
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
        "current_odometer": current_odometer,
        "last_service_odometer": last_service_odometer,
        "service_interval_km": service_interval_km,
        "next_due_odometer": next_due_odometer,
        "cost": _optional_float(values.get("cost")) or 0,
        "observations": _optional_text(values.get("observations")),
    }


def _clean_risk_payload(values: dict[str, Any]) -> dict[str, Any]:
    probability_initial = _scale_value(values.get("probability_initial"), "Probabilite initiale")
    severity_initial = _scale_value(values.get("severity_initial"), "Gravite initiale")
    probability_residual = _scale_value(values.get("probability_residual"), "Probabilite residuelle")
    severity_residual = _scale_value(values.get("severity_residual"), "Gravite residuelle")
    risk_initial = probability_initial * severity_initial
    risk_residual = probability_residual * severity_residual
    hierarchy_control = _required_text(values.get("hierarchy_control") or "administrative", "Hierarchie de controle")
    status = _required_text(values.get("status") or "open", "Statut")
    if hierarchy_control not in CONTROL_HIERARCHY:
        raise ValueError("Hierarchie de controle invalide.")
    if status not in RISK_STATUSES:
        raise ValueError("Statut risque invalide.")
    return {
        "activity": _required_text(values.get("activity"), "Activite"),
        "task": _optional_text(values.get("task")),
        "hazard": _required_text(values.get("hazard"), "Danger"),
        "risk_event": _required_text(values.get("risk_event"), "Evenement redoute"),
        "consequences": _required_text(values.get("consequences"), "Consequences"),
        "existing_controls": _optional_text(values.get("existing_controls")),
        "site_id": _optional_int(values.get("site_id")),
        "owner_employee_id": _optional_int(values.get("owner_employee_id")),
        "probability_initial": probability_initial,
        "severity_initial": severity_initial,
        "risk_initial": risk_initial,
        "level_initial": _risk_level(risk_initial),
        "hierarchy_control": hierarchy_control,
        "additional_controls": _optional_text(values.get("additional_controls")),
        "probability_residual": probability_residual,
        "severity_residual": severity_residual,
        "risk_residual": risk_residual,
        "level_residual": _risk_level(risk_residual),
        "status": status,
        "due_date": _optional_date(values.get("due_date"), "Echeance"),
        "review_date": _optional_date(values.get("review_date"), "Date de revue"),
    }


def _risk_payload_tuple(payload: dict[str, Any]) -> tuple[Any, ...]:
    return (
        payload["activity"],
        payload["task"],
        payload["hazard"],
        payload["risk_event"],
        payload["consequences"],
        payload["existing_controls"],
        payload["site_id"],
        payload["owner_employee_id"],
        payload["probability_initial"],
        payload["severity_initial"],
        payload["risk_initial"],
        payload["level_initial"],
        payload["hierarchy_control"],
        payload["additional_controls"],
        payload["probability_residual"],
        payload["severity_residual"],
        payload["risk_residual"],
        payload["level_residual"],
        payload["status"],
        payload["due_date"],
        payload["review_date"],
    )


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


def _scale_value(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: utilise une valeur de 1 a 5.") from exc
    if number < 1 or number > 5:
        raise ValueError(f"{label}: utilise une valeur de 1 a 5.")
    return number


def _risk_level(score: int) -> str:
    if score >= 17:
        return "critical"
    if score >= 10:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _risk_level_label(value: Any) -> str:
    return {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    }.get(str(value or ""), str(value or "-"))


def _risk_export_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(rows),
        "critical_initial": sum(1 for row in rows if row.get("level_initial") == "critical"),
        "high_initial": sum(1 for row in rows if row.get("level_initial") == "high"),
        "critical_residual": sum(1 for row in rows if row.get("level_residual") == "critical"),
        "high_residual": sum(1 for row in rows if row.get("level_residual") == "high"),
        "open": sum(1 for row in rows if row.get("status") in ("open", "in_progress")),
        "controlled": sum(1 for row in rows if row.get("status") in ("controlled", "closed")),
    }


def _risk_level_style(value: Any) -> str:
    return {
        "low": "done",
        "medium": "standard",
        "high": "soon",
        "critical": "danger",
    }.get(str(value or ""), "unfilled")


def _risk_status_style(value: Any) -> str:
    return {
        "open": "soon",
        "in_progress": "standard",
        "controlled": "done",
        "closed": "rest",
    }.get(str(value or ""), "unfilled")


def _control_style(value: Any) -> str:
    return {
        "elimination": "done",
        "substitution": "done",
        "engineering": "standard",
        "administrative": "soon",
        "ppe": "annual",
    }.get(str(value or ""), "unfilled")


def _risk_status_label(value: Any) -> str:
    return {
        "open": "Open",
        "in_progress": "In progress",
        "controlled": "Controlled",
        "closed": "Closed",
    }.get(str(value or ""), str(value or "-"))


def _control_label(value: Any) -> str:
    return {
        "elimination": "Elimination",
        "substitution": "Substitution",
        "engineering": "Engineering control",
        "administrative": "Administrative control",
        "ppe": "PPE",
    }.get(str(value or ""), str(value or "-"))


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
