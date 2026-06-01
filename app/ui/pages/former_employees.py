from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import export_rows_xlsx, list_former_employees, restore_employee
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def former_employees_page() -> ft.Control:
    state: dict[str, Any] = {"records": []}
    status = ft.Text("", size=12, color=MUTED)
    table_area = ft.Column(spacing=10)
    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=280)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        state["records"] = list_former_employees(search_field.value or "")
        render_table()
        _update()

    def restore(record: dict[str, Any]) -> None:
        try:
            restore_employee(int(record["id_employe"]))
            notify("Employe reintegre dans la liste active.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_list(event: ft.ControlEvent | None = None) -> None:
        output = export_rows_xlsx(
            "anciens_employes.xlsx",
            "Anciens employes",
            ["Matricule", "Nom", "Prenom", "Badge", "Fonction", "Site", "Motif", "Date sortie", "Commentaire"],
            [
                [
                    row.get("matricule") or "",
                    row.get("nom") or row.get("nom_complet") or "",
                    row.get("prenom") or "",
                    row.get("numero_badge") or "",
                    row.get("fonction") or "",
                    row.get("site") or "",
                    _departure_label(row.get("departure_type")),
                    row.get("departure_date") or "",
                    row.get("departure_comment") or "",
                ]
                for row in state["records"]
            ],
        )
        notify(f"Export Excel cree: {output}", SUCCESS)
        _update()

    def render_table() -> None:
        rows = state["records"]
        table_area.controls = [
            ft.Row(
                controls=[
                    search_field,
                    ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Rechercher", on_click=refresh),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_list),
                    status,
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(f"{len(rows)} ancien(s) employe(s)", size=12, color=MUTED),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Employe")),
                            ft.DataColumn(ft.Text("Badge")),
                            ft.DataColumn(ft.Text("Fonction")),
                            ft.DataColumn(ft.Text("Site")),
                            ft.DataColumn(ft.Text("Motif")),
                            ft.DataColumn(ft.Text("Date sortie")),
                            ft.DataColumn(ft.Text("Commentaire")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(
                                        ft.Column(
                                            controls=[
                                                ft.Text(_employee_name(row), color=TEXT, weight=ft.FontWeight.BOLD),
                                                ft.Text(str(row.get("matricule") or "-"), size=11, color=MUTED),
                                            ],
                                            spacing=1,
                                        )
                                    ),
                                    ft.DataCell(ft.Text(str(row.get("numero_badge") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("fonction") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("site") or "-"))),
                                    ft.DataCell(_departure_badge(row.get("departure_type"))),
                                    ft.DataCell(ft.Text(str(row.get("departure_date") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("departure_comment") or "-"))),
                                    ft.DataCell(
                                        ft.IconButton(
                                            icon=ft.Icons.RESTORE_OUTLINED,
                                            tooltip="Reintegrer",
                                            icon_color=SUCCESS,
                                            on_click=lambda event, current=row: restore(current),
                                        )
                                    ),
                                ]
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
            module_header("Anciens employes", "Historique des employes licencies, demissionnaires ou sortis."),
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
    refresh()
    return root


def _employee_name(record: dict[str, Any]) -> str:
    if record.get("nom") or record.get("prenom"):
        return f"{record.get('nom') or ''} {record.get('prenom') or ''}".strip()
    return str(record.get("nom_complet") or "-")


def _departure_label(value: Any) -> str:
    return {
        "licencie": "Licencie",
        "demissionne": "Demissionne",
        "autre": "Autre sortie",
    }.get(str(value or ""), "-")


def _departure_badge(value: Any) -> ft.Control:
    color = {
        "licencie": DANGER,
        "demissionne": WARNING,
        "autre": PRIMARY,
    }.get(str(value or ""), MUTED)
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(_departure_label(value), size=12, color=color),
    )

