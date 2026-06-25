from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.config import EXPORTS_DIR
from app.services.attendance_service import get_attendance_list
from app.services.employee_service import list_employees
from app.services.break_service import list_active_break_employees
from app.services.ppe_service import (
    get_ppe_export_data,
    list_ppe_assignments,
    list_ppe_employee_compliance_summary,
    list_ppe_inspections,
)
from app.services.monthly_timesheet_service import current_monthly_timesheet_month, get_monthly_10h_timesheet
from app.services.timesheet_service import get_timesheet, list_timesheet_audit, list_timesheet_history
from app.services.timesheet_period_service import (
    TIMESHEET_1_25,
    TIMESHEET_21_20,
    validate_timesheet_export_payload,
)
from app.services.toolbox_talk_service import list_toolbox_topics
from app.services.xlsx_service import (
    write_attendance_list_xlsx as write_attendance_list_workbook,
    write_daily_lineup_xlsx as write_daily_lineup_workbook,
    write_monthly_timesheet_report_xlsx,
    write_styled_xlsx,
    write_timesheet_21_20_report_xlsx,
    write_toolbox_talk_xlsx as write_toolbox_talk_workbook,
)


def export_rows_xlsx(
    filename: str,
    sheet_name: str,
    headers: list[str],
    rows: list[list[Any]],
) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = "".join(char if char.isalnum() or char in "._-" else "_" for char in filename)
    output_path = _unique_export_path(safe_filename)
    return _write_xlsx_safely(output_path, sheet_name[:31], headers, rows)


def export_styled_rows_xlsx(
    filename: str,
    sheet_name: str,
    headers: list[str],
    rows: list[list[Any]],
    styles: list[list[str | None]],
    document_title: str | None = None,
) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = "".join(char if char.isalnum() or char in "._-" else "_" for char in filename)
    output_path = _unique_export_path(safe_filename)
    return _write_styled_xlsx_safely(output_path, sheet_name[:31], headers, rows, styles, document_title=document_title)


def export_attendance_xlsx(date_presence: str) -> Path:
    rows = get_attendance_list(date_presence)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return export_attendance_records_xlsx(date_presence, [
        {
            "nom": row.get("nom") or "",
            "prenom": row.get("prenom") or "",
            "numero_badge": row.get("numero_badge") or "",
            "fonction": row.get("fonction") or "",
            "type_employe": row.get("type_employe") or "national",
            "shift": row.get("shift") or "",
            "statut": "Present" if row.get("statut_presence") == "present" else "Absent",
            "heure_entree": row.get("heure_entree") or "",
            "heure_sortie": row.get("heure_sortie") or "",
            "heures": row.get("heures_travaillees") or 0,
            "controle": "",
        }
        for row in rows
    ])


def export_attendance_records_xlsx(date_presence: str, records: list[dict[str, Any]]) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path(f"liste_presence_orezone_{date_presence}.xlsx")
    summary = {
        "total": len(records),
        "present": sum(1 for row in records if str(row.get("statut") or "").lower() == "present"),
        "absent": sum(1 for row in records if str(row.get("statut") or "").lower() == "absent"),
        "hours": round(sum(float(row.get("heures") or 0) for row in records), 2),
        "issues": sum(1 for row in records if str(row.get("controle") or "").lower() not in ("", "ok")),
        "day": sum(1 for row in records if "day" in str(row.get("shift") or "").lower()),
        "night": sum(1 for row in records if "night" in str(row.get("shift") or "").lower()),
        "missing_badge": sum(1 for row in records if not row.get("numero_badge")),
        "overtime": sum(1 for row in records if float(row.get("heures") or 0) > 12),
    }
    try:
        write_attendance_list_workbook(output_path, date_presence, records, datetime.now().strftime("%Y-%m-%d %H:%M"), summary)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(f"liste_presence_orezone_{date_presence}_nouveau.xlsx")
        write_attendance_list_workbook(fallback, date_presence, records, datetime.now().strftime("%Y-%m-%d %H:%M"), summary)
        return fallback


def export_attendance_pdf(date_presence: str) -> Path:
    rows = get_attendance_list(date_presence)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path(f"liste_presence_{date_presence}.pdf")
    records = [
        {
            "nom": row.get("nom") or "",
            "prenom": row.get("prenom") or "",
            "nom_complet": row.get("nom_complet") or "",
            "numero_badge": row.get("numero_badge") or "",
            "fonction": row.get("fonction") or "",
            "type_employe": row.get("type_employe") or "national",
            "shift": row.get("shift") or "",
            "statut": "Present" if row.get("statut_presence") == "present" else "Absent",
            "heure_entree": row.get("heure_entree") or "",
            "heure_sortie": row.get("heure_sortie") or "",
            "heures": row.get("heures_travaillees") or 0,
            "controle": "",
        }
        for row in rows
    ]
    summary = {
        "total": len(records),
        "present": sum(1 for row in records if str(row.get("statut") or "").lower() == "present"),
        "absent": sum(1 for row in records if str(row.get("statut") or "").lower() == "absent"),
        "hours": round(sum(float(row.get("heures") or 0) for row in records), 2),
        "day": sum(1 for row in records if "day" in str(row.get("shift") or "").lower()),
        "night": sum(1 for row in records if "night" in str(row.get("shift") or "").lower()),
        "missing_badge": sum(1 for row in records if not row.get("numero_badge")),
    }
    try:
        _write_attendance_pdf(output_path, date_presence, records, summary)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(f"liste_presence_{date_presence}_nouveau.pdf")
        _write_attendance_pdf(fallback, date_presence, records, summary)
        return fallback


def export_employees_xlsx() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("liste_employes.xlsx")
    headers = ["Matricule", "Nom", "Prenom", "Badge", "Fonction", "Site", "Situation"]
    rows = [
        [
            row.get("matricule") or "",
            row.get("nom") or row.get("nom_complet") or "",
            row.get("prenom") or "",
            row.get("numero_badge") or "",
            row.get("fonction") or "",
            row.get("site") or "",
            _state_label(row.get("current_state")),
        ]
        for row in list_employees()
    ]
    return _write_xlsx_safely(output_path, "Employes", headers, rows)


def export_daily_lineup_xlsx(records: list[dict[str, Any]]) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("list_of_orezone_employee.xlsx")
    rows, summary = _daily_lineup_export_payload(records)
    try:
        write_daily_lineup_workbook(output_path, rows, datetime.now().strftime("%Y-%m-%d %H:%M"), summary)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("list_of_orezone_employee_nouveau.xlsx")
        write_daily_lineup_workbook(fallback, rows, datetime.now().strftime("%Y-%m-%d %H:%M"), summary)
        return fallback


def export_daily_lineup_pdf(records: list[dict[str, Any]]) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("list_of_orezone_employee.pdf")
    rows, summary = _daily_lineup_export_payload(records)
    try:
        _write_employee_list_pdf(output_path, rows, summary)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("list_of_orezone_employee_nouveau.pdf")
        _write_employee_list_pdf(fallback, rows, summary)
        return fallback


def _daily_lineup_export_payload(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows = [
        {
            "matricule": row.get("matricule") or "",
            "nom": row.get("nom") or row.get("nom_complet") or "",
            "prenom": row.get("prenom") or "",
            "numero_badge": row.get("numero_badge") or "",
            "fonction": row.get("fonction") or "",
            "site": row.get("site") or "",
            "shift": _shift_label(row.get("shift_code"), row.get("shift")),
            "situation": _state_label(row.get("current_state")),
            "prochain_break": _break_due_text(row),
            "observation": _lineup_observation(row),
        }
        for row in records
    ]
    summary = {
        "total": len(records),
        "day": sum(1 for row in records if row.get("shift_code") == "DAY"),
        "night": sum(1 for row in records if row.get("shift_code") == "NIGHT"),
        "off": sum(1 for row in records if str(row.get("current_state") or "work") != "work"),
        "due": sum(
            1
            for row in records
            if row.get("days_until_break_due") is not None
            and int(row["days_until_break_due"]) <= 0
            and not row.get("next_planned_break_start")
        ),
    }
    return rows, summary


def export_training_matrix_xls(
    training_types: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("matrice_formations_orezone.xlsx")
    try:
        _write_training_matrix_xlsx(output_path, training_types, rows)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("matrice_formations_orezone_nouveau.xlsx")
        _write_training_matrix_xlsx(fallback, training_types, rows)
        return fallback


def export_timesheet_xls(month: str, site_id: int | None = None) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timesheet = get_timesheet(month, site_id=site_id)
    validate_timesheet_export_payload(timesheet, TIMESHEET_21_20)
    site_suffix = ""
    if timesheet.get("site"):
        site_suffix = "_" + "".join(
            char if char.isalnum() or char in "._-" else "_"
            for char in str(timesheet["site"].get("nom") or "")
        )
    output_path = _unique_export_path(f"timesheet_orezone{site_suffix}_{timesheet['period']['month']}.xlsx")
    try:
        _write_timesheet_xlsx(output_path, timesheet)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(f"timesheet_orezone{site_suffix}_{timesheet['period']['month']}_nouveau.xlsx")
        _write_timesheet_xlsx(fallback, timesheet)
        return fallback


def export_timesheet_employee_xls(month: str, employee_id: int) -> Path:
    timesheet = get_timesheet(month)
    validate_timesheet_export_payload(timesheet, TIMESHEET_21_20)
    employee_id = int(employee_id or 0)
    if not employee_id:
        raise ValueError("Employe obligatoire pour l'export TimeSheet individuel.")
    selected_rows = [
        row
        for row in timesheet["rows"]
        if int(row["employee"].get("id_employe") or 0) == employee_id
    ]
    if not selected_rows:
        raise ValueError("Employe introuvable dans ce TimeSheet.")
    employee_name = _timesheet_employee_name(selected_rows[0]["employee"])
    safe_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in employee_name)[:50]
    individual = {
        **timesheet,
        "rows": selected_rows,
        "summary": _timesheet_summary_for_rows(timesheet["summary"], selected_rows),
        "print_individual": True,
    }
    output_path = _unique_export_path(
        f"timesheet_orezone_{timesheet['period']['month']}_{safe_name or employee_id}.xlsx"
    )
    try:
        _write_timesheet_xlsx(output_path, individual)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(
            f"timesheet_orezone_{timesheet['period']['month']}_{safe_name or employee_id}_nouveau.xlsx"
        )
        _write_timesheet_xlsx(fallback, individual)
        return fallback


def export_timesheet_all_employees_xls(month: str) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timesheet = get_timesheet(month)
    validate_timesheet_export_payload(timesheet, TIMESHEET_21_20)
    rows = list(timesheet.get("rows") or [])
    if not rows:
        raise ValueError("Aucun employe disponible pour cet export TimeSheet.")
    return _export_timesheet_rows_to_directory(timesheet, rows, "timesheets_individuels_orezone")


def export_timesheet_annual_history_xls(site_id: int | None = None) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    history_21_20 = list_timesheet_history(limit=12)
    history_1_25 = _last_twelve_calendar_months()
    if not history_21_20 and not history_1_25:
        raise ValueError("Aucun historique TimeSheet disponible pour l'export annuel.")
    site_suffix = ""
    if site_id is not None:
        site_suffix = f"_site_{int(site_id)}"
    output_dir = _unique_export_dir(f"historique_timesheets_12_mois{site_suffix}")
    output_dir.mkdir(parents=True, exist_ok=True)
    timesheet_21_20_dir = output_dir / "timesheet_21_20"
    timesheet_1_25_dir = output_dir / "timesheet_1_25"
    timesheet_21_20_dir.mkdir(parents=True, exist_ok=True)
    timesheet_1_25_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[list[Any]] = []
    for item in history_21_20:
        month = str(item["month"])
        timesheet = get_timesheet(month, site_id=site_id)
        summary = timesheet.get("summary") or {}
        period = timesheet.get("period") or {}
        summary_rows.append(
            [
                "TimeSheet 21-20",
                month,
                period.get("start") or "",
                period.get("end") or "",
                summary.get("employees", 0),
                summary.get("worked_days", 0),
                summary.get("rest_days", 0),
                summary.get("break_days", 0),
                summary.get("permission_days", 0),
                summary.get("sick_days", 0),
                summary.get("absent_days", 0),
                summary.get("unfilled_days", 0),
                summary.get("drilling_hours", 0),
                summary.get("standard_hours", 0),
                summary.get("hours", 0),
                len(timesheet.get("rows") or []),
            ]
        )
        monthly_path = _unique_export_path_in_dir(
            timesheet_21_20_dir,
            f"timesheet_orezone_{month}.xlsx",
        )
        _write_timesheet_xlsx(monthly_path, timesheet)
    for month in history_1_25:
        timesheet = get_monthly_10h_timesheet(month, site_id=site_id)
        expatriates = get_monthly_10h_timesheet(month, site_id=site_id, employee_type="expatriate")
        summary = timesheet.get("summary") or {}
        period = timesheet.get("period") or {}
        summary_rows.append(
            [
                "TimeSheet 1-25",
                month,
                period.get("start") or "",
                period.get("end") or "",
                summary.get("employees", 0),
                summary.get("worked_days", 0),
                summary.get("rest_days", 0),
                summary.get("normal_break_days", 0),
                summary.get("permission_days", 0),
                summary.get("sick_days", 0),
                summary.get("absent_days", 0),
                summary.get("unfilled_days", 0),
                "",
                "",
                summary.get("hours", 0),
                len(timesheet.get("rows") or []),
            ]
        )
        monthly_path = _unique_export_path_in_dir(
            timesheet_1_25_dir,
            f"timesheet_1_25_orezone_{month}.xlsx",
        )
        _write_monthly_10h_timesheet_xlsx(monthly_path, timesheet, expatriates)
    _write_xlsx_safely(
        output_dir / "resume_historique_timesheets_12_mois.xlsx",
        "Historique 12 mois",
        [
            "Type TimeSheet",
            "Mois",
            "Debut periode",
            "Fin periode",
            "Employes",
            "Jours travailles",
            "Repos",
            "Break",
            "Permission",
            "Sick",
            "Absents",
            "Non renseignes",
            "Heures 12H",
            "Heures 8H",
            "Heures totales",
            "Lignes exportees",
        ],
        summary_rows,
    )
    return output_dir


def export_timesheet_selected_employees_xls(month: str, employee_ids: list[int]) -> Path:
    selected_ids = {int(employee_id) for employee_id in employee_ids if int(employee_id or 0)}
    if not selected_ids:
        raise ValueError("Selectionne au moins un employe pour l'export TimeSheet.")
    timesheet = get_timesheet(month)
    validate_timesheet_export_payload(timesheet, TIMESHEET_21_20)
    rows = [
        row
        for row in timesheet.get("rows", [])
        if int(row["employee"].get("id_employe") or 0) in selected_ids
    ]
    if not rows:
        raise ValueError("Aucun des employes selectionnes n'est disponible dans ce TimeSheet.")
    if len(rows) == 1:
        return export_timesheet_employee_xls(month, int(rows[0]["employee"].get("id_employe") or 0))
    return _export_timesheet_rows_to_directory(timesheet, rows, "timesheets_selection_orezone")


def _export_timesheet_rows_to_directory(timesheet: dict[str, Any], rows: list[dict[str, Any]], prefix: str) -> Path:
    output_dir = _unique_export_dir(f"timesheets_individuels_orezone_{timesheet['period']['month']}")
    if prefix != "timesheets_individuels_orezone":
        output_dir = _unique_export_dir(f"{prefix}_{timesheet['period']['month']}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        employee = row["employee"]
        employee_id = int(employee.get("id_employe") or 0)
        employee_name = _timesheet_employee_name(employee)
        safe_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in employee_name)[:50]
        individual = {
            **timesheet,
            "rows": [row],
            "summary": _timesheet_summary_for_rows(timesheet["summary"], [row]),
            "print_individual": True,
        }
        output_path = _unique_export_path_in_dir(
            output_dir,
            f"timesheet_orezone_{timesheet['period']['month']}_{safe_name or employee_id}.xlsx",
        )
        _write_timesheet_xlsx(output_path, individual)
    return output_dir


def export_timesheet_audit_xlsx(month: str) -> Path:
    rows = list_timesheet_audit(month, limit=10000)
    return export_rows_xlsx(
        f"audit_timesheet_orezone_{month}.xlsx",
        "Audit TimeSheet",
        [
            "Date changement",
            "Date TimeSheet",
            "Employe",
            "Action",
            "Ancienne valeur",
            "Nouvelle valeur",
            "Utilisateur",
            "Commentaire",
        ],
        [
            [
                row.get("changed_at") or "",
                row.get("date_presence") or "",
                f"{row.get('nom') or ''} {row.get('prenom') or ''}".strip(),
                row.get("action") or "",
                row.get("ancienne_valeur") or "",
                row.get("nouvelle_valeur") or "",
                row.get("changed_by") or "",
                row.get("commentaire") or "",
            ]
            for row in rows
        ],
    )


def export_monthly_10h_timesheet_xlsx(
    month: str | None = None,
    site_id: int | None = None,
    ts_type: str | None = None,
    employee_id: int | None = None,
) -> Path:
    resolved_ts_type = TIMESHEET_21_20 if ts_type == "21_20" else TIMESHEET_1_25
    selected_month = month or current_monthly_timesheet_month()
    timesheet = get_monthly_10h_timesheet(selected_month, site_id=site_id, ts_type=resolved_ts_type)
    validate_timesheet_export_payload(timesheet, resolved_ts_type)
    expatriates = get_monthly_10h_timesheet(selected_month, site_id=site_id,
                                            employee_type="expatriate", ts_type=resolved_ts_type)
    # Filter to a single employee if requested
    if employee_id is not None:
        timesheet["rows"] = [r for r in timesheet["rows"]
                             if int(r["employee"].get("id_employe") or 0) == employee_id]
        expatriates["rows"] = [r for r in expatriates["rows"]
                               if int(r["employee"].get("id_employe") or 0) == employee_id]
    type_tag = "21_20" if ts_type == "21_20" else "1_25"
    emp_suffix = f"_emp{employee_id}" if employee_id else ""
    site_suffix = ""
    if timesheet.get("site"):
        site_suffix = "_" + _safe_name(timesheet["site"].get("nom") or "")
    output_path = _unique_export_path(
        f"timesheet_10h_{type_tag}{site_suffix}{emp_suffix}_{timesheet['period']['month']}.xlsx"
    )
    try:
        _write_monthly_10h_timesheet_xlsx(output_path, timesheet, expatriates)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(
            f"timesheet_10h_{type_tag}{site_suffix}{emp_suffix}_{timesheet['period']['month']}_nouveau.xlsx"
        )
        _write_monthly_10h_timesheet_xlsx(fallback, timesheet, expatriates)
        return fallback


def export_monthly_10h_timesheet_pdf(
    month: str | None = None,
    ts_type: str | None = None,
    employee_id: int | None = None,
) -> Path:
    """Generate a PDF timesheet for the given month/period and return the file path."""
    from app.services.mobile_sync_service import build_timesheet_pdf_bytes
    selected_month = month or current_monthly_timesheet_month()
    type_tag = "21_20" if ts_type == "21_20" else "1_25"
    emp_suffix = f"_emp{employee_id}" if employee_id else ""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path(f"timesheet_10h_{type_tag}{emp_suffix}_{selected_month}.pdf")
    data = build_timesheet_pdf_bytes(selected_month, ts_type=ts_type or "1_25", employee_id=employee_id)
    output_path.write_bytes(data)
    return output_path


def _write_monthly_10h_timesheet_xlsx(
    path: Path,
    timesheet: dict[str, Any],
    expatriates: dict[str, Any],
) -> None:
    write_monthly_timesheet_report_xlsx(
        path,
        timesheet,
        expatriates,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def _monthly_10h_export_row(row: dict[str, Any]) -> list[Any]:
    employee = row["employee"]
    return [
        _timesheet_employee_name(employee),
        employee.get("numero_badge") or "",
        employee.get("fonction") or "",
        employee.get("site") or "",
        *[cell["label"] for cell in row["cells"]],
        row["worked_days"],
        row["rest_days"],
        row["normal_break_days"],
        row.get("permission_days", 0),
        row.get("sick_days", 0),
        row["annual_break_days"],
        row.get("absent_days", 0),
        row.get("unfilled_days", 0),
        row["hours"],
    ]


def _monthly_10h_export_style(row: dict[str, Any]) -> list[str | None]:
    return [
        None,
        None,
        None,
        None,
        *[_monthly_10h_cell_style(cell) for cell in row["cells"]],
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ]


def export_toolbox_talk_xlsx(month: str) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = list_toolbox_topics(month)
    output_path = _unique_export_path(f"toolbox_talk_meeting_{data['month']}.xlsx")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for row in data["rows"]:
        topic_en, theme_fr = _split_bilingual_toolbox_topic(str(row.get("theme") or ""))
        rows.append({**row, "topic_en": topic_en, "theme_fr": theme_fr})
    try:
        write_toolbox_talk_workbook(
            output_path,
            str(data.get("label") or data["month"]),
            str(data["month"]),
            rows,
            dict(data.get("summary") or {}),
            generated_at,
        )
        return output_path
    except PermissionError:
        fallback = _unique_export_path(f"toolbox_talk_meeting_{data['month']}_nouveau.xlsx")
        write_toolbox_talk_workbook(
            fallback,
            str(data.get("label") or data["month"]),
            str(data["month"]),
            rows,
            dict(data.get("summary") or {}),
            generated_at,
        )
        return fallback


def _split_bilingual_toolbox_topic(value: str) -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        return "", ""
    labeled = _split_labeled_toolbox_topic(text)
    if labeled is not None:
        return labeled
    for separator in (" / ", " | ", " - FR: "):
        if separator in text:
            left, right = text.split(separator, 1)
            return _ordered_bilingual_topic(left, right)
    return text, text


def _split_labeled_toolbox_topic(value: str) -> tuple[str, str] | None:
    text = str(value or "").strip()
    lowered = text.lower()
    markers = {
        "en:": "en",
        "english:": "en",
        "fr:": "fr",
        "french:": "fr",
        "francais:": "fr",
        "fran\u00e7ais:": "fr",
    }
    positions: list[tuple[int, str, str]] = []
    for marker, language in markers.items():
        position = lowered.find(marker)
        if position >= 0:
            positions.append((position, marker, language))
    if len(positions) < 2:
        return None
    positions.sort(key=lambda item: item[0])
    values: dict[str, str] = {}
    for index, (position, marker, language) in enumerate(positions):
        start = position + len(marker)
        end = positions[index + 1][0] if index + 1 < len(positions) else len(text)
        values[language] = _clean_topic_label(text[start:end])
    if values.get("en") or values.get("fr"):
        return values.get("en", ""), values.get("fr", "")
    return None


def _ordered_bilingual_topic(left: str, right: str) -> tuple[str, str]:
    left_clean = _clean_topic_label(left)
    right_clean = _clean_topic_label(right)
    left_language = _detect_topic_language(left_clean)
    right_language = _detect_topic_language(right_clean)
    if left_language == "fr" and right_language != "fr":
        return right_clean, left_clean
    if right_language == "en" and left_language != "en":
        return right_clean, left_clean
    return left_clean, right_clean


def _detect_topic_language(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    french_words = {
        "accidents", "alerte", "analyse", "avant", "balisage", "chaleur",
        "circulation", "controle", "de", "des", "du", "echelles", "engins",
        "epi", "et", "forage", "gestion", "hauteur", "hydratation",
        "incendie", "interdiction", "la", "le", "les", "manutention",
        "obligatoire", "pietons", "port", "prevention", "procedure",
        "produits", "protections", "risques", "securite", "travail",
        "travaux", "utilisation", "vehicules", "verification",
    }
    english_words = {
        "and", "before", "blind", "chemical", "communication", "control",
        "defensive", "driving", "emergency", "equipment", "fall", "fire",
        "for", "hazards", "height", "inspection", "job", "lifting",
        "management", "mandatory", "mobile", "near", "ppe", "prevention",
        "procedure", "protection", "reporting", "response", "risk",
        "safety", "site", "traffic", "use", "work", "working",
    }
    normalized = "".join(char if char.isalnum() else " " for char in text)
    tokens = normalized.split()
    french_score = sum(1 for token in tokens if token in french_words)
    english_score = sum(1 for token in tokens if token in english_words)
    if any(char in text for char in "\u00e0\u00e2\u00e7\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc"):
        french_score += 2
    if french_score > english_score:
        return "fr"
    if english_score > french_score:
        return "en"
    return "unknown"


def _clean_topic_label(value: str) -> str:
    text = str(value or "").strip()
    for prefix in ("EN:", "FR:", "English:", "French:", "Francais:", "Fran\u00e7ais:"):
        if text.lower().startswith(prefix.lower()):
            return text[len(prefix) :].strip()
    return text


def export_ppe_inventory_xls() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = get_ppe_export_data()
    output_path = _unique_export_path("gestion_epi_orezone.xlsx")
    try:
        _write_ppe_inventory_xlsx(output_path, data)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("gestion_epi_orezone_nouveau.xlsx")
        _write_ppe_inventory_xlsx(fallback, data)
        return fallback


def export_ppe_equipped_employees_xlsx() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    assignments = list_ppe_assignments(active_only=True)
    output_path = _unique_export_path("liste_employes_dotes_epi_orezone.xlsx")
    headers = [
        "N",
        "Matricule",
        "Nom",
        "Prenom",
        "Badge",
        "Fonction",
        "Site",
        "Type EPI",
        "EPI",
        "Quantite",
        "Date remise",
        "Statut",
        "Observations",
    ]
    rows: list[list[Any]] = []
    styles: list[list[str | None]] = []
    for index, item in enumerate(assignments, start=1):
        rows.append(
            [
                index,
                item.get("matricule") or "",
                item.get("nom") or "",
                item.get("prenom") or "",
                item.get("numero_badge") or "",
                item.get("fonction") or "",
                item.get("site") or "",
                item.get("type_epi") or "",
                item.get("epi") or "",
                item.get("quantite") or 0,
                item.get("date_remise") or "",
                item.get("statut") or "",
                item.get("observations") or "",
            ]
        )
        styles.append([None] * 11 + ["done"] + [None])
    rows.extend(
        [
            [],
            ["LEGENDE", "Vert = dotation en service", "Jaune = controle ou renouvellement requis", "Rouge = EPI manquant, perdu ou endommage"],
            [],
            ["Prepared by", "", "", "", "Checked by", "", "", "", "Approved by", "", "", "", ""],
            ["Name / Date / Signature", "", "", "", "Name / Date / Signature", "", "", "", "Name / Date / Signature", "", "", "", ""],
        ]
    )
    styles.extend(
        [
            [],
            ["section", "done", "soon", "danger"],
            [],
            ["section"] * 13,
            [None] * 13,
        ]
    )
    write_styled_xlsx(
        output_path,
        "Employes dotes EPI",
        headers,
        rows,
        styles,
        include_company_description=True,
        document_title="OREZONE QHSE - Liste detaillee des employes dotes en EPI",
    )
    return output_path


def export_ppe_compliance_xlsx() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("conformite_employes_epi_orezone.xlsx")
    headers = [
        "N",
        "Employe",
        "Fonction",
        "Site",
        "EPI requis",
        "EPI recus",
        "EPI manquants",
        "Conformite",
        "Statut",
    ]
    rows: list[list[Any]] = []
    styles: list[list[str | None]] = []
    for index, item in enumerate(list_ppe_employee_compliance_summary(), start=1):
        status = str(item.get("statut") or "manquant")
        rows.append(
            [
                index,
                f"{item.get('nom') or ''} {item.get('prenom') or ''}".strip(),
                item.get("fonction") or "",
                item.get("site") or "",
                item.get("requis") or 0,
                item.get("recus") or 0,
                item.get("epi_manquants") or "-",
                f"{item.get('pourcentage') or 0}%",
                status,
            ]
        )
        styles.append([None] * 7 + ["done" if status == "conforme" else "danger"] * 2)
    _append_ppe_legend_and_signatures(rows, styles, len(headers))
    write_styled_xlsx(
        output_path,
        "Conformite EPI",
        headers,
        rows,
        styles,
        include_company_description=True,
        document_title="OREZONE QHSE - Conformite des employes aux EPI obligatoires",
    )
    return output_path


def export_ppe_inspections_xlsx() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("inspections_epi_orezone.xlsx")
    headers = [
        "N",
        "Date inspection",
        "Type EPI",
        "EPI",
        "Etat",
        "Inspecteur",
        "Prochaine inspection",
        "Observation",
    ]
    rows: list[list[Any]] = []
    styles: list[list[str | None]] = []
    for index, item in enumerate(list_ppe_inspections(limit=10000), start=1):
        status = str(item.get("statut") or "")
        style = "danger" if status in {"endommage", "hors_service"} else "soon" if status == "a_surveiller" else "done"
        rows.append(
            [
                index,
                item.get("date_inspection") or "",
                item.get("type_epi") or "",
                item.get("epi") or "",
                status,
                item.get("inspecteur") or "",
                item.get("prochaine_inspection") or "",
                item.get("observations") or "",
            ]
        )
        styles.append([None] * 4 + [style] + [None] * 3)
    _append_ppe_legend_and_signatures(rows, styles, len(headers))
    write_styled_xlsx(
        output_path,
        "Inspections EPI",
        headers,
        rows,
        styles,
        include_company_description=True,
        document_title="OREZONE QHSE - Registre professionnel des inspections EPI",
    )
    return output_path


def _append_ppe_legend_and_signatures(
    rows: list[list[Any]],
    styles: list[list[str | None]],
    column_count: int,
) -> None:
    rows.extend(
        [
            [],
            ["LEGENDE", "Vert = conforme / OK", "Jaune = attention / a surveiller", "Rouge = critique / non conforme"],
            [],
            ["Prepared by", "", "Checked by", "", "Approved by", "", "", ""],
            ["Name / Date / Signature", "", "Name / Date / Signature", "", "Name / Date / Signature", "", "", ""],
        ]
    )
    styles.extend(
        [
            [],
            ["section", "done", "soon", "danger"],
            [],
            ["section"] * column_count,
            [None] * column_count,
        ]
    )


def export_active_breaks_xlsx() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("liste_employes_en_break.xlsx")
    headers = ["Nom", "Prenom", "Badge", "Fonction", "Type", "Date debut", "Date fin", "Statut"]
    rows = [
        [
            row.get("nom") or "",
            row.get("prenom") or "",
            row.get("numero_badge") or "",
            row.get("fonction") or "",
            _state_label(row.get("type_break")),
            row.get("date_debut") or "",
            row.get("date_fin") or "",
            row.get("statut") or "",
        ]
        for row in list_active_break_employees()
    ]
    return _write_xlsx_safely(output_path, "Employes en break", headers, rows)


def export_session_attendance_xlsx(date_theme: str) -> Path:
    """Generate a single-session attendance sheet with signature rows."""
    from app.db.connection import db_session as _db_session
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with _db_session() as conn:
        topic_row = conn.execute(
            """
            SELECT ts.theme, ts.facilitateur, ts.date_theme, s.nom AS site
            FROM themes_securite ts
            LEFT JOIN sites s ON s.id_site = ts.site_id
            WHERE ts.date_theme = ?
            """,
            (date_theme,),
        ).fetchone()
        conf_row = conn.execute(
            "SELECT attendees_count, comments FROM mobile_toolbox_confirmations WHERE date_theme = ?",
            (date_theme,),
        ).fetchone()
    topic_dict = dict(topic_row) if topic_row else {}
    theme_raw = str(topic_dict.get("theme") or "—")
    topic_en = theme_raw.split(" / ")[0] if " / " in theme_raw else theme_raw
    theme_fr = theme_raw.split(" / ")[1] if " / " in theme_raw else theme_raw
    facilitator = str(topic_dict.get("facilitateur") or "—")
    site = str(topic_dict.get("site") or "—")
    attendees = int((conf_row or {}).get("attendees_count") or 0) if conf_row else 0
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    headers = ["N°", "Nom & Prénom", "Matricule", "Poste / Fonction", "Signature"]
    rows: list[list[Any]] = [
        ["", f"TOOLBOX TALK — FICHE DE PRESENCE", "", "", ""],
        ["Date :", date_theme, "Site :", site, ""],
        ["Topic EN :", topic_en, "", "", ""],
        ["Theme FR :", theme_fr, "", "", ""],
        ["Facilitateur :", facilitator, "Participants :", str(attendees) if attendees else "—", ""],
        ["", "", "", "", ""],
    ]
    for i in range(1, 31):
        rows.append([str(i), "", "", "", ""])
    rows.append(["", "", "", "", ""])
    rows.append(["Signature facilitateur :", "", "Date :", generated_at, ""])

    safe_date = date_theme.replace("-", "")
    output_path = _unique_export_path(f"toolbox_fiche_presence_{safe_date}.xlsx")
    return _write_xlsx_safely(output_path, "Fiche Presence", headers, rows)


def _unique_export_path(filename: str) -> Path:
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".xlsx"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return EXPORTS_DIR / f"{stem}_{timestamp}{suffix}"


def _unique_export_dir(dirname: str) -> Path:
    safe_dirname = "".join(char if char.isalnum() or char in "._-" else "_" for char in dirname)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return EXPORTS_DIR / f"{safe_dirname}_{timestamp}"


def _unique_export_path_in_dir(directory: Path, filename: str) -> Path:
    safe_filename = "".join(char if char.isalnum() or char in "._-" else "_" for char in filename)
    candidate = directory / safe_filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        next_candidate = directory / f"{stem}_{counter}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        counter += 1


def _safe_name(value: Any) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in str(value or "").strip())


def _last_twelve_calendar_months(reference: date | None = None) -> list[str]:
    current = (reference or date.today()).replace(day=1)
    months: list[str] = []
    for offset in range(12):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year:04d}-{month:02d}")
    return months


def _monthly_10h_cell_style(cell: dict[str, Any]) -> str | None:
    status = str(cell.get("status") or "")
    if status == "worked":
        return "done"
    if status == "rest":
        return "rest"
    if status == "holiday":
        return "holiday"
    if status == "normal_break":
        return "missing"
    if status == "permission":
        return "permission"
    if status == "sick":
        return "sick"
    if status == "annual_break":
        return "annual"
    if status == "absent":
        return "danger"
    if status == "unfilled":
        return "unfilled"
    return None


def _write_xlsx_safely(path: Path, sheet_name: str, headers: list[str], rows: list[list[Any]]) -> Path:
    try:
        write_styled_xlsx(
            path,
            sheet_name,
            headers,
            rows,
            include_company_description=True,
            document_title=sheet_name,
        )
        return path
    except PermissionError:
        fallback = _unique_export_path(f"{path.stem}_nouveau{path.suffix}")
        write_styled_xlsx(
            fallback,
            sheet_name,
            headers,
            rows,
            include_company_description=True,
            document_title=sheet_name,
        )
        return fallback


def _write_styled_xlsx_safely(
    path: Path,
    sheet_name: str,
    headers: list[str],
    rows: list[list[Any]],
    styles: list[list[str | None]],
    document_title: str | None = None,
) -> Path:
    title = document_title or sheet_name
    try:
        write_styled_xlsx(
            path,
            sheet_name,
            headers,
            rows,
            styles,
            include_company_description=True,
            document_title=title,
        )
        return path
    except PermissionError:
        fallback = _unique_export_path(f"{path.stem}_nouveau{path.suffix}")
        write_styled_xlsx(
            fallback,
            sheet_name,
            headers,
            rows,
            styles,
            include_company_description=True,
            document_title=title,
        )
        return fallback


def _write_attendance_list_xls(
    path: Path,
    date_presence: str,
    records: list[dict[str, Any]],
    summary: dict[str, int | float],
) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    headers = [
        "N",
        "Nom",
        "Prenom",
        "Badge",
        "Fonction",
        "Department",
        "Supervisor",
        "Phone",
        "Company",
        "Camp/Zone",
        "Shift",
        "Statut",
        "Entree",
        "Sortie",
        "Heures",
        "Controle",
        "Reason of absence",
        "Remarks / HSE observation",
    ]
    header_html = "".join(f"<th>{_xml_escape(header)}</th>" for header in headers)
    body_rows = []
    for index, record in enumerate(records, start=1):
        status = str(record.get("statut") or "")
        control = str(record.get("controle") or "")
        remark = record.get("remarks") or _attendance_remark(record)
        values: list[tuple[Any, str]] = [
            (index, "number"),
            (record.get("nom") or "", ""),
            (record.get("prenom") or "", ""),
            (record.get("numero_badge") or "", "" if record.get("numero_badge") else "issue"),
            (record.get("fonction") or "", ""),
            (record.get("department") or "", ""),
            (record.get("supervisor") or "", ""),
            (record.get("phone") or "", ""),
            (record.get("company") or "", ""),
            (record.get("camp_zone") or "", ""),
            (record.get("shift") or "", _html_shift_class(record.get("shift"))),
            (status, "present" if status.lower() == "present" else "absent"),
            (record.get("heure_entree") or "", ""),
            (record.get("heure_sortie") or "", ""),
            (record.get("heures") or 0, "number"),
            (control, "ok" if control.lower() == "ok" else "issue"),
            (record.get("absence_reason") or "", "issue" if status.lower() == "absent" else ""),
            (remark, "issue" if remark else ""),
        ]
        body_rows.append(
            "<tr>"
            + "".join(
                f'<td class="{css_class}">{_xml_escape(value)}</td>'
                for value, css_class in values
            )
            + "</tr>"
        )

    summary_rows = _attendance_summary_rows(summary, records)
    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Calibri, Arial, sans-serif; color: #172033; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #cbd5e1; padding: 6px 8px; font-size: 11pt; }}
th {{ background: #1e3a8a; color: #fff; font-weight: bold; text-align: center; }}
.title {{ background: #1e3a8a; color: #fff; font-size: 22pt; font-weight: bold; text-align: center; }}
.logo {{ background: #1e3a8a; color: #fff; font-size: 20pt; font-weight: bold; text-align: center; }}
.subtitle {{ font-weight: bold; background: #eff6ff; }}
.muted {{ color: #64748b; font-style: italic; background: #f8fafc; }}
.metric {{ background: #dbeafe; font-weight: bold; text-align: center; }}
.metric-ok {{ background: #dcfce7; font-weight: bold; text-align: center; }}
.metric-danger {{ background: #fee2e2; color: #dc2626; font-weight: bold; text-align: center; }}
.metric-warn {{ background: #fef3c7; font-weight: bold; text-align: center; }}
.number {{ text-align: center; }}
.present, .day, .ok {{ background: #dcfce7; font-weight: bold; }}
.absent {{ background: #fee2e2; color: #dc2626; font-weight: bold; }}
.night {{ background: #dbeafe; font-weight: bold; }}
.issue {{ background: #fef3c7; font-weight: bold; }}
.signature {{ background: #eff6ff; font-weight: bold; text-align: center; height: 24px; }}
.signature-box {{ height: 58px; }}
.summary-title {{ background: #1e3a8a; color: #fff; font-size: 16pt; font-weight: bold; }}
tr:nth-child(even) .data {{ background: #f8fafc; }}
</style>
</head>
<body>
<table>
<tr><td class="logo" colspan="2" rowspan="3">OREZONE</td><td class="title" colspan="16">LISTE DE PRESENCE OREZONE</td></tr>
<tr><td class="subtitle" colspan="16">Date de presence: {_xml_escape(date_presence)} | Site: OREZONE | Document QHSE controle</td></tr>
<tr><td class="muted" colspan="16">Genere le: {_xml_escape(generated_at)} | Confidential - operational use only</td></tr>
<tr><td colspan="18"></td></tr>
<tr>
<td class="metric">Total: {summary.get("total", 0)}</td>
<td class="metric-ok">Presents: {summary.get("present", 0)}</td>
<td class="metric-danger">Absents: {summary.get("absent", 0)}</td>
<td class="metric">Heures: {summary.get("hours", 0)}</td>
<td class="metric-warn">A verifier: {summary.get("issues", 0)}</td>
<td class="metric">Day: {summary.get("day", 0)}</td>
<td class="metric">Night: {summary.get("night", 0)}</td>
<td class="metric-warn">Badge manquant: {summary.get("missing_badge", 0)}</td>
<td colspan="10"></td>
</tr>
<tr><td colspan="18"></td></tr>
<tr>{header_html}</tr>
{''.join(body_rows)}
<tr><td colspan="18"></td></tr>
<tr><td class="signature" colspan="4">Prepared by</td><td class="signature" colspan="4">Checked by</td><td class="signature" colspan="4">Approved by</td><td class="signature" colspan="6">QHSE Comments</td></tr>
<tr><td class="signature-box" colspan="4"></td><td class="signature-box" colspan="4"></td><td class="signature-box" colspan="4"></td><td class="signature-box" colspan="6"></td></tr>
</table>
<br>
<table>
{summary_rows}
</table>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def _write_employee_list_xls(
    path: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, int],
) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    headers = [
        "N",
        "Matricule",
        "Nom",
        "Prenom",
        "Badge",
        "Fonction",
        "Site",
        "Shift",
        "Situation",
        "Prochain break",
        "Observation",
    ]
    header_html = "".join(f"<th>{_xml_escape(header)}</th>" for header in headers)
    body_rows = []
    for index, row in enumerate(rows, start=1):
        values: list[tuple[Any, str]] = [
            (index, "number"),
            (row.get("matricule") or "", ""),
            (row.get("nom") or "", ""),
            (row.get("prenom") or "", ""),
            (row.get("numero_badge") or "", "" if row.get("numero_badge") else "issue"),
            (row.get("fonction") or "", ""),
            (row.get("site") or "", ""),
            (row.get("shift") or "", _html_shift_class(row.get("shift"))),
            (row.get("situation") or "", _employee_state_class(row.get("situation"))),
            (row.get("prochain_break") or "", "issue" if _break_text_is_due(row.get("prochain_break")) else ""),
            (row.get("observation") or "", "issue" if row.get("observation") else ""),
        ]
        body_rows.append(
            "<tr>"
            + "".join(
                f'<td class="{css_class}">{_xml_escape(value)}</td>'
                for value, css_class in values
            )
            + "</tr>"
        )

    summary_rows = _employee_summary_rows(summary, rows)
    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Calibri, Arial, sans-serif; color: #172033; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #cbd5e1; padding: 6px 8px; font-size: 11pt; }}
th {{ background: #1e3a8a; color: #fff; font-weight: bold; text-align: center; }}
.title {{ background: #1e3a8a; color: #fff; font-size: 22pt; font-weight: bold; text-align: center; }}
.logo {{ background: #1e3a8a; color: #fff; font-size: 20pt; font-weight: bold; text-align: center; }}
.subtitle {{ font-weight: bold; background: #eff6ff; }}
.muted {{ color: #64748b; font-style: italic; background: #f8fafc; }}
.metric {{ background: #dbeafe; font-weight: bold; text-align: center; }}
.metric-ok, .work, .day {{ background: #dcfce7; font-weight: bold; }}
.metric-danger, .sick {{ background: #fee2e2; color: #dc2626; font-weight: bold; }}
.metric-warn, .break, .issue {{ background: #fef3c7; font-weight: bold; }}
.permission {{ background: #e0e7ff; font-weight: bold; }}
.night {{ background: #dbeafe; font-weight: bold; }}
.number {{ text-align: center; }}
.summary-title {{ background: #1e3a8a; color: #fff; font-size: 16pt; font-weight: bold; }}
</style>
</head>
<body>
<table>
<tr><td class="logo" colspan="2" rowspan="3">OREZONE</td><td class="title" colspan="9">LIST OF OREZONE EMPLOYEE</td></tr>
<tr><td class="subtitle" colspan="9">OREZONE QHSE employee list, shift allocation, operational status and break follow-up.</td></tr>
<tr><td class="muted" colspan="9">Generated: {_xml_escape(generated_at)} | Controlled QHSE document | Use colors to identify employee status.</td></tr>
<tr><td colspan="11"></td></tr>
<tr>
<td class="metric">Total: {summary.get("total", 0)}</td>
<td class="metric-ok">Day: {summary.get("day", 0)}</td>
<td class="metric">Night: {summary.get("night", 0)}</td>
<td class="metric-warn">Break/Absence: {summary.get("off", 0)}</td>
<td class="metric-danger">Break due: {summary.get("due", 0)}</td>
<td colspan="6"></td>
</tr>
<tr><td colspan="11"></td></tr>
<tr>{header_html}</tr>
{''.join(body_rows)}
</table>
<br>
<table>
{summary_rows}
</table>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def _write_training_matrix_xls(
    path: Path,
    training_types: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    headers = ["N", "Employee", "Badge", "Function", *[str(item.get("nom") or "") for item in training_types]]
    header_html = "".join(f"<th>{_xml_escape(header)}</th>" for header in headers)
    total_cells = len(rows) * len(training_types)
    done = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "done")
    soon = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "soon")
    expired = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "expired")
    missing = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "missing")
    completion = round((done / total_cells) * 100) if total_cells else 0
    body_rows = []
    for index, row in enumerate(rows, start=1):
        employee = row["employee"]
        base_cells = [
            (index, "number"),
            (f"{employee.get('nom') or '-'} {employee.get('prenom') or ''}".strip(), ""),
            (employee.get("numero_badge") or "", "issue" if not employee.get("numero_badge") else ""),
            (employee.get("fonction") or "", ""),
        ]
        matrix_cells = [
            (_training_cell_text(cell), _training_cell_class(cell))
            for cell in row.get("cells", [])
        ]
        body_rows.append(
            "<tr>"
            + "".join(f'<td class="{css_class}">{_xml_escape(value)}</td>' for value, css_class in [*base_cells, *matrix_cells])
            + "</tr>"
        )

    summary_rows = _training_matrix_summary_rows(training_types, rows)
    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Calibri, Arial, sans-serif; color: #172033; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #cbd5e1; padding: 6px 8px; font-size: 11pt; }}
th {{ background: #1e3a8a; color: #fff; font-weight: bold; text-align: center; }}
.title {{ background: #1e3a8a; color: #fff; font-size: 22pt; font-weight: bold; text-align: center; }}
.logo {{ background: #1e3a8a; color: #fff; font-size: 20pt; font-weight: bold; text-align: center; }}
.subtitle {{ font-weight: bold; background: #eff6ff; }}
.muted {{ color: #64748b; font-style: italic; background: #f8fafc; }}
.metric {{ background: #dbeafe; font-weight: bold; text-align: center; }}
.done {{ background: #dcfce7; font-weight: bold; text-align: center; }}
.soon {{ background: #fef3c7; font-weight: bold; text-align: center; }}
.missing, .expired, .issue {{ background: #fee2e2; color: #dc2626; font-weight: bold; text-align: center; }}
.number {{ text-align: center; }}
.legend {{ background: #eff6ff; font-weight: bold; }}
.summary-title {{ background: #1e3a8a; color: #fff; font-size: 16pt; font-weight: bold; }}
</style>
</head>
<body>
<table>
<tr><td class="logo" colspan="2" rowspan="3">OREZONE</td><td class="title" colspan="{max(len(headers) - 2, 1)}">OREZONE TRAINING MATRIX</td></tr>
<tr><td class="subtitle" colspan="{max(len(headers) - 2, 1)}">OREZONE QHSE training compliance matrix for employees, mandatory competencies, renewal tracking and operational readiness.</td></tr>
<tr><td class="muted" colspan="{max(len(headers) - 2, 1)}">Generated: {_xml_escape(generated_at)} | Controlled QHSE document | Use colors to identify training status and priority actions.</td></tr>
<tr><td colspan="{len(headers)}"></td></tr>
<tr>
<td class="metric">Employees: {len(rows)}</td>
<td class="metric">Training types: {len(training_types)}</td>
<td class="done">Valid: {done}</td>
<td class="soon">Soon: {soon}</td>
<td class="missing">Expired: {expired}</td>
<td class="missing">Missing: {missing}</td>
<td class="metric">Compliance: {completion}%</td>
<td colspan="{max(len(headers) - 7, 1)}"></td>
</tr>
<tr><td colspan="{len(headers)}"></td></tr>
<tr>
<td class="done">Valid / Completed</td>
<td class="soon">Expiring soon</td>
<td class="missing">Missing / Expired</td>
<td class="legend" colspan="{max(len(headers) - 3, 1)}">Legend: green = compliant, yellow = renewal required soon, red = not compliant or expired. Each filled cell shows the expiry date.</td>
</tr>
<tr><td colspan="{len(headers)}"></td></tr>
<tr>{header_html}</tr>
{''.join(body_rows)}
</table>
<br>
<table>
{summary_rows}
</table>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def _write_timesheet_xlsx(path: Path, timesheet: dict[str, Any]) -> None:
    write_timesheet_21_20_report_xlsx(
        path,
        timesheet,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def _write_timesheet_xls(path: Path, timesheet: dict[str, Any]) -> None:
    if timesheet.get("print_individual") and len(timesheet.get("rows") or []) == 1:
        _write_individual_timesheet_print_xls(path, timesheet)
        return
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    days = timesheet["days"]
    period = timesheet["period"]
    summary = timesheet["summary"]
    headers = [
        "MLE",
        "NOM",
        "PRENOMS",
        "FONCTION",
        *[f"{day['day']:02d}" for day in days],
        "TOTAL",
        "12H",
        "8H",
        "R",
        "A",
        "B",
        "P",
        "S",
        "H",
    ]
    header_html = "".join(f"<th>{_xml_escape(header)}</th>" for header in headers)
    weekday_html = "".join(
        f'<td class="weekday {"sunday" if str(day["weekday"]).lower().startswith("dim") else ""}">{_xml_escape(day["weekday"])}</td>'
        for day in days
    )
    rows_html = []
    for index, row in enumerate(timesheet["rows"], start=1):
        employee = row["employee"]
        employee_style = _timesheet_employee_band_style(index)
        cells = [
            f'<td class="employee-id" bgcolor="{employee_style["bgcolor"]}" style="{employee_style["style"]}">{_xml_escape(_timesheet_employee_code(employee))}</td>',
            f'<td class="employee-name" bgcolor="{employee_style["bgcolor"]}" style="{employee_style["style"]}">{_xml_escape(employee.get("nom") or employee.get("nom_complet") or "-")}</td>',
            f'<td class="employee-name" bgcolor="{employee_style["bgcolor"]}" style="{employee_style["style"]}">{_xml_escape(employee.get("prenom") or "")}</td>',
            f'<td class="function" bgcolor="{employee_style["bgcolor"]}" style="{employee_style["style"]}">{_xml_escape(employee.get("fonction") or "-")}</td>',
        ]
        for cell in row["cells"]:
            inline_style = _timesheet_cell_inline_style(cell)
            cells.append(
                f'<td class="day-cell {_timesheet_cell_class(cell)} {_timesheet_week_class(cell)}" '
                f'bgcolor="{inline_style["bgcolor"]}" style="{inline_style["style"]}">'
                f'{_xml_escape(_timesheet_compact_cell_label(cell))}</td>'
            )
        cells.extend(
            [
                f'<td class="total ok">{row["worked_days"]}</td>',
                f'<td class="total worked-drilling">{row.get("drilling_hours", 0)}</td>',
                f'<td class="total worked-standard">{row.get("standard_hours", 0)}</td>',
                f'<td class="total rest">{row["rest_days"]}</td>',
                f'<td class="total absent">{row.get("absent_days", 0)}</td>',
                f'<td class="total break">{row["break_days"]}</td>',
                f'<td class="total permission">{row.get("permission_days", 0)}</td>',
                f'<td class="total sick">{row.get("sick_days", 0)}</td>',
                f'<td class="total hours">{row["hours"]}</td>',
            ]
        )
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    col_count = len(headers)
    day_count = len(days)
    title = "OREZONE MONTHLY TIMESHEET"
    if timesheet.get("site"):
        title += f" - {timesheet['site'].get('nom') or ''}"
    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{ mso-page-orientation: landscape; margin: 0.25in; }}
body {{ font-family: Calibri, Arial, sans-serif; color: #111827; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #94a3b8; padding: 2px 3px; font-size: 8pt; mso-number-format:"\\@"; }}
th {{ background: #e5e7eb; color: #111827; font-weight: bold; text-align: center; }}
.title {{ background: #111827; color: #fff; font-size: 14pt; font-weight: bold; text-align: center; }}
.subtitle {{ background: #e5e7eb; color: #111827; font-weight: bold; }}
.metric {{ background: #dbeafe; font-weight: bold; text-align: center; }}
.metric-ok {{ background: #dcfce7; font-weight: bold; text-align: center; }}
.metric-warn {{ background: #fef3c7; font-weight: bold; text-align: center; }}
.employee-id {{ width: 62px; font-weight: bold; text-align: center; }}
.employee-name {{ width: 145px; font-weight: bold; white-space: normal; mso-wrap-style: square; }}
.function {{ width: 180px; font-weight: bold; white-space: normal; mso-wrap-style: square; }}
.weekday {{ background: #f8fafc; color: #475569; text-align: center; font-size: 7pt; }}
.sunday {{ background: #d1d5db; color: #111827; font-weight: bold; }}
.day-cell {{ text-align: center; vertical-align: middle; font-weight: bold; width: 32px; min-width: 32px; max-width: 32px; }}
.week-start {{ border-left: 2px solid #111827; }}
.worked-drilling {{ background: #00a6d6; color: #111827; }}
.worked-standard {{ background: #ffffff; color: #111827; }}
.holiday {{ background: #22c55e; color: #ffffff; }}
.rest {{ background: #c0392b; color: #ffffff; }}
.absent {{ background: #ef4444; color: #ffffff; }}
.unfilled {{ background: #e5e7eb; color: #111827; }}
.break {{ background: #facc15; color: #111827; }}
.annual {{ background: #5b3db6; color: #ffffff; }}
.permission {{ background: #f4a261; color: #ffffff; }}
.sick {{ background: #10b981; color: #ffffff; }}
.total {{ text-align: center; font-weight: bold; }}
.ok {{ background: #dcfce7; }}
.hours {{ background: #dbeafe; color: #1e3a8a; }}
.legend-title {{ background: #111827; color: #fff; font-weight: bold; }}
.legend-cell {{ text-align: center; font-weight: bold; color: #fff; }}
.signature {{ background: #eff6ff; font-weight: bold; text-align: center; height: 24px; }}
.signature-box {{ height: 58px; }}
.note {{ color: #475569; font-style: italic; }}
</style>
</head>
<body>
<table>
<tr><td colspan="{col_count}" class="title">{_xml_escape(title)}</td></tr>
<tr><td colspan="{col_count}" class="subtitle">{_xml_escape(period["label"])} | Periode: {_xml_escape(period["start"])} au {_xml_escape(period["end"])} | Genere: {_xml_escape(generated_at)}</td></tr>
<tr><td colspan="{col_count}"></td></tr>
<tr>
<td class="metric">Employes: {summary.get("employees", 0)}</td>
<td class="metric-ok">Jours travailles: {summary.get("worked_days", 0)}</td>
<td class="metric-warn">Repos: {summary.get("rest_days", 0)}</td>
<td class="metric-warn">Break: {summary.get("break_days", 0)}</td>
<td class="metric">Heures: {summary.get("hours", 0)}</td>
<td class="metric">Heures 12H: {summary.get("drilling_hours", 0)}</td>
<td class="metric">Heures 8H: {summary.get("standard_hours", 0)}</td>
<td class="metric">Jours drilling: {summary.get("drilling_days", 0)}</td>
<td class="metric-warn">Absents: {summary.get("absent_days", 0)}</td>
<td class="metric-warn">Non renseignes: {summary.get("unfilled_days", 0)}</td>
<td colspan="{max(col_count - 10, 1)}"></td>
</tr>
<tr><td colspan="{col_count}"></td></tr>
<tr>{header_html}</tr>
<tr><td colspan="4" class="weekday">JOURS</td>{weekday_html}<td colspan="9" class="weekday">TOTAUX</td></tr>
{''.join(rows_html)}
<tr><td colspan="{col_count}"></td></tr>
<tr><td colspan="4" class="legend-title">Legende</td><td colspan="{max(col_count - 4, 1)}"></td></tr>
<tr><td colspan="4" class="legend-title">SUNDAY</td><td colspan="{day_count}" class="note">Les dimanches sont grises dans la ligne JOURS.</td><td colspan="9"></td></tr>
<tr>
<td class="legend-cell rest" bgcolor="#c0392b" style="background-color:#c0392b;color:#ffffff;">R = OFF DAYS</td>
<td colspan="3" class="legend-cell sick" bgcolor="#10b981" style="background-color:#10b981;color:#ffffff;">SICK LEAVE</td>
<td colspan="3" class="legend-cell permission" bgcolor="#f4a261" style="background-color:#f4a261;color:#ffffff;">PERMISSION</td>
<td colspan="3" class="legend-cell worked-drilling" bgcolor="#00a6d6" style="background-color:#00a6d6;color:#111827;">12 = JOURS DRILLING</td>
<td colspan="3" class="legend-cell holiday" bgcolor="#22c55e" style="background-color:#22c55e;color:#ffffff;">8 = JOURS FERIES &amp; CHOMES PAYES</td>
<td colspan="3" class="legend-cell break" bgcolor="#facc15" style="background-color:#facc15;color:#111827;">B = BREAK</td>
<td colspan="4" class="legend-cell" bgcolor="#5b3db6" style="background-color:#5b3db6;color:#ffffff;">ANNUAL LEAVE</td>
<td colspan="{max(col_count - 21, 1)}"></td>
</tr>
<tr><td class="legend-title">S1/S2</td><td colspan="5">Chaque semaine TimeSheet est un bloc de 7 jours depuis le 21</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="worked-drilling" bgcolor="#00a6d6" style="background-color:#00a6d6;color:#111827;">12</td><td colspan="5">Present avec activite drilling = 12H</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="worked-standard" bgcolor="#ffffff" style="background-color:#ffffff;color:#111827;">8</td><td colspan="5">Present sans activite drilling = 8H</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="holiday" bgcolor="#22c55e" style="background-color:#22c55e;color:#ffffff;">8</td><td colspan="5">Jour ferie ou chome paye = 8H</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td colspan="{col_count}"></td></tr>
<tr><td colspan="6" class="legend-title">Regles de calcul</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td colspan="6" class="note">Une presence sur jour drilling compte 12H. Une presence sur jour sans drilling compte 8H. Un jour ferie ou chome paye compte 8H. Les dimanches sont marques R. Break, permission, sick et annual leave comptent 8H. Repos, absent et non renseigne comptent 0H. Les heures reelles viennent de la liste de presence.</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td colspan="{col_count}"></td></tr>
<tr>
<td colspan="4" class="signature">Prepared by</td>
<td colspan="4" class="signature">Checked by</td>
<td colspan="4" class="signature">Approved by</td>
<td colspan="{max(col_count - 12, 1)}"></td>
</tr>
<tr>
<td colspan="4" class="signature-box"></td>
<td colspan="4" class="signature-box"></td>
<td colspan="4" class="signature-box"></td>
<td colspan="{max(col_count - 12, 1)}"></td>
</tr>
<tr>
<td colspan="4">Name / Date / Signature</td>
<td colspan="4">Name / Date / Signature</td>
<td colspan="4">Name / Date / Signature</td>
<td colspan="{max(col_count - 12, 1)}"></td>
</tr>
</table>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def _write_individual_timesheet_print_xls(path: Path, timesheet: dict[str, Any]) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    period = timesheet["period"]
    row = timesheet["rows"][0]
    employee = row["employee"]
    cells = list(row.get("cells") or [])
    left_cells = cells[:15]
    right_cells = cells[15:]
    max_rows = max(len(left_cells), len(right_cells))
    day_rows = []
    for index in range(max_rows):
        left = left_cells[index] if index < len(left_cells) else None
        right = right_cells[index] if index < len(right_cells) else None
        day_rows.append(
            "<tr>"
            + _individual_day_cells(left)
            + _individual_day_cells(right)
            + "</tr>"
        )
    weekly_rows = "".join(
        f"<tr><td>{_xml_escape(week)}</td><td class=\"total\">{_xml_escape(row.get('weekly_hours', {}).get(week, 0))}</td></tr>"
        for week in timesheet.get("week_labels", [])
    )
    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4 portrait; margin: 0.35in; mso-page-orientation: portrait; }}
body {{ font-family: Calibri, Arial, sans-serif; color: #172033; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #cbd5e1; padding: 3px 5px; font-size: 8.5pt; mso-number-format:"\\@"; }}
th {{ background: #1e3a8a; color: #fff; font-weight: bold; text-align: center; }}
.title {{ background: #1e3a8a; color: #fff; font-size: 18pt; font-weight: bold; text-align: center; }}
.subtitle {{ background: #eff6ff; font-weight: bold; }}
.section {{ background: #dbeafe; color: #1e3a8a; font-weight: bold; }}
.label {{ background: #f8fafc; color: #475569; font-weight: bold; }}
.value {{ font-weight: bold; }}
.total {{ text-align: center; font-weight: bold; background: #eff6ff; }}
.worked-drilling {{ background: #2563eb; color: #fff; text-align: center; font-weight: bold; }}
.worked-standard {{ background: #16a34a; color: #fff; text-align: center; font-weight: bold; }}
.rest {{ background: #cbd5e1; color: #172033; text-align: center; font-weight: bold; }}
.absent {{ background: #fca5a5; color: #172033; text-align: center; font-weight: bold; }}
.unfilled {{ background: #e5e7eb; color: #172033; text-align: center; font-weight: bold; }}
.break {{ background: #f59e0b; color: #172033; text-align: center; font-weight: bold; }}
.permission {{ background: #a855f7; color: #fff; text-align: center; font-weight: bold; }}
.sick {{ background: #dc2626; color: #fff; text-align: center; font-weight: bold; }}
.signature {{ height: 44px; }}
.note {{ color: #475569; font-style: italic; }}
</style>
</head>
<body>
<table>
<tr><td colspan="10" class="title">OREZONE INDIVIDUAL TIMESHEET</td></tr>
<tr><td colspan="10" class="subtitle">{_xml_escape(period["label"])} | Periode: {_xml_escape(period["start"])} au {_xml_escape(period["end"])} | Genere: {_xml_escape(generated_at)}</td></tr>
<tr>
<td class="label">Employe</td><td colspan="3" class="value">{_xml_escape(_timesheet_employee_name(employee))}</td>
<td class="label">Badge</td><td class="value">{_xml_escape(employee.get("numero_badge") or "-")}</td>
<td class="label">Fonction</td><td colspan="3" class="value">{_xml_escape(employee.get("fonction") or "-")}</td>
</tr>
<tr>
<td class="label">Site</td><td class="value">{_xml_escape(employee.get("site") or "-")}</td>
<td class="label">Groupe</td><td class="value">{_xml_escape(employee.get("groupe") or "-")}</td>
<td class="label">Shift</td><td class="value">{_xml_escape(employee.get("shift") or employee.get("shift_code") or "-")}</td>
<td class="label">Heures</td><td class="value">{_xml_escape(row.get("hours", 0))}</td>
<td class="label">Heures reelles</td><td class="value">{_xml_escape(row.get("actual_hours", 0))}</td>
</tr>
<tr><td colspan="10"></td></tr>
<tr>
<td class="section">Jours travailles</td><td class="total">{_xml_escape(row.get("worked_days", 0))}</td>
<td class="section">Heures 12H</td><td class="total">{_xml_escape(row.get("drilling_hours", 0))}</td>
<td class="section">Heures 8H</td><td class="total">{_xml_escape(row.get("standard_hours", 0))}</td>
<td class="section">Repos</td><td class="total">{_xml_escape(row.get("rest_days", 0))}</td>
<td class="section">Absents</td><td class="total">{_xml_escape(row.get("absent_days", 0))}</td>
</tr>
<tr>
<td class="section">Non renseignes</td><td class="total">{_xml_escape(row.get("unfilled_days", 0))}</td>
<td class="section">Break</td><td class="total">{_xml_escape(row.get("break_days", 0))}</td>
<td class="section">Permission</td><td class="total">{_xml_escape(row.get("permission_days", 0))}</td>
<td class="section">Sick</td><td class="total">{_xml_escape(row.get("sick_days", 0))}</td>
<td class="section">Mois</td><td class="total">{_xml_escape(period.get("month") or "")}</td>
</tr>
</table>
<br>
<table>
<tr><th>Date</th><th>Jour</th><th>Statut</th><th>Heures</th><th>Activite</th><th>Date</th><th>Jour</th><th>Statut</th><th>Heures</th><th>Activite</th></tr>
{''.join(day_rows)}
</table>
<br>
<table>
<tr><td colspan="2" class="section">Totaux par semaine</td><td colspan="8" class="section">Regles</td></tr>
{weekly_rows}
<tr><td colspan="2"></td><td colspan="8" class="note">Drilling = 12H. Sans drilling = 8H. Break, permission et sick = 8H quelle que soit l'activite. Repos, absent et non renseigne = 0H.</td></tr>
</table>
<br>
<table>
<tr><td class="section" colspan="3">Prepared by</td><td class="section" colspan="3">Checked by</td><td class="section" colspan="4">Approved by</td></tr>
<tr><td class="signature" colspan="3"></td><td class="signature" colspan="3"></td><td class="signature" colspan="4"></td></tr>
<tr><td colspan="3">Name / Date / Signature</td><td colspan="3">Name / Date / Signature</td><td colspan="4">Name / Date / Signature</td></tr>
</table>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def _individual_day_cells(cell: dict[str, Any] | None) -> str:
    if cell is None:
        return "<td></td><td></td><td></td><td></td><td></td>"
    status_class = _timesheet_cell_class(cell)
    activity = "Drilling" if cell.get("has_drilling") else "8H"
    return (
        f"<td>{_xml_escape(cell.get('date') or '')}</td>"
        f"<td>{_xml_escape(_weekday_from_iso(str(cell.get('date') or '')))}</td>"
        f'<td class="{status_class}" bgcolor="{_timesheet_cell_inline_style(cell)["bgcolor"]}" '
        f'style="{_timesheet_cell_inline_style(cell)["style"]}">{_xml_escape(_timesheet_status_text(cell))}</td>'
        f"<td class=\"total\">{_xml_escape(cell.get('hours', 0))}</td>"
        f"<td>{_xml_escape(activity)}</td>"
    )


def _weekday_from_iso(value: str) -> str:
    if not value:
        return ""
    labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    return labels[datetime.strptime(value, "%Y-%m-%d").weekday()]


def _timesheet_status_text(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status == "worked_drilling":
        return "12H"
    if status == "worked_standard":
        return "8H"
    if status == "rest":
        return "Repos"
    if status == "absent":
        return "Absent"
    if status == "unfilled":
        return "Non renseigne"
    if status == "break" and label == "P":
        return "Permission"
    if status == "break" and label == "S":
        return "Sick"
    if status == "break":
        return "Break"
    return label or status


def _write_ppe_inventory_xls(path: Path, data: dict[str, Any]) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary = data["summary"]

    def html_table(title: str, headers: list[str], rows: list[list[Any]]) -> str:
        header_html = "".join(f"<th>{_xml_escape(header)}</th>" for header in headers)
        row_html = "".join(
            "<tr>" + "".join(f"<td>{_xml_escape(value)}</td>" for value in row) + "</tr>"
            for row in rows
        )
        return f"""
        <h2>{_xml_escape(title)}</h2>
        <table>
            <tr>{header_html}</tr>
            {row_html}
        </table>
        """

    dashboard_rows = [
        ["Active PPE items", summary["items"]],
        ["Available stock", summary["stock_total"]],
        ["Assigned PPE", summary["assigned"]],
        ["Low stock alerts", summary["low_stock"]],
    ]
    catalogue_rows = [
        [
            item.get("type_epi") or "",
            item.get("nom") or "",
            item.get("taille") or "",
            item.get("norme") or "",
            item.get("etat") or "",
            item.get("quantite_disponible") or 0,
            item.get("seuil_minimum") or 0,
            "LOW STOCK" if item.get("stock_bas") else "OK",
        ]
        for item in data["items"]
    ]
    assignment_rows = [
        [
            item.get("nom") or "",
            item.get("prenom") or "",
            item.get("type_epi") or "",
            item.get("epi") or "",
            item.get("quantite") or 0,
            item.get("date_remise") or "",
            item.get("date_retour") or "",
            item.get("statut") or "",
        ]
        for item in data["assignments"]
    ]
    requirement_rows = [
        [
            item.get("fonction") or "",
            item.get("type_epi") or "",
            item.get("quantite") or 0,
            "Yes" if item.get("obligatoire") else "No",
        ]
        for item in data["requirements"]
    ]
    compliance_rows = [
        [
            item.get("nom") or "",
            item.get("prenom") or "",
            item.get("fonction") or "",
            item.get("type_epi") or "",
            item.get("requis") or 0,
            item.get("affecte") or 0,
            item.get("statut") or "",
        ]
        for item in data["compliance"]
    ]
    inspection_rows = [
        [
            item.get("date_inspection") or "",
            item.get("type_epi") or "",
            item.get("epi") or "",
            item.get("statut") or "",
            item.get("prochaine_inspection") or "",
            item.get("inspecteur") or "",
            item.get("observations") or "",
        ]
        for item in data["inspections"]
    ]
    alert_rows = [
        [
            item.get("alerte") or "",
            item.get("type_epi") or "",
            item.get("nom") or "",
            item.get("quantite_disponible") or "",
            item.get("seuil_minimum") or "",
            item.get("date_expiration") or "",
            item.get("etat") or "",
        ]
        for item in data["alerts"]
    ]
    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Calibri, Arial, sans-serif; color: #1e293b; }}
h1 {{ color: #0f172a; margin-bottom: 4px; }}
h2 {{ margin-top: 26px; color: #1d4ed8; }}
.meta {{ color: #64748b; margin-bottom: 18px; }}
table {{ border-collapse: collapse; margin-bottom: 16px; width: 100%; }}
th {{ background: #2563eb; color: #ffffff; border: 1px solid #bfdbfe; padding: 6px; text-align: left; }}
td {{ border: 1px solid #cbd5e1; padding: 5px; }}
tr:nth-child(even) td {{ background: #f8fafc; }}
</style>
</head>
<body>
<h1>OREZONE QHSE - Gestion des EPI</h1>
<div class="meta">Generated: {_xml_escape(generated_at)}</div>
{html_table("Dashboard", ["Indicator", "Value"], dashboard_rows)}
{html_table("Catalogue", ["Type", "PPE", "Size", "Standard", "Condition", "Stock", "Threshold", "Status"], catalogue_rows)}
{html_table("Assignments", ["Name", "First name", "Type", "PPE", "Quantity", "Issue date", "Return date", "Status"], assignment_rows)}
{html_table("Requirements", ["Function", "Required PPE type", "Quantity", "Mandatory"], requirement_rows)}
{html_table("Compliance", ["Name", "First name", "Function", "PPE type", "Required", "Assigned", "Status"], compliance_rows)}
{html_table("Inspections", ["Date", "Type", "PPE", "Status", "Next inspection", "Inspector", "Observations"], inspection_rows)}
{html_table("Alerts", ["Alert", "Type", "PPE", "Stock", "Threshold", "Expiration", "Condition"], alert_rows)}
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def _write_ppe_inventory_xlsx(path: Path, data: dict[str, Any]) -> None:
    summary = data["summary"]
    headers = ["Section", "Col 1", "Col 2", "Col 3", "Col 4", "Col 5", "Col 6", "Col 7", "Col 8"]
    rows: list[list[Any]] = [
        ["Dashboard", "Active PPE items", summary["items"], "Available stock", summary["stock_total"], "Assigned PPE", summary["assigned"], "Low stock alerts", summary["low_stock"]],
        [],
        ["Catalogue", "Type", "PPE", "Size", "Standard", "Condition", "Stock", "Threshold", "Status"],
    ]
    styles: list[list[str | None]] = [
        ["section", None, None, None, None, None, None, None, None],
        [],
        ["section", "section", "section", "section", "section", "section", "section", "section", "section"],
    ]
    for item in data["items"]:
        rows.append(
            [
                "Catalogue",
                item.get("type_epi") or "",
                item.get("nom") or "",
                item.get("taille") or "",
                item.get("norme") or "",
                item.get("etat") or "",
                item.get("quantite_disponible") or 0,
                item.get("seuil_minimum") or 0,
                "LOW STOCK" if item.get("stock_bas") else "OK",
            ]
        )
        styles.append([None, None, None, None, None, None, None, None, "danger" if item.get("stock_bas") else "done"])
    rows.append([])
    styles.append([])
    rows.append(["Assignments", "Name", "First name", "Type", "PPE", "Quantity", "Issue date", "Return date", "Status"])
    styles.append(["section"] * 9)
    for item in data["assignments"]:
        rows.append(["Assignments", item.get("nom") or "", item.get("prenom") or "", item.get("type_epi") or "", item.get("epi") or "", item.get("quantite") or 0, item.get("date_remise") or "", item.get("date_retour") or "", item.get("statut") or ""])
        styles.append([None] * 9)
    rows.append([])
    styles.append([])
    rows.append(["Compliance", "Name", "First name", "Function", "PPE type", "Required", "Assigned", "Status", ""])
    styles.append(["section"] * 9)
    for item in data["compliance"]:
        rows.append(["Compliance", item.get("nom") or "", item.get("prenom") or "", item.get("fonction") or "", item.get("type_epi") or "", item.get("requis") or 0, item.get("affecte") or 0, item.get("statut") or "", ""])
        styles.append([None, None, None, None, None, None, None, "done" if item.get("statut") == "ok" else "danger", None])
    rows.append([])
    styles.append([])
    rows.append(["Alerts", "Alert", "Type", "PPE", "Stock", "Threshold", "Expiration", "Condition", ""])
    styles.append(["section"] * 9)
    for item in data["alerts"]:
        rows.append(["Alerts", item.get("alerte") or "", item.get("type_epi") or "", item.get("nom") or "", item.get("quantite_disponible") or "", item.get("seuil_minimum") or "", item.get("date_expiration") or "", item.get("etat") or "", ""])
        styles.append(["danger"] * 9)
    rows.extend(
        [
            [],
            ["Legend", "Green = compliant / available", "Yellow = inspection or renewal soon", "Red = low stock, missing or expired", "", "", "", "", ""],
            [],
            ["Prepared by", "", "", "Checked by", "", "", "Approved by", "", ""],
            ["Name / Date / Signature", "", "", "Name / Date / Signature", "", "", "Name / Date / Signature", "", ""],
        ]
    )
    styles.extend(
        [
            [],
            ["section", "done", "soon", "danger", None, None, None, None, None],
            [],
            ["section"] * 9,
            [None] * 9,
        ]
    )
    write_styled_xlsx(
        path,
        "PPE Inventory",
        headers,
        rows,
        styles,
        include_company_description=True,
        document_title="OREZONE QHSE - PPE Inventory",
    )


def _timesheet_summary_for_rows(base_summary: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        **base_summary,
        "employees": len(rows),
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
    }
    for row in rows:
        for key in [
            "worked_days",
            "rest_days",
            "break_days",
            "permission_days",
            "sick_days",
            "absent_days",
            "unfilled_days",
            "drilling_hours",
            "standard_hours",
            "hours",
            "actual_hours",
        ]:
            summary[key] += row.get(key, 0) or 0
    summary["actual_hours"] = round(float(summary["actual_hours"]), 2)
    return summary


def _timesheet_employee_name(employee: dict[str, Any]) -> str:
    if employee.get("nom") or employee.get("prenom"):
        return f"{employee.get('nom') or ''} {employee.get('prenom') or ''}".strip()
    return str(employee.get("nom_complet") or "-")


def _timesheet_employee_code(employee: dict[str, Any]) -> str:
    return str(employee.get("matricule") or employee.get("numero_badge") or "-")


def _timesheet_employee_band_style(index: int) -> dict[str, str]:
    colors = [
        ("#7bbf43", "#111827"),
        ("#22a7c9", "#111827"),
        ("#facc15", "#111827"),
        ("#f97316", "#111827"),
        ("#93c5fd", "#111827"),
    ]
    background, text = colors[(index - 1) % len(colors)]
    return {
        "bgcolor": background,
        "style": f"background-color:{background};color:{text};font-weight:bold;",
    }


def _timesheet_compact_cell_label(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status in {"worked_drilling", "worked_standard"}:
        return str(int(float(cell.get("hours") or 0)))
    if label.lower().endswith("h") and label[:-1].isdigit():
        return label[:-1]
    return label


def _timesheet_cell_class(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status == "holiday":
        return "holiday"
    if status == "break" and label == "AL":
        return "annual"
    if status == "break" and label == "P":
        return "permission"
    if status == "break" and label == "S":
        return "sick"
    return status.replace("_", "-")


def _timesheet_xlsx_cell_style(cell: dict[str, Any]) -> str | None:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status == "worked_drilling":
        return "drilling"
    if status == "worked_standard":
        return "standard"
    if status == "holiday":
        return "holiday"
    if status == "rest":
        return "rest"
    if status == "absent":
        return "danger"
    if status == "unfilled":
        return "unfilled"
    if status == "break" and label == "AL":
        return "annual"
    if status == "break" and label == "P":
        return "permission"
    if status == "break" and label == "S":
        return "sick"
    if status == "break":
        return "break"
    return None


def _timesheet_week_class(cell: dict[str, Any]) -> str:
    return "week-start" if cell.get("week_start") else ""


def _timesheet_cell_inline_style(cell: dict[str, Any]) -> dict[str, str]:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    colors = {
        "worked_drilling": ("#00a6d6", "#111827"),
        "worked_standard": ("#ffffff", "#111827"),
        "holiday": ("#22c55e", "#ffffff"),
        "rest": ("#c0392b", "#ffffff"),
        "absent": ("#ef4444", "#ffffff"),
        "unfilled": ("#e5e7eb", "#111827"),
    }
    if status == "break" and label == "AL":
        background, text = "#5b3db6", "#ffffff"
    elif status == "break" and label == "P":
        background, text = "#f4a261", "#ffffff"
    elif status == "break" and label == "S":
        background, text = "#10b981", "#ffffff"
    elif status == "break":
        background, text = "#facc15", "#111827"
    else:
        background, text = colors.get(status, ("#cbd5e1", "#172033"))
    border = "border-left:3px solid #0f172a;" if cell.get("week_start") else ""
    return {
        "bgcolor": background,
        "style": f"background-color:{background};color:{text};font-weight:bold;text-align:center;{border}",
    }


def _shift_style(value: Any, default: str) -> str:
    text = str(value or "").lower()
    if "day" in text:
        return "Day"
    if "night" in text:
        return "Night"
    return default


def _html_shift_class(value: Any) -> str:
    text = str(value or "").lower()
    if "day" in text:
        return "day"
    if "night" in text:
        return "night"
    return ""


def _attendance_remark(record: dict[str, Any]) -> str:
    remarks: list[str] = []
    if not record.get("numero_badge"):
        remarks.append("Badge manquant")
    if str(record.get("statut") or "").lower() == "present":
        if not record.get("heure_entree") or not record.get("heure_sortie"):
            remarks.append("Heures incompletes")
        if float(record.get("heures") or 0) > 12:
            remarks.append("Plus de 12h")
    return " / ".join(remarks)


def _attendance_summary_rows(
    summary: dict[str, int | float],
    records: list[dict[str, Any]],
) -> str:
    by_shift: dict[str, int] = {}
    by_function: dict[str, int] = {}
    for record in records:
        shift = str(record.get("shift") or "Non defini")
        function = str(record.get("fonction") or "Non definie")
        by_shift[shift] = by_shift.get(shift, 0) + 1
        by_function[function] = by_function.get(function, 0) + 1

    rows = [
        _summary_html_row("LISTE DE PRESENCE OREZONE - SUMMARY", "", "summary-title"),
        _summary_html_row("Indicator", "Value", "metric"),
        _summary_html_row("Total employees", summary.get("total", 0)),
        _summary_html_row("Present", summary.get("present", 0), "present"),
        _summary_html_row("Absent", summary.get("absent", 0), "absent"),
        _summary_html_row("Total hours", summary.get("hours", 0)),
        _summary_html_row("Rows to check", summary.get("issues", 0), "issue"),
        _summary_html_row("Missing badge", summary.get("missing_badge", 0), "issue"),
        _summary_html_row("Overtime > 12h", summary.get("overtime", 0), "issue"),
        '<tr><td colspan="2"></td></tr>',
        _summary_html_row("By shift", "Count", "metric"),
    ]
    rows.extend(_summary_html_row(key, value) for key, value in sorted(by_shift.items()))
    rows.append('<tr><td colspan="2"></td></tr>')
    rows.append(_summary_html_row("By function", "Count", "metric"))
    rows.extend(_summary_html_row(key, value) for key, value in sorted(by_function.items()))
    return "\n".join(rows)


def _employee_summary_rows(summary: dict[str, int], rows: list[dict[str, Any]]) -> str:
    by_shift: dict[str, int] = {}
    by_function: dict[str, int] = {}
    by_state: dict[str, int] = {}
    for row in rows:
        shift = str(row.get("shift") or "Non defini")
        function = str(row.get("fonction") or "Non definie")
        state = str(row.get("situation") or "Non defini")
        by_shift[shift] = by_shift.get(shift, 0) + 1
        by_function[function] = by_function.get(function, 0) + 1
        by_state[state] = by_state.get(state, 0) + 1

    summary_rows = [
        _summary_html_row("LIST OF OREZONE EMPLOYEE - SUMMARY", "", "summary-title"),
        _summary_html_row("Indicator", "Value", "metric"),
        _summary_html_row("Total employees", summary.get("total", 0)),
        _summary_html_row("Day Shift", summary.get("day", 0), "day"),
        _summary_html_row("Night Shift", summary.get("night", 0), "night"),
        _summary_html_row("Break/Absence", summary.get("off", 0), "issue"),
        _summary_html_row("Break due", summary.get("due", 0), "issue"),
        '<tr><td colspan="2"></td></tr>',
        _summary_html_row("By status", "Count", "metric"),
    ]
    summary_rows.extend(_summary_html_row(key, value) for key, value in sorted(by_state.items()))
    summary_rows.append('<tr><td colspan="2"></td></tr>')
    summary_rows.append(_summary_html_row("By shift", "Count", "metric"))
    summary_rows.extend(_summary_html_row(key, value) for key, value in sorted(by_shift.items()))
    summary_rows.append('<tr><td colspan="2"></td></tr>')
    summary_rows.append(_summary_html_row("By function", "Count", "metric"))
    summary_rows.extend(_summary_html_row(key, value) for key, value in sorted(by_function.items()))
    return "\n".join(summary_rows)


def _employee_state_class(value: Any) -> str:
    text = str(value or "").lower()
    if "travail" in text:
        return "work"
    if "permission" in text:
        return "permission"
    if "malade" in text:
        return "sick"
    if "break" in text:
        return "break"
    return ""


def _break_text_is_due(value: Any) -> bool:
    text = str(value or "").lower()
    return "retard" in text or "aujourd" in text


def _write_training_matrix_xlsx(
    path: Path,
    training_types: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> None:
    headers = ["N", "Employee", "Badge", "Function", *[str(item.get("nom") or "") for item in training_types]]
    data_rows: list[list[Any]] = []
    styles: list[list[str | None]] = []
    total_cells = len(rows) * len(training_types)
    done = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "done")
    soon = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "soon")
    expired = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "expired")
    missing = sum(1 for row in rows for cell in row.get("cells", []) if cell.get("status") == "missing")
    compliance = round((done / total_cells) * 100) if total_cells else 0
    for index, row in enumerate(rows, start=1):
        employee = row["employee"]
        cells = row.get("cells", [])
        data_rows.append(
            [
                index,
                f"{employee.get('nom') or '-'} {employee.get('prenom') or ''}".strip(),
                employee.get("numero_badge") or "",
                employee.get("fonction") or "",
                *[_training_cell_text(cell) for cell in cells],
            ]
        )
        styles.append(
            [
                None,
                None,
                "danger" if not employee.get("numero_badge") else None,
                None,
                *[_training_cell_class(cell) for cell in cells],
            ]
        )
    data_rows.append([])
    styles.append([])
    data_rows.append(
        [
            "Summary",
            f"Employees: {len(rows)}",
            f"Training types: {len(training_types)}",
            f"Compliance: {compliance}%",
            f"Valid: {done}",
            f"Soon: {soon}",
            f"Expired: {expired}",
            f"Missing: {missing}",
        ]
    )
    styles.append(["section", "done", "section", "section", "done", "soon", "danger", "danger"])
    data_rows.append([])
    styles.append([])
    data_rows.append(["Legend", "Green = compliant", "Yellow = renewal soon", "Red = missing or expired"])
    styles.append(["section", "done", "soon", "danger"])
    write_styled_xlsx(
        path,
        "Training Matrix",
        headers,
        data_rows,
        styles,
        include_company_description=True,
        document_title="OREZONE QHSE - TRAINING MATRIX",
    )


def _training_matrix_summary_rows(
    training_types: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> str:
    summary_rows = [
        _summary_html_row("OREZONE TRAINING MATRIX - SUMMARY", "", "summary-title"),
        _summary_html_row("Training", "Valid / Soon / Expired / Missing / Compliance", "metric"),
    ]
    for index, training_type in enumerate(training_types):
        valid = 0
        soon = 0
        expired = 0
        missing = 0
        for row in rows:
            cells = row.get("cells", [])
            if index >= len(cells):
                continue
            status = cells[index].get("status")
            if status == "done":
                valid += 1
            elif status == "soon":
                soon += 1
            elif status == "expired":
                expired += 1
            elif status == "missing":
                missing += 1
        total = valid + soon + expired + missing
        compliance = round(valid * 100 / total) if total else 0
        summary_rows.append(
            _summary_html_row(
                training_type.get("nom") or "-",
                f"Valid: {valid} | Soon: {soon} | Expired: {expired} | Missing: {missing} | Compliance: {compliance}%",
                "issue" if expired or missing else "present",
            )
        )
    summary_rows.append('<tr><td colspan="2"></td></tr>')
    summary_rows.append(_summary_html_row("Function", "Employees", "metric"))
    by_function: dict[str, int] = {}
    for row in rows:
        function = str(row["employee"].get("fonction") or "Non definie")
        by_function[function] = by_function.get(function, 0) + 1
    summary_rows.extend(_summary_html_row(key, value) for key, value in sorted(by_function.items()))
    return "\n".join(summary_rows)


def _training_cell_text(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    if status == "missing":
        return "Non faite"
    if status == "expired":
        return f"Expiree {cell.get('date_expiration') or ''}".strip()
    if status == "soon":
        return f"J-{cell.get('days_left')} {cell.get('date_expiration') or ''}".strip()
    return str(cell.get("date_expiration") or cell.get("label") or "")


def _training_cell_class(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    if status in {"done", "soon", "missing", "expired"}:
        return status
    return ""


def _summary_html_row(label: Any, value: Any, css_class: str = "") -> str:
    return (
        "<tr>"
        f'<td class="{css_class}">{_xml_escape(label)}</td>'
        f'<td class="{css_class}">{_xml_escape(value)}</td>'
        "</tr>"
    )


def _xls_borders() -> str:
    return (
        '<Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>'
        '<Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>'
        '<Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>'
        '<Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>'
    )


def _state_label(state: str | None) -> str:
    return {
        "work": "Au travail",
        "break": "En break",
        "annual": "Break annuel",
        "permission": "Permission",
        "sick": "Malade",
    }.get(str(state or "work"), "Au travail")


def _shift_label(shift_code: Any, shift_label: Any) -> str:
    return {
        "DAY": "Day Shift",
        "NIGHT": "Night Shift",
        "BREAK": "Break",
    }.get(str(shift_code or ""), str(shift_label or ""))


def _break_due_text(record: dict[str, Any]) -> str:
    if record.get("next_planned_break_start"):
        return f"Planifie: {record['next_planned_break_start']}"
    due_date = str(record.get("next_break_due_date") or "")
    days = record.get("days_until_break_due")
    if days in ("", None):
        return due_date
    days_int = int(days)
    if days_int < 0:
        return f"En retard: {due_date}"
    if days_int == 0:
        return f"Aujourd'hui: {due_date}"
    return f"{due_date} ({days_int} j)"


def _lineup_observation(record: dict[str, Any]) -> str:
    if not record.get("numero_badge"):
        return "Badge a verifier"
    state = str(record.get("current_state") or "work")
    if state != "work":
        return _state_label(state)
    days = record.get("days_until_break_due")
    if days is not None and int(days) <= 0 and not record.get("next_planned_break_start"):
        return "Break a planifier"
    return ""


def _clip(value: Any, length: int) -> str:
    text = str(value)
    return text if len(text) <= length else text[: length - 1] + "."


def _write_attendance_pdf(
    path: Path,
    date_presence: str,
    rows: list[dict[str, Any]],
    summary: dict[str, int | float],
) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        lines = [
            "OREZONE QHSE",
            "OREZONE DAILY ATTENDANCE LIST",
            f"Complete date: {_pdf_date_label(date_presence)}",
            "Daily meeting topic: ____________________",
            "Meeting facilitator: ____________________",
            "",
            "Section | Name | Badge | Function | Shift | Entry | Exit | Hours | Signature",
        ]
        for section, group_rows in _attendance_pdf_groups(rows):
            lines.append(section)
            for row in group_rows:
                name = f"{row.get('nom') or ''} {row.get('prenom') or ''}".strip() or str(row.get("nom_complet") or "-")
                lines.append(
                    " | ".join(
                        [
                            section,
                            _clip(name, 22),
                            _clip(row.get("numero_badge") or "-", 10),
                            _clip(row.get("fonction") or "-", 18),
                            _clip(row.get("shift") or "-", 10),
                            row.get("heure_entree") or "-",
                            row.get("heure_sortie") or "-",
                            str(row.get("heures") or 0),
                            "__________",
                        ]
                    )
                )
        lines.extend(["", "Prepared by: ______ Checked by: ______ Approved by: ______"])
        _write_minimal_pdf(path, lines)
        return

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AttendanceTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "AttendanceSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.4,
        leading=10.5,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
    )
    small_style = ParagraphStyle(
        "AttendanceSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=8.3,
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "AttendanceHeaderCell",
        parent=small_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "AttendanceSection",
        parent=small_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.white,
        alignment=TA_LEFT,
    )

    document = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=9 * mm,
        rightMargin=9 * mm,
        topMargin=9 * mm,
        bottomMargin=10 * mm,
    )
    story: list[Any] = []
    header = Table(
        [
            [Paragraph("OREZONE", title_style), Paragraph("OREZONE DAILY ATTENDANCE LIST", title_style)],
            ["", Paragraph("Daily field meeting attendance | Controlled QHSE document", subtitle_style)],
            ["", Paragraph(f"Generated: {generated_at} | Orezone operational supervision and QHSE compliance", subtitle_style)],
        ],
        colWidths=[38 * mm, 239 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("BACKGROUND", (0, 1), (0, 2), colors.HexColor("#1E3A8A")),
                ("SPAN", (0, 0), (0, 2)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (1, 1), (1, 2), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#1E3A8A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFDBFE")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([header, Spacer(1, 4 * mm)])

    meeting = Table(
        [
            ["Complete date", _pdf_date_label(date_presence), "Meeting facilitator", ""],
            ["Daily meeting topic", "", "", ""],
        ],
        colWidths=[54 * mm, 74 * mm, 54 * mm, 95 * mm],
        rowHeights=[9 * mm, 13 * mm],
    )
    meeting.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 1), colors.HexColor("#EFF6FF")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#EFF6FF")),
                ("SPAN", (1, 1), (3, 1)),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, 1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.extend([meeting, Spacer(1, 4 * mm)])

    metrics = Table(
        [
            [
                Paragraph(f"<b>Total</b><br/>{summary.get('total', 0)}", subtitle_style),
                Paragraph(f"<b>Presents</b><br/>{summary.get('present', 0)}", subtitle_style),
                Paragraph(f"<b>Absents</b><br/>{summary.get('absent', 0)}", subtitle_style),
                Paragraph(f"<b>Hours</b><br/>{summary.get('hours', 0)}", subtitle_style),
                Paragraph(f"<b>Missing badges</b><br/>{summary.get('missing_badge', 0)}", subtitle_style),
            ]
        ],
        colWidths=[55.4 * mm] * 5,
    )
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#DBEAFE")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#DCFCE7")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#FEE2E2")),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#EFF6FF")),
                ("BACKGROUND", (4, 0), (4, 0), colors.HexColor("#FEF3C7")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 4 * mm)])

    table_data: list[list[Any]] = [
        [Paragraph(label, header_style) for label in ["N", "Name", "First name", "Badge", "Function", "Shift", "Entry", "Exit", "Hours", "Signature"]]
    ]
    index = 1
    section_row_indexes: list[int] = []
    for section, group_rows in _attendance_pdf_groups(rows):
        section_row_indexes.append(len(table_data))
        table_data.append([Paragraph(section, section_style), "", "", "", "", "", "", "", "", ""])
        if not group_rows:
            table_data.append(["", Paragraph("No employee in this section", small_style), "", "", "", "", "", "", "", ""])
            continue
        for row in group_rows:
            table_data.append(
                [
                    index,
                    Paragraph(_clip(row.get("nom") or row.get("nom_complet") or "-", 22), small_style),
                    Paragraph(_clip(row.get("prenom") or "-", 18), small_style),
                    _clip(row.get("numero_badge") or "-", 11),
                    Paragraph(_clip(row.get("fonction") or "-", 28), small_style),
                    _clip(row.get("shift") or "-", 11),
                    row.get("heure_entree") or "-",
                    row.get("heure_sortie") or "-",
                    row.get("heures") or 0,
                    "",
                ]
            )
            index += 1

    attendance_table = Table(
        table_data,
        colWidths=[8 * mm, 34 * mm, 30 * mm, 20 * mm, 52 * mm, 24 * mm, 20 * mm, 20 * mm, 18 * mm, 48 * mm],
        repeatRows=1,
    )
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 1), (3, -1), "CENTER"),
            ("ALIGN", (5, 1), (8, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )
    for row_index in section_row_indexes:
        table_style.add("SPAN", (0, row_index), (-1, row_index))
        table_style.add("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#1E3A8A"))
        table_style.add("TEXTCOLOR", (0, row_index), (-1, row_index), colors.white)
    for row_index, row in enumerate(table_data[1:], start=1):
        if row_index in section_row_indexes:
            continue
        if row and str(row[0]).isdigit():
            table_style.add("BACKGROUND", (9, row_index), (9, row_index), colors.HexColor("#FFFFFF"))
    attendance_table.setStyle(table_style)
    story.append(attendance_table)

    story.extend([Spacer(1, 5 * mm)])
    signature = Table(
        [
            ["Prepared by", "Checked by", "Approved by", "QHSE comments"],
            ["Name / Date / Signature", "Name / Date / Signature", "Name / Date / Signature", ""],
        ],
        colWidths=[55 * mm, 55 * mm, 55 * mm, 112 * mm],
        rowHeights=[8 * mm, 17 * mm],
    )
    signature.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ]
        )
    )
    story.append(signature)

    def add_page_footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(9 * mm, 6 * mm, "OREZONE QHSE - Controlled attendance document")
        canvas.drawRightString(288 * mm, 6 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)


def _attendance_pdf_groups(rows: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    return [
        ("EXPATRIATE EMPLOYEES", [row for row in rows if str(row.get("type_employe") or "").lower() == "expatriate"]),
        ("NATIONAL EMPLOYEES", [row for row in rows if str(row.get("type_employe") or "national").lower() != "expatriate"]),
    ]


def _pdf_date_label(value: str) -> str:
    try:
        return datetime.fromisoformat(str(value or "")).strftime("%A, %d %B %Y")
    except ValueError:
        return str(value or "")


def _write_employee_list_pdf(path: Path, rows: list[dict[str, Any]], summary: dict[str, int]) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        lines = [
            "OREZONE QHSE",
            "LIST OF OREZONE EMPLOYEE",
            f"Generated: {generated_at}",
            f"Total: {summary.get('total', 0)} | Day: {summary.get('day', 0)} | Night: {summary.get('night', 0)} | Break due: {summary.get('due', 0)}",
            "",
            "N | Matricule | Nom | Prenom | Badge | Fonction | Site | Shift | Situation | Prochain break",
        ]
        for index, row in enumerate(rows, start=1):
            lines.append(
                " | ".join(
                    [
                        str(index),
                        _clip(row.get("matricule") or "-", 10),
                        _clip(row.get("nom") or "-", 18),
                        _clip(row.get("prenom") or "-", 18),
                        _clip(row.get("numero_badge") or "-", 10),
                        _clip(row.get("fonction") or "-", 22),
                        _clip(row.get("site") or "-", 14),
                        _clip(row.get("shift") or "-", 8),
                        _clip(row.get("situation") or "-", 14),
                        _clip(row.get("prochain_break") or "-", 18),
                    ]
                )
            )
        _write_minimal_pdf(path, lines)
        return

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "OrezoneTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "OrezoneSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
    )
    small_style = ParagraphStyle(
        "OrezoneSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "OrezoneHeaderCell",
        parent=small_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    document = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=9 * mm,
        rightMargin=9 * mm,
        topMargin=9 * mm,
        bottomMargin=10 * mm,
    )
    story: list[Any] = []

    header = Table(
        [
            [
                Paragraph("OREZONE", title_style),
                Paragraph("LIST OF OREZONE EMPLOYEE", title_style),
            ],
            [
                "",
                Paragraph("Operational employee list, shift allocation, status follow-up and break readiness.", subtitle_style),
            ],
            [
                "",
                Paragraph(f"Generated: {generated_at} | Controlled QHSE document | Professional field use", subtitle_style),
            ],
        ],
        colWidths=[38 * mm, 239 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("BACKGROUND", (0, 1), (0, 2), colors.HexColor("#1E3A8A")),
                ("SPAN", (0, 0), (0, 2)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (1, 1), (1, 2), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#1E3A8A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFDBFE")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([header, Spacer(1, 5 * mm)])

    metric_data = [
        ["Total", summary.get("total", 0)],
        ["Day shift", summary.get("day", 0)],
        ["Night shift", summary.get("night", 0)],
        ["Break / Absence", summary.get("off", 0)],
        ["Break due", summary.get("due", 0)],
    ]
    metrics = Table([[Paragraph(f"<b>{label}</b><br/>{value}", subtitle_style) for label, value in metric_data]], colWidths=[55.4 * mm] * 5)
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#DCFCE7")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#DBEAFE")),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#FEF3C7")),
                ("BACKGROUND", (4, 0), (4, 0), colors.HexColor("#FEE2E2")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 4 * mm)])

    table_data: list[list[Any]] = [
        [Paragraph(label, header_style) for label in ["N", "Matricule", "Nom", "Prenom", "Badge", "Fonction", "Site", "Shift", "Situation", "Prochain break"]]
    ]
    for index, row in enumerate(rows, start=1):
        table_data.append(
            [
                index,
                _clip(row.get("matricule") or "-", 12),
                Paragraph(_clip(row.get("nom") or "-", 22), small_style),
                Paragraph(_clip(row.get("prenom") or "-", 22), small_style),
                _clip(row.get("numero_badge") or "-", 12),
                Paragraph(_clip(row.get("fonction") or "-", 30), small_style),
                Paragraph(_clip(row.get("site") or "-", 18), small_style),
                _clip(row.get("shift") or "-", 10),
                _clip(row.get("situation") or "-", 16),
                Paragraph(_clip(row.get("prochain_break") or "-", 24), small_style),
            ]
        )

    employee_table = Table(
        table_data,
        colWidths=[8 * mm, 21 * mm, 29 * mm, 29 * mm, 20 * mm, 47 * mm, 28 * mm, 19 * mm, 25 * mm, 51 * mm],
        repeatRows=1,
    )
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (1, -1), "CENTER"),
            ("ALIGN", (4, 1), (4, -1), "CENTER"),
            ("ALIGN", (7, 1), (8, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )
    for row_index, row in enumerate(rows, start=1):
        shift = str(row.get("shift") or "").lower()
        situation = str(row.get("situation") or "").lower()
        due = _break_text_is_due(row.get("prochain_break"))
        if "night" in shift:
            table_style.add("BACKGROUND", (7, row_index), (7, row_index), colors.HexColor("#DBEAFE"))
        elif "day" in shift:
            table_style.add("BACKGROUND", (7, row_index), (7, row_index), colors.HexColor("#DCFCE7"))
        if situation and "travail" not in situation.lower() and "work" not in situation.lower():
            table_style.add("BACKGROUND", (8, row_index), (8, row_index), colors.HexColor("#FEF3C7"))
        if due:
            table_style.add("BACKGROUND", (9, row_index), (9, row_index), colors.HexColor("#FEE2E2"))
            table_style.add("TEXTCOLOR", (9, row_index), (9, row_index), colors.HexColor("#991B1B"))
    employee_table.setStyle(table_style)
    story.append(employee_table)

    story.extend([Spacer(1, 5 * mm)])
    signature = Table(
        [
            ["Prepared by", "Checked by", "Approved by", "QHSE comments"],
            ["Name / Date / Signature", "Name / Date / Signature", "Name / Date / Signature", ""],
        ],
        colWidths=[55 * mm, 55 * mm, 55 * mm, 112 * mm],
        rowHeights=[8 * mm, 17 * mm],
    )
    signature.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ]
        )
    )
    story.append(signature)

    def add_page_footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(9 * mm, 6 * mm, "OREZONE QHSE - Controlled document")
        canvas.drawRightString(288 * mm, 6 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)


def _write_simple_pdf(path: Path, lines: list[str]) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        _write_minimal_pdf(path, lines)
        return

    document = canvas.Canvas(str(path), pagesize=A4)
    _, height = A4
    y = height - 52
    document.setFont("Helvetica-Bold", 12)
    document.drawString(50, y, str(lines[0] if lines else "OREZONE QHSE"))
    document.setFont("Helvetica", 9)
    y -= 22
    for line in lines[1:]:
        if y < 46:
            document.showPage()
            document.setFont("Helvetica", 9)
            y = height - 52
        document.drawString(50, y, str(line))
        y -= 14
    document.save()


def _write_minimal_pdf(path: Path, lines: list[str]) -> None:
    escaped_lines = [_escape_pdf(line) for line in lines]
    text_commands = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(escaped_lines):
        if index == 0:
            text_commands.append(f"({line}) Tj")
        else:
            text_commands.append(f"T* ({line}) Tj")
    text_commands.append("ET")
    stream = "\n".join(text_commands).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref_start = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(content)


def _escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _xml_escape(value: Any) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
