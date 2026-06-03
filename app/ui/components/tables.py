from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.theme import BORDER, MUTED, PANEL, PANEL_ALT, PRIMARY, TEXT


def professional_data_table(*args: Any, **kwargs: Any) -> ft.DataTable:
    """Shared industrial dashboard table styling."""
    rows = list(kwargs.get("rows") or [])
    kwargs.setdefault("bgcolor", PANEL)
    kwargs.setdefault("border", ft.border.all(1, BORDER))
    kwargs.setdefault("border_radius", 8)
    kwargs.setdefault("horizontal_lines", ft.BorderSide(1, "#E2E8F0"))
    kwargs.setdefault("vertical_lines", ft.BorderSide(1, "#F1F5F9"))
    kwargs.setdefault("heading_row_color", "#DBEAFE")
    kwargs.setdefault("heading_row_height", 48)
    kwargs.setdefault("data_row_min_height", 46)
    kwargs.setdefault("data_row_max_height", 76)
    kwargs.setdefault("column_spacing", 20)
    kwargs.setdefault("horizontal_margin", 16)
    kwargs.setdefault("divider_thickness", 0.6)
    kwargs.setdefault("show_bottom_border", True)
    kwargs.setdefault("show_checkbox_column", False)
    kwargs.setdefault("heading_text_style", ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color="#1E3A8A"))
    kwargs.setdefault("data_text_style", ft.TextStyle(size=12, color=TEXT))
    kwargs.setdefault(
        "data_row_color",
        {
            ft.ControlState.HOVERED: PANEL_ALT,
            ft.ControlState.PRESSED: "#EAF2FF",
            ft.ControlState.SELECTED: "#D7E7FF",
        },
    )
    table = ft.DataTable(*args, **kwargs)
    _enable_single_row_selection(table, rows)
    return table


def _enable_single_row_selection(table: ft.DataTable, rows: list[ft.DataRow]) -> None:
    if not rows:
        return

    def select_row(selected_row: ft.DataRow, previous_handler: object | None) -> object:
        def handler(event: ft.ControlEvent | None = None) -> None:
            for row in rows:
                row.selected = row is selected_row
            if callable(previous_handler):
                previous_handler(event)
            try:
                table.update()
            except RuntimeError:
                pass

        return handler

    for row in rows:
        previous_handler = getattr(row, "on_select_changed", None)
        row.on_select_changed = select_row(row, previous_handler)


def empty_table_state(message: str = "Aucune donnee disponible.") -> ft.Control:
    return ft.Container(
        bgcolor=PANEL_ALT,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=24,
        alignment=ft.alignment.center,
        content=ft.Text(message, color=MUTED, size=13),
    )

