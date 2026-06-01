from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from app.db.connection import db_session


EMPLOYEE_TYPES = ["national", "expatriate"]
EMPLOYEE_STATUSES = ["actif", "inactif", "suspendu"]
BADGE_STATUSES = ["valide", "suspendu", "non conforme"]
DEPARTURE_TYPES = ["licencie", "demissionne", "autre"]
BADGE_WARNING_DAYS = 30
BADGE_VALIDITY_MONTHS = 24


def list_options(table: str, pk: str, label: str, active_column: str | None = "actif") -> list[dict[str, Any]]:
    where = f"WHERE {active_column} = 1" if active_column else ""
    with db_session() as connection:
        rows = connection.execute(
            f"SELECT {pk} AS value, {label} AS label FROM {table} {where} ORDER BY {label}"
        ).fetchall()
        return [dict(row) for row in rows]


def list_site_options() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                s.id_site AS value,
                CASE
                    WHEN d.nom IS NULL THEN s.nom
                    ELSE s.nom || ' - ' || d.nom
                END AS label
            FROM sites s
            LEFT JOIN departments d ON d.id_department = s.department_id
            WHERE s.actif = 1
            ORDER BY CASE WHEN s.nom = 'SYAMA' THEN 0 ELSE 1 END, s.nom
            """
        ).fetchall()
        return [dict(row) for row in rows]


def list_employees(search: str = "", include_inactive: bool = False, employee_id: int | None = None) -> list[dict[str, Any]]:
    current_date = date.today().isoformat()
    pattern = f"%{search.strip()}%"
    search_clause = """
        (e.nom_complet LIKE ?
         OR COALESCE(e.nom, '') LIKE ?
         OR COALESCE(e.prenom, '') LIKE ?
         OR COALESCE(e.matricule, '') LIKE ?
         OR COALESCE(b.numero_badge, '') LIKE ?
         OR f.nom LIKE ?
         OR s.nom LIKE ?)
    """
    conditions: list[str] = []
    filter_params: list[Any] = []
    if not include_inactive:
        conditions.append("e.statut = 'actif'")
    if employee_id is not None:
        conditions.append("e.id_employe = ?")
        filter_params.append(employee_id)
    if search.strip():
        conditions.append(search_clause)
        filter_params.extend([pattern, pattern, pattern, pattern, pattern, pattern, pattern])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params: tuple[Any, ...] = (current_date, current_date, current_date, current_date, current_date, *filter_params)

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                e.id_employe,
                e.matricule,
                e.nom,
                e.prenom,
                e.nom_complet,
                e.fonction_id,
                f.nom AS fonction,
                e.site_id,
                s.nom AS site,
                d.nom AS departement_site,
                e.groupe_id,
                g.nom AS groupe,
                e.shift_id,
                sh.code AS shift_code,
                sh.libelle AS shift,
                e.type_employe,
                e.statut AS statut_employe,
                e.departure_type,
                e.departure_date,
                e.departure_comment,
                b.id_badge,
                b.numero_badge,
                b.statut AS statut_badge,
                b.date_remise,
                b.date_expiration AS date_expiration_badge,
                COALESCE(active_break.type_break, 'work') AS current_state,
                active_break.date_debut AS current_state_start,
                active_break.date_fin AS current_state_end,
                planned_break.date_debut AS next_planned_break_start,
                planned_break.date_fin AS next_planned_break_end,
                DATE(
                    COALESCE(last_break.date_fin, DATE(e.created_at)),
                    '+14 days'
                ) AS next_break_due_date,
                CAST(
                    JULIANDAY(DATE(
                        COALESCE(last_break.date_fin, DATE(e.created_at)),
                        '+14 days'
                    )) - JULIANDAY(?)
                    AS INTEGER
                ) AS days_until_break_due
            FROM employes e
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            JOIN sites s ON s.id_site = e.site_id
            LEFT JOIN departments d ON d.id_department = s.department_id
            LEFT JOIN groupes g ON g.id_groupe = e.groupe_id
            JOIN shifts sh ON sh.id_shift = e.shift_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            LEFT JOIN employee_breaks active_break
              ON active_break.id_break = (
                SELECT eb.id_break
                FROM employee_breaks eb
                WHERE eb.employe_id = e.id_employe
                  AND eb.statut IN ('planifie', 'en_cours')
                  AND eb.date_debut <= ?
                  AND eb.date_fin >= ?
                ORDER BY eb.date_debut DESC, eb.id_break DESC
                LIMIT 1
              )
            LEFT JOIN employee_breaks planned_break
              ON planned_break.id_break = (
                SELECT eb.id_break
                FROM employee_breaks eb
                WHERE eb.employe_id = e.id_employe
                  AND eb.type_break = 'break'
                  AND eb.statut IN ('planifie', 'en_cours')
                  AND eb.date_fin >= ?
                ORDER BY eb.date_debut ASC, eb.id_break ASC
                LIMIT 1
              )
            LEFT JOIN employee_breaks last_break
              ON last_break.id_break = (
                SELECT eb.id_break
                FROM employee_breaks eb
                WHERE eb.employe_id = e.id_employe
                  AND eb.type_break = 'break'
                  AND eb.statut IN ('planifie', 'en_cours', 'termine')
                  AND eb.date_fin < ?
                ORDER BY eb.date_fin DESC, eb.id_break DESC
                LIMIT 1
              )
            {where}
            ORDER BY e.nom_complet
            """,
            params,
        ).fetchall()
        return [_with_badge_validity(dict(row)) for row in rows]


def get_employee(employee_id: int) -> dict[str, Any] | None:
    rows = list_employees(include_inactive=True, employee_id=employee_id)
    return rows[0] if rows else None


def list_former_employees(search: str = "") -> list[dict[str, Any]]:
    rows = list_employees(search=search, include_inactive=True)
    return [
        row
        for row in rows
        if row.get("statut_employe") == "inactif" and row.get("departure_type")
    ]


def create_employee(values: dict[str, Any]) -> int:
    payload = _clean_payload(values)
    _validate_payload(payload)

    try:
        with db_session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO employes (
                    matricule, nom, prenom, nom_complet, fonction_id, site_id, groupe_id,
                    shift_id, type_employe, statut
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["matricule"],
                    payload["nom"],
                    payload["prenom"],
                    payload["nom_complet"],
                    payload["fonction_id"],
                    payload["site_id"],
                    payload["groupe_id"],
                    payload["shift_id"],
                    payload["type_employe"],
                    payload["statut_employe"],
                ),
            )
            employee_id = int(cursor.lastrowid)
            if payload["numero_badge"]:
                connection.execute(
                    """
                    INSERT INTO badges (employe_id, numero_badge, statut, date_remise, date_expiration)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        employee_id,
                        payload["numero_badge"],
                        payload["statut_badge"],
                        payload["date_remise"],
                        payload["date_expiration_badge"],
                    ),
                )
            _open_site_assignment(
                connection,
                employee_id,
                int(payload["site_id"]),
                date.today().isoformat(),
                "Affectation initiale",
            )
            return employee_id
    except sqlite3.IntegrityError as exc:
        raise ValueError(_friendly_integrity_error(exc)) from exc


def update_employee(employee_id: int, values: dict[str, Any]) -> None:
    payload = _clean_payload(values)
    _validate_payload(payload)

    try:
        with db_session() as connection:
            current = connection.execute(
                "SELECT site_id FROM employes WHERE id_employe = ?",
                (employee_id,),
            ).fetchone()
            if current is None:
                raise ValueError("Employe introuvable.")
            connection.execute(
                """
                UPDATE employes
                SET matricule = ?, nom = ?, prenom = ?, nom_complet = ?, fonction_id = ?, site_id = ?,
                    groupe_id = ?, shift_id = ?, type_employe = ?, statut = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_employe = ?
                """,
                (
                    payload["matricule"],
                    payload["nom"],
                    payload["prenom"],
                    payload["nom_complet"],
                    payload["fonction_id"],
                    payload["site_id"],
                    payload["groupe_id"],
                    payload["shift_id"],
                    payload["type_employe"],
                    payload["statut_employe"],
                    employee_id,
                ),
            )
            if int(current["site_id"]) != int(payload["site_id"]):
                _change_site_assignment(
                    connection,
                    employee_id,
                    int(payload["site_id"]),
                    date.today().isoformat(),
                    "Modification fiche employe",
                )

            existing_badge = connection.execute(
                "SELECT id_badge FROM badges WHERE employe_id = ?",
                (employee_id,),
            ).fetchone()

            if payload["numero_badge"]:
                if existing_badge:
                    connection.execute(
                        """
                        UPDATE badges
                        SET numero_badge = ?, statut = ?, date_remise = ?, date_expiration = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE employe_id = ?
                        """,
                        (
                            payload["numero_badge"],
                            payload["statut_badge"],
                            payload["date_remise"],
                            payload["date_expiration_badge"],
                            employee_id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO badges (employe_id, numero_badge, statut, date_remise, date_expiration)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            employee_id,
                            payload["numero_badge"],
                            payload["statut_badge"],
                            payload["date_remise"],
                            payload["date_expiration_badge"],
                        ),
                    )
            elif existing_badge:
                connection.execute("DELETE FROM badges WHERE employe_id = ?", (employee_id,))
    except sqlite3.IntegrityError as exc:
        raise ValueError(_friendly_integrity_error(exc)) from exc


def delete_employee(employee_id: int) -> None:
    try:
        with db_session() as connection:
            connection.execute("DELETE FROM badges WHERE employe_id = ?", (employee_id,))
            connection.execute("DELETE FROM employes WHERE id_employe = ?", (employee_id,))
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            "Suppression impossible: cet employe est deja utilise dans un autre module."
        ) from exc


def mark_employee_departure(
    employee_id: int,
    departure_type: str,
    departure_date: str,
    comment: str | None = None,
) -> None:
    if departure_type not in DEPARTURE_TYPES:
        raise ValueError("Motif de sortie invalide.")
    if not departure_date:
        raise ValueError("Date de sortie obligatoire.")
    try:
        date.fromisoformat(departure_date)
    except ValueError as exc:
        raise ValueError("Format date invalide. Utilise AAAA-MM-JJ.") from exc

    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE employes
            SET statut = 'inactif',
                departure_type = ?,
                departure_date = ?,
                departure_comment = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_employe = ?
            """,
            (departure_type, departure_date, str(comment or "").strip() or None, employee_id),
        )
        if not cursor.rowcount:
            raise ValueError("Employe introuvable.")
        connection.execute(
            """
            UPDATE employee_breaks
            SET statut = 'annule', updated_at = CURRENT_TIMESTAMP
            WHERE employe_id = ?
              AND statut IN ('planifie', 'en_cours')
            """,
            (employee_id,),
        )


def restore_employee(employee_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE employes
            SET statut = 'actif',
                departure_type = NULL,
                departure_date = NULL,
                departure_comment = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_employe = ?
            """,
            (employee_id,),
        )
        if not cursor.rowcount:
            raise ValueError("Employe introuvable.")


def update_employee_shift(employee_ids: list[int], shift_code: str) -> int:
    if not employee_ids:
        raise ValueError("Selectionne au moins un employe.")
    if shift_code not in {"DAY", "NIGHT"}:
        raise ValueError("Shift invalide. Choisis Day ou Night.")

    with db_session() as connection:
        shift = connection.execute(
            "SELECT id_shift FROM shifts WHERE code = ?",
            (shift_code,),
        ).fetchone()
        if shift is None:
            raise ValueError("Shift introuvable dans les referentiels.")
        cursor = connection.execute(
            f"""
            UPDATE employes
            SET shift_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id_employe IN ({','.join('?' for _ in employee_ids)})
            """,
            [shift["id_shift"], *employee_ids],
        )
        return int(cursor.rowcount or 0)


def get_employee_form_options() -> dict[str, list[dict[str, Any]]]:
    return {
        "fonctions": list_options("fonctions", "id_fonction", "nom"),
        "sites": list_site_options(),
        "groupes": list_options("groupes", "id_groupe", "nom"),
        "shifts": list_options("shifts", "id_shift", "libelle", active_column=None),
    }


def list_employee_site_assignments(employee_id: int) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                esa.id_assignment,
                esa.employe_id,
                esa.site_id,
                s.nom AS site,
                d.nom AS departement_site,
                esa.date_debut,
                esa.date_fin,
                esa.motif
            FROM employee_site_assignments esa
            JOIN sites s ON s.id_site = esa.site_id
            LEFT JOIN departments d ON d.id_department = s.department_id
            WHERE esa.employe_id = ?
            ORDER BY esa.date_debut DESC, esa.id_assignment DESC
            """,
            (employee_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def _open_site_assignment(
    connection: Any,
    employee_id: int,
    site_id: int,
    start_date: str,
    motif: str,
) -> None:
    connection.execute(
        """
        INSERT INTO employee_site_assignments(employe_id, site_id, date_debut, motif)
        VALUES (?, ?, ?, ?)
        """,
        (employee_id, site_id, start_date, motif),
    )


def _change_site_assignment(
    connection: Any,
    employee_id: int,
    site_id: int,
    start_date: str,
    motif: str,
) -> None:
    previous_day = (date.fromisoformat(start_date) - timedelta(days=1)).isoformat()
    current = connection.execute(
        """
        SELECT id_assignment, date_debut
        FROM employee_site_assignments
        WHERE employe_id = ?
          AND date_fin IS NULL
        ORDER BY date_debut DESC, id_assignment DESC
        LIMIT 1
        """,
        (employee_id,),
    ).fetchone()
    if current:
        if str(current["date_debut"]) > start_date:
            connection.execute(
                "DELETE FROM employee_site_assignments WHERE id_assignment = ?",
                (current["id_assignment"],),
            )
        else:
            end_date = previous_day
            if str(current["date_debut"]) == start_date:
                end_date = start_date
            connection.execute(
                """
                UPDATE employee_site_assignments
                SET date_fin = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id_assignment = ?
                """,
                (end_date, current["id_assignment"]),
            )
    _open_site_assignment(connection, employee_id, site_id, start_date, motif)


def _clean_payload(values: dict[str, Any]) -> dict[str, Any]:
    nom = _optional_text(values.get("nom"))
    prenom = _optional_text(values.get("prenom"))
    nom_complet = _required_text(values.get("nom_complet"))
    if nom or prenom:
        nom_complet = " ".join(part for part in [nom, prenom] if part).strip()

    return {
        "matricule": _optional_text(values.get("matricule")),
        "nom": nom,
        "prenom": prenom,
        "nom_complet": nom_complet,
        "fonction_id": _optional_int(values.get("fonction_id")),
        "site_id": _optional_int(values.get("site_id")),
        "groupe_id": _optional_int(values.get("groupe_id")),
        "shift_id": _optional_int(values.get("shift_id")),
        "type_employe": _required_text(values.get("type_employe")),
        "statut_employe": _required_text(values.get("statut_employe", "actif")),
        "numero_badge": _optional_text(values.get("numero_badge")),
        "statut_badge": _required_text(values.get("statut_badge", "valide")),
        "date_remise": _optional_date(values.get("date_remise"), "Date remise badge"),
        "date_expiration_badge": _badge_expiration_from_issue_date(values.get("date_remise")),
    }


def _validate_payload(payload: dict[str, Any]) -> None:
    required_fields = {
        "nom_complet": "Nom et prenom",
        "fonction_id": "Fonction",
        "site_id": "Site",
        "shift_id": "Shift",
        "type_employe": "Type employe",
        "statut_employe": "Statut employe",
    }
    for key, label in required_fields.items():
        if payload[key] in ("", None):
            raise ValueError(f"Champ obligatoire: {label}")

    if payload["type_employe"] not in EMPLOYEE_TYPES:
        raise ValueError("Type employe invalide.")
    if payload["statut_employe"] not in EMPLOYEE_STATUSES:
        raise ValueError("Statut employe invalide.")
    if payload["statut_badge"] not in BADGE_STATUSES:
        raise ValueError("Statut badge invalide.")


def _required_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    return int(value)


def _optional_date(value: Any, label: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{label}: format date invalide. Utilise AAAA-MM-JJ.") from exc
    return text


def _with_badge_validity(row: dict[str, Any]) -> dict[str, Any]:
    if not row.get("numero_badge"):
        row["badge_validity_state"] = "missing"
        row["badge_validity_label"] = "Sans badge"
        row["badge_days_left"] = None
        return row
    if row.get("statut_badge") != "valide":
        row["badge_validity_state"] = "invalid"
        row["badge_validity_label"] = str(row.get("statut_badge") or "Non conforme")
        row["badge_days_left"] = None
        return row
    expiration = row.get("date_expiration_badge")
    if not expiration and row.get("date_remise"):
        expiration = _add_months(str(row["date_remise"]), BADGE_VALIDITY_MONTHS)
        row["date_expiration_badge"] = expiration
    if not expiration:
        row["badge_validity_state"] = "unknown"
        row["badge_validity_label"] = "Expiration non renseignee"
        row["badge_days_left"] = None
        return row
    days_left = (date.fromisoformat(str(expiration)) - date.today()).days
    row["badge_days_left"] = days_left
    if days_left < 0:
        row["badge_validity_state"] = "expired"
        row["badge_validity_label"] = f"Expire: {expiration}"
    elif days_left <= BADGE_WARNING_DAYS:
        row["badge_validity_state"] = "soon"
        row["badge_validity_label"] = f"Expire dans {days_left} j"
    else:
        row["badge_validity_state"] = "valid"
        row["badge_validity_label"] = f"Valide jusqu'au {expiration}"
    return row


def _badge_expiration_from_issue_date(issue_date: Any) -> str | None:
    issued = _optional_date(issue_date, "Date remise badge")
    if not issued:
        return None
    return _add_months(issued, BADGE_VALIDITY_MONTHS)


def _add_months(value: str, months: int) -> str:
    start = date.fromisoformat(value)
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    month_days = [
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ][month - 1]
    return date(year, month, min(start.day, month_days)).isoformat()


def _friendly_integrity_error(exc: sqlite3.IntegrityError) -> str:
    message = str(exc)
    if "employes.matricule" in message:
        return "Enregistrement impossible: ce matricule existe deja."
    if "badges.numero_badge" in message:
        return "Enregistrement impossible: ce numero de badge existe deja."
    if "badges.employe_id" in message:
        return "Enregistrement impossible: cet employe possede deja un badge."
    if "FOREIGN KEY constraint failed" in message:
        return "Enregistrement impossible: une reference selectionnee est invalide."
    if "CHECK constraint failed" in message:
        return "Enregistrement impossible: une valeur ne respecte pas la regle autorisee."
    return "Enregistrement impossible: contrainte de base de donnees non respectee."
