from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any

from app.db.connection import db_session


WARNING_DAYS = 60
TRAINING_VALIDITY_MONTHS = 24
TRAINING_DEPARTMENTS = [
    "HSE",
    "Ressources humaines",
    "Operations",
    "Maintenance",
    "Mine",
    "Administration",
    "Sous-traitant",
    "Externe",
]


def list_trainings(search: str = "") -> list[dict[str, Any]]:
    pattern = f"%{search.strip()}%"
    where = ""
    params: tuple[Any, ...] = ()
    if search.strip():
        where = """
        WHERE tt.nom LIKE ?
           OR COALESCE(e.nom_complet, '') LIKE ?
           OR COALESCE(e.nom, '') LIKE ?
           OR COALESCE(e.prenom, '') LIKE ?
           OR COALESCE(b.numero_badge, '') LIKE ?
           OR COALESCE(f.structure_responsable, '') LIKE ?
        """
        params = (pattern, pattern, pattern, pattern, pattern, pattern)
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                f.id_formation,
                f.employe_id,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                e.nom_complet,
                b.numero_badge,
                fn.nom AS fonction,
                f.type_training_id,
                tt.nom AS formation,
                f.date_debut AS date_formation,
                f.date_expiration,
                f.structure_responsable,
                f.facilitateur,
                f.statut
            FROM formations f
            JOIN employes e ON e.id_employe = f.employe_id
            JOIN fonctions fn ON fn.id_fonction = e.fonction_id
            JOIN training_types tt ON tt.id_training_type = f.type_training_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            {where}
            ORDER BY f.date_expiration, formation, nom, prenom
            """,
            params,
        ).fetchall()
        return [_with_training_state(dict(row)) for row in rows]


def create_training(values: dict[str, Any]) -> int:
    payload = _clean_payload(values)
    with db_session() as connection:
        expiration = _add_months(
            payload["date_formation"],
            _training_validity_months(connection, payload["type_training_id"]),
        )
        status = _status_from_expiration(expiration)
        existing = connection.execute(
            """
            SELECT id_formation
            FROM formations
            WHERE employe_id = ? AND type_training_id = ?
            """,
            (payload["employe_id"], payload["type_training_id"]),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE formations
                SET date_debut = ?,
                    date_expiration = ?,
                    facilitateur = ?,
                    structure_responsable = ?,
                    statut = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_formation = ?
                """,
                (
                    payload["date_formation"],
                    expiration,
                    payload["facilitateur"],
                    payload["structure_responsable"],
                    status,
                    existing["id_formation"],
                ),
            )
            return int(existing["id_formation"])
        cursor = connection.execute(
            """
            INSERT INTO formations (
                employe_id, type_training_id, date_debut, date_expiration,
                facilitateur, structure_responsable, statut
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["employe_id"],
                payload["type_training_id"],
                payload["date_formation"],
                expiration,
                payload["facilitateur"],
                payload["structure_responsable"],
                status,
            ),
        )
        return int(cursor.lastrowid)


def create_trainings_for_employees(values: dict[str, Any]) -> int:
    employee_ids = _int_list(values.get("employee_ids"))
    training_type_ids = _int_list(values.get("training_type_ids"))
    if not employee_ids:
        raise ValueError("Selectionne au moins un employe.")
    if not training_type_ids:
        raise ValueError("Selectionne au moins une formation.")
    created_or_updated = 0
    for employee_id in sorted(set(employee_ids)):
        for training_type_id in sorted(set(training_type_ids)):
            create_training(
                {
                    "employe_id": employee_id,
                    "type_training_id": training_type_id,
                    "date_formation": values.get("date_formation"),
                    "facilitateur": values.get("facilitateur"),
                    "structure_responsable": values.get("structure_responsable"),
                }
            )
            created_or_updated += 1
    return created_or_updated


def update_training(training_id: int, values: dict[str, Any]) -> None:
    payload = _clean_payload(values)
    with db_session() as connection:
        expiration = _add_months(
            payload["date_formation"],
            _training_validity_months(connection, payload["type_training_id"]),
        )
        status = _status_from_expiration(expiration)
        duplicate = connection.execute(
            """
            SELECT id_formation
            FROM formations
            WHERE employe_id = ?
              AND type_training_id = ?
              AND id_formation <> ?
            """,
            (payload["employe_id"], payload["type_training_id"], training_id),
        ).fetchone()
        if duplicate:
            connection.execute("DELETE FROM formations WHERE id_formation = ?", (training_id,))
            cursor = connection.execute(
                """
                UPDATE formations
                SET date_debut = ?,
                    date_expiration = ?,
                    facilitateur = ?,
                    structure_responsable = ?,
                    statut = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_formation = ?
                """,
                (
                    payload["date_formation"],
                    expiration,
                    payload["facilitateur"],
                    payload["structure_responsable"],
                    status,
                    duplicate["id_formation"],
                ),
            )
            if not cursor.rowcount:
                raise ValueError("Formation introuvable.")
            return
        cursor = connection.execute(
            """
            UPDATE formations
            SET employe_id = ?,
                type_training_id = ?,
                date_debut = ?,
                date_expiration = ?,
                facilitateur = ?,
                structure_responsable = ?,
                statut = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_formation = ?
            """,
            (
                payload["employe_id"],
                payload["type_training_id"],
                payload["date_formation"],
                expiration,
                payload["facilitateur"],
                payload["structure_responsable"],
                status,
                training_id,
            ),
        )
        if not cursor.rowcount:
            raise ValueError("Formation introuvable.")


def update_trainings_bulk(training_ids: list[int], values: dict[str, Any]) -> int:
    if not training_ids:
        raise ValueError("Selectionne au moins une formation.")
    updated = 0
    for training_id in training_ids:
        existing = get_training(training_id)
        if existing is None:
            continue
        update_training(
            training_id,
            {
                "employe_id": existing["employe_id"],
                "type_training_id": values.get("type_training_id") or existing["type_training_id"],
                "date_formation": values.get("date_formation") or existing["date_formation"],
                "facilitateur": values.get("facilitateur") or existing["facilitateur"],
                "structure_responsable": values.get("structure_responsable") or existing["structure_responsable"],
            },
        )
        updated += 1
    return updated


def get_training(training_id: int) -> dict[str, Any] | None:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT
                id_formation,
                employe_id,
                type_training_id,
                date_debut AS date_formation,
                date_expiration,
                facilitateur,
                structure_responsable,
                statut
            FROM formations
            WHERE id_formation = ?
            """,
            (training_id,),
        ).fetchone()
        return dict(row) if row else None


def delete_training(training_id: int) -> None:
    with db_session() as connection:
        connection.execute("DELETE FROM formations WHERE id_formation = ?", (training_id,))


def create_training_type(name: str) -> int:
    training_name = str(name or "").strip()
    if not training_name:
        raise ValueError("Nom de la formation obligatoire.")
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO training_types (
                nom, categorie, validite_mois, actif
            ) VALUES (?, 'operationnelle', ?, 1)
            """,
            (training_name, TRAINING_VALIDITY_MONTHS),
        )
        if cursor.lastrowid:
            return int(cursor.lastrowid)
        row = connection.execute(
            "SELECT id_training_type FROM training_types WHERE nom = ?",
            (training_name,),
        ).fetchone()
        return int(row["id_training_type"])


def create_training_department(name: str) -> str:
    department_name = str(name or "").strip()
    if not department_name:
        raise ValueError("Nom du departement obligatoire.")
    with db_session() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO training_departments (nom, actif)
            VALUES (?, 1)
            """,
            (department_name,),
        )
    return department_name


def get_training_options() -> dict[str, list[dict[str, Any]]]:
    with db_session() as connection:
        employees = connection.execute(
            """
            SELECT e.id_employe AS value,
                   COALESCE(e.nom, e.nom_complet) || ' ' || COALESCE(e.prenom, '') ||
                   ' - ' || COALESCE(b.numero_badge, 'sans badge') AS label
            FROM employes e
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
            ORDER BY label
            """
        ).fetchall()
        training_types = connection.execute(
            """
            SELECT
                id_training_type AS value,
                nom AS label,
                validite_mois
            FROM training_types
            WHERE actif = 1
            ORDER BY nom
            """
        ).fetchall()
        departments = connection.execute(
            """
            SELECT nom AS value, nom AS label
            FROM training_departments
            WHERE actif = 1
            ORDER BY nom
            """
        ).fetchall()
        return {
            "employees": [dict(row) for row in employees],
            "training_types": [dict(row) for row in training_types],
            "departments": [dict(row) for row in departments],
        }


def get_training_matrix() -> dict[str, Any]:
    today = date.today()
    with db_session() as connection:
        employees = connection.execute(
            """
            SELECT e.id_employe, COALESCE(e.nom, e.nom_complet) AS nom,
                   COALESCE(e.prenom, '') AS prenom, b.numero_badge, fn.nom AS fonction
            FROM employes e
            JOIN fonctions fn ON fn.id_fonction = e.fonction_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
            ORDER BY nom, prenom
            """
        ).fetchall()
        types = connection.execute(
            """
            SELECT id_training_type, nom
            FROM training_types
            WHERE actif = 1
            ORDER BY nom
            """
        ).fetchall()
        latest = connection.execute(
            """
            SELECT f.*
            FROM formations f
            JOIN (
                SELECT employe_id, type_training_id, MAX(date_expiration) AS max_exp
                FROM formations
                GROUP BY employe_id, type_training_id
            ) latest
              ON latest.employe_id = f.employe_id
             AND latest.type_training_id = f.type_training_id
             AND latest.max_exp = f.date_expiration
            """
        ).fetchall()
    lookup = {(row["employe_id"], row["type_training_id"]): dict(row) for row in latest}
    matrix_rows = []
    stats_by_type = {
        int(training_type["id_training_type"]): {
            "type_training_id": int(training_type["id_training_type"]),
            "formation": training_type["nom"],
            "valid": 0,
            "soon": 0,
            "expired": 0,
            "missing": 0,
            "risk": 0,
            "total": 0,
            "compliance": 0,
        }
        for training_type in types
    }
    for employee in employees:
        cells = []
        for training_type in types:
            training_type_id = int(training_type["id_training_type"])
            stats = stats_by_type[training_type_id]
            stats["total"] += 1
            training = lookup.get((employee["id_employe"], training_type["id_training_type"]))
            if not training:
                stats["missing"] += 1
                stats["risk"] += 1
                cells.append(
                    {
                        "status": "missing",
                        "label": "Non faite",
                        "date_expiration": "",
                        "date_formation": "",
                        "days_left": None,
                        "type_training_id": training_type["id_training_type"],
                        "training_name": training_type["nom"],
                    }
                )
                continue
            expiration = datetime.strptime(training["date_expiration"], "%Y-%m-%d").date()
            days_left = (expiration - today).days
            if days_left < 0:
                status = "expired"
                label = f"Expiree {training['date_expiration']}"
                stats["expired"] += 1
                stats["risk"] += 1
            elif days_left <= WARNING_DAYS:
                status = "soon"
                label = f"J-{days_left} {training['date_expiration']}"
                stats["soon"] += 1
            else:
                status = "done"
                label = training["date_expiration"]
                stats["valid"] += 1
            cells.append(
                {
                    "status": status,
                    "label": label,
                    "date_expiration": training["date_expiration"],
                    "date_formation": training["date_debut"],
                    "days_left": days_left,
                    "type_training_id": training_type["id_training_type"],
                    "training_name": training_type["nom"],
                    "latest_training_id": training["id_formation"],
                }
            )
        matrix_rows.append({"employee": dict(employee), "cells": cells})
    for stats in stats_by_type.values():
        stats["compliance"] = round(stats["valid"] * 100 / stats["total"]) if stats["total"] else 0
    total_cells = len(matrix_rows) * len(types)
    valid = sum(stats["valid"] for stats in stats_by_type.values())
    soon = sum(stats["soon"] for stats in stats_by_type.values())
    expired = sum(stats["expired"] for stats in stats_by_type.values())
    missing = sum(stats["missing"] for stats in stats_by_type.values())
    summary = {
        "employees": len(matrix_rows),
        "training_types": len(types),
        "total_cells": total_cells,
        "valid": valid,
        "soon": soon,
        "expired": expired,
        "missing": missing,
        "risk": soon + expired + missing,
        "compliance": round(valid * 100 / total_cells) if total_cells else 0,
    }
    return {
        "training_types": [dict(row) for row in types],
        "rows": matrix_rows,
        "summary": summary,
        "training_stats": list(stats_by_type.values()),
    }


def _clean_payload(values: dict[str, Any]) -> dict[str, Any]:
    employee_id = int(values.get("employe_id") or 0)
    training_id = int(values.get("type_training_id") or 0)
    training_date = str(values.get("date_formation") or "").strip()
    structure = str(values.get("structure_responsable") or "").strip()
    facilitator = str(values.get("facilitateur") or "").strip() or None
    if not employee_id:
        raise ValueError("Employe obligatoire.")
    if not training_id:
        raise ValueError("Nom de la formation obligatoire.")
    training_dt = _parse_date(training_date)
    if training_dt > date.today():
        raise ValueError("La date de formation ne peut pas etre dans le futur.")
    if not structure:
        raise ValueError("Structure responsable obligatoire.")
    return {
        "employe_id": employee_id,
        "type_training_id": training_id,
        "date_formation": training_date,
        "facilitateur": facilitator,
        "structure_responsable": structure,
    }


def _int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [int(item) for item in value if int(item or 0)]
    if isinstance(value, str):
        return [int(item.strip()) for item in value.split(",") if int(item.strip() or 0)]
    item = int(value or 0)
    return [item] if item else []


def _training_validity_months(connection: Any, training_type_id: int) -> int:
    row = connection.execute(
        """
        SELECT id_training_type
        FROM training_types
        WHERE id_training_type = ?
        """,
        (training_type_id,),
    ).fetchone()
    if row is None:
        raise ValueError("Nom de la formation introuvable.")
    return TRAINING_VALIDITY_MONTHS


def _with_training_state(row: dict[str, Any]) -> dict[str, Any]:
    row["etat"] = _status_from_expiration(row["date_expiration"])
    return row


def _status_from_expiration(expiration: str) -> str:
    days_left = (_parse_date(expiration) - date.today()).days
    if days_left < 0:
        return "expiree"
    if days_left <= WARNING_DAYS:
        return "bientot_expiree"
    return "valide"


def _add_months(value: str, months: int) -> str:
    start = _parse_date(value)
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Format date invalide. Utilise AAAA-MM-JJ.") from exc
