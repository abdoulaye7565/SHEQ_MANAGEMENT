"""Modern paginator widget — dark cockpit theme, sliding page window."""
from __future__ import annotations

from typing import Callable

import flet as ft

# ── Palette ───────────────────────────────────────────────────────────────────
_BG         = "#071321"
_CARD       = "#0F2336"
_ACTIVE_BG  = "#2563EB"
_ACTIVE_TXT = "#FFFFFF"
_GHOST_BG   = "#10243A"
_GHOST_TXT  = "#9DB0C5"
_GHOST_BDR  = "#1E3A56"
_TEXT       = "#E2E8F0"
_MUTED      = "#9DB0C5"
_ELLIPSIS   = "#4A6080"

PAGE_SIZE = 10          # default; pages import and override locally
_WINDOW   = 5           # max numbered buttons shown at once


def _page_btn(label: str, active: bool, disabled: bool, on_click: Callable) -> ft.Control:
    """Single numbered page button."""
    return ft.Container(
        width=32, height=32,
        border_radius=8,
        bgcolor=_ACTIVE_BG if active else _GHOST_BG,
        border=ft.border.all(1, _ACTIVE_BG if active else _GHOST_BDR),
        alignment=ft.Alignment(0, 0),
        ink=not disabled and not active,
        on_click=(lambda _: on_click()) if (not disabled and not active) else None,
        content=ft.Text(
            label,
            size=12,
            weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
            color=_ACTIVE_TXT if active else _GHOST_TXT,
        ),
    )


def _ellipsis() -> ft.Control:
    return ft.Container(
        width=24, height=32,
        alignment=ft.Alignment(0, 0),
        content=ft.Text("…", size=13, color=_ELLIPSIS),
    )


def _nav_btn(
    icon: str,
    disabled: bool,
    on_click: Callable,
    tooltip: str = "",
) -> ft.Control:
    return ft.Container(
        width=32, height=32,
        border_radius=8,
        bgcolor=_GHOST_BG,
        border=ft.border.all(1, _GHOST_BDR),
        alignment=ft.Alignment(0, 0),
        ink=not disabled,
        tooltip=tooltip,
        opacity=0.35 if disabled else 1.0,
        on_click=(lambda _: on_click()) if not disabled else None,
        content=ft.Icon(icon, size=15, color=_GHOST_TXT if disabled else _TEXT),
    )


def pagination_row(
    current_page: int,
    max_page: int,
    total: int,
    shown_start: int,
    shown_end: int,
    item_label: str,
    on_prev: Callable[[], None],
    on_next: Callable[[], None],
    on_page: Callable[[int], None] | None = None,
) -> ft.Row:
    """Modern dark-theme paginator with sliding page-number window.

    Parameters
    ----------
    current_page  : zero-based current page index
    max_page      : zero-based last page index
    total         : total items across all pages
    shown_start   : 1-based index of first visible item (0 when empty)
    shown_end     : 1-based index of last visible item
    item_label    : noun for items, e.g. "alerte(s)", "employé(s)"
    on_prev       : callback when ← clicked
    on_next       : callback when → clicked
    on_page       : optional callback(page_index) for numbered buttons;
                    falls back to on_prev/on_next chains when omitted
    """
    controls: list[ft.Control] = []

    # ── Result count ──────────────────────────────────────────────────────────
    if total == 0:
        count_text = f"0 {item_label}"
    else:
        count_text = f"{shown_start}–{shown_end} / {total} {item_label}"

    controls.append(
        ft.Container(
            bgcolor=_GHOST_BG,
            border=ft.border.all(1, _GHOST_BDR),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            content=ft.Text(count_text, size=11, color=_MUTED, weight=ft.FontWeight.W_500),
        )
    )
    controls.append(ft.Container(expand=True))   # spacer — pushes nav to the right

    # ── Nothing to page ───────────────────────────────────────────────────────
    if max_page <= 0:
        return ft.Row(
            controls=controls,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )

    # ── ← Previous ───────────────────────────────────────────────────────────
    controls.append(
        _nav_btn(ft.Icons.CHEVRON_LEFT_ROUNDED, current_page <= 0, on_prev, "Page précédente")
    )

    # ── Numbered buttons (sliding window) ─────────────────────────────────────
    total_pages = max_page + 1
    half = _WINDOW // 2

    if total_pages <= _WINDOW + 2:
        # Show all page numbers
        page_nums = list(range(total_pages))
    else:
        # Sliding window with ellipsis
        start_w = max(1, min(current_page - half, total_pages - _WINDOW - 1))
        end_w   = min(start_w + _WINDOW - 1, total_pages - 2)
        page_nums_inner = list(range(start_w, end_w + 1))
        page_nums = [0] + (["…l"] if page_nums_inner[0] > 1 else []) + page_nums_inner + \
                    (["…r"] if page_nums_inner[-1] < total_pages - 2 else []) + [total_pages - 1]

    def _go(p: int) -> None:
        if on_page:
            on_page(p)
        else:
            # Emulate by calling prev/next repeatedly (fallback)
            delta = p - current_page
            if delta < 0:
                for _ in range(-delta):
                    on_prev()
            else:
                for _ in range(delta):
                    on_next()

    for p in page_nums:
        if p == "…l" or p == "…r":
            controls.append(_ellipsis())
        else:
            controls.append(
                _page_btn(
                    str(p + 1),
                    active=(p == current_page),
                    disabled=False,
                    on_click=lambda pp=p: _go(pp),
                )
            )

    # ── Next → ───────────────────────────────────────────────────────────────
    controls.append(
        _nav_btn(ft.Icons.CHEVRON_RIGHT_ROUNDED, current_page >= max_page, on_next, "Page suivante")
    )

    return ft.Row(
        controls=controls,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )
