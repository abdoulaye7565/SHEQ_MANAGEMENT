from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any, Callable

import flet as ft

from app.services import get_training_matrix, list_trainings
from app.ui.pages.training import training_page
from app.ui.pages.training_bulk import training_bulk_page
from app.ui.pages.training_matrix import training_matrix_page


from app.ui.components.dark_styles import BG, BORDER, CARD, FIELD
TEXT = "#FFFFFF"
MUTED = "#9DB0C5"
PRIMARY = "#2563EB"
SUCCESS = "#16A34A"
WARNING = "#F59E0B"
DANGER = "#EF4444"
PURPLE = "#8B5CF6"
TEAL = "#14B8A6"


def training_management_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"view": "overview", "cache": {}}
    content = ft.Container(expand=True, bgcolor="#071321")
    nav_buttons: dict[str, ft.TextButton] = {}

    def update_root() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def set_view(view: str) -> None:
        state["view"] = view
        render()

    def build_view(view: str) -> ft.Control:
        if view == "overview":
            return _overview(set_view)
        if view == "employees":
            return _employees_view(set_view)
        if view == "matrix":
            return training_matrix_page(page)
        if view == "bulk":
            return training_bulk_page(page)
        if view == "plan":
            return _training_plan()
        if view == "reports":
            return _training_reports(set_view)
        if view == "settings":
            return _training_settings()
        return training_page(page)

    def render() -> None:
        view = str(state["view"])
        for key, button in nav_buttons.items():
            selected = key == view
            button.style = ft.ButtonStyle(
                color="#60A5FA" if selected else MUTED,
                bgcolor="#0D2540" if selected else BG,
                shape=ft.RoundedRectangleBorder(radius=6),
                side=ft.BorderSide(1, "#2563EB" if selected else BORDER),
            )
        cache = state["cache"]
        if view not in cache:
            cache[view] = build_view(view)
        content.content = cache[view]
        update_root()

    nav_items = [
        ("overview",   "Vue d'ensemble",      ft.Icons.DASHBOARD_OUTLINED),
        ("employees",  "Fiches Employes",     ft.Icons.BADGE_OUTLINED),
        ("training",   "Formations",          ft.Icons.SCHOOL_OUTLINED),
        ("matrix",     "Matrice competences", ft.Icons.GRID_VIEW_OUTLINED),
        ("bulk",       "Mise a jour groupee", ft.Icons.DONE_ALL_OUTLINED),
        ("plan",       "Plan de formation",   ft.Icons.EVENT_NOTE_OUTLINED),
        ("reports",    "Rapports",            ft.Icons.ASSESSMENT_OUTLINED),
        ("settings",   "Parametres",          ft.Icons.SETTINGS_OUTLINED),
    ]
    for key, label, icon in nav_items:
        nav_buttons[key] = ft.TextButton(
            content=label,
            icon=icon,
            on_click=lambda event, current=key: set_view(current),
        )

    root = ft.Column(
        controls=[
            _module_heading(set_view),
            ft.Row(
                controls=list(nav_buttons.values()),
                spacing=6,
                scroll=ft.ScrollMode.AUTO,
            ),
            content,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _module_heading(set_view: Callable[[str], None]) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Text("Gestion formation", size=24, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Text(
                        "Suivi des formations, conformite des employes et matrice des competences.",
                        size=12,
                        color=MUTED,
                    ),
                ],
                spacing=2,
                expand=True,
            ),
            ft.ElevatedButton(
                "Nouvelle formation",
                icon=ft.Icons.ADD,
                on_click=lambda event: set_view("training"),
                style=ft.ButtonStyle(
                    bgcolor=PRIMARY,
                    color=TEXT,
                    shape=ft.RoundedRectangleBorder(radius=6),
                ),
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _overview(set_view: Callable[[str], None]) -> ft.Control:
    records = list_trainings()
    matrix = get_training_matrix()
    summary = matrix.get("summary") or {}
    employees_trained = len({int(row["employe_id"]) for row in records})
    valid = sum(1 for row in records if row.get("etat") == "valide")
    soon = sum(1 for row in records if row.get("etat") == "bientot_expiree")
    expired = sum(1 for row in records if row.get("etat") == "expiree")
    compliance = int(summary.get("compliance") or 0)

    kpis = [
        ("Total formations", summary.get("training_types") or 0, "Types actifs", PRIMARY, ft.Icons.SCHOOL_OUTLINED),
        ("Employes formes", employees_trained, f"Sur {summary.get('employees') or 0} employes", SUCCESS, ft.Icons.GROUPS_OUTLINED),
        ("Formations valides", valid, "Competences a jour", PURPLE, ft.Icons.VERIFIED_OUTLINED),
        ("Bientot expirees", soon, "Renouvellement requis", WARNING, ft.Icons.SCHEDULE_OUTLINED),
        ("Expirees", expired, "Action immediate", DANGER, ft.Icons.EVENT_BUSY_OUTLINED),
        ("Conformite globale", f"{compliance}%", "Matrice de competences", TEAL, ft.Icons.DONUT_LARGE_OUTLINED),
    ]
    recent = sorted(records, key=lambda row: str(row.get("date_formation") or ""), reverse=True)[:5]
    renewals = sorted(
        [row for row in records if row.get("etat") in {"bientot_expiree", "expiree"}],
        key=lambda row: str(row.get("date_expiration") or ""),
    )[:5]
    categories = Counter(str(row.get("training_department") or "Sans departement") for row in records)
    alerts = [
        (f"{soon} formation(s) bientot expiree(s)", "A renouveler dans les 60 prochains jours", WARNING, ft.Icons.SCHEDULE_OUTLINED),
        (f"{expired} formation(s) expiree(s)", "Necessitent un renouvellement", DANGER, ft.Icons.EVENT_BUSY_OUTLINED),
        (f"{summary.get('missing') or 0} competence(s) manquante(s)", "Employes non conformes dans la matrice", WARNING, ft.Icons.PERSON_OFF_OUTLINED),
        (f"{summary.get('risk') or 0} ecart(s) de conformite", "A traiter dans le plan de formation", PRIMARY, ft.Icons.REPORT_PROBLEM_OUTLINED),
    ]

    return ft.Column(
        controls=[
            ft.ResponsiveRow(
                controls=[
                    ft.Container(_kpi_card(*item), col={"xs": 12, "sm": 6, "md": 4, "lg": 2})
                    for item in kpis
                ],
                spacing=10,
                run_spacing=10,
            ),
            _filter_bar(),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        _panel(
                            "Etat de conformite des formations",
                            [_compliance_visual(summary)],
                        ),
                        col={"xs": 12, "lg": 4},
                    ),
                    ft.Container(
                        _panel(
                            "Formations par categorie",
                            [_category_bars(categories)],
                        ),
                        col={"xs": 12, "lg": 5},
                    ),
                    ft.Container(
                        _panel("Alertes & notifications", [_alerts_list(alerts)]),
                        col={"xs": 12, "lg": 3},
                    ),
                ],
                spacing=10,
                run_spacing=10,
            ),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        _panel("Formations recentes", [_recent_training_table(recent)]),
                        col={"xs": 12, "lg": 9},
                    ),
                    ft.Container(
                        ft.Column(
                            controls=[
                                _panel("Actions rapides", [_quick_actions(set_view)]),
                                _panel("Prochains renouvellements", [_renewal_list(renewals)]),
                            ],
                            spacing=10,
                        ),
                        col={"xs": 12, "lg": 3},
                    ),
                ],
                spacing=10,
                run_spacing=10,
            ),
        ],
        spacing=12,
    )


def _filter_bar() -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=10,
        content=ft.Row(
            controls=[
                _dark_dropdown("Mois courant", _current_month_label(), 180),
                _dark_dropdown("Site", "Tous les sites", 180),
                _dark_dropdown("Departement", "Tous", 180),
                _dark_dropdown("Fonction", "Toutes", 180),
                _dark_dropdown("Statut", "Tous", 170),
                ft.TextField(
                    hint_text="Rechercher formation, employe...",
                    prefix_icon=ft.Icons.SEARCH,
                    width=260,
                    bgcolor=FIELD,
                    color=TEXT,
                    border_color=BORDER,
                ),
            ],
            spacing=10,
            wrap=True,
        ),
    )


def _dark_dropdown(label: str, value: str, width: int) -> ft.Control:
    return ft.Dropdown(
        label=label,
        value=value,
        width=width,
        options=[ft.dropdown.Option(value, value)],
        bgcolor=FIELD,
        color=TEXT,
        border_color=BORDER,
        label_style=ft.TextStyle(color=MUTED),
    )


def _kpi_card(label: str, value: Any, detail: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        height=104,
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    bgcolor=f"{color}30",
                    border_radius=7,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=color, size=24),
                ),
                ft.Column(
                    controls=[
                        ft.Text(label, size=11, color=MUTED),
                        ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(detail, size=10, color=MUTED, max_lines=1),
                    ],
                    spacing=1,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Divider(height=1, color=BORDER),
                *controls,
            ],
            spacing=10,
        ),
    )


def _compliance_visual(summary: dict[str, Any]) -> ft.Control:
    total = max(int(summary.get("total_cells") or 0), 1)
    items = [
        ("Conformes", int(summary.get("valid") or 0), SUCCESS),
        ("Bientot expirees", int(summary.get("soon") or 0), WARNING),
        ("Expirees", int(summary.get("expired") or 0), DANGER),
        ("Non conformes", int(summary.get("missing") or 0), PRIMARY),
    ]
    return ft.Row(
        controls=[
            ft.Container(
                width=150,
                height=150,
                alignment=ft.Alignment.CENTER,
                content=ft.Stack(
                    controls=[
                        ft.ProgressRing(
                            value=min(max(int(summary.get("compliance") or 0) / 100, 0), 1),
                            width=150,
                            height=150,
                            stroke_width=18,
                            color=SUCCESS,
                            bgcolor=FIELD,
                        ),
                        ft.Container(
                            alignment=ft.Alignment.CENTER,
                            content=ft.Column(
                                controls=[
                                    ft.Text(str(summary.get("employees") or 0), size=26, weight=ft.FontWeight.BOLD, color=TEXT),
                                    ft.Text("Employes", size=11, color=MUTED),
                                ],
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ),
                    ]
                ),
            ),
            ft.Column(
                controls=[
                    _legend_line(label, value, round(value * 100 / total), color)
                    for label, value, color in items
                ],
                spacing=9,
                expand=True,
            ),
        ],
        spacing=18,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _legend_line(label: str, value: int, percent: int, color: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Container(width=9, height=9, bgcolor=color, border_radius=2),
            ft.Text(label, size=11, color=MUTED, expand=True),
            ft.Text(f"{value} ({percent}%)", size=11, color=TEXT, weight=ft.FontWeight.BOLD),
        ],
        spacing=6,
    )


def _category_bars(categories: Counter[str]) -> ft.Control:
    rows = categories.most_common(5)
    maximum = max((value for _, value in rows), default=1)
    colors = [PRIMARY, SUCCESS, WARNING, PURPLE, TEAL]
    return ft.Column(
        controls=[
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(label, width=110, size=11, color=MUTED),
                            ft.Text(str(value), size=11, color=TEXT, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        height=14,
                        bgcolor=FIELD,
                        border_radius=4,
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    width=max(24, int(360 * value / maximum)),
                                    height=14,
                                    bgcolor=colors[index % len(colors)],
                                    border_radius=4,
                                )
                            ]
                        ),
                    ),
                ],
                spacing=4,
            )
            for index, (label, value) in enumerate(rows)
        ]
        or [ft.Text("Aucune categorie de formation.", color=MUTED, size=12)],
        spacing=12,
    )


def _alerts_list(alerts: list[tuple[str, str, str, str]]) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Container(
                bgcolor=FIELD,
                border=ft.border.all(1, BORDER),
                border_radius=6,
                padding=9,
                content=ft.Row(
                    controls=[
                        ft.Icon(icon, color=color, size=18),
                        ft.Column(
                            controls=[
                                ft.Text(title, color=TEXT, size=11, weight=ft.FontWeight.BOLD),
                                ft.Text(detail, color=MUTED, size=9, max_lines=2),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
            )
            for title, detail, color, icon in alerts
        ],
        spacing=6,
    )


def _recent_training_table(records: list[dict[str, Any]]) -> ft.Control:
    header = ft.Row(
        controls=[
            _cell("Formation", 3, True),
            _cell("Employe", 3, True),
            _cell("Departement", 2, True),
            _cell("Expiration", 2, True),
            _cell("Statut", 2, True),
        ],
        spacing=4,
    )
    rows: list[ft.Control] = [header]
    for record in records:
        state = str(record.get("etat") or "")
        color = {"valide": SUCCESS, "bientot_expiree": WARNING, "expiree": DANGER}.get(state, MUTED)
        rows.append(
            ft.Container(
                border=ft.border.only(top=ft.BorderSide(1, BORDER)),
                padding=ft.padding.symmetric(vertical=8),
                content=ft.Row(
                    controls=[
                        _cell(str(record.get("formation") or "-"), 3),
                        _cell(f"{record.get('nom') or '-'} {record.get('prenom') or ''}", 3),
                        _cell(str(record.get("training_department") or "-"), 2),
                        _cell(str(record.get("date_expiration") or "-"), 2),
                        ft.Container(
                            content=ft.Text(_state_label(state), color=color, size=10),
                            border=ft.border.all(1, color),
                            border_radius=5,
                            padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            expand=2,
                        ),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )
    return ft.Column(controls=rows, spacing=0)


def _cell(value: str, flex: int, header: bool = False) -> ft.Control:
    return ft.Text(
        value,
        size=10 if header else 11,
        color=MUTED if header else TEXT,
        weight=ft.FontWeight.BOLD if header else None,
        max_lines=2,
        expand=flex,
    )


def _quick_actions(set_view: Callable[[str], None]) -> ft.Control:
    actions = [
        ("Ajouter formation", ft.Icons.ADD_TASK_OUTLINED, PRIMARY, "training"),
        ("Planifier session", ft.Icons.EVENT_AVAILABLE_OUTLINED, SUCCESS, "training"),
        ("Assigner formation", ft.Icons.GROUP_ADD_OUTLINED, PURPLE, "training"),
        ("Matrice competences", ft.Icons.GRID_VIEW_OUTLINED, WARNING, "matrix"),
        ("Exporter rapport", ft.Icons.DOWNLOAD_OUTLINED, TEAL, "matrix"),
        ("Plan de formation", ft.Icons.CALENDAR_MONTH_OUTLINED, PRIMARY, "training"),
    ]
    return ft.ResponsiveRow(
        controls=[
            ft.Container(
                col={"xs": 6},
                bgcolor=FIELD,
                border=ft.border.all(1, BORDER),
                border_radius=6,
                padding=8,
                on_click=lambda event, target=view: set_view(target),
                content=ft.Column(
                    controls=[
                        ft.Icon(icon, color=color, size=18),
                        ft.Text(label, size=9, color=TEXT, text_align=ft.TextAlign.CENTER),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            for label, icon, color, view in actions
        ],
        spacing=6,
        run_spacing=6,
    )


def _renewal_list(records: list[dict[str, Any]]) -> ft.Control:
    today = date.today()
    controls: list[ft.Control] = []
    for record in records:
        expiration = _parse_date(record.get("date_expiration"))
        days = (expiration - today).days if expiration else 0
        color = DANGER if days < 0 else WARNING
        controls.append(
            ft.Container(
                border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                padding=ft.padding.symmetric(vertical=6),
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(str(record.get("formation") or "-"), size=10, color=TEXT, weight=ft.FontWeight.BOLD),
                                ft.Text(str(record.get("date_expiration") or "-"), size=9, color=MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Text("Expiree" if days < 0 else f"{days} jours", size=9, color=color),
                    ]
                ),
            )
        )
    return ft.Column(
        controls=controls or [ft.Text("Aucun renouvellement prioritaire.", color=MUTED, size=11)],
        spacing=0,
    )


def _parse_date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _state_label(state: str) -> str:
    return {
        "valide": "Active",
        "bientot_expiree": "A renouveler",
        "expiree": "Expiree",
    }.get(state, state or "-")


def _current_month_label() -> str:
    months = [
        "Janvier",
        "Fevrier",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juillet",
        "Aout",
        "Septembre",
        "Octobre",
        "Novembre",
        "Decembre",
    ]
    today = date.today()
    return f"{months[today.month - 1]} {today.year}"


def _training_plan() -> ft.Control:
    matrix = get_training_matrix()
    stats = sorted(matrix.get("training_stats") or [], key=lambda item: int(item.get("risk") or 0), reverse=True)
    return ft.Column(
        controls=[
            _section_intro("Plan de formation", "Priorites calculees automatiquement depuis la matrice de conformite.", ft.Icons.EVENT_NOTE_OUTLINED),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        _kpi_card("Priorites", sum(1 for item in stats if int(item.get("risk") or 0)), "Formations a planifier", WARNING, ft.Icons.PRIORITY_HIGH_OUTLINED),
                        col={"xs": 12, "sm": 4},
                    ),
                    ft.Container(
                        _kpi_card("Employes a risque", matrix["summary"].get("risk") or 0, "Ecarts detectes", DANGER, ft.Icons.PERSON_OFF_OUTLINED),
                        col={"xs": 12, "sm": 4},
                    ),
                    ft.Container(
                        _kpi_card("Conformite", f"{matrix['summary'].get('compliance') or 0}%", "Objectif: 100%", SUCCESS, ft.Icons.QUERY_STATS_OUTLINED),
                        col={"xs": 12, "sm": 4},
                    ),
                ],
                spacing=8,
                run_spacing=8,
            ),
            _panel(
                "Plan recommande",
                [
                    ft.Container(
                        bgcolor=FIELD,
                        border=ft.border.all(1, BORDER),
                        border_radius=6,
                        padding=9,
                        content=ft.Row(
                            controls=[
                                ft.Text(str(item.get("formation") or "-"), color=TEXT, size=11, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(str(item.get("department") or "-"), color=MUTED, size=10, width=150),
                                ft.Text(f"{item.get('risk') or 0} a traiter", color=DANGER if item.get("risk") else SUCCESS, size=10, width=100),
                                ft.ProgressBar(value=min(int(item.get("compliance") or 0) / 100, 1), color=SUCCESS, bgcolor=FIELD, width=160),
                                ft.Text(f"{item.get('compliance') or 0}%", color=TEXT, size=10),
                            ],
                            spacing=8,
                        ),
                    )
                    for item in stats
                ]
                or [ft.Text("Aucune formation active.", color=MUTED)],
            ),
        ],
        spacing=10,
    )


def _training_reports(set_view: Callable[[str], None]) -> ft.Control:
    matrix = get_training_matrix()
    return ft.Column(
        controls=[
            _section_intro("Rapports formation", "Rapports professionnels disponibles pour la conformite et le pilotage.", ft.Icons.ASSESSMENT_OUTLINED),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        _report_card(title, description, icon, color, lambda event, target=target: set_view(target)),
                        col={"xs": 12, "sm": 6, "lg": 4},
                    )
                    for title, description, icon, color, target in [
                        ("Liste des formations", "Historique, expiration et statut de chaque formation.", ft.Icons.LIST_ALT_OUTLINED, PRIMARY, "training"),
                        ("Matrice competences", "Conformite employes x formations avec legende.", ft.Icons.GRID_VIEW_OUTLINED, SUCCESS, "matrix"),
                        ("Formations a venir", "Priorites et renouvellements recommandes.", ft.Icons.EVENT_UPCOMING_OUTLINED, WARNING, "plan"),
                        ("Historique groupe", "Campagnes multiples et operations auditees.", ft.Icons.HISTORY_OUTLINED, PURPLE, "bulk"),
                        ("Synthese conformite", f"Conformite globale actuelle: {matrix['summary'].get('compliance') or 0}%.", ft.Icons.QUERY_STATS_OUTLINED, TEAL, "overview"),
                        ("Formations expirees", f"{matrix['summary'].get('expired') or 0} competence(s) expiree(s).", ft.Icons.EVENT_BUSY_OUTLINED, DANGER, "matrix"),
                    ]
                ],
                spacing=10,
                run_spacing=10,
            ),
        ],
        spacing=10,
    )


def _training_settings() -> ft.Control:
    options = get_training_matrix()
    return ft.Column(
        controls=[
            _section_intro("Parametres formation", "Configuration des types, validites, departements et obligations par fonction.", ft.Icons.SETTINGS_OUTLINED),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        _kpi_card("Types de formation", options["summary"].get("training_types") or 0, "Types actifs", PRIMARY, ft.Icons.SCHOOL_OUTLINED),
                        col={"xs": 12, "sm": 4},
                    ),
                    ft.Container(
                        _kpi_card("Employes actifs", options["summary"].get("employees") or 0, "Dans la matrice", SUCCESS, ft.Icons.GROUPS_OUTLINED),
                        col={"xs": 12, "sm": 4},
                    ),
                    ft.Container(
                        _kpi_card("Regles metier", "Auto", "Expiration et N/A automatiques", PURPLE, ft.Icons.AUTO_AWESOME_OUTLINED),
                        col={"xs": 12, "sm": 4},
                    ),
                ],
                spacing=8,
                run_spacing=8,
            ),
            _panel(
                "Automatisations actives",
                [
                    _setting_line("Expiration automatique", "Calculee depuis la validite du type de formation.", True),
                    _setting_line("Conformite par fonction", "Les formations non requises sont marquees N/A.", True),
                    _setting_line("Doublons interdits", "Une formation existante est mise a jour ou ignoree.", True),
                    _setting_line("Audit des campagnes", "Chaque mise a jour groupee est tracee.", True),
                ],
            ),
        ],
        spacing=10,
    )


def _section_intro(title: str, subtitle: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Container(width=42, height=42, bgcolor="#1D4ED8", border_radius=7, alignment=ft.Alignment.CENTER, content=ft.Icon(icon, color=TEXT)),
                ft.Column([ft.Text(title, color=TEXT, size=16, weight=ft.FontWeight.BOLD), ft.Text(subtitle, color=MUTED, size=10)], spacing=1),
            ],
            spacing=9,
        ),
    )


def _report_card(title: str, description: str, icon: str, color: str, on_click: Any) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=12,
        on_click=on_click,
        content=ft.Column(
            controls=[
                ft.Icon(icon, color=color, size=25),
                ft.Text(title, color=TEXT, size=12, weight=ft.FontWeight.BOLD),
                ft.Text(description, color=MUTED, size=10, max_lines=2),
                ft.Text("Ouvrir", color="#60A5FA", size=10),
            ],
            spacing=5,
        ),
    )


def _setting_line(title: str, description: str, active: bool) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, BORDER),
        border_radius=6,
        padding=9,
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE if active else ft.Icons.CANCEL_OUTLINED, color=SUCCESS if active else DANGER),
                ft.Column([ft.Text(title, color=TEXT, size=11, weight=ft.FontWeight.BOLD), ft.Text(description, color=MUTED, size=9)], spacing=1, expand=True),
                ft.Text("Actif" if active else "Inactif", color=SUCCESS if active else DANGER, size=10),
            ],
            spacing=8,
        ),
    )


# ── Fiches Employes ───────────────────────────────────────────────────────────

def _employees_view(set_view: Any) -> ft.Control:
    from typing import Callable
    matrix = get_training_matrix()
    all_rows: list[dict[str, Any]] = matrix.get("rows") or []

    main_area = ft.Column(spacing=12)

    def _conformity_pct(cells: list[dict[str, Any]]) -> int:
        valid = sum(1 for c in cells if c.get("status") == "done")
        total = sum(1 for c in cells if c.get("status") != "not_applicable")
        return round(valid * 100 / total) if total else 0

    def _pct_color(pct: int) -> str:
        if pct >= 85: return SUCCESS
        if pct >= 60: return WARNING
        return DANGER

    def _cell_color(status: str) -> str:
        return {"done": SUCCESS, "soon": WARNING, "expired": DANGER, "missing": DANGER, "not_applicable": MUTED}.get(status, MUTED)

    def _cell_label(status: str) -> str:
        return {"done": "OK", "soon": "Bientot", "expired": "Expire", "missing": "Manquant", "not_applicable": "N/A"}.get(status, "-")

    def _name(emp: dict[str, Any]) -> str:
        return f"{emp.get('nom') or ''} {emp.get('prenom') or ''}".strip() or "Employe"

    def show_fiche(row: dict[str, Any]) -> None:
        employee = row.get("employee") or {}
        cells    = row.get("cells") or []
        conformity = _conformity_pct(cells)
        color      = _pct_color(conformity)
        initials   = (_name(employee)[0] + (_name(employee).split(" ")[1][0] if len(_name(employee).split(" ")) > 1 else "")).upper()

        formation_rows: list[ft.Control] = []
        for cell in cells:
            st = str(cell.get("status") or "missing")
            cc = _cell_color(st)
            formation_rows.append(ft.Container(
                border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                padding=ft.padding.symmetric(vertical=9),
                content=ft.Row([
                    ft.Container(width=8, height=8, bgcolor=cc, border_radius=4),
                    ft.Column([
                        ft.Text(str(cell.get("training_name") or "-"), size=12, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(str(cell.get("training_department") or "-"), size=10, color=MUTED),
                    ], spacing=1, expand=True),
                    ft.Column([
                        ft.Container(bgcolor=FIELD, border=ft.border.all(1, cc), border_radius=5,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            content=ft.Text(_cell_label(st), size=10, color=cc, weight=ft.FontWeight.BOLD)),
                        ft.Text(str(cell.get("date_expiration") or "-"), size=9, color=MUTED),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
            ))

        main_area.controls = [
            ft.TextButton("← Retour a la liste des employes",
                style=ft.ButtonStyle(color=MUTED),
                on_click=lambda e: show_grid()),
            ft.Container(
                bgcolor=CARD,
                border=ft.border.only(left=ft.BorderSide(4, color), top=ft.BorderSide(1, BORDER),
                    right=ft.BorderSide(1, BORDER), bottom=ft.BorderSide(1, BORDER)),
                border_radius=10, padding=16,
                content=ft.Row([
                    ft.Container(width=52, height=52, bgcolor=FIELD, border=ft.border.all(2, color),
                        border_radius=14, alignment=ft.Alignment(0, 0),
                        content=ft.Text(initials, size=18, weight=ft.FontWeight.BOLD, color=color)),
                    ft.Column([
                        ft.Text(_name(employee), size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row([
                            _mini_tag(str(employee.get("fonction") or "-"), PRIMARY),
                            _mini_tag(str(employee.get("departement") or "-"), MUTED),
                            _mini_tag(f"Badge {employee.get('numero_badge') or '-'}", MUTED),
                        ], spacing=6, wrap=True),
                    ], spacing=6, expand=True),
                    ft.Column([
                        ft.Text(f"{conformity}%", size=30, weight=ft.FontWeight.BOLD, color=color, text_align=ft.TextAlign.CENTER),
                        ft.Text("conformite", size=10, color=MUTED, text_align=ft.TextAlign.CENTER),
                        ft.ProgressBar(value=conformity / 100, color=color, bgcolor=FIELD, height=6, width=90),
                    ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            ft.ResponsiveRow([
                _mini_stat("Formations OK", sum(1 for c in cells if c.get("status") == "done"), SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
                _mini_stat("Bientot exp.", sum(1 for c in cells if c.get("status") == "soon"), WARNING, ft.Icons.SCHEDULE_OUTLINED),
                _mini_stat("Expirees", sum(1 for c in cells if c.get("status") == "expired"), DANGER, ft.Icons.EVENT_BUSY_OUTLINED),
                _mini_stat("Manquantes", sum(1 for c in cells if c.get("status") == "missing"), DANGER, ft.Icons.CANCEL_OUTLINED),
                _mini_stat("N/A", sum(1 for c in cells if c.get("status") == "not_applicable"), MUTED, ft.Icons.REMOVE_CIRCLE_OUTLINE),
            ], spacing=8, run_spacing=8),
            _panel("Formations & habilitations", [
                ft.Text(
                    f"{sum(1 for c in cells if c.get('status') != 'not_applicable')} formations requises  "
                    f"•  {sum(1 for c in cells if c.get('status') == 'done')} validees  "
                    f"•  {sum(1 for c in cells if c.get('status') in {'expired','missing'})} a traiter",
                    size=11, color=MUTED,
                ),
                *formation_rows,
            ]),
        ]
        try:
            main_area.update()
        except RuntimeError:
            pass

    def show_grid(query: str = "") -> None:
        filtered = all_rows
        if query.strip():
            q = query.strip().lower()
            filtered = [
                r for r in all_rows
                if q in f"{r.get('employee',{}).get('nom','')} {r.get('employee',{}).get('prenom','')} {r.get('employee',{}).get('fonction','')}".lower()
            ]
        conformes = sum(1 for r in filtered if _conformity_pct(r.get("cells") or []) >= 85)
        main_area.controls = [
            ft.Container(bgcolor=CARD, border=ft.border.all(1, BORDER), border_radius=8, padding=12,
                content=ft.Row([
                    ft.Icon(ft.Icons.GROUPS_OUTLINED, color=PRIMARY, size=20),
                    ft.Text(f"{len(filtered)} employe(s)  •  {conformes} conforme(s)  •  {len(filtered) - conformes} a traiter",
                           size=12, color=MUTED, expand=True),
                    ft.TextButton("Voir la matrice", icon=ft.Icons.GRID_VIEW_OUTLINED, on_click=lambda e: set_view("matrix"),
                        style=ft.ButtonStyle(color=PRIMARY)),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)),
            ft.ResponsiveRow([
                ft.Container(
                    col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
                    bgcolor=CARD,
                    border=ft.border.all(2, _pct_color(_conformity_pct(r.get("cells") or []))),
                    border_radius=10, padding=12, ink=True,
                    on_click=lambda e, row=r: show_fiche(row),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=8, height=8,
                                bgcolor=_pct_color(_conformity_pct(r.get("cells") or [])),
                                border_radius=4),
                            ft.Text(_name(r.get("employee") or {}), size=12, weight=ft.FontWeight.BOLD, color=TEXT,
                                expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ], spacing=6),
                        ft.Text(str((r.get("employee") or {}).get("fonction") or "-"), size=10, color=MUTED),
                        ft.Row([
                            ft.Text(f"{_conformity_pct(r.get('cells') or [])}%", size=20,
                                weight=ft.FontWeight.BOLD, color=_pct_color(_conformity_pct(r.get("cells") or []))),
                            ft.Text("conformite", size=10, color=MUTED),
                        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.BASELINE),
                        ft.ProgressBar(value=_conformity_pct(r.get("cells") or []) / 100,
                            color=_pct_color(_conformity_pct(r.get("cells") or [])), bgcolor=FIELD, height=5),
                        ft.Row([
                            _mini_badge(sum(1 for c in (r.get("cells") or []) if c.get("status") == "done"), SUCCESS),
                            _mini_badge(sum(1 for c in (r.get("cells") or []) if c.get("status") == "soon"), WARNING),
                            _mini_badge(sum(1 for c in (r.get("cells") or []) if c.get("status") in {"expired","missing"}), DANGER),
                        ], spacing=4),
                    ], spacing=6),
                )
                for r in filtered
            ], spacing=10, run_spacing=10) if filtered else ft.Text("Aucun employe trouve.", color=MUTED, size=12),
        ]
        try:
            main_area.update()
        except RuntimeError:
            pass

    search = ft.TextField(
        hint_text="Rechercher nom, prenom, fonction...",
        prefix_icon=ft.Icons.SEARCH, width=320,
        fill_color=FIELD, color=TEXT, border_color=BORDER,
        label_style=ft.TextStyle(color=MUTED),
        text_style=ft.TextStyle(color=TEXT),
        on_change=lambda e: show_grid(str(e.control.value or "")),
    )

    show_grid()
    return ft.Column([
        _section_intro("Fiches Employes", "Conformite individuelle et detail des habilitations par employe.", ft.Icons.BADGE_OUTLINED),
        ft.Container(bgcolor=CARD, border=ft.border.all(1, BORDER), border_radius=8, padding=12,
            content=ft.Row([search], spacing=10)),
        main_area,
    ], spacing=12)


def _mini_badge(count: int, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD, border=ft.border.all(1, color), border_radius=5,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        content=ft.Text(str(count), color=color, size=10, weight=ft.FontWeight.BOLD),
    )


def _mini_tag(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD, border=ft.border.all(1, color), border_radius=5,
        padding=ft.padding.symmetric(horizontal=7, vertical=2),
        content=ft.Text(label, color=color, size=10),
    )


def _mini_stat(label: str, value: int, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"xs": 6, "md": 4, "lg": 2},
        bgcolor=CARD, border=ft.border.all(1, BORDER), border_radius=8, padding=10,
        content=ft.Row([
            ft.Icon(icon, color=color, size=16),
            ft.Column([
                ft.Text(str(value), size=18, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(label, size=9, color=MUTED),
            ], spacing=1),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )
