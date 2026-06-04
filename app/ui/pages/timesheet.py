from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    current_timesheet_month,
    export_timesheet_audit_xlsx,
    export_timesheet_all_employees_xls,
    export_timesheet_annual_history_xls,
    export_timesheet_employee_xls,
    export_timesheet_xls,
    EmailConfigurationError,
    get_day_activity,
    get_timesheet,
    list_timesheet_audit,
    list_timesheet_history,
    list_timesheet_site_options,
    lock_timesheet_month,
    prepare_timesheet_outlook_draft,
    set_day_activity,
    set_day_activity_range,
    send_timesheet_email,
    unlock_timesheet_month,
    update_timesheet_day_status,
)
from app.ui.components.feedback import show_feedback
from app.ui.components.confirm import confirm_action
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


WORK_DRILLING = "#2563EB"
WORK_STANDARD = "#16A34A"
HOLIDAY = "#22C55E"
REST = "#CBD5E1"
ABSENT = "#FCA5A5"
UNFILLED = "#E5E7EB"
BREAK = "#F59E0B"
PERMISSION = "#A855F7"
SICK = "#DC2626"
PAGE_SIZE = 10
TIMESHEET_DAY_WIDTH = 34
TIMESHEET_DAY_HEIGHT = 28


def timesheet_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"timesheet": None, "history": [], "active": True, "page": 0}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    calendar_area = ft.Column(spacing=10)
    history_area = ft.Column(spacing=8)
    audit_area = ft.Column(spacing=8)
    validation_area = ft.Column(spacing=6)

    month_field = ft.TextField(
        label="Mois TimeSheet",
        value=current_timesheet_month(),
        hint_text="AAAA-MM",
        width=160,
    )
    site_scope_field = ft.Dropdown(label="TimeSheet site", value="all", width=250)
    activity_date_field = ft.TextField(label="Date activite", hint_text="AAAA-MM-JJ", width=170)
    drilling_switch = ft.Switch(label="Drilling actif", value=False, active_color=PRIMARY)
    day_type_field = ft.Dropdown(
        label="Type de jour",
        value="work",
        width=190,
        options=[
            ft.dropdown.Option("work", "Jour travaille"),
            ft.dropdown.Option("holiday", "Jour chome 8H"),
        ],
    )
    comment_field = ft.TextField(label="Commentaire", width=260)
    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=240)
    function_filter = ft.Dropdown(label="Fonction", value="all", width=220)
    status_filter = ft.Dropdown(
        label="Statut",
        value="all",
        width=180,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("worked_drilling", "12H drilling"),
            ft.dropdown.Option("worked_standard", "8H"),
            ft.dropdown.Option("holiday", "Jour chome 8H"),
            ft.dropdown.Option("rest", "Repos"),
            ft.dropdown.Option("absent", "Absent"),
            ft.dropdown.Option("unfilled", "Non renseigne"),
            ft.dropdown.Option("break", "Break"),
            ft.dropdown.Option("annual", "Annual leave"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Sick"),
        ],
    )
    week_filter = ft.Dropdown(label="Semaine", value="all", width=140)
    site_filter = ft.Dropdown(label="Site", value="all", width=160)
    group_filter = ft.Dropdown(label="Groupe", value="all", width=180)
    shift_filter = ft.Dropdown(label="Shift", value="all", width=150)
    badge_filter = ft.Dropdown(
        label="Badge",
        value="all",
        width=160,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("with_badge", "Avec badge"),
            ft.dropdown.Option("without_badge", "Sans badge"),
        ],
    )
    bulk_start_field = ft.TextField(label="Debut drilling", hint_text="AAAA-MM-JJ", width=170)
    bulk_end_field = ft.TextField(label="Fin drilling", hint_text="AAAA-MM-JJ", width=170)
    bulk_drilling_switch = ft.Switch(label="Drilling", value=True, active_color=PRIMARY)
    bulk_day_type_field = ft.Dropdown(
        label="Type periode",
        value="work",
        width=190,
        options=[
            ft.dropdown.Option("work", "Jours travailles"),
            ft.dropdown.Option("holiday", "Jours chomes 8H"),
        ],
    )
    edit_employee_field = ft.Dropdown(label="Employe", width=260)
    edit_date_field = ft.TextField(label="Date", hint_text="AAAA-MM-JJ", width=170)
    edit_status_field = ft.Dropdown(
        label="Statut",
        value="present",
        width=170,
        options=[
            ft.dropdown.Option("present", "Present"),
            ft.dropdown.Option("rest", "Repos"),
            ft.dropdown.Option("absent", "Absent"),
            ft.dropdown.Option("break", "Break"),
            ft.dropdown.Option("annual", "Annual leave"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Sick"),
        ],
    )

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color
        show_feedback(page, message, color)

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def selected_month() -> str:
        return str(month_field.value or "").strip()

    def selected_site_id() -> int | None:
        value = str(site_scope_field.value or "all")
        return None if value == "all" else int(value)

    def selected_site_label() -> str:
        value = str(site_scope_field.value or "all")
        for option in site_scope_field.options or []:
            if str(option.key) == value:
                return str(option.text or "Tous les sites")
        return "Tous les sites"

    def load_site_scope_options() -> None:
        options = list_timesheet_site_options()
        current = str(site_scope_field.value or "all")
        values = {str(option["value"]) for option in options}
        site_scope_field.options = [ft.dropdown.Option("all", "Tous les sites")]
        site_scope_field.options.extend(
            ft.dropdown.Option(str(option["value"]), str(option["label"]))
            for option in options
        )
        site_scope_field.value = current if current in {"all", *values} else "all"

    def refresh(event: ft.ControlEvent | None = None, automatic: bool = False) -> None:
        try:
            load_site_scope_options()
            state["timesheet"] = get_timesheet(selected_month(), site_id=selected_site_id())
            state["history"] = list_timesheet_history()
            days = state["timesheet"]["days"]
            if days and not activity_date_field.value and not automatic:
                activity_date_field.value = days[0]["date"]
                edit_date_field.value = days[0]["date"]
                bulk_start_field.value = days[0]["date"]
                bulk_end_field.value = days[0]["date"]
                load_activity()
            refresh_edit_options()
            refresh_filter_options()
            render()
            notify(
                "TimeSheet actualise automatiquement depuis la liste de presence."
                if automatic
                else "TimeSheet actualise depuis la liste de presence.",
                SUCCESS,
            )
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def refresh_filter_options() -> None:
        timesheet = state.get("timesheet") or {"rows": [], "week_labels": []}
        functions = sorted({str(row["employee"].get("fonction") or "-") for row in timesheet["rows"]})
        current_function = str(function_filter.value or "all")
        function_filter.options = [ft.dropdown.Option("all", "Toutes les fonctions")]
        function_filter.options.extend(ft.dropdown.Option(item, item) for item in functions)
        function_filter.value = current_function if current_function in {"all", *functions} else "all"

        weeks = list(timesheet.get("week_labels") or [])
        current_week = str(week_filter.value or "all")
        week_filter.options = [ft.dropdown.Option("all", "Toutes")]
        week_filter.options.extend(ft.dropdown.Option(item, item) for item in weeks)
        week_filter.value = current_week if current_week in {"all", *weeks} else "all"

        filter_specs = [
            (site_filter, "site", "Tous les sites"),
            (group_filter, "groupe", "Tous les groupes"),
            (shift_filter, "shift_code", "Tous les shifts"),
        ]
        for field, key, label in filter_specs:
            values = sorted({str(row["employee"].get(key) or "-") for row in timesheet["rows"]})
            current_value = str(field.value or "all")
            field.options = [ft.dropdown.Option("all", label)]
            field.options.extend(
                ft.dropdown.Option(value, _shift_label(value) if key == "shift_code" else value)
                for value in values
            )
            field.value = current_value if current_value in {"all", *values} else "all"

    def refresh_edit_options() -> None:
        timesheet = state.get("timesheet") or {"rows": []}
        employees = [
            row["employee"]
            for row in timesheet["rows"]
        ]
        current = str(edit_employee_field.value or "")
        edit_employee_field.options = [
            ft.dropdown.Option(
                str(employee["id_employe"]),
                f"{_employee_name(employee)} - {employee.get('numero_badge') or 'sans badge'}",
            )
            for employee in employees
        ]
        values = {str(employee["id_employe"]) for employee in employees}
        edit_employee_field.value = current if current in values else (
            str(employees[0]["id_employe"]) if employees else None
        )

    def load_activity(event: ft.ControlEvent | None = None) -> None:
        try:
            activity = get_day_activity(str(activity_date_field.value or ""))
            drilling_switch.value = bool(activity["has_drilling"])
            day_type_field.value = str(activity.get("day_type") or "work")
            comment_field.value = str(activity.get("commentaire") or "")
            notify("Activite du jour chargee.", MUTED)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def save_activity(event: ft.ControlEvent | None = None) -> None:
        try:
            set_day_activity(
                str(activity_date_field.value or ""),
                bool(drilling_switch.value),
                str(comment_field.value or ""),
                day_type=str(day_type_field.value or "work"),
            )
            notify("Activite du jour mise a jour. Le TimeSheet est recalcule.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_bulk_activity(event: ft.ControlEvent | None = None) -> None:
        try:
            updated = set_day_activity_range(
                str(bulk_start_field.value or ""),
                str(bulk_end_field.value or ""),
                bool(bulk_drilling_switch.value),
                str(comment_field.value or ""),
                day_type=str(bulk_day_type_field.value or "work"),
            )
            notify(f"{updated} jour(s) d'activite mis a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_timesheet_edit(event: ft.ControlEvent | None = None) -> None:
        try:
            update_timesheet_day_status(
                int(edit_employee_field.value or 0),
                str(edit_date_field.value or ""),
                str(edit_status_field.value or ""),
            )
            notify("Modification enregistree. Le TimeSheet est recalcule depuis les donnees source.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            timesheet = get_timesheet(selected_month(), site_id=selected_site_id())
            output = export_timesheet_xls(selected_month(), site_id=selected_site_id())
            notify(f"Export Excel TimeSheet complet: {len(timesheet['rows'])} employe(s) exporte(s) - {output}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def send_timesheet_by_email(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_xls(selected_month(), site_id=selected_site_id())
            result = send_timesheet_email(
                "TimeSheet 21-20",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"TimeSheet envoye par email a {', '.join(result['recipients'])}.", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        _update()

    def prepare_timesheet_in_outlook(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_xls(selected_month(), site_id=selected_site_id())
            result = prepare_timesheet_outlook_draft(
                "TimeSheet 21-20",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"Brouillon Outlook prepare pour {', '.join(result['recipients'])}.", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        _update()

    def export_employee_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            employee_id = int(edit_employee_field.value or 0)
            output = export_timesheet_employee_xls(selected_month(), employee_id)
            employee_label = edit_employee_field.value or employee_id
            notify(f"Export Excel TimeSheet individuel cree pour {employee_label}: {output}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def export_all_employee_excels(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_all_employees_xls(selected_month())
            notify(f"Exports TimeSheet individuels crees pour tous les employes: {output}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def export_audit(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_audit_xlsx(selected_month())
            notify(f"Export audit TimeSheet cree: {output}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def export_annual_history(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_annual_history_xls(site_id=selected_site_id())
            notify(f"Historique annuel TimeSheet exporte: {output}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def lock_month(event: ft.ControlEvent | None = None) -> None:
        confirm_action(
            page,
            "Verrouiller le TimeSheet",
            f"Le TimeSheet {selected_month()} sera verrouille. Les modifications directes seront bloquees.",
            _lock_month,
            confirm_label="Verrouiller",
        )

    def _lock_month() -> None:
        try:
            lock_timesheet_month(selected_month(), commentaire=str(comment_field.value or ""))
            notify("TimeSheet verrouille.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def unlock_month(event: ft.ControlEvent | None = None) -> None:
        confirm_action(
            page,
            "Deverrouiller le TimeSheet",
            f"Le TimeSheet {selected_month()} redeviendra modifiable.",
            _unlock_month,
            confirm_label="Deverrouiller",
            danger=True,
        )

    def _unlock_month() -> None:
        try:
            unlock_timesheet_month(selected_month(), commentaire=str(comment_field.value or ""))
            notify("TimeSheet deverrouille.", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def open_history(month: str) -> None:
        month_field.value = month
        activity_date_field.value = ""
        refresh()

    def dispose() -> None:
        state["active"] = False

    def render() -> None:
        timesheet = state.get("timesheet")
        if not timesheet:
            return
        render_summary(timesheet)
        render_calendar(timesheet)
        render_history()
        render_validation(timesheet)
        render_audit()

    def render_summary(timesheet: dict[str, Any]) -> None:
        summary = timesheet["summary"]
        period = timesheet["period"]
        summary_row.controls = [
            _summary_chip("Mois TimeSheet", period["month"], PRIMARY, ft.Icons.CALENDAR_MONTH_OUTLINED),
            _summary_chip("Periode", f"{period['start']} au {period['end']}", PRIMARY, ft.Icons.DATE_RANGE_OUTLINED),
            _summary_chip("Employes", summary["employees"], PRIMARY, ft.Icons.GROUP_OUTLINED),
            _summary_chip("Jours travailles", summary["worked_days"], SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _summary_chip("Repos", summary["rest_days"], MUTED, ft.Icons.EVENT_BUSY_OUTLINED),
            _summary_chip("Absents", summary.get("absent_days", 0), DANGER, ft.Icons.PERSON_OFF_OUTLINED),
            _summary_chip("Non renseignes", summary.get("unfilled_days", 0), WARNING, ft.Icons.HELP_OUTLINE),
            _summary_chip("Break", summary["break_days"], WARNING, ft.Icons.FREE_BREAKFAST_OUTLINED),
            _summary_chip("Permission", summary.get("permission_days", 0), PRIMARY, ft.Icons.EVENT_NOTE_OUTLINED),
            _summary_chip("Sick", summary.get("sick_days", 0), DANGER, ft.Icons.HEALING_OUTLINED),
            _summary_chip("Heures 12H", summary.get("drilling_hours", 0), PRIMARY, ft.Icons.ACCESS_TIME_OUTLINED),
            _summary_chip("Heures 8H", summary.get("standard_hours", 0), SUCCESS, ft.Icons.ACCESS_TIME_OUTLINED),
            _summary_chip("Heures", summary["hours"], PRIMARY, ft.Icons.ACCESS_TIME_OUTLINED),
            _summary_chip("Heures reelles", summary.get("actual_hours", 0), WARNING, ft.Icons.TIMER_OUTLINED),
        ]

    def render_calendar(timesheet: dict[str, Any]) -> None:
        days = timesheet["days"]
        rows = filtered_rows(timesheet)
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"])))
        start = int(state["page"]) * PAGE_SIZE
        page_rows = rows[start : start + PAGE_SIZE]
        columns = [
            ft.DataColumn(ft.Text("Employe")),
            ft.DataColumn(ft.Text("Badge")),
            ft.DataColumn(ft.Text("Fonction")),
            *[
                ft.DataColumn(_day_header(day))
                for day in days
            ],
            ft.DataColumn(ft.Text("JT")),
            ft.DataColumn(ft.Text("Repos")),
            ft.DataColumn(ft.Text("Break")),
            ft.DataColumn(ft.Text("Heures")),
            ft.DataColumn(ft.Text("H. reelles")),
        ]

        calendar_area.controls = [
            ft.Row(
                controls=[
                    _legend("12h drilling", WORK_DRILLING, "#FFFFFF"),
                    _legend("8h sans drilling", WORK_STANDARD, "#FFFFFF"),
                    _legend("Jour chome 8h", HOLIDAY, "#FFFFFF"),
                    _legend("Repos", REST, TEXT),
                    _legend("Absent", ABSENT, TEXT),
                    _legend("Non renseigne", UNFILLED, TEXT),
                    _legend("Break", BREAK, TEXT),
                    _legend("Permission", PERMISSION, "#FFFFFF"),
                    _legend("Sick", SICK, "#FFFFFF"),
                    _legend("Debut semaine", "#1E3A8A", "#FFFFFF"),
                    ft.Text(
                        f"{start + 1 if rows else 0}-{start + len(page_rows)} / {len(rows)} employe(s)",
                        size=12,
                        color=MUTED,
                    ),
                    ft.OutlinedButton(
                        "Precedent",
                        icon=ft.Icons.ARROW_BACK,
                        disabled=int(state["page"]) <= 0,
                        on_click=lambda event: change_page(-1),
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=6),
                        bgcolor="#EFF6FF",
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        content=ft.Text(f"Page {int(state['page']) + 1}/{max_page + 1}", size=12, color=TEXT),
                    ),
                    ft.OutlinedButton(
                        "Suivant",
                        icon=ft.Icons.ARROW_FORWARD,
                        disabled=int(state["page"]) >= max_page,
                        on_click=lambda event: change_page(1),
                    ),
                    status,
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=columns,
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(_employee_name(row["employee"]), color=TEXT, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row["employee"].get("numero_badge") or "-"))),
                                    ft.DataCell(ft.Text(str(row["employee"].get("fonction") or "-"))),
                                    *[
                                        ft.DataCell(_calendar_cell(cell, int(row["employee"]["id_employe"]), quick_edit_status))
                                        for cell in row["cells"]
                                    ],
                                    ft.DataCell(ft.Text(str(row["worked_days"]), color=SUCCESS, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row["rest_days"]), color=MUTED)),
                                    ft.DataCell(ft.Text(str(row["break_days"]), color=WARNING, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row["hours"]), color=PRIMARY, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row.get("actual_hours", 0)), color=WARNING, weight=ft.FontWeight.BOLD)),
                                ]
                            )
                            for row in page_rows
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                        data_row_min_height=42,
                        data_row_max_height=48,
                        column_spacing=6,
                        horizontal_margin=8,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    def change_page(delta: int) -> None:
        rows = filtered_rows(state.get("timesheet") or {"rows": []})
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"]) + delta))
        render_calendar(state["timesheet"])
        _update()

    def filtered_rows(timesheet: dict[str, Any]) -> list[dict[str, Any]]:
        query = str(search_field.value or "").strip().lower()
        selected_function = str(function_filter.value or "all")
        selected_status = str(status_filter.value or "all")
        selected_week = str(week_filter.value or "all")
        selected_site = str(site_filter.value or "all")
        selected_group = str(group_filter.value or "all")
        selected_shift = str(shift_filter.value or "all")
        selected_badge = str(badge_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for row in timesheet["rows"]:
            employee = row["employee"]
            haystack = " ".join(
                str(employee.get(key) or "")
                for key in ("nom", "prenom", "nom_complet", "numero_badge", "fonction")
            ).lower()
            cells = row["cells"]
            if selected_week != "all":
                cells = [cell for cell in cells if f"S{cell.get('week_index')}" == selected_week]
            if query and query not in haystack:
                continue
            if selected_function != "all" and str(employee.get("fonction") or "-") != selected_function:
                continue
            if selected_site != "all" and str(employee.get("site") or "-") != selected_site:
                continue
            if selected_group != "all" and str(employee.get("groupe") or "-") != selected_group:
                continue
            if selected_shift != "all" and str(employee.get("shift_code") or "-") != selected_shift:
                continue
            if selected_badge == "with_badge" and not employee.get("numero_badge"):
                continue
            if selected_badge == "without_badge" and employee.get("numero_badge"):
                continue
            if selected_status != "all":
                if selected_status in {"permission", "sick"}:
                    if not any(cell["status"] == "break" and cell["label"].lower() == selected_status[0] for cell in cells):
                        continue
                elif selected_status == "annual":
                    if not any(cell["status"] == "break" and cell["label"] == "AL" for cell in cells):
                        continue
                elif selected_status == "break":
                    if not any(cell["status"] == "break" and cell["label"] == "B" for cell in cells):
                        continue
                elif not any(cell["status"] == selected_status for cell in cells):
                    continue
            rows.append(row)
        return rows

    def quick_edit_status(employee_id: int, day: str, status_value: str) -> None:
        edit_employee_field.value = str(employee_id)
        edit_date_field.value = day
        edit_status_field.value = status_value
        save_timesheet_edit()

    def refresh_filtered(event: ft.ControlEvent | None = None) -> None:
        state["page"] = 0
        render_calendar(state["timesheet"])
        _update()

    def render_history() -> None:
        history_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Historique des TimeSheets", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.OutlinedButton(
                        "Telecharger 12 mois",
                        icon=ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED,
                        on_click=export_annual_history,
                    ),
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.OutlinedButton(
                        item["label"],
                        icon=ft.Icons.HISTORY_OUTLINED,
                        on_click=lambda event, month=item["month"]: open_history(month),
                    )
                    for item in state["history"]
                ],
                wrap=True,
                spacing=8,
            )
            if state["history"]
            else ft.Text("Aucun historique disponible.", size=12, color=MUTED),
        ]

    def render_validation(timesheet: dict[str, Any]) -> None:
        lock = timesheet.get("lock")
        validation = timesheet.get("validation") or {"issues": [], "blocking": [], "warnings": []}
        validation_area.controls = [
            ft.Row(
                controls=[
                    _status_chip(
                        "Verrouille" if lock else "Modifiable",
                        SUCCESS if lock else WARNING,
                        ft.Icons.LOCK_OUTLINE if lock else ft.Icons.LOCK_OPEN_OUTLINED,
                    ),
                    ft.Text(
                        f"{len(validation['blocking'])} bloquant(s), {len(validation['warnings'])} alerte(s)",
                        size=12,
                        color=DANGER if validation["blocking"] else MUTED,
                    ),
                    ft.ElevatedButton("Verrouiller", icon=ft.Icons.LOCK_OUTLINE, disabled=bool(lock), on_click=lock_month),
                    ft.OutlinedButton("Deverrouiller", icon=ft.Icons.LOCK_OPEN_OUTLINED, disabled=not bool(lock), on_click=unlock_month),
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Text(str(issue.get("message") or ""), size=12, color=WARNING)
                    for issue in validation["issues"][:6]
                ],
                spacing=3,
            )
            if validation["issues"]
            else ft.Text("Validation OK pour les controles TimeSheet.", size=12, color=SUCCESS),
        ]

    def render_audit() -> None:
        rows = list_timesheet_audit(selected_month(), limit=12)
        audit_area.controls = [
            ft.Text("Audit TimeSheet", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{row['changed_at']} - {row.get('date_presence') or row.get('action')}: "
                        f"{row.get('nom') or ''} {row.get('prenom') or ''} "
                        f"{row.get('ancienne_valeur') or '-'} -> {row.get('nouvelle_valeur') or '-'}",
                        size=12,
                        color=MUTED,
                    )
                    for row in rows
                ],
                spacing=4,
            )
            if rows
            else ft.Text("Aucune modification auditee pour ce mois.", size=12, color=MUTED),
        ]

    root = ft.Column(
        controls=[
            module_header(
                "TimeSheet",
                "Calendrier des heures travaillees du 21 au 20, calcule depuis la liste de presence.",
            ),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                month_field,
                                site_scope_field,
                                ft.ElevatedButton("Actualiser", icon=ft.Icons.SYNC_OUTLINED, on_click=refresh),
                                ft.PopupMenuButton(
                                    content=ft.OutlinedButton("Exports", icon=ft.Icons.DOWNLOAD_OUTLINED),
                                    items=[
                                        ft.PopupMenuItem(
                                            content=ft.Text("TimeSheet complet Excel"),
                                            on_click=export_excel,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("Envoyer TimeSheet par email"),
                                            on_click=send_timesheet_by_email,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("Preparer dans Outlook"),
                                            on_click=prepare_timesheet_in_outlook,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("TimeSheet individuel Excel"),
                                            on_click=export_employee_excel,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("Tous les individuels Excel"),
                                            on_click=export_all_employee_excels,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("Exporter audit"),
                                            on_click=export_audit,
                                        ),
                                    ],
                                ),
                                _summary_chip("Source", "Presence", SUCCESS, ft.Icons.AUTORENEW_OUTLINED),
                                status,
                            ],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.ExpansionTile(
                            title="Filtres",
                            leading=ft.Icons.FILTER_ALT_OUTLINED,
                            expanded=True,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[
                                ft.Row(
                                    controls=[
                                        search_field,
                                        function_filter,
                                        status_filter,
                                        week_filter,
                                        site_filter,
                                        group_filter,
                                        shift_filter,
                                        badge_filter,
                                        ft.ElevatedButton("Appliquer", icon=ft.Icons.FILTER_ALT_OUTLINED, on_click=refresh_filtered),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                )
                            ],
                        ),
                        ft.ExpansionTile(
                            title="Activite drilling",
                            leading=ft.Icons.DATE_RANGE_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[
                                ft.Row(
                                    controls=[
                                        activity_date_field,
                                        drilling_switch,
                                        day_type_field,
                                        comment_field,
                                        ft.OutlinedButton("Charger jour", icon=ft.Icons.TODAY_OUTLINED, on_click=load_activity),
                                        ft.ElevatedButton("Enregistrer jour", icon=ft.Icons.SAVE_OUTLINED, on_click=save_activity),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    controls=[
                                        bulk_start_field,
                                        bulk_end_field,
                                        bulk_drilling_switch,
                                        bulk_day_type_field,
                                        ft.OutlinedButton("Appliquer periode", icon=ft.Icons.DATE_RANGE_OUTLINED, on_click=save_bulk_activity),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                        ),
                        ft.ExpansionTile(
                            title="Modification manuelle",
                            leading=ft.Icons.EDIT_CALENDAR_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[
                                ft.Row(
                                    controls=[
                                        edit_employee_field,
                                        edit_date_field,
                                        edit_status_field,
                                        ft.ElevatedButton("Modifier", icon=ft.Icons.SAVE_OUTLINED, on_click=save_timesheet_edit),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                )
                            ],
                        ),
                        ft.ExpansionTile(
                            title="Validation",
                            leading=ft.Icons.VERIFIED_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[validation_area],
                        ),
                        summary_row,
                    ],
                    spacing=14,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=calendar_area,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=history_area,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=audit_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    root.data = {"dispose": dispose}
    refresh()
    return root


def _employee_name(employee: dict[str, Any]) -> str:
    if employee.get("nom") or employee.get("prenom"):
        return f"{employee.get('nom') or ''} {employee.get('prenom') or ''}".strip()
    return str(employee.get("nom_complet") or "-")


def _calendar_cell(cell: dict[str, Any], employee_id: int, on_status_change: object) -> ft.Control:
    color, text_color, tooltip = _cell_style(cell)
    content = ft.Container(
        width=TIMESHEET_DAY_WIDTH,
        height=TIMESHEET_DAY_HEIGHT,
        bgcolor=color,
        border=ft.border.only(
            left=ft.BorderSide(3 if cell.get("week_start") else 1, "#1E3A8A" if cell.get("week_start") else "#94A3B8"),
            right=ft.BorderSide(1, "#94A3B8"),
            top=ft.BorderSide(1, "#94A3B8"),
            bottom=ft.BorderSide(1, "#94A3B8"),
        ),
        border_radius=4,
        alignment=ft.Alignment(0, 0),
        tooltip=tooltip,
        content=ft.Text(str(cell["label"]), size=10, color=text_color, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
    )
    return ft.PopupMenuButton(
        content=content,
        tooltip=f"{tooltip} - cliquer pour modifier",
        items=[
            ft.PopupMenuItem(content=ft.Text("Present"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "present")),
            ft.PopupMenuItem(content=ft.Text("Repos"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "rest")),
            ft.PopupMenuItem(content=ft.Text("Absent"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "absent")),
            ft.PopupMenuItem(content=ft.Text("Break"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "break")),
            ft.PopupMenuItem(content=ft.Text("Annual leave"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "annual")),
            ft.PopupMenuItem(content=ft.Text("Permission"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "permission")),
            ft.PopupMenuItem(content=ft.Text("Sick"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "sick")),
        ],
    )


def _cell_style(cell: dict[str, Any]) -> tuple[str, str, str]:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status == "worked_drilling":
        return WORK_DRILLING, "#FFFFFF", "Present avec activite drilling: 12H"
    if status == "worked_standard":
        return WORK_STANDARD, "#FFFFFF", "Present sans drilling: 8H"
    if status == "holiday":
        return HOLIDAY, "#FFFFFF", "Jour ferie ou chome paye: 8H"
    if status == "break" and label == "P":
        return PERMISSION, "#FFFFFF", "Permission"
    if status == "break" and label == "S":
        return SICK, "#FFFFFF", "Sick / Maladie"
    if status == "break" and label == "AL":
        return "#5B3DB6", "#FFFFFF", "Annual leave"
    if status == "break":
        return BREAK, TEXT, "Break"
    if status == "absent":
        return ABSENT, TEXT, "Absent"
    if status == "unfilled":
        return UNFILLED, TEXT, "Non renseigne"
    if status == "not_assigned":
        return "#F8FAFC", MUTED, "Non affecte a ce site"
    return REST, TEXT, "Repos"


def _break_color(label: str) -> str:
    return {"B": BREAK, "P": PERMISSION, "S": SICK, "AL": "#5B3DB6"}.get(label, BREAK)


def _shift_label(shift_code: str) -> str:
    return {"DAY": "Day Shift", "NIGHT": "Night Shift", "BREAK": "Break"}.get(shift_code, shift_code)


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _status_chip(label: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=7),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=18),
                ft.Text(label, color=color, weight=ft.FontWeight.BOLD, size=12),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _legend(label: str, color: str, text_color: str) -> ft.Control:
    return ft.Container(
        bgcolor=color,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
        content=ft.Text(label, size=12, color=text_color, weight=ft.FontWeight.BOLD),
    )


def _day_header(day: dict[str, Any]) -> ft.Control:
    activity_color = WORK_DRILLING if day["has_drilling"] else WORK_STANDARD
    return ft.Container(
        width=TIMESHEET_DAY_WIDTH,
        padding=ft.padding.symmetric(horizontal=2, vertical=3),
        bgcolor="#EFF6FF" if int(day["week_index"]) % 2 else "#F8FAFC",
        border=ft.border.only(
            left=ft.BorderSide(3 if day.get("week_start") else 1, "#1E3A8A" if day.get("week_start") else "#BFDBFE"),
            right=ft.BorderSide(1, "#BFDBFE"),
            top=ft.BorderSide(1, "#BFDBFE"),
            bottom=ft.BorderSide(1, "#BFDBFE"),
        ),
        border_radius=4,
        content=ft.Column(
            controls=[
                ft.Text(f"S{day['week_index']}", size=10, color=PRIMARY, weight=ft.FontWeight.BOLD),
                ft.Text(str(day["day"]), size=11, color=TEXT, weight=ft.FontWeight.BOLD),
                ft.Text(day["weekday"], size=9, color=MUTED),
                ft.Text("12h" if day["has_drilling"] else "8h", size=9, color=activity_color, weight=ft.FontWeight.BOLD),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
