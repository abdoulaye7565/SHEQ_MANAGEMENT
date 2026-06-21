import flet as ft

from app.ui.theme import HEADER_SOFT, MUTED, PRIMARY, TEXT


def module_header(title: str, subtitle: str, icon: str | None = None) -> ft.Control:
    icon_widget = ft.Container(
        width=40, height=40,
        bgcolor="#DBEAFE",
        border_radius=10,
        alignment=ft.Alignment(0, 0),
        content=ft.Icon(icon or ft.Icons.APPS_OUTLINED, size=20, color=PRIMARY),
    )
    return ft.Container(
        bgcolor=HEADER_SOFT,
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        content=ft.Row(
            controls=[
                ft.Container(width=4, height=44, bgcolor=PRIMARY, border_radius=4),
                icon_widget,
                ft.Column(
                    controls=[
                        ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(subtitle, size=12, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=3,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
