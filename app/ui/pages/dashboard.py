from __future__ import annotations

import base64
from typing import Any

import flet as ft

from app.services import get_dashboard_summary
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


CARD_BORDER = "#DBEAFE"
PANEL_BG = "#FFFFFF"
SOFT_BG = "#F8FAFC"
PURPLE = "#8B5CF6"


def dashboard_page() -> ft.Control:
    summary = get_dashboard_summary()
    today = summary["presence_today"]
    ppe = summary["ppe"]
    training = summary["training"]

    kpis = [
        _metric_card(
            "Presence aujourd'hui",
            f"{today['rate']}%",
            SUCCESS if today["rate"] >= 85 else WARNING,
            ft.Icons.CHECK_CIRCLE_OUTLINE,
            f"{today['present']} presents / {today['total']} suivis",
            today["rate"],
        ),
        _metric_card(
            "Effectif disponible",
            f"{summary['workforce_rate']}%",
            PRIMARY,
            ft.Icons.GROUPS_OUTLINED,
            f"{summary['workforce_at_work']} au travail sur {summary['employes']}",
            summary["workforce_rate"],
        ),
        _metric_card(
            "Personnes en break",
            summary["workforce_on_break"],
            WARNING,
            ft.Icons.BEACH_ACCESS_OUTLINED,
            "Break actif aujourd'hui",
            min(summary["workforce_on_break"] * 10, 100),
        ),
        _metric_card(
            "Heures 14 jours",
            summary["trend_total_hours"],
            PRIMARY,
            ft.Icons.ACCESS_TIME_OUTLINED,
            f"Moyenne presence {summary['trend_average_rate']}%",
            min(int(summary["trend_total_hours"]), 100),
        ),
        _metric_card(
            "Alertes critiques",
            summary["alertes_ouvertes"] + summary["breaks_dus"] + ppe["low_stock"] + training["expired"],
            DANGER,
            ft.Icons.REPORT_PROBLEM_OUTLINED,
            "Alertes, breaks, EPI et formations",
            min((summary["alertes_ouvertes"] + summary["breaks_dus"] + ppe["low_stock"] + training["expired"]) * 10, 100),
        ),
    ]

    return ft.Column(
        controls=[
            module_header(
                "Tableau de bord",
                "Vue de pilotage QHSE: presences, disponibilite, EPI, formations, breaks et alertes.",
            ),
            ft.ResponsiveRow(
                controls=[ft.Container(card, col={"sm": 12, "md": 6, "lg": 3}) for card in kpis],
                spacing=14,
                run_spacing=14,
            ),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_attendance_trend_panel(summary), col={"sm": 12, "lg": 8}),
                    ft.Container(_workforce_panel(summary), col={"sm": 12, "lg": 4}),
                ],
                spacing=14,
                run_spacing=14,
            ),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_performance_panel(summary), col={"sm": 12, "lg": 4}),
                    ft.Container(_operational_focus_panel(summary), col={"sm": 12, "lg": 4}),
                    ft.Container(_shift_panel(summary), col={"sm": 12, "lg": 4}),
                ],
                spacing=14,
                run_spacing=14,
            ),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_team_analysis_panel(summary), col={"sm": 12, "lg": 8}),
                    ft.Container(_qhse_panel(summary), col={"sm": 12, "lg": 4}),
                ],
                spacing=14,
                run_spacing=14,
            ),
            ft.Container(_referential_panel(summary), col={"sm": 12}),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )


def _metric_card(label: str, value: Any, color: str, icon: str, subtitle: str, progress: int) -> ft.Control:
    return ft.Container(
        height=132,
        border=ft.border.all(1, CARD_BORDER),
        border_radius=8,
        bgcolor=PANEL_BG,
        padding=16,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            bgcolor=_soft_color(color),
                            border_radius=8,
                            padding=7,
                            content=ft.Icon(icon, color=color, size=20),
                        ),
                        ft.Text(label, color=MUTED, size=12, expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(str(value), size=30, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.ProgressBar(value=max(min(progress, 100), 0) / 100, color=color, bgcolor="#E2E8F0", height=5),
                ft.Text(subtitle, size=11, color=MUTED),
            ],
            spacing=7,
        ),
    )


def _attendance_trend_panel(summary: dict[str, Any]) -> ft.Control:
    trend = summary["presence_trend"]
    chart = _line_chart_svg(
        trend,
        width=760,
        height=260,
        lines=[
            ("present", "Presents", "#2563EB"),
            ("absent", "Absents", "#DC2626"),
        ],
    )
    return _panel(
        "Tendance presence - 14 jours",
        "Courbes journalieres basees sur les listes de presence validees.",
        ft.Column(
            controls=[
                _legend([("Presents", "#2563EB"), ("Absents", "#DC2626")]),
                ft.Image(src=chart, height=260, fit=ft.BoxFit.CONTAIN, expand=True),
            ],
            spacing=8,
        ),
    )


def _workforce_panel(summary: dict[str, Any]) -> ft.Control:
    values = [item for item in summary["workforce_by_state"] if int(item["value"] or 0) > 0]
    if not values:
        values = [{"label": "Aucune donnee", "value": 1, "color": "#CBD5E1"}]
    chart = _donut_svg(values, width=310, height=220)
    return _panel(
        "Disponibilite workforce",
        "Repartition actuelle des employes actifs.",
        ft.Column(
            controls=[
                ft.Image(src=chart, height=220, fit=ft.BoxFit.CONTAIN),
                _legend([(item["label"], item["color"]) for item in values]),
            ],
            spacing=8,
        ),
    )


def _operational_focus_panel(summary: dict[str, Any]) -> ft.Control:
    today = summary["presence_today"]
    items = [
        ("Au travail", summary["workforce_at_work"], SUCCESS, ft.Icons.ENGINEERING_OUTLINED),
        ("En break", summary["workforce_on_break"], WARNING, ft.Icons.BEACH_ACCESS_OUTLINED),
        ("Presents aujourd'hui", today["present"], SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
        ("Absents aujourd'hui", today["absent"], DANGER, ft.Icons.CANCEL_OUTLINED),
        ("Breaks a planifier", summary["breaks_dus"], DANGER, ft.Icons.EVENT_BUSY_OUTLINED),
    ]
    return _panel(
        "Priorites operationnelles",
        "Les points qui demandent une action rapide.",
        ft.Column(controls=[_operation_line(*item) for item in items], spacing=8),
    )


def _performance_panel(summary: dict[str, Any]) -> ft.Control:
    return _panel(
        "Indicateurs de performance",
        "KPI compares aux cibles de pilotage.",
        ft.Column(
            controls=[_kpi_line(item) for item in summary["performance_indicators"]],
            spacing=8,
        ),
    )


def _shift_panel(summary: dict[str, Any]) -> ft.Control:
    rows = summary["presence_by_shift"]
    content = (
        ft.Column(controls=[_shift_line(row) for row in rows], spacing=8)
        if rows
        else ft.Text("Aucune liste de presence enregistree aujourd'hui.", size=12, color=MUTED)
    )
    return _panel(
        "Presence par shift",
        "Comparaison presents / absents pour la journee.",
        content,
    )


def _team_analysis_panel(summary: dict[str, Any]) -> ft.Control:
    rows = summary["workforce_by_team"]
    if not rows:
        content = ft.Text("Aucune equipe active a analyser.", size=12, color=MUTED)
    else:
        content = ft.Column(controls=[_team_line(row) for row in rows], spacing=8)
    return _panel(
        "Analyse par equipe",
        "Au travail, break, presence et disponibilite par groupe operationnel.",
        content,
    )


def _qhse_panel(summary: dict[str, Any]) -> ft.Control:
    ppe = summary["ppe"]
    training = summary["training"]
    items = [
        ("EPI actifs", ppe["items"], PRIMARY, ft.Icons.HEALTH_AND_SAFETY_OUTLINED),
        ("Stock EPI bas", ppe["low_stock"], DANGER if ppe["low_stock"] else SUCCESS, ft.Icons.INVENTORY_2_OUTLINED),
        ("EPI affectes", ppe["assigned"], PRIMARY, ft.Icons.ASSIGNMENT_IND_OUTLINED),
        ("Formations expirees", training["expired"], DANGER if training["expired"] else SUCCESS, ft.Icons.SCHOOL_OUTLINED),
        ("Formations <= 30j", training["soon"], WARNING if training["soon"] else SUCCESS, ft.Icons.UPDATE_OUTLINED),
    ]
    return _panel(
        "Conformite QHSE",
        "Synthese EPI et formations a surveiller.",
        ft.Column(controls=[_operation_line(*item) for item in items], spacing=8),
    )


def _referential_panel(summary: dict[str, Any]) -> ft.Control:
    items = [
        ("Sites", summary["sites"], ft.Icons.LOCATION_ON_OUTLINED),
        ("Groupes", summary["groupes"], ft.Icons.GROUPS_OUTLINED),
        ("Fonctions", summary["fonctions"], ft.Icons.BADGE_OUTLINED),
        ("Types formation", summary["types_formations"], ft.Icons.SCHOOL_OUTLINED),
        ("Types EPI", summary["types_epi"], ft.Icons.HEALTH_AND_SAFETY_OUTLINED),
    ]
    return _panel(
        "Socle referentiel",
        "Donnees de base disponibles pour alimenter les modules QHSE.",
        ft.Row(controls=[_mini_count(*item) for item in items], spacing=10, wrap=True),
    )


def _kpi_line(item: dict[str, Any]) -> ft.Control:
    status = str(item.get("status") or "")
    color = {"bon": SUCCESS, "attention": WARNING, "critique": DANGER}.get(status, MUTED)
    value = f"{item['value']}{item.get('suffix') or ''}"
    target = f"Cible: {item['target']}{item.get('suffix') or ''}"
    progress = _kpi_progress(item)
    return ft.Container(
        bgcolor=SOFT_BG,
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(str(item["label"]), color=TEXT, size=13, expand=True),
                        ft.Text(value, color=color, size=17, weight=ft.FontWeight.BOLD),
                    ],
                ),
                ft.ProgressBar(value=progress, color=color, bgcolor="#E2E8F0", height=7),
                ft.Row(
                    controls=[
                        ft.Text(target, color=MUTED, size=11, expand=True),
                        _status_badge(status, color),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=5,
        ),
    )


def _team_line(row: dict[str, Any]) -> ft.Control:
    availability = int(row.get("availability_rate") or 0)
    attendance = int(row.get("attendance_rate") or 0)
    color = SUCCESS if availability >= 85 else WARNING if availability >= 70 else DANGER
    return ft.Container(
        bgcolor=SOFT_BG,
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(str(row["label"]), color=TEXT, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(f"{availability}% disponible", color=color, weight=ft.FontWeight.BOLD),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.ProgressBar(value=availability / 100, color=color, bgcolor="#E2E8F0", height=7),
                ft.Row(
                    controls=[
                        _mini_badge("Au travail", row["au_travail"], SUCCESS),
                        _mini_badge("Break", row["break"], WARNING),
                        _mini_badge("Permission", row["permission"], PURPLE),
                        _mini_badge("Sick", row["sick"], DANGER),
                        _mini_badge("Presence", f"{attendance}%", PRIMARY),
                    ],
                    wrap=True,
                    spacing=6,
                ),
            ],
            spacing=7,
        ),
    )


def _kpi_progress(item: dict[str, Any]) -> float:
    value = int(item.get("value") or 0)
    target = int(item.get("target") or 0)
    if str(item.get("suffix") or "") == "%":
        return max(min(value, 100), 0) / 100
    if target == 0:
        return 1.0 if value == 0 else max(0.05, 1 - min(value, 10) / 10)
    return max(min(value / target, 1), 0)


def _panel(title: str, subtitle: str, content: ft.Control) -> ft.Control:
    return ft.Container(
        bgcolor=PANEL_BG,
        border=ft.border.all(1, CARD_BORDER),
        border_radius=8,
        padding=18,
        content=ft.Column(
            controls=[
                ft.Text(title, size=17, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text(subtitle, size=12, color=MUTED),
                content,
            ],
            spacing=12,
        ),
    )


def _status_badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(label.upper(), size=10, color=color, weight=ft.FontWeight.BOLD),
    )


def _mini_badge(label: str, value: Any, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Row(
            controls=[
                ft.Container(width=8, height=8, bgcolor=color, border_radius=4),
                ft.Text(f"{label}: {value}", size=11, color=TEXT),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _operation_line(label: str, value: int, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=SOFT_BG,
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=10,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=19),
                ft.Text(label, color=TEXT, size=13, expand=True),
                ft.Text(str(value), color=color, weight=ft.FontWeight.BOLD, size=18),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _shift_line(row: dict[str, Any]) -> ft.Control:
    total = int(row["total"] or 0)
    present = int(row["present"] or 0)
    absent = int(row["absent"] or 0)
    rate = round((present / total) * 100) if total else 0
    return ft.Container(
        bgcolor=SOFT_BG,
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(str(row["label"]), color=TEXT, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(f"{rate}%", color=SUCCESS if rate >= 85 else WARNING, weight=ft.FontWeight.BOLD),
                    ],
                ),
                ft.ProgressBar(value=rate / 100, color=SUCCESS if rate >= 85 else WARNING, bgcolor="#FECACA", height=7),
                ft.Text(f"{present} presents | {absent} absents | total {total}", color=MUTED, size=11),
            ],
            spacing=5,
        ),
    )


def _mini_count(label: str, value: int, icon: str) -> ft.Control:
    return ft.Container(
        width=188,
        bgcolor=SOFT_BG,
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=PRIMARY, size=20),
                ft.Column(
                    controls=[
                        ft.Text(label, color=MUTED, size=12),
                        ft.Text(str(value), color=TEXT, weight=ft.FontWeight.BOLD, size=20),
                    ],
                    spacing=2,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _legend(items: list[tuple[str, str]]) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                    ft.Text(label, size=11, color=MUTED),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for label, color in items
        ],
        wrap=True,
        spacing=12,
    )


def _line_chart_svg(
    data: list[dict[str, Any]],
    width: int,
    height: int,
    lines: list[tuple[str, str, str]],
) -> str:
    padding_left = 44
    padding_top = 18
    padding_right = 20
    padding_bottom = 42
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom
    max_value = max([int(item.get(key) or 0) for item in data for key, _, _ in lines] + [1])
    x_step = chart_w / max(len(data) - 1, 1)

    grid = []
    for tick in range(5):
        value = round((max_value / 4) * tick)
        y = padding_top + chart_h - ((value / max_value) * chart_h if max_value else 0)
        grid.append(
            f'<line x1="{padding_left}" y1="{y:.1f}" x2="{width - padding_right}" y2="{y:.1f}" stroke="#E2E8F0" stroke-width="1"/>'
            f'<text x="8" y="{y + 4:.1f}" font-size="10" fill="#64748B">{value}</text>'
        )

    series = []
    for key, label, color in lines:
        points = []
        dots = []
        for index, item in enumerate(data):
            x = padding_left + index * x_step
            value = int(item.get(key) or 0)
            y = padding_top + chart_h - ((value / max_value) * chart_h if max_value else 0)
            points.append(f"{x:.1f},{y:.1f}")
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"><title>{_xml(label)} {value}</title></circle>')
        series.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
        series.extend(dots)

    labels = []
    for index, item in enumerate(data):
        if index % 2 == 0 or index == len(data) - 1:
            x = padding_left + index * x_step
            labels.append(f'<text x="{x:.1f}" y="{height - 16}" font-size="10" fill="#64748B" text-anchor="middle">{_xml(str(item["date"])[5:])}</text>')

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect width="{width}" height="{height}" rx="12" fill="#FFFFFF"/>
        {''.join(grid)}
        <line x1="{padding_left}" y1="{padding_top}" x2="{padding_left}" y2="{height - padding_bottom}" stroke="#CBD5E1"/>
        <line x1="{padding_left}" y1="{height - padding_bottom}" x2="{width - padding_right}" y2="{height - padding_bottom}" stroke="#CBD5E1"/>
        {''.join(series)}
        {''.join(labels)}
    </svg>
    """
    return _svg_src(svg)


def _donut_svg(values: list[dict[str, Any]], width: int, height: int) -> str:
    total = sum(int(item.get("value") or 0) for item in values) or 1
    cx = width / 2
    cy = height / 2
    radius = min(width, height) / 2 - 24
    circumference = 2 * 3.14159 * radius
    offset = 0.0
    rings = []
    for item in values:
        value = int(item.get("value") or 0)
        length = (value / total) * circumference
        rings.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{item["color"]}" stroke-width="26" '
            f'stroke-dasharray="{length:.2f} {circumference - length:.2f}" stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += length
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect width="{width}" height="{height}" rx="12" fill="#FFFFFF"/>
        <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#E2E8F0" stroke-width="26"/>
        {''.join(rings)}
        <text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="26" font-weight="700" fill="#172033">{total}</text>
        <text x="{cx}" y="{cy + 18}" text-anchor="middle" font-size="11" fill="#64748B">employees</text>
    </svg>
    """
    return _svg_src(svg)


def _svg_src(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _soft_color(color: str) -> str:
    return {
        PRIMARY: "#DBEAFE",
        SUCCESS: "#DCFCE7",
        DANGER: "#FEE2E2",
        WARNING: "#FEF3C7",
        PURPLE: "#EDE9FE",
    }.get(color, "#E2E8F0")


def _xml(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
