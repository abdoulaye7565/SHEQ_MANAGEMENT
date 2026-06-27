from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services.monthly_timesheet_service import (
    current_monthly_timesheet_month,
    get_monthly_10h_timesheet,
    list_monthly_timesheet_site_options,
)
from app.services import (
    EmailConfigurationError,
    export_monthly_10h_timesheet_xlsx,
    export_timesheet_annual_history_xls,
    prepare_timesheet_outlook_draft,
    prepare_timesheet_whatsapp_share,
    send_timesheet_email,
    update_timesheet_day_status,
)
from app.services.attendance_export_service import export_sheq_timesheet_xls
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


WORK = "#16A34A"
REST = "#334155"
NORMAL_BREAK = "#F59E0B"
ANNUAL_BREAK = "#A855F7"
PERMISSION = "#F97316"
SICK = "#DC2626"
ABSENT = "#EF4444"
UNFILLED = "#475569"
NOT_ASSIGNED = "#1E293B"
from app.ui.components.dark_styles import BG, BORDER, CARD, FIELD
DARK_TEXT = "#FFFFFF"
DARK_MUTED = "#9DB0C5"
PAGE_SIZE = 10
MONTHLY_DAY_WIDTH = 34
MONTHLY_DAY_HEIGHT = 29


def monthly_timesheet_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"timesheet": None, "page": 0, "view": "dashboard"}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    table_area = ft.Column(spacing=10)
    dashboard_area = ft.Column(spacing=12)
    anomalies_area = ft.Column(spacing=10)
    content_area = ft.Container()
    nav_buttons: dict[str, ft.TextButton] = {}

    month_field = ft.TextField(
        label="Mois courant",
        value=current_monthly_timesheet_month(),
        hint_text="AAAA-MM",
        width=150,
        read_only=True,
    )
    site_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Site", value="all", width=260)
    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=240)
    function_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Fonction", value="all", width=190)
    group_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Groupe", value="all", width=170)
    shift_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Shift", value="all", width=160)
    status_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Statut",
        value="all",
        width=190,
        options=[
            ft.dropdown.Option("all", "Tous les statuts"),
            ft.dropdown.Option("worked", "10h travaille"),
            ft.dropdown.Option("rest", "Repos"),
            ft.dropdown.Option("normal_break", "Break normal"),
            ft.dropdown.Option("annual_break", "Break annuel"),
            ft.dropdown.Option("absent", "Absent"),
            ft.dropdown.Option("unfilled", "Non renseigne"),
        ],
    )
    compact_switch = ft.Switch(label="Affichage compact", value=True, active_color=PRIMARY)
    monthly_edit_employee = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Employe", width=270)
    monthly_edit_date = ft.TextField(label="Date", hint_text="AAAA-MM-JJ", width=170)
    monthly_edit_status = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Statut",
        value="worked",
        width=180,
        options=[
            ft.dropdown.Option("worked", "10h travaille"),
            ft.dropdown.Option("rest", "Repos"),
            ft.dropdown.Option("absent", "Absent"),
            ft.dropdown.Option("normal_break", "Break normal"),
            ft.dropdown.Option("annual_break", "Break annuel"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Sick"),
        ],
    )
    for control in (month_field, site_field, search_field, function_filter, group_filter, shift_filter, status_filter,
                    monthly_edit_employee, monthly_edit_date, monthly_edit_status):
        control.bgcolor = FIELD
        control.color = DARK_TEXT
        control.border_color = BORDER
        control.focused_border_color = PRIMARY
        control.label_style = ft.TextStyle(color=DARK_MUTED)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def selected_site_id() -> int | None:
        value = str(site_field.value or "all")
        return None if value == "all" else int(value)

    def selected_month() -> str:
        return str(month_field.value or current_monthly_timesheet_month())

    def selected_site_label() -> str:
        value = str(site_field.value or "all")
        for option in site_field.options or []:
            if str(option.key) == value:
                return str(option.text or "Tous les sites")
        return "Tous les sites"

    def load_site_options() -> None:
        options = list_monthly_timesheet_site_options()
        current = str(site_field.value or "all")
        values = {str(option["value"]) for option in options}
        site_field.options = [ft.dropdown.Option("all", "Tous les sites")]
        site_field.options.extend(
            ft.dropdown.Option(str(option["value"]), str(option["label"]))
            for option in options
        )
        site_field.value = current if current in {"all", *values} else "all"

    def refresh_filter_options() -> None:
        rows = (state.get("timesheet") or {"rows": []})["rows"]
        for field, key, label in [
            (function_filter, "fonction", "Toutes"),
            (group_filter, "groupe", "Tous"),
            (shift_filter, "shift", "Tous"),
        ]:
            values = sorted({str(row["employee"].get(key) or "-") for row in rows})
            current = str(field.value or "all")
            field.options = [ft.dropdown.Option("all", label)]
            field.options.extend(ft.dropdown.Option(value, value) for value in values)
            field.value = current if current in {"all", *values} else "all"

    def refresh_monthly_edit_options() -> None:
        rows = (state.get("timesheet") or {"rows": []})["rows"]
        employees = [row["employee"] for row in rows]
        current = str(monthly_edit_employee.value or "")
        monthly_edit_employee.options = [
            ft.dropdown.Option(
                str(emp["id_employe"]),
                f"{_employee_name(emp)} — {emp.get('numero_badge') or 'sans badge'}",
            )
            for emp in employees
        ]
        values = {str(emp["id_employe"]) for emp in employees}
        monthly_edit_employee.value = current if current in values else (
            str(employees[0]["id_employe"]) if employees else None
        )
        if monthly_edit_date.value == "":
            timesheet = state.get("timesheet") or {}
            days = timesheet.get("days") or []
            if days:
                monthly_edit_date.value = str(days[0]["date"])

    def save_monthly_correction(event: ft.ControlEvent | None = None) -> None:
        try:
            emp_id = int(monthly_edit_employee.value or 0)
            date_str = str(monthly_edit_date.value or "").strip()
            status_val = str(monthly_edit_status.value or "worked")
            if not emp_id:
                raise ValueError("Choisis un employe.")
            if not date_str:
                raise ValueError("Renseigne une date.")
            update_timesheet_day_status(emp_id, date_str, status_val)
            notify(f"Correction enregistree — statut '{status_val}' pour le {date_str}.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            load_site_options()
            month_field.value = current_monthly_timesheet_month()
            state["page"] = 0
            state["timesheet"] = get_monthly_10h_timesheet(
                current_monthly_timesheet_month(),
                site_id=selected_site_id(),
            )
            refresh_filter_options()
            refresh_monthly_edit_options()
            render()
            notify("TimeSheet 1-25 actualise.", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def export_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_monthly_10h_timesheet_xlsx(
                selected_month(),
                site_id=selected_site_id(),
            )
            notify(f"Export Excel TimeSheet 1-25 cree: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def send_timesheet_by_email(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_monthly_10h_timesheet_xlsx(
                selected_month(),
                site_id=selected_site_id(),
            )
            result = send_timesheet_email(
                "TimeSheet 1-25",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"TimeSheet 1-25 envoye par email a {', '.join(result['recipients'])}.", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def prepare_timesheet_in_outlook(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_monthly_10h_timesheet_xlsx(
                selected_month(),
                site_id=selected_site_id(),
            )
            result = prepare_timesheet_outlook_draft(
                "TimeSheet 1-25",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"Brouillon Outlook prepare pour {', '.join(result['recipients'])}.", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def prepare_timesheet_in_whatsapp(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_monthly_10h_timesheet_xlsx(
                selected_month(),
                site_id=selected_site_id(),
            )
            result = prepare_timesheet_whatsapp_share(
                "TimeSheet 1-25",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"WhatsApp ouvert pour {len(result['targets'])} destinataire(s). Fichier a joindre: {result['attachment']}", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def export_history(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_annual_history_xls(site_id=selected_site_id())
            notify(f"Historique 12 mois des deux TimeSheets exporte: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def export_sheq(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_sheq_timesheet_xls(
                month=selected_month(),
                site_id=selected_site_id(),
            )
            notify(f"Export SHEQ Timesheet cree : {output}", SUCCESS)
        except Exception as exc:
            notify(f"Erreur export SHEQ : {exc}", DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def filtered_rows() -> list[dict[str, Any]]:
        timesheet = state.get("timesheet") or {"rows": []}
        query = str(search_field.value or "").strip().lower()
        selected_status = str(status_filter.value or "all")
        selected_function = str(function_filter.value or "all")
        selected_group = str(group_filter.value or "all")
        selected_shift = str(shift_filter.value or "all")
        rows = []
        for row in timesheet["rows"]:
            employee = row["employee"]
            haystack = " ".join(
                str(employee.get(key) or "")
                for key in ("nom", "prenom", "nom_complet", "numero_badge", "fonction", "site", "groupe")
            ).lower()
            if query and query not in haystack:
                continue
            if selected_function != "all" and str(employee.get("fonction") or "-") != selected_function:
                continue
            if selected_group != "all" and str(employee.get("groupe") or "-") != selected_group:
                continue
            if selected_shift != "all" and str(employee.get("shift") or "-") != selected_shift:
                continue
            if selected_status != "all" and not any(cell.get("status") == selected_status for cell in row["cells"]):
                continue
            rows.append(row)
        return rows

    def apply_filters(event: ft.ControlEvent | None = None) -> None:
        state["page"] = 0
        render()
        try:
            root.update()
        except RuntimeError:
            pass

    def change_page(delta: int) -> None:
        rows = filtered_rows()
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"]) + delta))
        render()
        try:
            root.update()
        except RuntimeError:
            pass

    def render() -> None:
        timesheet = state.get("timesheet") or get_monthly_10h_timesheet(current_monthly_timesheet_month())
        state["timesheet"] = timesheet
        summary = timesheet["summary"]
        synchronization = timesheet.get("synchronization") or {}
        summary_row.controls = [
            _summary_chip("Mois courant", _month_label(timesheet["period"]["month"]), PRIMARY, ft.Icons.CALENDAR_MONTH_OUTLINED),
            _summary_chip(
                "Presence synchronisee",
                f"{synchronization.get('days_with_data', 0)} j / {synchronization.get('validated_days', 0)} valides",
                SUCCESS,
                ft.Icons.SYNC_OUTLINED,
            ),
            _summary_chip("Employes", summary["employees"], PRIMARY, ft.Icons.PEOPLE_ALT_OUTLINED),
            _summary_chip("Jours travailles", summary["worked_days"], SUCCESS, ft.Icons.WORK_OUTLINE),
            _summary_chip("Heures travaillees", f"{summary['hours']} h", SUCCESS, ft.Icons.ACCESS_TIME_OUTLINED),
            _summary_chip("Break normal", summary["normal_break_days"], WARNING, ft.Icons.BEACH_ACCESS_OUTLINED),
            _summary_chip("Permission", summary.get("permission_days", 0), PERMISSION, ft.Icons.EVENT_NOTE_OUTLINED),
            _summary_chip("Absents", summary.get("absent_days", 0), DANGER, ft.Icons.PERSON_OFF_OUTLINED),
            _summary_chip("Repos dimanche", summary.get("rest_days", 0), REST, ft.Icons.WEEKEND_OUTLINED),
        ]
        rows = filtered_rows()
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"])))
        start = int(state["page"]) * PAGE_SIZE
        page_rows = rows[start : start + PAGE_SIZE]
        columns = [
            ft.DataColumn(ft.Text("Employe")),
            ft.DataColumn(ft.Text("Fonction")),
            *[
                ft.DataColumn(
                    ft.Column(
                        controls=[
                            ft.Text(str(day["day"]), size=11, weight=ft.FontWeight.BOLD),
                            ft.Text(str(day["weekday"]), size=10, color=DARK_MUTED),
                        ],
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
                for day in timesheet["days"]
            ],
            ft.DataColumn(ft.Text("Total jours")),
            ft.DataColumn(ft.Text("Heures")),
        ]
        table_area.controls = [
            ft.Row(
                controls=[
                    _legend("10h", WORK, "#FFFFFF"),
                    _legend("R dimanche", REST, TEXT),
                    _legend("Break normal", NORMAL_BREAK, TEXT),
                    _legend("Permission", PERMISSION, "#FFFFFF"),
                    _legend("Sick", SICK, "#FFFFFF"),
                    _legend("Annual leave", ANNUAL_BREAK, "#FFFFFF"),
                    _legend("Absent", ABSENT, "#FFFFFF"),
                    _legend("NR", UNFILLED, TEXT),
                    _legend("N/A site", NOT_ASSIGNED, MUTED),
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
                        bgcolor=FIELD,
                        border=ft.border.all(1, BORDER),
                        border_radius=8,
                        content=ft.Text(f"Page {int(state['page']) + 1}/{max_page + 1}", size=12, color=DARK_TEXT),
                    ),
                    ft.OutlinedButton(
                        "Suivant",
                        icon=ft.Icons.ARROW_FORWARD,
                        disabled=int(state["page"]) >= max_page,
                        on_click=lambda event: change_page(1),
                    ),
                    status,
                ],
                spacing=8,
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
                                    ft.DataCell(
                                        _employee_identity(row["employee"])
                                    ),
                                    ft.DataCell(ft.Text(str(row["employee"].get("fonction") or "-"), color=DARK_MUTED)),
                                    *[
                                        ft.DataCell(_day_cell(cell))
                                        for cell in row["cells"]
                                    ],
                                    ft.DataCell(ft.Text(str(row["worked_days"]), color=DARK_TEXT, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(f"{row['hours']}h", color="#38BDF8", weight=ft.FontWeight.BOLD)),
                                ],
                            )
                            for row in page_rows
                        ],
                        bgcolor=FIELD,
                        border=ft.border.all(1, BORDER),
                        border_radius=8,
                        heading_row_color="#142B45",
                        data_row_min_height=36 if compact_switch.value else 44,
                        data_row_max_height=40 if compact_switch.value else 52,
                        column_spacing=5,
                        horizontal_margin=8,
                        horizontal_lines=ft.BorderSide(1, BORDER),
                        vertical_lines=ft.BorderSide(1, BORDER),
                        heading_text_style=ft.TextStyle(size=10, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                        data_text_style=ft.TextStyle(size=10, color=DARK_MUTED),
                        data_row_color={
                            ft.ControlState.HOVERED: "#142B45",
                            ft.ControlState.PRESSED: "#17304A",
                            ft.ControlState.SELECTED: "#123B46",
                        },
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]
        render_dashboard(timesheet)
        render_anomalies(timesheet)
        render_view()

    def render_dashboard(timesheet: dict[str, Any]) -> None:
        dashboard_area.controls = [
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        col={"xs": 12, "lg": 9},
                        content=_dark_panel("Indicateurs de la periode", [summary_row]),
                    ),
                    ft.Container(
                        col={"xs": 12, "lg": 3},
                        content=_quick_actions_panel(
                            export_excel,
                            send_timesheet_by_email,
                            prepare_timesheet_in_whatsapp,
                            prepare_timesheet_in_outlook,
                            export_history,
                        ),
                    ),
                ],
                spacing=12,
                run_spacing=12,
            ),
            filters_panel,
            _dark_panel("Matrice TimeSheet 01 - 25", [table_area]),
        ]

    def render_anomalies(timesheet: dict[str, Any]) -> None:
        anomalies_area.controls = [
            _dark_panel("Anomalies et donnees a completer", _monthly_alert_controls(timesheet))
        ]

    def set_view(view: str) -> None:
        state["view"] = view
        render_view()
        try:
            root.update()
        except RuntimeError:
            pass

    def render_view() -> None:
        view = str(state["view"])
        for key, button in nav_buttons.items():
            selected = key == view
            button.style = ft.ButtonStyle(
                color="#FFFFFF" if selected else DARK_MUTED,
                bgcolor=PRIMARY if selected else FIELD,
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        content_area.content = views[view]

    compact_switch.on_change = apply_filters
    filters_panel = _dark_panel(
        "Recherche et filtres",
        [
            ft.Row(
                controls=[
                    search_field,
                    function_filter,
                    group_filter,
                    shift_filter,
                    status_filter,
                    ft.ElevatedButton("Filtres avances", icon=ft.Icons.FILTER_ALT_OUTLINED, on_click=apply_filters),
                    compact_switch,
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ],
    )
    validation_view = _dark_panel(
        "Validation du TimeSheet",
        [
            *_monthly_alert_controls(state.get("timesheet") or get_monthly_10h_timesheet()),
            ft.Text(
                "La validation finale doit etre effectuee apres correction des absences et jours non renseignes.",
                color=DARK_MUTED,
                size=10,
            ),
        ],
    )
    configuration_view = ft.Column(
        controls=[
            _dark_panel(
                "Parametres du TimeSheet 01 - 25",
                [
                    _distribution_line("Regle quotidienne", "10 heures", WORK),
                    _distribution_line("Periode", "01 au 25 du mois courant", PRIMARY),
                    _distribution_line("Repos automatique", "Dimanche sans presence", REST),
                    _distribution_line("Source principale", "Liste de presence synchronisee", SUCCESS),
                ],
            ),
            _dark_panel(
                "Correction manuelle d'un statut employe",
                [
                    ft.Text(
                        "Permet de corriger un statut pour un employe et un jour specifique "
                        "lorsque la source presence est incorrecte ou incomplete.",
                        size=11,
                        color=DARK_MUTED,
                    ),
                    ft.Row(
                        controls=[
                            monthly_edit_employee,
                            monthly_edit_date,
                            monthly_edit_status,
                            ft.ElevatedButton(
                                "Corriger",
                                icon=ft.Icons.SAVE_OUTLINED,
                                on_click=save_monthly_correction,
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Text(
                        "Note : la correction cree un override persistant. Le prochain rechargement refletera le changement.",
                        size=10,
                        color=DARK_MUTED,
                        italic=True,
                    ),
                ],
            ),
        ],
        spacing=12,
    )
    history_view = _dark_panel(
        "Historique annuel",
        [
            ft.Text("Telecharge les deux types de TimeSheet sur les douze derniers mois.", color=DARK_MUTED, size=10),
            ft.ElevatedButton("Telecharger historique 12 mois", icon=ft.Icons.HISTORY_OUTLINED, on_click=export_history),
        ],
    )
    views = {
        "dashboard": dashboard_area,
        "matrix": dashboard_area,
        "anomalies": anomalies_area,
        "validation": validation_view,
        "history": history_view,
        "configuration": configuration_view,
    }
    for key, label, icon in [
        ("dashboard", "Vue d'ensemble", ft.Icons.DASHBOARD_OUTLINED),
        ("matrix", "Matrice TimeSheet", ft.Icons.GRID_VIEW_OUTLINED),
        ("anomalies", "Anomalies", ft.Icons.WARNING_AMBER_OUTLINED),
        ("validation", "Validation", ft.Icons.VERIFIED_OUTLINED),
        ("history", "Historique", ft.Icons.HISTORY_OUTLINED),
        ("configuration", "Configuration", ft.Icons.SETTINGS_OUTLINED),
    ]:
        nav_buttons[key] = ft.TextButton(label, icon=icon, on_click=lambda event, target=key: set_view(target))
    root = ft.Container(
        bgcolor=BG,
        expand=True,
        padding=12,
        content=ft.Column(
            controls=[
                _monthly_header(
                    month_field,
                    site_field,
                    refresh,
                    export_excel,
                    send_timesheet_by_email,
                    prepare_timesheet_in_outlook,
                    prepare_timesheet_in_whatsapp,
                    export_history,
                    lambda event: set_view("validation"),
                    export_sheq=export_sheq,
                ),
                ft.Container(
                    bgcolor=CARD,
                    border=ft.border.all(1, BORDER),
                    border_radius=8,
                    padding=8,
                    content=ft.Row(controls=list(nav_buttons.values()), spacing=6, wrap=True),
                ),
                status,
                content_area,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
    load_site_options()
    refresh()
    return root


def _day_cell(cell: dict[str, Any]) -> ft.Control:
    color, text_color, tooltip = _cell_style(cell)
    return ft.Container(
        width=MONTHLY_DAY_WIDTH,
        height=MONTHLY_DAY_HEIGHT,
        alignment=ft.Alignment(0, 0),
        bgcolor=color,
        border_radius=4,
        tooltip=tooltip,
        content=ft.Text(str(cell["label"]), size=10, color=text_color, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
    )


def _cell_style(cell: dict[str, Any]) -> tuple[str, str, str]:
    status = str(cell.get("status") or "")
    break_period = _break_period(cell)
    if status == "worked":
        return WORK, "#FFFFFF", "Jour travaille: 10H"
    if status == "normal_break":
        return NORMAL_BREAK, TEXT, f"Break normal{break_period}"
    if status == "permission":
        return PERMISSION, "#FFFFFF", f"Permission{break_period}"
    if status == "sick":
        return SICK, "#FFFFFF", f"Sick leave{break_period}"
    if status == "annual_break":
        return ANNUAL_BREAK, "#FFFFFF", f"Break annuel / leave{break_period}"
    if status == "absent":
        return ABSENT, "#FFFFFF", "Absent"
    if status == "unfilled":
        return UNFILLED, TEXT, "Non renseigne"
    if status == "not_assigned":
        return NOT_ASSIGNED, MUTED, "Non affecte a ce site"
    return REST, TEXT, "Repos dimanche"


def _break_period(cell: dict[str, Any]) -> str:
    start = str(cell.get("break_start") or "")
    end = str(cell.get("break_end") or "")
    if not start or not end:
        return ""
    return f" du {start} au {end}"


def _employee_name(employee: dict[str, Any]) -> str:
    if employee.get("nom") or employee.get("prenom"):
        return f"{employee.get('nom') or ''} {employee.get('prenom') or ''}".strip()
    return str(employee.get("nom_complet") or "-")


def _employee_identity(employee: dict[str, Any]) -> ft.Control:
    name = _employee_name(employee)
    initials = "".join(part[0] for part in name.split()[:2] if part) or "?"
    return ft.Row(
        controls=[
            ft.Container(
                width=30,
                height=30,
                bgcolor=PRIMARY,
                border_radius=15,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(initials.upper(), color="#FFFFFF", size=9, weight=ft.FontWeight.BOLD),
            ),
            ft.Column(
                controls=[
                    ft.Text(name, color=DARK_TEXT, size=10, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"{employee.get('numero_badge') or 'sans badge'} | {employee.get('site') or '-'}",
                        color=DARK_MUTED,
                        size=8,
                    ),
                ],
                spacing=0,
            ),
        ],
        spacing=6,
    )


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    bgcolor=color,
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color="#FFFFFF", size=22),
                ),
                ft.Column(
                    controls=[
                        ft.Text(label, color=DARK_MUTED, size=10),
                        ft.Text(str(value), color=DARK_TEXT, size=20, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=0,
                ),
            ],
            spacing=9,
        ),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _legend(label: str, color: str, text_color: str) -> ft.Control:
    return ft.Container(
        bgcolor=color,
        border=ft.border.all(1, BORDER),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=9, vertical=5),
        content=ft.Text(label, color=text_color, size=11, weight=ft.FontWeight.BOLD),
    )


def _dark_panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[ft.Text(title, color=DARK_TEXT, size=15, weight=ft.FontWeight.BOLD), *controls],
            spacing=11,
        ),
    )


def _week_bar(label: str, value: float, maximum: float) -> ft.Control:
    height = max(16, int(130 * value / maximum)) if maximum else 16
    return ft.Column(
        controls=[
            ft.Text(str(round(value)), color=DARK_TEXT, size=10, weight=ft.FontWeight.BOLD),
            ft.Container(width=54, height=height, bgcolor=WORK, border_radius=6),
            ft.Text(label, color=DARK_MUTED, size=9),
        ],
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.END,
    )


def _distribution_line(label: str, value: Any, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=9,
        content=ft.Row(
            controls=[
                ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                ft.Text(label, color=DARK_MUTED, size=10, expand=True),
                ft.Text(str(value), color=DARK_TEXT, size=11, weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        ),
    )


def _monthly_alert_controls(timesheet: dict[str, Any]) -> list[ft.Control]:
    summary = timesheet["summary"]
    missing_badges = sum(1 for row in timesheet["rows"] if not row["employee"].get("numero_badge"))
    alerts = [
        ("Jours non renseignes", summary.get("unfilled_days", 0), DANGER),
        ("Absences enregistrees", summary.get("absent_days", 0), DANGER),
        ("Employes sans badge", missing_badges, WARNING),
        ("Permissions", summary.get("permission_days", 0), WARNING),
        ("Sick leave", summary.get("sick_days", 0), DANGER),
    ]
    controls = [
        _distribution_line(label, value, color)
        for label, value, color in alerts
        if int(value or 0) > 0
    ]
    return controls or [ft.Text("Aucune anomalie critique detectee.", color=SUCCESS, size=11)]


def _monthly_header(
    month_field: ft.TextField,
    site_field: ft.Dropdown,
    refresh: Any,
    export_excel: Any,
    email: Any,
    outlook: Any,
    whatsapp: Any,
    history: Any,
    validation: Any,
    export_sheq: Any = None,
) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("TimeSheet 1-25", color=DARK_TEXT, size=20, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                ft.Text(
                                    f"Periode en cours : 01 - 25 {_month_label(str(month_field.value or current_monthly_timesheet_month()))}",
                                    color=DARK_MUTED,
                                    size=10,
                                ),
                                ft.Container(
                                    bgcolor="#064E3B",
                                    border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                    content=ft.Text("En cours", color=SUCCESS, size=9, weight=ft.FontWeight.BOLD),
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=2,
                    width=280,
                ),
                site_field,
                ft.OutlinedButton("Synchroniser presence", icon=ft.Icons.SYNC_OUTLINED, on_click=refresh),
                ft.IconButton(icon=ft.Icons.MAIL_OUTLINED, tooltip="Envoyer par email", icon_color=DARK_TEXT, on_click=email),
                ft.PopupMenuButton(
                    icon=ft.Icons.DOWNLOAD_OUTLINED,
                    tooltip="Exports et partage",
                    items=[
                        ft.PopupMenuItem(content=ft.Text("Exporter Excel"), on_click=export_excel),
                        ft.PopupMenuItem(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.SHIELD_OUTLINED, size=14, color="#F59E0B"),
                                    ft.Text("Exporter SHEQ (01-25)", color="#F59E0B"),
                                ],
                                spacing=6,
                            ),
                            on_click=export_sheq,
                        ),
                        ft.PopupMenuItem(content=ft.Text("Envoyer par email"), on_click=email),
                        ft.PopupMenuItem(content=ft.Text("Preparer dans Outlook"), on_click=outlook),
                        ft.PopupMenuItem(content=ft.Text("Preparer dans WhatsApp"), on_click=whatsapp),
                        ft.PopupMenuItem(content=ft.Text("Historique 12 mois"), on_click=history),
                    ],
                ),
                ft.ElevatedButton("Valider TimeSheet", icon=ft.Icons.LOCK_OUTLINE, on_click=validation),
            ],
            spacing=10,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _quick_actions_panel(
    export_excel: Any,
    email: Any,
    whatsapp: Any,
    outlook: Any,
    history: Any,
) -> ft.Control:
    return _dark_panel(
        "Actions rapides",
        [
            ft.ResponsiveRow(
                controls=[
                    _quick_action("Exporter Excel", ft.Icons.TABLE_VIEW_OUTLINED, SUCCESS, export_excel),
                    _quick_action("Envoyer email", ft.Icons.MAIL_OUTLINED, PRIMARY, email),
                    _quick_action("WhatsApp", ft.Icons.CHAT_OUTLINED, SUCCESS, whatsapp),
                    _quick_action("Outlook", ft.Icons.OUTBOX_OUTLINED, PRIMARY, outlook),
                    _quick_action("Historique", ft.Icons.HISTORY_OUTLINED, ANNUAL_BREAK, history),
                ],
                spacing=8,
                run_spacing=8,
            )
        ],
    )


def _quick_action(label: str, icon: str, color: str, callback: Any) -> ft.Control:
    return ft.Container(
        col={"xs": 6, "sm": 4, "lg": 6},
        bgcolor=FIELD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=8,
        on_click=callback,
        ink=True,
        content=ft.Column(
            controls=[
                ft.Icon(icon, color=color, size=22),
                ft.Text(label, color=DARK_TEXT, size=9, text_align=ft.TextAlign.CENTER),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _month_label(value: str) -> str:
    year, month = str(value).split("-", 1)
    months = {
        "01": "Janvier",
        "02": "Fevrier",
        "03": "Mars",
        "04": "Avril",
        "05": "Mai",
        "06": "Juin",
        "07": "Juillet",
        "08": "Aout",
        "09": "Septembre",
        "10": "Octobre",
        "11": "Novembre",
        "12": "Decembre",
    }
    return f"{months.get(month, month)} {year}"
