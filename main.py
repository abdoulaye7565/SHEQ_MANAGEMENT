import asyncio
import os
import sys
import warnings
from pathlib import Path

import flet as ft

from app.db.connection import initialize_database
from app.ui.app_shell import build_app
from app.ui.theme import page_theme


warnings.filterwarnings("ignore", category=DeprecationWarning)


def _configure_frozen_env() -> None:
    """Point Flet to the bundled binary so the app works fully offline.

    The PyInstaller hook (hook-flet.py) copies the extracted Flet desktop
    binary into _internal/flet_desktop/app/flet/.  flet_desktop's own
    resolution logic only looks for an archive there, so it would fall through
    to a network download on a fresh machine.  Setting FLET_VIEW_PATH before
    ft.app() starts makes flet_desktop use the already-extracted directory.
    """
    if not getattr(sys, "frozen", False):
        return
    exe_dir = Path(sys.executable).parent
    # Primary: PyInstaller one-folder bundle (_internal/ layout)
    bundled = exe_dir / "_internal" / "flet_desktop" / "app" / "flet"
    if bundled.is_dir() and (bundled / "flet.exe").is_file():
        os.environ.setdefault("FLET_VIEW_PATH", str(bundled))
        return
    # Fallback: flet_view/ placed alongside the exe (portable / custom builds)
    portable = exe_dir / "flet_view"
    if portable.is_dir() and (portable / "flet.exe").is_file():
        os.environ.setdefault("FLET_VIEW_PATH", str(portable))


def ignore_closed_flet_connection(
    loop: asyncio.AbstractEventLoop,
    context: dict[str, object],
) -> None:
    exception = context.get("exception")
    if isinstance(exception, ConnectionResetError) and getattr(exception, "winerror", None) == 10054:
        return
    loop.default_exception_handler(context)


def patch_windows_proactor_close_noise() -> None:
    if sys.platform != "win32":
        return
    try:
        from asyncio import proactor_events
    except ImportError:
        return

    transport = proactor_events._ProactorBasePipeTransport
    original = transport._call_connection_lost

    def quiet_call_connection_lost(self, exc):
        try:
            original(self, exc)
        except ConnectionResetError as error:
            if getattr(error, "winerror", None) == 10054:
                return
            raise

    transport._call_connection_lost = quiet_call_connection_lost


def main(page: ft.Page) -> None:
    initialize_database()
    page.theme = page_theme()
    build_app(page)


if __name__ == "__main__":
    _configure_frozen_env()
    patch_windows_proactor_close_noise()
    ft.app(target=main, assets_dir="assets")
