from __future__ import annotations

from typing import Any

import flet as ft

from app.services import get_alert_action_plan, get_alert_summary, list_alerts, run_startup_automations
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING

_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"


def automation_controls_page(navigate: Any | None = None) -> ft.Control:
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    result_area = ft.Column(spacing=8)
    plan_area = ft.ResponsiveRow(spacing=12, run_spacing=12)
    rules_area = ft.ResponsiveRow(spacing=12, run_spacing=12)
    state: dict[str, Any] = {"last_run": None}

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh() -> None:
        try:
            state["all_rows"] = list_alerts(statut="all")
            alert_summary = get_alert_summary(state["all_rows"])
            summary_row.controls = [
                _summary_chip("Alertes ouvertes", alert_summary["open"], DANGER if alert_summary["open"] else SUCCESS, ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
                _summary_chip("Critiques", alert_summary["critical"], DANGER if alert_summary["critical"] else SUCCESS, ft.Icons.PRIORITY_HIGH_OUTLINED),
                _summary_chip("Haut", alert_summary["high"], WARNING if alert_summary["high"] else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
                _summary_chip("Sources", len(alert_summary["by_source"]), PRIMARY, ft.Icons.ACCOUNT_TREE_OUTLINED),
            ]
            render_last_run()
            render_plan()
            render_rules()
        except Exception as exc:
            status.value = str(exc)
            status.color = DANGER

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
        plan = get_alert_action_plan(limit=6, alerts=state.get("all_rows") or [])
        plan_area.controls = [
            ft.Container(
                col={"xs": 12, "md": 6, "xl": 4},
                content=ft.Container(
                    bgcolor=_DK_CARD,
                    border=ft.border.only(
                        left=ft.BorderSide(4, _level_color(str(item.get("top_level") or ""))),
                        top=ft.BorderSide(1, _DK_BORDER),
                        right=ft.BorderSide(1, _DK_BORDER),
                        bottom=ft.BorderSide(1, _DK_BORDER),
                    ),
                    border_radius=10,
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(bgcolor=_DK_HEAD, border_radius=7, padding=7,
                                        content=ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED,
                                            color=_level_color(str(item.get("top_level") or "")), size=16)),
                                    ft.Text(str(item.get("source") or "-"), color=_DK_TEXT, weight=ft.FontWeight.BOLD, expand=True),
                                    ft.Container(bgcolor=_DK_HEAD, border_radius=8,
                                        padding=ft.padding.symmetric(horizontal=8,vertical=3),
                                        content=ft.Text(str(item.get("count") or 0), color=PRIMARY, weight=ft.FontWeight.BOLD, size=13)),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Text(str(item.get("top_message") or ""), color=_DK_TEXT, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(str(item.get("action_hint") or ""), color=_DK_MUTED, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.OutlinedButton(
                                "Ouvrir le module",
                                icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                                disabled=navigate is None or _target_key(str(item.get("source_key") or "")) is None,
                                style=ft.ButtonStyle(color=PRIMARY, side=ft.BorderSide(1,PRIMARY),
                                    shape=ft.RoundedRectangleBorder(radius=8)),
                                on_click=lambda event, key=_target_key(str(item.get("source_key") or "")): navigate(key) if navigate and key else None,
                            ),
                        ],
                        spacing=8,
                    ),
                ),
            )
            for item in plan
        ] or [
            ft.Container(
                col={"xs": 12},
                bgcolor=_DK_CARD,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=10,
                padding=14,
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=18),
                    ft.Text("Aucune action prioritaire ouverte.", color=SUCCESS, size=12),
                ], spacing=10),
            )
        ]

    def render_rules() -> None:
        last = state.get("last_run")
        rules = [
            ("Presence quotidienne", "Prepare la liste du jour et controle les pointages incomplets.", ft.Icons.EVENT_AVAILABLE_OUTLINED, SUCCESS, "attendance"),
            ("Maintenance & actions", "Detecte les echeances date, kilometre et actions en retard.", ft.Icons.HANDYMAN_OUTLINED, WARNING, "maintenance"),
            ("Toolbox Talk", "Assigne les themes et controle la planification bilingue.", ft.Icons.FACT_CHECK_OUTLINED, PRIMARY, "toolbox"),
            ("Formations & EPI", "Surveille expirations, conformite et stocks critiques.", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, DANGER, "formations_epi"),
        ]
        rules_area.controls = [
            ft.Container(
                col={"xs": 12, "md": 6},
                content=ft.Container(
                    bgcolor=_DK_CARD,
                    border=ft.border.only(
                        left=ft.BorderSide(4, color),
                        top=ft.BorderSide(1, _DK_BORDER),
                        right=ft.BorderSide(1, _DK_BORDER),
                        bottom=ft.BorderSide(1, _DK_BORDER),
                    ),
                    border_radius=10,
                    padding=12,
                    content=ft.Row(
                        controls=[
                            ft.Container(bgcolor=_DK_HEAD, border_radius=8, padding=9,
                                content=ft.Icon(icon, color=color, size=20)),
                            ft.Column(
                                controls=[
                                    ft.Text(title, color=_DK_TEXT, size=13, weight=ft.FontWeight.BOLD),
                                    ft.Text(description, color=_DK_MUTED, size=11, max_lines=2),
                                    _status_pill("Etat", *_rule_status(key, last)),
                                ],
                                spacing=5,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ),
            )
            for title, description, icon, color, key in rules
        ]

    root = ft.Column(
        controls=[
            _dk_panel_hdr("Automatisations QHSE", ft.Icons.AUTO_MODE_OUTLINED, PRIMARY, [
                ft.Row(controls=[
                    ft.ElevatedButton("Executer maintenant", icon=ft.Icons.PLAY_CIRCLE_OUTLINED,
                        on_click=run_now,
                        style=ft.ButtonStyle(bgcolor=PRIMARY, color="#FFFFFF",
                            shape=ft.RoundedRectangleBorder(radius=8))),
                    status,
                ], spacing=10, wrap=False, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                summary_row,
                result_area,
            ]),
            _dk_panel_hdr("Regles automatiques surveillees", ft.Icons.SETTINGS_SUGGEST_OUTLINED, WARNING, [
                rules_area,
            ]),
            _dk_panel_hdr("Priorites detectees automatiquement", ft.Icons.AUTO_AWESOME_OUTLINED, SUCCESS, [
                plan_area,
            ]),
        ],
        spacing=14,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    _OV = {PRIMARY:"#0F2D5E", SUCCESS:"#052E16", DANGER:"#3B0F0F", WARNING:"#2D1600", MUTED:"#0A1929"}
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 3},
        content=ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.only(
                left=ft.BorderSide(4, color),
                top=ft.BorderSide(1, _DK_BORDER),
                right=ft.BorderSide(1, _DK_BORDER),
                bottom=ft.BorderSide(1, _DK_BORDER),
            ),
            border_radius=12,
            padding=ft.padding.only(left=14, right=14, top=11, bottom=11),
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Container(width=30, height=30, bgcolor=_OV.get(color, "#0F2D5E"),
                        border_radius=8, alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, color=color, size=15)),
                    ft.Text(label, color=_DK_MUTED, size=10, weight=ft.FontWeight.W_500, expand=True),
                ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
            ], spacing=3),
        ),
    )


def _status_pill(label: str, value: Any, color: str) -> ft.Control:
    _OV = {PRIMARY:"#0F2D5E", SUCCESS:"#052E16", DANGER:"#3B0F0F", WARNING:"#2D1600", MUTED:"#0A1929"}
    return ft.Container(
        bgcolor=_OV.get(color, _DK_CARD),
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row(
            controls=[
                ft.Text(label, color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD),
                ft.Text(str(value), color=color, size=13, weight=ft.FontWeight.BOLD),
            ],
            spacing=7,
            tight=True,
        ),
    )


def _rule_status(key: str, last_run: dict | None) -> tuple[str, str]:
    if last_run is None:
        return "Non teste", MUTED
    if key == "attendance":
        return ("OK", SUCCESS) if last_run.get("attendance_ready") else ("A verifier", WARNING)
    if key == "maintenance":
        m = last_run.get("maintenance") or {}
        count = int(m.get("maintenance") or 0) + int(m.get("actions") or 0)
        return (f"{count} en retard", WARNING) if count else ("OK", SUCCESS)
    if key == "toolbox":
        assigned = int(last_run.get("toolbox_assigned") or 0)
        return (f"{assigned} assignes", PRIMARY) if assigned else ("OK", SUCCESS)
    warnings = last_run.get("warnings") or []
    return ("OK", SUCCESS) if not warnings else (f"{len(warnings)} avert.", WARNING)


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


def _dk_panel_hdr(title: str, icon: str, accent: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER),
        border_radius=12, padding=0, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(controls=[
            ft.Container(
                bgcolor=_DK_HEAD,
                border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                content=ft.Row(controls=[
                    ft.Container(width=3, height=14, bgcolor=accent, border_radius=2),
                    ft.Icon(icon, color=accent, size=18),
                    ft.Text(title, color=_DK_TEXT, size=16, weight=ft.FontWeight.BOLD),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=14),
                content=ft.Column(controls=controls, spacing=12),
            ),
        ], spacing=0),
    )
