from __future__ import annotations

import flet as ft

_FILL   = "#0A1929"
_TEXT   = "#E2E8F0"
_LABEL  = "#9DB0C5"
_BORDER = "#1E3A5F"
_FOCUS  = "#2563EB"


def dark_dropdown(
    label: str = "",
    options: list[ft.dropdown.Option] | None = None,
    value: str | None = None,
    width: int | None = None,
    expand: bool | int | None = None,
    on_change=None,
    disabled: bool = False,
    hint_text: str | None = None,
) -> ft.Dropdown:
    """Standard dark-themed dropdown for the cockpit UI."""
    kwargs: dict = dict(
        label=label,
        options=options or [],
        fill_color=_FILL,
        color=_TEXT,
        border_color=_BORDER,
        focused_border_color=_FOCUS,
        label_style=ft.TextStyle(color=_LABEL),
        text_style=ft.TextStyle(color=_TEXT),
    )
    if value is not None:
        kwargs["value"] = value
    if width is not None:
        kwargs["width"] = width
    if expand is not None:
        kwargs["expand"] = expand
    if on_change is not None:
        kwargs["on_change"] = on_change
    if disabled:
        kwargs["disabled"] = True
    if hint_text is not None:
        kwargs["hint_text"] = hint_text
        kwargs["hint_style"] = ft.TextStyle(color=_LABEL)
    return ft.Dropdown(**kwargs)


def dark_field(
    label: str = "",
    value: str | None = None,
    width: int | None = None,
    expand: bool | int | None = None,
    multiline: bool = False,
    min_lines: int | None = None,
    max_lines: int | None = None,
    read_only: bool = False,
    hint_text: str | None = None,
    on_change=None,
    on_submit=None,
    password: bool = False,
    prefix_icon: str | None = None,
    suffix_text: str | None = None,
) -> ft.TextField:
    """Standard dark-themed text field for the cockpit UI."""
    kwargs: dict = dict(
        label=label,
        fill_color=_FILL,
        color=_TEXT,
        border_color=_BORDER,
        focused_border_color=_FOCUS,
        label_style=ft.TextStyle(color=_LABEL),
        text_style=ft.TextStyle(color=_TEXT),
        cursor_color=_FOCUS,
    )
    if value is not None:
        kwargs["value"] = value
    if width is not None:
        kwargs["width"] = width
    if expand is not None:
        kwargs["expand"] = expand
    if multiline:
        kwargs["multiline"] = True
    if min_lines is not None:
        kwargs["min_lines"] = min_lines
    if max_lines is not None:
        kwargs["max_lines"] = max_lines
    if read_only:
        kwargs["read_only"] = True
    if hint_text:
        kwargs["hint_text"] = hint_text
        kwargs["hint_style"] = ft.TextStyle(color=_LABEL)
    if on_change:
        kwargs["on_change"] = on_change
    if on_submit:
        kwargs["on_submit"] = on_submit
    if password:
        kwargs["password"] = True
        kwargs["can_reveal_password"] = True
    if prefix_icon:
        kwargs["prefix_icon"] = prefix_icon
    if suffix_text:
        kwargs["suffix_text"] = suffix_text
        kwargs["suffix_style"] = ft.TextStyle(color=_LABEL)
    return ft.TextField(**kwargs)
