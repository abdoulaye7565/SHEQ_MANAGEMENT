from __future__ import annotations

from typing import Any

import flet as ft

from app.services import (
    create_manual_alert,
    delete_manual_alert,
    export_rows_xlsx,
    filter_alert_rows,
    get_alert_action_plan,
    get_alert_filter_options,
    get_alert_summary,
    list_alerts,
    update_manual_alert_status,
)
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


LEVEL_COLORS = {
    "bas": SUCCESS,
    "moyen": PRIMARY,
    "haut": WARNING,
    "critique": DANGER,
}

_WHITE      = "#0D2040"
_SURFACE    = "#071321"
_BLUE_SOFT  = "#0F2D5E"
_BLUE_BDR   = "#2563EB"
_RED_SOFT   = "#3B0F0F"
_RED_BDR    = "#DC2626"
_GREEN_SOFT = "#052E16"
_GREEN_BDR  = "#16A34A"
_AMBER_SOFT = "#2D1600"
_AMBER_BDR  = "#F59E0B"
_SLATE      = "#0A1929"
_SLATE_BDR  = "#1E3A5F"
_DK_TEXT    = "#E2E8F0"
_DK_MUTED   = "#9DB0C5"
_DK_HEAD    = "#112240"
_DK_TRACK   = "#1A3050"


def alerts_page(navigate: Any | None = None, show_header: bool = True) -> ft.Control:
    status = ft.Text("", size=12, color=MUTED)
    table_status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    table_area = ft.Column(spacing=8)
    source_area = ft.Row(spacing=6, wrap=True)
    action_plan_area = ft.ResponsiveRow(spacing=12, run_spacing=12)
    state: dict[str, Any] = {"all_rows": []}

    options = get_alert_filter_options()

    search_field = ft.TextField(
        label="Recherche",
        prefix_icon=ft.Icons.SEARCH,
        width=240,
        border_radius=8,
        filled=True,
        fill_color=_WHITE,
    )
    source_filter = ft.Dropdown(
        label="Source",
        value="all",
        width=200,
        border_radius=8,
        filled=True,
        fill_color=_WHITE,
        options=[ft.dropdown.Option(row["value"], row["label"]) for row in options["sources"]],
    )
    level_filter = ft.Dropdown(
        label="Niveau",
        value="all",
        width=160,
        border_radius=8,
        filled=True,
        fill_color=_WHITE,
        options=[ft.dropdown.Option(row["value"], row["label"]) for row in options["levels"]],
    )
    status_filter = ft.Dropdown(
        label="Statut",
        value="ouverte",
        width=160,
        border_radius=8,
        filled=True,
        fill_color=_WHITE,
        options=[ft.dropdown.Option(row["value"], row["label"]) for row in options["statuses"]],
    )
    manual_type_field = ft.TextField(
        label="Type d'alerte",
        width=220,
        border_radius=8,
        filled=True,
        fill_color=_WHITE,
    )
    manual_level_field = ft.Dropdown(
        label="Niveau",
        value="moyen",
        width=150,
        border_radius=8,
        filled=True,
        fill_color=_WHITE,
        options=[
            ft.dropdown.Option("bas", "Bas"),
            ft.dropdown.Option("moyen", "Moyen"),
            ft.dropdown.Option("haut", "Haut"),
            ft.dropdown.Option("critique", "Critique"),
        ],
    )
    manual_message_field = ft.TextField(
        label="Message",
        multiline=True,
        min_lines=2,
        max_lines=3,
        expand=True,
        border_radius=8,
        filled=True,
        fill_color=_WHITE,
    )

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color
        table_status.value = message
        table_status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def current_rows() -> list[dict[str, Any]]:
        return filter_alert_rows(
            state["all_rows"],
            source=str(source_filter.value or "all"),
            niveau=str(level_filter.value or "all"),
            statut=str(status_filter.value or "ouverte"),
            search=str(search_field.value or ""),
        )

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            state["all_rows"] = list_alerts(statut="all")
            summary = get_alert_summary(state["all_rows"])
            rows = current_rows()
            render_summary(summary)
            render_sources(summary)
            render_action_plan()
            render_table(rows)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        source_filter.value = "all"
        level_filter.value = "all"
        status_filter.value = "ouverte"
        refresh()

    def save_manual_alert(event: ft.ControlEvent | None = None) -> None:
        try:
            create_manual_alert(
                manual_type_field.value,
                manual_message_field.value,
                str(manual_level_field.value or "moyen"),
            )
            manual_type_field.value = ""
            manual_message_field.value = ""
            notify("Alerte manuelle creee.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def close_manual(alert_id: str, new_status: str) -> None:
        try:
            update_manual_alert_status(_manual_id(alert_id), new_status)
            notify("Statut d'alerte mis a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def remove_manual(alert_id: str) -> None:
        try:
            delete_manual_alert(_manual_id(alert_id))
            notify("Alerte supprimee.", MUTED)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_alerts(event: ft.ControlEvent | None = None) -> None:
        rows = current_rows()
        output = export_rows_xlsx(
            "alertes_qhse_filtrees.xlsx",
            "Alertes QHSE",
            ["Date", "Source", "Type", "Niveau", "Statut", "Reference", "Message", "Action"],
            [
                [
                    row.get("date_creation") or "",
                    row.get("source") or "",
                    row.get("type_alerte") or "",
                    row.get("niveau_label") or "",
                    row.get("statut") or "",
                    row.get("reference_label") or "",
                    row.get("message") or "",
                    row.get("action_hint") or "",
                ]
                for row in rows
            ],
        )
        notify(f"Export Excel cree: {output}", SUCCESS)
        _update()

    def render_summary(summary: dict[str, Any]) -> None:
        summary_row.controls = [
            _kpi_chip("Ouvertes",  summary["open"],     DANGER if summary["open"]     else SUCCESS, ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            _kpi_chip("Critiques", summary["critical"], DANGER if summary["critical"] else SUCCESS, ft.Icons.PRIORITY_HIGH_OUTLINED),
            _kpi_chip("Haut",      summary["high"],     WARNING if summary["high"]    else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _kpi_chip("Moyen",     summary["medium"],   PRIMARY, ft.Icons.INFO_OUTLINED),
            _kpi_chip("Total",     summary["total"],    MUTED,   ft.Icons.FORMAT_LIST_BULLETED_OUTLINED),
        ]

    def render_sources(summary: dict[str, Any]) -> None:
        items = sorted(summary["by_source"].items())
        source_area.controls = [_source_chip(label, value) for label, value in items] or [
            ft.Container(
                bgcolor=_GREEN_SOFT,
                border=ft.border.all(1, _GREEN_BDR),
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=12, vertical=5),
                content=ft.Text("Aucune source en alerte", size=12, color=SUCCESS, weight=ft.FontWeight.W_500),
            )
        ]

    def render_action_plan() -> None:
        plan = get_alert_action_plan(limit=3, alerts=state["all_rows"])
        action_plan_area.controls = [
            _action_plan_card(item, navigate)
            for item in plan
        ] or [
            ft.Container(
                col={"xs": 12},
                bgcolor=_GREEN_SOFT,
                border=ft.border.all(1, _GREEN_BDR),
                border_radius=10,
                padding=14,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=20),
                        ft.Text("Aucune action prioritaire ouverte.", color=SUCCESS, size=13),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        ]

    def render_table(rows: list[dict[str, Any]]) -> None:
        count_color = DANGER if rows else SUCCESS
        table_area.controls = [
            ft.Row(
                controls=[
                    ft.Container(
                        bgcolor=_BLUE_SOFT,
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        content=ft.Text(
                            f"{len(rows)} alerte(s)",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=count_color,
                        ),
                    ),
                    ft.Container(expand=True),
                    table_status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(
                controls=[_alert_card(row, close_manual, remove_manual, navigate) for row in rows],
                spacing=8,
            )
            if rows
            else ft.Container(
                bgcolor=_GREEN_SOFT,
                border=ft.border.all(1, _GREEN_BDR),
                border_radius=10,
                padding=20,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=22),
                        ft.Text("Aucune alerte pour les filtres selectionnes.", size=13, color=SUCCESS),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        ]

    search_field.on_submit = refresh
    search_field.on_change = refresh
    for control in (source_filter, level_filter, status_filter):
        control.on_change = refresh

    # ── barre de filtres ─────────────────────────────────────────────────────
    filter_bar = ft.Container(
        bgcolor=_WHITE,
        border=ft.border.all(1, _SLATE_BDR),
        border_radius=12,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.only(bottom=ft.BorderSide(1, _SLATE_BDR)),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=14, bgcolor=PRIMARY, border_radius=2),
                            ft.Icon(ft.Icons.FILTER_ALT_OUTLINED, color=PRIMARY, size=18),
                            ft.Text("Filtres & KPI", size=14, weight=ft.FontWeight.BOLD, color=_DK_TEXT, expand=True),
                            status,
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    search_field,
                                    source_filter,
                                    level_filter,
                                    status_filter,
                                    ft.IconButton(
                                        icon=ft.Icons.SYNC_OUTLINED,
                                        tooltip="Actualiser",
                                        icon_color=PRIMARY,
                                        on_click=refresh,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.RESTART_ALT_OUTLINED,
                                        tooltip="Reinitialiser",
                                        icon_color=_DK_MUTED,
                                        on_click=reset_filters,
                                    ),
                                    ft.OutlinedButton(
                                        "Exporter Excel",
                                        icon=ft.Icons.DOWNLOAD_OUTLINED,
                                        on_click=export_alerts,
                                        style=ft.ButtonStyle(
                                            color=SUCCESS,
                                            side=ft.BorderSide(1, SUCCESS),
                                            shape=ft.RoundedRectangleBorder(radius=8),
                                        ),
                                    ),
                                ],
                                spacing=10,
                                wrap=True,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            summary_row,
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text("Par source", size=11, color=_DK_MUTED, weight=ft.FontWeight.W_500),
                                        source_area,
                                    ],
                                    spacing=6,
                                ),
                            ),
                        ],
                        spacing=12,
                    ),
                ),
            ],
            spacing=0,
        ),
    )

    # ── plan d'action ────────────────────────────────────────────────────────
    action_plan_section = ft.Container(
        bgcolor=_WHITE,
        border=ft.border.all(1, _SLATE_BDR),
        border_radius=12,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.only(bottom=ft.BorderSide(1, _SLATE_BDR)),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=14, bgcolor=WARNING, border_radius=2),
                            ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color=WARNING, size=18),
                            ft.Text("Plan d'action prioritaire", size=14, weight=ft.FontWeight.BOLD, color=_DK_TEXT, expand=True),
                            ft.Text("Classe automatiquement par criticite et source", size=11, color=_DK_MUTED),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    content=action_plan_area,
                ),
            ],
            spacing=0,
        ),
    )

    table_section = ft.Container(
        bgcolor=_WHITE,
        border=ft.border.all(1, _SLATE_BDR),
        border_radius=12,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.only(bottom=ft.BorderSide(1, _SLATE_BDR)),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=14, bgcolor=DANGER, border_radius=2),
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, color=DANGER, size=18),
                            ft.Text("File de traitement", color=_DK_TEXT, size=14, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    content=table_area,
                ),
            ],
            spacing=0,
        ),
    )

    manual_section = ft.Container(
        bgcolor=_WHITE,
        border=ft.border.all(1, _SLATE_BDR),
        border_radius=12,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.ExpansionTile(
            title="Nouvelle alerte manuelle",
            leading=ft.Icon(ft.Icons.ADD_ALERT_OUTLINED, color=PRIMARY, size=18),
            expanded=False,
            controls_padding=ft.padding.only(left=16, right=16, bottom=16),
            controls=[
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[manual_type_field, manual_level_field, manual_message_field],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "Creer l'alerte",
                                    icon=ft.Icons.ADD_ALERT_OUTLINED,
                                    on_click=save_manual_alert,
                                    style=ft.ButtonStyle(
                                        bgcolor=DANGER,
                                        color="#FFFFFF",
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                    ),
                                ),
                                ft.Text(
                                    "Les alertes automatiques se ferment dans leur module d'origine.",
                                    size=12,
                                    color=_DK_MUTED,
                                ),
                            ],
                            spacing=12,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=12,
                ),
            ],
        ),
    )

    controls: list[ft.Control] = []
    if show_header:
        controls.append(
            module_header(
                "Alertes",
                "Centralisation des signaux QHSE: formations, presence, breaks, badges, EPI et stock.",
            )
        )
    controls.extend([filter_bar, action_plan_section, table_section, manual_section])

    root = ft.Column(
        controls=controls,
        spacing=14,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


# ── composants ───────────────────────────────────────────────────────────────

def _alert_card(row: dict[str, Any], close_action: Any, delete_action: Any, navigate: Any | None) -> ft.Control:
    color = LEVEL_COLORS.get(str(row.get("niveau") or ""), MUTED)
    soft = _level_soft(color)
    can_close = bool(row.get("can_close"))
    target_key = _target_key(str(row.get("source_key") or ""))
    return ft.Container(
        bgcolor=_WHITE,
        border=ft.border.only(
            left=ft.BorderSide(4, color),
            top=ft.BorderSide(1, _SLATE_BDR),
            right=ft.BorderSide(1, _SLATE_BDR),
            bottom=ft.BorderSide(1, _SLATE_BDR),
        ),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        _level_badge(str(row.get("niveau_label") or "-"), color),
                        ft.Container(
                            bgcolor=_SLATE,
                            border_radius=6,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            content=ft.Text(str(row.get("source") or "-"), size=11, color=_DK_MUTED, weight=ft.FontWeight.W_500),
                        ),
                        ft.Text(str(row.get("type_alerte") or "-"), color=_DK_TEXT, weight=ft.FontWeight.BOLD, expand=True, size=13),
                        ft.Container(
                            bgcolor=_SLATE,
                            border_radius=6,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            content=ft.Text(str(row.get("statut") or "-"), size=11, color=_DK_MUTED),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(str(row.get("message") or "-"), color=_DK_TEXT, size=13),
                ft.Row(
                    controls=[
                        ft.Container(
                            bgcolor=soft,
                            border=ft.border.all(1, _level_border(color)),
                            border_radius=6,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            content=ft.Text(str(row.get("reference_label") or "-"), color=color, size=11),
                        ),
                        ft.Text(str(row.get("action_hint") or "-"), color=_DK_MUTED, size=12, expand=True),
                        ft.Row(
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.DONE_OUTLINED,
                                    tooltip="Marquer traitee",
                                    icon_color=SUCCESS,
                                    icon_size=18,
                                    visible=can_close and row.get("statut") == "ouverte",
                                    on_click=lambda event, current=row: close_action(current["id"], "traitee"),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.VISIBILITY_OFF_OUTLINED,
                                    tooltip="Ignorer",
                                    icon_color=WARNING,
                                    icon_size=18,
                                    visible=can_close and row.get("statut") == "ouverte",
                                    on_click=lambda event, current=row: close_action(current["id"], "ignoree"),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    tooltip="Supprimer",
                                    icon_color=DANGER,
                                    icon_size=18,
                                    visible=can_close,
                                    on_click=lambda event, current=row: delete_action(current["id"]),
                                ),
                                ft.OutlinedButton(
                                    "Ouvrir",
                                    icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                                    visible=navigate is not None and target_key is not None,
                                    style=ft.ButtonStyle(
                                        color=color,
                                        side=ft.BorderSide(1, color),
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                    ),
                                    on_click=lambda event, key=target_key: navigate(key) if navigate and key is not None else None,
                                ),
                            ],
                            spacing=2,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
        ),
    )


def _action_plan_card(item: dict[str, Any], navigate: Any | None) -> ft.Control:
    color = LEVEL_COLORS.get(str(item.get("top_level") or ""), MUTED)
    soft = _level_soft(color)
    border = _level_border(color)
    target_key = _target_key(str(item.get("source_key") or ""))
    return ft.Container(
        col={"xs": 12, "md": 6, "xl": 4},
        bgcolor=_WHITE,
        border=ft.border.only(
            left=ft.BorderSide(4, color),
            top=ft.BorderSide(1, _SLATE_BDR),
            right=ft.BorderSide(1, _SLATE_BDR),
            bottom=ft.BorderSide(1, _SLATE_BDR),
        ),
        border_radius=10,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.only(bottom=ft.BorderSide(1, _SLATE_BDR)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row(
                        controls=[
                            _level_badge(_level_label(str(item.get("top_level") or "bas")), color),
                            ft.Text(str(item.get("source") or "-"), color=_DK_TEXT, weight=ft.FontWeight.BOLD, expand=True, size=13),
                            ft.Container(
                                bgcolor=color,
                                border_radius=12,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                content=ft.Text(str(item.get("count") or 0), color="#FFFFFF", size=11, weight=ft.FontWeight.BOLD),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    content=ft.Column(
                        controls=[
                            ft.Text(str(item.get("top_message") or ""), color=_DK_TEXT, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(str(item.get("action_hint") or ""), color=_DK_MUTED, size=11, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.OutlinedButton(
                                "Ouvrir le module",
                                icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                                disabled=navigate is None or target_key is None,
                                style=ft.ButtonStyle(
                                    color=color,
                                    side=ft.BorderSide(1, color),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=lambda event, key=target_key: navigate(key) if navigate and key else None,
                            ),
                        ],
                        spacing=8,
                    ),
                ),
            ],
            spacing=0,
        ),
    )


def _kpi_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
        content=ft.Container(
            bgcolor=_WHITE,
            border=ft.border.only(
                left=ft.BorderSide(4, color),
                top=ft.BorderSide(1, _SLATE_BDR),
                right=ft.BorderSide(1, _SLATE_BDR),
                bottom=ft.BorderSide(1, _SLATE_BDR),
            ),
            border_radius=12, padding=0, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Container(
                expand=True,
                padding=ft.padding.only(left=14, right=14, top=12, bottom=12),
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Container(width=32, height=32, bgcolor=_level_soft(color),
                            border_radius=8, alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=color, size=16)),
                        ft.Text(str(label), color=_DK_MUTED, size=10, weight=ft.FontWeight.W_500, expand=True, max_lines=2),
                    ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                ], spacing=4),
            ),
        ),
    )


def _source_chip(label: str, value: int) -> ft.Control:
    clr = DANGER if value > 0 else SUCCESS
    return ft.Container(
        bgcolor=_level_soft(clr),
        border=ft.border.all(1, _level_border(clr)),
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=12, vertical=5),
        content=ft.Row(
            controls=[
                ft.Text(label, size=12, color=_DK_TEXT, weight=ft.FontWeight.W_500),
                ft.Container(
                    bgcolor=clr,
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=6, vertical=1),
                    content=ft.Text(str(value), size=11, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
    )


def _level_badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=_level_soft(color),
        border=ft.border.all(1, _level_border(color)),
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=9, vertical=4),
        content=ft.Text(label, size=11, color=color, weight=ft.FontWeight.BOLD),
    )


def _level_soft(color: str) -> str:
    return {DANGER: _RED_SOFT, WARNING: _AMBER_SOFT, SUCCESS: _GREEN_SOFT, PRIMARY: _BLUE_SOFT}.get(color, _SLATE)


def _level_border(color: str) -> str:
    return {DANGER: _RED_BDR, WARNING: _AMBER_BDR, SUCCESS: _GREEN_BDR, PRIMARY: _BLUE_BDR}.get(color, _SLATE_BDR)


def _level_label(value: str) -> str:
    return {"bas": "Bas", "moyen": "Moyen", "haut": "Haut", "critique": "Critique"}.get(value, value or "-")


def _manual_id(alert_id: str) -> int:
    return int(str(alert_id).split(":", 1)[1])


def _target_key(source_key: str) -> str | None:
    return {
        "breaks": "EmployeeManagement",
        "attendance": "TimeSheet",
        "ppe": "Ppe",
        "maintenance": "MaintenanceActions",
        "training": "TrainingManagement",
        "toolbox": "ToolboxTalk",
    }.get(source_key)
