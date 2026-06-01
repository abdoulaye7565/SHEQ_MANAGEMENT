from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    export_rows_xlsx,
    list_active_break_employees,
    return_employees_to_service,
)
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def active_breaks_page() -> ft.Control:
    state: dict[str, Any] = {"records": []}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=12, wrap=True)
    table_area = ft.Column(spacing=12)
    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=280)
    type_filter = ft.Dropdown(
        label="Situation",
        value="all",
        width=180,
        options=[
            ft.dropdown.Option("all", "Toutes"),
            ft.dropdown.Option("break", "Break"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Maladie"),
        ],
    )
    function_filter = ft.Dropdown(label="Fonction", value="all", width=220)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        state["records"] = list_active_break_employees()
        refresh_filter_options()
        render_summary()
        render_table()
        _update()

    def refresh_filter_options() -> None:
        functions = sorted({str(record.get("fonction") or "-") for record in state["records"]})
        function_filter.options = [ft.dropdown.Option("all", "Toutes les fonctions")]
        function_filter.options.extend(ft.dropdown.Option(item, item) for item in functions)
        if function_filter.value not in {"all", *functions}:
            function_filter.value = "all"

    def filtered_records() -> list[dict[str, Any]]:
        query = str(search_field.value or "").strip().lower()
        selected_type = str(type_filter.value or "all")
        selected_function = str(function_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for record in state["records"]:
            searchable = " ".join(
                str(record.get(key) or "")
                for key in ("nom", "prenom", "numero_badge", "fonction", "commentaire")
            ).lower()
            if query and query not in searchable:
                continue
            if selected_type != "all" and str(record.get("type_break") or "") != selected_type:
                continue
            if selected_function != "all" and str(record.get("fonction") or "-") != selected_function:
                continue
            rows.append(record)
        return rows

    def return_one(employee_id: int) -> None:
        try:
            updated = return_employees_to_service([employee_id])
            notify(f"{updated} employe remis en service.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_list(event: ft.ControlEvent | None = None) -> None:
        records = filtered_records()
        output = export_rows_xlsx(
            "liste_employes_en_break_filtree.xlsx",
            "Employes en break",
            ["Nom", "Prenom", "Badge", "Fonction", "Situation", "Debut", "Fin", "Statut", "Commentaire"],
            [
                [
                    record.get("nom") or "",
                    record.get("prenom") or "",
                    record.get("numero_badge") or "",
                    record.get("fonction") or "",
                    _state_text(record.get("type_break")),
                    record.get("date_debut") or "",
                    record.get("date_fin") or "",
                    record.get("statut") or "",
                    record.get("commentaire") or "",
                ]
                for record in records
            ],
        )
        notify(f"Export Excel cree: {output}", SUCCESS)
        _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        type_filter.value = "all"
        function_filter.value = "all"
        render_summary()
        render_table()
        _update()

    def render_summary() -> None:
        records = filtered_records()
        summary_row.controls = [
            _summary_chip("Affiches", len(records), PRIMARY, ft.Icons.FILTER_ALT_OUTLINED),
            _summary_chip("Break", _count_type(records, "break"), WARNING, ft.Icons.BEACH_ACCESS_OUTLINED),
            _summary_chip("Permission", _count_type(records, "permission"), PRIMARY, ft.Icons.EVENT_NOTE_OUTLINED),
            _summary_chip("Maladie", _count_type(records, "sick"), DANGER, ft.Icons.LOCAL_HOSPITAL_OUTLINED),
        ]

    def render_table() -> None:
        records = filtered_records()
        table_area.controls = [
            ft.Row(
                controls=[
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_list),
                    ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Actualiser", on_click=refresh),
                    status,
                ],
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Employe")),
                            ft.DataColumn(ft.Text("Badge")),
                            ft.DataColumn(ft.Text("Fonction")),
                            ft.DataColumn(ft.Text("Situation")),
                            ft.DataColumn(ft.Text("Debut")),
                            ft.DataColumn(ft.Text("Fin")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(f"{record.get('nom') or '-'} {record.get('prenom') or ''}", color=TEXT)),
                                    ft.DataCell(ft.Text(str(record.get("numero_badge") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("fonction") or "-"))),
                                    ft.DataCell(_state_badge(record.get("type_break"))),
                                    ft.DataCell(ft.Text(str(record.get("date_debut") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("date_fin") or "-"))),
                                    ft.DataCell(
                                        ft.OutlinedButton(
                                            "En service",
                                            icon=ft.Icons.WORK_OUTLINE,
                                            on_click=lambda event, current=record: return_one(int(current["employe_id"])),
                                        )
                                    ),
                                ],
                            )
                            for record in records
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
                "Employes en break",
                "Recherche, filtres et retour rapide au service.",
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
                                search_field,
                                type_filter,
                                function_filter,
                                ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Appliquer", on_click=refresh),
                                ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_filters),
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
                padding=18,
                content=table_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    return root


def _count_type(records: list[dict[str, Any]], break_type: str) -> int:
    return sum(1 for record in records if record.get("type_break") == break_type)


def _summary_chip(label: str, value: int, color: str, icon: str) -> ft.Control:
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


def _state_badge(state: str | None) -> ft.Control:
    labels = {
        "break": ("En break", WARNING),
        "permission": ("Permission", PRIMARY),
        "sick": ("Maladie", DANGER),
    }
    label, color = labels.get(str(state or "break"), ("En break", WARNING))
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color),
    )


def _state_text(state: str | None) -> str:
    return {
        "break": "En break",
        "permission": "Permission",
        "sick": "Maladie",
    }.get(str(state or "break"), "En break")

