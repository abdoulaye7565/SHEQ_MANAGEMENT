from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.module_header import module_header
from app.ui.pages.alerts import alerts_page
from app.ui.pages.automation_controls import automation_controls_page
from app.ui.pages.reports import reports_page
from app.ui.theme import BORDER, MUTED, PRIMARY, TEXT


def alerts_reports_page(navigate: Any | None = None) -> ft.Control:
    state: dict[str, str] = {"selected": "alerts"}
    content_area = ft.Column(spacing=0)
    tab_buttons: dict[str, ft.TextButton] = {}

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
                        control.color = PRIMARY if selected else MUTED
                    if isinstance(control, ft.Text):
                        control.color = TEXT if selected else MUTED

    def select_tab(key: str) -> None:
        state["selected"] = key
        content_area.controls = [build_content(key)]
        refresh_tab_styles()
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
        spacing=6,
        wrap=True,
    )
    root = ft.Column(
        controls=[
            module_header(
                "Alertes & Rapports",
                "Control center QHSE: alertes, automatisations et rapports operationnels.",
            ),
            ft.Container(
                border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                content=tab_row,
            ),
            content_area,
        ],
        spacing=16,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    content_area.controls = [build_content(state["selected"])]
    refresh_tab_styles()
    return root


def _tab_style(selected: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color=TEXT if selected else MUTED,
        bgcolor="#EFF6FF" if selected else "#FFFFFF",
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )
