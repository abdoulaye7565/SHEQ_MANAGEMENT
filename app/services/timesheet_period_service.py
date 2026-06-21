from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.db.connection import db_session


TIMESHEET_21_20 = "21_20"
TIMESHEET_1_25 = "1_25"
TIMESHEET_TYPES = {TIMESHEET_21_20, TIMESHEET_1_25}


def get_active_timesheet_period(type_timesheet: str, current_date: date | None = None) -> dict[str, str]:
    """Return the period that must be displayed by default for the supplied date."""
    timesheet_type = _normalize_type(type_timesheet)
    today = current_date or date.today()
    if timesheet_type == TIMESHEET_21_20:
        anchor = today.replace(day=1)
        if today.day <= 20:
            anchor = (anchor - timedelta(days=1)).replace(day=1)
        return get_timesheet_period_for_month(timesheet_type, anchor.strftime("%Y-%m"))

    anchor = today.replace(day=1)
    if today.day > 25:
        anchor = _next_month(anchor)
    return get_timesheet_period_for_month(timesheet_type, anchor.strftime("%Y-%m"))


def get_timesheet_period_for_month(type_timesheet: str, month: str) -> dict[str, str]:
    """Build a stable TimeSheet period from its anchor month."""
    timesheet_type = _normalize_type(type_timesheet)
    anchor = _parse_month(month)
    if timesheet_type == TIMESHEET_21_20:
        start = anchor.replace(day=21)
        end = _next_month(anchor).replace(day=20)
        label = f"TimeSheet {anchor:%Y-%m} (21/{anchor:%m} au 20/{end:%m})"
    else:
        start = anchor.replace(day=1)
        end = anchor.replace(day=25)
        label = f"TimeSheet {anchor:%Y-%m} (01 au 25)"
    return {
        "type": timesheet_type,
        "month": anchor.strftime("%Y-%m"),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "label": label,
    }


def get_timesheet_sync_status(
    type_timesheet: str,
    month: str,
    site_id: int | None = None,
) -> dict[str, Any]:
    """Describe the presence data used to calculate a TimeSheet period."""
    period = get_timesheet_period_for_month(type_timesheet, month)
    selected_site_id = int(site_id or 0) or None
    site_join = ""
    site_filter = ""
    params: list[Any] = [period["start"], period["end"]]
    if selected_site_id is not None:
        site_join = "JOIN employes e ON e.id_employe = p.employe_id"
        site_filter = "AND e.site_id = ?"
        params.append(selected_site_id)
    with db_session() as connection:
        presence_row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS records,
                COUNT(DISTINCT p.date_presence) AS days_with_data,
                MAX(p.updated_at) AS last_presence_update
            FROM presences p
            {site_join}
            WHERE p.date_presence BETWEEN ? AND ?
            {site_filter}
            """,
            tuple(params),
        ).fetchone()
        lock_row = connection.execute(
            """
            SELECT COUNT(*) AS validated_days, MAX(locked_at) AS last_validation
            FROM attendance_day_locks
            WHERE date_presence BETWEEN ? AND ?
            """,
            (period["start"], period["end"]),
        ).fetchone()
    records = int(presence_row["records"] or 0)
    days_with_data = int(presence_row["days_with_data"] or 0)
    validated_days = int(lock_row["validated_days"] or 0)
    return {
        "source": "presences",
        "period": period,
        "presence_records": records,
        "days_with_data": days_with_data,
        "validated_days": validated_days,
        "unvalidated_days_with_data": max(days_with_data - validated_days, 0),
        "last_presence_update": presence_row["last_presence_update"],
        "last_validation": lock_row["last_validation"],
        "synchronized": True,
        "message": "TimeSheet calcule en direct depuis la liste de presence.",
    }


def validate_timesheet_export_payload(payload: dict[str, Any], type_timesheet: str) -> dict[str, Any]:
    """Prevent exporting a payload whose dates do not match its declared period."""
    period = dict(payload.get("period") or {})
    expected = get_timesheet_period_for_month(type_timesheet, str(period.get("month") or ""))
    if period.get("start") != expected["start"] or period.get("end") != expected["end"]:
        raise ValueError("Export impossible: la periode TimeSheet affichee est incoherente.")
    synchronization = dict(payload.get("synchronization") or {})
    if synchronization and synchronization.get("source") != "presences":
        raise ValueError("Export impossible: la liste de presence n'est pas la source du TimeSheet.")
    sync_period = dict(synchronization.get("period") or {})
    if sync_period and (sync_period.get("start") != expected["start"] or sync_period.get("end") != expected["end"]):
        raise ValueError("Export impossible: la synchronisation presence utilise une autre periode.")
    start = expected["start"]
    end = expected["end"]
    for row in payload.get("rows") or []:
        for cell in row.get("cells") or []:
            cell_date = str(cell.get("date") or "")
            if not start <= cell_date <= end:
                raise ValueError("Export impossible: une donnee de presence est hors de la periode TimeSheet.")
    if not payload.get("rows"):
        raise ValueError("Export impossible: le TimeSheet est vide pour cette periode.")
    return expected


def _normalize_type(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace("->", "_")
    aliases = {"21_20": TIMESHEET_21_20, "2120": TIMESHEET_21_20, "1_25": TIMESHEET_1_25, "01_25": TIMESHEET_1_25, "125": TIMESHEET_1_25}
    result = aliases.get(normalized)
    if result is None:
        raise ValueError("Type TimeSheet invalide. Utilise 21_20 ou 1_25.")
    return result


def _parse_month(month: str) -> date:
    try:
        parsed = date.fromisoformat(f"{str(month or '').strip()}-01")
    except ValueError as exc:
        raise ValueError("Format mois invalide. Utilise AAAA-MM.") from exc
    return parsed


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)
