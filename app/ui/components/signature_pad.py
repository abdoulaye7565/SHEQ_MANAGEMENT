"""Reusable signature capture pad widget for Flet 0.84."""
from __future__ import annotations

import base64
import io
from typing import Callable

import flet as ft
import flet.canvas as cv

_SIG_INK = "#1E3A8A"
_SIG_BG  = "#FFFFFF"
_BORDER  = "#1E3A56"
_MUTED   = "#9DB0C5"
_DANGER  = "#EF4444"


def _u(ctrl: ft.Control) -> None:
    try:
        ctrl.update()
    except (RuntimeError, AssertionError):
        pass


def strokes_to_png_bytes(
    strokes: list[list[tuple[float, float]]],
    width: int = 300,
    height: int = 110,
) -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    for stroke in strokes:
        pts = [(int(x), int(y)) for x, y in stroke if 0 <= x <= width and 0 <= y <= height]
        if len(pts) == 1:
            x, y = pts[0]
            draw.ellipse([(x - 2, y - 2), (x + 2, y + 2)], fill=_SIG_INK)
        elif len(pts) >= 2:
            draw.line(pts, fill=_SIG_INK, width=3, joint="curve")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def strokes_to_b64(
    strokes: list[list[tuple[float, float]]],
    width: int = 300,
    height: int = 110,
) -> str:
    return base64.b64encode(strokes_to_png_bytes(strokes, width, height)).decode()


class SignaturePad:
    """
    Interactive signature pad.  Access .widget to embed in the UI.
    Call .get_base64() to retrieve the PNG as a base64 string (or None if empty).
    """

    def __init__(
        self,
        label: str = "Signature",
        width: int = 300,
        height: int = 110,
        existing_b64: str | None = None,
        on_signed: Callable[[], None] | None = None,
    ) -> None:
        self._strokes: list[list[tuple[float, float]]] = []
        self._current: list[tuple[float, float]] = []
        self._existing_b64: str | None = existing_b64
        self._drew = False
        self._w = width
        self._h = height
        self._on_signed = on_signed

        self._canvas = cv.Canvas(shapes=[], width=width, height=height)

        def _on_start(e: ft.DragStartEvent) -> None:
            self._current = [(e.local_position.x, e.local_position.y)]

        def _on_update(e: ft.DragUpdateEvent) -> None:
            x, y = e.local_position.x, e.local_position.y
            if not self._current:
                self._current = [(x, y)]
                return
            px, py = self._current[-1]
            self._current.append((x, y))
            self._canvas.shapes.append(
                cv.Path(
                    elements=[
                        cv.Path.MoveTo(px, py),
                        cv.Path.LineTo(x, y),
                    ],
                    paint=ft.Paint(
                        color=_SIG_INK,
                        stroke_width=2.5,
                        style=ft.PaintingStyle.STROKE,
                        stroke_cap=ft.StrokeCap.ROUND,
                        stroke_join=ft.StrokeJoin.ROUND,
                    ),
                )
            )
            _u(self._canvas)

        def _on_end(e: ft.DragEndEvent) -> None:
            if self._current:
                self._strokes.append(list(self._current))
                self._drew = True
                if self._on_signed:
                    self._on_signed()
            self._current = []

        def _clear(_) -> None:
            self._strokes.clear()
            self._current.clear()
            self._drew = False
            self._canvas.shapes.clear()
            _u(self._canvas)

        gesture = ft.GestureDetector(
            content=self._canvas,
            on_pan_start=_on_start,
            on_pan_update=_on_update,
            on_pan_end=_on_end,
            drag_interval=10,
        )

        pad = ft.Container(
            content=gesture,
            width=width,
            height=height,
            bgcolor=_SIG_BG,
            border=ft.border.all(1, _BORDER),
            border_radius=6,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

        hint_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.DRAW_OUTLINED, size=13, color=_MUTED),
                ft.Text("Signer ici", size=11, color=_MUTED),
            ],
            spacing=4,
        )

        self.widget = ft.Column(
            controls=[
                ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=_MUTED),
                ft.Stack(
                    controls=[pad, ft.Container(content=hint_row, padding=ft.padding.only(left=8, top=4))],
                    width=width,
                    height=height,
                ),
                ft.Row(
                    controls=[
                        ft.TextButton(
                            "Effacer",
                            icon=ft.Icons.CLEAR,
                            icon_color=_DANGER,
                            on_click=_clear,
                            style=ft.ButtonStyle(color=_DANGER),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=4,
            width=width,
        )

    def get_base64(self) -> str | None:
        if self._drew and self._strokes:
            return strokes_to_b64(self._strokes, self._w, self._h)
        return self._existing_b64

    def has_signature(self) -> bool:
        return self._drew or bool(self._existing_b64)

    def is_newly_drawn(self) -> bool:
        return self._drew
