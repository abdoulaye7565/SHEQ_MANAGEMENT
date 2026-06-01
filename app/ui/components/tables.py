from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.theme import BORDER, MUTED, PANEL, PRIMARY, TEXT


def professional_data_table(*args: Any, **kwargs: Any) -> ft.DataTable:
    """Shared industrial dashboard table styling."""
    kwargs.setdefault("bgcolor", PANEL)
    kwargs.setdefault("border", ft.border.all(1, BORDER))
    kwargs.setdefault("border_radius", 8)
    kwargs.setdefault("horizontal_lines", ft.BorderSide(1, "#E5EAF2"))
    kwargs.setdefault("vertical_lines", ft.BorderSide(1, "#EEF2F7"))
    kwargs.setdefault("heading_row_color", "#EAF2FF")
    kwargs.setdefault("heading_row_height", 46)
    kwargs.setdefault("data_row_min_height", 44)
    kwargs.setdefault("data_row_max_height", 72)
    kwargs.setdefault("column_spacing", 18)
    kwargs.setdefault("horizontal_margin", 14)
    kwargs.setdefault("divider_thickness", 0.6)
    kwargs.setdefault("show_bottom_border", True)
    kwargs.setdefault("heading_text_style", ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color=PRIMARY))
    kwargs.setdefault("data_text_style", ft.TextStyle(size=12, color=TEXT))
    kwargs.setdefault(
        "data_row_color",
        {
            ft.ControlState.HOVERED: "#F8FAFC",
            ft.ControlState.SELECTED: "#DBEAFE",
        },
    )
    return ft.DataTable(*args, **kwargs)


def empty_table_state(message: str = "Aucune donnee disponible.") -> ft.Control:
    return ft.Container(
        bgcolor="#F8FAFC",
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=24,
        alignment=ft.alignment.center,
        content=ft.Text(message, color=MUTED, size=13),
    )

