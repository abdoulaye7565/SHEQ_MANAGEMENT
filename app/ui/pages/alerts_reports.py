from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.module_header import module_header
from app.ui.pages.alerts import alerts_page
from app.ui.pages.automation_controls import automation_controls_page
from app.ui.pages.reports import reports_page
from app.services import get_alert_summary, get_report_summary, list_alerts
from app.ui.theme import BORDER, DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING

_DK_CARD   = "#0D2040"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"


def alerts_reports_page(navigate: Any | None = None) -> ft.Control:
    state: dict[str, str] = {"selected": "alerts"}
    content_area = ft.Container(expand=True, bgcolor="#071321")
    report_summary = get_report_summary()
    tab_buttons: dict[str, ft.TextButton] = {}
    kpi_row = ft.ResponsiveRow(spacing=10, run_spacing=10)

    def refresh_kpis() -> None:
        summary = get_alert_summary(list_alerts(statut="all"))
        kpi_row.controls = [
            _control_metric("Alertes ouvertes", summary["open"], DANGER if summary["open"] else SUCCESS, ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            _control_metric("Critiques", summary["critical"], DANGER if summary["critical"] else SUCCESS, ft.Icons.PRIORITY_HIGH_OUTLINED),
            _control_metric("Rapports disponibles", report_summary["reports"], PRIMARY, ft.Icons.DESCRIPTION_OUTLINED),
            _control_metric("Categories", report_summary["categories"], WARNING, ft.Icons.ACCOUNT_TREE_OUTLINED),
        ]
        try:
            kpi_row.update()
        except RuntimeError:
            pass

    def build_content(key: str) -> ft.Control:
        if key == "reports":
            return reports_page(show_header=False)
        if key == "automation":
            return automation_controls_page(navigate=navigate)
        return alerts_page(navigate=navigate, show_header=False)

    def tab_button(key: str, label: str, icon: str) -> ft.TextButton:
        button = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=18),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_600),
                ],
                spacing=7,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            style=_tab_style(selected=key == state["selected"]),
            on_click=lambda event, current=key: select_tab(current),
        )
        tab_buttons[key] = button
        return button

    def refresh_tab_styles() -> None:
        for key, button in tab_buttons.items():
            selected = key == state["selected"]
            button.style = _tab_style(selected=selected)
            if isinstance(button.content, ft.Row):
                for control in button.content.controls:
                    if isinstance(control, ft.Icon):
                        control.color = "#FFFFFF" if selected else MUTED
                    if isinstance(control, ft.Text):
                        control.color = "#FFFFFF" if selected else MUTED

    def select_tab(key: str) -> None:
        state["selected"] = key
        content_area.content = build_content(key)
        refresh_tab_styles()
        refresh_kpis()
        try:
            root.update()
        except RuntimeError:
            pass

    tab_row = ft.Row(
        controls=[
            tab_button("alerts", "Alertes", ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            tab_button("reports", "Rapports", ft.Icons.PICTURE_AS_PDF_OUTLINED),
            tab_button("automation", "Automatisations", ft.Icons.AUTO_MODE_OUTLINED),
        ],
        spacing=8,
        wrap=True,
    )
    root = ft.Column(
        controls=[
            module_header(
                "Alertes & Rapports",
                "Control center QHSE: alertes, automatisations et rapports operationnels.",
            ),
            ft.Container(
                bgcolor=_DK_CARD,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=12,
                padding=0,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Column(
                    controls=[
                        ft.Container(
                            bgcolor=_DK_HEAD,
                            border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                            padding=ft.padding.symmetric(horizontal=16, vertical=10),
                            content=tab_row,
                        ),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                            content=kpi_row,
                        ),
                    ],
                    spacing=0,
                ),
            ),
            content_area,
        ],
        spacing=14,
        expand=True,
    )
    content_area.content = build_content(state["selected"])
    refresh_tab_styles()
    refresh_kpis()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _tab_style(selected: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        bgcolor=PRIMARY if selected else _DK_CARD,
        color="#FFFFFF" if selected else _DK_MUTED,
        shape=ft.RoundedRectangleBorder(radius=6),
        padding=ft.padding.symmetric(horizontal=18, vertical=11),
        side=None if selected else ft.BorderSide(1, _DK_BORDER),
    )


def _control_metric(label: str, value: Any, color: str, icon: str) -> ft.Control:
    _OV = {PRIMARY:"#0F2D5E", SUCCESS:"#052E16", DANGER:"#3B0F0F", WARNING:"#2D1600", MUTED:"#0A1929"}
    return ft.Container(
        col={"xs": 12, "sm": 6, "lg": 3},
        content=ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.only(
                left=ft.BorderSide(4, color),
                top=ft.BorderSide(1, _DK_BORDER),
                right=ft.BorderSide(1, _DK_BORDER),
                bottom=ft.BorderSide(1, _DK_BORDER),
            ),
            border_radius=12,
            padding=ft.padding.only(left=14, right=14, top=12, bottom=12),
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Container(width=32, height=32, bgcolor=_OV.get(color, "#0F2D5E"),
                        border_radius=8, alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, color=color, size=16)),
                    ft.Text(label, size=10, color=_DK_MUTED, weight=ft.FontWeight.W_500, expand=True),
                ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
            ], spacing=4),
        ),
    )
