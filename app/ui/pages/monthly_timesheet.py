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
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


WORK = "#16A34A"
REST = "#CBD5E1"
NORMAL_BREAK = "#F59E0B"
ANNUAL_BREAK = "#A855F7"
NOT_ASSIGNED = "#F8FAFC"


def monthly_timesheet_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"timesheet": None}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=8, wrap=True)
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

    def render() -> None:
        timesheet = state.get("timesheet") or get_monthly_10h_timesheet(current_monthly_timesheet_month())
        state["timesheet"] = timesheet
        summary = timesheet["summary"]
        summary_row.controls = [
            _summary_chip("Employes", summary["employees"], PRIMARY, ft.Icons.PEOPLE_ALT_OUTLINED),
            _summary_chip("Jours travailles", summary["worked_days"], SUCCESS, ft.Icons.WORK_OUTLINE),
            _summary_chip("Repos dimanche", summary["rest_days"], MUTED, ft.Icons.WEEKEND_OUTLINED),
            _summary_chip("Break normal", summary["normal_break_days"], WARNING, ft.Icons.BEACH_ACCESS_OUTLINED),
            _summary_chip("Break annuel", summary["annual_break_days"], PRIMARY, ft.Icons.EVENT_AVAILABLE_OUTLINED),
            _summary_chip("Heures", summary["hours"], SUCCESS, ft.Icons.ACCESS_TIME_OUTLINED),
        ]
        rows = filtered_rows()
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
                    _legend("Break annuel", ANNUAL_BREAK, "#FFFFFF"),
                    _legend("N/A site", NOT_ASSIGNED, MUTED),
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
                            for row in rows
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
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
        width=34,
        height=28,
        alignment=ft.Alignment(0, 0),
        bgcolor=color,
        border_radius=4,
        tooltip=tooltip,
        content=ft.Text(str(cell["label"]), size=10, color=text_color, weight=ft.FontWeight.BOLD),
    )


def _cell_style(cell: dict[str, Any]) -> tuple[str, str, str]:
    status = str(cell.get("status") or "")
    break_period = _break_period(cell)
    if status == "worked":
        return WORK, "#FFFFFF", "Jour travaille: 10H"
    if status == "normal_break":
        return NORMAL_BREAK, TEXT, f"Break normal{break_period}"
    if status == "annual_break":
        return ANNUAL_BREAK, "#FFFFFF", f"Break annuel / leave{break_period}"
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
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=15),
                ft.Text(label, color=MUTED, size=11),
                ft.Text(str(value), color=TEXT, size=12, weight=ft.FontWeight.BOLD),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _legend(label: str, color: str, text_color: str) -> ft.Control:
    return ft.Container(
        bgcolor=color,
        border=ft.border.all(1, "#CBD5E1"),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=9, vertical=5),
        content=ft.Text(label, color=text_color, size=11, weight=ft.FontWeight.BOLD),
    )

