from __future__ import annotations

from datetime import date
from typing import Any

from app.db.connection import db_session
from app.services.timesheet_period_service import (
    TIMESHEET_1_25,
    TIMESHEET_21_20,
    get_active_timesheet_period,
    get_timesheet_period_for_month,
    get_timesheet_sync_status,
)


WORK_HOURS = 10
HOLIDAY_HOURS = 8
BREAK_HOURS = 8
PERMISSION_DAYS = 3


def current_monthly_timesheet_month() -> str:
    return get_active_timesheet_period(TIMESHEET_1_25)["month"]


def get_monthly_timesheet_period(month: str) -> dict[str, str]:
    return get_timesheet_period_for_month(TIMESHEET_1_25, month)


def list_monthly_timesheet_days(month: str) -> list[str]:
    period = get_monthly_timesheet_period(month)
    return _list_days_for_period(period)


def _list_days_for_period(period: dict) -> list[str]:
    from datetime import timedelta
    start = date.fromisoformat(period["start"])
    end = date.fromisoformat(period["end"])
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def list_monthly_timesheet_site_options() -> list[dict[str, Any]]:
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


def get_monthly_10h_timesheet(
    month: str | None = None,
    site_id: int | None = None,
    employee_type: str = "national",
    ts_type: str | None = None,
) -> dict[str, Any]:
    selected_month = month or current_monthly_timesheet_month()
    resolved_type = ts_type or TIMESHEET_1_25
    period = get_timesheet_period_for_month(resolved_type, selected_month)
    days = _list_days_for_period(period)
    selected_site_id = int(site_id or 0) or None
    selected_employee_type = str(employee_type or "national").strip()
    if selected_employee_type not in {"national", "expatriate"}:
        raise ValueError("Type employe invalide pour le TimeSheet.")
    with db_session() as connection:
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
                b.numero_badge,
                f.nom AS fonction,
                s.id_site AS site_id,
                s.nom AS site,
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
            WHERE e.type_employe = ?
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
                OR EXISTS (
                    SELECT 1
                    FROM timesheet_day_overrides tdo
                    WHERE tdo.employe_id = e.id_employe
                      AND tdo.date_presence BETWEEN ? AND ?
                )
              )
              {site_filter}
            ORDER BY nom, prenom, e.nom_complet
            """,
            (
                selected_employee_type,
                period["start"],
                period["end"],
                period["end"],
                period["start"],
                period["start"],
                period["end"],
                *site_params,
            ),
        ).fetchall()
        breaks = _breaks_by_employee(connection, period["start"], period["end"])
        presences = _presences_by_employee(connection, period["start"], period["end"])
        overrides = _overrides_by_employee(connection, period["start"], period["end"])
        settings = _settings_by_day(connection, period["start"], period["end"])
        assignments = _site_assignments_by_employee(connection, period["start"], period["end"], selected_site_id)
        site = _site_context(connection, selected_site_id)

    rows: list[dict[str, Any]] = []
    summary = {
        "employees": 0,
        "worked_days": 0,
        "rest_days": 0,
        "normal_break_days": 0,
        "permission_days": 0,
        "sick_days": 0,
        "annual_break_days": 0,
        "absent_days": 0,
        "unfilled_days": 0,
        "hours": 0,
    }
    for employee in employees:
        employee_id = int(employee["id_employe"])
        cells = []
        employee_hours = 0
        worked_days = 0
        rest_days = 0
        normal_break_days = 0
        permission_days = 0
        sick_days = 0
        annual_break_days = 0
        absent_days = 0
        unfilled_days = 0
        for day in days:
            parsed = date.fromisoformat(day)
            if selected_site_id is not None and not _assigned_to_site_on_day(
                assignments.get(employee_id, []),
                selected_site_id,
                day,
            ):
                status = "not_assigned"
                label = "N/A"
                hours = 0
                break_type = None
                break_start = None
                break_end = None
            else:
                break_record = _break_for_day(breaks.get(employee_id, []), day)
                presence = presences.get((employee_id, day))
                override = overrides.get((employee_id, day))
                day_type = str(settings.get(day, {}).get("day_type") or "work")
                if break_record and _permission_exceeds_allowed_days(break_record, day):
                    status = "absent"
                    label = "A"
                    hours = 0
                    absent_days += 1
                elif break_record and str(break_record.get("type_break")) == "annual":
                    status = "annual_break"
                    label = "AL"
                    hours = BREAK_HOURS
                    employee_hours += hours
                    annual_break_days += 1
                elif break_record and str(break_record.get("type_break")) == "permission":
                    status = "permission"
                    label = "P"
                    hours = BREAK_HOURS
                    employee_hours += hours
                    permission_days += 1
                elif break_record and str(break_record.get("type_break")) == "sick":
                    status = "sick"
                    label = "S"
                    hours = BREAK_HOURS
                    employee_hours += hours
                    sick_days += 1
                elif break_record:
                    status = "normal_break"
                    label = "B"
                    hours = BREAK_HOURS
                    employee_hours += hours
                    normal_break_days += 1
                elif override:
                    status = str(override.get("status") or "rest")
                    label = "R" if status == "rest" else "A"
                    hours = 0
                    if status == "rest":
                        rest_days += 1
                    else:
                        absent_days += 1
                elif day_type == "holiday":
                    status = "holiday"
                    label = "8H"
                    hours = HOLIDAY_HOURS
                    employee_hours += hours
                elif parsed.weekday() == 6:
                    if presence and presence.get("statut_presence") == "present":
                        status = "worked"
                        label = "10h"
                        hours = WORK_HOURS
                        employee_hours += hours
                        worked_days += 1
                    else:
                        status = "rest"
                        label = "R"
                        hours = 0
                        rest_days += 1
                elif presence and presence.get("statut_presence") == "present":
                    status = "worked"
                    label = "10h"
                    hours = WORK_HOURS
                    employee_hours += hours
                    worked_days += 1
                elif presence and presence.get("statut_presence") == "absent":
                    status = "absent"
                    label = "A"
                    hours = 0
                    absent_days += 1
                else:
                    status = "unfilled"
                    label = "NR"
                    hours = 0
                    unfilled_days += 1
                break_type = str(break_record.get("type_break")) if break_record else None
                break_start = str(break_record.get("date_debut")) if break_record else None
                break_end = str(break_record.get("date_fin")) if break_record else None
            cells.append(
                {
                    "date": day,
                    "day": int(day[-2:]),
                    "weekday": _weekday_label(day),
                    "status": status,
                    "label": label,
                    "hours": hours,
                    "break_type": break_type,
                    "break_start": break_start,
                    "break_end": break_end,
                }
            )
        rows.append(
            {
                "employee": dict(employee),
                "cells": cells,
                "worked_days": worked_days,
                "rest_days": rest_days,
                "normal_break_days": normal_break_days,
                "permission_days": permission_days,
                "sick_days": sick_days,
                "annual_break_days": annual_break_days,
                "absent_days": absent_days,
                "unfilled_days": unfilled_days,
                "hours": employee_hours,
            }
        )
        summary["employees"] += 1
        summary["worked_days"] += worked_days
        summary["rest_days"] += rest_days
        summary["normal_break_days"] += normal_break_days
        summary["permission_days"] += permission_days
        summary["sick_days"] += sick_days
        summary["annual_break_days"] += annual_break_days
        summary["absent_days"] += absent_days
        summary["unfilled_days"] += unfilled_days
        summary["hours"] += employee_hours
    return {
        "period": period,
        "synchronization": get_timesheet_sync_status(resolved_type, selected_month, selected_site_id),
        "site_id": selected_site_id,
        "site": site,
        "days": [
            {
                "date": day,
                "day": int(day[-2:]),
                "weekday": _weekday_label(day),
                "is_sunday": date.fromisoformat(day).weekday() == 6,
            }
            for day in days
        ],
        "rows": rows,
        "summary": summary,
    }


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


def _presences_by_employee(connection: Any, start: str, end: str) -> dict[tuple[int, str], dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT employe_id, date_presence, statut_presence, heures_travaillees
        FROM presences
        WHERE date_presence BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchall()
    return {
        (int(row["employe_id"]), str(row["date_presence"])): dict(row)
        for row in rows
    }


def _overrides_by_employee(connection: Any, start: str, end: str) -> dict[tuple[int, str], dict[str, Any]]:
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


def _settings_by_day(connection: Any, start: str, end: str) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT date_presence, day_type
        FROM timesheet_day_settings
        WHERE date_presence BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchall()
    return {
        str(row["date_presence"]): {"day_type": str(row["day_type"] or "work")}
        for row in rows
    }


def _permission_exceeds_allowed_days(record: dict[str, Any], day: str) -> bool:
    if str(record.get("type_break") or "") != "permission":
        return False
    start = date.fromisoformat(str(record.get("date_debut") or ""))
    current = date.fromisoformat(day)
    return (current - start).days >= PERMISSION_DAYS


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


def _site_context(connection: Any, site_id: int | None) -> dict[str, Any] | None:
    if site_id is None:
        return None
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


def _parse_month(value: str) -> date:
    try:
        parsed = date.fromisoformat(f"{str(value or '').strip()}-01")
    except ValueError as exc:
        raise ValueError("Mois invalide. Utilise le format AAAA-MM.") from exc
    return parsed


def _weekday_label(value: str) -> str:
    labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    return labels[date.fromisoformat(value).weekday()]
