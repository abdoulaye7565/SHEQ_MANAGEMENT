from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.db.connection import db_session


BREAK_TYPES = ["break", "annual", "permission", "sick"]
BREAK_STATUSES = ["planifie", "en_cours", "termine", "annule"]
WORK_DAYS_BEFORE_BREAK = 14
DEFAULT_BREAK_DAYS = 7


def list_breaks() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                eb.id_break,
                eb.employe_id,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                b.numero_badge,
                f.nom AS fonction,
                eb.type_break,
                eb.date_debut,
                eb.date_fin,
                eb.statut,
                eb.commentaire
            FROM employee_breaks eb
            JOIN employes e ON e.id_employe = eb.employe_id
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            ORDER BY eb.date_debut DESC, nom, prenom
            """
        ).fetchall()
        return [dict(row) for row in rows]


def list_active_break_employees(reference_date: str | None = None) -> list[dict[str, Any]]:
    target_date = reference_date or date.today().isoformat()
    _parse_date(target_date)
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                eb.id_break,
                eb.employe_id,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                b.numero_badge,
                f.nom AS fonction,
                eb.type_break,
                eb.date_debut,
                eb.date_fin,
                eb.statut,
                eb.commentaire
            FROM employee_breaks eb
            JOIN employes e ON e.id_employe = eb.employe_id
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE eb.statut IN ('planifie', 'en_cours')
              AND eb.date_debut <= ?
              AND eb.date_fin >= ?
            ORDER BY eb.date_fin, nom, prenom
            """,
            (target_date, target_date),
        ).fetchall()
        return [dict(row) for row in rows]


def create_break(values: dict[str, Any]) -> int:
    payload = _clean_payload(values)
    _validate_payload(payload)
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO employee_breaks (
                employe_id, type_break, date_debut, date_fin, statut, commentaire
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload["employe_id"],
                payload["type_break"],
                payload["date_debut"],
                payload["date_fin"],
                payload["statut"],
                payload["commentaire"],
            ),
        )
        return int(cursor.lastrowid)


def create_break_for_employees(values: dict[str, Any]) -> int:
    employee_ids = [int(item) for item in values.get("employee_ids", []) if int(item)]
    if not employee_ids:
        raise ValueError("Selectionne au moins un employe.")

    current_date = date.today().isoformat()
    created = 0
    with db_session() as connection:
        for employee_id in employee_ids:
            payload = _clean_payload({**values, "employe_id": employee_id})
            _validate_payload(payload)
            active = connection.execute(
                """
                SELECT id_break
                FROM employee_breaks
                WHERE employe_id = ?
                  AND statut IN ('planifie', 'en_cours')
                  AND date_fin >= ?
                LIMIT 1
                """,
                (employee_id, current_date),
            ).fetchone()
            if active:
                continue
            connection.execute(
                """
                INSERT INTO employee_breaks (
                    employe_id, type_break, date_debut, date_fin, statut, commentaire
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["employe_id"],
                    payload["type_break"],
                    payload["date_debut"],
                    payload["date_fin"],
                    payload["statut"],
                    payload["commentaire"],
                ),
            )
            created += 1
    return created


def return_employees_to_service(employee_ids: list[int], return_date: str | None = None) -> int:
    if not employee_ids:
        raise ValueError("Selectionne au moins un employe.")
    service_date = return_date or date.today().isoformat()
    _parse_date(service_date)
    with db_session() as connection:
        cursor = connection.execute(
            f"""
            UPDATE employee_breaks
            SET statut = 'termine',
                date_fin = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE employe_id IN ({','.join('?' for _ in employee_ids)})
              AND statut IN ('planifie', 'en_cours')
              AND date_fin >= ?
            """,
            [service_date, *employee_ids, service_date],
        )
        return int(cursor.rowcount or 0)


def update_break_status(break_id: int, statut: str) -> None:
    if statut not in BREAK_STATUSES:
        raise ValueError("Statut de break invalide.")
    with db_session() as connection:
        connection.execute(
            """
            UPDATE employee_breaks
            SET statut = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id_break = ?
            """,
            (statut, break_id),
        )


def delete_break(break_id: int) -> None:
    with db_session() as connection:
        connection.execute("DELETE FROM employee_breaks WHERE id_break = ?", (break_id,))


def list_break_alerts(reference_date: str | None = None) -> dict[str, list[dict[str, Any]]]:
    current_date = _parse_date(reference_date) if reference_date else date.today()
    tomorrow = current_date + timedelta(days=1)
    due_breaks: list[dict[str, Any]] = []
    ending_tomorrow: list[dict[str, Any]] = []

    with db_session() as connection:
        employees = connection.execute(
            """
            SELECT
                e.id_employe,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                b.numero_badge,
                f.nom AS fonction,
                DATE(e.created_at) AS date_reference
            FROM employes e
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
            ORDER BY nom, prenom
            """
        ).fetchall()

        for employee in employees:
            last_break = connection.execute(
                """
                SELECT date_fin
                FROM employee_breaks
                WHERE employe_id = ?
                  AND type_break = 'break'
                  AND statut IN ('planifie', 'en_cours', 'termine')
                ORDER BY date_fin DESC
                LIMIT 1
                """,
                (employee["id_employe"],),
            ).fetchone()
            active_or_future = connection.execute(
                """
                SELECT id_break
                FROM employee_breaks
                WHERE employe_id = ?
                  AND statut IN ('planifie', 'en_cours')
                  AND date_fin >= ?
                LIMIT 1
                """,
                (employee["id_employe"], current_date.isoformat()),
            ).fetchone()

            reference = last_break["date_fin"] if last_break else employee["date_reference"]
            reference_dt = _parse_date(reference)
            days_worked = (current_date - reference_dt).days
            if not active_or_future and days_worked >= WORK_DAYS_BEFORE_BREAK:
                row = dict(employee)
                row["jours_travailles"] = days_worked
                row["date_break_suggeree"] = current_date.isoformat()
                row["date_retour_suggeree"] = (current_date + timedelta(days=DEFAULT_BREAK_DAYS)).isoformat()
                due_breaks.append(row)

        ending_rows = connection.execute(
            """
            SELECT
                eb.id_break,
                eb.employe_id,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                b.numero_badge,
                f.nom AS fonction,
                eb.type_break,
                eb.date_debut,
                eb.date_fin,
                eb.statut
            FROM employee_breaks eb
            JOIN employes e ON e.id_employe = eb.employe_id
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE eb.statut IN ('planifie', 'en_cours')
              AND eb.date_fin = ?
            ORDER BY nom, prenom
            """,
            (tomorrow.isoformat(),),
        ).fetchall()
        ending_tomorrow = [dict(row) for row in ending_rows]

    return {"due_breaks": due_breaks, "ending_tomorrow": ending_tomorrow}


def _clean_payload(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "employe_id": int(values.get("employe_id") or 0),
        "type_break": str(values.get("type_break") or "break").strip(),
        "date_debut": str(values.get("date_debut") or "").strip(),
        "date_fin": str(values.get("date_fin") or "").strip(),
        "statut": str(values.get("statut") or "planifie").strip(),
        "commentaire": str(values.get("commentaire") or "").strip() or None,
    }


def _validate_payload(payload: dict[str, Any]) -> None:
    if not payload["employe_id"]:
        raise ValueError("Employe obligatoire.")
    if payload["type_break"] not in BREAK_TYPES:
        raise ValueError("Type de conge invalide.")
    if payload["statut"] not in BREAK_STATUSES:
        raise ValueError("Statut invalide.")
    start = _parse_date(payload["date_debut"])
    end = _parse_date(payload["date_fin"])
    if end < start:
        raise ValueError("La date de fin doit etre apres la date de debut.")


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Format de date invalide. Utilise AAAA-MM-JJ.") from exc
