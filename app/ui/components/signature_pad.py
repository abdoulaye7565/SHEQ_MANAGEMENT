"""Signature capture widget — image file picker (desktop) / camera scan (mobile)."""
from __future__ import annotations

import base64
from typing import Callable

import flet as ft

_SIG_BG   = "#0D1B2A"
_BORDER   = "#1E3A56"
_MUTED    = "#9DB0C5"
_DANGER   = "#EF4444"
_BTN_BG   = "#1B3A5C"
_BTN_FG   = "#FFFFFF"


def _u(ctrl: ft.Control) -> None:
    try:
        ctrl.update()
    except (RuntimeError, AssertionError):
        pass


class SignaturePad:
    """
    Signature capture widget using FilePicker.
    User picks/takes a photo of the handwritten signature.
    Access .widget to embed in the UI.
    """

    def __init__(
        self,
        label: str = "Signature",
        page: ft.Page | None = None,
        width: int = 300,
        height: int = 110,
        existing_b64: str | None = None,
        on_signed: Callable[[], None] | None = None,
    ) -> None:
        self._b64: str | None = existing_b64
        self._page = page
        self._w = width
        self._h = height
        self._on_signed = on_signed
        self._picker = ft.FilePicker()
        # In Flet 0.84, FilePicker is a Service — must be in page.services for _invoke_method to work
        if page is not None and self._picker not in page.services:
            page.services.append(self._picker)

        def _b64_src(b64: str | None) -> str:
            return f"data:image/png;base64,{b64}" if b64 else ""

        # Preview image
        self._preview_img = ft.Image(
            src=_b64_src(existing_b64),
            width=width,
            height=height,
            fit=ft.BoxFit.CONTAIN,
            visible=bool(existing_b64),
        )

        # Placeholder shown when no signature
        self._placeholder = ft.Container(
            width=width,
            height=height,
            bgcolor=_SIG_BG,
            border=ft.border.all(1, _BORDER),
            border_radius=6,
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.IMAGE_OUTLINED, color=_MUTED, size=28),
                    ft.Text("Aucune signature", color=_MUTED, size=11),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            visible=not bool(existing_b64),
        )

        status_txt = ft.Text(
            "✓ Signature ajoutée" if existing_b64 else "",
            color="#4ADE80",
            size=11,
        )

        def _refresh_display() -> None:
            has = bool(self._b64)
            self._preview_img.src = _b64_src(self._b64)
            self._preview_img.visible = has
            self._placeholder.visible = not has
            status_txt.value = "✓ Signature ajoutée" if has else ""
            _u(self._preview_img)
            _u(self._placeholder)
            _u(status_txt)

        self._refresh_display = _refresh_display

        async def _pick(_) -> None:
            files = await self._picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.IMAGE,
            )
            if not files:
                return
            path = files[0].path
            if not path:
                return
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                self._b64 = base64.b64encode(raw).decode()
                _refresh_display()
                if self._on_signed:
                    self._on_signed()
            except Exception:
                pass

        def _clear(_) -> None:
            self._b64 = None
            _refresh_display()

        self.widget = ft.Column(
            controls=[
                ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=_MUTED),
                ft.Stack(
                    controls=[self._placeholder, self._preview_img],
                    width=width,
                    height=height,
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Importer signature",
                            icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
                            bgcolor=_BTN_BG,
                            color=_BTN_FG,
                            on_click=_pick,
                        ),
                        ft.TextButton(
                            "Effacer",
                            icon=ft.Icons.CLEAR,
                            icon_color=_DANGER,
                            on_click=_clear,
                            style=ft.ButtonStyle(color=_DANGER),
                        ),
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.START,
                ),
                status_txt,
            ],
            spacing=4,
            width=width,
        )

    def get_base64(self) -> str | None:
        return self._b64

    def has_signature(self) -> bool:
        return bool(self._b64)

    def set_signature(self, b64: str | None) -> None:
        """Charge une signature (base64 brut) et rafraîchit l'affichage."""
        self._b64 = b64
        self._refresh_display()
