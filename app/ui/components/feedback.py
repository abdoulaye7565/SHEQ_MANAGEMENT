from __future__ import annotations

import flet as ft

from app.ui.theme import DANGER, MUTED, SUCCESS, WARNING


def show_feedback(page: ft.Page | None, message: str, color: str = MUTED) -> None:
    if page is None or not message:
        return
    try:
        snackbar = ft.SnackBar(
            content=ft.Text(str(message), color="#FFFFFF"),
            bgcolor=_feedback_bgcolor(color),
            show_close_icon=True,
            duration=3500,
            open=True,
        )
        page.overlay.append(snackbar)
        page.update()
    except Exception:
        return


def _feedback_bgcolor(color: str) -> str:
    if color == SUCCESS:
        return SUCCESS
    if color == DANGER:
        return DANGER
    if color == WARNING:
        return WARNING
    return MUTED
