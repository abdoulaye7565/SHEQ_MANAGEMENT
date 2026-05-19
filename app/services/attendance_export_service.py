from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import EXPORTS_DIR
from app.services.attendance_service import get_attendance_list
from app.services.employee_service import list_employees
from app.services.break_service import list_active_break_employees
from app.services.ppe_service import get_ppe_export_data
from app.services.monthly_timesheet_service import get_monthly_10h_timesheet
from app.services.timesheet_service import get_timesheet, list_timesheet_audit
from app.services.toolbox_talk_service import list_toolbox_topics
from app.services.xlsx_service import write_attendance_list_xlsx, write_simple_xlsx, write_styled_xlsx


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
) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = "".join(char if char.isalnum() or char in "._-" else "_" for char in filename)
    output_path = _unique_export_path(safe_filename)
    return _write_styled_xlsx_safely(output_path, sheet_name[:31], headers, rows, styles)


def export_attendance_xlsx(date_presence: str) -> Path:
    rows = get_attendance_list(date_presence)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path(f"liste_presence_{date_presence}.xlsx")

    headers = [
        "Date",
        "Nom",
        "Prenom",
        "Numero badge",
        "Fonction",
        "Statut presence",
        "Heure entree",
        "Heure sortie",
        "Heures travaillees",
    ]
    data = [
        [
            date_presence,
            row.get("nom") or "",
            row.get("prenom") or "",
            row.get("numero_badge") or "",
            row.get("fonction") or "",
            "Present" if row.get("statut_presence") == "present" else "Absent",
            row.get("heure_entree") or "",
            row.get("heure_sortie") or "",
            row.get("heures_travaillees") or 0,
        ]
        for row in rows
    ]
    return export_attendance_records_xlsx(date_presence, [
        {
            "nom": row[1],
            "prenom": row[2],
            "numero_badge": row[3],
            "fonction": row[4],
            "shift": "",
            "statut": row[5],
            "heure_entree": row[6],
            "heure_sortie": row[7],
            "heures": row[8],
            "controle": "",
        }
        for row in data
    ])


def export_attendance_records_xlsx(date_presence: str, records: list[dict[str, Any]]) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path(f"liste_presence_orezone_{date_presence}.xls")
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
        _write_attendance_list_xls(output_path, date_presence, records, summary)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(f"liste_presence_orezone_{date_presence}_nouveau.xls")
        _write_attendance_list_xls(fallback, date_presence, records, summary)
        return fallback


def export_attendance_pdf(date_presence: str) -> Path:
    rows = get_attendance_list(date_presence)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path(f"liste_presence_{date_presence}.pdf")

    lines = [
        "OREZONE QHSE",
        f"Liste de presence - {date_presence}",
        "",
        "Nom | Badge | Fonction | Statut | Entree | Sortie | Heures",
        "-" * 92,
    ]
    for row in rows:
        name = f"{row.get('nom') or ''} {row.get('prenom') or ''}".strip() or str(row.get("nom_complet") or "-")
        status = "Present" if row.get("statut_presence") == "present" else "Absent"
        lines.append(
            " | ".join(
                [
                    _clip(name, 24),
                    _clip(row.get("numero_badge") or "-", 12),
                    _clip(row.get("fonction") or "-", 18),
                    status,
                    row.get("heure_entree") or "-",
                    row.get("heure_sortie") or "-",
                    str(row.get("heures_travaillees") or 0),
                ]
            )
        )
    _write_simple_pdf(output_path, lines)
    return output_path


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
    output_path = _unique_export_path("list_of_orezone_employee.xls")
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
    try:
        _write_employee_list_xls(output_path, rows, summary)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("list_of_orezone_employee_nouveau.xls")
        _write_employee_list_xls(fallback, rows, summary)
        return fallback


def export_training_matrix_xls(
    training_types: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_export_path("matrice_formations_orezone.xls")
    try:
        _write_training_matrix_xls(output_path, training_types, rows)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("matrice_formations_orezone_nouveau.xls")
        _write_training_matrix_xls(fallback, training_types, rows)
        return fallback


def export_timesheet_xls(month: str, site_id: int | None = None) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timesheet = get_timesheet(month, site_id=site_id)
    site_suffix = ""
    if timesheet.get("site"):
        site_suffix = "_" + "".join(
            char if char.isalnum() or char in "._-" else "_"
            for char in str(timesheet["site"].get("nom") or "")
        )
    output_path = _unique_export_path(f"timesheet_orezone{site_suffix}_{timesheet['period']['month']}.xls")
    try:
        _write_timesheet_xls(output_path, timesheet)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(f"timesheet_orezone{site_suffix}_{timesheet['period']['month']}_nouveau.xls")
        _write_timesheet_xls(fallback, timesheet)
        return fallback


def export_timesheet_employee_xls(month: str, employee_id: int) -> Path:
    timesheet = get_timesheet(month)
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
        f"timesheet_orezone_{timesheet['period']['month']}_{safe_name or employee_id}.xls"
    )
    try:
        _write_timesheet_xls(output_path, individual)
        return output_path
    except PermissionError:
        fallback = _unique_export_path(
            f"timesheet_orezone_{timesheet['period']['month']}_{safe_name or employee_id}_nouveau.xls"
        )
        _write_timesheet_xls(fallback, individual)
        return fallback


def export_timesheet_all_employees_xls(month: str) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timesheet = get_timesheet(month)
    rows = list(timesheet.get("rows") or [])
    if not rows:
        raise ValueError("Aucun employe disponible pour cet export TimeSheet.")
    return _export_timesheet_rows_to_directory(timesheet, rows, "timesheets_individuels_orezone")


def export_timesheet_selected_employees_xls(month: str, employee_ids: list[int]) -> Path:
    selected_ids = {int(employee_id) for employee_id in employee_ids if int(employee_id or 0)}
    if not selected_ids:
        raise ValueError("Selectionne au moins un employe pour l'export TimeSheet.")
    timesheet = get_timesheet(month)
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
            f"timesheet_orezone_{timesheet['period']['month']}_{safe_name or employee_id}.xls",
        )
        _write_timesheet_xls(output_path, individual)
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


def export_monthly_10h_timesheet_xlsx(month: str, site_id: int | None = None) -> Path:
    timesheet = get_monthly_10h_timesheet(month, site_id=site_id)
    expatriates = get_monthly_10h_timesheet(month, site_id=site_id, employee_type="expatriate")
    site_suffix = ""
    if timesheet.get("site"):
        site_suffix = "_" + _safe_name(timesheet["site"].get("nom") or "")
    headers = [
        "Employe",
        "Badge",
        "Fonction",
        "Site",
        *[f"{day['day']} {day['weekday']}" for day in timesheet["days"]],
        "Jours travailles",
        "Repos",
        "Break normal",
        "Break annuel",
        "Heures",
    ]
    rows = []
    styles = []
    for row in timesheet["rows"]:
        rows.append(_monthly_10h_export_row(row))
        styles.append(_monthly_10h_export_style(row))
    rows.append(["EXPATRIES - RESERVE", *["" for _ in headers[1:]]])
    styles.append(["section" for _ in headers])
    rows.append(headers)
    styles.append(["section" for _ in headers])
    if expatriates["rows"]:
        for row in expatriates["rows"]:
            rows.append(_monthly_10h_export_row(row))
            styles.append(_monthly_10h_export_style(row))
    else:
        rows.append(["Aucun employe expatrie actif pour cette periode.", *["" for _ in headers[1:]]])
        styles.append([None for _ in headers])
    return export_styled_rows_xlsx(
        f"timesheet_10h_1_25{site_suffix}_{timesheet['period']['month']}.xlsx",
        "TimeSheet 1-25",
        headers,
        rows,
        styles,
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
        row["annual_break_days"],
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
    ]


def export_toolbox_talk_xlsx(month: str) -> Path:
    data = list_toolbox_topics(month)
    table_headers = ["Date", "Jour", "Theme / Topic", "Facilitateur", "Site", "Etat"]
    rows = [
        [
            "Description OREZONE",
            "Planning mensuel des Toolbox Talk Meeting pour la sensibilisation QHSE terrain.",
            "",
            "",
            "",
            "",
        ],
        ["Mois", data.get("label") or data["month"], "", "", "", ""],
        ["", "", "", "", "", ""],
        table_headers,
    ]
    styles = [
        ["section", "section", "section", "section", "section", "section"],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        ["section", "section", "section", "section", "section", "section"],
    ]
    rows.extend(
        [
            row["date_theme"],
            row["weekday"],
            row.get("theme") or "",
            row.get("facilitateur") or "",
            row.get("site") or "",
            "Renseigne" if row.get("status") == "done" else "A completer",
        ]
        for row in data["rows"]
    )
    styles.extend(
        [None, None, None, None, None, "done" if row.get("status") == "done" else "danger"]
        for row in data["rows"]
    )
    return export_styled_rows_xlsx(
        f"toolbox_talk_meeting_{data['month']}.xlsx",
        "Toolbox Talk",
        ["OREZONE QHSE - TOOLBOX TALK MEETING", "", "", "", "", ""],
        rows,
        styles,
    )


def export_ppe_inventory_xls() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = get_ppe_export_data()
    output_path = _unique_export_path("gestion_epi_orezone.xls")
    try:
        _write_ppe_inventory_xls(output_path, data)
        return output_path
    except PermissionError:
        fallback = _unique_export_path("gestion_epi_orezone_nouveau.xls")
        _write_ppe_inventory_xls(fallback, data)
        return fallback


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


def _monthly_10h_cell_style(cell: dict[str, Any]) -> str | None:
    status = str(cell.get("status") or "")
    if status == "worked":
        return "done"
    if status == "rest":
        return "soon"
    if status == "normal_break":
        return "missing"
    if status == "annual_break":
        return "annual"
    return None


def _write_xlsx_safely(path: Path, sheet_name: str, headers: list[str], rows: list[list[Any]]) -> Path:
    try:
        write_simple_xlsx(path, sheet_name, headers, rows)
        return path
    except PermissionError:
        fallback = _unique_export_path(f"{path.stem}_nouveau{path.suffix}")
        write_simple_xlsx(fallback, sheet_name, headers, rows)
        return fallback


def _write_styled_xlsx_safely(
    path: Path,
    sheet_name: str,
    headers: list[str],
    rows: list[list[Any]],
    styles: list[list[str | None]],
) -> Path:
    try:
        write_styled_xlsx(path, sheet_name, headers, rows, styles)
        return path
    except PermissionError:
        fallback = _unique_export_path(f"{path.stem}_nouveau{path.suffix}")
        write_styled_xlsx(fallback, sheet_name, headers, rows, styles)
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
    risk = soon + expired + missing
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


def _write_timesheet_xls(path: Path, timesheet: dict[str, Any]) -> None:
    if timesheet.get("print_individual") and len(timesheet.get("rows") or []) == 1:
        _write_individual_timesheet_print_xls(path, timesheet)
        return
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    days = timesheet["days"]
    period = timesheet["period"]
    summary = timesheet["summary"]
    headers = [
        "N",
        "Employe",
        "Badge",
        "Fonction",
        *[f"S{day['week_index']}\n{day['day']:02d}\n{day['weekday']}\n{day['planned_hours']}h" for day in days],
        "Jours travailles",
        *timesheet.get("week_labels", []),
        "Heures 12H",
        "Heures 8H",
        "Repos",
        "Absent",
        "Non renseigne",
        "Break",
        "Permission",
        "Sick",
        "Heures",
        "Heures reelles",
    ]
    header_html = "".join(f"<th>{_xml_escape(header)}</th>" for header in headers)
    rows_html = []
    for index, row in enumerate(timesheet["rows"], start=1):
        employee = row["employee"]
        cells = [
            f'<td class="number">{index}</td>',
            f'<td class="employee">{_xml_escape(_timesheet_employee_name(employee))}</td>',
            f'<td>{_xml_escape(employee.get("numero_badge") or "-")}</td>',
            f'<td>{_xml_escape(employee.get("fonction") or "-")}</td>',
        ]
        for cell in row["cells"]:
            inline_style = _timesheet_cell_inline_style(cell)
            cells.append(
                f'<td class="day-cell {_timesheet_cell_class(cell)} {_timesheet_week_class(cell)}" '
                f'bgcolor="{inline_style["bgcolor"]}" style="{inline_style["style"]}">'
                f'{_xml_escape(cell["label"])}</td>'
            )
        cells.extend(
            [
                f'<td class="total ok">{row["worked_days"]}</td>',
                *[
                    f'<td class="total hours">{row.get("weekly_hours", {}).get(week, 0)}</td>'
                    for week in timesheet.get("week_labels", [])
                ],
                f'<td class="total worked-drilling">{row.get("drilling_hours", 0)}</td>',
                f'<td class="total worked-standard">{row.get("standard_hours", 0)}</td>',
                f'<td class="total rest">{row["rest_days"]}</td>',
                f'<td class="total absent">{row.get("absent_days", 0)}</td>',
                f'<td class="total unfilled">{row.get("unfilled_days", 0)}</td>',
                f'<td class="total break">{row["break_days"]}</td>',
                f'<td class="total permission">{row.get("permission_days", 0)}</td>',
                f'<td class="total sick">{row.get("sick_days", 0)}</td>',
                f'<td class="total hours">{row["hours"]}</td>',
                f'<td class="total hours">{row.get("actual_hours", 0)}</td>',
            ]
        )
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    col_count = len(headers)
    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Calibri, Arial, sans-serif; color: #172033; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #cbd5e1; padding: 5px 7px; font-size: 10pt; mso-number-format:"\\@"; }}
th {{ background: #1e3a8a; color: #fff; font-weight: bold; text-align: center; white-space: pre-line; }}
th:nth-child(7n+5) {{ border-left: 3px solid #0f172a; }}
.title {{ background: #1e3a8a; color: #fff; font-size: 20pt; font-weight: bold; text-align: center; }}
.subtitle {{ background: #eff6ff; color: #172033; font-weight: bold; }}
.metric {{ background: #dbeafe; font-weight: bold; text-align: center; }}
.metric-ok {{ background: #dcfce7; font-weight: bold; text-align: center; }}
.metric-warn {{ background: #fef3c7; font-weight: bold; text-align: center; }}
.employee {{ font-weight: bold; min-width: 180px; }}
.number {{ text-align: center; }}
.day-cell {{ text-align: center; font-weight: bold; width: 42px; }}
.week-start {{ border-left: 3px solid #0f172a; }}
.worked-drilling {{ background: #2563eb; color: #fff; }}
.worked-standard {{ background: #16a34a; color: #fff; }}
.rest {{ background: #cbd5e1; color: #172033; }}
.absent {{ background: #fca5a5; color: #172033; }}
.unfilled {{ background: #e5e7eb; color: #172033; }}
.break {{ background: #f59e0b; color: #172033; }}
.permission {{ background: #a855f7; color: #fff; }}
.sick {{ background: #dc2626; color: #fff; }}
.total {{ text-align: center; font-weight: bold; }}
.ok {{ background: #dcfce7; }}
.hours {{ background: #dbeafe; color: #1e3a8a; }}
.legend-title {{ background: #1e3a8a; color: #fff; font-weight: bold; }}
.signature {{ background: #eff6ff; font-weight: bold; text-align: center; height: 24px; }}
.signature-box {{ height: 58px; }}
.note {{ color: #475569; font-style: italic; }}
</style>
</head>
<body>
<table>
<tr><td colspan="{col_count}" class="title">OREZONE TIMESHEET</td></tr>
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
{''.join(rows_html)}
<tr><td colspan="{col_count}"></td></tr>
<tr><td colspan="6" class="legend-title">Legende</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="worked-drilling" bgcolor="#2563eb" style="background-color:#2563eb;color:#ffffff;">12h</td><td colspan="5">Present avec activite drilling = 12H</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="worked-standard" bgcolor="#16a34a" style="background-color:#16a34a;color:#ffffff;">8h</td><td colspan="5">Present sans activite drilling = 8H</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="rest" bgcolor="#cbd5e1" style="background-color:#cbd5e1;color:#172033;">R</td><td colspan="5">Repos planifie</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="absent" bgcolor="#fca5a5" style="background-color:#fca5a5;color:#172033;">A</td><td colspan="5">Absent sur la liste de presence</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="unfilled" bgcolor="#e5e7eb" style="background-color:#e5e7eb;color:#172033;">NR</td><td colspan="5">Statut non renseigne</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="break" bgcolor="#f59e0b" style="background-color:#f59e0b;color:#172033;">B</td><td colspan="5">Break</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="permission" bgcolor="#a855f7" style="background-color:#a855f7;color:#ffffff;">P</td><td colspan="5">Permission</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="sick" bgcolor="#dc2626" style="background-color:#dc2626;color:#ffffff;">S</td><td colspan="5">Sick / Maladie</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td class="legend-title">S1/S2</td><td colspan="5">Chaque semaine TimeSheet est un bloc de 7 jours depuis le 21</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td colspan="{col_count}"></td></tr>
<tr><td colspan="6" class="legend-title">Regles de calcul</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
<tr><td colspan="6" class="note">Une presence sur jour drilling compte 12H. Une presence sur jour sans drilling compte 8H. Break, permission et sick comptent 8H quelle que soit l'activite. Repos, absent et non renseigne comptent 0H. Les heures reelles viennent de la liste de presence.</td><td colspan="{max(col_count - 6, 1)}"></td></tr>
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


def _timesheet_cell_class(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status == "break" and label == "P":
        return "permission"
    if status == "break" and label == "S":
        return "sick"
    return status.replace("_", "-")


def _timesheet_week_class(cell: dict[str, Any]) -> str:
    return "week-start" if cell.get("week_start") else ""


def _timesheet_cell_inline_style(cell: dict[str, Any]) -> dict[str, str]:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    colors = {
        "worked_drilling": ("#2563eb", "#ffffff"),
        "worked_standard": ("#16a34a", "#ffffff"),
        "rest": ("#cbd5e1", "#172033"),
        "absent": ("#fca5a5", "#172033"),
        "unfilled": ("#e5e7eb", "#172033"),
    }
    if status == "break" and label == "P":
        background, text = "#a855f7", "#ffffff"
    elif status == "break" and label == "S":
        background, text = "#dc2626", "#ffffff"
    elif status == "break":
        background, text = "#f59e0b", "#172033"
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
