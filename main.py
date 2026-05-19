import asyncio
import sys
import warnings

import flet as ft

from app.db.connection import initialize_database
from app.ui.app_shell import build_app
from app.ui.theme import page_theme


warnings.filterwarnings("ignore", category=DeprecationWarning)


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
    patch_windows_proactor_close_noise()
    ft.app(target=main)
