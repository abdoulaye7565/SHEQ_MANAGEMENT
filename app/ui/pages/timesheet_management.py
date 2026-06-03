from __future__ import annotations

import flet as ft

from app.ui.pages.monthly_timesheet import monthly_timesheet_page
from app.ui.pages.timesheet import timesheet_page
from app.ui.theme import BORDER, PANEL, PRIMARY, TEXT


def timesheet_management_page(page: ft.Page) -> ft.Control:
    content = ft.Container(expand=True)
    state = {"active": "21-20"}

    def render() -> None:
        content.content = timesheet_page(page) if state["active"] == "21-20" else monthly_timesheet_page(page)
        button_21.style = _tab_style(state["active"] == "21-20")
        button_125.style = _tab_style(state["active"] == "1-25")

    def switch(target: str) -> None:
        state["active"] = target
        render()
        try:
            root.update()
        except RuntimeError:
            pass

    button_21 = ft.TextButton(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=18),
                ft.Text("TimeSheet 21-20", weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
            tight=True,
        ),
        on_click=lambda event: switch("21-20"),
    )
    button_125 = ft.TextButton(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.EVENT_NOTE_OUTLINED, size=18),
                ft.Text("TimeSheet 1-25 / Mois courant", weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
            tight=True,
        ),
        on_click=lambda event: switch("1-25"),
    )

    root = ft.Column(
        controls=[
            ft.Container(
                bgcolor=PANEL,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=8,
                content=ft.Row(
                    controls=[button_21, button_125],
                    wrap=True,
                    spacing=8,
                ),
            ),
            content,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render()
    return root


def _tab_style(selected: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color="#FFFFFF" if selected else TEXT,
        bgcolor=PRIMARY if selected else "#FFFFFF",
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )
