"""SHEQ Timesheet 01-25 — logique calquée sur le format Excel SHEQ HOUR STATS.

Vue séparée du timesheet RH :
- Tous les shifts = 10h (pas de 12h, pas de 8h breaks)
- Cellules : 10 (travaillé) | WOR (repos rotatif) | LEAVE (congé) | SICK (maladie) | blank (absent/dimanche)
- Séparation EXPATS / LOCALS
- Totaux : Hrs = shifts×10, Shifts = jours travaillés, TRN = shifts formation
- Stats journalières : Labour actif par jour, WOR par jour, absents par jour
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.db.connection import db_session
from app.services.monthly_timesheet_service import get_monthly_10h_timesheet
from app.services.timesheet_period_service import TIMESHEET_1_25, get_timesheet_period_for_month

_log = logging.getLogger(__name__)

SHEQ_WORK_HOURS = 10


# ── Status → SHEQ label ───────────────────────────────────────────────────────

def sheq_cell_label(status: str) -> str:
    """Map project status to SHEQ Excel cell value."""
    return {
        "worked":       "10",
        "rest":         "WOR",
        "normal_break": "WOR",
        "annual_break": "LEAVE",
        "permission":   "LEAVE",
        "sick":         "SICK",
        "absent":       "",
        "unfilled":     "",
        "not_assigned": "",
        "holiday":      "10",   # jours fériés comptent comme travaillés dans SHEQ
    }.get(status, "")


def sheq_cell_hours(label: str) -> int:
    """Hours credited in SHEQ for each label."""
    return SHEQ_WORK_HOURS if label == "10" else 0


# ── Main SHEQ builder ─────────────────────────────────────────────────────────

def build_sheq_timesheet(
    month: str | None = None,
    site_id: int | None = None,
) -> dict[str, Any]:
    """Build the full SHEQ Timesheet data structure for the 01-25 period.

    Returns a dict with:
      period, days, expats, locals,
      daily_stats (Labour/WOR/Absent per day),
      grand_totals (Hrs, Shifts, Labour headcount),
    """
    from app.services.monthly_timesheet_service import current_monthly_timesheet_month
    selected_month = month or current_monthly_timesheet_month()
    period = get_timesheet_period_for_month(TIMESHEET_1_25, selected_month)
    days = _list_period_days(period)

    # Load both employee types in parallel (same period)
    expat_ts = get_monthly_10h_timesheet(selected_month, site_id, "expatriate", TIMESHEET_1_25)
    local_ts  = get_monthly_10h_timesheet(selected_month, site_id, "national",   TIMESHEET_1_25)

    # Training shifts per employee for the period
    trn_by_employee = _training_shifts_by_employee(period["start"], period["end"])

    expats = [_build_sheq_row(r, trn_by_employee) for r in expat_ts.get("rows", [])]
    locals_ = [_build_sheq_row(r, trn_by_employee) for r in local_ts.get("rows", [])]

    all_rows = expats + locals_
    daily_stats = _compute_daily_stats(all_rows, days)
    grand_totals = _compute_grand_totals(all_rows)

    return {
        "period": period,
        "month": selected_month,
        "days": days,
        "expats": expats,
        "locals": locals_,
        "daily_stats": daily_stats,
        "grand_totals": grand_totals,
        "site_id": site_id,
    }


# ── Row builder ───────────────────────────────────────────────────────────────

def _build_sheq_row(row: dict[str, Any], trn_by_employee: dict[int, int]) -> dict[str, Any]:
    """Convert a monthly_timesheet row to SHEQ format."""
    employee = row["employee"]
    employee_id = int(employee["id_employe"])
    sheq_cells: list[dict[str, Any]] = []
    worked_shifts = 0

    for cell in row.get("cells", []):
        label = sheq_cell_label(cell["status"])
        hours = sheq_cell_hours(label)
        if label == "10":
            worked_shifts += 1
        sheq_cells.append({
            "date":    cell["date"],
            "day":     cell["day"],
            "weekday": cell["weekday"],
            "status":  cell["status"],
            "label":   label,
            "hours":   hours,
        })

    trn_shifts = trn_by_employee.get(employee_id, 0)

    return {
        "employee":      employee,
        "sheq_cells":    sheq_cells,
        "sheq_hrs":      worked_shifts * SHEQ_WORK_HOURS,
        "sheq_shifts":   worked_shifts,
        "sheq_trn":      trn_shifts,
        # Keep original totals for reference
        "worked_days":   row.get("worked_days", 0),
        "rest_days":     row.get("rest_days", 0) + row.get("normal_break_days", 0),
        "leave_days":    row.get("annual_break_days", 0) + row.get("permission_days", 0),
        "sick_days":     row.get("sick_days", 0),
        "absent_days":   row.get("absent_days", 0),
    }


# ── Daily stats ───────────────────────────────────────────────────────────────

def _compute_daily_stats(
    all_rows: list[dict[str, Any]],
    days: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per-day: Labour (active = '10'), WOR count, Absent/Leave count, Hours."""
    stats: list[dict[str, Any]] = []
    for day_info in days:
        day_str = day_info["date"]
        labour = wor = absent = leave = sick = 0
        daily_hrs = 0
        for row in all_rows:
            for cell in row["sheq_cells"]:
                if cell["date"] == day_str:
                    lbl = cell["label"]
                    if lbl == "10":
                        labour += 1
                        daily_hrs += SHEQ_WORK_HOURS
                    elif lbl == "WOR":
                        wor += 1
                    elif lbl == "LEAVE":
                        leave += 1
                    elif lbl == "SICK":
                        sick += 1
                    else:
                        absent += 1
        stats.append({
            "date":       day_str,
            "day":        day_info["day"],
            "weekday":    day_info["weekday"],
            "is_sunday":  day_info.get("is_sunday", False),
            "labour":     labour,
            "wor":        wor,
            "leave":      leave,
            "sick":       sick,
            "absent":     absent,
            "total_hrs":  daily_hrs,
        })
    return stats


def _compute_grand_totals(all_rows: list[dict[str, Any]]) -> dict[str, int]:
    total_hrs = sum(r["sheq_hrs"] for r in all_rows)
    total_shifts = sum(r["sheq_shifts"] for r in all_rows)
    total_trn = sum(r["sheq_trn"] for r in all_rows)
    headcount = len(all_rows)
    return {
        "headcount":    headcount,
        "total_hrs":    total_hrs,
        "total_shifts": total_shifts,
        "total_trn":    total_trn,
    }


# ── Training shifts ───────────────────────────────────────────────────────────

def _training_shifts_by_employee(start: str, end: str) -> dict[int, int]:
    """Count training days (formations attended) per employee within the period.

    A 'training shift' = a day when an employee started a formation.
    """
    try:
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT employe_id, COUNT(DISTINCT date_debut) AS trn_count
                FROM formations
                WHERE date_debut BETWEEN ? AND ?
                  AND statut IN ('valide', 'en_cours')
                GROUP BY employe_id
                """,
                (start, end),
            ).fetchall()
        return {int(r["employe_id"]): int(r["trn_count"]) for r in rows}
    except Exception as exc:
        _log.warning("[sheq_timesheet] training shifts failed: %s", exc)
        return {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _list_period_days(period: dict[str, Any]) -> list[dict[str, Any]]:
    from datetime import timedelta
    start = date.fromisoformat(period["start"])
    end   = date.fromisoformat(period["end"])
    days  = []
    current = start
    while current <= end:
        days.append({
            "date":      current.isoformat(),
            "day":       current.day,
            "weekday":   _weekday_label(current),
            "is_sunday": current.weekday() == 6,
        })
        current += timedelta(days=1)
    return days


def _weekday_label(d: date) -> str:
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]
