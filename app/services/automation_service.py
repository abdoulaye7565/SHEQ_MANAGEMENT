from __future__ import annotations

from typing import Any

from app.services.attendance_service import ensure_attendance_day, today_iso
from app.services.maintenance_action_service import sync_overdue_maintenance_actions
from app.services.toolbox_talk_service import (
    assign_monthly_topics,
    current_toolbox_month,
    generate_toolbox_theme_catalog,
)


def run_startup_automations() -> dict[str, Any]:
    results: dict[str, Any] = {
        "attendance_ready": False,
        "maintenance": {"maintenance": 0, "actions": 0},
        "toolbox_assigned": 0,
        "warnings": [],
    }
    try:
        ensure_attendance_day(today_iso())
        results["attendance_ready"] = True
    except ValueError as exc:
        results["warnings"].append(f"Presence: {exc}")
    try:
        results["maintenance"] = sync_overdue_maintenance_actions()
    except ValueError as exc:
        results["warnings"].append(f"Maintenance: {exc}")
    try:
        generate_toolbox_theme_catalog()
        results["toolbox_assigned"] = assign_monthly_topics(current_toolbox_month(), overwrite=False)
    except ValueError as exc:
        results["warnings"].append(f"Toolbox: {exc}")
    return results
