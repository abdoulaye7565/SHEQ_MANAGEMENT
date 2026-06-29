"""maintenance_indus.py — Module Gestion Maintenance Industrielle.

Onglets : Dashboard | Équipements | Plan PM | Interventions (OT) | Pièces | Indicateurs
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import flet as ft

from app.services.maintenance_indus_service import (
    delete_equipement, delete_intervention, delete_piece,
    delete_plan_pm, delete_prestataire,
    get_indicateurs_mtbf, get_maintenance_dashboard,
    list_equipements, list_familles, list_interventions,
    list_pieces, list_plan_pm, list_prestataires,
    next_numero_ot, save_equipement, save_intervention,
    save_piece, save_plan_pm, save_prestataire, valider_pm,
    cloture_intervention,
)

_log = logging.getLogger(__name__)

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0F172A"
CARD    = "#1E293B"
CARD2   = "#162032"
BORDER  = "#334155"
TEXT    = "#F1F5F9"
MUTED   = "#94A3B8"
PRIMARY = "#3B82F6"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER  = "#EF4444"
GOLD    = "#C8A400"
NAVY    = "#0D1B2A"
TEAL    = "#14B8A6"
PURPLE  = "#8B5CF6"
ORANGE  = "#F97316"
FIELD   = "#0F172A"

TYPES_MAINT = [
    "Préventive systématique", "Préventive conditionnelle",
    "Corrective urgente", "Corrective planifiée",
    "Améliorative", "Prédictive",
]
FREQUENCES  = ["Journalier","Hebdomadaire","Mensuel","Trimestriel",
               "Semestriel","Annuel","1 000 h","2 500 h","5 000 h","10 000 h"]
STATUTS_OT  = ["Ouvert","En cours","Cloture"]
STATUTS_EQ  = ["En service","Maintenance","Arret","Reforme"]

TYPE_COLORS = {
    "Préventive systématique":  SUCCESS,
    "Préventive conditionnelle": TEAL,
    "Corrective urgente":        DANGER,
    "Corrective planifiée":      WARNING,
    "Améliorative":              PURPLE,
    "Prédictive":                PRIMARY,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_fcfa(v: float) -> str:
    return f"{v:,.0f} F".replace(",", " ")

def _card(content: ft.Control, padding: int = 14) -> ft.Container:
    return ft.Container(
        bgcolor=CARD, border=ft.border.all(1, BORDER),
        border_radius=10, padding=padding, content=content,
    )

def _section_title(text: str, icon: str, color: str = PRIMARY) -> ft.Row:
    return ft.Row(controls=[
        ft.Icon(icon, color=color, size=18),
        ft.Text(text, color=TEXT, size=15, weight=ft.FontWeight.BOLD),
    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

def _badge(text: str, color: str) -> ft.Container:
    return ft.Container(
        bgcolor=color + "22", border=ft.border.all(1, color + "55"),
        border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(text, color=color, size=10, weight=ft.FontWeight.BOLD),
    )

def _kpi(title: str, value: str, subtitle: str, color: str, icon: str,
         width: int = 230) -> ft.Container:
    return ft.Container(
        bgcolor=CARD2, border=ft.border.all(1, color + "44"),
        border_radius=10, padding=14, width=width,
        content=ft.Column(controls=[
            ft.Row(controls=[
                ft.Container(
                    width=34, height=34, bgcolor=color + "22", border_radius=8,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color=color, size=18),
                ),
                ft.Column(controls=[
                    ft.Text(title, color=MUTED, size=9),
                    ft.Text(value, color=color, size=16, weight=ft.FontWeight.BOLD),
                ], spacing=1, tight=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(subtitle, color=MUTED, size=9),
        ], spacing=5, tight=True),
    )

def _field(label: str, ref: ft.Ref, multiline: bool = False,
           width: int | None = None) -> ft.TextField:
    return ft.TextField(
        label=label, ref=ref, bgcolor=FIELD, color=TEXT,
        border_color=BORDER, focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=MUTED),
        multiline=multiline, min_lines=3 if multiline else 1,
        max_lines=5 if multiline else 1, width=width, text_size=12,
    )

def _dd(label: str, ref: ft.Ref, options: list[str],
        width: int | None = None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label, ref=ref, bgcolor=FIELD, color=TEXT,
        border_color=BORDER, focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=MUTED),
        width=width, text_size=12,
        options=[ft.dropdown.Option("", "— Choisir —")] +
                [ft.dropdown.Option(o, o) for o in options],
    )

def _alert_badge(count: int, color: str = DANGER) -> ft.Container:
    return ft.Container(
        bgcolor=color, border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        content=ft.Text(str(count), color="#FFFFFF", size=10,
                        weight=ft.FontWeight.BOLD),
        visible=count > 0,
    )


# ── Page principale ───────────────────────────────────────────────────────────

def maintenance_indus_page(page: Any = None) -> ft.Control:
    from app.services.maintenance_indus_export import export_maintenance_xlsx

    state: dict[str, Any] = {"tab": "dashboard"}
    status_ref = ft.Ref[ft.Text]()
    content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)

    def notify(msg: str, color: str = SUCCESS) -> None:
        if status_ref.current:
            status_ref.current.value = msg
            status_ref.current.color = color
            try:
                status_ref.current.update()
            except RuntimeError:
                pass

    def _upd() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def _do_export() -> None:
        try:
            notify("Export en cours...", WARNING)
            path = export_maintenance_xlsx()
            notify(f"Export : {path.name}", SUCCESS)
            _upd()
        except Exception as exc:
            notify(f"Erreur export : {exc}", DANGER)

    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    def build_dashboard() -> None:
        try:
            dash = get_maintenance_dashboard()
        except Exception as exc:
            _log.warning("[maint_ui] dashboard: %s", exc)
            dash = {}

        ratio_pm = dash.get("ratio_pm", 0)
        ratio_color = SUCCESS if ratio_pm >= 70 else (WARNING if ratio_pm >= 50 else DANGER)

        kpi_row = ft.Row(controls=[
            _kpi("Équipements actifs",
                 f"{dash.get('nb_eq_actif',0)}/{dash.get('nb_equipements',0)}",
                 "En service / Total", TEAL, ft.Icons.ENGINEERING_OUTLINED),
            _kpi("OT en cours",
                 str(dash.get("nb_ot_open", 0)),
                 f"YTD: {dash.get('nb_ot_ytd',0)} OT", WARNING, ft.Icons.BUILD_CIRCLE_OUTLINED),
            _kpi("Coût maintenance YTD",
                 f"{dash.get('cout_ytd',0)/1000000:.1f} M F",
                 f"PM:{dash.get('nb_pm_ytd',0)} CM:{dash.get('nb_cm_ytd',0)}", GOLD,
                 ft.Icons.MONETIZATION_ON_OUTLINED),
            _kpi("Arrêts pannes YTD",
                 f"{dash.get('h_arret_ytd',0):.0f} h",
                 "Heures d'immobilisation", DANGER, ft.Icons.TIMER_OFF_OUTLINED),
            _kpi("Ratio PM/CM",
                 f"{ratio_pm:.0f}%",
                 "Objectif ≥ 70% préventif", ratio_color, ft.Icons.PIE_CHART_OUTLINED),
            _kpi("Alertes pièces",
                 str(dash.get("nb_alerte_pieces", 0)),
                 "Stock sous seuil minimum", DANGER if dash.get("nb_alerte_pieces",0) > 0 else SUCCESS,
                 ft.Icons.WARNING_AMBER_OUTLINED),
        ], spacing=10, wrap=True)

        # PM échus
        pm_echus = dash.get("pm_echus", [])
        pm_rows = []
        for p in pm_echus[:8]:
            crit = str(p.get("criticite") or "B")
            crit_color = DANGER if crit == "A" else (WARNING if crit == "B" else TEAL)
            pm_rows.append(ft.Container(
                bgcolor=CARD2, border=ft.border.all(1, crit_color + "44"),
                border_radius=6, padding=8,
                content=ft.Row(controls=[
                    _badge(crit, crit_color),
                    ft.Text(str(p.get("code_equipement","")), color=PRIMARY, size=10, width=80),
                    ft.Text(str(p.get("designation_eq","")), color=TEXT, size=11, width=180),
                    ft.Text(str(p.get("tache","")), color=MUTED, size=10, width=200),
                    ft.Text(str(p.get("frequence","")), color=TEAL, size=10, width=100),
                    ft.Text(f"Échu : {p.get('prochaine_echeance','')}", color=DANGER, size=10),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))

        # Alertes pièces
        alerte_pieces = dash.get("alerte_pieces", [])
        ap_rows = []
        for a in alerte_pieces[:6]:
            crit = str(a.get("criticite") or "B")
            c = DANGER if crit == "A" else WARNING
            ap_rows.append(ft.Container(
                bgcolor=CARD2, border=ft.border.all(1, c + "44"),
                border_radius=6, padding=8,
                content=ft.Row(controls=[
                    _badge(crit, c),
                    ft.Text(str(a.get("code_piece","")), color=GOLD, size=10, width=90),
                    ft.Text(str(a.get("designation","")), color=TEXT, size=11, width=220),
                    ft.Text(
                        f"Stock: {float(a.get('stock_actuel') or 0):.0f}  |  Min: {float(a.get('stock_min') or 0):.0f}",
                        color=c, size=10, weight=ft.FontWeight.BOLD,
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))

        # Récents OT
        recent = dash.get("recent_ot", [])
        recent_rows = []
        for r in recent:
            t = str(r.get("type_maintenance",""))
            tc = TYPE_COLORS.get(t, MUTED)
            recent_rows.append(ft.Container(
                bgcolor=CARD2, border_radius=6, padding=8,
                content=ft.Row(controls=[
                    ft.Text(str(r.get("numero_ot","")), color=tc, size=10, weight=ft.FontWeight.BOLD, width=120),
                    ft.Text(str(r.get("date_ouverture",""))[:10], color=MUTED, size=10, width=90),
                    ft.Text(str(r.get("designation_eq","")), color=TEXT, size=11, width=180),
                    ft.Container(expand=True),
                    _badge(str(r.get("statut","")).upper(), SUCCESS if "lôt" in str(r.get("statut","")) else WARNING),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))

        # Mouvements mensuels
        monthly = dash.get("monthly", [])
        month_rows_w = []
        for m in monthly:
            nb_pm = int(m.get("nb_pm") or 0)
            nb_cm = int(m.get("nb_cm") or 0)
            if nb_pm == 0 and nb_cm == 0:
                continue
            month_rows_w.append(ft.Container(
                bgcolor=CARD2, border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                content=ft.Row(controls=[
                    ft.Text(m["mois"], color=TEXT, size=11, weight=ft.FontWeight.BOLD, width=40),
                    ft.Container(width=90, content=ft.Text(f"PM: {nb_pm}", color=SUCCESS, size=10, text_align=ft.TextAlign.RIGHT)),
                    ft.Container(width=90, content=ft.Text(f"CM: {nb_cm}", color=DANGER, size=10, text_align=ft.TextAlign.RIGHT)),
                    ft.Container(width=110, content=ft.Text(f"Arrêt: {float(m.get('h_arret') or 0):.0f}h", color=WARNING, size=10, text_align=ft.TextAlign.RIGHT)),
                    ft.Container(width=130, content=ft.Text(f"Coût: {_fmt_fcfa(float(m.get('cout') or 0))}", color=GOLD, size=10, text_align=ft.TextAlign.RIGHT)),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))

        content_area.controls = [
            _card(ft.Column(controls=[
                _section_title("Tableau de bord Maintenance Industrielle",
                               ft.Icons.HANDYMAN_OUTLINED, GOLD),
                kpi_row,
            ], spacing=12)),
            ft.Row(controls=[
                ft.Container(expand=True, content=_card(ft.Column(controls=[
                    ft.Row(controls=[
                        _section_title("PM Échus — Action requise", ft.Icons.ALARM_OUTLINED, DANGER),
                        ft.Container(expand=True),
                        _alert_badge(len(pm_echus), DANGER),
                    ], spacing=8),
                    ft.Divider(color=BORDER, height=1),
                    *(pm_rows if pm_rows else [
                        ft.Row(controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=18),
                            ft.Text("Aucun PM échu", color=SUCCESS, size=12),
                        ], spacing=6)
                    ]),
                ], spacing=6))),
                ft.Container(expand=True, content=_card(ft.Column(controls=[
                    ft.Row(controls=[
                        _section_title("Alertes Pièces de Rechange", ft.Icons.WARNING_AMBER_OUTLINED, WARNING),
                        ft.Container(expand=True),
                        _alert_badge(len(alerte_pieces), WARNING),
                    ], spacing=8),
                    ft.Divider(color=BORDER, height=1),
                    *(ap_rows if ap_rows else [
                        ft.Row(controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=18),
                            ft.Text("Stocks OK", color=SUCCESS, size=12),
                        ], spacing=6)
                    ]),
                ], spacing=6))),
            ], spacing=12),
            ft.Row(controls=[
                ft.Container(expand=True, content=_card(ft.Column(controls=[
                    _section_title("Derniers Ordres de Travail", ft.Icons.ASSIGNMENT_OUTLINED, PRIMARY),
                    ft.Divider(color=BORDER, height=1),
                    *(recent_rows if recent_rows else [ft.Text("Aucun OT.", color=MUTED, size=11)]),
                ], spacing=6))),
                ft.Container(expand=True, content=_card(ft.Column(controls=[
                    _section_title(f"Mouvements {date.today().year}", ft.Icons.BAR_CHART_OUTLINED, TEAL),
                    ft.Divider(color=BORDER, height=1),
                    ft.Row(controls=[
                        ft.Text("Mois", color=MUTED, size=10, width=40),
                        ft.Container(width=90, content=ft.Text("PM", color=SUCCESS, size=10, text_align=ft.TextAlign.RIGHT)),
                        ft.Container(width=90, content=ft.Text("CM", color=DANGER, size=10, text_align=ft.TextAlign.RIGHT)),
                        ft.Container(width=110, content=ft.Text("Arrêts", color=WARNING, size=10, text_align=ft.TextAlign.RIGHT)),
                        ft.Container(width=130, content=ft.Text("Coût FCFA", color=GOLD, size=10, text_align=ft.TextAlign.RIGHT)),
                    ], spacing=6),
                    *(month_rows_w if month_rows_w else [ft.Text("Aucun mouvement.", color=MUTED, size=11)]),
                ], spacing=4))),
            ], spacing=12),
        ]

    # ── ÉQUIPEMENTS ───────────────────────────────────────────────────────────
    _eq_search = ft.Ref[ft.TextField]()
    _eq_table  = ft.Ref[ft.Column]()
    _eq_form   = ft.Ref[ft.Column]()
    _eq_editing: dict = {}
    eq_refs = {k: ft.Ref[ft.TextField]() for k in [
        "code_equipement","designation","famille","sous_famille",
        "criticite","site_zone","emplacement","marque","modele",
        "numero_serie","date_mise_en_service","capacite_puissance",
        "fournisseur","valeur_remplacement","statut","observations",
    ]}
    eq_crit_ref   = ft.Ref[ft.Dropdown]()
    eq_statut_ref = ft.Ref[ft.Dropdown]()

    def _eq_row(e: dict) -> ft.Container:
        crit = str(e.get("criticite","B"))
        crit_c = DANGER if crit == "A" else (WARNING if crit == "B" else TEAL)
        statut = str(e.get("statut","En service"))
        stat_c = SUCCESS if "service" in statut else (WARNING if "Maint" in statut else DANGER)
        return ft.Container(
            bgcolor=CARD2, border=ft.border.all(1, crit_c + "33"),
            border_radius=8, padding=10,
            content=ft.Row(controls=[
                ft.Container(width=4, bgcolor=crit_c, border_radius=2, height=44),
                ft.Column(controls=[
                    ft.Row(controls=[
                        _badge(crit, crit_c),
                        ft.Text(f"[{e.get('code_equipement','')}]", color=PRIMARY, size=10,
                                weight=ft.FontWeight.BOLD, width=90),
                        ft.Text(str(e.get("designation","")), color=TEXT, size=12, width=220),
                        ft.Text(str(e.get("famille","")), color=MUTED, size=10, width=140),
                        ft.Container(expand=True),
                        _badge(statut, stat_c),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, color=MUTED, size=12),
                        ft.Text(f"{e.get('site_zone','')} — {e.get('emplacement','')}", color=MUTED, size=10, width=200),
                        ft.Text(f"{e.get('marque','')} {e.get('modele','')}", color=MUTED, size=10, width=160),
                        ft.Text(f"Valeur: {_fmt_fcfa(float(e.get('valeur_remplacement') or 0))}", color=GOLD, size=10),
                    ], spacing=6),
                ], spacing=3, expand=True, tight=True),
                ft.Row(controls=[
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                  on_click=lambda ev, x=e: _eq_edit(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                  on_click=lambda ev, x=e: _eq_delete(x["code_equipement"])),
                ], spacing=0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _eq_load() -> None:
        q = str(_eq_search.current.value or "") if _eq_search.current else ""
        rows = list_equipements(search=q)
        col  = _eq_table.current
        if col:
            col.controls = [_eq_row(e) for e in rows] or [
                ft.Text("Aucun équipement.", color=MUTED, size=12)]
            try:
                col.update()
            except RuntimeError:
                pass

    def _eq_edit(e: dict) -> None:
        _eq_editing.clear()
        _eq_editing.update(e)
        for k, ref in eq_refs.items():
            if ref.current:
                ref.current.value = str(e.get(k) or "")
                try:
                    ref.current.update()
                except RuntimeError:
                    pass
        if eq_crit_ref.current:
            eq_crit_ref.current.value = str(e.get("criticite","B"))
            try: eq_crit_ref.current.update()
            except RuntimeError: pass
        if eq_statut_ref.current:
            eq_statut_ref.current.value = str(e.get("statut","En service"))
            try: eq_statut_ref.current.update()
            except RuntimeError: pass
        f = _eq_form.current
        if f:
            f.visible = True
            try: f.update()
            except RuntimeError: pass

    def _eq_delete(code: str) -> None:
        try:
            delete_equipement(code)
            notify(f"Équipement {code} supprimé.")
            _eq_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _eq_save(ev: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in eq_refs.items()}
        if eq_crit_ref.current:
            data["criticite"] = eq_crit_ref.current.value or "B"
        if eq_statut_ref.current:
            data["statut"] = eq_statut_ref.current.value or "En service"
        if _eq_editing:
            data["code_equipement"] = _eq_editing["code_equipement"]
        try:
            code = save_equipement(data)
            notify(f"Équipement {code} enregistré.")
            _eq_editing.clear()
            f = _eq_form.current
            if f:
                f.visible = False
                try: f.update()
                except RuntimeError: pass
            _eq_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def build_equipements() -> None:
        form = ft.Column(ref=_eq_form, visible=False, spacing=10, controls=[
            ft.Divider(color=BORDER),
            _section_title("Fiche Équipement", ft.Icons.ENGINEERING_OUTLINED, TEAL),
            ft.Row(controls=[
                _field("Code Équipement *", eq_refs["code_equipement"], width=140),
                _field("Désignation *", eq_refs["designation"], width=280),
                _field("Famille", eq_refs["famille"], width=160),
                _field("Sous-famille", eq_refs["sous_famille"], width=160),
                _dd("Criticité", eq_crit_ref, ["A","B","C"], width=100),
                _dd("Statut", eq_statut_ref, STATUTS_EQ, width=150),
            ], spacing=8, wrap=True),
            ft.Row(controls=[
                _field("Site / Zone", eq_refs["site_zone"], width=160),
                _field("Emplacement", eq_refs["emplacement"], width=160),
                _field("Marque", eq_refs["marque"], width=130),
                _field("Modèle", eq_refs["modele"], width=130),
                _field("N° Série", eq_refs["numero_serie"], width=160),
                _field("Date MES (AAAA-MM-JJ)", eq_refs["date_mise_en_service"], width=170),
                _field("Capacité / Puissance", eq_refs["capacite_puissance"], width=160),
            ], spacing=8, wrap=True),
            ft.Row(controls=[
                _field("Fournisseur", eq_refs["fournisseur"], width=200),
                _field("Valeur remplacement (FCFA)", eq_refs["valeur_remplacement"], width=200),
            ], spacing=8),
            _field("Observations", eq_refs["observations"], multiline=True),
            ft.Row(controls=[
                ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                  bgcolor=SUCCESS, color="#FFFFFF", on_click=_eq_save),
                ft.OutlinedButton("Annuler",
                                  style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: MUTED},
                                                       side=ft.BorderSide(1, BORDER)),
                                  on_click=lambda e: (setattr(_eq_form.current,"visible",False),
                                                      _eq_form.current.update())),
            ], spacing=8),
        ])
        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Registre Équipements", ft.Icons.PRECISION_MANUFACTURING_OUTLINED, TEAL),
                    ft.Container(expand=True),
                    ft.TextField(ref=_eq_search, hint_text="Rechercher...",
                                 bgcolor=FIELD, color=TEXT, border_color=BORDER,
                                 focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=MUTED),
                                 width=200, height=38, text_size=12,
                                 on_submit=lambda e: _eq_load()),
                    ft.ElevatedButton("Nouvel équipement", icon=ft.Icons.ADD,
                                      bgcolor=TEAL, color="#FFFFFF",
                                      on_click=lambda e: (_eq_editing.clear(),
                                                          [setattr(r.current,"value","") or r.current.update()
                                                           for r in eq_refs.values() if r.current],
                                                          setattr(_eq_form.current,"visible",True),
                                                          _eq_form.current.update())),
                ], spacing=8),
                form,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_eq_table, spacing=6),
            ], spacing=10)),
        ]
        _eq_load()

    # ── PLAN PM ───────────────────────────────────────────────────────────────
    _pm_table  = ft.Ref[ft.Column]()
    _pm_form   = ft.Ref[ft.Column]()
    _pm_editing: dict = {}
    pm_refs = {k: ft.Ref[ft.TextField]() for k in [
        "code_equipement","designation_eq","tache","derniere_realisation",
        "duree_h","ressources","pieces_necessaires","instructions","responsable",
    ]}
    pm_freq_ref = ft.Ref[ft.Dropdown]()
    _pm_filter_echu = ft.Ref[ft.Checkbox]()

    def _pm_row(p: dict) -> ft.Container:
        today = date.today().isoformat()
        proch = str(p.get("prochaine_echeance") or "")
        echu  = proch and proch < today
        color = DANGER if echu else SUCCESS
        freq  = str(p.get("frequence",""))
        freq_c = {
            "Journalier": TEAL, "Hebdomadaire": PRIMARY, "Mensuel": PURPLE,
            "Trimestriel": ORANGE, "Semestriel": WARNING, "Annuel": GOLD,
        }.get(freq, MUTED)
        return ft.Container(
            bgcolor=CARD2, border=ft.border.all(1, color + "33"),
            border_radius=8, padding=10,
            content=ft.Row(controls=[
                ft.Container(width=4, bgcolor=color, border_radius=2, height=44),
                ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(str(p.get("code_equipement","")), color=PRIMARY, size=10,
                                weight=ft.FontWeight.BOLD, width=80),
                        ft.Text(str(p.get("designation_eq","")), color=TEXT, size=11, width=180),
                        ft.Text(str(p.get("tache","")), color=MUTED, size=10, width=240),
                        ft.Container(expand=True),
                        _badge(freq, freq_c),
                        _badge("ÉCHU" if echu else "OK", DANGER if echu else SUCCESS),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=MUTED, size=11),
                        ft.Text(f"Dernière: {p.get('derniere_realisation','—')}", color=MUTED, size=10),
                        ft.Icon(ft.Icons.SCHEDULE_OUTLINED, color=color, size=11),
                        ft.Text(f"Prochaine: {proch or '—'}", color=color, size=10,
                                weight=ft.FontWeight.BOLD),
                        ft.Text(f"Durée: {p.get('duree_h','—')} h", color=MUTED, size=10),
                    ], spacing=6),
                ], spacing=3, expand=True, tight=True),
                ft.Row(controls=[
                    ft.IconButton(ft.Icons.CHECK_CIRCLE_OUTLINE, icon_color=SUCCESS, icon_size=18,
                                  tooltip="Valider PM réalisé",
                                  on_click=lambda ev, x=p: _pm_valider(x["id_plan"])),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                  on_click=lambda ev, x=p: _pm_edit(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                  on_click=lambda ev, x=p: _pm_delete(x["id_plan"])),
                ], spacing=0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _pm_load() -> None:
        echu_only = bool(_pm_filter_echu.current and _pm_filter_echu.current.value)
        rows = list_plan_pm(echu_seulement=echu_only)
        col  = _pm_table.current
        if col:
            col.controls = [_pm_row(p) for p in rows] or [
                ft.Text("Aucune tâche PM.", color=MUTED, size=12)]
            try: col.update()
            except RuntimeError: pass

    def _pm_edit(p: dict) -> None:
        _pm_editing.clear()
        _pm_editing.update(p)
        for k, ref in pm_refs.items():
            if ref.current:
                ref.current.value = str(p.get(k) or "")
                try: ref.current.update()
                except RuntimeError: pass
        if pm_freq_ref.current:
            pm_freq_ref.current.value = str(p.get("frequence","Mensuel"))
            try: pm_freq_ref.current.update()
            except RuntimeError: pass
        f = _pm_form.current
        if f:
            f.visible = True
            try: f.update()
            except RuntimeError: pass

    def _pm_delete(pid: int) -> None:
        try:
            delete_plan_pm(pid)
            notify("Tâche PM supprimée.")
            _pm_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _pm_valider(pid: int) -> None:
        try:
            valider_pm(pid, date.today().isoformat())
            notify("PM validé — prochaine échéance calculée.", SUCCESS)
            _pm_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _pm_save(ev: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in pm_refs.items()}
        if pm_freq_ref.current:
            data["frequence"] = pm_freq_ref.current.value or "Mensuel"
        if _pm_editing:
            data["id_plan"] = _pm_editing["id_plan"]
        try:
            save_plan_pm(data)
            notify("Tâche PM enregistrée.")
            _pm_editing.clear()
            f = _pm_form.current
            if f:
                f.visible = False
                try: f.update()
                except RuntimeError: pass
            _pm_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def build_plan_pm() -> None:
        form = ft.Column(ref=_pm_form, visible=False, spacing=10, controls=[
            ft.Divider(color=BORDER),
            _section_title("Tâche de Maintenance Préventive", ft.Icons.EVENT_REPEAT_OUTLINED, SUCCESS),
            ft.Row(controls=[
                _field("Code Équipement *", pm_refs["code_equipement"], width=140),
                _field("Désignation équipement", pm_refs["designation_eq"], width=260),
                _dd("Fréquence *", pm_freq_ref, FREQUENCES, width=160),
                _field("Durée (h)", pm_refs["duree_h"], width=80),
                _field("Responsable", pm_refs["responsable"], width=160),
            ], spacing=8, wrap=True),
            ft.Row(controls=[
                _field("Dernière réalisation (AAAA-MM-JJ)", pm_refs["derniere_realisation"], width=220),
                _field("Ressources requises", pm_refs["ressources"], width=220),
                _field("Pièces nécessaires", pm_refs["pieces_necessaires"], width=220),
            ], spacing=8, wrap=True),
            _field("Tâche *", pm_refs["tache"], width=None),
            _field("Instructions détaillées", pm_refs["instructions"], multiline=True),
            ft.Row(controls=[
                ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                  bgcolor=SUCCESS, color="#FFFFFF", on_click=_pm_save),
                ft.OutlinedButton("Annuler",
                                  style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: MUTED},
                                                       side=ft.BorderSide(1, BORDER)),
                                  on_click=lambda e: (setattr(_pm_form.current,"visible",False),
                                                      _pm_form.current.update())),
            ], spacing=8),
        ])
        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Plan de Maintenance Préventive", ft.Icons.EVENT_REPEAT_OUTLINED, SUCCESS),
                    ft.Container(expand=True),
                    ft.Checkbox(ref=_pm_filter_echu, label="Échus seulement",
                                label_style=ft.TextStyle(color=MUTED, size=11),
                                fill_color={ft.ControlState.SELECTED: DANGER},
                                on_change=lambda e: _pm_load()),
                    ft.ElevatedButton("Nouvelle tâche PM", icon=ft.Icons.ADD,
                                      bgcolor=SUCCESS, color="#FFFFFF",
                                      on_click=lambda e: (_pm_editing.clear(),
                                                          [setattr(r.current,"value","") or r.current.update()
                                                           for r in pm_refs.values() if r.current],
                                                          setattr(_pm_form.current,"visible",True),
                                                          _pm_form.current.update())),
                ], spacing=8),
                form,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_pm_table, spacing=6),
            ], spacing=10)),
        ]
        _pm_load()

    # ── INTERVENTIONS (OT) ────────────────────────────────────────────────────
    _ot_search   = ft.Ref[ft.TextField]()
    _ot_table    = ft.Ref[ft.Column]()
    _ot_form     = ft.Ref[ft.Column]()
    _ot_filter   = ft.Ref[ft.Dropdown]()
    _ot_editing: dict = {}
    ot_refs = {k: ft.Ref[ft.TextField]() for k in [
        "numero_ot","date_ouverture","date_cloture","code_equipement",
        "designation_eq","nature_panne","description_travaux","technicien",
        "temps_arret","duree_intervention","pieces_utilisees",
        "cout_mo","cout_pieces","observations",
    ]}
    ot_type_ref   = ft.Ref[ft.Dropdown]()
    ot_statut_ref = ft.Ref[ft.Dropdown]()

    def _ot_row(o: dict) -> ft.Container:
        t = str(o.get("type_maintenance",""))
        tc = TYPE_COLORS.get(t, MUTED)
        statut = str(o.get("statut",""))
        stat_c = SUCCESS if "lôt" in statut else (PRIMARY if "cours" in statut else WARNING)
        cout = float(o.get("cout_total") or 0)
        return ft.Container(
            bgcolor=CARD2, border=ft.border.all(1, tc + "33"),
            border_radius=8, padding=10,
            content=ft.Row(controls=[
                ft.Container(width=4, bgcolor=tc, border_radius=2, height=44),
                ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(str(o.get("numero_ot","")), color=tc, size=10,
                                weight=ft.FontWeight.BOLD, width=120),
                        ft.Text(str(o.get("date_ouverture",""))[:10], color=MUTED, size=10, width=90),
                        ft.Text(str(o.get("designation_eq","")), color=TEXT, size=11, width=200),
                        ft.Container(expand=True),
                        _badge(t[:20], tc),
                        _badge(statut, stat_c),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.PERSON_OUTLINED, color=MUTED, size=11),
                        ft.Text(str(o.get("technicien","—")), color=MUTED, size=10, width=140),
                        ft.Icon(ft.Icons.TIMER_OUTLINED, color=DANGER, size=11),
                        ft.Text(f"Arrêt: {float(o.get('temps_arret') or 0):.0f}h", color=DANGER, size=10, width=90),
                        ft.Text(f"Coût: {_fmt_fcfa(cout)}", color=GOLD, size=10,
                                weight=ft.FontWeight.BOLD),
                    ], spacing=6),
                ], spacing=3, expand=True, tight=True),
                ft.Row(controls=[
                    ft.IconButton(ft.Icons.CHECK_CIRCLE_OUTLINE, icon_color=SUCCESS, icon_size=18,
                                  tooltip="Clôturer OT",
                                  on_click=lambda ev, x=o: _ot_cloture(x["id_intervention"])),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                  on_click=lambda ev, x=o: _ot_edit(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                  on_click=lambda ev, x=o: _ot_delete(x["id_intervention"])),
                ], spacing=0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _ot_load() -> None:
        q = str(_ot_search.current.value or "") if _ot_search.current else ""
        statut_f = (_ot_filter.current.value or "") if _ot_filter.current else ""
        rows = list_interventions(search=q, statut=statut_f)
        col  = _ot_table.current
        if col:
            col.controls = [_ot_row(o) for o in rows] or [
                ft.Text("Aucune intervention.", color=MUTED, size=12)]
            try: col.update()
            except RuntimeError: pass

    def _ot_edit(o: dict) -> None:
        _ot_editing.clear()
        _ot_editing.update(o)
        for k, ref in ot_refs.items():
            if ref.current:
                ref.current.value = str(o.get(k) or "")
                try: ref.current.update()
                except RuntimeError: pass
        if ot_type_ref.current:
            ot_type_ref.current.value = str(o.get("type_maintenance",""))
            try: ot_type_ref.current.update()
            except RuntimeError: pass
        if ot_statut_ref.current:
            ot_statut_ref.current.value = str(o.get("statut","Ouvert"))
            try: ot_statut_ref.current.update()
            except RuntimeError: pass
        f = _ot_form.current
        if f:
            f.visible = True
            try: f.update()
            except RuntimeError: pass

    def _ot_delete(eid: int) -> None:
        try:
            delete_intervention(eid)
            notify("OT supprimé.")
            _ot_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _ot_cloture(eid: int) -> None:
        try:
            cloture_intervention(eid)
            notify("OT clôturé.", SUCCESS)
            _ot_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _ot_save(ev: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in ot_refs.items()}
        if ot_type_ref.current:
            data["type_maintenance"] = ot_type_ref.current.value or "Corrective urgente"
        if ot_statut_ref.current:
            data["statut"] = ot_statut_ref.current.value or "Ouvert"
        if _ot_editing:
            data["id_intervention"] = _ot_editing["id_intervention"]
        try:
            save_intervention(data)
            notify("OT enregistré.")
            _ot_editing.clear()
            f = _ot_form.current
            if f:
                f.visible = False
                try: f.update()
                except RuntimeError: pass
            _ot_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _ot_new() -> None:
        _ot_editing.clear()
        for k, ref in ot_refs.items():
            if ref.current:
                v = next_numero_ot() if k == "numero_ot" else (
                    date.today().isoformat() if k == "date_ouverture" else "")
                ref.current.value = v
                try: ref.current.update()
                except RuntimeError: pass
        f = _ot_form.current
        if f:
            f.visible = True
            try: f.update()
            except RuntimeError: pass

    def build_interventions() -> None:
        form = ft.Column(ref=_ot_form, visible=False, spacing=10, controls=[
            ft.Divider(color=BORDER),
            _section_title("Ordre de Travail", ft.Icons.BUILD_CIRCLE_OUTLINED, WARNING),
            ft.Row(controls=[
                _field("N° OT *", ot_refs["numero_ot"], width=140),
                _field("Date ouverture *", ot_refs["date_ouverture"], width=150),
                _field("Date clôture", ot_refs["date_cloture"], width=150),
                _field("Code équipement *", ot_refs["code_equipement"], width=140),
                _field("Désignation équipement", ot_refs["designation_eq"], width=240),
            ], spacing=8, wrap=True),
            ft.Row(controls=[
                _dd("Type maintenance *", ot_type_ref, TYPES_MAINT, width=230),
                _dd("Statut *", ot_statut_ref, STATUTS_OT, width=140),
                _field("Nature panne / tâche", ot_refs["nature_panne"], width=240),
                _field("Technicien", ot_refs["technicien"], width=180),
            ], spacing=8, wrap=True),
            _field("Description des travaux *", ot_refs["description_travaux"], multiline=True),
            ft.Row(controls=[
                _field("Temps arrêt (h)", ot_refs["temps_arret"], width=120),
                _field("Durée intervention (h)", ot_refs["duree_intervention"], width=150),
                _field("Pièces utilisées", ot_refs["pieces_utilisees"], width=260),
                _field("Coût MO (FCFA)", ot_refs["cout_mo"], width=150),
                _field("Coût pièces (FCFA)", ot_refs["cout_pieces"], width=150),
            ], spacing=8, wrap=True),
            _field("Observations", ot_refs["observations"], multiline=True),
            ft.Row(controls=[
                ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                  bgcolor=WARNING, color="#FFFFFF", on_click=_ot_save),
                ft.OutlinedButton("Annuler",
                                  style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: MUTED},
                                                       side=ft.BorderSide(1, BORDER)),
                                  on_click=lambda e: (setattr(_ot_form.current,"visible",False),
                                                      _ot_form.current.update())),
            ], spacing=8),
        ])
        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Registre des Interventions (OT)", ft.Icons.ASSIGNMENT_OUTLINED, WARNING),
                    ft.Container(expand=True),
                    ft.TextField(ref=_ot_search, hint_text="Rechercher...",
                                 bgcolor=FIELD, color=TEXT, border_color=BORDER,
                                 focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=MUTED),
                                 width=180, height=38, text_size=12,
                                 on_submit=lambda e: _ot_load()),
                    _dd("Statut", _ot_filter, STATUTS_OT, width=140),
                    ft.ElevatedButton("Nouvel OT", icon=ft.Icons.ADD,
                                      bgcolor=WARNING, color="#FFFFFF",
                                      on_click=lambda e: _ot_new()),
                ], spacing=8),
                form,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_ot_table, spacing=6),
            ], spacing=10)),
        ]
        _ot_load()

    # ── PIÈCES DE RECHANGE ────────────────────────────────────────────────────
    _pr_search = ft.Ref[ft.TextField]()
    _pr_table  = ft.Ref[ft.Column]()
    _pr_form   = ft.Ref[ft.Column]()
    _pr_filter_alerte = ft.Ref[ft.Checkbox]()
    _pr_editing: dict = {}
    pr_refs = {k: ft.Ref[ft.TextField]() for k in [
        "code_piece","designation","reference_fabricant","equipements_concernes",
        "unite","stock_actuel","stock_min","stock_max","emplacement_magasin",
        "prix_unitaire","fournisseur","delai_appro","observations",
    ]}
    pr_crit_ref = ft.Ref[ft.Dropdown]()

    def _pr_row(p: dict) -> ft.Container:
        stk = float(p.get("stock_actuel") or 0)
        mn  = float(p.get("stock_min") or 0)
        mx  = float(p.get("stock_max") or 1)
        crit = str(p.get("criticite","B"))
        color = DANGER if stk <= mn else (WARNING if stk < mn * 1.5 else SUCCESS)
        crit_c = DANGER if crit == "A" else (WARNING if crit == "B" else TEAL)
        pct = max(0, min(100, int(stk / max(mx, 0.001) * 100)))
        return ft.Container(
            bgcolor=CARD2, border=ft.border.all(1, color + "33"),
            border_radius=8, padding=10,
            content=ft.Column(controls=[
                ft.Row(controls=[
                    _badge(crit, crit_c),
                    ft.Text(f"[{p.get('code_piece','')}]", color=GOLD, size=10,
                            weight=ft.FontWeight.BOLD, width=90),
                    ft.Text(str(p.get("designation","")), color=TEXT, size=11, width=220),
                    ft.Text(str(p.get("reference_fabricant","")), color=MUTED, size=10, width=140),
                    ft.Container(expand=True),
                    ft.Text(f"Stock: {stk:.0f} {p.get('unite','')}", color=color,
                            size=11, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                  on_click=lambda ev, x=p: _pr_edit(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=18,
                                  on_click=lambda ev, x=p: _pr_delete(x["code_piece"])),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row(controls=[
                    ft.Text(f"Min: {mn:.0f}  Max: {mx:.0f}", color=MUTED, size=9, width=120),
                    ft.Text(f"PU: {_fmt_fcfa(float(p.get('prix_unitaire') or 0))}", color=MUTED, size=9, width=130),
                    ft.Text(str(p.get("fournisseur","—")), color=MUTED, size=9, width=160),
                    ft.Text(f"Délai: {p.get('delai_appro','—')} j", color=MUTED, size=9, width=80),
                    ft.Container(expand=True,
                                 content=ft.ProgressBar(value=pct/100, bgcolor=BORDER,
                                                        color=color, height=4)),
                    ft.Text(f"{pct}%", color=color, size=9, width=35),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=4, tight=True),
        )

    def _pr_load() -> None:
        q = str(_pr_search.current.value or "") if _pr_search.current else ""
        alerte = bool(_pr_filter_alerte.current and _pr_filter_alerte.current.value)
        rows   = list_pieces(search=q, alerte_seulement=alerte)
        col    = _pr_table.current
        if col:
            col.controls = [_pr_row(p) for p in rows] or [
                ft.Text("Aucune pièce.", color=MUTED, size=12)]
            try: col.update()
            except RuntimeError: pass

    def _pr_edit(p: dict) -> None:
        _pr_editing.clear()
        _pr_editing.update(p)
        for k, ref in pr_refs.items():
            if ref.current:
                ref.current.value = str(p.get(k) or "")
                try: ref.current.update()
                except RuntimeError: pass
        if pr_crit_ref.current:
            pr_crit_ref.current.value = str(p.get("criticite","B"))
            try: pr_crit_ref.current.update()
            except RuntimeError: pass
        f = _pr_form.current
        if f:
            f.visible = True
            try: f.update()
            except RuntimeError: pass

    def _pr_delete(code: str) -> None:
        try:
            delete_piece(code)
            notify(f"Pièce {code} supprimée.")
            _pr_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def _pr_save(ev: Any = None) -> None:
        data = {k: (ref.current.value if ref.current else "") for k, ref in pr_refs.items()}
        if pr_crit_ref.current:
            data["criticite"] = pr_crit_ref.current.value or "B"
        if _pr_editing:
            data["code_piece"] = _pr_editing["code_piece"]
        try:
            code = save_piece(data)
            notify(f"Pièce {code} enregistrée.")
            _pr_editing.clear()
            f = _pr_form.current
            if f:
                f.visible = False
                try: f.update()
                except RuntimeError: pass
            _pr_load(); _upd()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)

    def build_pieces() -> None:
        form = ft.Column(ref=_pr_form, visible=False, spacing=10, controls=[
            ft.Divider(color=BORDER),
            _section_title("Fiche Pièce de Rechange", ft.Icons.INVENTORY_2_OUTLINED, PURPLE),
            ft.Row(controls=[
                _field("Code Pièce *", pr_refs["code_piece"], width=130),
                _field("Désignation *", pr_refs["designation"], width=260),
                _field("Réf. Fabricant", pr_refs["reference_fabricant"], width=180),
                _field("Équipements concernés", pr_refs["equipements_concernes"], width=220),
                _dd("Criticité", pr_crit_ref, ["A","B","C"], width=100),
                _field("Unité", pr_refs["unite"], width=80),
            ], spacing=8, wrap=True),
            ft.Row(controls=[
                _field("Stock actuel", pr_refs["stock_actuel"], width=110),
                _field("Stock minimum", pr_refs["stock_min"], width=110),
                _field("Stock maximum", pr_refs["stock_max"], width=110),
                _field("Emplacement magasin", pr_refs["emplacement_magasin"], width=180),
                _field("Prix unitaire (FCFA)", pr_refs["prix_unitaire"], width=160),
                _field("Fournisseur", pr_refs["fournisseur"], width=200),
                _field("Délai appro (jours)", pr_refs["delai_appro"], width=140),
            ], spacing=8, wrap=True),
            _field("Observations", pr_refs["observations"], multiline=True),
            ft.Row(controls=[
                ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED,
                                  bgcolor=PURPLE, color="#FFFFFF", on_click=_pr_save),
                ft.OutlinedButton("Annuler",
                                  style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: MUTED},
                                                       side=ft.BorderSide(1, BORDER)),
                                  on_click=lambda e: (setattr(_pr_form.current,"visible",False),
                                                      _pr_form.current.update())),
            ], spacing=8),
        ])
        content_area.controls = [
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("Pièces de Rechange", ft.Icons.INVENTORY_2_OUTLINED, PURPLE),
                    ft.Container(expand=True),
                    ft.Checkbox(ref=_pr_filter_alerte, label="Alertes seulement",
                                label_style=ft.TextStyle(color=MUTED, size=11),
                                fill_color={ft.ControlState.SELECTED: DANGER},
                                on_change=lambda e: _pr_load()),
                    ft.TextField(ref=_pr_search, hint_text="Rechercher...",
                                 bgcolor=FIELD, color=TEXT, border_color=BORDER,
                                 focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=MUTED),
                                 width=180, height=38, text_size=12,
                                 on_submit=lambda e: _pr_load()),
                    ft.ElevatedButton("Nouvelle pièce", icon=ft.Icons.ADD,
                                      bgcolor=PURPLE, color="#FFFFFF",
                                      on_click=lambda e: (_pr_editing.clear(),
                                                          [setattr(r.current,"value","") or r.current.update()
                                                           for r in pr_refs.values() if r.current],
                                                          setattr(_pr_form.current,"visible",True),
                                                          _pr_form.current.update())),
                ], spacing=8),
                form,
                ft.Divider(color=BORDER, height=1),
                ft.Column(ref=_pr_table, spacing=6),
            ], spacing=10)),
        ]
        _pr_load()

    # ── INDICATEURS (MTBF/MTTR) ───────────────────────────────────────────────
    def build_indicateurs() -> None:
        try:
            rows = get_indicateurs_mtbf()
        except Exception as exc:
            _log.warning("[maint_ui] indicateurs: %s", exc)
            rows = []

        obj_dispo = 95.0

        ind_rows = []
        for r in rows:
            dispo = float(r.get("disponibilite") or 100)
            nb    = int(r.get("nb_pannes") or 0)
            mtbf  = float(r.get("mtbf") or 0)
            mttr  = float(r.get("mttr") or 0)
            crit  = str(r.get("criticite","B"))
            crit_c = DANGER if crit == "A" else (WARNING if crit == "B" else TEAL)
            dispo_c = SUCCESS if dispo >= obj_dispo else (WARNING if dispo >= 90 else DANGER)
            pct_bar = max(0, min(100, int(dispo)))

            ind_rows.append(ft.Container(
                bgcolor=CARD2, border=ft.border.all(1, dispo_c + "33"),
                border_radius=8, padding=10,
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        _badge(crit, crit_c),
                        ft.Text(str(r.get("code_equipement","")), color=PRIMARY, size=10,
                                weight=ft.FontWeight.BOLD, width=80),
                        ft.Text(str(r.get("designation","")), color=TEXT, size=11, width=220),
                        ft.Text(str(r.get("famille","")), color=MUTED, size=10, width=140),
                        ft.Container(expand=True),
                        ft.Text(f"Dispo: {dispo:.1f}%", color=dispo_c, size=12,
                                weight=ft.FontWeight.BOLD),
                    ], spacing=8),
                    ft.Row(controls=[
                        ft.Text(f"Pannes YTD: {nb}", color=MUTED, size=10, width=110),
                        ft.Text(f"Arrêt total: {float(r.get('total_arret') or 0):.0f} h", color=DANGER, size=10, width=120),
                        ft.Text(f"MTBF: {mtbf:.0f} h", color=SUCCESS, size=10, weight=ft.FontWeight.BOLD, width=100),
                        ft.Text(f"MTTR: {mttr:.1f} h", color=WARNING, size=10, weight=ft.FontWeight.BOLD, width=90),
                        ft.Container(expand=True,
                                     content=ft.ProgressBar(value=pct_bar/100, bgcolor=BORDER,
                                                            color=dispo_c, height=6)),
                        ft.Text(f"{pct_bar}%", color=dispo_c, size=10, weight=ft.FontWeight.BOLD, width=40),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=4, tight=True),
            ))

        # Légende KPIs
        legend = _card(ft.Column(controls=[
            _section_title("Définitions des Indicateurs", ft.Icons.INFO_OUTLINE, PRIMARY),
            ft.Divider(color=BORDER, height=1),
            ft.Row(controls=[
                ft.Column(controls=[
                    ft.Text("MTBF (Mean Time Between Failures)", color=SUCCESS, size=11, weight=ft.FontWeight.BOLD),
                    ft.Text("= Temps de marche total / Nombre de pannes\nObjectif équipements critiques A : MTBF > 300 h", color=MUTED, size=10),
                ], spacing=2, expand=True),
                ft.Column(controls=[
                    ft.Text("MTTR (Mean Time To Repair)", color=WARNING, size=11, weight=ft.FontWeight.BOLD),
                    ft.Text("= Temps d'arrêt total / Nombre de pannes\nObjectif : MTTR < 4 h pour criticité A", color=MUTED, size=10),
                ], spacing=2, expand=True),
                ft.Column(controls=[
                    ft.Text("Disponibilité (%)", color=TEAL, size=11, weight=ft.FontWeight.BOLD),
                    ft.Text("= MTBF / (MTBF + MTTR) × 100\nObjectif global : ≥ 95%", color=MUTED, size=10),
                ], spacing=2, expand=True),
                ft.Column(controls=[
                    ft.Text("Ratio PM/CM (%)", color=PURPLE, size=11, weight=ft.FontWeight.BOLD),
                    ft.Text("= OT Préventifs / Total OT × 100\nObjectif : ≥ 70% préventif", color=MUTED, size=10),
                ], spacing=2, expand=True),
            ], spacing=20),
        ], spacing=8))

        content_area.controls = [
            legend,
            _card(ft.Column(controls=[
                ft.Row(controls=[
                    _section_title("MTBF / MTTR / Disponibilité par Équipement (YTD)",
                                   ft.Icons.ANALYTICS_OUTLINED, TEAL),
                    ft.Container(expand=True),
                    ft.Container(
                        bgcolor=SUCCESS + "22", border=ft.border.all(1, SUCCESS + "55"),
                        border_radius=8, padding=ft.padding.symmetric(horizontal=12, vertical=6),
                        content=ft.Text(f"Objectif disponibilité : {obj_dispo:.0f}%",
                                        color=SUCCESS, size=11, weight=ft.FontWeight.BOLD),
                    ),
                ], spacing=8),
                ft.Divider(color=BORDER, height=1),
                ft.Column(
                    controls=ind_rows if ind_rows else [
                        ft.Row(controls=[
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=MUTED, size=18),
                            ft.Text("Aucune intervention enregistrée — les indicateurs apparaîtront "
                                    "dès la saisie des premiers OT.", color=MUTED, size=12),
                        ], spacing=8)
                    ],
                    spacing=6,
                ),
            ], spacing=10)),
        ]

    # ── Navigation tabs ───────────────────────────────────────────────────────
    tabs_def = [
        ("dashboard",    "Tableau de bord", ft.Icons.DASHBOARD_OUTLINED,              GOLD),
        ("equipements",  "Équipements",     ft.Icons.PRECISION_MANUFACTURING_OUTLINED, TEAL),
        ("plan_pm",      "Plan PM",         ft.Icons.EVENT_REPEAT_OUTLINED,            SUCCESS),
        ("interventions","Interventions",   ft.Icons.ASSIGNMENT_OUTLINED,              WARNING),
        ("pieces",       "Pièces",          ft.Icons.INVENTORY_2_OUTLINED,             PURPLE),
        ("indicateurs",  "Indicateurs",     ft.Icons.ANALYTICS_OUTLINED,               PRIMARY),
    ]
    tab_buttons: dict[str, ft.TextButton] = {}

    def set_tab(key: str) -> None:
        state["tab"] = key
        for k, btn in tab_buttons.items():
            _, lbl, ic, col = next(t for t in tabs_def if t[0] == k)
            selected = k == key
            btn.style = ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: col if selected else MUTED},
                bgcolor={ft.ControlState.DEFAULT: col + "22" if selected else "transparent"},
            )
            try: btn.update()
            except RuntimeError: pass
        {
            "dashboard":    build_dashboard,
            "equipements":  build_equipements,
            "plan_pm":      build_plan_pm,
            "interventions":build_interventions,
            "pieces":       build_pieces,
            "indicateurs":  build_indicateurs,
        }[key]()
        try: content_area.update()
        except RuntimeError: pass

    for key, label, icon, color in tabs_def:
        btn = ft.TextButton(label, icon=icon,
                            style=ft.ButtonStyle(
                                color={ft.ControlState.DEFAULT: MUTED},
                                bgcolor={ft.ControlState.DEFAULT: "transparent"},
                            ),
                            on_click=lambda e, k=key: set_tab(k))
        tab_buttons[key] = btn

    header = ft.Container(
        bgcolor=CARD, border=ft.border.all(1, BORDER), border_radius=10, padding=14,
        content=ft.Row(controls=[
            ft.Container(
                width=44, height=44, bgcolor=WARNING + "22", border_radius=8,
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.HANDYMAN_OUTLINED, color=WARNING, size=26),
            ),
            ft.Column(controls=[
                ft.Text("Maintenance Industrielle", color=TEXT, size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Équipements | Plan PM | OT | Pièces | MTBF/MTTR", color=MUTED, size=11),
            ], spacing=2, tight=True),
            ft.Container(expand=True),
            ft.Text("", ref=status_ref, color=MUTED, size=11),
            ft.ElevatedButton("Exporter XLS", icon=ft.Icons.DOWNLOAD_OUTLINED,
                              bgcolor=GOLD, color=NAVY, on_click=lambda e: _do_export()),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    tab_bar = ft.Container(
        bgcolor=CARD, border=ft.border.all(1, BORDER), border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row(controls=list(tab_buttons.values()),
                       spacing=4, scroll=ft.ScrollMode.AUTO),
    )

    root = ft.Container(
        bgcolor=BG, expand=True, padding=12,
        content=ft.Column(controls=[header, tab_bar, content_area],
                          spacing=12, expand=True, scroll=ft.ScrollMode.AUTO),
    )

    set_tab("dashboard")
    return root
