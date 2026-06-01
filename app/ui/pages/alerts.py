from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    create_manual_alert,
    delete_manual_alert,
    export_rows_xlsx,
    get_alert_filter_options,
    get_alert_summary,
    list_alerts,
    update_manual_alert_status,
)
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


LEVEL_COLORS = {
    "bas": SUCCESS,
    "moyen": PRIMARY,
    "haut": WARNING,
    "critique": DANGER,
}


def alerts_page(navigate: Any | None = None) -> ft.Control:
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=8, wrap=True)
    table_area = ft.Column(spacing=10)
    source_area = ft.Row(spacing=8, wrap=True)

    options = get_alert_filter_options()
    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=260)
    source_filter = ft.Dropdown(
        label="Source",
        value="all",
        width=210,
        options=[ft.dropdown.Option(row["value"], row["label"]) for row in options["sources"]],
    )
    level_filter = ft.Dropdown(
        label="Niveau",
        value="all",
        width=170,
        options=[ft.dropdown.Option(row["value"], row["label"]) for row in options["levels"]],
    )
    status_filter = ft.Dropdown(
        label="Statut",
        value="ouverte",
        width=170,
        options=[ft.dropdown.Option(row["value"], row["label"]) for row in options["statuses"]],
    )

    manual_type_field = ft.TextField(label="Type d'alerte", width=220)
    manual_level_field = ft.Dropdown(
        label="Niveau",
        value="moyen",
        width=150,
        options=[
            ft.dropdown.Option("bas", "Bas"),
            ft.dropdown.Option("moyen", "Moyen"),
            ft.dropdown.Option("haut", "Haut"),
            ft.dropdown.Option("critique", "Critique"),
        ],
    )
    manual_message_field = ft.TextField(label="Message", multiline=True, min_lines=2, max_lines=3, expand=True)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def current_rows() -> list[dict[str, Any]]:
        return list_alerts(
            source=str(source_filter.value or "all"),
            niveau=str(level_filter.value or "all"),
            statut=str(status_filter.value or "ouverte"),
            search=str(search_field.value or ""),
        )

    def refresh(event: ft.ControlEvent | None = None) -> None:
        render_summary()
        render_sources()
        render_table()
        _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        source_filter.value = "all"
        level_filter.value = "all"
        status_filter.value = "ouverte"
        refresh()

    def save_manual_alert(event: ft.ControlEvent | None = None) -> None:
        try:
            create_manual_alert(
                manual_type_field.value,
                manual_message_field.value,
                str(manual_level_field.value or "moyen"),
            )
            manual_type_field.value = ""
            manual_message_field.value = ""
            notify("Alerte manuelle creee.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def close_manual(alert_id: str, new_status: str) -> None:
        try:
            update_manual_alert_status(_manual_id(alert_id), new_status)
            notify("Statut d'alerte mis a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def remove_manual(alert_id: str) -> None:
        try:
            delete_manual_alert(_manual_id(alert_id))
            notify("Alerte supprimee.", MUTED)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_alerts(event: ft.ControlEvent | None = None) -> None:
        rows = current_rows()
        output = export_rows_xlsx(
            "alertes_qhse_filtrees.xlsx",
            "Alertes QHSE",
            ["Date", "Source", "Type", "Niveau", "Statut", "Reference", "Message", "Action"],
            [
                [
                    row.get("date_creation") or "",
                    row.get("source") or "",
                    row.get("type_alerte") or "",
                    row.get("niveau_label") or "",
                    row.get("statut") or "",
                    row.get("reference_label") or "",
                    row.get("message") or "",
                    row.get("action_hint") or "",
                ]
                for row in rows
            ],
        )
        notify(f"Export Excel cree: {output}", SUCCESS)
        _update()

    def render_summary() -> None:
        summary = get_alert_summary()
        summary_row.controls = [
            _summary_chip("Ouvertes", summary["open"], DANGER if summary["open"] else SUCCESS, ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            _summary_chip("Critiques", summary["critical"], DANGER if summary["critical"] else SUCCESS, ft.Icons.PRIORITY_HIGH_OUTLINED),
            _summary_chip("Haut", summary["high"], WARNING if summary["high"] else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _summary_chip("Moyen", summary["medium"], PRIMARY, ft.Icons.INFO_OUTLINED),
            _summary_chip("Total", summary["total"], MUTED, ft.Icons.FORMAT_LIST_BULLETED_OUTLINED),
        ]

    def render_sources() -> None:
        summary = get_alert_summary()
        source_area.controls = [
            _source_badge(label, value)
            for label, value in sorted(summary["by_source"].items())
        ] or [ft.Text("Aucune source en alerte.", size=12, color=SUCCESS)]

    def render_table() -> None:
        rows = current_rows()
        table_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"Alertes ({len(rows)})", size=17, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Niveau")),
                            ft.DataColumn(ft.Text("Source")),
                            ft.DataColumn(ft.Text("Type")),
                            ft.DataColumn(ft.Text("Reference")),
                            ft.DataColumn(ft.Text("Message")),
                            ft.DataColumn(ft.Text("Action")),
                            ft.DataColumn(ft.Text("Statut")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[_alert_row(row, close_manual, remove_manual, navigate) for row in rows],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            )
            if rows
            else ft.Container(
                bgcolor="#F8FAFC",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=16,
                content=ft.Text("Aucune alerte pour les filtres selectionnes.", size=13, color=SUCCESS),
            ),
        ]

    for control in (search_field, source_filter, level_filter, status_filter):
        control.on_change = refresh

    root = ft.Column(
        controls=[
            module_header(
                "Alertes",
                "Centralisation des signaux QHSE: formations, presence, breaks, badges, EPI et stock.",
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
                                source_filter,
                                level_filter,
                                status_filter,
                                ft.IconButton(icon=ft.Icons.SYNC_OUTLINED, tooltip="Actualiser", on_click=refresh),
                                ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_filters),
                                ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_alerts),
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        summary_row,
                        source_area,
                    ],
                    spacing=12,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Nouvelle alerte manuelle", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[manual_type_field, manual_level_field, manual_message_field],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("Creer l'alerte", icon=ft.Icons.ADD_ALERT_OUTLINED, on_click=save_manual_alert),
                                ft.Text("Les alertes automatiques se ferment dans leur module d'origine.", size=12, color=MUTED),
                            ],
                            spacing=10,
                            wrap=True,
                        ),
                    ],
                    spacing=10,
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
    refresh()
    return root


def _alert_row(row: dict[str, Any], close_action: Any, delete_action: Any, navigate: Any | None) -> ft.DataRow:
    color = LEVEL_COLORS.get(str(row.get("niveau") or ""), MUTED)
    can_close = bool(row.get("can_close"))
    target_key = _target_key(str(row.get("source_key") or ""))
    return ft.DataRow(
        cells=[
            ft.DataCell(_level_badge(str(row.get("niveau_label") or "-"), color)),
            ft.DataCell(ft.Text(str(row.get("source") or "-"))),
            ft.DataCell(ft.Text(str(row.get("type_alerte") or "-"), weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(str(row.get("reference_label") or "-"))),
            ft.DataCell(ft.Text(str(row.get("message") or "-"), width=360)),
            ft.DataCell(ft.Text(str(row.get("action_hint") or "-"), color=MUTED, width=180)),
            ft.DataCell(ft.Text(str(row.get("statut") or "-"))),
            ft.DataCell(
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.DONE_OUTLINED,
                            tooltip="Marquer traitee",
                            icon_color=SUCCESS,
                            visible=can_close and row.get("statut") == "ouverte",
                            on_click=lambda event, current=row: close_action(current["id"], "traitee"),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.VISIBILITY_OFF_OUTLINED,
                            tooltip="Ignorer",
                            icon_color=WARNING,
                            visible=can_close and row.get("statut") == "ouverte",
                            on_click=lambda event, current=row: close_action(current["id"], "ignoree"),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            tooltip="Supprimer",
                            icon_color=DANGER,
                            visible=can_close,
                            on_click=lambda event, current=row: delete_action(current["id"]),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                            tooltip="Ouvrir le module source",
                            icon_color=PRIMARY,
                            visible=navigate is not None and target_key is not None,
                            on_click=lambda event, key=target_key: navigate(key) if navigate and key is not None else None,
                        ),
                    ],
                    spacing=0,
                )
            ),
        ]
    )


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=16),
                ft.Text(label, color=MUTED, size=11),
                ft.Text(str(value), color=color, size=13, weight=ft.FontWeight.BOLD),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _source_badge(label: str, value: int) -> ft.Control:
    return ft.Container(
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        content=ft.Text(f"{label}: {value}", size=12, color=TEXT),
    )


def _level_badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color, weight=ft.FontWeight.BOLD),
    )


def _manual_id(alert_id: str) -> int:
    return int(str(alert_id).split(":", 1)[1])


def _target_key(source_key: str) -> str | None:
    return {
        "breaks": "EmployeeManagement",
        "attendance": "TimeSheet",
        "ppe": "Ppe",
        "maintenance": "MaintenanceActions",
        "training": "TrainingManagement",
    }.get(source_key)

