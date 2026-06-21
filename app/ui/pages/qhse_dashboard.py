from __future__ import annotations
from datetime import datetime
from typing import Any

import flet as ft

_BG     = "#071321"
_CARD   = "#0D2040"
_CARD2  = "#0A1929"
_HEAD   = "#112240"
_BORDER = "#1E3A5F"
_TEXT   = "#E2E8F0"
_MUTED  = "#9DB0C5"
PRIMARY = "#3B82F6"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER  = "#EF4444"
VIOLET  = "#7C3AED"
ORANGE  = "#F97316"


def qhse_dashboard_page(page: Any = None) -> ft.Control:
    content_area = ft.Container()
    timestamp_text = ft.Text("", color=_MUTED, size=10, italic=True)

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def _safe(fn, default=None):
        try:
            return fn()
        except Exception:
            return default if default is not None else {}

    def _kpi_card(label: str, value: Any, color: str, icon: str, col: dict | None = None) -> ft.Control:
        return ft.Container(
            col=col or {"xs": 6, "sm": 4, "md": 3, "lg": 2},
            bgcolor=_CARD,
            border=ft.border.all(1, _BORDER),
            border_radius=8,
            padding=10,
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=36, height=36, bgcolor=color, border_radius=8,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, color="#FFFFFF", size=18),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(str(value), color=_TEXT, size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(label, color=_MUTED, size=9),
                        ],
                        spacing=0,
                        tight=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _alert_card(source: str, priorite: str, titre: str, message: str, icon: str) -> ft.Control:
        clr_map = {"critique": DANGER, "urgent": WARNING, "info": PRIMARY, "succes": SUCCESS}
        clr = clr_map.get(priorite, PRIMARY)
        return ft.Container(
            bgcolor=_CARD2,
            border=ft.border.only(
                left=ft.BorderSide(4, clr),
                top=ft.BorderSide(1, _BORDER),
                right=ft.BorderSide(1, _BORDER),
                bottom=ft.BorderSide(1, _BORDER),
            ),
            border_radius=6,
            padding=10,
            margin=ft.margin.only(bottom=4),
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=clr, size=18),
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        bgcolor=clr,
                                        border_radius=4,
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        content=ft.Text(priorite.upper(), color="#FFFFFF", size=8, weight=ft.FontWeight.BOLD),
                                    ),
                                    ft.Text(source, color=_MUTED, size=9),
                                ],
                                spacing=6,
                            ),
                            ft.Text(titre, color=_TEXT, size=10, weight=ft.FontWeight.W_600,
                                    max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(message, color=_MUTED, size=9,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )

    def _gauge(label: str, value: float, color: str) -> ft.Control:
        pct = max(0.0, min(100.0, float(value)))
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 3},
            bgcolor=_CARD,
            border=ft.border.all(1, _BORDER),
            border_radius=8,
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(label, color=_MUTED, size=10, expand=True),
                            ft.Text(f"{int(pct)}%", color=color, size=12, weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    ft.Stack(
                        controls=[
                            ft.Container(bgcolor=_BORDER, border_radius=4, height=8, width=220),
                            ft.Container(bgcolor=color, border_radius=4, height=8, width=max(4, 220 * pct / 100)),
                        ],
                        height=8,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
        )

    def _panel(title: str, icon: str, color: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            bgcolor=_CARD,
            border=ft.border.all(1, _BORDER),
            border_radius=8,
            padding=14,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon, color=color, size=16),
                            ft.Text(title, color=_TEXT, size=13, weight=ft.FontWeight.BOLD, expand=True),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(color=_BORDER, height=1),
                    *controls,
                ],
                spacing=8,
                tight=True,
            ),
        )

    def _mini_permit_card(p: dict[str, Any]) -> ft.Control:
        type_clr = {
            "hauteur": WARNING, "feu": DANGER, "espace_confine": VIOLET,
            "electrique": ORANGE, "levage": PRIMARY, "excavation": "#8B5CF6", "general": SUCCESS,
        }.get(str(p.get("type_permis", "")), PRIMARY)
        return ft.Container(
            bgcolor=_CARD2,
            border=ft.border.all(1, _BORDER),
            border_radius=6,
            padding=8,
            margin=ft.margin.only(bottom=4),
            content=ft.Row(
                controls=[
                    ft.Container(
                        bgcolor=type_clr, border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        content=ft.Text(
                            str(p.get("type_permis", "?")).replace("_", " ").upper()[:8],
                            color="#FFFFFF", size=8, weight=ft.FontWeight.BOLD,
                        ),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(str(p.get("titre", "—"))[:35], color=_TEXT, size=10, weight=ft.FontWeight.W_600),
                            ft.Text(f"{p.get('lieu', '—')} · expire {p.get('date_fin', '—')}", color=_MUTED, size=9),
                        ],
                        spacing=1,
                        tight=True,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _mini_accident_card(a: dict[str, Any]) -> ft.Control:
        grav_clr = {
            "fatal": VIOLET, "grave": DANGER, "majeur": ORANGE,
            "mineur": WARNING, "benin": SUCCESS,
        }.get(str(a.get("gravite", "")), _MUTED)
        return ft.Container(
            bgcolor=_CARD2,
            border=ft.border.only(
                left=ft.BorderSide(3, grav_clr),
                top=ft.BorderSide(1, _BORDER),
                right=ft.BorderSide(1, _BORDER),
                bottom=ft.BorderSide(1, _BORDER),
            ),
            border_radius=6,
            padding=8,
            margin=ft.margin.only(bottom=4),
            content=ft.Row(
                controls=[
                    ft.Container(
                        bgcolor=grav_clr, border_radius=4,
                        padding=ft.padding.symmetric(horizontal=5, vertical=2),
                        content=ft.Text(
                            str(a.get("gravite", "—")).upper()[:6],
                            color="#FFFFFF", size=8, weight=ft.FontWeight.BOLD,
                        ),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(f"{a.get('numero', '?')} — {a.get('type_evenement', '').replace('_', ' ').title()}", color=_TEXT, size=10, weight=ft.FontWeight.W_600),
                            ft.Text(f"{a.get('date_evenement', '—')} · {a.get('lieu', '—')} · {a.get('statut', '').title()}", color=_MUTED, size=9),
                        ],
                        spacing=1,
                        tight=True,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def refresh(e: Any = None) -> None:
        # ── Fetch all data ────────────────────────────────────────────────
        from app.services.risk_service import list_risks, get_overdue_reviews
        from app.services.accident_service import get_accident_summary, compute_kpis, list_accidents
        from app.services.permit_service import get_permit_summary, get_expiring_permits, list_permits
        from app.services.ppe_service import get_ppe_summary

        risks      = _safe(list_risks, [])
        overdue_rv = _safe(get_overdue_reviews, [])
        acc_sum    = _safe(get_accident_summary, {})
        acc_kpis   = _safe(compute_kpis, {})
        accidents  = _safe(list_accidents, [])
        permit_sum = _safe(get_permit_summary, {})
        expiring_p = _safe(lambda: get_expiring_permits(2), [])
        permits    = _safe(lambda: list_permits(statut="actif"), [])
        ppe_sum    = _safe(get_ppe_summary, {})

        # ── KPI counts ───────────────────────────────────────────────────
        from collections import Counter
        risk_levels = Counter(r.get("risk_level", "moyen") for r in risks)
        n_critique  = risk_levels.get("critique", 0)
        n_eleve     = risk_levels.get("eleve", 0)
        n_moyen     = risk_levels.get("moyen", 0)
        n_faible    = risk_levels.get("faible", 0)

        tf_val = float(acc_kpis.get("tf", 0) or 0)
        tf_clr = DANGER if tf_val > 5 else WARNING if tf_val > 1 else SUCCESS

        compliance = float(ppe_sum.get("compliance_rate", 0) or 0)
        comp_clr   = SUCCESS if compliance == 100 else WARNING if compliance > 80 else DANGER

        # ── KPI row ──────────────────────────────────────────────────────
        kpi_row = ft.ResponsiveRow(
            controls=[
                _kpi_card("Risques critiques", n_critique, DANGER if n_critique else SUCCESS, ft.Icons.CRISIS_ALERT_OUTLINED),
                _kpi_card("Risques élevés",    n_eleve,    WARNING if n_eleve else SUCCESS,   ft.Icons.WARNING_AMBER_OUTLINED),
                _kpi_card("Risques moyens",     n_moyen,    PRIMARY,                           ft.Icons.REMOVE_CIRCLE_OUTLINE),
                _kpi_card("Risques faibles",    n_faible,   SUCCESS,                           ft.Icons.CHECK_CIRCLE_OUTLINE),
                _kpi_card("Accidents ouverts",  acc_sum.get("ouverts", 0), DANGER if acc_sum.get("ouverts") else SUCCESS, ft.Icons.PERSONAL_INJURY_OUTLINED),
                _kpi_card("TF (×10⁶h)",         tf_val,     tf_clr,                            ft.Icons.TRENDING_UP_OUTLINED),
                _kpi_card("Permis actifs",      permit_sum.get("actifs", 0), SUCCESS,           ft.Icons.ASSIGNMENT_OUTLINED),
                _kpi_card("Permis en attente",  permit_sum.get("en_attente", 0), WARNING if permit_sum.get("en_attente") else SUCCESS, ft.Icons.PENDING_ACTIONS_OUTLINED),
                _kpi_card("Conformité EPI",     f"{int(compliance)}%", comp_clr,                ft.Icons.HEALTH_AND_SAFETY_OUTLINED),
                _kpi_card("Stock EPI bas",      ppe_sum.get("low_stock", 0), DANGER if ppe_sum.get("low_stock") else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            ],
            spacing=8,
            run_spacing=8,
        )

        # ── Alerts column ────────────────────────────────────────────────
        alert_cards: list[ft.Control] = []
        for r in overdue_rv[:3]:
            desc = str(r.get("activity") or r.get("title") or "Risque")[:45]
            alert_cards.append(_alert_card("Risques", "urgent", f"Révision en retard : {desc}",
                                           f"Date prévue : {r.get('review_date', '?')}", ft.Icons.SHIELD_OUTLINED))
        for a in [x for x in accidents if x.get("statut") == "ouvert"][:3]:
            alert_cards.append(_alert_card("Accidents",
                                           "critique" if a.get("gravite") in ("grave", "fatal") else "urgent",
                                           f"{a.get('numero', '?')} — {a.get('gravite', '').title()}",
                                           f"{a.get('date_evenement', '?')} · {a.get('lieu', '?')}", ft.Icons.PERSONAL_INJURY_OUTLINED))
        for p in expiring_p[:3]:
            alert_cards.append(_alert_card("Permis", "urgent",
                                           f"Permis expirant : {p.get('titre', '?')[:35]}",
                                           f"Expire le {p.get('date_fin', '?')} · {p.get('lieu', '?')}", ft.Icons.ASSIGNMENT_OUTLINED))

        if not alert_cards:
            alert_cards = [ft.Container(
                bgcolor="#052E16", border=ft.border.all(1, SUCCESS),
                border_radius=8, padding=12,
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=20),
                    ft.Text("Aucune alerte critique — Tout est sous contrôle", color=SUCCESS, size=11),
                ], spacing=8),
            )]

        alerts_col = _panel("Alertes prioritaires", ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, DANGER,
                            alert_cards)

        # ── Permits column ────────────────────────────────────────────────
        permit_cards: list[ft.Control] = [_mini_permit_card(p) for p in permits[:5]]
        if not permit_cards:
            permit_cards = [ft.Text("Aucun permis actif.", color=_MUTED, size=11, italic=True)]
        permits_col = _panel("Permis actifs", ft.Icons.ASSIGNMENT_OUTLINED, SUCCESS, permit_cards)

        # ── Accidents column ──────────────────────────────────────────────
        recent_acc = accidents[:5]
        acc_cards: list[ft.Control] = [_mini_accident_card(a) for a in recent_acc]
        if not acc_cards:
            acc_cards = [ft.Text("Aucun accident récent.", color=_MUTED, size=11, italic=True)]
        acc_col = _panel("Accidents récents", ft.Icons.PERSONAL_INJURY_OUTLINED, WARNING, acc_cards)

        # ── Gauges row ────────────────────────────────────────────────────
        active_risks = [r for r in risks if r.get("status") != "clos"]
        closed_risks = len(risks) - len(active_risks)
        risk_pct = round(closed_risks / len(risks) * 100, 1) if risks else 0.0

        total_acc = int(acc_sum.get("total", 0) or 0)
        investigated = total_acc - int(acc_sum.get("ouverts", 0) or 0)
        acc_inv_pct = round(investigated / total_acc * 100, 1) if total_acc else 100.0

        total_p = int(permit_sum.get("total", 0) or 0)
        actifs_p = int(permit_sum.get("actifs", 0) or 0)
        permit_pct = round(actifs_p / total_p * 100, 1) if total_p else 0.0

        gauges_row = ft.ResponsiveRow(
            controls=[
                _gauge("Conformité EPI", compliance, comp_clr),
                _gauge("Risques traités", risk_pct, SUCCESS if risk_pct > 80 else WARNING),
                _gauge("Accidents investigués", acc_inv_pct, SUCCESS if acc_inv_pct > 80 else WARNING),
                _gauge("Permis actifs / total", permit_pct, PRIMARY),
            ],
            spacing=8,
            run_spacing=8,
        )

        # ── Middle row ───────────────────────────────────────────────────
        middle_row = ft.Row(
            controls=[
                ft.Container(content=alerts_col, expand=2),
                ft.Container(content=permits_col, expand=1),
                ft.Container(content=acc_col, expand=1),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        now_str = datetime.now().strftime("%H:%M:%S")
        timestamp_text.value = f"Données mises à jour à {now_str}"

        content_area.content = ft.Column(
            controls=[kpi_row, middle_row, gauges_row, timestamp_text],
            spacing=12,
            tight=True,
        )
        _update()

    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH_OUTLINED,
        icon_color=PRIMARY,
        tooltip="Actualiser le tableau de bord",
        on_click=refresh,
    )

    header = ft.Container(
        bgcolor=_CARD,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=44, height=44, bgcolor=PRIMARY, border_radius=8,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.SHIELD_OUTLINED, color="#FFFFFF", size=24),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Tableau de bord QHSE", color=_TEXT, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("Synthèse temps réel — Risques · Accidents · Permis · EPI", color=_MUTED, size=11),
                    ],
                    spacing=2,
                    tight=True,
                ),
                ft.Container(expand=True),
                refresh_btn,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    root = ft.Container(
        bgcolor=_BG,
        expand=True,
        content=ft.Column(
            controls=[header, content_area],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    refresh()
    return root
