"""magasin.py — Page Gestion du Magasin Diamond Drilling.

Onglets : Dashboard | Catalogue | Fournisseurs | Entrées | Sorties | Stock
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import flet as ft

from app.services.magasin_export_service import export_magasin_xlsx
from app.services.magasin_service import (
    delete_article,
    delete_entree,
    delete_fournisseur,
    delete_sortie,
    get_magasin_dashboard,
    get_stock_actuel,
    get_stock_alerts,
    list_articles,
    list_entrees,
    list_fournisseurs,
    list_sorties,
    next_numero_be,
    next_numero_bs,
    save_article,
    save_entree,
    save_fournisseur,
    save_sortie,
)

_log = logging.getLogger(__name__)

# ── Palette ──────────────────────────────────────────────────────────────────
BG       = "#0F172A"
CARD     = "#1E293B"
CARD2    = "#162032"
BORDER   = "#334155"
TEXT     = "#F1F5F9"
MUTED    = "#94A3B8"
PRIMARY  = "#3B82F6"
SUCCESS  = "#10B981"
WARNING  = "#F59E0B"
DANGER   = "#EF4444"
GOLD     = "#C8A400"
LIGHT_GOLD = "#FFD700"
NAVY     = "#0D1B2A"
FIELD    = "#0F172A"

_MONTHS = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_fcfa(val: float) -> str:
    return f"{val:,.0f} FCFA".replace(",", " ")


def _card(content: ft.Control, padding: int = 14, expand: bool | int = False) -> ft.Container:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=10,
        padding=padding,
        expand=expand or None,
        content=content,
    )


def _kpi(title: str, value: str, subtitle: str, color: str, icon: str) -> ft.Container:
    return ft.Container(
        bgcolor=CARD2,
        border=ft.border.all(1, color + "55"),
        border_radius=10,
        padding=14,
        expand=True,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=36, height=36, bgcolor=color + "22",
                            border_radius=8,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=color, size=20),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(title, color=MUTED, size=10),
                                ft.Text(value, color=color, size=18, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=2, tight=True, expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(subtitle, color=MUTED, size=10),
            ],
            spacing=6, tight=True,
        ),
    )


def _section_title(text: str, icon: str, color: str = PRIMARY) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Icon(icon, color=color, size=18),
            ft.Text(text, color=TEXT, size=15, weight=ft.FontWeight.BOLD),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _field(label: str, ref: ft.Ref, multiline: bool = False, width: int | None = None) -> ft.TextField:
    tf = ft.TextField(
        label=label,
        ref=ref,
        bgcolor=FIELD,
        color=TEXT,
        border_color=BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=MUTED),
        multiline=multiline,
        min_lines=3 if multiline else 1,
        max_lines=5 if multiline else 1,
        width=width,
        text_size=12,
    )
    return tf


def _dd(label: str, ref: ft.Ref, options: list[str], width: int | None = None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        ref=ref,
        bgcolor=FIELD,
        color=TEXT,
        border_color=BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=MUTED),
        width=width,
        text_size=12,
        options=[ft.dropdown.Option("", "— Choisir —")] + [
            ft.dropdown.Option(o, o) for o in options
        ],
    )


def _alert_badge(count: int, color: str = DANGER) -> ft.Container:
    return ft.Container(
        bgcolor=color,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        content=ft.Text(str(count), color="#FFFFFF", size=10, weight=ft.FontWeight.BOLD),
        visible=count > 0,
    )


# ── Stock bar chart (mini) ────────────────────────────────────────────────────

def _mini_bar_chart(monthly: list[dict]) -> ft.Control:
    if not monthly:
        return ft.Text("Aucun mouvement.", color=MUTED, size=11)
    max_val = max((m["entrees"] + m["sorties"]) for m in monthly) or 1
    bars = []
    for m in monthly:
        ent_h = int(60 * m["entrees"] / max_val)
        sor_h = int(60 * m["sorties"] / max_val)
        bars.append(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(width=8, height=max(2, ent_h), bgcolor=SUCCESS, border_radius=2),
                            ft.Container(width=8, height=max(2, sor_h), bgcolor=DANGER, border_radius=2),
                        ],
                        spacing=2,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    ft.Text(m["mois"], color=MUTED, size=8, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
                tight=True,
            )
        )
    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(width=10, height=10, bgcolor=SUCCESS, border_radius=2),
                    ft.Text("Entrées", color=MUTED, size=10),
                    ft.Container(width=10, height=10, bgcolor=DANGER, border_radius=2),
                    ft.Text("Sorties", color=MUTED, size=10),
                ],
                spacing=6,
            ),
            ft.Row(controls=bars, spacing=6, vertical_alignment=ft.CrossAxisAlignment.END),
        ],
        spacing=8,
    )


# ── Main page ─────────────────────────────────────────────────────────────────

def magasin_page(page: Any = None) -> ft.Control:
    state: dict[str, Any] = {"tab": "dashboard"}
    status_text = ft.Text("", color=MUTED, size=11)
    content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)

    def notify(msg: str, color: str = SUCCESS) -> None:
        status_text.value = msg
        status_text.color = color
        try:
            status_text.update()
        except RuntimeError:
            pass

    def _upd() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    # ── TAB: DASHBOARD ────────────────────────────────────────────────────────
    def build_dashboard() -> None:
        try:
            dash = get_magasin_dashboard()
        except Exception as exc:
            _log.warning("[magasin] dashboard load failed: %s", exc)
            dash = {}

        def _kpi_card(title: str, value: str, subtitle: str, color: str, icon: str) -> ft.Container:
            return ft.Container(
                bgcolor=CARD2,
                border=ft.border.all(1, color + "55"),
                border_radius=10,
                padding=14,
                width=260,
                content=ft.Column(
                    controls=[
                        ft.Row(controls=[
                            ft.Container(
                                width=36, height=36, bgcolor=color + "22",
                                border_radius=8,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(icon, color=color, size=20),
                            ),
                            ft.Column(controls=[
                                ft.Text(title, color=MUTED, size=10),
                                ft.Text(value, color=color, size=16, weight=ft.FontWeight.BOLD),
                            ], spacing=2, tight=True),
                        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(subtitle, color=MUTED, size=10),
                    ],
                    spacing=6, tight=True,
                ),
            )

        kpi_row = ft.Row(
            controls=[
                _kpi_card("Valeur Stock", _fmt_fcfa(dash.get("valeur_stock_actuel", 0)),
                          "Stock total estimé", GOLD, ft.Icons.INVENTORY_2_OUTLINED),
                _kpi_card("Valeur Entrées", _fmt_fcfa(dash.get("total_entrees_valeur", 0)),
                          f"{dash.get('nb_entrees',0)} bons d'entrée", SUCCESS, ft.Icons.MOVE_TO_INBOX_OUTLINED),
                _kpi_card("Valeur Sorties", _fmt_fcfa(dash.get("total_sorties_valeur", 0)),
                          f"{dash.get('nb_sorties',0)} bons de sortie", DANGER, ft.Icons.OUTBOX_OUTLINED),
                _kpi_card("Références", str(dash.get("nb_articles", 0)),
                          f"{dash.get('nb_fournisseurs',0)} fournisseurs", PRIMARY, ft.Icons.CATEGORY_OUTLINED),
            ],
            spacing=10,
            wrap=True,
        )

        # Graphique mensuel simplifié — tableau texte
        monthly = dash.get("monthly", [])
        month_rows = []
        for m in monthly:
            ent = float(m.get("entrees") or 0)
            sor = float(m.get("sorties") or 0)
            if ent == 0 and sor == 0:
                continue
            solde = ent - sor
            s_color = SUCCESS if solde >= 0 else DANGER
            month_rows.append(
                ft.Container(
                    bgcolor=CARD2, border_radius=6, padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    content=ft.Row(controls=[
                        ft.Text(m["mois"], color=TEXT, size=11, weight=ft.FontWeight.BOLD, width=40),
                        ft.Container(width=80, content=ft.Text(f"{ent:,.0f}", color=SUCCESS, size=10, text_align=ft.TextAlign.RIGHT)),
                        ft.Container(width=80, content=ft.Text(f"{sor:,.0f}", color=DANGER, size=10, text_align=ft.TextAlign.RIGHT)),
                        ft.Container(width=100, content=ft.Text(f"{solde:+,.0f}", color=s_color, size=10, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT)),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        monthly_section = ft.Column(controls=[
            ft.Row(controls=[
                ft.Text("Mois", color=MUTED, size=10, width=40),
                ft.Container(width=80, content=ft.Text("Entrées FCFA", color=SUCCESS, size=10, text_align=ft.TextAlign.RIGHT)),
                ft.Container(width=80, content=ft.Text("Sorties FCFA", color=DANGER, size=10, text_align=ft.TextAlign.RIGHT)),
                ft.Container(width=100, content=ft.Text("Solde FCFA", color=MUTED, size=10, text_align=ft.TextAlign.RIGHT)),
            ], spacing=8),
            *(month_rows if month_rows else [ft.Text("Aucun mouvement enregistré.", color=MUTED, size=11)]),
        ], spacing=4)

        alerts = dash.get("alerts", [])
        nb_crit = dash.get("nb_critiques", 0)
        nb_alert_only = len(alerts) - nb_crit

        alert_rows = []
        for a in alerts[:8]:
            is_crit = float(a.get("stock_actuel") or 0) <= float(a.get("stock_min") or 0)
            color = DANGER if is_crit else WARNING
            label = "CRITIQUE" if is_crit else "ALERTE"
            alert_rows.append(
                ft.Container(
                    bgcolor=color + "15",
                    border=ft.border.all(1, color + "55"),
                    border_radius=6,
                    padding=8,
                    content=ft.Row(controls=[
                        ft.Container(
                            bgcolor=color, border_radius=4,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            content=ft.Text(label, color="#FFFFFF", size=8, weight=ft.FontWeight.BOLD),
                        ),
                        ft.Text(f"[{a.get('code_article','')}]", color=MUTED, size=10, width=90),
                        ft.Text(str(a.get("designation") or ""), color=TEXT, size=11, width=200),
                        ft.Text(
                            f"Stock: {float(a.get('stock_actuel') or 0):.0f} {a.get('unite','') or ''}  |  Min: {float(a.get('stock_min') or 0):.0f}",
                            color=color, size=10, weight=ft.FontWeight.BOLD,
                        ),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        recent_ent = dash.get("recent_entrees", [])
        recent_sor = dash.get("recent_sorties", [])

        def _recent_ent_item(r: dict) -> ft.Container:
            return ft.Container(
                bgcolor=CARD2, border_radius=6, padding=8,
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(str(r.get("numero_be") or ""), color=SUCCESS, size=10, weight=ft.FontWeight.BOLD, width=110),
                        ft.Text(str(r.get("date_entree") or "")[:10], color=MUTED, size=10),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Text(str(r.get("designation") or ""), color=TEXT, size=11, width=200),
                        ft.Text(f"{float(r.get('quantite') or 0):.0f} {r.get('unite') or ''}", color=PRIMARY, size=10),
                    ], spacing=8),
                ], spacing=2, tight=True),
            )

        def _recent_sor_item(r: dict) -> ft.Container:
            return ft.Container(
                bgcolor=CARD2, border_radius=6, padding=8,
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(str(r.get("numero_bs") or ""), color=DANGER, size=10, weight=ft.FontWeight.BOLD, width=110),
                        ft.Text(str(r.get("date_sortie") or "")[:10], color=MUTED, size=10),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Text(str(r.get("designation") or ""), color=TEXT, size=11, width=200),
                        ft.Text(str(r.get("demandeur") or ""), color=MUTED, size=10),
                    ], spacing=8),
                ], spacing=2, tight=True),
            )

        content_area.controls = [
            # KPIs
            _card(ft.Column(controls=[
                _section_title("Tableau de bord Magasin", ft.Icons.STORE_OUTLINED, GOLD),
                kpi_row,
            ], spacing=12)),
            # Mouvements mensuels
            _card(ft.Column(controls=[
                _section_title(f"Mouvements {date.today().year}", ft.Icons.BAR_CHART_OUTLINED, PRIMARY),
                ft.Divider(color=BORDER, height=1),
                monthly_section,
            ], spacing=8)),
            # Alertes
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Alertes Stock", ft.Icons.WARNING_AMBER_OUTLINED, DANGER),
                    ft.Container(expand=True),
                    _alert_badge(nb_crit, DANGER),
                    _alert_badge(nb_alert_only, WARNING),
                ], spacing=8),
                ft.Divider(color=BORDER, height=1),
                *(alert_rows if alert_rows else [
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=20),
                        ft.Text("Aucun article en alerte", color=SUCCESS, size=12),
                    ], spacing=8)
                ]),
            ], spacing=8)),
            # Récents
            ft.Row(controls=[
                ft.Container(
                    expand=True,
                    content=_card(ft.Column(controls=[
                        _section_title("Dernières Entrées", ft.Icons.MOVE_TO_INBOX_OUTLINED, SUCCESS),
                        ft.Divider(color=BORDER, height=1),
                        *(
                            [_recent_ent_item(r) for r in recent_ent]
                            if recent_ent else [ft.Text("Aucune entrée récente.", color=MUTED, size=11)]
                        ),
                    ], spacing=6)),
                ),
                ft.Container(
                    expand=True,
                    content=_card(ft.Column(controls=[
                        _section_title("Dernières Sorties", ft.Icons.OUTBOX_OUTLINED, DANGER),
                        ft.Divider(color=BORDER, height=1),
                        *(
                            [_recent_sor_item(r) for r in recent_sor]
                            if recent_sor else [ft.Text("Aucune sortie récente.", color=MUTED, size=11)]
                        ),
                    ], spacing=6)),
                ),
            ], spacing=12),
        ]

    # ── TAB: CATALOGUE ────────────────────────────────────────────────────────
    _cat_search = ft.Ref[ft.TextField]()
    _cat_table  = ft.Ref[ft.Column]()
    _cat_form_visible = ft.Ref[ft.Column]()

    cat_refs = {k: ft.Ref[ft.TextField]() for k in [
        "code_article", "designation", "categorie", "sous_categorie",
        "unite", "stock_min", "stock_max", "stock_alerte",
        "prix_unitaire", "fournisseur_prefere", "emplacement", "observations",
    ]}
    _cat_editing: dict[str, Any] = {}

    def _cat_row(a: dict) -> ft.Container:
        stk = get_stock_actuel()
        stk_map = {s["code_article"]: s for s in stk}
        s = stk_map.get(a["code_article"], {})
        stock_val = float(s.get("stock_actuel") or 0)
        alerte = float(a.get("stock_alerte") or 0)
        min_s  = float(a.get("stock_min") or 0)
        color  = DANGER if stock_val <= min_s else (WARNING if stock_val <= alerte else SUCCESS)
        return ft.Container(
            bgcolor=CARD2,
            border=ft.border.all(1, color + "33"),
            border_radius=8,
            padding=10,
            content=ft.Row(
                controls=[
                    ft.Container(width=4, bgcolor=color, border_radius=2, height=40),
                    ft.Column(
                        controls=[
                            ft.Row(controls=[
                                ft.Text(f"[{a['code_article']}]", color=PRIMARY, size=10, weight=ft.FontWeight.BOLD, width=100),
                                ft.Text(str(a["designation"] or ""), color=TEXT, size=11, expand=True),
                                ft.Text(str(a.get("categorie") or ""), color=MUTED, size=10, width=120),
                            ], spacing=8),
                            ft.Row(controls=[
                                ft.Text(f"Unité: {a.get('unite') or '-'}", color=MUTED, size=10, width=80),
                                ft.Text(f"Min: {a.get('stock_min') or 0:.0f}", color=MUTED, size=10, width=70),
                                ft.Text(f"Max: {a.get('stock_max') or 0:.0f}", color=MUTED, size=10, width=70),
                                ft.Text(f"Stock: {stock_val:.0f}", color=color, size=10, weight=ft.FontWeight.BOLD, width=80),
                                ft.Text(f"PU: {a.get('prix_unitaire') or 0:,.0f} FCFA", color=GOLD, size=10),
                            ], spacing=8),
                        ],
                        spacing=3, expand=True, tight=True,
                    ),
                    ft.Row(controls=[
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                      tooltip="Modifier",
                                      on_click=lambda e, x=a: _cat_edit(x)),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                      tooltip="Supprimer",
                                      on_click=lambda e, x=a: _cat_delete(x["code_article"])),
                    ], spacing=0),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _cat_load() -> None:
        q = str(_cat_search.current.value or "") if _cat_search.current else ""
        arts = list_articles(search=q)
        col = _cat_table.current
        if col is None:
            return
        col.controls = [_cat_row(a) for a in arts] or [
            ft.Text("Aucun article.", color=MUTED, size=12)
        ]
        try:
            col.update()
        except RuntimeError:
            pass

    def _cat_edit(a: dict) -> None:
        _cat_editing.clear()
        _cat_editing.update(a)
        for k, ref in cat_refs.items():
            if ref.current:
                ref.current.value = str(a.get(k) or "")
                try:
                    ref.current.update()
                except RuntimeError:
                    pass
        _show_cat_form(True)

    def _cat_delete(code: str) -> None:
        try:
            delete_article(code)
            notify(f"Article {code} supprimé.")
            _cat_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _cat_save(e: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in cat_refs.items()}
        if _cat_editing:
            data["code_article"] = _cat_editing["code_article"]
        try:
            code = save_article(data)
            notify(f"Article {code} enregistré.")
            _cat_editing.clear()
            _show_cat_form(False)
            _cat_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _show_cat_form(visible: bool) -> None:
        form = _cat_form_visible.current
        if form:
            form.visible = visible
            try:
                form.update()
            except RuntimeError:
                pass

    def build_catalogue() -> None:
        form_col = ft.Column(
            ref=_cat_form_visible,
            visible=False,
            controls=[
                ft.Divider(color=BORDER),
                _section_title("Formulaire Article", ft.Icons.EDIT_OUTLINED, PRIMARY),
                ft.Row(controls=[
                    _field("Code Article *", cat_refs["code_article"], width=140),
                    _field("Désignation *", cat_refs["designation"], width=280),
                    _field("Catégorie", cat_refs["categorie"], width=160),
                    _field("Sous-catégorie", cat_refs["sous_categorie"], width=160),
                    _field("Unité", cat_refs["unite"], width=80),
                ], spacing=8, wrap=True),
                ft.Row(controls=[
                    _field("Stock Min", cat_refs["stock_min"], width=100),
                    _field("Stock Max", cat_refs["stock_max"], width=100),
                    _field("Stock Alerte", cat_refs["stock_alerte"], width=100),
                    _field("Prix Unitaire (FCFA)", cat_refs["prix_unitaire"], width=160),
                    _field("Fournisseur Préféré", cat_refs["fournisseur_prefere"], width=200),
                    _field("Emplacement", cat_refs["emplacement"], width=140),
                ], spacing=8, wrap=True),
                _field("Observations", cat_refs["observations"], multiline=True),
                ft.Row(controls=[
                    ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                      bgcolor=SUCCESS, color="#FFFFFF", on_click=_cat_save),
                    ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE,
                                      style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: MUTED},
                                                           side=ft.BorderSide(1, BORDER)),
                                      on_click=lambda e: _show_cat_form(False)),
                ], spacing=8),
            ],
            spacing=10,
        )

        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Catalogue des Articles", ft.Icons.INVENTORY_OUTLINED, PRIMARY),
                    ft.Container(expand=True),
                    ft.TextField(
                        ref=_cat_search, hint_text="Rechercher...",
                        bgcolor=FIELD, color=TEXT, border_color=BORDER,
                        focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=MUTED),
                        width=200, height=38, text_size=12,
                        on_submit=lambda e: _cat_load(),
                    ),
                    ft.ElevatedButton("Nouvel article", icon=ft.Icons.ADD,
                                      bgcolor=PRIMARY, color="#FFFFFF",
                                      on_click=lambda e: (_cat_editing.clear(),
                                                          [setattr(r.current, 'value', '') or r.current.update()
                                                           for r in cat_refs.values() if r.current],
                                                          _show_cat_form(True))),
                ], spacing=8),
                form_col,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_cat_table, spacing=6),
            ], spacing=10)),
        ]
        _cat_load()

    # ── TAB: FOURNISSEURS ─────────────────────────────────────────────────────
    _fou_search = ft.Ref[ft.TextField]()
    _fou_table  = ft.Ref[ft.Column]()
    _fou_form   = ft.Ref[ft.Column]()
    fou_refs = {k: ft.Ref[ft.TextField]() for k in [
        "code_fournisseur", "raison_sociale", "categorie", "contact",
        "telephone", "email", "delai_livraison", "conditions_paiement", "note_qualite",
    ]}
    _fou_editing: dict[str, Any] = {}

    def _fou_row(f: dict) -> ft.Container:
        note = float(f.get("note_qualite") or 0)
        stars = "★" * int(note) + "☆" * (5 - int(note))
        return ft.Container(
            bgcolor=CARD2, border=ft.border.all(1, BORDER), border_radius=8, padding=10,
            content=ft.Row(controls=[
                ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(f"[{f['code_fournisseur']}]", color=PRIMARY, size=10, weight=ft.FontWeight.BOLD, width=100),
                        ft.Text(str(f["raison_sociale"] or ""), color=TEXT, size=11, expand=True),
                        ft.Text(str(f.get("categorie") or ""), color=MUTED, size=10, width=120),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.PHONE_OUTLINED, color=MUTED, size=12),
                        ft.Text(str(f.get("telephone") or "-"), color=MUTED, size=10, width=120),
                        ft.Icon(ft.Icons.MAIL_OUTLINED, color=MUTED, size=12),
                        ft.Text(str(f.get("email") or "-"), color=MUTED, size=10, expand=True),
                        ft.Text(stars, color=GOLD, size=12),
                    ], spacing=6),
                ], spacing=3, expand=True, tight=True),
                ft.Row(controls=[
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                  on_click=lambda e, x=f: _fou_edit(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                  on_click=lambda e, x=f: _fou_delete(x["code_fournisseur"])),
                ], spacing=0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _fou_load() -> None:
        q = str(_fou_search.current.value or "") if _fou_search.current else ""
        fous = list_fournisseurs(search=q)
        col = _fou_table.current
        if col:
            col.controls = [_fou_row(f) for f in fous] or [ft.Text("Aucun fournisseur.", color=MUTED, size=12)]
            try:
                col.update()
            except RuntimeError:
                pass

    def _fou_edit(f: dict) -> None:
        _fou_editing.clear()
        _fou_editing.update(f)
        for k, ref in fou_refs.items():
            if ref.current:
                ref.current.value = str(f.get(k) or "")
                try:
                    ref.current.update()
                except RuntimeError:
                    pass
        col = _fou_form.current
        if col:
            col.visible = True
            try:
                col.update()
            except RuntimeError:
                pass

    def _fou_delete(code: str) -> None:
        try:
            delete_fournisseur(code)
            notify(f"Fournisseur {code} supprimé.")
            _fou_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _fou_save(e: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in fou_refs.items()}
        if _fou_editing:
            data["code_fournisseur"] = _fou_editing["code_fournisseur"]
        try:
            code = save_fournisseur(data)
            notify(f"Fournisseur {code} enregistré.")
            _fou_editing.clear()
            col = _fou_form.current
            if col:
                col.visible = False
                try:
                    col.update()
                except RuntimeError:
                    pass
            _fou_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def build_fournisseurs() -> None:
        form_col = ft.Column(
            ref=_fou_form, visible=False,
            controls=[
                ft.Divider(color=BORDER),
                _section_title("Formulaire Fournisseur", ft.Icons.EDIT_OUTLINED, PRIMARY),
                ft.Row(controls=[
                    _field("Code Fournisseur *", fou_refs["code_fournisseur"], width=140),
                    _field("Raison Sociale *", fou_refs["raison_sociale"], width=260),
                    _field("Catégorie", fou_refs["categorie"], width=160),
                    _field("Contact", fou_refs["contact"], width=160),
                ], spacing=8, wrap=True),
                ft.Row(controls=[
                    _field("Téléphone", fou_refs["telephone"], width=140),
                    _field("Email", fou_refs["email"], width=220),
                    _field("Délai Livraison", fou_refs["delai_livraison"], width=140),
                    _field("Conditions Paiement", fou_refs["conditions_paiement"], width=180),
                    _field("Note Qualité (0-5)", fou_refs["note_qualite"], width=120),
                ], spacing=8, wrap=True),
                ft.Row(controls=[
                    ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                      bgcolor=SUCCESS, color="#FFFFFF", on_click=_fou_save),
                    ft.OutlinedButton("Annuler", style=ft.ButtonStyle(
                        color={ft.ControlState.DEFAULT: MUTED}, side=ft.BorderSide(1, BORDER)),
                        on_click=lambda e: setattr(_fou_form.current, 'visible', False) or _fou_form.current.update()),
                ], spacing=8),
            ], spacing=10,
        )
        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Fournisseurs", ft.Icons.BUSINESS_OUTLINED, PRIMARY),
                    ft.Container(expand=True),
                    ft.TextField(ref=_fou_search, hint_text="Rechercher...",
                                 bgcolor=FIELD, color=TEXT, border_color=BORDER,
                                 focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=MUTED),
                                 width=200, height=38, text_size=12,
                                 on_submit=lambda e: _fou_load()),
                    ft.ElevatedButton("Nouveau fournisseur", icon=ft.Icons.ADD,
                                      bgcolor=PRIMARY, color="#FFFFFF",
                                      on_click=lambda e: (_fou_editing.clear(),
                                                          [setattr(r.current, 'value', '') or r.current.update()
                                                           for r in fou_refs.values() if r.current],
                                                          setattr(_fou_form.current, 'visible', True),
                                                          _fou_form.current.update())),
                ], spacing=8),
                form_col,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_fou_table, spacing=6),
            ], spacing=10)),
        ]
        _fou_load()

    # ── TAB: ENTRÉES ──────────────────────────────────────────────────────────
    _ent_search = ft.Ref[ft.TextField]()
    _ent_table  = ft.Ref[ft.Column]()
    _ent_form   = ft.Ref[ft.Column]()
    ent_refs = {k: ft.Ref[ft.TextField]() for k in [
        "numero_be", "date_entree", "code_article", "designation",
        "categorie", "quantite", "unite", "prix_unitaire",
        "fournisseur", "numero_bl", "numero_commande", "receptionne_par", "observations",
    ]}
    _ent_editing: dict[str, Any] = {}

    def _ent_row(e_: dict) -> ft.Container:
        return ft.Container(
            bgcolor=CARD2, border=ft.border.all(1, SUCCESS + "33"), border_radius=8, padding=10,
            content=ft.Row(controls=[
                ft.Container(width=4, bgcolor=SUCCESS, border_radius=2, height=40),
                ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(str(e_.get("numero_be") or ""), color=SUCCESS, size=10, weight=ft.FontWeight.BOLD, width=110),
                        ft.Text(str(e_.get("date_entree") or "")[:10], color=MUTED, size=10, width=90),
                        ft.Text(f"[{e_.get('code_article') or ''}]", color=PRIMARY, size=10, width=90),
                        ft.Text(str(e_.get("designation") or ""), color=TEXT, size=11, expand=True),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Text(f"Qté: {e_.get('quantite') or 0:.0f} {e_.get('unite') or ''}", color=TEXT, size=10, width=110),
                        ft.Text(f"PU: {float(e_.get('prix_unitaire') or 0):,.0f}", color=MUTED, size=10, width=110),
                        ft.Text(f"Total: {_fmt_fcfa(float(e_.get('valeur_totale') or 0))}", color=GOLD, size=10, weight=ft.FontWeight.BOLD),
                        ft.Text(str(e_.get("fournisseur") or ""), color=MUTED, size=10),
                    ], spacing=8),
                ], spacing=3, expand=True, tight=True),
                ft.Row(controls=[
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                  on_click=lambda ev, x=e_: _ent_edit(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                  on_click=lambda ev, x=e_: _ent_delete(x["id_entree"])),
                ], spacing=0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _ent_load() -> None:
        q = str(_ent_search.current.value or "") if _ent_search.current else ""
        ents = list_entrees(search=q)
        col = _ent_table.current
        if col:
            col.controls = [_ent_row(e_) for e_ in ents] or [ft.Text("Aucune entrée.", color=MUTED, size=12)]
            try:
                col.update()
            except RuntimeError:
                pass

    def _ent_edit(e_: dict) -> None:
        _ent_editing.clear()
        _ent_editing.update(e_)
        for k, ref in ent_refs.items():
            if ref.current:
                ref.current.value = str(e_.get(k) or "")
                try:
                    ref.current.update()
                except RuntimeError:
                    pass
        form = _ent_form.current
        if form:
            form.visible = True
            try:
                form.update()
            except RuntimeError:
                pass

    def _ent_delete(eid: int) -> None:
        try:
            delete_entree(eid)
            notify("Entrée supprimée.")
            _ent_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _ent_save(e: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in ent_refs.items()}
        if _ent_editing:
            data["id_entree"] = _ent_editing["id_entree"]
        try:
            save_entree(data)
            notify("Bon d'entrée enregistré.")
            _ent_editing.clear()
            form = _ent_form.current
            if form:
                form.visible = False
                try:
                    form.update()
                except RuntimeError:
                    pass
            _ent_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _ent_new() -> None:
        _ent_editing.clear()
        for k, ref in ent_refs.items():
            if ref.current:
                ref.current.value = next_numero_be() if k == "numero_be" else (
                    date.today().isoformat() if k == "date_entree" else "")
                try:
                    ref.current.update()
                except RuntimeError:
                    pass
        form = _ent_form.current
        if form:
            form.visible = True
            try:
                form.update()
            except RuntimeError:
                pass

    def build_entrees() -> None:
        form_col = ft.Column(
            ref=_ent_form, visible=False,
            controls=[
                ft.Divider(color=BORDER),
                _section_title("Bon d'Entrée", ft.Icons.MOVE_TO_INBOX_OUTLINED, SUCCESS),
                ft.Row(controls=[
                    _field("N° BE *", ent_refs["numero_be"], width=140),
                    _field("Date Entrée *", ent_refs["date_entree"], width=130),
                    _field("Code Article *", ent_refs["code_article"], width=140),
                    _field("Désignation", ent_refs["designation"], width=260),
                    _field("Catégorie", ent_refs["categorie"], width=140),
                ], spacing=8, wrap=True),
                ft.Row(controls=[
                    _field("Quantité *", ent_refs["quantite"], width=100),
                    _field("Unité", ent_refs["unite"], width=80),
                    _field("Prix Unitaire (FCFA)", ent_refs["prix_unitaire"], width=160),
                    _field("Fournisseur", ent_refs["fournisseur"], width=200),
                    _field("N° BL Fournisseur", ent_refs["numero_bl"], width=140),
                    _field("N° Commande", ent_refs["numero_commande"], width=130),
                    _field("Réceptionné par", ent_refs["receptionne_par"], width=160),
                ], spacing=8, wrap=True),
                _field("Observations", ent_refs["observations"], multiline=True),
                ft.Row(controls=[
                    ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                      bgcolor=SUCCESS, color="#FFFFFF", on_click=_ent_save),
                    ft.OutlinedButton("Annuler", style=ft.ButtonStyle(
                        color={ft.ControlState.DEFAULT: MUTED}, side=ft.BorderSide(1, BORDER)),
                        on_click=lambda e: (setattr(_ent_form.current, 'visible', False), _ent_form.current.update())),
                ], spacing=8),
            ], spacing=10,
        )
        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Registre des Entrées", ft.Icons.MOVE_TO_INBOX_OUTLINED, SUCCESS),
                    ft.Container(expand=True),
                    ft.TextField(ref=_ent_search, hint_text="Rechercher...",
                                 bgcolor=FIELD, color=TEXT, border_color=BORDER,
                                 focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=MUTED),
                                 width=200, height=38, text_size=12,
                                 on_submit=lambda e: _ent_load()),
                    ft.ElevatedButton("Nouveau BE", icon=ft.Icons.ADD,
                                      bgcolor=SUCCESS, color="#FFFFFF",
                                      on_click=lambda e: _ent_new()),
                ], spacing=8),
                form_col,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_ent_table, spacing=6),
            ], spacing=10)),
        ]
        _ent_load()

    # ── TAB: SORTIES ──────────────────────────────────────────────────────────
    _sor_search = ft.Ref[ft.TextField]()
    _sor_table  = ft.Ref[ft.Column]()
    _sor_form   = ft.Ref[ft.Column]()
    sor_refs = {k: ft.Ref[ft.TextField]() for k in [
        "numero_bs", "date_sortie", "code_article", "designation",
        "categorie", "quantite", "unite", "prix_unitaire",
        "site_chantier", "reference_forage", "demandeur", "autorise_par", "motif_sortie",
    ]}
    _sor_editing: dict[str, Any] = {}

    def _sor_row(s: dict) -> ft.Container:
        return ft.Container(
            bgcolor=CARD2, border=ft.border.all(1, DANGER + "33"), border_radius=8, padding=10,
            content=ft.Row(controls=[
                ft.Container(width=4, bgcolor=DANGER, border_radius=2, height=40),
                ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(str(s.get("numero_bs") or ""), color=DANGER, size=10, weight=ft.FontWeight.BOLD, width=110),
                        ft.Text(str(s.get("date_sortie") or "")[:10], color=MUTED, size=10, width=90),
                        ft.Text(f"[{s.get('code_article') or ''}]", color=PRIMARY, size=10, width=90),
                        ft.Text(str(s.get("designation") or ""), color=TEXT, size=11, expand=True),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Text(f"Qté: {s.get('quantite') or 0:.0f} {s.get('unite') or ''}", color=TEXT, size=10, width=110),
                        ft.Text(f"Site: {s.get('site_chantier') or '-'}", color=MUTED, size=10, width=140),
                        ft.Text(f"Dem.: {s.get('demandeur') or '-'}", color=MUTED, size=10, expand=True),
                        ft.Text(f"Total: {_fmt_fcfa(float(s.get('valeur_totale') or 0))}", color=GOLD, size=10, weight=ft.FontWeight.BOLD),
                    ], spacing=8),
                ], spacing=3, expand=True, tight=True),
                ft.Row(controls=[
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                  on_click=lambda ev, x=s: _sor_edit(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                  on_click=lambda ev, x=s: _sor_delete(x["id_sortie"])),
                ], spacing=0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _sor_load() -> None:
        q = str(_sor_search.current.value or "") if _sor_search.current else ""
        sors = list_sorties(search=q)
        col = _sor_table.current
        if col:
            col.controls = [_sor_row(s) for s in sors] or [ft.Text("Aucune sortie.", color=MUTED, size=12)]
            try:
                col.update()
            except RuntimeError:
                pass

    def _sor_edit(s: dict) -> None:
        _sor_editing.clear()
        _sor_editing.update(s)
        for k, ref in sor_refs.items():
            if ref.current:
                ref.current.value = str(s.get(k) or "")
                try:
                    ref.current.update()
                except RuntimeError:
                    pass
        form = _sor_form.current
        if form:
            form.visible = True
            try:
                form.update()
            except RuntimeError:
                pass

    def _sor_delete(sid: int) -> None:
        try:
            delete_sortie(sid)
            notify("Sortie supprimée.")
            _sor_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _sor_save(e: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in sor_refs.items()}
        if _sor_editing:
            data["id_sortie"] = _sor_editing["id_sortie"]
        try:
            save_sortie(data)
            notify("Bon de sortie enregistré.")
            _sor_editing.clear()
            form = _sor_form.current
            if form:
                form.visible = False
                try:
                    form.update()
                except RuntimeError:
                    pass
            _sor_load()
            _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _sor_new() -> None:
        _sor_editing.clear()
        for k, ref in sor_refs.items():
            if ref.current:
                ref.current.value = next_numero_bs() if k == "numero_bs" else (
                    date.today().isoformat() if k == "date_sortie" else "")
                try:
                    ref.current.update()
                except RuntimeError:
                    pass
        form = _sor_form.current
        if form:
            form.visible = True
            try:
                form.update()
            except RuntimeError:
                pass

    def build_sorties() -> None:
        form_col = ft.Column(
            ref=_sor_form, visible=False,
            controls=[
                ft.Divider(color=BORDER),
                _section_title("Bon de Sortie", ft.Icons.OUTBOX_OUTLINED, DANGER),
                ft.Row(controls=[
                    _field("N° BS *", sor_refs["numero_bs"], width=140),
                    _field("Date Sortie *", sor_refs["date_sortie"], width=130),
                    _field("Code Article *", sor_refs["code_article"], width=140),
                    _field("Désignation", sor_refs["designation"], width=260),
                    _field("Catégorie", sor_refs["categorie"], width=140),
                ], spacing=8, wrap=True),
                ft.Row(controls=[
                    _field("Quantité *", sor_refs["quantite"], width=100),
                    _field("Unité", sor_refs["unite"], width=80),
                    _field("Prix Unitaire (FCFA)", sor_refs["prix_unitaire"], width=160),
                    _field("Site / Chantier", sor_refs["site_chantier"], width=180),
                    _field("Réf. Forage", sor_refs["reference_forage"], width=140),
                    _field("Demandeur", sor_refs["demandeur"], width=160),
                    _field("Autorisé par", sor_refs["autorise_par"], width=140),
                    _field("Motif de Sortie", sor_refs["motif_sortie"], width=200),
                ], spacing=8, wrap=True),
                ft.Row(controls=[
                    ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                      bgcolor=DANGER, color="#FFFFFF", on_click=_sor_save),
                    ft.OutlinedButton("Annuler", style=ft.ButtonStyle(
                        color={ft.ControlState.DEFAULT: MUTED}, side=ft.BorderSide(1, BORDER)),
                        on_click=lambda e: (setattr(_sor_form.current, 'visible', False), _sor_form.current.update())),
                ], spacing=8),
            ], spacing=10,
        )
        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Registre des Sorties", ft.Icons.OUTBOX_OUTLINED, DANGER),
                    ft.Container(expand=True),
                    ft.TextField(ref=_sor_search, hint_text="Rechercher...",
                                 bgcolor=FIELD, color=TEXT, border_color=BORDER,
                                 focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=MUTED),
                                 width=200, height=38, text_size=12,
                                 on_submit=lambda e: _sor_load()),
                    ft.ElevatedButton("Nouveau BS", icon=ft.Icons.ADD,
                                      bgcolor=DANGER, color="#FFFFFF",
                                      on_click=lambda e: _sor_new()),
                ], spacing=8),
                form_col,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_sor_table, spacing=6),
            ], spacing=10)),
        ]
        _sor_load()

    # ── TAB: STOCK ACTUEL ─────────────────────────────────────────────────────
    def build_stock() -> None:
        rows = get_stock_actuel()
        total_val = sum(float(r.get("valeur_stock") or 0) for r in rows)

        def _stock_row(r: dict) -> ft.Container:
            stock = float(r.get("stock_actuel") or 0)
            alerte = float(r.get("stock_alerte") or 0)
            min_s  = float(r.get("stock_min") or 0)
            color  = DANGER if stock <= min_s else (WARNING if stock <= alerte else SUCCESS)
            pct = max(0, min(100, int(stock / max(float(r.get("stock_max") or 1), 0.001) * 100)))
            return ft.Container(
                bgcolor=CARD2, border=ft.border.all(1, color + "33"),
                border_radius=8, padding=10,
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Container(width=4, bgcolor=color, border_radius=2, height=30),
                        ft.Text(f"[{r['code_article']}]", color=PRIMARY, size=10, weight=ft.FontWeight.BOLD, width=90),
                        ft.Text(str(r["designation"] or ""), color=TEXT, size=11, expand=True),
                        ft.Text(str(r.get("categorie") or ""), color=MUTED, size=10, width=120),
                        ft.Text(f"Stock: {stock:.0f} {r.get('unite') or ''}", color=color, size=11, weight=ft.FontWeight.BOLD, width=100),
                        ft.Text(f"Valeur: {_fmt_fcfa(float(r.get('valeur_stock') or 0))}", color=GOLD, size=10, width=140),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Text(f"Entrées: {r.get('total_entrees') or 0:.0f}", color=SUCCESS, size=9, width=90),
                        ft.Text(f"Sorties: {r.get('total_sorties') or 0:.0f}", color=DANGER, size=9, width=90),
                        ft.Text(f"Min: {min_s:.0f}", color=MUTED, size=9, width=60),
                        ft.Text(f"Max: {r.get('stock_max') or 0:.0f}", color=MUTED, size=9, width=60),
                        ft.Container(
                            expand=True,
                            content=ft.Column(controls=[
                                ft.ProgressBar(value=pct / 100, bgcolor=BORDER, color=color, height=4),
                            ]),
                        ),
                        ft.Text(f"{pct}%", color=color, size=9, width=32),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=4, tight=True),
            )

        alerts = [r for r in rows if float(r.get("stock_actuel") or 0) <= float(r.get("stock_alerte") or 0)]

        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("État du Stock Actuel", ft.Icons.WAREHOUSE_OUTLINED, GOLD),
                    ft.Container(expand=True),
                    ft.Container(
                        bgcolor=GOLD + "22", border=ft.border.all(1, GOLD + "55"), border_radius=8,
                        padding=ft.padding.symmetric(horizontal=14, vertical=6),
                        content=ft.Text(f"Valeur totale stock : {_fmt_fcfa(total_val)}",
                                        color=GOLD, size=12, weight=ft.FontWeight.BOLD),
                    ),
                    _alert_badge(len(alerts), DANGER),
                ], spacing=8),
                ft.Divider(color=BORDER, height=1),
                ft.Column(
                    controls=[_stock_row(r) for r in rows] or [
                        ft.Text("Aucun article en catalogue.", color=MUTED, size=12)
                    ],
                    spacing=6,
                ),
            ], spacing=10)),
        ]

    # ── Navigation tabs ───────────────────────────────────────────────────────
    tabs_def = [
        ("dashboard",    "Tableau de bord", ft.Icons.DASHBOARD_OUTLINED,    GOLD),
        ("catalogue",    "Catalogue",        ft.Icons.INVENTORY_OUTLINED,    PRIMARY),
        ("fournisseurs", "Fournisseurs",     ft.Icons.BUSINESS_OUTLINED,     PRIMARY),
        ("entrees",      "Entrées",          ft.Icons.MOVE_TO_INBOX_OUTLINED,SUCCESS),
        ("sorties",      "Sorties",          ft.Icons.OUTBOX_OUTLINED,       DANGER),
        ("stock",        "Stock Actuel",     ft.Icons.WAREHOUSE_OUTLINED,    WARNING),
    ]
    tab_buttons: dict[str, ft.TextButton] = {}

    def set_tab(key: str) -> None:
        state["tab"] = key
        for k, btn in tab_buttons.items():
            selected = k == key
            _, lbl, ic, col = next(t for t in tabs_def if t[0] == k)
            btn.style = ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: col if selected else MUTED},
                bgcolor={ft.ControlState.DEFAULT: col + "22" if selected else "transparent"},
            )
            try:
                btn.update()
            except RuntimeError:
                pass
        {
            "dashboard":    build_dashboard,
            "catalogue":    build_catalogue,
            "fournisseurs": build_fournisseurs,
            "entrees":      build_entrees,
            "sorties":      build_sorties,
            "stock":        build_stock,
        }[key]()
        try:
            content_area.update()
        except RuntimeError:
            pass

    for key, label, icon, color in tabs_def:
        btn = ft.TextButton(
            label, icon=icon,
            style=ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: MUTED},
                bgcolor={ft.ControlState.DEFAULT: "transparent"},
            ),
            on_click=lambda e, k=key: set_tab(k),
        )
        tab_buttons[key] = btn

    header = ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=10,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=44, height=44, bgcolor=GOLD + "22", border_radius=8,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.STORE_OUTLINED, color=GOLD, size=26),
                ),
                ft.Column(controls=[
                    ft.Text("Gestion du Magasin", color=TEXT, size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("Diamond Drilling — Catalogue | Entrées | Sorties | Stock", color=MUTED, size=11),
                ], spacing=2, tight=True),
                ft.Container(expand=True),
                status_text,
                ft.ElevatedButton(
                    "Exporter XLS",
                    icon=ft.Icons.DOWNLOAD_OUTLINED,
                    bgcolor=GOLD,
                    color=NAVY,
                    on_click=lambda e: _do_export(),
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    tab_bar = ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row(
            controls=list(tab_buttons.values()),
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    root = ft.Container(
        bgcolor=BG,
        expand=True,
        padding=12,
        content=ft.Column(
            controls=[header, tab_bar, content_area],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    def _do_export() -> None:
        try:
            notify("Export en cours...", WARNING)
            path = export_magasin_xlsx()
            notify(f"Export créé : {path.name}", SUCCESS)
            _upd()
        except Exception as exc:
            notify(f"Erreur export : {exc}", DANGER)

    set_tab("dashboard")
    return root
