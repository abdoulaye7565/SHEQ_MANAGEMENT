"""Shared pagination row widget used by all table pages."""
from __future__ import annotations

from typing import Callable

import flet as ft

from app.ui.theme import MUTED, TEXT


def pagination_row(
    current_page: int,
    max_page: int,
    total: int,
    shown_start: int,
    shown_end: int,
    item_label: str,
    on_prev: Callable[[], None],
    on_next: Callable[[], None],
) -> ft.Row:
    """Return a styled Prev / Page-N / Next pagination row.

    Parameters
    ----------
    current_page : int
        Zero-based current page index.
    max_page : int
        Zero-based last page index.
    total : int
        Total number of items across all pages.
    shown_start : int
        1-based index of the first shown item (pass 0 when total==0).
    shown_end : int
        1-based index of the last shown item.
    item_label : str
        Plural noun for the items, e.g. "formation(s)" or "employe(s)".
    on_prev : Callable
        Called when the Previous button is clicked.
    on_next : Callable
        Called when the Next button is clicked.
    """
    return ft.Row(
        controls=[
            ft.Text(
                f"{shown_start}-{shown_end} / {total} {item_label}",
                size=12,
                color=MUTED,
            ),
            ft.OutlinedButton(
                "Precedent",
                icon=ft.Icons.ARROW_BACK,
                disabled=current_page <= 0,
                on_click=lambda _: on_prev(),
            ),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                content=ft.Text(f"Page {current_page + 1}/{max_page + 1}", size=12, color=TEXT),
            ),
            ft.OutlinedButton(
                "Suivant",
                icon=ft.Icons.ARROW_FORWARD,
                disabled=current_page >= max_page,
                on_click=lambda _: on_next(),
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
