from __future__ import annotations

from pathlib import Path
from typing import Any

import flet as ft

from app.services import generate_report, get_report_summary, list_employees, list_report_definitions
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


CATEGORY_COLORS = {
    "Presence": PRIMARY,
    "Employes": SUCCESS,
    "Breaks": WARNING,
    "Formations": "#8B5CF6",
    "TimeSheet": PRIMARY,
    "Toolbox": "#0F766E",
    "EPI": SUCCESS,
    "Maintenance": "#475569",
    "Actions": "#EA580C",
    "Alertes": DANGER,
}


def reports_page(show_header: bool = True) -> ft.Control:
    definitions = list_report_definitions()
    summary = get_report_summary()
    employees = list_employees()
    state: dict[str, Any] = {"generated": [], "selected_employee_ids": set()}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    reports_area = ft.ResponsiveRow(spacing=12, run_spacing=12)
    generated_area = ft.Column(spacing=8)

    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=260)
    category_filter = ft.Dropdown(
        label="Categorie",
        value="all",
        width=210,
        options=[ft.dropdown.Option("all", "Toutes")]
        + [ft.dropdown.Option(name, name) for name in summary["category_names"]],
    )
    date_field = ft.TextField(label="Date", value=summary["default_date"], hint_text="AAAA-MM-JJ", width=160)
    month_field = ft.TextField(label="Mois", value=summary["default_month"], hint_text="AAAA-MM", width=140)
    employee_selection_area = ft.Column(spacing=6)
    if employees:
        state["selected_employee_ids"] = {int(employees[0]["id_employe"])}

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def filtered_definitions() -> list[dict[str, Any]]:
        query = str(search_field.value or "").strip().lower()
        category = str(category_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for report in definitions:
            haystack = " ".join(str(report.get(key) or "") for key in ("title", "category", "description")).lower()
            if query and query not in haystack:
                continue
            if category != "all" and str(report.get("category") or "") != category:
                continue
            rows.append(report)
        return rows

    def refresh(event: ft.ControlEvent | None = None) -> None:
        render_summary()
        render_reports()
        render_generated()
        _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        category_filter.value = "all"
        refresh()

    def generate(report: dict[str, Any]) -> None:
        try:
            output = generate_report(
                str(report["key"]),
                {"date": date_field.value, "month": month_field.value, "employee_ids": selected_employee_ids()},
            )
            state["generated"].insert(0, {"report": report["title"], "path": output})
            notify(f"Rapport cree: {output}", SUCCESS)
            render_generated()
        except ValueError as exc:
            notify(str(exc), DANGER)
        except OSError as exc:
            notify(f"Export impossible: ferme le fichier Excel ouvert puis recommence. Detail: {exc}", DANGER)
        _update()

    def generate_category(event: ft.ControlEvent | None = None) -> None:
        rows = filtered_definitions()
        created = 0
        try:
            for report in rows:
                output = generate_report(
                    str(report["key"]),
                    {"date": date_field.value, "month": month_field.value, "employee_ids": selected_employee_ids()},
                )
                state["generated"].insert(0, {"report": report["title"], "path": output})
                created += 1
            notify(f"{created} rapport(s) cree(s).", SUCCESS)
            render_generated()
        except ValueError as exc:
            notify(str(exc), DANGER)
        except OSError as exc:
            notify(f"Export impossible: ferme le fichier Excel ouvert puis recommence. Detail: {exc}", DANGER)
        _update()

    def render_summary() -> None:
        visible = filtered_definitions()
        summary_row.controls = [
            _summary_chip("Rapports", len(visible), PRIMARY, ft.Icons.DESCRIPTION_OUTLINED),
            _summary_chip("Categories", summary["categories"], SUCCESS, ft.Icons.ACCOUNT_TREE_OUTLINED),
            _summary_chip("Generes", len(state["generated"]), WARNING if state["generated"] else MUTED, ft.Icons.FILE_DOWNLOAD_DONE_OUTLINED),
            _summary_chip("Date", date_field.value or "-", PRIMARY, ft.Icons.TODAY_OUTLINED),
            _summary_chip("Mois", month_field.value or "-", PRIMARY, ft.Icons.CALENDAR_MONTH_OUTLINED),
            _summary_chip("Employes", len(employees), SUCCESS, ft.Icons.PEOPLE_ALT_OUTLINED),
            _summary_chip("Selection", len(selected_employee_ids()), WARNING, ft.Icons.CHECKLIST_OUTLINED),
        ]

    def selected_employee_ids() -> list[int]:
        return sorted(int(item) for item in state["selected_employee_ids"])

    def toggle_employee(employee_id: int, selected: bool) -> None:
        selected_ids: set[int] = state["selected_employee_ids"]
        if selected:
            selected_ids.add(employee_id)
        else:
            selected_ids.discard(employee_id)
        render_employee_selection()
        render_summary()
        _update()

    def select_all_employees(selected: bool) -> None:
        if selected:
            state["selected_employee_ids"] = {int(row["id_employe"]) for row in employees}
        else:
            state["selected_employee_ids"] = set()
        render_employee_selection()
        render_summary()
        _update()

    def render_employee_selection() -> None:
        selected_ids = set(selected_employee_ids())
        employee_selection_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Employes TimeSheet", color=TEXT, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{len(selected_ids)} selectionne(s)", color=MUTED, size=12),
                    ft.OutlinedButton("Tous", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=lambda event: select_all_employees(True)),
                    ft.OutlinedButton("Aucun", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=lambda event: select_all_employees(False)),
                ],
                wrap=True,
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        width=260,
                        content=ft.Checkbox(
                            label=f"{_employee_name(row)} - {row.get('numero_badge') or 'sans badge'}",
                            value=int(row["id_employe"]) in selected_ids,
                            on_change=lambda event, current=row: toggle_employee(
                                int(current["id_employe"]),
                                bool(event.control.value),
                            ),
                        ),
                    )
                    for row in employees
                ],
                wrap=True,
                spacing=6,
            )
            if employees
            else ft.Text("Aucun employe actif disponible.", color=MUTED, size=12),
        ]

    def render_reports() -> None:
        rows = filtered_definitions()
        reports_area.controls = [
            ft.Container(
                col={"sm": 12, "md": 6, "lg": 4},
                content=_report_card(report, generate),
            )
            for report in rows
        ]
        if not rows:
            reports_area.controls = [
                ft.Container(
                    col={"sm": 12},
                    bgcolor="#F8FAFC",
                    border=ft.border.all(1, "#E2E8F0"),
                    border_radius=8,
                    padding=16,
                    content=ft.Text("Aucun rapport trouve.", color=MUTED),
                )
            ]

    def render_generated() -> None:
        generated = state["generated"][:8]
        generated_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Derniers fichiers", size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Container(
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=8,
                        padding=10,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, color=PRIMARY, size=18),
                                ft.Text(item["report"], color=TEXT, width=220, weight=ft.FontWeight.BOLD),
                                ft.Text(str(Path(item["path"]).name), color=MUTED, expand=True),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                    for item in generated
                ],
                spacing=8,
            )
            if generated
            else ft.Text("Aucun fichier genere dans cette session.", size=12, color=MUTED),
        ]

    for control in (search_field, category_filter):
        control.on_change = refresh

    controls = [
        module_header(
            "Rapports",
            "Exports QHSE consolides pour presence, employees, formations, TimeSheet, EPI et alertes.",
        )
    ] if show_header else []
    controls.extend(
        [
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                search_field,
                                category_filter,
                                date_field,
                                month_field,
                                ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Filtrer", on_click=refresh),
                                ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_filters),
                                ft.ElevatedButton("Generer la selection", icon=ft.Icons.FILE_DOWNLOAD_OUTLINED, on_click=generate_category),
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.ExpansionTile(
                            title="Selection employes TimeSheet",
                            leading=ft.Icons.PEOPLE_ALT_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[employee_selection_area],
                        ),
                        summary_row,
                    ],
                    spacing=12,
                ),
            ),
            reports_area,
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=generated_area,
            ),
        ]
    )
    root = ft.Column(
        controls=controls,
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    render_employee_selection()
    return root


def _report_card(report: dict[str, Any], generate: Any) -> ft.Control:
    category = str(report.get("category") or "")
    color = CATEGORY_COLORS.get(category, PRIMARY)
    badges = []
    if report.get("date_param"):
        badges.append(("Date", ft.Icons.TODAY_OUTLINED))
    if report.get("month_param"):
        badges.append(("Mois", ft.Icons.CALENDAR_MONTH_OUTLINED))
    if report.get("employee_param"):
        badges.append(("Employe", ft.Icons.PERSON_OUTLINE))
    return ft.Container(
        height=178,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=16,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            bgcolor=_soft_color(color),
                            border_radius=8,
                            padding=7,
                            content=ft.Icon(_category_icon(category), color=color, size=20),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(str(report["title"]), color=TEXT, size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(category, color=color, size=11, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Text(str(report.get("description") or ""), size=12, color=MUTED, max_lines=2),
                ft.Row(
                    controls=[_param_badge(label, icon) for label, icon in badges] or [_param_badge("Instantane", ft.Icons.FLASH_ON_OUTLINED)],
                    spacing=6,
                    wrap=True,
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Generer",
                            icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
                            on_click=lambda event, current=report: generate(current),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=10,
        ),
    )


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _param_badge(label: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=MUTED, size=13),
                ft.Text(label, color=MUTED, size=11),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _category_icon(category: str) -> str:
    return {
        "Presence": ft.Icons.EVENT_AVAILABLE_OUTLINED,
        "Employes": ft.Icons.PEOPLE_ALT_OUTLINED,
        "Breaks": ft.Icons.BEACH_ACCESS_OUTLINED,
        "Formations": ft.Icons.SCHOOL_OUTLINED,
        "TimeSheet": ft.Icons.CALENDAR_MONTH_OUTLINED,
        "Toolbox": ft.Icons.FACT_CHECK_OUTLINED,
        "EPI": ft.Icons.INVENTORY_2_OUTLINED,
        "Maintenance": ft.Icons.HANDYMAN_OUTLINED,
        "Actions": ft.Icons.TASK_ALT_OUTLINED,
        "Alertes": ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,
    }.get(category, ft.Icons.DESCRIPTION_OUTLINED)


def _employee_name(record: dict[str, Any]) -> str:
    if record.get("nom") or record.get("prenom"):
        return f"{record.get('nom') or ''} {record.get('prenom') or ''}".strip()
    return str(record.get("nom_complet") or "-")


def _soft_color(color: str) -> str:
    return {
        PRIMARY: "#DBEAFE",
        SUCCESS: "#DCFCE7",
        DANGER: "#FEE2E2",
        WARNING: "#FEF3C7",
        "#8B5CF6": "#EDE9FE",
        "#0F766E": "#CCFBF1",
        "#475569": "#E2E8F0",
        "#EA580C": "#FFEDD5",
    }.get(color, "#E2E8F0")
