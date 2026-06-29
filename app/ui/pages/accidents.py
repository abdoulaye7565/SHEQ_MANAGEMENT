from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

import flet as ft

from app.services.app_logger import get_logger

_LOGGER = get_logger(__name__)

from app.services.accident_service import (
    create_accident,
    update_accident,
    delete_accident,
    get_accident,
    list_accidents,
    get_accident_summary,
    compute_kpis,
    list_causes,
    add_cause,
    delete_cause,
    list_actions,
    add_action,
    update_action,
    delete_action,
    get_accident_options,
)
from app.services import export_accident_report
from app.ui.components.pagination import PAGE_SIZE, pagination_row
from app.ui.theme import DANGER, PRIMARY, SUCCESS, WARNING

# ── Dark palette ───────────────────────────────────────────────────────────────
_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"

# ── Type / gravite colours ─────────────────────────────────────────────────────
_TYPE_COLORS: dict[str, str] = {
    "accident":             DANGER,
    "presquaccident":       WARNING,
    "situation_dangereuse": PRIMARY,
}
_TYPE_LABELS: dict[str, str] = {
    "accident":             "Accident",
    "presquaccident":       "Presqu'accident",
    "situation_dangereuse": "Situation dangereuse",
}
_GRAVITE_COLORS: dict[str, str] = {
    "fatal":  "#7C3AED",
    "grave":  DANGER,
    "majeur": "#F97316",
    "mineur": WARNING,
    "benin":  SUCCESS,
}
_GRAVITE_LABELS: dict[str, str] = {
    "fatal":  "Fatal",
    "grave":  "Grave",
    "majeur": "Majeur",
    "mineur": "Mineur",
    "benin":  "Benin",
}
_STATUT_COLORS: dict[str, str] = {
    "ouvert":   DANGER,
    "en_cours": WARNING,
    "clos":     SUCCESS,
}
_STATUT_LABELS: dict[str, str] = {
    "ouvert":   "Ouvert",
    "en_cours": "En cours",
    "clos":     "Clos",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _badge(label: str, color: str, bg: str | None = None) -> ft.Control:
    if bg is None:
        # derive a dark tint
        tint_map = {
            DANGER:   "#3B0F0F",
            WARNING:  "#2D1F00",
            SUCCESS:  "#052E16",
            PRIMARY:  "#0F2D5E",
            "#7C3AED": "#1E0B40",
            "#F97316": "#2D1600",
        }
        bg = tint_map.get(color, _DK_CARD2)
    return ft.Container(
        bgcolor=bg,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(label, color=color, size=10, weight=ft.FontWeight.BOLD),
    )


def _type_badge(type_ev: str) -> ft.Control:
    color = _TYPE_COLORS.get(type_ev, _DK_MUTED)
    label = _TYPE_LABELS.get(type_ev, type_ev)
    return _badge(label, color)


def _gravite_badge(gravite: str) -> ft.Control:
    color = _GRAVITE_COLORS.get(gravite, _DK_MUTED)
    label = _GRAVITE_LABELS.get(gravite, gravite)
    return _badge(label, color)


def _statut_badge(statut: str) -> ft.Control:
    color = _STATUT_COLORS.get(statut, _DK_MUTED)
    label = _STATUT_LABELS.get(statut, statut)
    return _badge(label, color)


def _kpi_card(label: str, value: Any, color: str, icon: str) -> ft.Control:
    tint_map = {
        DANGER:   "#3B0F0F",
        WARNING:  "#2D1F00",
        SUCCESS:  "#052E16",
        PRIMARY:  "#0F2D5E",
        "#7C3AED": "#1E0B40",
        "#F97316": "#2D1600",
    }
    bg = tint_map.get(color, _DK_CARD)
    return ft.Container(
        bgcolor=bg,
        border=ft.border.all(1, color),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=18, vertical=14),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=32, height=32,
                            bgcolor=_DK_HEAD,
                            border_radius=8,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=color, size=16),
                        ),
                        ft.Text(str(value), color=color, size=22, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(label, color=_DK_MUTED, size=11),
            ],
            spacing=6,
            tight=True,
        ),
    )


def _panel(title: str, icon: str, accent: str, body: ft.Control) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=14, bgcolor=accent, border_radius=2),
                            ft.Icon(icon, color=accent, size=16),
                            ft.Text(title, color=_DK_TEXT, size=14, weight=ft.FontWeight.BOLD),
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


def _empty_state(icon: str, title: str, subtitle: str = "") -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=24, vertical=40),
        content=ft.Column(
            controls=[
                ft.Container(
                    width=64, height=64,
                    bgcolor=_DK_HEAD,
                    border_radius=32,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color=_DK_MUTED, size=28),
                ),
                ft.Text(title, color=_DK_TEXT, size=15, weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(subtitle, color=_DK_MUTED, size=12, text_align=ft.TextAlign.CENTER)
                if subtitle else ft.Container(height=0),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
    )


def _last_12_months() -> list[str]:
    today = date.today()
    months: list[str] = []
    for i in range(11, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")
    return months


def _section_header(title: str) -> ft.Control:
    return ft.Container(
        padding=ft.padding.only(bottom=10),
        content=ft.Row(
            controls=[
                ft.Container(width=4, height=16, bgcolor=PRIMARY, border_radius=2),
                ft.Text(title, color=_DK_TEXT, size=14, weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _text_field(label: str, value: str = "", multiline: bool = False,
                min_lines: int = 1, max_lines: int = 1) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        multiline=multiline,
        min_lines=min_lines if multiline else None,
        max_lines=max_lines if multiline else None,
        border_radius=8,
        border_color=_DK_BORDER,
        focused_border_color=PRIMARY,
        bgcolor=_DK_CARD2,
        color=_DK_TEXT,
        label_style=ft.TextStyle(color=_DK_MUTED),
        cursor_color=PRIMARY,
    )


def _dropdown(label: str, options: list[tuple[str, str]], value: str | None = None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        options=[ft.dropdown.Option(k, v) for k, v in options],
        border_radius=8,
        border_color=_DK_BORDER,
        focused_border_color=PRIMARY,
        bgcolor=_DK_CARD2,
        color=_DK_TEXT,
        label_style=ft.TextStyle(color=_DK_MUTED),
    )


# ── Main page ──────────────────────────────────────────────────────────────────

def accidents_page(page: Any = None) -> ft.Control:  # noqa: ANN001
    content_area = ft.Container()
    active_tab: dict[str, str] = {"key": "dashboard"}
    tab_buttons: list[ft.ElevatedButton] = []

    # ── shared state ──
    _edit_id: dict[str, int | None] = {"v": None}
    _selected_accident: dict[str, dict[str, Any] | None] = {"v": None}
    _filter: dict[str, str | None] = {"type_ev": None, "gravite": None, "statut": None}
    _sort: dict[str, Any] = {"col": "date_evenement", "dir": "desc"}
    _page: dict[str, int] = {"v": 0}

    def _safe_update(ctrl: ft.Control) -> None:
        try:
            ctrl.update()
        except RuntimeError:
            pass

    def _switch_tab(key: str) -> None:
        active_tab["key"] = key
        builders = {
            "dashboard": _build_dashboard,
            "registre":  _build_registre,
            "analyse":   _build_analyse,
            "saisie":    _build_saisie,
        }
        content_area.content = ft.Column(
            controls=[builders[key]()],
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        _refresh_tab_styles()
        try:
            content_area.update()
        except RuntimeError:
            pass

    def _refresh_tab_styles() -> None:
        labels = {
            "dashboard": "Tableau de bord",
            "registre":  "Registre",
            "analyse":   "Analyse",
            "saisie":    "Saisie",
        }
        keys = list(labels.keys())
        for i, btn in enumerate(tab_buttons):
            k = keys[i]
            selected = k == active_tab["key"]
            btn.style = ft.ButtonStyle(
                bgcolor=PRIMARY if selected else _DK_HEAD,
                color="#FFFFFF" if selected else _DK_MUTED,
                shape=ft.RoundedRectangleBorder(radius=8),
                overlay_color=ft.Colors.with_opacity(0.08, "#FFFFFF"),
            )
            try:
                btn.update()
            except RuntimeError:
                pass

    # ── Tab 1: Dashboard ───────────────────────────────────────────────────────
    def _build_dashboard() -> ft.Control:  # noqa: PLR0912
        try:
            summary   = get_accident_summary()
            kpis      = compute_kpis()
            all_acc   = list_accidents()
        except Exception as _exc:
            _LOGGER.error("Chargement dashboard accidents échoué: %s", _exc)
            summary  = {}
            kpis     = {"tf": 0.0, "tg": 0.0, "nb_accidents": 0, "total_jours_arret": 0}
            all_acc  = []

        # ── KPI values ───────────────────────────────────────────────────────
        total       = int(summary.get("total") or 0)
        accidents_n = int(summary.get("accidents") or 0)
        presqu      = int(summary.get("presquaccidents") or 0)
        situations  = int(summary.get("situations") or 0)
        graves      = int(summary.get("graves") or 0)
        jours_arret = int(summary.get("total_jours_arret") or 0)
        ouverts     = int(summary.get("ouverts") or 0)
        tf  = float(kpis.get("tf") or 0)
        tg  = float(kpis.get("tg") or 0)
        tf_color = SUCCESS if tf < 1 else (WARNING if tf <= 5 else DANGER)

        # ── Jours sans accident avec arrêt ───────────────────────────────────
        lta_dates = sorted(
            [str(a.get("date_evenement") or "")[:10]
             for a in all_acc
             if int(a.get("jours_arret") or 0) > 0
             and str(a.get("date_evenement") or "")],
            reverse=True,
        )
        days_without: int | None = None
        if lta_dates:
            try:
                days_without = (date.today() - date.fromisoformat(lta_dates[0])).days
            except ValueError:
                pass
        dw_color = SUCCESS if days_without is None else (
            DANGER if days_without == 0 else (WARNING if days_without <= 30 else SUCCESS)
        )
        dw_value = str(days_without) if days_without is not None else "∞"

        # ── Compteur sécurité (carte hero) ───────────────────────────────────
        safety_card = ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.all(2, dw_color),
            border_radius=14,
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                width=52, height=52,
                                bgcolor=_DK_HEAD,
                                border_radius=14,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(ft.Icons.VERIFIED_OUTLINED, color=dw_color, size=30),
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(dw_value, color=dw_color, size=44,
                                            weight=ft.FontWeight.BOLD),
                                    ft.Text("Jours sans accident\navec arrêt de travail",
                                            color=_DK_MUTED, size=11),
                                ],
                                spacing=1, tight=True,
                            ),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(color=_DK_BORDER, height=1),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("TF", color=_DK_MUTED, size=10),
                                    ft.Text(f"{tf:.2f}", color=tf_color, size=20,
                                            weight=ft.FontWeight.BOLD),
                                    ft.Text("×10⁶ h", color=_DK_MUTED, size=9),
                                ],
                                spacing=2, tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Container(width=1, height=40, bgcolor=_DK_BORDER),
                            ft.Column(
                                controls=[
                                    ft.Text("TG", color=_DK_MUTED, size=10),
                                    ft.Text(f"{tg:.2f}", color=WARNING, size=20,
                                            weight=ft.FontWeight.BOLD),
                                    ft.Text("×10³ h", color=_DK_MUTED, size=9),
                                ],
                                spacing=2, tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Container(width=1, height=40, bgcolor=_DK_BORDER),
                            ft.Column(
                                controls=[
                                    ft.Text("Ouverts", color=_DK_MUTED, size=10),
                                    ft.Text(str(ouverts),
                                            color=DANGER if ouverts else SUCCESS,
                                            size=20, weight=ft.FontWeight.BOLD),
                                    ft.Text("dossiers", color=_DK_MUTED, size=9),
                                ],
                                spacing=2, tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=14, tight=True,
            ),
        )

        # ── Grille de KPIs ───────────────────────────────────────────────────
        kpi_data = [
            ("Total", total, PRIMARY, ft.Icons.SUMMARIZE_OUTLINED),
            ("Accidents", accidents_n, DANGER, ft.Icons.PERSONAL_INJURY_OUTLINED),
            ("Presqu'acc.", presqu, WARNING, ft.Icons.WARNING_AMBER_OUTLINED),
            ("Sit. dang.", situations, PRIMARY, ft.Icons.CRISIS_ALERT_OUTLINED),
            ("Graves/Fatals", graves, "#7C3AED", ft.Icons.EMERGENCY_OUTLINED),
            ("Jours arrêt", jours_arret, "#F97316", ft.Icons.CALENDAR_TODAY_OUTLINED),
        ]
        kpi_rows: list[ft.Control] = []
        for i in range(0, len(kpi_data), 3):
            chunk = kpi_data[i:i + 3]
            kpi_rows.append(
                ft.Row(
                    controls=[_kpi_card(lbl, val, col, ico) for lbl, val, col, ico in chunk],
                    spacing=10,
                )
            )
        kpi_grid = ft.Column(controls=kpi_rows, spacing=10, tight=True)

        top_row = ft.Row(
            controls=[
                ft.Container(content=safety_card, expand=2),
                ft.Container(content=kpi_grid, expand=3),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # ── Tendance mensuelle (12 mois) ─────────────────────────────────────
        months_12 = _last_12_months()
        month_counts = Counter(str(a.get("date_evenement") or "")[:7] for a in all_acc)
        chart_h = 110
        max_val = max((month_counts.get(m, 0) for m in months_12), default=0) or 1
        has_data = any(month_counts.get(m, 0) for m in months_12)
        if has_data:
            bar_cols: list[ft.Control] = []
            for m in months_12:
                val = month_counts.get(m, 0)
                bar_h = max(2, int(val / max_val * chart_h))
                spacer_h = chart_h - bar_h
                bar_cols.append(ft.Column(
                    controls=[
                        ft.Text(str(val) if val else "", color=DANGER, size=8,
                                weight=ft.FontWeight.BOLD),
                        ft.Container(height=max(0, spacer_h - 14), width=1),
                        ft.Container(
                            bgcolor=DANGER if val else _DK_BORDER,
                            border_radius=ft.border_radius.only(top_left=3, top_right=3),
                            width=22, height=bar_h,
                        ),
                        ft.Text(m[5:], color=_DK_MUTED, size=7),
                    ],
                    spacing=2, tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ))
            trend_content = ft.Container(
                height=chart_h + 50,
                content=ft.Row(
                    controls=bar_cols,
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.padding.symmetric(horizontal=6, vertical=4),
            )
        else:
            trend_content = ft.Container(
                padding=ft.padding.symmetric(vertical=16),
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BAR_CHART_OUTLINED, color=_DK_MUTED, size=28),
                        ft.Text("Aucun événement sur les 12 derniers mois.",
                                color=_DK_MUTED, size=11, italic=True),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        trend_panel = _panel(
            "Tendance mensuelle — 12 mois",
            ft.Icons.SHOW_CHART_OUTLINED,
            DANGER,
            trend_content,
        )

        # ── Distributions ────────────────────────────────────────────────────
        total_dist = len(all_acc) or 1

        def _hbar(label: str, count: int, color: str) -> ft.Control:
            pct = min(int(count / total_dist * 100), 100)
            filled = max(1, pct) if pct > 0 else 0
            empty  = max(1, 100 - pct) if pct < 100 else 0
            bar_parts: list[ft.Control] = []
            if filled:
                bar_parts.append(ft.Container(bgcolor=color, expand=filled,
                                              border_radius=ft.border_radius.only(top_left=3, bottom_left=3)))
            if empty:
                bar_parts.append(ft.Container(bgcolor=_DK_HEAD, expand=empty,
                                              border_radius=ft.border_radius.only(top_right=3, bottom_right=3)))
            return ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(label, color=_DK_TEXT, size=10, expand=True),
                            ft.Text(f"{count}  ({pct}%)", color=color, size=10,
                                    weight=ft.FontWeight.BOLD),
                        ],
                        spacing=6,
                    ),
                    ft.Container(
                        bgcolor=_DK_HEAD,
                        border_radius=3,
                        height=8,
                        content=ft.Row(controls=bar_parts, spacing=0),
                    ),
                ],
                spacing=4, tight=True,
            )

        type_col = ft.Column(
            controls=[
                _hbar("Accident", sum(1 for a in all_acc if a.get("type_evenement") == "accident"), DANGER),
                _hbar("Presqu'accident", sum(1 for a in all_acc if a.get("type_evenement") == "presquaccident"), WARNING),
                _hbar("Situation dang.", sum(1 for a in all_acc if a.get("type_evenement") == "situation_dangereuse"), PRIMARY),
            ],
            spacing=10, tight=True,
        )
        grav_col = ft.Column(
            controls=[
                _hbar("Fatal",  sum(1 for a in all_acc if a.get("gravite") == "fatal"),  "#7C3AED"),
                _hbar("Grave",  sum(1 for a in all_acc if a.get("gravite") == "grave"),  DANGER),
                _hbar("Majeur", sum(1 for a in all_acc if a.get("gravite") == "majeur"), "#F97316"),
                _hbar("Mineur", sum(1 for a in all_acc if a.get("gravite") == "mineur"), WARNING),
                _hbar("Bénin",  sum(1 for a in all_acc if a.get("gravite") == "benin"),  SUCCESS),
            ],
            spacing=10, tight=True,
        )
        dist_row = ft.Row(
            controls=[
                ft.Container(
                    content=_panel("Par type d'événement", ft.Icons.CATEGORY_OUTLINED, WARNING, type_col),
                    expand=True,
                ),
                ft.Container(
                    content=_panel("Par gravité", ft.Icons.PRIORITY_HIGH_OUTLINED, DANGER, grav_col),
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # ── Événements récents ───────────────────────────────────────────────
        recent_controls: list[ft.Control] = []
        for acc in all_acc[:8]:
            type_ev = str(acc.get("type_evenement") or "")
            gravite = str(acc.get("gravite") or "")
            emp_nom = str(acc.get("employe_nom") or "")
            emp_prenom = str(acc.get("employe_prenom") or "")
            emp_label = f"{emp_nom} {emp_prenom}".strip() or "—"
            recent_controls.append(
                ft.Container(
                    bgcolor=_DK_CARD,
                    border=ft.border.only(
                        left=ft.BorderSide(3, _TYPE_COLORS.get(type_ev, _DK_BORDER)),
                        top=ft.BorderSide(1, _DK_BORDER),
                        right=ft.BorderSide(1, _DK_BORDER),
                        bottom=ft.BorderSide(1, _DK_BORDER),
                    ),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(str(acc.get("numero") or ""),
                                            color=PRIMARY, size=12, weight=ft.FontWeight.BOLD),
                                    ft.Text(str(acc.get("date_evenement") or ""),
                                            color=_DK_MUTED, size=10),
                                ],
                                spacing=2, tight=True, width=120,
                            ),
                            _type_badge(type_ev),
                            ft.Text(
                                str(acc.get("lieu") or "—"),
                                color=_DK_TEXT, size=11,
                                expand=True, overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            _gravite_badge(gravite),
                            _statut_badge(str(acc.get("statut") or "")),
                            ft.Text(emp_label, color=_DK_MUTED, size=10, width=130,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        if not recent_controls:
            recent_controls = [_empty_state(
                ft.Icons.PERSONAL_INJURY_OUTLINED,
                "Aucun événement enregistré",
                "Utilisez l'onglet Saisie pour déclarer un incident.",
            )]

        recent_panel = _panel(
            "Événements récents",
            ft.Icons.LIST_ALT_OUTLINED,
            PRIMARY,
            ft.Column(controls=recent_controls, spacing=6, tight=True),
        )

        return ft.Column(
            controls=[
                top_row,
                ft.Container(height=4),
                trend_panel,
                ft.Container(height=4),
                dist_row,
                ft.Container(height=4),
                recent_panel,
            ],
            spacing=0, tight=True,
        )

    # ── Tab 2: Registre ────────────────────────────────────────────────────────
    def _build_registre() -> ft.Control:
        # ── Fiche view (accident selected) ──────────────────────────────────────
        if _selected_accident["v"] is not None:
            sel = _selected_accident["v"]
            acc_id = int(sel.get("id") or 0)

            def _back(e: Any) -> None:
                _selected_accident["v"] = None
                _switch_tab("registre")

            def _edit_sel(e: Any) -> None:
                _edit_id["v"] = acc_id
                _switch_tab("saisie")

            def _del_sel(e: Any) -> None:
                try:
                    delete_accident(acc_id)
                except Exception as _exc:
                    _LOGGER.error("Suppression accident #%s échouée: %s", acc_id, _exc)
                _selected_accident["v"] = None
                _switch_tab("registre")

            _export_status = ft.Text("", size=11, color=SUCCESS)

            def _export_pdf(e: Any) -> None:
                try:
                    path = export_accident_report(acc_id)
                    _export_status.value = f"PDF : {path.name}"
                    _export_status.color = SUCCESS
                    import os as _os
                    _os.startfile(str(path))
                except Exception as _exc:
                    _export_status.value = str(_exc)
                    _export_status.color = DANGER
                try:
                    action_bar.update()
                except Exception:
                    pass

            action_bar = ft.Row(
                controls=[
                    ft.OutlinedButton(
                        "Retour au registre",
                        icon=ft.Icons.ARROW_BACK_OUTLINED,
                        style=ft.ButtonStyle(
                            color=_DK_MUTED,
                            side=ft.BorderSide(1, _DK_BORDER),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=_back,
                    ),
                    ft.Container(expand=True),
                    _export_status,
                    ft.OutlinedButton(
                        "Exporter PDF",
                        icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                        style=ft.ButtonStyle(
                            color=SUCCESS,
                            side=ft.BorderSide(1, SUCCESS),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=_export_pdf,
                    ),
                    ft.OutlinedButton(
                        "Modifier",
                        icon=ft.Icons.EDIT_OUTLINED,
                        style=ft.ButtonStyle(
                            color=WARNING,
                            side=ft.BorderSide(1, WARNING),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=_edit_sel,
                    ),
                    ft.OutlinedButton(
                        "Supprimer",
                        icon=ft.Icons.DELETE_OUTLINE,
                        style=ft.ButtonStyle(
                            color=DANGER,
                            side=ft.BorderSide(1, DANGER),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=_del_sel,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            return ft.Column(
                controls=[action_bar, ft.Container(height=4), _build_accident_detail(sel)],
                spacing=0,
                tight=True,
            )

        # ── Card browser ────────────────────────────────────────────────────────
        flt_type = _dropdown(
            "Type",
            [("", "Tous"), ("accident", "Accident"),
             ("presquaccident", "Presqu'accident"),
             ("situation_dangereuse", "Situation dangereuse")],
            _filter["type_ev"] or "",
        )
        flt_grav = _dropdown(
            "Gravite",
            [("", "Toutes"), ("fatal", "Fatal"), ("grave", "Grave"),
             ("majeur", "Majeur"), ("mineur", "Mineur"), ("benin", "Benin")],
            _filter["gravite"] or "",
        )
        flt_stat = _dropdown(
            "Statut",
            [("", "Tous"), ("ouvert", "Ouvert"),
             ("en_cours", "En cours"), ("clos", "Clos")],
            _filter["statut"] or "",
        )

        cards_area = ft.Column(tight=True, spacing=0)

        def _open_fiche(acc: dict[str, Any]) -> None:
            try:
                full = get_accident(int(acc.get("id") or 0))
            except Exception as _exc:
                _LOGGER.warning("Chargement détail accident #%s: %s", acc.get("id"), _exc)
                full = None
            _selected_accident["v"] = full or acc
            _switch_tab("registre")

        def _acc_card(acc: dict[str, Any]) -> ft.Control:
            type_ev  = str(acc.get("type_evenement") or "")
            grav     = str(acc.get("gravite") or "")
            statut   = str(acc.get("statut") or "")
            grav_color = _GRAVITE_COLORS.get(grav, _DK_BORDER)
            emp_label = (
                f"{acc.get('employe_nom') or ''} {acc.get('employe_prenom') or ''}".strip()
                or "—"
            )
            jours = int(acc.get("jours_arret") or 0)
            lieu  = str(acc.get("lieu") or "—")

            chips_bottom: list[ft.Control] = [_statut_badge(statut)]
            if jours > 0:
                chips_bottom.append(
                    ft.Container(
                        bgcolor=_DK_HEAD,
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.HOTEL_OUTLINED, color=WARNING, size=10),
                                ft.Text(f"{jours}j", color=WARNING, size=10,
                                        weight=ft.FontWeight.W_600),
                            ],
                            spacing=3, tight=True,
                        ),
                    )
                )

            return ft.Container(
                col={"xs": 12, "sm": 6, "md": 4},
                bgcolor=_DK_CARD,
                border=ft.border.all(2, grav_color),
                border_radius=12,
                padding=14,
                on_click=lambda e, a=acc: _open_fiche(a),
                ink=True,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                _type_badge(type_ev),
                                ft.Container(expand=True),
                                _gravite_badge(grav),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(str(acc.get("numero") or ""), color=PRIMARY, size=14,
                                weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=_DK_MUTED, size=12),
                                ft.Text(str(acc.get("date_evenement") or "")[:10],
                                        color=_DK_MUTED, size=11),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, color=_DK_MUTED, size=12),
                                ft.Text(lieu, color=_DK_TEXT, size=11, expand=True,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.PERSON_OUTLINED, color=_DK_MUTED, size=12),
                                ft.Text(emp_label, color=_DK_MUTED, size=11, expand=True,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(controls=chips_bottom, spacing=6, wrap=True),
                    ],
                    spacing=6,
                    tight=True,
                ),
            )

        def _reload_cards(reset_page: bool = True) -> None:
            if reset_page:
                _page["v"] = 0
            type_ev = flt_type.value or None
            grav    = flt_grav.value or None
            stat    = flt_stat.value or None
            _filter["type_ev"] = type_ev
            _filter["gravite"] = grav
            _filter["statut"]  = stat
            try:
                rows = list_accidents(type_ev=type_ev, gravite=grav, statut=stat)
            except Exception as _exc:
                _LOGGER.error("Filtre accidents échoué: %s", _exc)
                rows = []

            col_key = _sort["col"]
            rev = _sort["dir"] == "desc"
            rows.sort(key=lambda r: str(r.get(col_key) or ""), reverse=rev)

            if not rows:
                cards_area.controls = [_empty_state(
                    ft.Icons.SEARCH_OFF_OUTLINED,
                    "Aucun evenement trouve",
                    "Modifiez les filtres ou saisissez un nouvel evenement.",
                )]
                _safe_update(cards_area)
                return

            total = len(rows)
            max_page = max(0, (total - 1) // PAGE_SIZE)
            _page["v"] = max(0, min(max_page, _page["v"]))
            start = _page["v"] * PAGE_SIZE
            page_rows = rows[start : start + PAGE_SIZE]

            cards_area.controls = [
                ft.ResponsiveRow(
                    controls=[_acc_card(a) for a in page_rows],
                    spacing=12,
                    run_spacing=12,
                ),
                pagination_row(
                    current_page=_page["v"],
                    max_page=max_page,
                    total=total,
                    shown_start=start + 1 if page_rows else 0,
                    shown_end=start + len(page_rows),
                    item_label="evenement(s)",
                    on_prev=lambda: (_page.__setitem__("v", _page["v"] - 1), _reload_cards(reset_page=False)),
                    on_next=lambda: (_page.__setitem__("v", _page["v"] + 1), _reload_cards(reset_page=False)),
                    on_page=lambda p: (_page.__setitem__("v", p), _reload_cards(reset_page=False)),
                ),
            ]
            _safe_update(cards_area)

        flt_type.on_change = lambda e: _reload_cards()
        flt_grav.on_change = lambda e: _reload_cards()
        flt_stat.on_change = lambda e: _reload_cards()

        def _new_accident() -> None:
            _edit_id["v"] = None
            _switch_tab("saisie")

        filter_row = ft.Row(
            controls=[
                ft.Container(content=flt_type, width=200),
                ft.Container(content=flt_grav, width=180),
                ft.Container(content=flt_stat, width=160),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Nouveau",
                    icon=ft.Icons.ADD_OUTLINED,
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color="#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: _new_accident(),
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        _reload_cards()

        return ft.Column(
            controls=[filter_row, ft.Container(height=12), cards_area],
            spacing=0,
            tight=True,
        )

    # ── Tab 3: Analyse ─────────────────────────────────────────────────────────
    def _build_analyse() -> ft.Control:  # noqa: PLR0914
        try:
            all_acc = list_accidents()
            summary = get_accident_summary()
            kpis    = compute_kpis()
        except Exception:
            all_acc = []
            summary = {}
            kpis    = {}

        total   = int(summary.get("total") or 0)
        ouverts = int(summary.get("ouverts") or 0)
        tf      = float(kpis.get("tf") or 0)
        tg      = float(kpis.get("tg") or 0)

        kpi_row = ft.Row(
            controls=[
                _kpi_card("Total evenements", total, PRIMARY, ft.Icons.LIST_ALT_OUTLINED),
                _kpi_card("Ouverts", ouverts,
                          DANGER if ouverts > 0 else SUCCESS,
                          ft.Icons.LOCK_OPEN_OUTLINED),
                _kpi_card("TF ×10⁶ h", f"{tf:.2f}",
                          SUCCESS if tf < 1 else (WARNING if tf <= 5 else DANGER),
                          ft.Icons.SPEED_OUTLINED),
                _kpi_card("TG ×10³ h", f"{tg:.2f}", WARNING, ft.Icons.TIMER_OUTLINED),
            ],
            spacing=10,
            wrap=True,
        )

        # ── Horizontal mini-bar helper ────────────────────────────────────────
        def _mini_bar(label: str, count: int, max_v: int, color: str) -> ft.Control:
            pct = count / max_v if max_v else 0
            return ft.Row(
                controls=[
                    ft.Text(label, color=_DK_MUTED, size=11, width=110,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Container(
                        width=200, height=14, bgcolor=_DK_HEAD, border_radius=4,
                        content=ft.Container(
                            width=max(2, int(200 * pct)) if count else 0,
                            height=14, bgcolor=color, border_radius=4,
                        ),
                        alignment=ft.Alignment(-1, 0),
                    ),
                    ft.Text(str(count), color=color, size=11, width=28,
                            weight=ft.FontWeight.W_600, text_align=ft.TextAlign.RIGHT),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        # ── Employee involvement ──────────────────────────────────────────────
        emp_acc: Counter[str] = Counter()
        emp_jours: Counter[str] = Counter()
        zone_counts: Counter[str] = Counter()

        for a in all_acc:
            emp = (
                f"{a.get('employe_nom') or ''} {a.get('employe_prenom') or ''}".strip()
            )
            if emp:
                emp_acc[emp] += 1
                emp_jours[emp] += int(a.get("jours_arret") or 0)
            z = str(a.get("zone") or a.get("lieu") or "").strip()
            if z:
                zone_counts[z] += 1

        top_emp_acc = emp_acc.most_common(8)
        top_emp_j   = emp_jours.most_common(8)
        top_zones   = zone_counts.most_common(8)

        max_emp_acc = top_emp_acc[0][1] if top_emp_acc else 1
        max_emp_j   = top_emp_j[0][1]   if top_emp_j   else 1
        max_zones   = top_zones[0][1]    if top_zones   else 1

        emp_acc_bars = (
            [_mini_bar(n[:18], c, max_emp_acc, DANGER) for n, c in top_emp_acc]
            if top_emp_acc
            else [ft.Text("Aucun employe implique", color=_DK_MUTED, size=12)]
        )
        emp_j_bars = (
            [_mini_bar(n[:18], c, max_emp_j, WARNING) for n, c in top_emp_j if c > 0]
            if any(c > 0 for _, c in top_emp_j)
            else [ft.Text("Aucun jour d'arret", color=_DK_MUTED, size=12)]
        )
        zone_bars = (
            [_mini_bar(z[:18], c, max_zones, PRIMARY) for z, c in top_zones]
            if top_zones
            else [ft.Text("Aucune zone renseignee", color=_DK_MUTED, size=12)]
        )

        emp_acc_panel = _panel(
            "Employes impliques (nb. evenements)",
            ft.Icons.PERSON_OUTLINED,
            DANGER,
            ft.Column(controls=emp_acc_bars, spacing=8, tight=True),
        )
        emp_j_panel = _panel(
            "Employes — jours d'arret cumules",
            ft.Icons.HOTEL_OUTLINED,
            WARNING,
            ft.Column(controls=emp_j_bars, spacing=8, tight=True),
        )
        zone_panel = _panel(
            "Zones / lieux les plus touches",
            ft.Icons.LOCATION_ON_OUTLINED,
            PRIMARY,
            ft.Column(controls=zone_bars, spacing=8, tight=True),
        )

        return ft.Column(
            controls=[
                kpi_row,
                ft.Container(height=4),
                ft.Row(
                    controls=[
                        ft.Container(content=emp_acc_panel, expand=True),
                        ft.Container(content=emp_j_panel,   expand=True),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                zone_panel,
            ],
            spacing=12,
            tight=True,
        )

    def _build_accident_detail(acc: dict[str, Any]) -> ft.Control:
        acc_id = int(acc.get("id") or 0)
        emp_nom = str(acc.get("employe_nom") or "")
        emp_prenom = str(acc.get("employe_prenom") or "")
        emp_label = f"{emp_nom} {emp_prenom}".strip() or "—"

        header_card = ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.all(1, _DK_BORDER),
            border_radius=12,
            padding=16,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(str(acc.get("numero") or ""), color=PRIMARY, size=16,
                                    weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            _type_badge(str(acc.get("type_evenement") or "")),
                            _gravite_badge(str(acc.get("gravite") or "")),
                            _statut_badge(str(acc.get("statut") or "")),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=_DK_MUTED, size=14),
                            ft.Text(str(acc.get("date_evenement") or ""), color=_DK_MUTED, size=12),
                            ft.Text(" | ", color=_DK_BORDER, size=12),
                            ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, color=_DK_MUTED, size=14),
                            ft.Text(str(acc.get("lieu") or "—"), color=_DK_MUTED, size=12),
                            ft.Text(" | ", color=_DK_BORDER, size=12),
                            ft.Icon(ft.Icons.PERSON_OUTLINED, color=_DK_MUTED, size=14),
                            ft.Text(emp_label, color=_DK_MUTED, size=12),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                    ),
                    ft.Container(
                        bgcolor=_DK_HEAD,
                        border_radius=8,
                        padding=10,
                        content=ft.Text(str(acc.get("description") or ""),
                                        color=_DK_TEXT, size=12),
                    ),
                    # Status update row
                    ft.Row(
                        controls=[
                            ft.Text("Changer statut:", color=_DK_MUTED, size=12),
                            *[
                                ft.OutlinedButton(
                                    lbl,
                                    style=ft.ButtonStyle(
                                        color=_STATUT_COLORS.get(k, _DK_MUTED),
                                        side=ft.BorderSide(1, _STATUT_COLORS.get(k, _DK_BORDER)),
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                    ),
                                    on_click=lambda e, s=k: _change_statut(acc_id, s),
                                )
                                for k, lbl in _STATUT_LABELS.items()
                            ],
                        ],
                        spacing=8,
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
                tight=True,
            ),
        )

        # Causes panel
        try:
            causes = list_causes(acc_id)
        except Exception:
            causes = []

        cause_categories = [
            ("immediate",   "Causes immediates",  DANGER),
            ("racine",      "Causes racines",      WARNING),
            ("systemique",  "Causes systemiques",  PRIMARY),
        ]

        causes_area = ft.Column(tight=True, spacing=8)

        def _rebuild_causes() -> None:
            try:
                clist = list_causes(acc_id)
            except Exception:
                clist = []
            causes_area.controls = _render_causes(clist)
            _safe_update(causes_area)

        def _render_causes(clist: list[dict[str, Any]]) -> list[ft.Control]:
            ctrls = []
            for cat_key, cat_label, cat_color in cause_categories:
                cat_causes = [c for c in clist if c.get("type_cause") == cat_key]
                new_desc = ft.TextField(
                    hint_text=f"Nouvelle cause {cat_label.lower()}...",
                    border_radius=8,
                    border_color=_DK_BORDER,
                    focused_border_color=cat_color,
                    bgcolor=_DK_CARD2,
                    color=_DK_TEXT,
                    label_style=ft.TextStyle(color=_DK_MUTED),
                    cursor_color=cat_color,
                    expand=True,
                )

                def _add_cause_cb(e: Any, ck: str = cat_key, nd: ft.TextField = new_desc) -> None:
                    if nd.value and nd.value.strip():
                        try:
                            add_cause(acc_id, ck, nd.value.strip())
                        except Exception:
                            pass
                        nd.value = ""
                        _rebuild_causes()

                cause_items: list[ft.Control] = []
                for c in cat_causes:
                    cid = int(c.get("id") or 0)

                    def _del_cause(e: Any, cid_: int = cid) -> None:
                        try:
                            delete_cause(cid_)
                        except Exception:
                            pass
                        _rebuild_causes()

                    cause_items.append(
                        ft.Container(
                            bgcolor=_DK_CARD2,
                            border=ft.border.all(1, _DK_BORDER),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                            content=ft.Row(
                                controls=[
                                    ft.Container(width=3, height=12, bgcolor=cat_color, border_radius=2),
                                    ft.Text(str(c.get("description") or ""),
                                            color=_DK_TEXT, size=12, expand=True),
                                    ft.IconButton(
                                        ft.Icons.DELETE_OUTLINE,
                                        icon_color=DANGER,
                                        icon_size=14,
                                        on_click=_del_cause,
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        )
                    )

                ctrls.append(
                    ft.Container(
                        bgcolor=_DK_CARD,
                        border=ft.border.all(1, cat_color),
                        border_radius=10,
                        padding=12,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(width=3, height=14, bgcolor=cat_color, border_radius=2),
                                        ft.Text(cat_label, color=cat_color, size=13,
                                                weight=ft.FontWeight.BOLD),
                                    ],
                                    spacing=6,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                *cause_items,
                                ft.Row(
                                    controls=[
                                        new_desc,
                                        ft.IconButton(
                                            ft.Icons.ADD_CIRCLE_OUTLINED,
                                            icon_color=cat_color,
                                            icon_size=20,
                                            tooltip="Ajouter",
                                            on_click=_add_cause_cb,
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=8,
                            tight=True,
                        ),
                    )
                )
            return ctrls

        causes_area.controls = _render_causes(causes)

        causes_panel = _panel(
            "Analyse des causes (5 Pourquoi / Arbre des causes)",
            ft.Icons.ACCOUNT_TREE_OUTLINED,
            WARNING,
            causes_area,
        )

        # Actions panel
        try:
            actions = list_actions(acc_id)
        except Exception:
            actions = []

        actions_area = ft.Column(tight=True, spacing=8)

        act_desc = _text_field("Description de l'action *")
        act_resp = _text_field("Responsable")
        act_date = _text_field("Date echeance (AAAA-MM-JJ)")
        act_stat = _dropdown(
            "Statut",
            [("planifie", "Planifie"), ("en_cours", "En cours"), ("realise", "Realise")],
            "planifie",
        )

        def _rebuild_actions() -> None:
            try:
                alist = list_actions(acc_id)
            except Exception:
                alist = []
            actions_area.controls = _render_actions(alist)
            _safe_update(actions_area)

        def _render_actions(alist: list[dict[str, Any]]) -> list[ft.Control]:
            action_stat_colors = {
                "planifie":  WARNING,
                "en_cours":  PRIMARY,
                "realise":   SUCCESS,
            }
            action_stat_labels = {
                "planifie":  "Planifie",
                "en_cours":  "En cours",
                "realise":   "Realise",
            }
            items: list[ft.Control] = []
            for act in alist:
                aid = int(act.get("id") or 0)
                stat = str(act.get("statut") or "planifie")
                stat_color = action_stat_colors.get(stat, _DK_MUTED)

                def _del_act(e: Any, aid_: int = aid) -> None:
                    try:
                        delete_action(aid_)
                    except Exception:
                        pass
                    _rebuild_actions()

                def _toggle_act(e: Any, aid_: int = aid, curr: str = stat) -> None:
                    new_stat = "realise" if curr != "realise" else "planifie"
                    try:
                        update_action(aid_, new_stat)
                    except Exception:
                        pass
                    _rebuild_actions()

                items.append(
                    ft.Container(
                        bgcolor=_DK_CARD2,
                        border=ft.border.all(1, stat_color),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        content=ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(str(act.get("description") or ""),
                                                color=_DK_TEXT, size=12),
                                        ft.Row(
                                            controls=[
                                                ft.Icon(ft.Icons.PERSON_OUTLINED,
                                                        color=_DK_MUTED, size=12),
                                                ft.Text(str(act.get("responsable") or "—"),
                                                        color=_DK_MUTED, size=11),
                                                ft.Text(" | ", color=_DK_BORDER, size=11),
                                                ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED,
                                                        color=_DK_MUTED, size=12),
                                                ft.Text(str(act.get("date_echeance") or "—"),
                                                        color=_DK_MUTED, size=11),
                                            ],
                                            spacing=4,
                                            tight=True,
                                        ),
                                    ],
                                    spacing=4,
                                    tight=True,
                                    expand=True,
                                ),
                                _badge(
                                    action_stat_labels.get(stat, stat),
                                    stat_color,
                                ),
                                ft.IconButton(
                                    ft.Icons.CHECK_CIRCLE_OUTLINED if stat != "realise"
                                    else ft.Icons.UNDO_OUTLINED,
                                    icon_color=SUCCESS if stat != "realise" else WARNING,
                                    icon_size=16,
                                    tooltip="Marquer realise" if stat != "realise" else "Rouvrir",
                                    on_click=_toggle_act,
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color=DANGER,
                                    icon_size=16,
                                    on_click=_del_act,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            return items

        actions_area.controls = _render_actions(actions)

        def _add_action_cb(e: Any) -> None:
            if not act_desc.value or not act_desc.value.strip():
                return
            try:
                add_action(acc_id, {
                    "description":  act_desc.value.strip(),
                    "responsable":  act_resp.value or None,
                    "date_echeance": act_date.value or None,
                    "statut":       act_stat.value or "planifie",
                })
            except Exception:
                pass
            act_desc.value = ""
            act_resp.value = ""
            act_date.value = ""
            act_stat.value = "planifie"
            _rebuild_actions()
            try:
                act_desc.update()
                act_resp.update()
                act_date.update()
                act_stat.update()
            except RuntimeError:
                pass

        add_form = ft.Container(
            bgcolor=_DK_HEAD,
            border=ft.border.all(1, _DK_BORDER),
            border_radius=10,
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Text("Nouvelle action corrective", color=_DK_MUTED, size=12,
                            weight=ft.FontWeight.BOLD),
                    ft.Row(controls=[act_desc], spacing=0),
                    ft.Row(
                        controls=[
                            ft.Container(content=act_resp, expand=True),
                            ft.Container(content=act_date, expand=True),
                            ft.Container(content=act_stat, width=160),
                        ],
                        spacing=10,
                    ),
                    ft.ElevatedButton(
                        "Ajouter l'action",
                        icon=ft.Icons.ADD_OUTLINED,
                        style=ft.ButtonStyle(
                            bgcolor=SUCCESS,
                            color="#FFFFFF",
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=_add_action_cb,
                    ),
                ],
                spacing=10,
                tight=True,
            ),
        )

        actions_panel = _panel(
            "Actions correctives & preventives",
            ft.Icons.TASK_ALT_OUTLINED,
            SUCCESS,
            ft.Column(
                controls=[actions_area, add_form],
                spacing=12,
                tight=True,
            ),
        )

        return ft.Column(
            controls=[header_card, causes_panel, actions_panel],
            spacing=12,
            tight=True,
        )

    def _change_statut(acc_id: int, statut: str) -> None:
        try:
            acc = get_accident(acc_id)
            if acc:
                data = dict(acc)
                data["statut"] = statut
                update_accident(acc_id, data)
                _selected_accident["v"] = get_accident(acc_id)
        except Exception:
            pass
        _switch_tab("registre")

    # ── Tab 4: Saisie ──────────────────────────────────────────────────────────
    def _build_saisie() -> ft.Control:
        edit_id = _edit_id["v"]
        existing: dict[str, Any] = {}
        if edit_id is not None:
            try:
                existing = get_accident(edit_id) or {}
            except Exception:
                existing = {}

        try:
            opts = get_accident_options()
        except Exception:
            opts = {"employees": []}
        employees = opts.get("employees", [])

        fld_type = _dropdown(
            "Type d'evenement *",
            [("accident", "Accident"),
             ("presquaccident", "Presqu'accident"),
             ("situation_dangereuse", "Situation dangereuse")],
            str(existing.get("type_evenement") or "presquaccident"),
        )
        fld_date = _text_field(
            "Date (AAAA-MM-JJ) *",
            str(existing.get("date_evenement") or date.today().isoformat()),
        )
        fld_heure = _text_field(
            "Heure (HH:MM)",
            str(existing.get("heure_evenement") or ""),
        )
        fld_lieu = _text_field("Lieu", str(existing.get("lieu") or ""))
        fld_zone = _text_field("Zone", str(existing.get("zone") or ""))
        fld_desc = _text_field(
            "Description *",
            str(existing.get("description") or ""),
            multiline=True,
            min_lines=3,
            max_lines=6,
        )
        fld_tiers = _text_field("Tiers implique", str(existing.get("tiers_implique") or ""))
        fld_jours = _text_field("Jours d'arret", str(existing.get("jours_arret") or "0"))
        fld_emp = _dropdown(
            "Employe implique",
            [("", "— Aucun —")] + [(e["value"], e["label"]) for e in employees],
            str(existing.get("employe_id") or "") if existing.get("employe_id") else "",
        )
        fld_grav = _dropdown(
            "Gravite *",
            [("benin", "Benin"), ("mineur", "Mineur"),
             ("majeur", "Majeur"), ("grave", "Grave"), ("fatal", "Fatal")],
            str(existing.get("gravite") or "benin"),
        )
        fld_stat = _dropdown(
            "Statut",
            [("ouvert", "Ouvert"), ("en_cours", "En cours"), ("clos", "Clos")],
            str(existing.get("statut") or "ouvert"),
        )

        status_msg = ft.Text("", color=SUCCESS, size=12)

        def _save(e: Any) -> None:
            desc = (fld_desc.value or "").strip()
            if not desc:
                status_msg.value = "La description est obligatoire."
                status_msg.color = DANGER
                try:
                    status_msg.update()
                except RuntimeError:
                    pass
                return
            data: dict[str, Any] = {
                "type_evenement":  fld_type.value or "presquaccident",
                "date_evenement":  (fld_date.value or "").strip() or date.today().isoformat(),
                "heure_evenement": (fld_heure.value or "").strip() or None,
                "lieu":            (fld_lieu.value or "").strip() or None,
                "zone":            (fld_zone.value or "").strip() or None,
                "description":     desc,
                "employe_id":      fld_emp.value or None,
                "tiers_implique":  (fld_tiers.value or "").strip() or None,
                "gravite":         fld_grav.value or "benin",
                "jours_arret":     int(fld_jours.value or 0) if (fld_jours.value or "").isdigit() else 0,
                "statut":          fld_stat.value or "ouvert",
            }
            try:
                if edit_id is not None:
                    update_accident(edit_id, data)
                    status_msg.value = "Evenement mis a jour avec succes."
                else:
                    create_accident(data)
                    status_msg.value = "Evenement enregistre avec succes."
                status_msg.color = SUCCESS
                _edit_id["v"] = None
            except Exception as exc:
                status_msg.value = f"Erreur: {exc}"
                status_msg.color = DANGER
            try:
                status_msg.update()
            except RuntimeError:
                pass

        def _cancel(e: Any) -> None:
            _edit_id["v"] = None
            _switch_tab("registre")

        title_text = (
            "Modifier l'evenement" if edit_id is not None
            else "Declarer un accident / incident"
        )

        form_card = ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.all(1, _DK_BORDER),
            border_radius=14,
            padding=24,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                width=36, height=36,
                                bgcolor=_DK_HEAD,
                                border_radius=9,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(ft.Icons.PERSONAL_INJURY_OUTLINED,
                                                color=PRIMARY, size=18),
                            ),
                            ft.Text(title_text, color=_DK_TEXT, size=16,
                                    weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(color=_DK_BORDER, height=1),
                    _section_header("Identification de l'evenement"),
                    ft.Row(
                        controls=[
                            ft.Container(content=fld_type, expand=2),
                            ft.Container(content=fld_date, expand=1),
                            ft.Container(content=fld_heure, expand=1),
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(content=fld_lieu, expand=True),
                            ft.Container(content=fld_zone, expand=True),
                        ],
                        spacing=12,
                    ),
                    _section_header("Details"),
                    fld_desc,
                    ft.Row(
                        controls=[
                            ft.Container(content=fld_emp, expand=True),
                            ft.Container(content=fld_tiers, expand=True),
                        ],
                        spacing=12,
                    ),
                    _section_header("Classification"),
                    ft.Row(
                        controls=[
                            ft.Container(content=fld_grav, expand=True),
                            ft.Container(content=fld_jours, width=150),
                            ft.Container(content=fld_stat, expand=True),
                        ],
                        spacing=12,
                    ),
                    ft.Container(height=4),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "Enregistrer",
                                icon=ft.Icons.SAVE_OUTLINED,
                                style=ft.ButtonStyle(
                                    bgcolor=PRIMARY,
                                    color="#FFFFFF",
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=_save,
                            ),
                            ft.OutlinedButton(
                                "Annuler",
                                icon=ft.Icons.CLOSE_OUTLINED,
                                style=ft.ButtonStyle(
                                    color=_DK_MUTED,
                                    side=ft.BorderSide(1, _DK_BORDER),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=_cancel,
                            ),
                            status_msg,
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=14,
                tight=True,
            ),
        )

        return form_card

    # ── Tab bar ────────────────────────────────────────────────────────────────
    tab_defs = [
        ("dashboard", "Tableau de bord", ft.Icons.DASHBOARD_OUTLINED),
        ("registre",  "Registre",        ft.Icons.LIST_ALT_OUTLINED),
        ("analyse",   "Analyse",         ft.Icons.ACCOUNT_TREE_OUTLINED),
        ("saisie",    "Saisie",          ft.Icons.ADD_CIRCLE_OUTLINED),
    ]

    for key, label, icon in tab_defs:
        k = key

        def _on_tab_click(e: Any, k_: str = k) -> None:
            if k_ != "saisie":
                _edit_id["v"] = None
            if k_ == "registre":
                _selected_accident["v"] = None
            _switch_tab(k_)

        btn = ft.ElevatedButton(
            label,
            icon=icon,
            style=ft.ButtonStyle(
                bgcolor=_DK_HEAD,
                color=_DK_MUTED,
                shape=ft.RoundedRectangleBorder(radius=8),
                overlay_color=ft.Colors.with_opacity(0.08, "#FFFFFF"),
            ),
            on_click=_on_tab_click,
        )
        tab_buttons.append(btn)

    tab_bar = ft.Container(
        bgcolor=_DK_CARD2,
        border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        content=ft.Row(
            controls=tab_buttons,
            spacing=8,
        ),
    )

    _switch_tab("dashboard")

    return ft.Column(
        controls=[
            tab_bar,
            ft.Container(
                content=content_area,
                padding=ft.padding.symmetric(horizontal=0, vertical=12),
                expand=True,
            ),
        ],
        spacing=0,
        tight=True,
        expand=True,
    )
