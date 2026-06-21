from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Any

from app.db.connection import db_session
from app.services.timesheet_period_service import (
    TIMESHEET_21_20,
    get_active_timesheet_period,
    get_timesheet_period_for_month,
    get_timesheet_sync_status,
)


DRILLING_HOURS = 12
STANDARD_HOURS = 8
BREAK_HOURS = 8
PERMISSION_DAYS = 3
DAY_STATUSES = {"present", "rest", "absent", "break", "annual", "permission", "sick"}
DAY_TYPES = {"work", "holiday"}


def current_timesheet_month() -> str:
    return get_active_timesheet_period(TIMESHEET_21_20)["month"]


def get_timesheet_period(month: str) -> dict[str, str]:
    return get_timesheet_period_for_month(TIMESHEET_21_20, month)


def list_timesheet_days(month: str) -> list[str]:
    period = get_timesheet_period(month)
    current = _parse_date(period["start"])
    end = _parse_date(period["end"])
    days: list[str] = []
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def get_day_activity(date_presence: str) -> dict[str, Any]:
    target_date = _parse_date(date_presence).isoformat()
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT date_presence, has_drilling, day_type, updated_at, commentaire
            FROM timesheet_day_settings
            WHERE date_presence = ?
            """,
            (target_date,),
        ).fetchone()
        if row:
            return dict(row)
    return {
        "date_presence": target_date,
        "has_drilling": 0,
        "day_type": "holiday" if _is_sunday(target_date) else "work",
        "updated_at": None,
        "commentaire": None,
    }


def set_day_activity(
    date_presence: str,
    has_drilling: bool,
    commentaire: str | None = None,
    day_type: str = "work",
) -> None:
    target_date = _parse_date(date_presence).isoformat()
    day_type = _normalize_day_type(day_type)
    _ensure_not_future(target_date)
    month = _timesheet_month_for_date(target_date)
    with db_session() as connection:
        _ensure_month_unlocked(connection, month)
        _ensure_attendance_day_unlocked(connection, target_date)
        previous = get_day_activity(target_date)
        connection.execute(
            """
            INSERT INTO timesheet_day_settings (
                date_presence, has_drilling, day_type, updated_at, commentaire
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(date_presence) DO UPDATE SET
                has_drilling = excluded.has_drilling,
                day_type = excluded.day_type,
                updated_at = CURRENT_TIMESTAMP,
                commentaire = excluded.commentaire
            """,
            (target_date, 1 if has_drilling else 0, day_type, str(commentaire or "").strip() or None),
        )
        _insert_audit(
            connection,
            month,
            target_date,
            None,
            "activity",
            _activity_audit_value(previous),
            _activity_audit_value({"has_drilling": has_drilling, "day_type": day_type}),
            commentaire,
        )


def set_day_activity_range(
    start_date: str,
    end_date: str,
    has_drilling: bool,
    commentaire: str | None = None,
    day_type: str = "work",
) -> int:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if end < start:
        raise ValueError("La date de fin doit etre apres la date de debut.")
    if end > date.today():
        raise ValueError("Modification impossible: ce jour n'est pas encore arrive.")
    updated = 0
    current = start
    while current <= end:
        set_day_activity(current.isoformat(), has_drilling, commentaire, day_type=day_type)
        updated += 1
        current += timedelta(days=1)
    return updated


def update_timesheet_day_status(
    employee_id: int,
    date_presence: str,
    status: str,
) -> None:
    target_date = _parse_date(date_presence).isoformat()
    _ensure_not_future(target_date)
    month = _timesheet_month_for_date(target_date)
    employee_id = int(employee_id or 0)
    status = str(status or "").strip()
    if not employee_id:
        raise ValueError("Employe obligatoire.")
    if status not in DAY_STATUSES:
        raise ValueError("Statut TimeSheet invalide.")

    with db_session() as connection:
        _ensure_month_unlocked(connection, month)
        _ensure_attendance_day_unlocked(connection, target_date)
        employee = connection.execute(
            """
            SELECT id_employe, shift_id, type_employe
            FROM employes
            WHERE id_employe = ?
            """,
            (employee_id,),
        ).fetchone()
        if employee is None:
            raise ValueError("Employe introuvable.")
        if str(employee["type_employe"] or "") == "expatriate":
            raise ValueError("Les employes expatries ne sont pas inclus dans le TimeSheet.")
        old_status = _current_employee_day_status(connection, employee_id, target_date)

        if status in {"present", "rest", "absent"}:
            _ensure_no_blocking_break(connection, employee_id, target_date)
            connection.execute(
                """
                UPDATE employee_breaks
                SET statut = 'annule', updated_at = CURRENT_TIMESTAMP
                WHERE employe_id = ?
                  AND date_debut = ?
                  AND date_fin = ?
                  AND statut IN ('planifie', 'en_cours')
                """,
                (employee_id, target_date, target_date),
            )
            if status == "present":
                connection.execute(
                    """
                    DELETE FROM timesheet_day_overrides
                    WHERE employe_id = ? AND date_presence = ?
                    """,
                    (employee_id, target_date),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO timesheet_day_overrides (
                        employe_id, date_presence, status, updated_at
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(employe_id, date_presence) DO UPDATE SET
                        status = excluded.status,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (employee_id, target_date, status),
                )
            has_drilling = _setting_has_drilling(
                _settings_by_day(connection, target_date, target_date),
                target_date,
            )
            entry_time, exit_time = _default_times_for_activity(has_drilling)
            hours = DRILLING_HOURS if has_drilling else STANDARD_HOURS
            connection.execute(
                """
                INSERT INTO presences (
                    employe_id, date_presence, statut_presence, shift_id,
                    heure_entree, heure_sortie, heures_travaillees
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(employe_id, date_presence) DO UPDATE SET
                    statut_presence = excluded.statut_presence,
                    heure_entree = excluded.heure_entree,
                    heure_sortie = excluded.heure_sortie,
                    heures_travaillees = excluded.heures_travaillees,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    employee_id,
                    target_date,
                    "present" if status == "present" else "absent",
                    employee["shift_id"],
                    entry_time if status == "present" else None,
                    exit_time if status == "present" else None,
                    hours if status == "present" else 0,
                ),
            )
            _insert_audit(connection, month, target_date, employee_id, "status", old_status, status)
            return

        existing = connection.execute(
            """
            SELECT id_break, date_debut, date_fin
            FROM employee_breaks
            WHERE employe_id = ?
              AND statut IN ('planifie', 'en_cours')
              AND date_debut <= ?
              AND date_fin >= ?
            ORDER BY date_debut DESC, id_break DESC
            LIMIT 1
            """,
            (employee_id, target_date, target_date),
        ).fetchone()
        if existing and (
            str(existing["date_debut"]) != target_date
            or str(existing["date_fin"]) != target_date
        ):
            raise ValueError("Ce jour appartient a un break multi-jours. Modifie-le dans le module Breaks.")
        if existing:
            connection.execute(
                """
                UPDATE employee_breaks
                SET type_break = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id_break = ?
                """,
                (status, existing["id_break"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO employee_breaks (
                    employe_id, type_break, date_debut, date_fin, statut
                ) VALUES (?, ?, ?, ?, 'planifie')
                """,
                (employee_id, status, target_date, target_date),
            )
        connection.execute(
            """
            DELETE FROM timesheet_day_overrides
            WHERE employe_id = ? AND date_presence = ?
            """,
            (employee_id, target_date),
        )
        connection.execute(
            """
            UPDATE presences
            SET statut_presence = 'absent',
                heure_entree = NULL,
                heure_sortie = NULL,
                heures_travaillees = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE employe_id = ? AND date_presence = ?
            """,
            (employee_id, target_date),
        )
        _insert_audit(connection, month, target_date, employee_id, "status", old_status, status)


def get_timesheet_lock(month: str) -> dict[str, Any] | None:
    selected_month = get_timesheet_period(month)["month"]
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT month, locked_by, locked_at, commentaire
            FROM timesheet_month_locks
            WHERE month = ?
            """,
            (selected_month,),
        ).fetchone()
        return dict(row) if row else None


def is_timesheet_locked(month: str) -> bool:
    return get_timesheet_lock(month) is not None


def lock_timesheet_month(
    month: str,
    locked_by: str = "superviseur",
    commentaire: str | None = None,
) -> None:
    selected_month = get_timesheet_period(month)["month"]
    validation = validate_timesheet_month(selected_month)
    if validation["blocking"]:
        raise ValueError("Verrouillage impossible: corrige d'abord les points bloquants.")
    with db_session() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO timesheet_month_locks (
                month, locked_by, locked_at, commentaire
            ) VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (selected_month, locked_by, str(commentaire or "").strip() or None),
        )
        _insert_audit(connection, selected_month, None, None, "lock", "", "locked", commentaire)


def unlock_timesheet_month(month: str, commentaire: str | None = None) -> None:
    selected_month = get_timesheet_period(month)["month"]
    with db_session() as connection:
        connection.execute("DELETE FROM timesheet_month_locks WHERE month = ?", (selected_month,))
        _insert_audit(connection, selected_month, None, None, "unlock", "locked", "unlocked", commentaire)


def get_timesheet(month: str | None = None, site_id: int | None = None) -> dict[str, Any]:
    selected_month = month or current_timesheet_month()
    period = get_timesheet_period(selected_month)
    days = list_timesheet_days(selected_month)
    selected_site_id = int(site_id or 0) or None

    with db_session() as connection:
        settings = _settings_by_day(connection, period["start"], period["end"])
        site_filter = ""
        site_params: tuple[Any, ...] = ()
        if selected_site_id is not None:
            site_filter = """
              AND EXISTS (
                    SELECT 1
                    FROM employee_site_assignments esa_site
                    WHERE esa_site.employe_id = e.id_employe
                      AND esa_site.site_id = ?
                      AND esa_site.date_debut <= ?
                      AND COALESCE(esa_site.date_fin, '9999-12-31') >= ?
              )
            """
            site_params = (selected_site_id, period["end"], period["start"])
        employees = connection.execute(
            f"""
            SELECT DISTINCT
                e.id_employe,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                e.nom_complet,
                e.matricule,
                b.numero_badge,
                f.nom AS fonction,
                s.nom AS site,
                s.id_site AS site_id,
                d.nom AS departement_site,
                COALESCE(g.nom, '-') AS groupe,
                sh.code AS shift_code,
                sh.libelle AS shift
            FROM employes e
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            JOIN sites s ON s.id_site = e.site_id
            LEFT JOIN departments d ON d.id_department = s.department_id
            LEFT JOIN groupes g ON g.id_groupe = e.groupe_id
            JOIN shifts sh ON sh.id_shift = e.shift_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.type_employe <> 'expatriate'
              AND (
                e.statut = 'actif'
                OR EXISTS (
                    SELECT 1
                    FROM presences p
                    WHERE p.employe_id = e.id_employe
                      AND p.date_presence BETWEEN ? AND ?
                )
                OR EXISTS (
                    SELECT 1
                    FROM employee_breaks eb
                    WHERE eb.employe_id = e.id_employe
                      AND eb.date_debut <= ?
                      AND eb.date_fin >= ?
                )
              )
              {site_filter}
            ORDER BY nom, prenom, e.nom_complet
            """,
            (period["start"], period["end"], period["end"], period["start"], *site_params),
        ).fetchall()
        attendance = _attendance_by_employee_day(connection, period["start"], period["end"])
        breaks = _breaks_by_employee(connection, period["start"], period["end"])
        overrides = _overrides_by_employee_day(connection, period["start"], period["end"])
        site_assignments = _site_assignments_by_employee(
            connection,
            period["start"],
            period["end"],
            selected_site_id,
        )

    rows: list[dict[str, Any]] = []
    summary = {
        "employees": 0,
        "worked_days": 0,
        "rest_days": 0,
        "break_days": 0,
        "permission_days": 0,
        "sick_days": 0,
        "absent_days": 0,
        "unfilled_days": 0,
        "drilling_hours": 0,
        "standard_hours": 0,
        "hours": 0,
        "actual_hours": 0,
        "drilling_days": sum(1 for item in days if _setting_has_drilling(settings, item)),
        "standard_days": sum(
            1
            for item in days
            if not _setting_has_drilling(settings, item)
            and _setting_day_type(settings, item) == "work"
            and not _is_sunday(item)
        ),
        "holiday_days": sum(1 for item in days if _setting_day_type(settings, item) == "holiday"),
    }

    for employee in employees:
        employee_id = int(employee["id_employe"])
        cells = []
        total_hours = 0
        worked_days = 0
        rest_days = 0
        break_days = 0
        permission_days = 0
        sick_days = 0
        absent_days = 0
        unfilled_days = 0
        drilling_hours = 0
        standard_hours = 0
        actual_hours = 0.0
        weekly_hours: dict[str, int] = {}
        for day_index, day in enumerate(days):
            has_drilling = _setting_has_drilling(settings, day)
            day_type = _setting_day_type(settings, day)
            week_key = f"S{_period_week_index(day_index)}"
            weekly_hours.setdefault(week_key, 0)
            if selected_site_id is not None and not _assigned_to_site_on_day(
                site_assignments.get(employee_id, []),
                selected_site_id,
                day,
            ):
                cells.append(
                    {
                        "date": day,
                        "day": int(day[-2:]),
                        "status": "not_assigned",
                        "label": "N/A",
                        "hours": 0,
                        "actual_hours": 0,
                        "has_drilling": has_drilling,
                        "day_type": day_type,
                        "week_index": _period_week_index(day_index),
                        "week_start": day_index % 7 == 0,
                    }
                )
                continue
            break_record = _break_for_day(breaks.get(employee_id, []), day)
            presence = attendance.get((employee_id, day))
            override = overrides.get((employee_id, day))
            if break_record:
                label = _break_label(str(break_record.get("type_break") or "break"))
                if _permission_exceeds_allowed_days(break_record, day):
                    status = "absent"
                    label = "A"
                    hours = 0
                    absent_days += 1
                else:
                    status = "break"
                    hours = BREAK_HOURS
                    total_hours += hours
                    weekly_hours[week_key] += hours
                    standard_hours += hours
                    if label == "P":
                        permission_days += 1
                    elif label == "S":
                        sick_days += 1
                    else:
                        break_days += 1
            elif override:
                status = str(override.get("status") or "rest")
                label = "R" if status == "rest" else "A"
                hours = 0
                if status == "rest":
                    rest_days += 1
                else:
                    absent_days += 1
            elif presence and presence.get("statut_presence") == "present":
                status = "worked_drilling" if has_drilling else "worked_standard"
                hours = DRILLING_HOURS if has_drilling else STANDARD_HOURS
                label = f"{hours}h"
                worked_days += 1
                total_hours += hours
                weekly_hours[week_key] += hours
                if has_drilling:
                    drilling_hours += hours
                else:
                    standard_hours += hours
                actual_hours += float(presence.get("heures_travaillees") or 0)
            elif presence and presence.get("statut_presence") == "absent":
                status = "absent"
                label = "A"
                hours = 0
                absent_days += 1
            elif day_type == "holiday":
                status = "holiday"
                label = "8"
                hours = STANDARD_HOURS
                worked_days += 1
                total_hours += hours
                weekly_hours[week_key] += hours
                standard_hours += hours
            elif _is_sunday(day):
                status = "rest"
                label = "R"
                hours = 0
                rest_days += 1
            else:
                status = "unfilled"
                label = "NR"
                hours = 0
                unfilled_days += 1
            cells.append(
                {
                    "date": day,
                    "day": int(day[-2:]),
                    "status": status,
                    "label": label,
                    "hours": hours,
                    "actual_hours": float(presence.get("heures_travaillees") or 0) if presence else 0,
                    "has_drilling": has_drilling,
                    "day_type": day_type,
                    "week_index": _period_week_index(day_index),
                    "week_start": day_index % 7 == 0,
                }
            )

        rows.append(
            {
                "employee": dict(employee),
                "cells": cells,
                "worked_days": worked_days,
                "rest_days": rest_days,
                "break_days": break_days,
                "permission_days": permission_days,
                "sick_days": sick_days,
                "absent_days": absent_days,
                "unfilled_days": unfilled_days,
                "drilling_hours": drilling_hours,
                "standard_hours": standard_hours,
                "weekly_hours": weekly_hours,
                "hours": total_hours,
                "actual_hours": round(actual_hours, 2),
            }
        )
        summary["employees"] += 1
        summary["worked_days"] += worked_days
        summary["rest_days"] += rest_days
        summary["break_days"] += break_days
        summary["permission_days"] += permission_days
        summary["sick_days"] += sick_days
        summary["absent_days"] += absent_days
        summary["unfilled_days"] += unfilled_days
        summary["drilling_hours"] += drilling_hours
        summary["standard_hours"] += standard_hours
        summary["hours"] += total_hours
        summary["actual_hours"] = round(float(summary["actual_hours"]) + actual_hours, 2)

    return {
        "period": period,
        "synchronization": get_timesheet_sync_status(TIMESHEET_21_20, selected_month, selected_site_id),
        "site_id": selected_site_id,
        "site": _site_context(selected_site_id),
        "lock": get_timesheet_lock(selected_month),
        "validation": validate_timesheet_month(selected_month, site_id=selected_site_id),
        "week_labels": [f"S{index}" for index in range(1, _period_week_index(len(days) - 1) + 1)],
        "days": [
            {
                "date": day,
                "day": int(day[-2:]),
                "weekday": _weekday_label(day),
                "has_drilling": _setting_has_drilling(settings, day),
                "day_type": _setting_day_type(settings, day),
                "planned_hours": 0
                if _is_sunday(day)
                else (DRILLING_HOURS if _setting_has_drilling(settings, day) else STANDARD_HOURS),
                "week_index": _period_week_index(index),
                "week_start": index % 7 == 0,
            }
            for index, day in enumerate(days)
        ],
        "rows": rows,
        "summary": summary,
    }


def list_timesheet_history(limit: int = 12) -> list[dict[str, Any]]:
    month_limit = max(1, int(limit or 12))
    with db_session() as connection:
        rows = connection.execute(
            """
            WITH dates AS (
                SELECT date_presence AS source_date FROM presences
                UNION
                SELECT date_debut AS source_date FROM employee_breaks
                UNION
                SELECT date_presence AS source_date FROM timesheet_day_settings
                UNION
                SELECT date_presence AS source_date FROM timesheet_day_overrides
            )
            SELECT DISTINCT
                CASE
                    WHEN CAST(strftime('%d', source_date) AS INTEGER) >= 21
                    THEN strftime('%Y-%m', source_date)
                    ELSE strftime('%Y-%m', date(source_date, 'start of month', '-1 day'))
                END AS month
            FROM dates
            WHERE source_date IS NOT NULL
            ORDER BY month DESC
            LIMIT ?
            """,
            (month_limit,),
        ).fetchall()
    months = [str(row["month"]) for row in rows if row["month"]]
    if not months:
        months = [current_timesheet_month()]
    return [get_timesheet_period(month) for month in months[:month_limit]]


def list_timesheet_site_options() -> list[dict[str, Any]]:
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


def list_timesheet_audit(month: str, limit: int = 50) -> list[dict[str, Any]]:
    selected_month = get_timesheet_period(month)["month"]
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                ta.changed_at,
                ta.date_presence,
                ta.action,
                ta.ancienne_valeur,
                ta.nouvelle_valeur,
                ta.changed_by,
                ta.commentaire,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom
            FROM timesheet_audit ta
            LEFT JOIN employes e ON e.id_employe = ta.employe_id
            WHERE ta.month = ?
            ORDER BY ta.changed_at DESC, ta.id_audit DESC
            LIMIT ?
            """,
            (selected_month, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def validate_timesheet_month(month: str, site_id: int | None = None) -> dict[str, Any]:
    period = get_timesheet_period(month)
    days = list_timesheet_days(month)
    today = date.today()
    issues: list[dict[str, Any]] = []
    selected_site_id = int(site_id or 0) or None
    with db_session() as connection:
        settings = _settings_by_day(connection, period["start"], period["end"])
        for day in days:
            parsed = _parse_date(day)
            if parsed > today or (_is_sunday(day) and day not in settings):
                continue
            if day not in settings:
                issues.append(
                    {
                        "date": day,
                        "niveau": "bloquant",
                        "message": "Activite drilling/non-drilling non configuree.",
                    }
                )
        attendance = _attendance_by_employee_day(connection, period["start"], period["end"])
        breaks = _breaks_by_employee(connection, period["start"], period["end"])
        overrides = _overrides_by_employee_day(connection, period["start"], period["end"])
        site_filter = ""
        site_params: tuple[Any, ...] = ()
        if selected_site_id is not None:
            site_filter = """
              AND EXISTS (
                    SELECT 1
                    FROM employee_site_assignments esa_site
                    WHERE esa_site.employe_id = e.id_employe
                      AND esa_site.site_id = ?
                      AND esa_site.date_debut <= ?
                      AND COALESCE(esa_site.date_fin, '9999-12-31') >= ?
              )
            """
            site_params = (selected_site_id, period["end"], period["start"])
        site_assignments = _site_assignments_by_employee(
            connection,
            period["start"],
            period["end"],
            selected_site_id,
        )
        employees = connection.execute(
            f"""
            SELECT e.id_employe, COALESCE(e.nom, e.nom_complet) AS nom, COALESCE(e.prenom, '') AS prenom
            FROM employes e
            WHERE e.type_employe <> 'expatriate'
              AND (
                e.statut = 'actif'
                OR EXISTS (
                    SELECT 1 FROM presences p
                    WHERE p.employe_id = e.id_employe
                      AND p.date_presence BETWEEN ? AND ?
                )
                OR EXISTS (
                    SELECT 1 FROM employee_breaks eb
                    WHERE eb.employe_id = e.id_employe
                      AND eb.date_debut <= ?
                      AND eb.date_fin >= ?
                )
              )
              {site_filter}
            """,
            (period["start"], period["end"], period["end"], period["start"], *site_params),
        ).fetchall()
        for employee in employees:
            employee_id = int(employee["id_employe"])
            name = f"{employee['nom']} {employee['prenom']}".strip()
            employee_breaks = breaks.get(employee_id, [])
            for day in days:
                parsed = _parse_date(day)
                if _setting_day_type(settings, day) == "holiday":
                    continue
                if parsed > today or (_is_sunday(day) and day not in settings):
                    continue
                if selected_site_id is not None and not _assigned_to_site_on_day(
                    site_assignments.get(employee_id, []),
                    selected_site_id,
                    day,
                ):
                    continue
                presence = attendance.get((employee_id, day))
                break_record = _break_for_day(employee_breaks, day)
                override = overrides.get((employee_id, day))
                if break_record and presence and presence.get("statut_presence") == "present":
                    issues.append(
                        {
                            "date": day,
                            "niveau": "bloquant",
                            "message": f"Conflit presence/break: {name} le {day}.",
                        }
                    )
                if presence and presence.get("statut_presence") == "present":
                    if not presence.get("heure_entree") or not presence.get("heure_sortie"):
                        issues.append(
                            {
                                "date": day,
                                "niveau": "bloquant",
                                "message": f"Heures entree/sortie incompletes: {name} le {day}.",
                            }
                        )
                elif not break_record and not override and not presence:
                    issues.append(
                        {
                            "date": day,
                            "niveau": "bloquant",
                            "message": f"Statut non renseigne: {name} le {day}.",
                        }
                    )
        employees_without_badge = connection.execute(
            f"""
            SELECT e.id_employe, COALESCE(e.nom, e.nom_complet) AS nom, COALESCE(e.prenom, '') AS prenom
            FROM employes e
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
              AND e.type_employe <> 'expatriate'
              AND b.id_badge IS NULL
              {site_filter}
            """,
            site_params,
        ).fetchall()
        for employee in employees_without_badge:
            issues.append(
                {
                    "date": None,
                    "niveau": "alerte",
                    "message": f"Badge manquant: {employee['nom']} {employee['prenom']}".strip(),
                }
            )
    return {
        "issues": issues,
        "blocking": [issue for issue in issues if issue["niveau"] == "bloquant"],
        "warnings": [issue for issue in issues if issue["niveau"] == "alerte"],
    }


def _site_context(site_id: int | None) -> dict[str, Any] | None:
    if site_id is None:
        return None
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT s.id_site, s.nom, s.localisation, d.nom AS departement
            FROM sites s
            LEFT JOIN departments d ON d.id_department = s.department_id
            WHERE s.id_site = ?
            """,
            (site_id,),
        ).fetchone()
        return dict(row) if row else None


def _settings_by_day(connection: Any, start: str, end: str) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT date_presence, has_drilling, day_type
        FROM timesheet_day_settings
        WHERE date_presence BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchall()
    return {
        str(row["date_presence"]): {
            "has_drilling": bool(row["has_drilling"]),
            "day_type": str(row["day_type"] or "work"),
        }
        for row in rows
    }


def _setting_has_drilling(settings: dict[str, dict[str, Any]], day: str) -> bool:
    return bool(settings.get(day, {}).get("has_drilling", False))


def _setting_day_type(settings: dict[str, dict[str, Any]], day: str) -> str:
    value = str(settings.get(day, {}).get("day_type") or "work")
    return value if value in DAY_TYPES else "work"


def _normalize_day_type(day_type: str) -> str:
    normalized = str(day_type or "work").strip().lower()
    if normalized not in DAY_TYPES:
        raise ValueError("Type de jour invalide. Choisis travail ou jour chome.")
    return normalized


def _activity_audit_value(activity: dict[str, Any]) -> str:
    if str(activity.get("day_type") or "work") == "holiday":
        return "holiday"
    return "drilling" if activity.get("has_drilling") else "standard"


def _ensure_month_unlocked(connection: Any, month: str) -> None:
    row = connection.execute(
        "SELECT month FROM timesheet_month_locks WHERE month = ?",
        (month,),
    ).fetchone()
    if row:
        raise ValueError("TimeSheet verrouille: deverrouille le mois avant modification.")


def _ensure_attendance_day_unlocked(connection: Any, target_date: str) -> None:
    row = connection.execute(
        "SELECT date_presence FROM attendance_day_locks WHERE date_presence = ?",
        (target_date,),
    ).fetchone()
    if row:
        raise ValueError(
            f"Presence verrouillee: deverrouille la journee {target_date} avant modification TimeSheet."
        )


def _insert_audit(
    connection: Any,
    month: str,
    date_presence: str | None,
    employee_id: int | None,
    action: str,
    old_value: Any,
    new_value: Any,
    commentaire: str | None = None,
) -> None:
    if str(old_value or "") == str(new_value or "") and action not in {"lock", "unlock"}:
        return
    connection.execute(
        """
        INSERT INTO timesheet_audit (
            month, date_presence, employe_id, action,
            ancienne_valeur, nouvelle_valeur, commentaire
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            month,
            date_presence,
            employee_id,
            action,
            "" if old_value is None else str(old_value),
            "" if new_value is None else str(new_value),
            str(commentaire or "").strip() or None,
        ),
    )


def _current_employee_day_status(connection: Any, employee_id: int, target_date: str) -> str:
    break_row = connection.execute(
        """
        SELECT type_break
        FROM employee_breaks
        WHERE employe_id = ?
          AND statut IN ('planifie', 'en_cours')
          AND date_debut <= ?
          AND date_fin >= ?
        ORDER BY date_debut DESC, id_break DESC
        LIMIT 1
        """,
        (employee_id, target_date, target_date),
    ).fetchone()
    if break_row:
        return str(break_row["type_break"])
    override = connection.execute(
        """
        SELECT status
        FROM timesheet_day_overrides
        WHERE employe_id = ? AND date_presence = ?
        """,
        (employee_id, target_date),
    ).fetchone()
    if override:
        return str(override["status"])
    presence = connection.execute(
        """
        SELECT statut_presence
        FROM presences
        WHERE employe_id = ? AND date_presence = ?
        """,
        (employee_id, target_date),
    ).fetchone()
    if presence and presence["statut_presence"] == "present":
        return "present"
    if presence and presence["statut_presence"] == "absent":
        return "absent"
    return "unfilled"


def _attendance_by_employee_day(connection: Any, start: str, end: str) -> dict[tuple[int, str], dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT employe_id, date_presence, statut_presence, heure_entree, heure_sortie, heures_travaillees
        FROM presences
        WHERE date_presence BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchall()
    return {
        (int(row["employe_id"]), str(row["date_presence"])): dict(row)
        for row in rows
    }


def _overrides_by_employee_day(connection: Any, start: str, end: str) -> dict[tuple[int, str], dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT employe_id, date_presence, status
        FROM timesheet_day_overrides
        WHERE date_presence BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchall()
    return {
        (int(row["employe_id"]), str(row["date_presence"])): dict(row)
        for row in rows
    }


def _site_assignments_by_employee(
    connection: Any,
    start: str,
    end: str,
    site_id: int | None,
) -> dict[int, list[dict[str, Any]]]:
    if site_id is None:
        return {}
    rows = connection.execute(
        """
        SELECT employe_id, site_id, date_debut, date_fin
        FROM employee_site_assignments
        WHERE site_id = ?
          AND date_debut <= ?
          AND COALESCE(date_fin, '9999-12-31') >= ?
        ORDER BY date_debut
        """,
        (site_id, end, start),
    ).fetchall()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["employe_id"]), []).append(dict(row))
    return grouped


def _assigned_to_site_on_day(records: list[dict[str, Any]], site_id: int, day: str) -> bool:
    return any(
        int(record.get("site_id") or 0) == site_id
        and str(record.get("date_debut") or "") <= day
        and str(record.get("date_fin") or "9999-12-31") >= day
        for record in records
    )


def _breaks_by_employee(connection: Any, start: str, end: str) -> dict[int, list[dict[str, Any]]]:
    rows = connection.execute(
        """
        SELECT employe_id, type_break, date_debut, date_fin, statut
        FROM employee_breaks
        WHERE statut IN ('planifie', 'en_cours', 'termine')
          AND date_debut <= ?
          AND date_fin >= ?
        ORDER BY date_debut
        """,
        (end, start),
    ).fetchall()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["employe_id"]), []).append(dict(row))
    return grouped


def _break_for_day(records: list[dict[str, Any]], day: str) -> dict[str, Any] | None:
    for record in records:
        if str(record["date_debut"]) <= day <= str(record["date_fin"]):
            return record
    return None


def _permission_exceeds_allowed_days(record: dict[str, Any], day: str) -> bool:
    if str(record.get("type_break") or "") != "permission":
        return False
    start = _parse_date(str(record.get("date_debut") or ""))
    current = _parse_date(day)
    return (current - start).days >= PERMISSION_DAYS


def _ensure_no_blocking_break(connection: Any, employee_id: int, target_date: str) -> None:
    row = connection.execute(
        """
        SELECT id_break, date_debut, date_fin, statut
        FROM employee_breaks
        WHERE employe_id = ?
          AND statut IN ('planifie', 'en_cours', 'termine')
          AND date_debut <= ?
          AND date_fin >= ?
        ORDER BY date_debut DESC, id_break DESC
        LIMIT 1
        """,
        (employee_id, target_date, target_date),
    ).fetchone()
    if not row:
        return
    if row["statut"] == "termine":
        raise ValueError("Ce jour appartient a un break termine. Corrige-le dans le module Breaks avant modification.")
    if str(row["date_debut"]) != target_date or str(row["date_fin"]) != target_date:
        raise ValueError("Ce jour appartient a un break multi-jours. Modifie-le dans le module Breaks.")


def _default_times_for_activity(has_drilling: bool) -> tuple[str, str]:
    return ("06:00", "18:00") if has_drilling else ("06:00", "14:00")


def _ensure_not_future(target_date: str) -> None:
    if _parse_date(target_date) > date.today():
        raise ValueError("Modification impossible: ce jour n'est pas encore arrive.")


def _timesheet_month_for_date(value: str) -> str:
    parsed = _parse_date(value)
    if parsed.day >= 21:
        return parsed.strftime("%Y-%m")
    first = parsed.replace(day=1)
    previous = first - timedelta(days=1)
    return previous.strftime("%Y-%m")


def _break_label(kind: str) -> str:
    return {
        "break": "B",
        "permission": "P",
        "sick": "S",
        "annual": "AL",
    }.get(kind, "B")


def _weekday_label(value: str) -> str:
    labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    return labels[_parse_date(value).weekday()]


def _is_sunday(value: str) -> bool:
    return _parse_date(value).weekday() == 6


def _period_week_index(day_index: int) -> int:
    return (day_index // 7) + 1


def _parse_month(value: str) -> date:
    text = str(value or "").strip()
    try:
        parsed = datetime.strptime(text, "%Y-%m").date()
    except ValueError as exc:
        raise ValueError("Format mois invalide. Utilise AAAA-MM.") from exc
    last_day = calendar.monthrange(parsed.year, parsed.month)[1]
    if parsed.day > last_day:
        raise ValueError("Mois invalide.")
    return parsed.replace(day=1)


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Format date invalide. Utilise AAAA-MM-JJ.") from exc
