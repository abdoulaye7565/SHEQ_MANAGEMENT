from __future__ import annotations

import base64
from datetime import date
from typing import Any

import flet as ft

from app.services import get_dashboard_summary, list_admin_audit
from app.services.alert_service import list_alerts
from app.services.app_logger import get_logger
from app.services.maintenance_action_service import list_equipment_maintenance
from app.services.monthly_timesheet_service import current_monthly_timesheet_month, get_monthly_10h_timesheet
from app.ui.theme import DANGER, PRIMARY, SUCCESS, WARNING

_LOGGER = get_logger(__name__)


# ── palette cockpit dark ──────────────────────────────────────────────────────
_CARD   = "#0D2040"   # fond de carte principale
_CARD2  = "#0A1929"   # fond alternatif (rows de liste)
_HEAD   = "#112240"   # zone titre de panneau
_BORDER = "#1E3A5F"   # bordure subtile
_TEXT   = "#E2E8F0"   # texte principal sur fond sombre
_MUTED  = "#9DB0C5"   # texte secondaire sur fond sombre
_WHITE  = "#FFFFFF"
_PURPLE = "#8B5CF6"
_TRACK  = "#1A3050"   # piste ProgressBar sur fond sombre


def _ov(color: str) -> str:
    return {
        PRIMARY: "#0F2D5E",
        SUCCESS: "#052E16",
        DANGER:  "#3B0F0F",
        WARNING: "#2D1600",
        _PURPLE: "#1E0A4E",
    }.get(color, "#111F35")


def _bdr(color: str) -> str:
    return {
        PRIMARY: "#2563EB",
        SUCCESS: "#16A34A",
        DANGER:  "#DC2626",
        WARNING: "#D97706",
        _PURPLE: "#7C3AED",
    }.get(color, "#1E3A5F")


# ── page principale ───────────────────────────────────────────────────────────

def dashboard_page(navigate: Any | None = None, user: dict[str, object] | None = None) -> ft.Control:
    summary          = get_dashboard_summary()
    today            = summary["presence_today"]
    ppe              = summary["ppe"]
    training         = summary["training"]
    maintenance      = summary["maintenance_actions"]
    alerts           = _safe_rows(lambda: list_alerts(statut="ouverte"))[:6]
    maintenance_rows = _safe_rows(lambda: list_equipment_maintenance(limit=6))
    audit_rows       = _safe_rows(lambda: list_admin_audit(limit=6))
    timesheet        = _safe_dict(lambda: get_monthly_10h_timesheet(current_monthly_timesheet_month()))
    ts_summary       = timesheet.get("summary") or {}
    ts_rows          = timesheet.get("rows") or []
    validated_ts     = sum(1 for r in ts_rows if int(r.get("unfilled_days") or 0) == 0)
    critical_total   = (
        summary["alertes_ouvertes"]
        + summary["breaks_dus"]
        + ppe["low_stock"]
        + training["expired"]
        + maintenance["maintenance_late"]
        + maintenance["actions_late"]
        + maintenance["maintenance_critical"]
        + maintenance["actions_critical"]
    )

    kpis = [
        ("Employes actifs",     summary["employes"],              SUCCESS,  ft.Icons.GROUPS_OUTLINED,              "Personnel actif"),
        ("Presents",            today["present"],                 SUCCESS,  ft.Icons.CHECK_CIRCLE_OUTLINE,         f"{today['rate']}% taux de presence"),
        ("Absents",             today["absent"],                  DANGER,   ft.Icons.CANCEL_OUTLINED,              f"{max(100 - today['rate'], 0)}% du suivi"),
        ("En break",            summary["workforce_on_break"],    WARNING,  ft.Icons.COFFEE_OUTLINED,              "Actifs hors site"),
        ("Formations expirees", training["expired"],              DANGER,   ft.Icons.SCHOOL_OUTLINED,              "A renouveler d'urgence"),
        ("EPI stock critique",  ppe["low_stock"],                 DANGER,   ft.Icons.HEALTH_AND_SAFETY_OUTLINED,   "Articles sous seuil"),
        ("Alertes critiques",   critical_total,                   DANGER,   ft.Icons.REPORT_PROBLEM_OUTLINED,      "Actions requises"),
        ("Maintenance retard",  maintenance["maintenance_late"],  WARNING,  ft.Icons.HANDYMAN_OUTLINED,            "Interventions dues"),
        ("Heures 14 jours",     summary["trend_total_hours"],     PRIMARY,  ft.Icons.ACCESS_TIME_OUTLINED,         "Temps travaille total"),
        ("Timesheets",          f"{validated_ts}/{ts_summary.get('employees') or 0}", SUCCESS, ft.Icons.FACT_CHECK_OUTLINED, "Periode en cours"),
    ]

    return ft.Column(
        controls=[
            _welcome_hero(summary, critical_total, user or {}),
            *([_critical_banner(summary, training, maintenance, navigate)] if critical_total > 0 else []),
            _section_label("INDICATEURS CLES DE PERFORMANCE"),
            ft.ResponsiveRow(
                controls=[ft.Container(_kpi_card(*kpi), col={"sm": 6, "md": 4, "lg": 2.4}) for kpi in kpis],
                spacing=10, run_spacing=10,
            ),
            _section_label("PERFORMANCE & CONFORMITE"),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_performance_panel(summary), col={"sm": 12, "lg": 6}),
                    ft.Container(_compliance_panel(summary), col={"sm": 12, "lg": 6}),
                ],
                spacing=10, run_spacing=10,
            ),
            _section_label("TENDANCES & REPARTITION DU PERSONNEL"),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_attendance_trend_panel(summary), col={"sm": 12, "lg": 7}),
                    ft.Container(_workforce_panel(summary), col={"sm": 12, "md": 6, "lg": 2.5}),
                    ft.Container(_shift_panel(summary), col={"sm": 12, "md": 6, "lg": 2.5}),
                ],
                spacing=10, run_spacing=10,
            ),
            _section_label("TRAITEMENT EN COURS"),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_alert_list_panel(alerts, navigate), col={"sm": 12, "lg": 4}),
                    ft.Container(_maintenance_list_panel(maintenance_rows, navigate), col={"sm": 12, "lg": 4}),
                    ft.Container(_timesheet_panel(timesheet, navigate), col={"sm": 12, "lg": 4}),
                ],
                spacing=10, run_spacing=10,
            ),
            _section_label("SUIVI OPERATIONNEL"),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_operational_focus_panel(summary), col={"sm": 12, "lg": 6}),
                    ft.Container(_recent_activity_panel(audit_rows), col={"sm": 12, "lg": 6}),
                ],
                spacing=10, run_spacing=10,
            ),
            _section_label("ACCES RAPIDE & ASSISTANT"),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_quick_actions_panel(navigate), col={"sm": 12, "lg": 7}),
                    ft.Container(_assistant_panel(navigate), col={"sm": 12, "lg": 5}),
                ],
                spacing=10, run_spacing=10,
            ),
        ],
        spacing=14,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )


# ── utilitaires ───────────────────────────────────────────────────────────────

def _safe_rows(loader: Any) -> list[dict[str, Any]]:
    try:
        return list(loader())
    except Exception as exc:
        _LOGGER.warning("Dashboard data load failed [%s]: %s", getattr(loader, "__name__", loader), exc, exc_info=True)
        return []


def _safe_dict(loader: Any) -> dict[str, Any]:
    try:
        return dict(loader())
    except Exception as exc:
        _LOGGER.warning("Dashboard data load failed [%s]: %s", getattr(loader, "__name__", loader), exc, exc_info=True)
        return {}


def _section_label(text: str) -> ft.Control:
    return ft.Container(
        padding=ft.padding.only(left=2, top=6, bottom=2),
        content=ft.Row(
            controls=[
                ft.Container(width=3, height=13, bgcolor=PRIMARY, border_radius=2),
                ft.Text(text, size=10, color=_MUTED, weight=ft.FontWeight.W_700),
                ft.Container(expand=True, height=1, bgcolor=_BORDER),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


# ── hero de bienvenue ─────────────────────────────────────────────────────────

def _welcome_hero(summary: dict[str, Any], critical_total: int, user: dict[str, object]) -> ft.Control:
    username  = str(user.get("username") or "Utilisateur").strip()
    role      = str(user.get("role") or "QHSE").strip()
    today_str = date.today().strftime("%A %d %B %Y").capitalize()
    today     = summary["presence_today"]

    return ft.Container(
        bgcolor="#0F2545",
        border=ft.border.all(1, _BORDER),
        border_radius=14,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor="#112240",
                    padding=ft.padding.symmetric(horizontal=24, vertical=20),
                    content=ft.Row(
                        controls=[
                            # Identite
                            ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                width=52, height=52,
                                                bgcolor=PRIMARY,
                                                border_radius=14,
                                                alignment=ft.Alignment(0, 0),
                                                content=ft.Icon(ft.Icons.SHIELD_OUTLINED, color=_WHITE, size=28),
                                            ),
                                            ft.Column(
                                                controls=[
                                                    ft.Text("OREZONE QHSE Platform", size=11, color=_MUTED, weight=ft.FontWeight.W_600),
                                                    ft.Text(f"Bonjour, {username}", size=24, color=_WHITE, weight=ft.FontWeight.BOLD),
                                                ],
                                                spacing=2,
                                            ),
                                        ],
                                        spacing=14,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    ft.Row(
                                        controls=[
                                            _hero_tag(ft.Icons.BADGE_OUTLINED,         role,                        PRIMARY),
                                            _hero_tag(ft.Icons.CALENDAR_TODAY_OUTLINED, today_str,                  _MUTED),
                                            _hero_tag(ft.Icons.LOCATION_ON_OUTLINED,   f"{summary['sites']} sites", SUCCESS),
                                        ],
                                        spacing=8,
                                        wrap=True,
                                    ),
                                ],
                                spacing=14,
                                expand=True,
                            ),
                            # KPIs hero
                            ft.Row(
                                controls=[
                                    _hero_kpi("Actifs",   summary["employes"], SUCCESS),
                                    _hero_kpi("Presents", today["present"],    SUCCESS if today["rate"] >= 85 else WARNING),
                                    _hero_kpi("Alertes",  critical_total,      DANGER if critical_total else SUCCESS),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=24,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    bgcolor="#091A30",
                    padding=ft.padding.symmetric(horizontal=24, vertical=9),
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                width=8, height=8,
                                bgcolor=SUCCESS,
                                border_radius=4,
                            ),
                            ft.Text("Systeme operationnel", size=11, color=_MUTED),
                            ft.Container(width=1, height=12, bgcolor=_BORDER),
                            ft.Text("ISO 45001  •  ISO 9001  •  ISO 14001", size=11, color=_MUTED),
                            ft.Container(expand=True),
                            ft.Text(
                                f"Presence du jour : {today['rate']}%",
                                size=11,
                                color=SUCCESS if today["rate"] >= 85 else WARNING,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            ],
            spacing=0,
        ),
    )


def _critical_banner(
    summary: dict[str, Any],
    training: dict[str, Any],
    maintenance: dict[str, Any],
    navigate: Any | None,
) -> ft.Control:
    items: list[tuple[str, str, str, str]] = []
    if maintenance.get("maintenance_late", 0):
        items.append((ft.Icons.HANDYMAN_OUTLINED, f"{maintenance['maintenance_late']} maintenance(s) en retard", DANGER, "MaintenanceActions"))
    if maintenance.get("actions_critical", 0):
        items.append((ft.Icons.PRIORITY_HIGH_OUTLINED, f"{maintenance['actions_critical']} action(s) critique(s)", DANGER, "MaintenanceActions"))
    if training.get("expired", 0):
        items.append((ft.Icons.SCHOOL_OUTLINED, f"{training['expired']} formation(s) expiree(s)", WARNING, "TrainingManagement"))
    if summary.get("breaks_dus", 0):
        items.append((ft.Icons.COFFEE_OUTLINED, f"{summary['breaks_dus']} break(s) a planifier", WARNING, "EmployeeManagement"))
    if not items:
        return ft.Container()
    return ft.Container(
        bgcolor="#1A0A0A",
        border=ft.border.all(1, DANGER),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=DANGER, size=18),
                ft.Text("ACTIONS REQUISES :", color=DANGER, size=12, weight=ft.FontWeight.W_700),
                ft.Row(
                    controls=[
                        ft.Container(
                            bgcolor="#2D0D0D",
                            border=ft.border.all(1, color),
                            border_radius=20,
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            ink=True,
                            on_click=(lambda e, key=nav_key: navigate(key)) if navigate else None,
                            content=ft.Row([
                                ft.Icon(icon, color=color, size=12),
                                ft.Text(label, color=color, size=11, weight=ft.FontWeight.W_500),
                            ], spacing=5, tight=True),
                        )
                        for icon, label, color, nav_key in items[:4]
                    ],
                    spacing=6,
                    wrap=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        ),
    )


def _hero_tag(icon: str, label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=_ov(color),
        border=ft.border.all(1, _bdr(color)),
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=12),
                ft.Text(label, color=color, size=11, weight=ft.FontWeight.W_500),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
    )


def _hero_kpi(label: str, value: Any, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=_ov(color),
        border=ft.border.all(1, _bdr(color)),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=22, vertical=16),
        content=ft.Column(
            controls=[
                ft.Text(str(value), size=34, color=color, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=11, color=_MUTED),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


# ── cartes KPI ────────────────────────────────────────────────────────────────

def _kpi_card(label: str, value: Any, color: str, icon: str, subtitle: str) -> ft.Control:
    return ft.Container(
        height=116,
        bgcolor=_CARD,
        border=ft.border.only(
            left=ft.BorderSide(4, color),
            top=ft.BorderSide(1, _BORDER),
            right=ft.BorderSide(1, _BORDER),
            bottom=ft.BorderSide(1, _BORDER),
        ),
        border_radius=ft.border_radius.all(12),
        padding=ft.padding.only(left=12, right=14, top=14, bottom=12),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=34, height=34,
                            bgcolor=_ov(color),
                            border_radius=9,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=color, size=18),
                        ),
                        ft.Text(label, color=_MUTED, size=10, weight=ft.FontWeight.W_500, expand=True, max_lines=2),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(str(value), size=30, weight=ft.FontWeight.BOLD, color=_WHITE),
                ft.Text(subtitle, size=9, color=_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ],
            spacing=5,
        ),
    )


# ── panneau generique ─────────────────────────────────────────────────────────

def _panel(title: str, subtitle: str, content: ft.Control, accent: str = PRIMARY) -> ft.Control:
    return ft.Container(
        bgcolor=_CARD,
        border=ft.border.all(1, _BORDER),
        border_radius=14,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_HEAD,
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=28, bgcolor=accent, border_radius=2),
                            ft.Column(
                                controls=[
                                    ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=_TEXT),
                                    ft.Text(subtitle, size=10, color=_MUTED),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=14),
                    content=content,
                ),
            ],
            spacing=0,
        ),
    )


def _section_panel(
    title: str, subtitle: str, controls: list[ft.Control],
    action_label: str = "", navigate: Any | None = None,
    navigate_key: str = "", accent: str = PRIMARY,
) -> ft.Control:
    action = (
        ft.TextButton(
            action_label,
            icon=ft.Icons.ARROW_FORWARD_OUTLINED,
            style=ft.ButtonStyle(color=accent),
            on_click=(lambda event: navigate(navigate_key)) if navigate and navigate_key else None,
        )
        if action_label else ft.Container()
    )
    return ft.Container(
        bgcolor=_CARD,
        border=ft.border.all(1, _BORDER),
        border_radius=14,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_HEAD,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=24, bgcolor=accent, border_radius=2),
                            ft.Column(
                                controls=[
                                    ft.Text(title, color=_TEXT, size=13, weight=ft.FontWeight.BOLD),
                                    ft.Text(subtitle, color=_MUTED, size=10),
                                ],
                                spacing=1, expand=True,
                            ),
                            action,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    content=ft.Column(
                        controls=controls or [ft.Text("Aucune donnee disponible.", color=_MUTED, size=11)],
                        spacing=6,
                    ),
                ),
            ],
            spacing=0,
        ),
    )


# ── panneaux specifiques ──────────────────────────────────────────────────────

def _compliance_panel(summary: dict[str, Any]) -> ft.Control:
    ppe        = summary["ppe"]
    training   = summary["training"]
    maintenance = summary["maintenance_actions"]
    indicators = [
        ("Presence",        summary["attendance_rate"],                                      SUCCESS),
        ("Disponibilite",   summary["workforce_rate"],                                       PRIMARY),
        ("EPI conformes",   max(100 - min(ppe["low_stock"] * 10, 100), 0),                  WARNING if ppe["low_stock"]           else SUCCESS),
        ("Formations val.", max(100 - min(training["expired"] * 10, 100), 0),               WARNING if training["expired"]        else SUCCESS),
        ("Maintenance",     max(100 - min(maintenance["maintenance_late"] * 10, 100), 0),   WARNING if maintenance["maintenance_late"] else SUCCESS),
    ]
    global_rate = round(sum(i[1] for i in indicators) / len(indicators))
    ring_color  = SUCCESS if global_rate >= 85 else WARNING
    content = ft.Row(
        controls=[
            ft.Container(
                width=110, height=110,
                border=ft.border.all(11, ring_color),
                border_radius=55,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    controls=[
                        ft.Text(f"{global_rate}%", size=22, color=_TEXT, weight=ft.FontWeight.BOLD),
                        ft.Text("Global", size=10, color=_MUTED),
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            ft.Column(
                controls=[_compliance_line(*item) for item in indicators],
                spacing=8, expand=True,
            ),
        ],
        spacing=18,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return _panel("Conformite globale", "Synthese des principaux indicateurs.", content, ring_color)


def _compliance_line(label: str, value: int, color: str) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Row(controls=[
                ft.Text(label, color=_MUTED, size=11, expand=True),
                ft.Text(f"{value}%", color=color, size=11, weight=ft.FontWeight.BOLD),
            ]),
            ft.ProgressBar(value=max(min(value, 100), 0) / 100, color=color, bgcolor=_TRACK, height=5, border_radius=3),
        ],
        spacing=3,
    )


def _performance_panel(summary: dict[str, Any]) -> ft.Control:
    return _panel(
        "Indicateurs de performance",
        "KPI compares aux cibles de pilotage.",
        ft.Column(controls=[_kpi_line(item) for item in summary["performance_indicators"]], spacing=8),
        PRIMARY,
    )


def _attendance_trend_panel(summary: dict[str, Any]) -> ft.Control:
    trend = summary["presence_trend"]
    chart = _line_chart_svg(trend, width=760, height=260, lines=[
        ("present", "Presents", "#3B82F6"),
        ("absent",  "Absents",  "#F87171"),
    ])
    return _panel(
        "Tendance presence — 14 jours",
        "Courbes journalieres basees sur les listes de presence validees.",
        ft.Column(controls=[
            _legend([("Presents", "#3B82F6"), ("Absents", "#F87171")]),
            ft.Image(src=chart, height=260, fit=ft.BoxFit.CONTAIN, expand=True),
        ], spacing=8),
        PRIMARY,
    )


def _workforce_panel(summary: dict[str, Any]) -> ft.Control:
    values = [item for item in summary["workforce_by_state"] if int(item["value"] or 0) > 0]
    if not values:
        values = [{"label": "Aucune donnee", "value": 1, "color": _BORDER}]
    chart = _donut_svg(values, width=310, height=220)
    return _panel(
        "Disponibilite workforce",
        "Repartition actuelle du personnel.",
        ft.Column(controls=[
            ft.Image(src=chart, height=220, fit=ft.BoxFit.CONTAIN),
            _legend([(item["label"], item["color"]) for item in values]),
        ], spacing=8),
        SUCCESS,
    )


def _shift_panel(summary: dict[str, Any]) -> ft.Control:
    rows = summary["presence_by_shift"]
    content = (
        ft.Column(controls=[_shift_line(row) for row in rows], spacing=8)
        if rows
        else ft.Text("Aucune liste de presence enregistree.", size=12, color=_MUTED)
    )
    return _panel("Presence par shift", "Presents / absents pour la journee.", content, WARNING)


def _operational_focus_panel(summary: dict[str, Any]) -> ft.Control:
    today       = summary["presence_today"]
    maintenance = summary["maintenance_actions"]
    items = [
        ("Au travail",           summary["workforce_at_work"],          SUCCESS, ft.Icons.ENGINEERING_OUTLINED),
        ("En break",             summary["workforce_on_break"],          WARNING, ft.Icons.BEACH_ACCESS_OUTLINED),
        ("Presents aujourd'hui", today["present"],                       SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
        ("Absents aujourd'hui",  today["absent"],                        DANGER,  ft.Icons.CANCEL_OUTLINED),
        ("Breaks a planifier",   summary["breaks_dus"],                  DANGER,  ft.Icons.EVENT_BUSY_OUTLINED),
        ("Maintenances ouvertes",maintenance["maintenance_open"],        WARNING if maintenance["maintenance_open"] else SUCCESS, ft.Icons.HANDYMAN_OUTLINED),
        ("Actions ouvertes",     maintenance["actions_open"],            WARNING if maintenance["actions_open"] else SUCCESS, ft.Icons.TASK_ALT_OUTLINED),
    ]
    return _panel(
        "Priorites operationnelles",
        "Points qui demandent une action rapide.",
        ft.Column(controls=[_operation_line(*item) for item in items], spacing=6),
        DANGER,
    )


def _recent_activity_panel(rows: list[dict[str, Any]]) -> ft.Control:
    controls = [
        _list_row(
            str(item.get("action") or "Activite"),
            f"{item.get('cible_type') or '-'}  •  {item.get('changed_by') or 'systeme'}",
            str(item.get("changed_at") or "")[-8:-3],
            PRIMARY,
            ft.Icons.HISTORY_OUTLINED,
        )
        for item in rows
    ]
    return _panel(
        "Activites recentes",
        "Dernieres operations enregistrees.",
        ft.Column(controls=controls or [ft.Text("Aucune activite.", color=_MUTED, size=12)], spacing=6),
        PRIMARY,
    )


# ── sections listes ───────────────────────────────────────────────────────────

def _alert_list_panel(alerts: list[dict[str, Any]], navigate: Any | None) -> ft.Control:
    rows = [
        _list_row(
            str(item.get("source") or "Alerte"),
            str(item.get("message") or "-"),
            str(item.get("niveau") or "-").upper(),
            DANGER if item.get("niveau") in {"critique", "haut"} else WARNING,
            ft.Icons.WARNING_AMBER_OUTLINED,
        )
        for item in alerts
    ]
    return _section_panel("Alertes critiques", "Priorites necessitant une action.", rows, "Voir tout", navigate, "Alerts", DANGER)


def _maintenance_list_panel(rows: list[dict[str, Any]], navigate: Any | None) -> ft.Control:
    controls = [
        _list_row(
            str(item.get("equipment_code") or item.get("equipment_name") or "Equipement"),
            f"{item.get('equipment_name') or '-'}  •  {item.get('site') or '-'}",
            str(item.get("status") or "-").replace("_", " ").upper(),
            DANGER if item.get("status") == "en_retard" else WARNING,
            ft.Icons.HANDYMAN_OUTLINED,
        )
        for item in rows
    ]
    return _section_panel("Maintenance", "Equipements prioritaires.", controls, "Voir tout", navigate, "MaintenanceActions", WARNING)


def _timesheet_panel(timesheet: dict[str, Any], navigate: Any | None) -> ft.Control:
    summary   = timesheet.get("summary") or {}
    period    = timesheet.get("period") or {}
    employees = int(summary.get("employees") or 0)
    unfilled  = int(summary.get("unfilled_days") or 0)
    controls  = [
        ft.Container(
            bgcolor=_ov(PRIMARY),
            border=ft.border.all(1, _bdr(PRIMARY)),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=7),
            content=ft.Text(
                f"Periode : {period.get('start') or '-'} au {period.get('end') or '-'}",
                color=PRIMARY, size=11, weight=ft.FontWeight.BOLD,
            ),
        ),
        _summary_line("Heures normales",    f"{summary.get('hours') or 0} h",               SUCCESS),
        _summary_line("Employes suivis",    employees,                                        PRIMARY),
        _summary_line("Jours non remplis",  unfilled,                                         DANGER if unfilled else SUCCESS),
        _summary_line("Validation estimee", f"{max(employees - unfilled, 0)} / {employees}", WARNING if unfilled else SUCCESS),
    ]
    return _section_panel("Timesheet — periode en cours", "Etat de preparation mensuelle.", controls, "Voir les Timesheets", navigate, "TimeSheet", SUCCESS)


# ── actions rapides ───────────────────────────────────────────────────────────

def _quick_actions_panel(navigate: Any | None) -> ft.Control:
    actions = [
        ("Employes",     ft.Icons.PERSON_ADD_ALT_OUTLINED,    "EmployeeManagement", SUCCESS),
        ("Presence",     ft.Icons.HOW_TO_REG_OUTLINED,        "EmployeeManagement", PRIMARY),
        ("Formation",    ft.Icons.SCHOOL_OUTLINED,            "TrainingManagement", _PURPLE),
        ("Toolbox",      ft.Icons.FORUM_OUTLINED,             "ToolboxTalk",        SUCCESS),
        ("EPI",          ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "Ppe",                WARNING),
        ("Maintenance",  ft.Icons.HANDYMAN_OUTLINED,          "MaintenanceActions", WARNING),
        ("Rapports",     ft.Icons.ASSESSMENT_OUTLINED,        "Alerts",             PRIMARY),
        ("Assistant IA", ft.Icons.AUTO_AWESOME_OUTLINED,      "AiAssistant",        _PURPLE),
    ]
    buttons = [
        ft.Container(
            width=108, height=80,
            bgcolor=_CARD2,
            border=ft.border.all(1, _bdr(color)),
            border_radius=12,
            ink=True,
            on_click=(lambda event, key=key: navigate(key)) if navigate else None,
            padding=10,
            content=ft.Column(
                controls=[
                    ft.Container(
                        width=34, height=34,
                        bgcolor=_ov(color),
                        border_radius=9,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, color=color, size=18),
                    ),
                    ft.Text(label, color=_TEXT, size=10, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
        for label, icon, key, color in actions
    ]
    return _panel(
        "Actions rapides",
        "Acces direct aux modules operationnels.",
        ft.Row(buttons, wrap=True, spacing=8),
        PRIMARY,
    )


def _assistant_panel(navigate: Any | None) -> ft.Control:
    prompts = [
        "Qui doit partir en break cette semaine ?",
        "Quels EPI expirent ce mois-ci ?",
        "Montre les formations expirees.",
        "Genere le rapport HSE du mois.",
    ]
    controls = [
        ft.Container(
            bgcolor=_ov(_PURPLE),
            border=ft.border.all(1, _bdr(_PURPLE)),
            border_radius=8,
            ink=True,
            on_click=(lambda event: navigate("AiAssistant")) if navigate else None,
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color=_PURPLE, size=14),
                    ft.Text(prompt, color=_TEXT, size=11, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=_PURPLE, size=16),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        for prompt in prompts
    ]
    return _section_panel(
        "Assistant IA QHSE",
        "Analyse et aide a la decision.",
        controls,
        "Ouvrir l'assistant",
        navigate,
        "AiAssistant",
        _PURPLE,
    )


# ── composants de ligne ───────────────────────────────────────────────────────

def _list_row(title: str, subtitle: str, value: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=_CARD2,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=30, height=30,
                    bgcolor=_ov(color),
                    border_radius=6,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color=color, size=15),
                ),
                ft.Column(
                    controls=[
                        ft.Text(title, color=_TEXT, size=11, weight=ft.FontWeight.BOLD, max_lines=1),
                        ft.Text(subtitle, color=_MUTED, size=9, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=1, expand=True,
                ),
                ft.Container(
                    bgcolor=_ov(color),
                    border=ft.border.all(1, _bdr(color)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    content=ft.Text(value, color=color, size=9, weight=ft.FontWeight.BOLD),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _summary_line(label: str, value: Any, color: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Text(label, color=_MUTED, size=11, expand=True),
            ft.Text(str(value), color=color, size=12, weight=ft.FontWeight.BOLD),
        ],
    )


def _kpi_line(item: dict[str, Any]) -> ft.Control:
    status   = str(item.get("status") or "")
    color    = {"bon": SUCCESS, "attention": WARNING, "critique": DANGER}.get(status, _MUTED)
    value    = f"{item['value']}{item.get('suffix') or ''}"
    target   = f"Cible : {item['target']}{item.get('suffix') or ''}"
    progress = _kpi_progress(item)
    return ft.Container(
        bgcolor=_CARD2,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Row(controls=[
                    ft.Text(str(item["label"]), color=_TEXT, size=12, expand=True),
                    ft.Text(value, color=color, size=16, weight=ft.FontWeight.BOLD),
                ]),
                ft.ProgressBar(value=progress, color=color, bgcolor=_TRACK, height=6, border_radius=3),
                ft.Row(
                    controls=[
                        ft.Text(target, color=_MUTED, size=10, expand=True),
                        _status_badge(status, color),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=5,
        ),
    )


def _operation_line(label: str, value: int, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=_ov(color),
        border=ft.border.all(1, _bdr(color)),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=16),
                ft.Text(label, color=_TEXT, size=12, expand=True),
                ft.Text(str(value), color=color, weight=ft.FontWeight.BOLD, size=18),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _shift_line(row: dict[str, Any]) -> ft.Control:
    total   = int(row["total"] or 0)
    present = int(row["present"] or 0)
    absent  = int(row["absent"] or 0)
    rate    = round((present / total) * 100) if total else 0
    color   = SUCCESS if rate >= 85 else WARNING
    return ft.Container(
        bgcolor=_CARD2,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Row(controls=[
                    ft.Text(str(row["label"]), color=_TEXT, weight=ft.FontWeight.BOLD, expand=True, size=12),
                    ft.Text(f"{rate}%", color=color, weight=ft.FontWeight.BOLD, size=12),
                ]),
                ft.ProgressBar(value=rate / 100, color=color, bgcolor=_TRACK, height=6, border_radius=3),
                ft.Text(f"{present} presents  •  {absent} absents  •  {total} total", color=_MUTED, size=10),
            ],
            spacing=5,
        ),
    )


def _status_badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=_ov(color),
        border=ft.border.all(1, _bdr(color)),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(label.upper(), size=10, color=color, weight=ft.FontWeight.BOLD),
    )


def _legend(items: list[tuple[str, str]]) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                    ft.Text(label, size=11, color=_MUTED),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for label, color in items
        ],
        wrap=True, spacing=12,
    )


# ── SVG charts (dark theme) ───────────────────────────────────────────────────

def _kpi_progress(item: dict[str, Any]) -> float:
    value  = int(item.get("value") or 0)
    target = int(item.get("target") or 0)
    if str(item.get("suffix") or "") == "%":
        return max(min(value, 100), 0) / 100
    if target == 0:
        return 1.0 if value == 0 else max(0.05, 1 - min(value, 10) / 10)
    return max(min(value / target, 1), 0)


def _line_chart_svg(
    data: list[dict[str, Any]], width: int, height: int, lines: list[tuple[str, str, str]]
) -> str:
    pl, pt, pr, pb = 44, 18, 20, 42
    cw = width - pl - pr
    ch = height - pt - pb
    max_val = max([int(item.get(k) or 0) for item in data for k, _, _ in lines] + [1])
    x_step  = cw / max(len(data) - 1, 1)

    grid = []
    for tick in range(5):
        val = round((max_val / 4) * tick)
        y   = pt + ch - ((val / max_val) * ch if max_val else 0)
        grid.append(
            f'<line x1="{pl}" y1="{y:.1f}" x2="{width-pr}" y2="{y:.1f}" stroke="#1E3A5F" stroke-width="1"/>'
            f'<text x="8" y="{y+4:.1f}" font-size="10" fill="#9DB0C5">{val}</text>'
        )

    series = []
    for key, label, color in lines:
        points, dots = [], []
        for i, item in enumerate(data):
            x   = pl + i * x_step
            val = int(item.get(key) or 0)
            y   = pt + ch - ((val / max_val) * ch if max_val else 0)
            points.append(f"{x:.1f},{y:.1f}")
            dots.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" stroke="#0D2040" stroke-width="1.5">'
                f'<title>{_xml(label)} {val}</title></circle>'
            )
        series.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" '
            f'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        series.extend(dots)

    labels = []
    for i, item in enumerate(data):
        if i % 2 == 0 or i == len(data) - 1:
            x = pl + i * x_step
            labels.append(
                f'<text x="{x:.1f}" y="{height-16}" font-size="10" fill="#9DB0C5" text-anchor="middle">'
                f'{_xml(str(item["date"])[5:])}</text>'
            )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" rx="10" fill="#0D2040"/>'
        f'{"".join(grid)}'
        f'<line x1="{pl}" y1="{pt}" x2="{pl}" y2="{height-pb}" stroke="#1E3A5F"/>'
        f'<line x1="{pl}" y1="{height-pb}" x2="{width-pr}" y2="{height-pb}" stroke="#1E3A5F"/>'
        f'{"".join(series)}{"".join(labels)}'
        f'</svg>'
    )
    return _svg_src(svg)


def _donut_svg(values: list[dict[str, Any]], width: int, height: int) -> str:
    total  = sum(int(item.get("value") or 0) for item in values) or 1
    cx, cy = width / 2, height / 2
    radius = min(width, height) / 2 - 24
    circ   = 2 * 3.14159 * radius
    offset = 0.0
    rings  = []
    for item in values:
        val    = int(item.get("value") or 0)
        length = (val / total) * circ
        rings.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{item["color"]}" stroke-width="24" '
            f'stroke-dasharray="{length:.2f} {circ - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += length
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" rx="10" fill="#0D2040"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#1E3A5F" stroke-width="24"/>'
        f'{"".join(rings)}'
        f'<text x="{cx}" y="{cy-4}" text-anchor="middle" font-size="26" font-weight="700" fill="#E2E8F0">{total}</text>'
        f'<text x="{cx}" y="{cy+18}" text-anchor="middle" font-size="11" fill="#9DB0C5">Employes</text>'
        f'</svg>'
    )
    return _svg_src(svg)


def _svg_src(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _xml(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
