from __future__ import annotations

from typing import Any

import flet as ft

from app.services.risk_service import (
    list_risks,
    get_risk,
    create_risk,
    update_risk,
    delete_risk,
    get_risk_summary,
    get_risk_heatmap,
    list_controls,
    create_control,
    update_control,
    delete_control,
    get_risk_filter_options,
    get_risk_history,
    list_risk_links,
    add_risk_link,
    delete_risk_link,
    get_overdue_reviews,
)
from app.services.risk_export_service import (
    export_risk_register_pdf,
    export_risk_register_xlsx,
    export_risk_fiche_pdf,
    open_export_file,
)
from app.ui.components.module_header import module_header
from app.ui.components.pagination import PAGE_SIZE, pagination_row
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING

# ── Dark palette ──────────────────────────────────────────────────────────────
_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"
_DK_TRACK  = "#1A3050"

# ── Risk level colours ────────────────────────────────────────────────────────
_CLR_CRITIQUE = "#EF4444"
_CLR_ELEVE    = "#F97316"
_CLR_MOYEN    = "#F59E0B"
_CLR_FAIBLE   = "#10B981"

_OV: dict[str, str] = {
    "#EF4444": "#3B0F0F",
    "#F97316": "#2D1600",
    "#F59E0B": "#2D1F00",
    "#10B981": "#052E16",
    PRIMARY:   "#0F2D5E",
    DANGER:    "#3B0F0F",
    WARNING:   "#2D1F00",
    SUCCESS:   "#052E16",
}

# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _risk_color(score: int) -> str:
    if score >= 15:
        return "#EF4444"
    if score >= 10:
        return "#F97316"
    if score >= 5:
        return "#F59E0B"
    return "#10B981"


def _risk_level_label(score: int) -> str:
    if score >= 15:
        return "CRITIQUE"
    if score >= 10:
        return "ÉLEVÉ"
    if score >= 5:
        return "MOYEN"
    return "FAIBLE"


def _level_badge(level: str) -> ft.Control:
    colors = {
        "critique": "#EF4444",
        "eleve":    "#F97316",
        "moyen":    "#F59E0B",
        "faible":   "#10B981",
    }
    labels = {
        "critique": "CRITIQUE",
        "eleve":    "ÉLEVÉ",
        "moyen":    "MOYEN",
        "faible":   "FAIBLE",
    }
    ov = {
        "#EF4444": "#3B0F0F",
        "#F97316": "#2D1600",
        "#F59E0B": "#2D1F00",
        "#10B981": "#052E16",
    }
    color = colors.get(level, "#9DB0C5")
    return ft.Container(
        bgcolor=ov.get(color, "#0A1929"),
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(
            labels.get(level, level.upper()),
            color=color,
            size=10,
            weight=ft.FontWeight.BOLD,
        ),
    )


def _status_badge(status: str) -> ft.Control:
    colors = {
        "ouvert":   "#EF4444",
        "en_cours": "#F59E0B",
        "clos":     "#10B981",
    }
    labels = {
        "ouvert":   "Ouvert",
        "en_cours": "En cours",
        "clos":     "Clos",
    }
    ov = {
        "#EF4444": "#3B0F0F",
        "#F59E0B": "#2D1F00",
        "#10B981": "#052E16",
    }
    color = colors.get(status, "#9DB0C5")
    return ft.Container(
        bgcolor=ov.get(color, "#0A1929"),
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(
            labels.get(status, status),
            color=color,
            size=10,
            weight=ft.FontWeight.BOLD,
        ),
    )


def _control_status_badge(status: str) -> ft.Control:
    colors = {
        "planifie":  WARNING,
        "en_cours":  PRIMARY,
        "realise":   SUCCESS,
    }
    labels = {
        "planifie":  "Planifié",
        "en_cours":  "En cours",
        "realise":   "Réalisé",
    }
    ov_map = {
        WARNING: "#2D1F00",
        PRIMARY: "#0F2D5E",
        SUCCESS: "#052E16",
    }
    color = colors.get(status, "#9DB0C5")
    return ft.Container(
        bgcolor=ov_map.get(color, "#0A1929"),
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(
            labels.get(status, status),
            color=color,
            size=10,
            weight=ft.FontWeight.BOLD,
        ),
    )


def _empty_state(icon: str, title: str, subtitle: str = "") -> ft.Control:
    return ft.Container(
        bgcolor="#0D2040",
        border=ft.border.all(1, "#1E3A5F"),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=24, vertical=40),
        content=ft.Column(
            controls=[
                ft.Container(
                    width=64,
                    height=64,
                    bgcolor="#112240",
                    border_radius=32,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color="#9DB0C5", size=28),
                ),
                ft.Text(
                    title,
                    color="#E2E8F0",
                    size=15,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(subtitle, color="#9DB0C5", size=12, text_align=ft.TextAlign.CENTER)
                if subtitle
                else ft.Container(height=0),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
    )


def _panel_dk(title: str, icon: str, accent: str, body: ft.Control) -> ft.Control:
    return ft.Container(
        bgcolor="#0D2040",
        border=ft.border.all(1, "#1E3A5F"),
        border_radius=12,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor="#112240",
                    border=ft.border.only(bottom=ft.BorderSide(1, "#1E3A5F")),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=14, bgcolor=accent, border_radius=2),
                            ft.Icon(icon, color=accent, size=16),
                            ft.Text(title, color="#E2E8F0", size=14, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=14),
                    content=body,
                ),
            ],
            spacing=0,
        ),
    )


def _score_display(score: int) -> ft.Control:
    color = _risk_color(score)
    label = _risk_level_label(score)
    return ft.Container(
        bgcolor=_OV.get(color, "#0F2D5E"),
        border=ft.border.all(2, color),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            controls=[
                ft.Text(
                    f"Score: {score}",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    label,
                    size=14,
                    color=color,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main page
# ─────────────────────────────────────────────────────────────────────────────

def risk_analysis_page(page: Any = None) -> ft.Control:  # noqa: C901
    state: dict[str, Any] = {
        "tab":              "dashboard",
        "editing_id":       None,
        "selected_risk_id": None,
        "filter_level":     "tous",
        "filter_status":    "tous",
        "filter_hazard":    "tous",
        "sort_col":         "risk_score",
        "sort_dir":         "desc",
        "page":             0,
    }

    content_area = ft.Container()
    tab_buttons: dict[str, ft.ElevatedButton] = {}

    # ── Tab bar ───────────────────────────────────────────────────────────────
    _TABS = [
        ("dashboard",  "Tableau de bord",       ft.Icons.DASHBOARD_OUTLINED),
        ("registre",   "Registre des risques",  ft.Icons.TABLE_ROWS_OUTLINED),
        ("evaluation", "Nouvelle évaluation",   ft.Icons.EDIT_NOTE_OUTLINED),
        ("actions",    "Plan de maîtrise",      ft.Icons.CHECKLIST_OUTLINED),
    ]

    def _switch_tab(tab_key: str) -> None:
        state["tab"] = tab_key
        _refresh_tab_styles()
        _render_content()

    def _refresh_tab_styles() -> None:
        for key, btn in tab_buttons.items():
            if key == state["tab"]:
                btn.style = ft.ButtonStyle(
                    bgcolor={ft.ControlState.DEFAULT: PRIMARY},
                    color={ft.ControlState.DEFAULT: "#FFFFFF"},
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                )
            else:
                btn.style = ft.ButtonStyle(
                    bgcolor={ft.ControlState.DEFAULT: _DK_CARD},
                    color={ft.ControlState.DEFAULT: _DK_MUTED},
                    shape=ft.RoundedRectangleBorder(radius=8),
                    side=ft.BorderSide(1, _DK_BORDER),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                )
            try:
                btn.update()
            except RuntimeError:
                pass

    def _render_content() -> None:
        try:
            if state["tab"] == "dashboard":
                controls = _render_dashboard()
            elif state["tab"] == "registre":
                controls = _render_registre()
            elif state["tab"] == "evaluation":
                controls = _render_evaluation()
            elif state["tab"] == "actions":
                controls = _render_actions()
            else:
                controls = []
            content_area.content = ft.Column(controls=controls, spacing=14, tight=True)
        except Exception as exc:
            content_area.content = ft.Container(
                bgcolor=_DK_CARD,
                border=ft.border.all(1, DANGER),
                border_radius=10,
                padding=16,
                content=ft.Text(f"Erreur de rendu: {exc}", color=DANGER, size=12),
            )
        try:
            content_area.update()
        except RuntimeError:
            pass

    # ── TAB 1: Dashboard ──────────────────────────────────────────────────────

    def _render_dashboard() -> list[ft.Control]:
        try:
            summary = get_risk_summary()
        except Exception:
            summary = {
                "total": 0, "critique": 0, "eleve": 0, "moyen": 0,
                "faible": 0, "ouvert": 0, "en_cours": 0, "clos": 0,
            }

        kpi_defs = [
            ("Total risques",  summary["total"],    PRIMARY,        ft.Icons.GRID_VIEW_OUTLINED),
            ("Critiques",      summary["critique"], _CLR_CRITIQUE,  ft.Icons.REPORT_PROBLEM_OUTLINED),
            ("Élevés",         summary["eleve"],    _CLR_ELEVE,     ft.Icons.WARNING_AMBER_OUTLINED),
            ("Moyens",         summary["moyen"],    _CLR_MOYEN,     ft.Icons.REMOVE_CIRCLE_OUTLINED),
            ("Ouverts",        summary["ouvert"],   WARNING,        ft.Icons.LOCK_OPEN_OUTLINED),
            ("Clos",           summary["clos"],     SUCCESS,        ft.Icons.LOCK_OUTLINED),
        ]

        kpi_cards = []
        for label, value, color, icon in kpi_defs:
            kpi_cards.append(
                ft.Container(
                    col={"xs": 12, "sm": 6, "md": 4, "lg": 2},
                    content=ft.Container(
                        bgcolor=_DK_CARD,
                        border=ft.border.only(
                            left=ft.BorderSide(4, color),
                            top=ft.BorderSide(1, _DK_BORDER),
                            right=ft.BorderSide(1, _DK_BORDER),
                            bottom=ft.BorderSide(1, _DK_BORDER),
                        ),
                        border_radius=12,
                        padding=ft.padding.only(left=14, right=14, top=12, bottom=12),
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            width=32,
                                            height=32,
                                            bgcolor=_OV.get(color, "#0F2D5E"),
                                            border_radius=8,
                                            alignment=ft.Alignment(0, 0),
                                            content=ft.Icon(icon, color=color, size=16),
                                        ),
                                        ft.Text(
                                            label,
                                            color=_DK_MUTED,
                                            size=10,
                                            weight=ft.FontWeight.W_500,
                                            expand=True,
                                            max_lines=2,
                                        ),
                                    ],
                                    spacing=7,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Text(
                                    str(value),
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color=_DK_TEXT,
                                ),
                            ],
                            spacing=4,
                        ),
                    ),
                )
            )

        kpi_row = ft.ResponsiveRow(controls=kpi_cards, spacing=12, run_spacing=12)

        # Heatmap
        try:
            heatmap_data = get_risk_heatmap()
        except Exception:
            heatmap_data = {}

        axis_label_style = ft.TextStyle(color=_DK_MUTED, size=10, weight=ft.FontWeight.W_500)

        grid_rows: list[ft.Control] = []
        for prob in range(5, 0, -1):
            row_cells: list[ft.Control] = [
                ft.Container(
                    width=30,
                    height=40,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(f"P{prob}", style=axis_label_style),
                )
            ]
            for sev in range(1, 6):
                score = prob * sev
                clr = _risk_color(score)
                cnt = heatmap_data.get((prob, sev), 0)
                cell_text = str(cnt) if cnt > 0 else str(score)
                row_cells.append(
                    ft.Container(
                        width=56,
                        height=40,
                        bgcolor=_OV.get(clr, "#0F2D5E"),
                        border=ft.border.all(1, clr),
                        border_radius=6,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            cell_text,
                            color=clr,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                    )
                )
            grid_rows.append(
                ft.Row(controls=row_cells, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

        # X-axis labels
        x_labels: list[ft.Control] = [ft.Container(width=30)]
        for sev in range(1, 6):
            x_labels.append(
                ft.Container(
                    width=56,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(f"G{sev}", style=axis_label_style),
                )
            )
        grid_rows.append(ft.Row(controls=x_labels, spacing=4))

        # Legend
        legend_items = [
            ("Critique", _CLR_CRITIQUE),
            ("Élevé",    _CLR_ELEVE),
            ("Moyen",    _CLR_MOYEN),
            ("Faible",   _CLR_FAIBLE),
        ]
        legend_pills: list[ft.Control] = []
        for lbl, clr in legend_items:
            legend_pills.append(
                ft.Container(
                    bgcolor=_OV.get(clr, "#0F2D5E"),
                    border=ft.border.all(1, clr),
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                    content=ft.Text(lbl, color=clr, size=11, weight=ft.FontWeight.W_600),
                )
            )

        heatmap_body = ft.Column(
            controls=[
                ft.Column(controls=grid_rows, spacing=4),
                ft.Row(controls=legend_pills, spacing=8, wrap=True),
            ],
            spacing=12,
        )

        heatmap_panel = _panel_dk(
            "Matrice de Criticité 5×5",
            ft.Icons.GRID_VIEW_OUTLINED,
            PRIMARY,
            heatmap_body,
        )

        # Top critical risks
        try:
            all_risks = list_risks()
        except Exception:
            all_risks = []

        top_risks = sorted(all_risks, key=lambda r: r.get("risk_score", 0) or 0, reverse=True)[:5]

        if top_risks:
            top_rows: list[ft.Control] = []
            for risk in top_risks:
                sc = risk.get("risk_score") or 0
                clr = _risk_color(int(sc))
                hazard = risk.get("hazard_type") or ""
                top_rows.append(
                    ft.Container(
                        bgcolor=_DK_CARD2,
                        border=ft.border.all(1, _DK_BORDER),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    width=36,
                                    height=36,
                                    bgcolor=_OV.get(clr, "#0F2D5E"),
                                    border=ft.border.all(2, clr),
                                    border_radius=8,
                                    alignment=ft.Alignment(0, 0),
                                    content=ft.Text(
                                        str(int(sc)),
                                        color=clr,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ),
                                ft.Text(
                                    str(risk.get("title") or ""),
                                    color=_DK_TEXT,
                                    size=12,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Container(
                                    bgcolor=_DK_HEAD,
                                    border=ft.border.all(1, _DK_BORDER),
                                    border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    content=ft.Text(hazard, color=_DK_MUTED, size=10),
                                ) if hazard else ft.Container(width=0),
                                _level_badge(str(risk.get("risk_level") or "faible")),
                                _status_badge(str(risk.get("status") or "ouvert")),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            top_body = ft.Column(controls=top_rows, spacing=6)
        else:
            top_body = ft.Text("Aucun risque enregistré.", color=_DK_MUTED, size=12)

        top_panel = _panel_dk(
            "Top risques critiques",
            ft.Icons.PRIORITY_HIGH_OUTLINED,
            _CLR_CRITIQUE,
            top_body,
        )

        # Révisions en retard (B)
        try:
            overdue = get_overdue_reviews()
        except Exception:
            overdue = []

        panels: list[ft.Control] = [kpi_row, heatmap_panel, top_panel]

        if overdue:
            overdue_rows: list[ft.Control] = []
            for ov_r in overdue:
                days_str = str(ov_r.get("review_date") or "")
                overdue_rows.append(
                    ft.Container(
                        bgcolor=_DK_CARD2,
                        border=ft.border.all(1, _CLR_ELEVE),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=7),
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=_CLR_ELEVE, size=14),
                                ft.Text(
                                    str(ov_r.get("title") or ""),
                                    color=_DK_TEXT,
                                    size=12,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(f"Prévue: {days_str}", color=_CLR_ELEVE, size=11),
                                _level_badge(str(ov_r.get("risk_level") or "faible")),
                                ft.Text(str(ov_r.get("owner") or "—"), color=_DK_MUTED, size=11),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            overdue_body = ft.Column(controls=overdue_rows, spacing=6, tight=True)
            overdue_panel = _panel_dk(
                f"Révisions en retard ({len(overdue)})",
                ft.Icons.ALARM_OUTLINED,
                _CLR_ELEVE,
                overdue_body,
            )
            panels.append(overdue_panel)

        return panels

    # ── TAB 2: Registre ───────────────────────────────────────────────────────

    def _render_registre() -> list[ft.Control]:
        try:
            filter_opts = get_risk_filter_options()
            hazard_types = filter_opts.get("hazard_types", [])
        except Exception:
            hazard_types = []

        dd_style = dict(
            fill_color=_DK_CARD,
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            text_style=ft.TextStyle(color=_DK_TEXT),
            width=160,
        )

        dd_level = ft.Dropdown(
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
            label="Niveau",
            value=state["filter_level"],
            options=[
                ft.dropdown.Option("tous",     "Tous"),
                ft.dropdown.Option("critique", "Critique"),
                ft.dropdown.Option("eleve",    "Élevé"),
                ft.dropdown.Option("moyen",    "Moyen"),
                ft.dropdown.Option("faible",   "Faible"),
            ],
            **dd_style,
        )
        dd_status = ft.Dropdown(
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
            label="Statut",
            value=state["filter_status"],
            options=[
                ft.dropdown.Option("tous",     "Tous"),
                ft.dropdown.Option("ouvert",   "Ouvert"),
                ft.dropdown.Option("en_cours", "En cours"),
                ft.dropdown.Option("clos",     "Clos"),
            ],
            **dd_style,
        )

        hazard_options = [ft.dropdown.Option("tous", "Tous")]
        for h in hazard_types:
            hazard_options.append(ft.dropdown.Option(h, h.capitalize()))
        dd_hazard = ft.Dropdown(
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
            label="Type de danger",
            value=state["filter_hazard"],
            options=hazard_options,
            **dd_style,
        )

        _LEVEL_SORT: dict[str, int] = {"critique": 4, "eleve": 3, "moyen": 2, "faible": 1}

        def _sort_key_fn(key: str):
            mapping: dict[str, Any] = {
                "id":          lambda r: r.get("id") or 0,
                "title":       lambda r: str(r.get("title") or "").lower(),
                "activity":    lambda r: str(r.get("activity") or "").lower(),
                "hazard_type": lambda r: str(r.get("hazard_type") or "").lower(),
                "risk_score":  lambda r: r.get("risk_score") or 0,
                "risk_level":  lambda r: _LEVEL_SORT.get(str(r.get("risk_level") or "faible"), 0),
                "status":      lambda r: str(r.get("status") or "").lower(),
                "owner":       lambda r: str(r.get("owner") or "").lower(),
            }
            return mapping.get(key, lambda r: 0)

        def _sort_by_col(key: str) -> None:
            if state.get("sort_col") == key:
                state["sort_dir"] = "asc" if state.get("sort_dir") == "desc" else "desc"
            else:
                state["sort_col"] = key
                state["sort_dir"] = "desc"
            _load_table()

        def _make_col_header(label: str, key: str | None = None) -> ft.DataColumn:
            if key is None:
                return ft.DataColumn(
                    ft.Text(label, color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)
                )
            is_sorted = state.get("sort_col") == key
            sort_icon = (
                ft.Icons.ARROW_UPWARD if state.get("sort_dir") == "asc"
                else ft.Icons.ARROW_DOWNWARD
            ) if is_sorted else ft.Icons.UNFOLD_MORE
            return ft.DataColumn(
                ft.TextButton(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                label,
                                color=PRIMARY if is_sorted else _DK_MUTED,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Icon(sort_icon, color=PRIMARY if is_sorted else _DK_MUTED, size=12),
                        ],
                        spacing=2,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    style=ft.ButtonStyle(padding=ft.padding.all(0)),
                    on_click=lambda e, k=key: _sort_by_col(k),
                )
            )

        def _print_fiche(risk: dict[str, Any]) -> None:
            try:
                path = export_risk_fiche_pdf(int(risk["id"]))
                open_export_file(path)
                if page:
                    page.show_dialog(ft.SnackBar(
                        content=ft.Text(f"Fiche PDF : {path.name}", color="#FFFFFF"),
                        bgcolor=SUCCESS,
                    ))
            except Exception as exc:
                if page:
                    page.show_dialog(ft.SnackBar(
                        content=ft.Text(f"Erreur fiche PDF : {exc}", color="#FFFFFF"),
                        bgcolor=DANGER,
                    ))

        table_area = ft.Column(spacing=8, tight=True)

        def _load_table() -> None:
            try:
                risks = list_risks(
                    status=state["filter_status"] if state["filter_status"] != "tous" else None,
                    level=state["filter_level"] if state["filter_level"] != "tous" else None,
                    hazard_type=state["filter_hazard"] if state["filter_hazard"] != "tous" else None,
                )
            except Exception:
                risks = []

            sort_col = state.get("sort_col", "risk_score")
            sort_rev = state.get("sort_dir", "desc") == "desc"
            try:
                risks = sorted(risks, key=_sort_key_fn(sort_col), reverse=sort_rev)
            except Exception:
                pass

            total = len(risks)
            max_page = max(0, (total - 1) // PAGE_SIZE) if total else 0
            state["page"] = max(0, min(max_page, state["page"]))
            start = state["page"] * PAGE_SIZE
            page_risks = risks[start : start + PAGE_SIZE]

            if not risks:
                table_area.controls = [
                    _empty_state(
                        ft.Icons.TABLE_ROWS_OUTLINED,
                        "Aucun risque trouvé",
                        "Modifiez les filtres ou créez un nouveau risque.",
                    )
                ]
                try:
                    table_area.update()
                except RuntimeError:
                    pass
                return

            cols = [
                _make_col_header("N°",          "id"),
                _make_col_header("Titre",       "title"),
                _make_col_header("Activité",    "activity"),
                _make_col_header("Type",        "hazard_type"),
                _make_col_header("P×G",         "risk_score"),
                _make_col_header("Niveau",      "risk_level"),
                _make_col_header("Statut",      "status"),
                _make_col_header("Responsable", "owner"),
                _make_col_header("Actions"),
            ]

            rows: list[ft.DataRow] = []
            for risk in page_risks:
                rid    = risk.get("id", "")
                sc     = risk.get("risk_score") or 0
                clr    = _risk_color(int(sc))
                lvl    = str(risk.get("risk_level") or "faible")
                stat   = str(risk.get("status") or "ouvert")

                def _edit(r=risk) -> None:
                    state["editing_id"] = r.get("id")
                    _switch_tab("evaluation")

                def _del(r=risk) -> None:
                    try:
                        delete_risk(int(r["id"]))
                    except Exception:
                        pass
                    _render_content()

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(rid), color=_DK_MUTED, size=11)),
                            ft.DataCell(
                                ft.Text(
                                    str(risk.get("title") or ""),
                                    color=_DK_TEXT,
                                    size=12,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    str(risk.get("activity") or "—"),
                                    color=_DK_MUTED,
                                    size=11,
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    str(risk.get("hazard_type") or "—"),
                                    color=_DK_MUTED,
                                    size=11,
                                )
                            ),
                            ft.DataCell(
                                ft.Text(str(int(sc)), color=clr, size=12, weight=ft.FontWeight.BOLD)
                            ),
                            ft.DataCell(_level_badge(lvl)),
                            ft.DataCell(_status_badge(stat)),
                            ft.DataCell(
                                ft.Text(
                                    str(risk.get("owner") or "—"),
                                    color=_DK_MUTED,
                                    size=11,
                                )
                            ),
                            ft.DataCell(
                                ft.Row(
                                    controls=[
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT_OUTLINED,
                                            icon_color=PRIMARY,
                                            icon_size=16,
                                            tooltip="Modifier",
                                            on_click=lambda e, r=risk: _edit(r),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                                            icon_color=WARNING,
                                            icon_size=16,
                                            tooltip="Fiche PDF",
                                            on_click=lambda e, r=risk: _print_fiche(r),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            icon_color=DANGER,
                                            icon_size=16,
                                            tooltip="Supprimer",
                                            on_click=lambda e, r=risk: _del(r),
                                        ),
                                    ],
                                    spacing=0,
                                )
                            ),
                        ]
                    )
                )

            table = ft.DataTable(
                columns=cols,
                rows=rows,
                heading_row_color={ft.ControlState.DEFAULT: _DK_HEAD},
                data_row_color={ft.ControlState.DEFAULT: _DK_CARD},
                border=ft.border.all(1, _DK_BORDER),
                border_radius=10,
                column_spacing=16,
                data_row_min_height=44,
            )

            table_area.controls = [
                ft.Container(
                    bgcolor=_DK_CARD,
                    border_radius=10,
                    content=ft.Row(
                        controls=[table],
                        scroll=ft.ScrollMode.AUTO,
                        tight=True,
                    ),
                ),
                pagination_row(
                    current_page=state["page"],
                    max_page=max_page,
                    total=total,
                    shown_start=start + 1 if page_risks else 0,
                    shown_end=start + len(page_risks),
                    item_label="risque(s)",
                    on_prev=lambda: (state.__setitem__("page", state["page"] - 1), _load_table()),
                    on_next=lambda: (state.__setitem__("page", state["page"] + 1), _load_table()),
                    on_page=lambda p: (state.__setitem__("page", p), _load_table()),
                ),
            ]
            try:
                table_area.update()
            except RuntimeError:
                pass

        def _apply_filters(e: Any = None) -> None:
            state["filter_level"]  = dd_level.value or "tous"
            state["filter_status"] = dd_status.value or "tous"
            state["filter_hazard"] = dd_hazard.value or "tous"
            state["page"] = 0
            _load_table()

        def _reset_filters(e: Any = None) -> None:
            state["filter_level"]  = "tous"
            state["filter_status"] = "tous"
            state["filter_hazard"] = "tous"
            state["page"] = 0
            dd_level.value  = "tous"
            dd_status.value = "tous"
            dd_hazard.value = "tous"
            for dd in (dd_level, dd_status, dd_hazard):
                try:
                    dd.update()
                except RuntimeError:
                    pass
            _load_table()

        def _new_risk(e: Any = None) -> None:
            state["editing_id"] = None
            _switch_tab("evaluation")

        def _do_export_xlsx(e: Any = None) -> None:
            try:
                path = export_risk_register_xlsx(
                    status=state["filter_status"] if state["filter_status"] != "tous" else None,
                    level=state["filter_level"] if state["filter_level"] != "tous" else None,
                    hazard_type=state["filter_hazard"] if state["filter_hazard"] != "tous" else None,
                )
                open_export_file(path)
                if page:
                    page.show_dialog(ft.SnackBar(
                        content=ft.Text(f"Export Excel : {path.name}", color="#FFFFFF"),
                        bgcolor=SUCCESS,
                    ))
            except Exception as exc:
                if page:
                    page.show_dialog(ft.SnackBar(
                        content=ft.Text(f"Erreur export Excel : {exc}", color="#FFFFFF"),
                        bgcolor=DANGER,
                    ))

        def _do_export_pdf(e: Any = None) -> None:
            try:
                path = export_risk_register_pdf(
                    status=state["filter_status"] if state["filter_status"] != "tous" else None,
                    level=state["filter_level"] if state["filter_level"] != "tous" else None,
                    hazard_type=state["filter_hazard"] if state["filter_hazard"] != "tous" else None,
                )
                open_export_file(path)
                if page:
                    page.show_dialog(ft.SnackBar(
                        content=ft.Text(f"Export PDF : {path.name}", color="#FFFFFF"),
                        bgcolor=SUCCESS,
                    ))
            except Exception as exc:
                if page:
                    page.show_dialog(ft.SnackBar(
                        content=ft.Text(f"Erreur export PDF : {exc}", color="#FFFFFF"),
                        bgcolor=DANGER,
                    ))

        filter_bar = ft.Container(
            bgcolor=_DK_CARD2,
            border=ft.border.all(1, _DK_BORDER),
            border_radius=10,
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            dd_level,
                            dd_status,
                            dd_hazard,
                            ft.ElevatedButton(
                                "Filtrer",
                                icon=ft.Icons.FILTER_LIST,
                                bgcolor=PRIMARY,
                                color="#FFFFFF",
                                on_click=_apply_filters,
                            ),
                            ft.OutlinedButton(
                                "Réinitialiser",
                                icon=ft.Icons.REFRESH,
                                style=ft.ButtonStyle(
                                    color={ft.ControlState.DEFAULT: _DK_MUTED},
                                    side=ft.BorderSide(1, _DK_BORDER),
                                ),
                                on_click=_reset_filters,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "+ Nouveau risque",
                                bgcolor=SUCCESS,
                                color="#FFFFFF",
                                icon=ft.Icons.ADD,
                                on_click=_new_risk,
                            ),
                            ft.OutlinedButton(
                                "Export Excel",
                                icon=ft.Icons.TABLE_CHART_OUTLINED,
                                style=ft.ButtonStyle(
                                    color={ft.ControlState.DEFAULT: SUCCESS},
                                    side=ft.BorderSide(1, SUCCESS),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=_do_export_xlsx,
                            ),
                            ft.OutlinedButton(
                                "Export PDF",
                                icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                                style=ft.ButtonStyle(
                                    color={ft.ControlState.DEFAULT: DANGER},
                                    side=ft.BorderSide(1, DANGER),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=_do_export_pdf,
                            ),
                        ],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
        )

        _load_table()
        return [filter_bar, table_area]

    # ── TAB 3: Évaluation ─────────────────────────────────────────────────────

    def _render_evaluation() -> list[ft.Control]:
        editing_id = state.get("editing_id")
        existing: dict[str, Any] = {}
        if editing_id is not None:
            try:
                existing = get_risk(int(editing_id)) or {}
            except Exception:
                existing = {}

        # Form fields – left column
        tf_titre = ft.TextField(
            label="Titre du risque *",
            value=str(existing.get("title") or ""),
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
        )
        tf_activite = ft.TextField(
            label="Activité / Tâche",
            value=str(existing.get("activity") or ""),
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
        )
        tf_zone = ft.TextField(
            label="Zone / Localisation",
            value=str(existing.get("location") or existing.get("zone") or ""),
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
        )

        hazard_options_eval = [
            ft.dropdown.Option("physique",       "Physique"),
            ft.dropdown.Option("chimique",       "Chimique"),
            ft.dropdown.Option("biologique",     "Biologique"),
            ft.dropdown.Option("ergonomique",    "Ergonomique"),
            ft.dropdown.Option("psychosocial",   "Psychosocial"),
            ft.dropdown.Option("environnemental","Environnemental"),
            ft.dropdown.Option("electrique",     "Electrique"),
            ft.dropdown.Option("incendie",       "Incendie"),
            ft.dropdown.Option("chute",          "Chute"),
            ft.dropdown.Option("autre",          "Autre"),
        ]
        dd_hazard_type = ft.Dropdown(
            label="Type de danger",
            value=str(existing.get("hazard_type") or "physique"),
            options=hazard_options_eval,
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            text_style=ft.TextStyle(color=_DK_TEXT),
        )
        tf_exposed = ft.TextField(
            label="Personnes exposées",
            value=str(existing.get("affected_people") or ""),
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
        )
        tf_source = ft.TextField(
            label="Source du danger",
            value=str(existing.get("source_of_danger") or ""),
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
        )
        tf_existing_controls = ft.TextField(
            label="Mesures existantes",
            value=str(existing.get("existing_controls") or ""),
            multiline=True,
            max_lines=3,
            min_lines=3,
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
        )

        # Right column – evaluation
        prob_options = [
            ft.dropdown.Option("1", "1 – Rare"),
            ft.dropdown.Option("2", "2 – Peu probable"),
            ft.dropdown.Option("3", "3 – Possible"),
            ft.dropdown.Option("4", "4 – Probable"),
            ft.dropdown.Option("5", "5 – Presque certain"),
        ]
        sev_options = [
            ft.dropdown.Option("1", "1 – Négligeable"),
            ft.dropdown.Option("2", "2 – Mineur"),
            ft.dropdown.Option("3", "3 – Modéré"),
            ft.dropdown.Option("4", "4 – Grave"),
            ft.dropdown.Option("5", "5 – Catastrophique"),
        ]

        dd_prob = ft.Dropdown(
            label="Probabilité",
            value=str(existing.get("probability") or "1"),
            options=prob_options,
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            text_style=ft.TextStyle(color=_DK_TEXT),
        )
        dd_sev = ft.Dropdown(
            label="Gravité",
            value=str(existing.get("severity") or "1"),
            options=sev_options,
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            text_style=ft.TextStyle(color=_DK_TEXT),
        )

        score_display_ref = ft.Ref[ft.Container]()

        def _compute_score_widget(prob_val: str, sev_val: str) -> ft.Control:
            try:
                sc = int(prob_val or "1") * int(sev_val or "1")
            except Exception:
                sc = 1
            return _score_display(sc)

        score_container = ft.Container(
            content=_compute_score_widget(
                str(existing.get("probability") or "1"),
                str(existing.get("severity") or "1"),
            )
        )

        def _on_score_change(e: Any = None) -> None:
            score_container.content = _compute_score_widget(
                dd_prob.value or "1",
                dd_sev.value or "1",
            )
            try:
                score_container.update()
            except RuntimeError:
                pass

        def _on_res_score_change(e: Any = None) -> None:
            res_score_container.content = _compute_score_widget(
                dd_res_prob.value or "1",
                dd_res_sev.value or "1",
            )
            try:
                res_score_container.update()
            except RuntimeError:
                pass

        dd_prob.on_change = _on_score_change
        dd_sev.on_change  = _on_score_change

        dd_res_prob = ft.Dropdown(
            label="Probabilité résiduelle",
            value=str(existing.get("residual_probability") or "1"),
            options=prob_options,
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            text_style=ft.TextStyle(color=_DK_TEXT),
        )
        dd_res_sev = ft.Dropdown(
            label="Gravité résiduelle",
            value=str(existing.get("residual_severity") or "1"),
            options=sev_options,
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            text_style=ft.TextStyle(color=_DK_TEXT),
        )

        res_score_container = ft.Container(
            content=_compute_score_widget(
                str(existing.get("residual_probability") or "1"),
                str(existing.get("residual_severity") or "1"),
            )
        )

        dd_res_prob.on_change = _on_res_score_change
        dd_res_sev.on_change  = _on_res_score_change

        # Bottom row
        dd_status_eval = ft.Dropdown(
            label="Statut",
            value=str(existing.get("status") or "ouvert"),
            options=[
                ft.dropdown.Option("ouvert",   "Ouvert"),
                ft.dropdown.Option("en_cours", "En cours"),
                ft.dropdown.Option("clos",     "Clos"),
            ],
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            text_style=ft.TextStyle(color=_DK_TEXT),
            width=160,
        )
        tf_owner = ft.TextField(
            label="Responsable",
            value=str(existing.get("owner") or ""),
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            width=200,
        )
        tf_review_date = ft.TextField(
            label="Date de révision",
            hint_text="YYYY-MM-DD",
            value=str(existing.get("review_date") or ""),
            border_color=_DK_BORDER,
            focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=_DK_MUTED),
            hint_style=ft.TextStyle(color=_DK_MUTED),
            width=160,
        )

        feedback = ft.Text("", color=SUCCESS, size=12)

        def _save(e: Any = None) -> None:
            if not tf_titre.value or not tf_titre.value.strip():
                feedback.value = "Le titre est obligatoire."
                feedback.color = DANGER
                try:
                    feedback.update()
                except RuntimeError:
                    pass
                return
            data = {
                "title":                tf_titre.value.strip(),
                "activity":             tf_activite.value,
                "location":             tf_zone.value,
                "zone":                 tf_zone.value,
                "hazard_type":          dd_hazard_type.value,
                "affected_people":      tf_exposed.value,
                "source_of_danger":     tf_source.value,
                "existing_controls":    tf_existing_controls.value,
                "probability":          dd_prob.value or "1",
                "severity":             dd_sev.value or "1",
                "residual_probability": dd_res_prob.value or "1",
                "residual_severity":    dd_res_sev.value or "1",
                "status":               dd_status_eval.value or "ouvert",
                "owner":                tf_owner.value,
                "review_date":          tf_review_date.value,
            }
            try:
                if state["editing_id"] is not None:
                    update_risk(int(state["editing_id"]), data)
                else:
                    create_risk(data)
                state["editing_id"] = None
                if page:
                    page.show_dialog(ft.SnackBar(
                        content=ft.Text("Risque enregistré.", color="#FFFFFF"),
                        bgcolor=SUCCESS,
                    ))
                _switch_tab("registre")
            except Exception as exc:
                feedback.value = f"Erreur: {exc}"
                feedback.color = DANGER
                try:
                    feedback.update()
                except RuntimeError:
                    pass

        def _cancel(e: Any = None) -> None:
            state["editing_id"] = None
            _switch_tab("registre")

        left_col = ft.Column(
            controls=[
                tf_titre,
                tf_activite,
                tf_zone,
                dd_hazard_type,
                tf_exposed,
                tf_source,
                tf_existing_controls,
            ],
            spacing=12,
            expand=True,
        )

        right_col = ft.Column(
            controls=[
                dd_prob,
                dd_sev,
                score_container,
                ft.Text(
                    "Risque résiduel (après mesures):",
                    color=_DK_MUTED,
                    size=12,
                    weight=ft.FontWeight.W_500,
                ),
                dd_res_prob,
                dd_res_sev,
                res_score_container,
            ],
            spacing=12,
            expand=True,
        )

        form_row = ft.Row(
            controls=[left_col, ft.VerticalDivider(color=_DK_BORDER, width=1), right_col],
            spacing=20,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        bottom_row = ft.Row(
            controls=[
                dd_status_eval,
                tf_owner,
                tf_review_date,
            ],
            spacing=12,
            wrap=True,
        )

        action_row = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "Enregistrer le risque",
                    icon=ft.Icons.SAVE_OUTLINED,
                    bgcolor=PRIMARY,
                    color="#FFFFFF",
                    on_click=_save,
                ),
                ft.OutlinedButton(
                    "Annuler",
                    icon=ft.Icons.CLOSE,
                    style=ft.ButtonStyle(
                        color={ft.ControlState.DEFAULT: _DK_MUTED},
                        side=ft.BorderSide(1, _DK_BORDER),
                    ),
                    on_click=_cancel,
                ),
                feedback,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        title_text = "Modifier le risque" if editing_id is not None else "Nouvelle évaluation des risques"
        form_panel = _panel_dk(
            title_text,
            ft.Icons.EDIT_NOTE_OUTLINED,
            PRIMARY,
            ft.Column(
                controls=[form_row, ft.Divider(color=_DK_BORDER), bottom_row, action_row],
                spacing=16,
            ),
        )

        # ── Extras: liens + historique (uniquement si édition d'un risque existant) ──
        extra_panels: list[ft.Control] = []

        if editing_id is not None:
            # G+H+I — Liens inter-modules
            link_chips_col = ft.Column(spacing=4, tight=True)

            def _refresh_link_chips() -> None:
                try:
                    lnks = list_risk_links(int(editing_id))
                except Exception:
                    lnks = []
                if not lnks:
                    link_chips_col.controls = [
                        ft.Text("Aucun lien défini.", color=_DK_MUTED, size=11, italic=True)
                    ]
                else:
                    chips: list[ft.Control] = []
                    for lnk in lnks:
                        lnk_id = lnk.get("id")
                        ltype  = str(lnk.get("link_type") or "")
                        llabel = str(lnk.get("linked_label") or "")
                        type_icon = {
                            "equipement": ft.Icons.BUILD_OUTLINED,
                            "formation":  ft.Icons.SCHOOL_OUTLINED,
                            "epi":        ft.Icons.SAFETY_CHECK_OUTLINED,
                        }.get(ltype, ft.Icons.LINK_OUTLINED)
                        type_color = {
                            "equipement": WARNING,
                            "formation":  PRIMARY,
                            "epi":        SUCCESS,
                        }.get(ltype, _DK_MUTED)

                        def _del_link(e: Any, lid: int = lnk_id) -> None:
                            try:
                                delete_risk_link(int(lid))
                            except Exception:
                                pass
                            _refresh_link_chips()

                        chips.append(
                            ft.Container(
                                bgcolor=_DK_CARD2,
                                border=ft.border.all(1, _DK_BORDER),
                                border_radius=8,
                                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(type_icon, color=type_color, size=14),
                                        ft.Container(
                                            bgcolor=_DK_HEAD,
                                            border_radius=4,
                                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                            content=ft.Text(ltype.capitalize(), color=type_color, size=10),
                                        ),
                                        ft.Text(llabel, color=_DK_TEXT, size=12, expand=True),
                                        ft.IconButton(
                                            icon=ft.Icons.CLOSE,
                                            icon_color=DANGER,
                                            icon_size=14,
                                            on_click=_del_link,
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            )
                        )
                    link_chips_col.controls = chips
                try:
                    link_chips_col.update()
                except RuntimeError:
                    pass

            _refresh_link_chips()

            dd_link_type = ft.Dropdown(
                label="Type de lien",
                value="equipement",
                options=[
                    ft.dropdown.Option("equipement", "Équipement"),
                    ft.dropdown.Option("formation",  "Formation"),
                    ft.dropdown.Option("epi",        "EPI"),
                ],
                border_color=_DK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=_DK_MUTED),
                text_style=ft.TextStyle(color=_DK_TEXT),
                width=160,
            )
            tf_link_label = ft.TextField(
                label="Description / Référence *",
                border_color=_DK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=_DK_MUTED),
                expand=True,
            )
            link_feedback = ft.Text("", size=11, color=DANGER)

            def _add_link_entry(e: Any = None) -> None:
                if not tf_link_label.value or not tf_link_label.value.strip():
                    link_feedback.value = "La description est obligatoire."
                    try:
                        link_feedback.update()
                    except RuntimeError:
                        pass
                    return
                try:
                    add_risk_link(
                        int(editing_id),
                        dd_link_type.value or "equipement",
                        tf_link_label.value.strip(),
                    )
                    tf_link_label.value = ""
                    link_feedback.value = ""
                    for _ctrl in (tf_link_label, link_feedback):
                        try:
                            _ctrl.update()
                        except RuntimeError:
                            pass
                    _refresh_link_chips()
                except Exception as exc:
                    link_feedback.value = f"Erreur: {exc}"
                    try:
                        link_feedback.update()
                    except RuntimeError:
                        pass

            links_panel = _panel_dk(
                "Liens inter-modules (Équipement · Formation · EPI)",
                ft.Icons.LINK_OUTLINED,
                WARNING,
                ft.Column(
                    controls=[
                        link_chips_col,
                        ft.Divider(color=_DK_BORDER),
                        ft.Row(
                            controls=[dd_link_type, tf_link_label],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "Ajouter le lien",
                                    icon=ft.Icons.ADD_LINK,
                                    bgcolor=PRIMARY,
                                    color="#FFFFFF",
                                    on_click=_add_link_entry,
                                ),
                                link_feedback,
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=10,
                    tight=True,
                ),
            )
            extra_panels.append(links_panel)

            # D — Historique des modifications
            try:
                history_entries = get_risk_history(int(editing_id))
            except Exception:
                history_entries = []

            if history_entries:
                action_clr_map = {
                    "Création":     SUCCESS,
                    "Modification": PRIMARY,
                    "Suppression":  DANGER,
                }
                h_rows: list[ft.Control] = []
                for h in history_entries:
                    action = str(h.get("action") or "")
                    aclr   = action_clr_map.get(action, _DK_MUTED)
                    h_rows.append(
                        ft.Container(
                            bgcolor=_DK_CARD2,
                            border=ft.border.all(1, _DK_BORDER),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=10, vertical=7),
                            content=ft.Row(
                                controls=[
                                    ft.Container(width=3, height=30, bgcolor=aclr, border_radius=2),
                                    ft.Column(
                                        controls=[
                                            ft.Text(action, color=aclr, size=12, weight=ft.FontWeight.W_600),
                                            ft.Text(str(h.get("details") or ""), color=_DK_MUTED, size=11),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    ft.Text(
                                        str(h.get("changed_at") or "")[:16],
                                        color=_DK_MUTED,
                                        size=10,
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        )
                    )
                history_body: ft.Control = ft.Column(controls=h_rows, spacing=6, tight=True)
            else:
                history_body = ft.Text(
                    "Aucun historique disponible.", color=_DK_MUTED, size=12, italic=True
                )

            history_panel = _panel_dk(
                "Historique des modifications",
                ft.Icons.HISTORY_OUTLINED,
                _DK_MUTED,
                history_body,
            )
            extra_panels.append(history_panel)

        return [form_panel] + extra_panels

    # ── TAB 4: Plan de maîtrise ───────────────────────────────────────────────

    def _render_actions() -> list[ft.Control]:
        try:
            risks = list_risks()
        except Exception:
            risks = []

        right_panel_ref = ft.Ref[ft.Column]()
        right_container = ft.Column(spacing=12, tight=True, ref=right_panel_ref)

        def _render_controls_panel(risk_id: int) -> None:
            right_container.controls.clear()
            try:
                risk = get_risk(risk_id)
                controls_list = list_controls(risk_id)
            except Exception:
                risk = None
                controls_list = []

            if risk is None:
                right_container.controls.append(
                    _empty_state(
                        ft.Icons.CHECKLIST_OUTLINED,
                        "Risque introuvable",
                        "Ce risque n'existe plus dans la base.",
                    )
                )
                try:
                    right_container.update()
                except RuntimeError:
                    pass
                return

            sc = risk.get("risk_score") or 0
            clr = _risk_color(int(sc))

            risk_header = ft.Container(
                bgcolor=_DK_CARD2,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                content=ft.Row(
                    controls=[
                        ft.Container(
                            width=40,
                            height=40,
                            bgcolor=_OV.get(clr, "#0F2D5E"),
                            border=ft.border.all(2, clr),
                            border_radius=8,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text(
                                str(int(sc)),
                                color=clr,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    str(risk.get("title") or ""),
                                    color=_DK_TEXT,
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Row(
                                    controls=[
                                        _level_badge(str(risk.get("risk_level") or "faible")),
                                        _status_badge(str(risk.get("status") or "ouvert")),
                                    ],
                                    spacing=6,
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

            # ISO 45001 hierarchy
            hierarchy = [
                ("elimination",   "1. Élimination",   SUCCESS),
                ("substitution",  "2. Substitution",  PRIMARY),
                ("ingenierie",    "3. Ingénierie",     WARNING),
                ("administratif", "4. Administratif",  _CLR_ELEVE),
                ("epi",           "5. EPI",            DANGER),
            ]

            # Add control form
            dd_ctrl_type = ft.Dropdown(
                label="Type de mesure",
                value="administratif",
                options=[ft.dropdown.Option(k, v) for k, v, _ in hierarchy],
                border_color=_DK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=_DK_MUTED),
                text_style=ft.TextStyle(color=_DK_TEXT),
                width=200,
            )
            tf_ctrl_desc = ft.TextField(
                label="Description *",
                border_color=_DK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=_DK_MUTED),
                expand=True,
            )
            tf_ctrl_resp = ft.TextField(
                label="Responsable",
                border_color=_DK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=_DK_MUTED),
                width=160,
            )
            tf_ctrl_date = ft.TextField(
                label="Date cible",
                hint_text="YYYY-MM-DD",
                border_color=_DK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=_DK_MUTED),
                hint_style=ft.TextStyle(color=_DK_MUTED),
                width=140,
            )
            dd_ctrl_status = ft.Dropdown(
                label="Statut",
                value="planifie",
                options=[
                    ft.dropdown.Option("planifie",  "Planifié"),
                    ft.dropdown.Option("en_cours",  "En cours"),
                    ft.dropdown.Option("realise",   "Réalisé"),
                ],
                border_color=_DK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=_DK_MUTED),
                text_style=ft.TextStyle(color=_DK_TEXT),
                width=140,
            )
            ctrl_feedback = ft.Text("", size=11, color=DANGER)

            def _add_control(e: Any = None) -> None:
                if not tf_ctrl_desc.value or not tf_ctrl_desc.value.strip():
                    ctrl_feedback.value = "La description est obligatoire."
                    try:
                        ctrl_feedback.update()
                    except RuntimeError:
                        pass
                    return
                try:
                    create_control({
                        "risk_id":      risk_id,
                        "control_type": dd_ctrl_type.value or "administratif",
                        "description":  tf_ctrl_desc.value.strip(),
                        "responsible":  tf_ctrl_resp.value,
                        "target_date":  tf_ctrl_date.value,
                        "status":       dd_ctrl_status.value or "planifie",
                    })
                    tf_ctrl_desc.value = ""
                    tf_ctrl_resp.value = ""
                    tf_ctrl_date.value = ""
                    ctrl_feedback.value = ""
                    try:
                        tf_ctrl_desc.update()
                    except RuntimeError:
                        pass
                        tf_ctrl_resp.update()
                        tf_ctrl_date.update()
                        ctrl_feedback.update()
                    _render_controls_panel(risk_id)
                except Exception as exc:
                    ctrl_feedback.value = f"Erreur: {exc}"
                    try:
                        ctrl_feedback.update()
                    except RuntimeError:
                        pass

            add_form = ft.Container(
                bgcolor=_DK_CARD2,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=10,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Ajouter une mesure de maîtrise",
                            color=_DK_TEXT,
                            size=13,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Row(
                            controls=[dd_ctrl_type, tf_ctrl_desc],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        ft.Row(
                            controls=[tf_ctrl_resp, tf_ctrl_date, dd_ctrl_status],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "Ajouter",
                                    icon=ft.Icons.ADD,
                                    bgcolor=PRIMARY,
                                    color="#FFFFFF",
                                    on_click=_add_control,
                                ),
                                ctrl_feedback,
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=10,
                ),
            )

            # Group controls by type
            controls_by_type: dict[str, list[dict[str, Any]]] = {}
            for ctrl in controls_list:
                ctype = str(ctrl.get("control_type") or "administratif")
                controls_by_type.setdefault(ctype, []).append(ctrl)

            hierarchy_panels: list[ft.Control] = []
            for key, label, color in hierarchy:
                type_controls = controls_by_type.get(key, [])
                ctrl_rows: list[ft.Control] = []
                for ctrl in type_controls:
                    ctrl_id = ctrl.get("id")
                    cstat = str(ctrl.get("status") or "planifie")

                    def _del_ctrl(e: Any, cid: int = ctrl_id, rid: int = risk_id) -> None:
                        try:
                            delete_control(int(cid))
                        except Exception:
                            pass
                        _render_controls_panel(rid)

                    ctrl_rows.append(
                        ft.Container(
                            bgcolor=_DK_HEAD,
                            border=ft.border.all(1, _DK_BORDER),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=10, vertical=7),
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        width=3,
                                        height=24,
                                        bgcolor=color,
                                        border_radius=2,
                                    ),
                                    ft.Text(
                                        str(ctrl.get("description") or ""),
                                        color=_DK_TEXT,
                                        size=12,
                                        expand=True,
                                        max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        str(ctrl.get("responsible") or ""),
                                        color=_DK_MUTED,
                                        size=11,
                                    ),
                                    _control_status_badge(cstat),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=DANGER,
                                        icon_size=14,
                                        tooltip="Supprimer",
                                        on_click=_del_ctrl,
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        )
                    )

                if not ctrl_rows:
                    ctrl_rows = [
                        ft.Text("Aucune mesure.", color=_DK_MUTED, size=11, italic=True)
                    ]

                body = ft.Column(controls=ctrl_rows, spacing=6)
                hierarchy_panels.append(_panel_dk(label, ft.Icons.CHECKLIST_OUTLINED, color, body))

            right_container.controls = [risk_header] + hierarchy_panels + [add_form]
            try:
                right_container.update()
            except RuntimeError:
                pass

        # Risk list (left panel)
        if not risks:
            left_body = _empty_state(
                ft.Icons.TABLE_ROWS_OUTLINED,
                "Aucun risque",
                "Créez d'abord un risque dans l'onglet Évaluation.",
            )
        else:
            risk_cards: list[ft.Control] = []
            for risk in risks:
                rid = risk.get("id")
                sc  = risk.get("risk_score") or 0
                clr = _risk_color(int(sc))
                is_selected = rid == state.get("selected_risk_id")

                def _select_risk(e: Any, r: dict[str, Any] = risk) -> None:
                    state["selected_risk_id"] = r.get("id")
                    _render_content()

                risk_cards.append(
                    ft.Container(
                        bgcolor=_DK_HEAD if is_selected else _DK_CARD2,
                        border=ft.border.all(2 if is_selected else 1, PRIMARY if is_selected else _DK_BORDER),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=8),
                        on_click=_select_risk,
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    width=32,
                                    height=32,
                                    bgcolor=_OV.get(clr, "#0F2D5E"),
                                    border=ft.border.all(1, clr),
                                    border_radius=6,
                                    alignment=ft.Alignment(0, 0),
                                    content=ft.Text(
                                        str(int(sc)),
                                        color=clr,
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ),
                                ft.Text(
                                    str(risk.get("title") or ""),
                                    color=_DK_TEXT if is_selected else _DK_MUTED,
                                    size=12,
                                    expand=True,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            left_body = ft.Column(controls=risk_cards, spacing=6, scroll=ft.ScrollMode.AUTO)

        left_panel = _panel_dk(
            f"Risques ({len(risks)})",
            ft.Icons.TABLE_ROWS_OUTLINED,
            PRIMARY,
            left_body,
        )

        # Right panel
        if state.get("selected_risk_id") is not None:
            _render_controls_panel(int(state["selected_risk_id"]))
        else:
            right_container.controls = [
                _empty_state(
                    ft.Icons.CHECKLIST_OUTLINED,
                    "Sélectionnez un risque",
                    "Choisissez un risque dans la liste pour gérer ses mesures de maîtrise.",
                )
            ]

        layout = ft.Row(
            controls=[
                ft.Container(content=left_panel, width=280),
                ft.Container(
                    content=ft.Column(
                        controls=[right_container],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        return [layout]

    # ── Build tab bar ─────────────────────────────────────────────────────────
    tab_btn_controls: list[ft.Control] = []
    for key, label, icon in _TABS:
        btn = ft.ElevatedButton(
            label,
            icon=icon,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: _DK_CARD},
                color={ft.ControlState.DEFAULT: _DK_MUTED},
                shape=ft.RoundedRectangleBorder(radius=8),
                side=ft.BorderSide(1, _DK_BORDER),
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
            ),
            on_click=lambda e, k=key: _switch_tab(k),
        )
        tab_buttons[key] = btn
        tab_btn_controls.append(btn)

    tab_bar = ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            controls=tab_btn_controls,
            spacing=8,
            wrap=True,
        ),
    )

    root = ft.Column(
        controls=[
            module_header(
                "Analyse des Risques",
                "ISO 31000:2018 · ISO 45001 · Matrice de criticité 5×5",
            ),
            tab_bar,
            content_area,
        ],
        spacing=14,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    _switch_tab("dashboard")
    return ft.Container(bgcolor="#071321", expand=True, content=root)
