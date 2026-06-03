from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services.monthly_timesheet_service import (
    current_monthly_timesheet_month,
    get_monthly_10h_timesheet,
    list_monthly_timesheet_site_options,
)
from app.services import export_monthly_10h_timesheet_xlsx
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


WORK = "#16A34A"
REST = "#CBD5E1"
NORMAL_BREAK = "#F59E0B"
ANNUAL_BREAK = "#A855F7"
PERMISSION = "#F97316"
SICK = "#DC2626"
ABSENT = "#EF4444"
UNFILLED = "#E5E7EB"
NOT_ASSIGNED = "#F8FAFC"
PAGE_SIZE = 10
MONTHLY_DAY_WIDTH = 28
MONTHLY_DAY_HEIGHT = 24


def monthly_timesheet_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"timesheet": None, "page": 0}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    table_area = ft.Column(spacing=10)

    month_field = ft.TextField(
        label="Mois",
        value=current_monthly_timesheet_month(),
        hint_text="AAAA-MM",
        width=150,
    )
    site_field = ft.Dropdown(label="Site", value="all", width=260)
    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=240)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def selected_site_id() -> int | None:
        value = str(site_field.value or "all")
        return None if value == "all" else int(value)

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

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            load_site_options()
            state["page"] = 0
            state["timesheet"] = get_monthly_10h_timesheet(
                str(month_field.value or ""),
                site_id=selected_site_id(),
            )
            render()
            notify("TimeSheet 1-25 actualise.", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def export_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_monthly_10h_timesheet_xlsx(
                str(month_field.value or ""),
                site_id=selected_site_id(),
            )
            notify(f"Export Excel TimeSheet 1-25 cree: {output}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        try:
            root.update()
        except RuntimeError:
            pass

    def filtered_rows() -> list[dict[str, Any]]:
        timesheet = state.get("timesheet") or {"rows": []}
        query = str(search_field.value or "").strip().lower()
        rows = []
        for row in timesheet["rows"]:
            employee = row["employee"]
            haystack = " ".join(
                str(employee.get(key) or "")
                for key in ("nom", "prenom", "nom_complet", "numero_badge", "fonction", "site", "groupe")
            ).lower()
            if query and query not in haystack:
                continue
            rows.append(row)
        return rows

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
        summary_row.controls = [
            _summary_chip("Employes", summary["employees"], PRIMARY, ft.Icons.PEOPLE_ALT_OUTLINED),
            _summary_chip("Jours travailles", summary["worked_days"], SUCCESS, ft.Icons.WORK_OUTLINE),
            _summary_chip("Repos dimanche", summary["rest_days"], MUTED, ft.Icons.WEEKEND_OUTLINED),
            _summary_chip("Break normal", summary["normal_break_days"], WARNING, ft.Icons.BEACH_ACCESS_OUTLINED),
            _summary_chip("Permission", summary.get("permission_days", 0), WARNING, ft.Icons.EVENT_NOTE_OUTLINED),
            _summary_chip("Break annuel", summary["annual_break_days"], PRIMARY, ft.Icons.EVENT_AVAILABLE_OUTLINED),
            _summary_chip("Absents", summary.get("absent_days", 0), DANGER, ft.Icons.PERSON_OFF_OUTLINED),
            _summary_chip("Heures", summary["hours"], SUCCESS, ft.Icons.ACCESS_TIME_OUTLINED),
        ]
        rows = filtered_rows()
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"])))
        start = int(state["page"]) * PAGE_SIZE
        page_rows = rows[start : start + PAGE_SIZE]
        columns = [
            ft.DataColumn(ft.Text("Employe")),
            *[
                ft.DataColumn(
                    ft.Column(
                        controls=[
                            ft.Text(str(day["day"]), size=11, weight=ft.FontWeight.BOLD),
                            ft.Text(str(day["weekday"]), size=10, color=MUTED),
                        ],
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
                for day in timesheet["days"]
            ],
            ft.DataColumn(ft.Text("Total")),
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
                                        ft.Column(
                                            controls=[
                                                ft.Text(_employee_name(row["employee"]), color=TEXT, weight=ft.FontWeight.BOLD),
                                                ft.Text(
                                                    f"{row['employee'].get('numero_badge') or 'sans badge'} | {row['employee'].get('site') or '-'}",
                                                    size=10,
                                                    color=MUTED,
                                                ),
                                            ],
                                            spacing=1,
                                        )
                                    ),
                                    *[
                                        ft.DataCell(_day_cell(cell))
                                        for cell in row["cells"]
                                    ],
                                    ft.DataCell(ft.Text(str(row["hours"]), weight=ft.FontWeight.BOLD, color=TEXT)),
                                ],
                            )
                            for row in page_rows
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                        data_row_min_height=38,
                        data_row_max_height=44,
                        column_spacing=5,
                        horizontal_margin=8,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    root = ft.Column(
        controls=[
            module_header(
                "TimeSheet 1-25",
                "TimeSheet mensuel 10H par jour travaille, repos dimanche et couleurs break normal / break annuel.",
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
                                site_field,
                                search_field,
                                ft.ElevatedButton("Actualiser", icon=ft.Icons.SYNC_OUTLINED, on_click=refresh),
                                ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_excel),
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
                content=table_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
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


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _legend(label: str, color: str, text_color: str) -> ft.Control:
    return ft.Container(
        bgcolor=color,
        border=ft.border.all(1, "#CBD5E1"),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=9, vertical=5),
        content=ft.Text(label, color=text_color, size=11, weight=ft.FontWeight.BOLD),
    )
