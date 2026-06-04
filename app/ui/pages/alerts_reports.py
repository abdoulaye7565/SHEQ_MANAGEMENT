from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.module_header import module_header
from app.ui.pages.alerts import alerts_page
from app.ui.pages.automation_controls import automation_controls_page
from app.ui.pages.reports import reports_page


def alerts_reports_page(navigate: Any | None = None) -> ft.Control:
    views: dict[str, ft.Control] = {
        "alerts": alerts_page(navigate=navigate, show_header=False),
    }
    content_area = ft.Container(content=views["alerts"], expand=True)
    switch = ft.SegmentedButton(
        selected=["alerts"],
        allow_empty_selection=False,
        segments=[
            ft.Segment(
                value="alerts",
                icon=ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,
                label="Alertes",
            ),
            ft.Segment(
                value="reports",
                icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                label="Rapports",
            ),
            ft.Segment(
                value="automation",
                icon=ft.Icons.AUTO_MODE_OUTLINED,
                label="Automatisations",
            ),
        ],
    )

    def change_tab(event: ft.ControlEvent | None = None) -> None:
        selected = "automation" if "automation" in switch.selected else ("reports" if "reports" in switch.selected else "alerts")
        if selected not in views:
            views[selected] = automation_controls_page(navigate=navigate) if selected == "automation" else reports_page(show_header=False)
        content_area.content = views[selected]
        try:
            content_area.update()
        except RuntimeError:
            pass

    switch.on_change = change_tab
    return ft.Column(
        controls=[
            module_header(
                "Alertes & Rapports",
                "Control center QHSE: alertes, automatisations et rapports operationnels.",
            ),
            ft.Row(
                controls=[switch],
                wrap=True,
            ),
            ft.Container(
                padding=ft.padding.only(top=4),
                content=content_area,
                expand=True,
            ),
        ],
        spacing=16,
        expand=True,
    )
