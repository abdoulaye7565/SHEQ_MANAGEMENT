from __future__ import annotations

from typing import Any

import flet as ft

from app.services import get_alert_action_plan, get_alert_summary, run_startup_automations
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def automation_controls_page(navigate: Any | None = None) -> ft.Control:
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    result_area = ft.Column(spacing=8)
    plan_area = ft.ResponsiveRow(spacing=12, run_spacing=12)
    state: dict[str, Any] = {"last_run": None}

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh() -> None:
        alert_summary = get_alert_summary()
        summary_row.controls = [
            _summary_chip("Alertes ouvertes", alert_summary["open"], DANGER if alert_summary["open"] else SUCCESS, ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            _summary_chip("Critiques", alert_summary["critical"], DANGER if alert_summary["critical"] else SUCCESS, ft.Icons.PRIORITY_HIGH_OUTLINED),
            _summary_chip("Haut", alert_summary["high"], WARNING if alert_summary["high"] else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _summary_chip("Sources", len(alert_summary["by_source"]), PRIMARY, ft.Icons.ACCOUNT_TREE_OUTLINED),
        ]
        render_last_run()
        render_plan()

    def run_now(event: ft.ControlEvent | None = None) -> None:
        state["last_run"] = run_startup_automations()
        status.value = "Automatisations executees."
        status.color = SUCCESS
        refresh()
        _update()

    def render_last_run() -> None:
        result = state.get("last_run")
        if not result:
            result_area.controls = [
                ft.Text(
                    "Les controles automatiques s'executent deja a l'ouverture de l'application. Tu peux les relancer manuellement ici.",
                    color=MUTED,
                    size=12,
                )
            ]
            return
        maintenance = result.get("maintenance") or {}
        warnings = result.get("warnings") or []
        result_area.controls = [
            ft.Row(
                controls=[
                    _status_pill("Presence du jour", "OK" if result.get("attendance_ready") else "A verifier", SUCCESS if result.get("attendance_ready") else WARNING),
                    _status_pill("Maintenances retard", maintenance.get("maintenance", 0), WARNING if maintenance.get("maintenance") else SUCCESS),
                    _status_pill("Actions retard", maintenance.get("actions", 0), WARNING if maintenance.get("actions") else SUCCESS),
                    _status_pill("Themes Toolbox", result.get("toolbox_assigned", 0), PRIMARY),
                ],
                spacing=8,
                wrap=True,
            ),
            ft.Column(
                controls=[ft.Text(str(item), color=WARNING, size=12) for item in warnings],
                spacing=4,
            )
            if warnings
            else ft.Text("Aucun avertissement d'automatisation.", color=SUCCESS, size=12),
        ]

    def render_plan() -> None:
        plan = get_alert_action_plan(limit=6)
        plan_area.controls = [
            ft.Container(
                col={"xs": 12, "md": 6, "xl": 4},
                bgcolor="#FFFFFF",
                border=ft.border.all(1, _level_color(str(item.get("top_level") or ""))),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color=_level_color(str(item.get("top_level") or "")), size=18),
                                ft.Text(str(item.get("source") or "-"), color=TEXT, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(str(item.get("count") or 0), color=PRIMARY, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(str(item.get("top_message") or ""), color=TEXT, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(item.get("action_hint") or ""), color=MUTED, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.OutlinedButton(
                            "Ouvrir le module",
                            icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                            disabled=navigate is None or _target_key(str(item.get("source_key") or "")) is None,
                            on_click=lambda event, key=_target_key(str(item.get("source_key") or "")): navigate(key) if navigate and key else None,
                        ),
                    ],
                    spacing=8,
                ),
            )
            for item in plan
        ] or [
            ft.Container(
                col={"xs": 12},
                bgcolor="#F8FAFC",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=12,
                content=ft.Text("Aucune action prioritaire ouverte.", color=SUCCESS, size=12),
            )
        ]

    root = ft.Column(
        controls=[
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text("Automatisations QHSE", color=TEXT, size=18, weight=ft.FontWeight.BOLD, expand=True),
                                ft.ElevatedButton("Executer maintenant", icon=ft.Icons.PLAY_CIRCLE_OUTLINED, on_click=run_now),
                                status,
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        summary_row,
                        result_area,
                    ],
                    spacing=12,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Priorites detectees automatiquement", color=TEXT, size=16, weight=ft.FontWeight.BOLD),
                        plan_area,
                    ],
                    spacing=12,
                ),
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    return root


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(stat_card(label, value, color, icon, compact=True), col={"xs": 12, "sm": 6, "md": 3})


def _status_pill(label: str, value: Any, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=7),
        content=ft.Row(
            controls=[
                ft.Text(label, color=MUTED, size=11, weight=ft.FontWeight.BOLD),
                ft.Text(str(value), color=color, size=13, weight=ft.FontWeight.BOLD),
            ],
            spacing=7,
            tight=True,
        ),
    )


def _level_color(level: str) -> str:
    return {
        "critique": DANGER,
        "haut": WARNING,
        "moyen": PRIMARY,
        "bas": SUCCESS,
    }.get(level, MUTED)


def _target_key(source_key: str) -> str | None:
    return {
        "breaks": "EmployeeManagement",
        "attendance": "TimeSheet",
        "ppe": "Ppe",
        "maintenance": "MaintenanceActions",
        "training": "TrainingManagement",
        "toolbox": "ToolboxTalk",
    }.get(source_key)
