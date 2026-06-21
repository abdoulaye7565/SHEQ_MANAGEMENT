from __future__ import annotations
from collections import Counter
from datetime import date, timedelta
from typing import Any

import flet as ft

_BG     = "#071321"
_CARD   = "#0D2040"
_CARD2  = "#0A1929"
_BORDER = "#1E3A5F"
_FIELD  = "#0C1C2E"
_TEXT   = "#E2E8F0"
_MUTED  = "#9DB0C5"
PRIMARY = "#3B82F6"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER  = "#EF4444"
VIOLET  = "#7C3AED"
ORANGE  = "#F97316"


def statistics_page(page: Any = None) -> ft.Control:
    content_area = ft.Container()
    nav_buttons: dict[str, ft.ElevatedButton] = {}
    active_tab = {"key": "accidents"}

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def _safe(fn, default=None):
        try:
            return fn()
        except Exception:
            return default if default is not None else []

    def _panel(title: str, icon: str, color: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            bgcolor=_CARD,
            border=ft.border.all(1, _BORDER),
            border_radius=8,
            padding=14,
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(icon, color=color, size=16),
                            ft.Text(title, color=_TEXT, size=13, weight=ft.FontWeight.BOLD)], spacing=8),
                    ft.Divider(color=_BORDER, height=1),
                    *controls,
                ],
                spacing=10,
                tight=True,
            ),
        )

    def _kpi_chip(label: str, value: Any, color: str) -> ft.Control:
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 2},
            bgcolor=_CARD, border=ft.border.all(1, _BORDER), border_radius=8, padding=10,
            content=ft.Column(
                controls=[
                    ft.Text(str(value), color=color, size=22, weight=ft.FontWeight.BOLD),
                    ft.Text(label, color=_MUTED, size=9),
                ],
                spacing=2, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _vert_bar_chart(
        labels: list[str], counts: dict[str, int], color: str, chart_h: int = 140
    ) -> ft.Control:
        total_data = sum(counts.values())
        if not total_data:
            return ft.Container(
                bgcolor=_CARD2,
                border=ft.border.all(1, _BORDER),
                border_radius=6,
                padding=16,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BAR_CHART_OUTLINED, color=_MUTED, size=28),
                        ft.Text("Aucune donnée sur la période sélectionnée.", color=_MUTED, size=11, italic=True),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        max_val = max(counts.values()) or 1
        cols: list[ft.Control] = []
        for lbl in labels:
            val = counts.get(lbl, 0)
            bar_h = max(2, int(val / max_val * chart_h))
            spacer_h = chart_h - bar_h
            cols.append(
                ft.Column(
                    controls=[
                        ft.Text(
                            str(val) if val > 0 else "",
                            color=color, size=8, weight=ft.FontWeight.BOLD,
                        ),
                        ft.Container(height=max(0, spacer_h - 14), width=1),
                        ft.Container(
                            bgcolor=color if val > 0 else _BORDER,
                            border_radius=ft.border_radius.only(top_left=3, top_right=3),
                            width=20,
                            height=bar_h,
                        ),
                        ft.Text(lbl[-5:], color=_MUTED, size=7),
                    ],
                    spacing=2,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        return ft.Container(
            bgcolor=_CARD2,
            border=ft.border.all(1, _BORDER),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            height=chart_h + 60,
            content=ft.Row(
                controls=cols,
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.END,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    def _color_dot(color: str, label: str, value: int, total: int) -> ft.Control:
        pct = int(value / total * 100) if total else 0
        return ft.Row(controls=[
            ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
            ft.Text(f"{label}  {value}  ({pct}%)", color=_TEXT, size=10),
        ], spacing=6)

    def _horiz_bar(label: str, count: int, total: int, color: str) -> ft.Control:
        pct = max(0, min(100, int(count / total * 100))) if total else 0
        return ft.Container(
            bgcolor=_CARD2, border=ft.border.all(1, _BORDER), border_radius=6, padding=8,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(label, color=_TEXT, size=10, expand=True),
                            ft.Text(f"{count}  ({pct}%)", color=color, size=10, weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    ft.Stack(
                        controls=[
                            ft.Container(bgcolor=_BORDER, border_radius=3, height=6, width=300),
                            ft.Container(bgcolor=color, border_radius=3, height=6, width=max(4, 300 * pct // 100)),
                        ],
                        height=6,
                    ),
                ],
                spacing=4, tight=True,
            ),
        )

    def _switch_tab(key: str) -> None:
        active_tab["key"] = key
        for k, btn in nav_buttons.items():
            selected = k == key
            btn.style = ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: "#FFFFFF" if selected else _MUTED},
                bgcolor={ft.ControlState.DEFAULT: PRIMARY if selected else _FIELD},
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        _render_tab(key)
        _update()

    def _last_12_months() -> list[str]:
        today = date.today()
        labels = []
        for i in range(11, -1, -1):
            d = (today.replace(day=1) - timedelta(days=30 * i))
            labels.append(d.strftime("%Y-%m"))
        return labels

    def _render_tab(key: str) -> None:
        if key == "accidents":
            _render_accidents()
        elif key == "epi_risques":
            _render_epi_risques()
        elif key == "permis":
            _render_permis()

    # ── Tab 1 — Accidents ─────────────────────────────────────────────────
    def _render_accidents() -> None:
        from app.services.accident_service import list_accidents, get_accident_summary, compute_kpis
        accidents  = _safe(list_accidents, [])
        summary    = _safe(get_accident_summary, {})
        kpis       = _safe(compute_kpis, {})

        kpi_row = ft.ResponsiveRow(controls=[
            _kpi_chip("Total événements", summary.get("total", 0), PRIMARY),
            _kpi_chip("Accidents AT", summary.get("accidents", 0), DANGER),
            _kpi_chip("Presqu'accidents", summary.get("presquaccidents", 0), WARNING),
            _kpi_chip("Situations dang.", summary.get("situations", 0), ORANGE),
            _kpi_chip("Graves + fatals", summary.get("graves", 0), VIOLET),
            _kpi_chip("Jours d'arrêt", int(summary.get("total_jours_arret", 0) or 0), DANGER),
        ], spacing=8, run_spacing=8)

        # TF / TG cards
        tf = float(kpis.get("tf", 0) or 0)
        tg = float(kpis.get("tg", 0) or 0)
        tf_clr = DANGER if tf > 5 else WARNING if tf > 1 else SUCCESS
        tg_clr = DANGER if tg > 10 else WARNING if tg > 3 else SUCCESS
        kpi_kpi = ft.Row(controls=[
            ft.Container(
                bgcolor=_CARD, border=ft.border.all(1, tf_clr), border_radius=8, padding=16,
                content=ft.Column([
                    ft.Text("Taux de Fréquence (TF)", color=_MUTED, size=10),
                    ft.Text(f"{tf:.2f}", color=tf_clr, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("accidents / million heures exposées", color=_MUTED, size=9),
                ], spacing=2, tight=True),
            ),
            ft.Container(
                bgcolor=_CARD, border=ft.border.all(1, tg_clr), border_radius=8, padding=16,
                content=ft.Column([
                    ft.Text("Taux de Gravité (TG)", color=_MUTED, size=10),
                    ft.Text(f"{tg:.2f}", color=tg_clr, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("jours perdus / millier heures exposées", color=_MUTED, size=9),
                ], spacing=2, tight=True),
            ),
        ], spacing=12)

        # Monthly bar chart (custom — no ft.BarChart)
        months = _last_12_months()
        month_counts = Counter(str(a.get("date_evenement", ""))[:7] for a in accidents)
        bar_chart = _vert_bar_chart(months, month_counts, PRIMARY)
        chart_panel = _panel(
            "Événements par mois (12 derniers mois)",
            ft.Icons.BAR_CHART_OUTLINED, PRIMARY,
            [bar_chart],
        )

        # Distribution by gravity
        total = len(accidents) or 1
        grav_bars = ft.Column(
            controls=[
                _horiz_bar(g.replace("_", " ").title(), sum(1 for a in accidents if a.get("gravite") == g), total, clr)
                for g, clr in [("benin", SUCCESS), ("mineur", WARNING), ("majeur", ORANGE), ("grave", DANGER), ("fatal", VIOLET)]
            ],
            spacing=4, tight=True,
        )
        grav_panel = _panel("Distribution par gravité", ft.Icons.SHOW_CHART_OUTLINED, WARNING, [grav_bars])

        # Type distribution
        type_bars = ft.Column(
            controls=[
                _horiz_bar(t.replace("_", " ").title(), sum(1 for a in accidents if a.get("type_evenement") == t), total, clr)
                for t, clr in [("accident", DANGER), ("presquaccident", WARNING), ("situation_dangereuse", PRIMARY)]
            ],
            spacing=4, tight=True,
        )
        type_panel = _panel("Distribution par type", ft.Icons.PIE_CHART_OUTLINE, ORANGE, [type_bars])

        content_area.content = ft.Column(
            controls=[
                kpi_row,
                kpi_kpi,
                chart_panel,
                ft.Row(controls=[
                    ft.Container(content=grav_panel, expand=1),
                    ft.Container(content=type_panel, expand=1),
                ], spacing=10),
            ],
            spacing=12, tight=True,
        )

    # ── Tab 2 — EPI & Risques ─────────────────────────────────────────────
    def _render_epi_risques() -> None:
        from app.services.ppe_service import get_ppe_summary, list_ppe_items
        from app.services.risk_service import list_risks

        ppe_sum = _safe(get_ppe_summary, {})
        items   = _safe(list_ppe_items, [])
        risks   = _safe(list_risks, [])

        ppe_kpis = ft.ResponsiveRow(controls=[
            _kpi_chip("Total EPI", ppe_sum.get("items", 0), PRIMARY),
            _kpi_chip("Stock total", ppe_sum.get("stock_total", 0), SUCCESS),
            _kpi_chip("Affectés", ppe_sum.get("assigned", 0), PRIMARY),
            _kpi_chip("Stock bas", ppe_sum.get("low_stock", 0), DANGER if ppe_sum.get("low_stock") else SUCCESS),
            _kpi_chip("Expirés", ppe_sum.get("expired", 0), DANGER if ppe_sum.get("expired") else SUCCESS),
            _kpi_chip("Conformité", f"{ppe_sum.get('compliance_rate', 0)}%", SUCCESS if ppe_sum.get("compliance_rate") == 100 else WARNING),
        ], spacing=8, run_spacing=8)

        # Top 5 lowest stock
        low_items = sorted([i for i in items if i.get("quantite_disponible") is not None],
                           key=lambda x: int(x.get("quantite_disponible") or 0))[:8]
        stock_rows = ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_CARD2, border=ft.border.all(1, _BORDER), border_radius=6, padding=8,
                    content=ft.Row(controls=[
                        ft.Text(str(it.get("nom") or "—"), color=_TEXT, size=10, expand=True),
                        ft.Text(f"Stock: {it.get('quantite_disponible', 0)}", color=DANGER if (it.get("stock_bas")) else SUCCESS, size=10, weight=ft.FontWeight.BOLD),
                        ft.Text(f"/ seuil {it.get('seuil_minimum', 0)}", color=_MUTED, size=9),
                    ], spacing=8),
                )
                for it in low_items
            ],
            spacing=4, tight=True,
        ) if low_items else ft.Text("Aucun EPI en stock bas.", color=SUCCESS, italic=True, size=11)

        stock_panel = _panel("Stock EPI (niveaux les plus bas)", ft.Icons.INVENTORY_2_OUTLINED, DANGER, [stock_rows])

        # Risks by level — pie chart
        level_counts = Counter(r.get("risk_level", "moyen") for r in risks)
        LEVEL_CLR = {"critique": DANGER, "eleve": WARNING, "moyen": PRIMARY, "faible": SUCCESS}
        LEVEL_LBL = {"critique": "Critique", "eleve": "Élevé", "moyen": "Moyen", "faible": "Faible"}

        # Risk distribution — custom horizontal bars (no ft.PieChart)
        total_risks = len(risks) or 1
        risk_dist = ft.Column(
            controls=[
                _horiz_bar(LEVEL_LBL.get(lvl, lvl), level_counts.get(lvl, 0), total_risks, LEVEL_CLR.get(lvl, PRIMARY))
                for lvl in ["critique", "eleve", "moyen", "faible"]
            ],
            spacing=4, tight=True,
        )
        legend = ft.Row(
            controls=[_color_dot(LEVEL_CLR[lv], LEVEL_LBL[lv], level_counts.get(lv, 0), total_risks)
                      for lv in ["critique", "eleve", "moyen", "faible"]],
            spacing=12, wrap=True,
        )

        risk_kpis = ft.ResponsiveRow(controls=[
            _kpi_chip("Total risques", len(risks), PRIMARY),
            _kpi_chip("Critiques", level_counts.get("critique", 0), DANGER),
            _kpi_chip("Élevés", level_counts.get("eleve", 0), WARNING),
            _kpi_chip("Moyens", level_counts.get("moyen", 0), PRIMARY),
            _kpi_chip("Faibles", level_counts.get("faible", 0), SUCCESS),
            _kpi_chip("Actifs", sum(1 for r in risks if r.get("status") != "clos"), WARNING),
        ], spacing=8, run_spacing=8)

        risk_panel = _panel("Distribution des risques par niveau", ft.Icons.CRISIS_ALERT_OUTLINED, DANGER,
                            [risk_kpis, legend, risk_dist])

        content_area.content = ft.Column(
            controls=[ppe_kpis, ft.Row(controls=[
                ft.Container(content=stock_panel, expand=1),
                ft.Container(content=risk_panel, expand=1),
            ], spacing=10)],
            spacing=12, tight=True,
        )

    # ── Tab 3 — Permis ────────────────────────────────────────────────────
    def _render_permis() -> None:
        from app.services.permit_service import list_permits, get_permit_summary, PERMIT_TYPES

        permits    = _safe(list_permits, [])
        permit_sum = _safe(get_permit_summary, {})

        kpi_row = ft.ResponsiveRow(controls=[
            _kpi_chip("Total", permit_sum.get("total", 0), PRIMARY),
            _kpi_chip("Actifs", permit_sum.get("actifs", 0), SUCCESS),
            _kpi_chip("En validation", permit_sum.get("en_attente", 0), WARNING),
            _kpi_chip("Brouillons", permit_sum.get("brouillons", 0), _MUTED),
            _kpi_chip("Suspendus", permit_sum.get("suspendus", 0), DANGER),
            _kpi_chip("Clos", permit_sum.get("clos", 0), SUCCESS),
        ], spacing=8, run_spacing=8)

        # By type
        type_counts = Counter(p.get("type_permis", "general") for p in permits)
        total_p = len(permits) or 1
        TYPE_CLR = {
            "hauteur": WARNING, "feu": DANGER, "espace_confine": VIOLET,
            "electrique": ORANGE, "levage": PRIMARY, "excavation": "#8B5CF6", "general": SUCCESS,
        }
        type_bars = ft.Column(
            controls=[
                _horiz_bar(
                    PERMIT_TYPES.get(tp, tp.replace("_", " ").title()),
                    cnt, total_p,
                    TYPE_CLR.get(tp, PRIMARY),
                )
                for tp, cnt in type_counts.most_common()
            ],
            spacing=4, tight=True,
        )
        type_panel = _panel("Permis par type", ft.Icons.ASSIGNMENT_OUTLINED, PRIMARY, [type_bars])

        # By status
        status_counts = Counter(p.get("statut", "brouillon") for p in permits)
        STATUS_CLR = {
            "brouillon": "#64748B", "en_validation": WARNING,
            "valide": PRIMARY, "actif": SUCCESS, "suspendu": ORANGE, "clos": _MUTED,
        }
        status_bars = ft.Column(
            controls=[
                _horiz_bar(s.replace("_", " ").title(), cnt, total_p, STATUS_CLR.get(s, PRIMARY))
                for s, cnt in status_counts.most_common()
            ],
            spacing=4, tight=True,
        )
        status_panel = _panel("Permis par statut", ft.Icons.FACT_CHECK_OUTLINED, SUCCESS, [status_bars])

        # Monthly activity (custom bar chart — no ft.BarChart)
        months = _last_12_months()
        month_counts = Counter(str(p.get("date_emission", ""))[:7] for p in permits)
        bar_chart = _vert_bar_chart(months, month_counts, SUCCESS)
        chart_panel = _panel("Activité mensuelle (12 mois)", ft.Icons.BAR_CHART_OUTLINED, SUCCESS, [bar_chart])

        content_area.content = ft.Column(
            controls=[
                kpi_row,
                chart_panel,
                ft.Row(controls=[
                    ft.Container(content=type_panel, expand=1),
                    ft.Container(content=status_panel, expand=1),
                ], spacing=10),
            ],
            spacing=12, tight=True,
        )

    # ── Nav tabs ──────────────────────────────────────────────────────────
    tab_defs = [
        ("accidents",  "Accidents & Incidents", ft.Icons.PERSONAL_INJURY_OUTLINED),
        ("epi_risques","EPI & Risques",          ft.Icons.HEALTH_AND_SAFETY_OUTLINED),
        ("permis",     "Permis de Travail",      ft.Icons.ASSIGNMENT_OUTLINED),
    ]
    for key, label, icon in tab_defs:
        nav_buttons[key] = ft.ElevatedButton(
            label, icon=icon,
            style=ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: _MUTED},
                bgcolor={ft.ControlState.DEFAULT: _FIELD},
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=lambda ev, k=key: _switch_tab(k),
        )

    header = ft.Container(
        bgcolor=_CARD,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=44, height=44, bgcolor=VIOLET, border_radius=8,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.ANALYTICS_OUTLINED, color="#FFFFFF", size=24),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Statistiques QHSE", color=_TEXT, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("Tendances, distributions et indicateurs de performance", color=_MUTED, size=11),
                    ],
                    spacing=2, tight=True,
                ),
            ],
            spacing=12,
        ),
    )

    nav_bar = ft.Container(
        bgcolor=_CARD,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=8,
        content=ft.Row(controls=list(nav_buttons.values()), spacing=6, wrap=True),
    )

    root = ft.Container(
        bgcolor=_BG,
        expand=True,
        content=ft.Column(
            controls=[header, nav_bar, content_area],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    _switch_tab("accidents")
    return root
