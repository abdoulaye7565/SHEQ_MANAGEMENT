import flet as ft

from app.ui.theme import HEADER_SOFT, MUTED, PRIMARY, TEXT


def module_header(title: str, subtitle: str) -> ft.Control:
    return ft.Container(
        bgcolor=HEADER_SOFT,
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        content=ft.Row(
            controls=[
                ft.Container(width=4, height=46, bgcolor=PRIMARY, border_radius=4),
                ft.Column(
                    controls=[
                        ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(subtitle, size=12, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=4,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
