from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import export_rows_xlsx, list_former_employees, restore_employee
from app.ui.components.module_header import module_header
from app.ui.components.pagination import PAGE_SIZE, pagination_row
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING

_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"
_DK_TRACK  = "#1A3050"


def former_employees_page() -> ft.Control:
    state: dict[str, Any] = {"records": [], "page": 0}
    status = ft.Text("", size=12, color=_DK_MUTED)
    table_area = ft.Column(spacing=10)
    search_field = ft.TextField(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Recherche", prefix_icon=ft.Icons.SEARCH, width=280)

    def notify(message: str, color: str = _DK_MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        state["page"] = 0
        try:
            state["records"] = list_former_employees(search_field.value or "")
            render_table()
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def restore(record: dict[str, Any]) -> None:
        try:
            restore_employee(int(record["id_employe"]))
            notify("Employe reintegre dans la liste active.", SUCCESS)
            refresh()
        except Exception as exc:
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
        all_rows = state["records"]
        total = len(all_rows)
        max_page = max(0, (total - 1) // PAGE_SIZE) if total else 0
        state["page"] = max(0, min(max_page, state["page"]))
        start = state["page"] * PAGE_SIZE
        rows = all_rows[start : start + PAGE_SIZE]

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
            ft.Text(f"{total} ancien(s) employe(s)", size=12, color=_DK_MUTED),
        ]
        if not all_rows:
            table_area.controls.append(
                _empty_state(
                    ft.Icons.PEOPLE_OUTLINE,
                    "Aucun employé archivé",
                    "Les employés quittant l'entreprise apparaîtront ici.",
                )
            )
        else:
            table_area.controls.append(
                ft.Container(
                    bgcolor=_DK_CARD,
                    content=ft.Row(
                        scroll=ft.ScrollMode.AUTO,
                        controls=[
                            professional_data_table(
                                columns=[
                                    ft.DataColumn(ft.Text("Employe", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                    ft.DataColumn(ft.Text("Badge", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                    ft.DataColumn(ft.Text("Fonction", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                    ft.DataColumn(ft.Text("Site", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                    ft.DataColumn(ft.Text("Motif", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                    ft.DataColumn(ft.Text("Date sortie", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                    ft.DataColumn(ft.Text("Commentaire", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                    ft.DataColumn(ft.Text("Actions", style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD))),
                                ],
                                rows=[
                                    ft.DataRow(
                                        cells=[
                                            ft.DataCell(
                                                ft.Column(
                                                    controls=[
                                                        ft.Text(_employee_name(row), color=_DK_TEXT, weight=ft.FontWeight.BOLD),
                                                        ft.Text(str(row.get("matricule") or "-"), size=11, color=_DK_MUTED),
                                                    ],
                                                    spacing=1,
                                                )
                                            ),
                                            ft.DataCell(ft.Text(str(row.get("numero_badge") or "-"), color=_DK_TEXT)),
                                            ft.DataCell(ft.Text(str(row.get("fonction") or "-"), color=_DK_TEXT)),
                                            ft.DataCell(ft.Text(str(row.get("site") or "-"), color=_DK_TEXT)),
                                            ft.DataCell(_departure_badge(row.get("departure_type"))),
                                            ft.DataCell(ft.Text(str(row.get("departure_date") or "-"), color=_DK_TEXT)),
                                            ft.DataCell(ft.Text(str(row.get("departure_comment") or "-"), color=_DK_TEXT)),
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
                                border=ft.border.all(1, _DK_BORDER),
                                border_radius=8,
                                heading_row_color=_DK_HEAD,
                                bgcolor=_DK_CARD,
                                data_row_color={
                                    ft.ControlState.DEFAULT: _DK_CARD,
                                    ft.ControlState.HOVERED: _DK_CARD2,
                                },
                                horizontal_lines=ft.BorderSide(1, _DK_BORDER),
                                heading_text_style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD),
                                data_text_style=ft.TextStyle(color=_DK_TEXT),
                            )
                        ],
                    ),
                )
            )
            table_area.controls.append(
                pagination_row(
                    current_page=state["page"],
                    max_page=max_page,
                    total=total,
                    shown_start=start + 1 if rows else 0,
                    shown_end=start + len(rows),
                    item_label="employe(s)",
                    on_prev=lambda: (state.__setitem__("page", state["page"] - 1), render_table(), _update()),
                    on_next=lambda: (state.__setitem__("page", state["page"] + 1), render_table(), _update()),
                    on_page=lambda p: (state.__setitem__("page", p), render_table(), _update()),
                )
            )

    root = ft.Column(
        controls=[
            module_header("Anciens employes", "Historique des employes licencies, demissionnaires ou sortis."),
            ft.Container(
                bgcolor=_DK_CARD,
                border=ft.border.all(1, _DK_BORDER),
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
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _empty_state(icon: str, title: str, subtitle: str = "") -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=24, vertical=40),
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            controls=[
                ft.Container(
                    width=64, height=64,
                    bgcolor=_DK_HEAD,
                    border_radius=32,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color=_DK_MUTED, size=28),
                ),
                ft.Text(title, color=_DK_TEXT, size=15, weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(subtitle, color=_DK_MUTED, size=12,
                        text_align=ft.TextAlign.CENTER) if subtitle else ft.Container(),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
    )


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
    }.get(str(value or ""), _DK_MUTED)
    return ft.Container(
        bgcolor=_DK_CARD2,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(_departure_label(value), size=12, color=color),
    )
