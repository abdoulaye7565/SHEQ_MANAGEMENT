from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.module_header import module_header
from app.ui.pages.alerts import alerts_page
from app.ui.pages.automation_controls import automation_controls_page
from app.ui.pages.reports import reports_page
from app.ui.theme import BORDER, MUTED, PRIMARY, TEXT


def alerts_reports_page(navigate: Any | None = None) -> ft.Control:
    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Alertes", icon=ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            ft.Tab(label="Rapports", icon=ft.Icons.PICTURE_AS_PDF_OUTLINED),
            ft.Tab(label="Automatisations", icon=ft.Icons.AUTO_MODE_OUTLINED),
        ],
        indicator_color=PRIMARY,
        label_color=TEXT,
        unselected_label_color=MUTED,
        divider_color=BORDER,
    )
    tab_view = ft.TabBarView(
        controls=[
            _tab_content(alerts_page(navigate=navigate, show_header=False)),
            _tab_content(reports_page(show_header=False)),
            _tab_content(automation_controls_page(navigate=navigate)),
        ],
        expand=True,
    )
    tabs = ft.Tabs(
        content=ft.Column(
            controls=[tab_bar, tab_view],
            spacing=12,
            expand=True,
        ),
        length=3,
        selected_index=0,
        animation_duration=120,
        expand=True,
    )
    return ft.Column(
        controls=[
            module_header(
                "Alertes & Rapports",
                "Control center QHSE: alertes, automatisations et rapports operationnels.",
            ),
            tabs,
        ],
        spacing=16,
        expand=True,
    )


def _tab_content(content: ft.Control) -> ft.Control:
    return ft.Container(
        padding=ft.padding.only(top=2, right=2),
        content=content,
        expand=True,
    )
