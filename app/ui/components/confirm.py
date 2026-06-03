from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.ui.theme import DANGER, MUTED, PRIMARY, TEXT


def confirm_action(
    page: ft.Page | None,
    title: str,
    message: str,
    on_confirm: Callable[[], None],
    *,
    confirm_label: str = "Confirmer",
    cancel_label: str = "Annuler",
    danger: bool = False,
) -> None:
    """Show a confirmation dialog before an important action."""
    if page is None:
        on_confirm()
        return

    def close(event: ft.ControlEvent | None = None) -> None:
        page.pop_dialog()
        page.update()

    def confirm(event: ft.ControlEvent | None = None) -> None:
        close()
        on_confirm()

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.WARNING_AMBER_OUTLINED if danger else ft.Icons.HELP_OUTLINE,
                        color=DANGER if danger else PRIMARY,
                    ),
                    ft.Text(title, color=TEXT, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Text(message, color=MUTED, size=13),
            actions=[
                ft.TextButton(cancel_label, on_click=close),
                ft.ElevatedButton(
                    confirm_label,
                    icon=ft.Icons.CHECK_OUTLINED,
                    bgcolor=DANGER if danger else PRIMARY,
                    color="#FFFFFF",
                    on_click=confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
    )
