import flet as ft

from app.ui.theme import MUTED, TEXT


def module_header(title: str, subtitle: str) -> ft.Control:
    return ft.Container(
        padding=ft.padding.only(bottom=4),
        content=ft.Column(
            controls=[
                ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text(subtitle, size=12, color=MUTED),
            ],
            spacing=4,
        ),
    )
