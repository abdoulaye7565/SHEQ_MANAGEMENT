from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.db.connection import db_session


ATTENDANCE_STATUSES = ["present", "absent"]


def today_iso() -> str:
    return date.today().isoformat()


def get_attendance_list(date_presence: str) -> list[dict[str, Any]]:
    ensure_attendance_day(date_presence)
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                e.id_employe,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                e.nom_complet,
                b.numero_badge,
                f.nom AS fonction,
                sh.code AS shift_code,
                sh.libelle AS shift,
                p.id_presence,
                p.date_presence,
                p.statut_presence,
                p.heure_entree,
                p.heure_sortie,
                p.heures_travaillees
            FROM employes e
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            JOIN presences p
                ON p.employe_id = e.id_employe
               AND p.date_presence = ?
            JOIN shifts sh ON sh.id_shift = p.shift_id
            WHERE e.statut = 'actif'
              AND NOT EXISTS (
                  SELECT 1
                  FROM employee_breaks eb
                  WHERE eb.employe_id = e.id_employe
                    AND eb.statut IN ('planifie', 'en_cours')
                    AND eb.date_debut <= ?
                    AND eb.date_fin >= ?
              )
            ORDER BY nom, prenom, e.nom_complet
            """,
            (date_presence, date_presence, date_presence),
        ).fetchall()
        return [dict(row) for row in rows]


def ensure_attendance_day(date_presence: str) -> None:
    if not date_presence:
        raise ValueError("La date de presence est obligatoire.")

    with db_session() as connection:
        default_shift = connection.execute(
            "SELECT id_shift FROM shifts ORDER BY id_shift LIMIT 1"
        ).fetchone()
        if default_shift is None:
            raise ValueError("Aucun shift n'est configure.")

        employees = connection.execute(
            """
            SELECT id_employe, shift_id
            FROM employes e
            WHERE e.statut = 'actif'
              AND NOT EXISTS (
                  SELECT 1
                  FROM employee_breaks eb
                  WHERE eb.employe_id = e.id_employe
                    AND eb.statut IN ('planifie', 'en_cours')
                    AND eb.date_debut <= ?
                    AND eb.date_fin >= ?
              )
            """,
            (date_presence, date_presence),
        ).fetchall()
        for employee in employees:
            connection.execute(
                """
                INSERT OR IGNORE INTO presences (
                    employe_id, date_presence, statut_presence, shift_id
                ) VALUES (?, ?, 'absent', ?)
                """,
                (
                    employee["id_employe"],
                    date_presence,
                    employee["shift_id"] or default_shift["id_shift"],
                ),
            )


def set_attendance_status(
    employee_id: int,
    date_presence: str,
    statut_presence: str,
) -> None:
    if statut_presence not in ATTENDANCE_STATUSES:
        raise ValueError("Statut de presence invalide.")

    ensure_attendance_day(date_presence)
    with db_session() as connection:
        if statut_presence == "present":
            _ensure_employee_not_on_break(connection, employee_id, date_presence)
        connection.execute(
            """
            UPDATE presences
            SET statut_presence = ?, updated_at = CURRENT_TIMESTAMP
            WHERE employe_id = ? AND date_presence = ?
            """,
            (statut_presence, employee_id, date_presence),
        )


def save_attendance_day(date_presence: str, attendances: dict[int, Any]) -> None:
    ensure_attendance_day(date_presence)
    if is_attendance_day_locked(date_presence):
        raise ValueError("Journee verrouillee: devalidation requise avant modification.")
    with db_session() as connection:
        for employee_id, attendance in attendances.items():
            if isinstance(attendance, dict):
                status = str(attendance.get("statut_presence") or "absent")
                heure_entree = _optional_time(attendance.get("heure_entree"))
                heure_sortie = _optional_time(attendance.get("heure_sortie"))
            else:
                status = str(attendance)
                heure_entree = None
                heure_sortie = None
            if status not in ATTENDANCE_STATUSES:
                raise ValueError("Statut de presence invalide.")
            if status == "present":
                _ensure_employee_not_on_break(connection, employee_id, date_presence)
            if status == "absent":
                heure_entree = None
                heure_sortie = None
            heures_travaillees = _calculate_hours(heure_entree, heure_sortie)
            previous = connection.execute(
                """
                SELECT id_presence, statut_presence, heure_entree, heure_sortie, heures_travaillees
                FROM presences
                WHERE employe_id = ? AND date_presence = ?
                """,
                (employee_id, date_presence),
            ).fetchone()
            connection.execute(
                """
                UPDATE presences
                SET statut_presence = ?,
                    heure_entree = ?,
                    heure_sortie = ?,
                    heures_travaillees = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE employe_id = ? AND date_presence = ?
                """,
                (
                    status,
                    heure_entree,
                    heure_sortie,
                    heures_travaillees,
                    employee_id,
                    date_presence,
                ),
            )
            if previous:
                _audit_presence_changes(
                    connection,
                    previous,
                    employee_id,
                    date_presence,
                    {
                        "statut_presence": status,
                        "heure_entree": heure_entree,
                        "heure_sortie": heure_sortie,
                        "heures_travaillees": heures_travaillees,
                    },
                )


def get_attendance_summary(date_presence: str) -> dict[str, int]:
    ensure_attendance_day(date_presence)
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT statut_presence, COUNT(*) AS total
            FROM presences p
            JOIN employes e ON e.id_employe = p.employe_id
            WHERE p.date_presence = ?
              AND e.statut = 'actif'
              AND NOT EXISTS (
                  SELECT 1
                  FROM employee_breaks eb
                  WHERE eb.employe_id = p.employe_id
                    AND eb.statut IN ('planifie', 'en_cours')
                    AND eb.date_debut <= ?
                    AND eb.date_fin >= ?
              )
            GROUP BY statut_presence
            """,
            (date_presence, date_presence, date_presence),
        ).fetchall()
        summary = {"present": 0, "absent": 0}
        for row in rows:
            summary[row["statut_presence"]] = int(row["total"])
        summary["total"] = summary["present"] + summary["absent"]
        return summary


def list_shift_templates() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT shift_code, libelle, heure_entree, heure_sortie
            FROM shift_templates
            WHERE actif = 1
            ORDER BY id_template
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_attendance_day_lock(date_presence: str) -> dict[str, Any] | None:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT date_presence, locked_by, locked_at, commentaire
            FROM attendance_day_locks
            WHERE date_presence = ?
            """,
            (date_presence,),
        ).fetchone()
        return dict(row) if row else None


def is_attendance_day_locked(date_presence: str) -> bool:
    return get_attendance_day_lock(date_presence) is not None


def lock_attendance_day(
    date_presence: str,
    locked_by: str = "superviseur",
    commentaire: str | None = None,
) -> None:
    validation = validate_attendance_day(date_presence)
    if validation["blocking"]:
        raise ValueError("Validation impossible: corrige d'abord les lignes a completer.")
    with db_session() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO attendance_day_locks (
                date_presence, locked_by, locked_at, commentaire
            ) VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (date_presence, locked_by, commentaire),
        )


def unlock_attendance_day(date_presence: str) -> None:
    with db_session() as connection:
        connection.execute(
            "DELETE FROM attendance_day_locks WHERE date_presence = ?",
            (date_presence,),
        )


def validate_attendance_day(date_presence: str) -> dict[str, Any]:
    rows = get_attendance_list(date_presence)
    issues: list[dict[str, Any]] = []
    for row in rows:
        status = row["statut_presence"]
        entry = row.get("heure_entree")
        exit_ = row.get("heure_sortie")
        hours = float(row.get("heures_travaillees") or 0)
        if status == "present" and (not entry or not exit_):
            issues.append({**row, "niveau": "bloquant", "message": "Heures entree/sortie incompletes."})
        elif status == "present" and hours > 12:
            issues.append({**row, "niveau": "alerte", "message": "Plus de 12 heures travaillees."})
        elif status == "present" and hours == 0:
            issues.append({**row, "niveau": "alerte", "message": "Aucune heure calculee."})
        elif not row.get("numero_badge"):
            issues.append({**row, "niveau": "alerte", "message": "Badge manquant."})
    return {
        "total": len(rows),
        "issues": issues,
        "blocking": [issue for issue in issues if issue["niveau"] == "bloquant"],
        "warnings": [issue for issue in issues if issue["niveau"] == "alerte"],
    }


def get_monthly_attendance_summary(month: str) -> dict[str, Any]:
    if len(month) != 7:
        raise ValueError("Format mois invalide. Utilise AAAA-MM.")
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                e.id_employe,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                b.numero_badge,
                f.nom AS fonction,
                COUNT(p.id_presence) AS jours_suivis,
                SUM(CASE WHEN p.statut_presence = 'present' THEN 1 ELSE 0 END) AS jours_presents,
                SUM(CASE WHEN p.statut_presence = 'absent' THEN 1 ELSE 0 END) AS jours_absents,
                SUM(p.heures_travaillees) AS heures
            FROM employes e
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            LEFT JOIN presences p
              ON p.employe_id = e.id_employe
             AND substr(p.date_presence, 1, 7) = ?
            WHERE e.statut = 'actif'
            GROUP BY e.id_employe, e.nom, e.prenom, e.nom_complet, b.numero_badge, f.nom
            ORDER BY nom, prenom
            """,
            (month,),
        ).fetchall()
        data = [dict(row) for row in rows]
        return {
            "month": month,
            "total_employes": len(data),
            "jours_presents": sum(int(row["jours_presents"] or 0) for row in data),
            "jours_absents": sum(int(row["jours_absents"] or 0) for row in data),
            "heures": round(sum(float(row["heures"] or 0) for row in data), 2),
            "rows": data,
        }


def list_attendance_audit(date_presence: str, limit: int = 20) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                aa.changed_at,
                aa.champ,
                aa.ancienne_valeur,
                aa.nouvelle_valeur,
                aa.changed_by,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom
            FROM attendance_audit aa
            JOIN employes e ON e.id_employe = aa.employe_id
            WHERE aa.date_presence = ?
            ORDER BY aa.changed_at DESC, aa.id_audit DESC
            LIMIT ?
            """,
            (date_presence, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def _optional_time(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError as exc:
        raise ValueError("Format heure invalide. Utilise HH:MM.") from exc
    return text


def _ensure_employee_not_on_break(connection: Any, employee_id: int, date_presence: str) -> None:
    row = connection.execute(
        """
        SELECT type_break, date_debut, date_fin
        FROM employee_breaks
        WHERE employe_id = ?
          AND statut IN ('planifie', 'en_cours')
          AND date_debut <= ?
          AND date_fin >= ?
        ORDER BY date_debut DESC, id_break DESC
        LIMIT 1
        """,
        (employee_id, date_presence, date_presence),
    ).fetchone()
    if row:
        raise ValueError(
            "Presence impossible: cet employe est en break "
            f"du {row['date_debut']} au {row['date_fin']}."
        )


def _audit_presence_changes(
    connection: Any,
    previous: Any,
    employee_id: int,
    date_presence: str,
    new_values: dict[str, Any],
) -> None:
    for field, new_value in new_values.items():
        old_value = previous[field]
        old_text = "" if old_value is None else str(old_value)
        new_text = "" if new_value is None else str(new_value)
        if old_text == new_text:
            continue
        connection.execute(
            """
            INSERT INTO attendance_audit (
                presence_id, employe_id, date_presence, champ,
                ancienne_valeur, nouvelle_valeur, changed_by
            ) VALUES (?, ?, ?, ?, ?, ?, 'system')
            """,
            (
                previous["id_presence"],
                employee_id,
                date_presence,
                field,
                old_text,
                new_text,
            ),
        )


def _calculate_hours(heure_entree: str | None, heure_sortie: str | None) -> float:
    if not heure_entree or not heure_sortie:
        return 0
    start = datetime.strptime(heure_entree, "%H:%M")
    end = datetime.strptime(heure_sortie, "%H:%M")
    if end < start:
        end = end + timedelta(days=1)
    return round((end - start).seconds / 3600, 2)
