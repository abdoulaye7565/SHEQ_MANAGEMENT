from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.theme import BORDER, MUTED, PANEL, PRIMARY, TEXT


def stat_card(
    label: str,
    value: Any,
    color: str = PRIMARY,
    icon: str | None = None,
    subtitle: str | None = None,
    *,
    compact: bool = False,
) -> ft.Control:
    """Reusable dashboard statistic card."""
    return ft.Container(
        height=92 if compact else 112,
        bgcolor=PANEL,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=40,
                    height=40,
                    border_radius=8,
                    bgcolor=_soft_color(color),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon or ft.Icons.INSIGHTS_OUTLINED, color=color, size=20),
                ),
                ft.Column(
                    controls=[
                        ft.Text(str(label), size=11, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(value), size=22 if compact else 25, color=TEXT, weight=ft.FontWeight.BOLD, max_lines=1),
                        ft.Text(
                            str(subtitle or ""),
                            size=10,
                            color=MUTED,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            visible=bool(subtitle),
                        ),
                    ],
                    spacing=2,
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def stat_grid(cards: list[ft.Control], *, min_width: int = 190) -> ft.Control:
    return ft.ResponsiveRow(
        controls=[
            ft.Container(
                card,
                col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
                min_width=min_width,
            )
            for card in cards
        ],
        spacing=12,
        run_spacing=12,
    )


def _soft_color(color: str) -> str:
    return {
        "#2563EB": "#DBEAFE",
        "#1D4ED8": "#DBEAFE",
        "#16A34A": "#DCFCE7",
        "#DC2626": "#FEE2E2",
        "#F59E0B": "#FEF3C7",
        "#0891B2": "#CFFAFE",
        "#64748B": "#E2E8F0",
    }.get(color, "#E2E8F0")
