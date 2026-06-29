"""maintenance_indus_export.py — Export Excel HTML du module Maintenance Industrielle."""
from __future__ import annotations

import html
import logging
from datetime import date
from pathlib import Path

from app.services.maintenance_indus_service import (
    get_maintenance_dashboard,
    list_equipements,
    list_interventions,
    list_pieces,
    list_plan_pm,
    list_prestataires,
    get_indicateurs_mtbf,
)

_log = logging.getLogger(__name__)

_GOLD  = "#C8A400"
_NAVY  = "#0D1B2A"
_STEEL = "#1C3557"
_WHITE = "#FFFFFF"
_RED   = "#C0392B"
_GREEN = "#00A86B"
_BLUE  = "#2E86C1"
_ORANGE= "#E67E22"
_MUTED = "#94A3B8"
_LRED  = "#FADBD8"
_LGRN  = "#D5F5E3"
_LORG  = "#FDEBD0"
_LBLU  = "#D6EAF8"


def _xe(v: object) -> str:
    return html.escape(str(v) if v is not None else "")


def _fmt(v: float, suffix: str = "") -> str:
    try:
        return f"{float(v):,.0f}{suffix}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


def _unique_path(base: str) -> Path:
    try:
        from app.services.attendance_export_service import _unique_export_path
        return _unique_export_path(base)
    except ImportError:
        p = Path(base)
        if not p.exists():
            return p
        stem, ext = p.stem, p.suffix
        for i in range(1, 999):
            q = p.with_name(f"{stem}_{i}{ext}")
            if not q.exists():
                return q
        return p


def _th(text: str, width: str = "auto", color: str = _GOLD) -> str:
    return (f'<th style="background:{_NAVY};color:{color};'
            f'padding:8px 10px;border:1px solid {_STEEL};'
            f'font-size:11px;white-space:nowrap;width:{width}">{_xe(text)}</th>')


def _td(text: str, bg: str = _WHITE, color: str = "#1A252F",
        bold: bool = False, align: str = "left") -> str:
    fw = "bold" if bold else "normal"
    return (f'<td style="background:{bg};color:{color};'
            f'padding:6px 10px;border:1px solid #D5D8DC;'
            f'font-size:10px;font-weight:{fw};text-align:{align}">{_xe(text)}</td>')


def _section(title: str, subtitle: str = "") -> str:
    sub = f'<div style="font-size:10px;color:#7F8C8D;margin-top:2px">{_xe(subtitle)}</div>' if subtitle else ""
    return (
        f'<tr><td colspan="20" style="background:{_STEEL};color:{_GOLD};'
        f'font-size:13px;font-weight:bold;padding:10px 14px;'
        f'border-top:3px solid {_GOLD}">{_xe(title)}{sub}</td></tr>'
    )


def _kpi_badge(label: str, value: str, color: str = _BLUE) -> str:
    return (
        f'<div style="display:inline-block;margin:6px;padding:12px 20px;'
        f'background:{_NAVY};border:2px solid {color};border-radius:8px;'
        f'text-align:center;min-width:120px">'
        f'<div style="font-size:9px;color:#94A3B8;text-transform:uppercase">{_xe(label)}</div>'
        f'<div style="font-size:20px;font-weight:bold;color:{color}">{_xe(value)}</div>'
        f'</div>'
    )


def export_maintenance_xlsx() -> Path:
    year = date.today().year
    path = _unique_path(f"maintenance_industrielle_{year}.xls")

    try:
        dash = get_maintenance_dashboard()
    except Exception:
        dash = {}

    try:
        equipements = list_equipements()
    except Exception:
        equipements = []

    try:
        plan_pm = list_plan_pm()
    except Exception:
        plan_pm = []

    try:
        interventions = list_interventions()
    except Exception:
        interventions = []

    try:
        pieces = list_pieces()
    except Exception:
        pieces = []

    try:
        prestataires = list_prestataires()
    except Exception:
        prestataires = []

    try:
        indicateurs = get_indicateurs_mtbf()
    except Exception:
        indicateurs = []

    today = date.today().strftime("%d/%m/%Y")
    ratio_pm = dash.get("ratio_pm", 0)

    # ── KPI block ─────────────────────────────────────────────────────────────
    kpi_html = "".join([
        _kpi_badge("Équipements actifs",
                   f"{dash.get('nb_eq_actif',0)}/{dash.get('nb_equipements',0)}", _BLUE),
        _kpi_badge("OT YTD", str(dash.get("nb_ot_ytd",0)), _ORANGE),
        _kpi_badge("Coût maintenance",
                   f"{dash.get('cout_ytd',0)/1000000:.1f} M F", _GOLD),
        _kpi_badge("Arrêts pannes",
                   f"{dash.get('h_arret_ytd',0):.0f} h", _RED),
        _kpi_badge("Ratio PM/CM", f"{ratio_pm:.0f}%",
                   _GREEN if ratio_pm >= 70 else _RED),
        _kpi_badge("Alertes pièces",
                   str(dash.get("nb_alerte_pieces",0)),
                   _RED if dash.get("nb_alerte_pieces",0) > 0 else _GREEN),
    ])

    # ── Équipements ───────────────────────────────────────────────────────────
    crit_colors = {"A": _RED, "B": _ORANGE, "C": _BLUE}
    stat_colors = {"En service": _GREEN, "Maintenance": _ORANGE,
                   "Arret": _RED, "Reforme": "#777777"}

    eq_rows = ""
    for i, e in enumerate(equipements):
        bg = _LBLU if i % 2 == 0 else _WHITE
        crit = str(e.get("criticite","B"))
        cc   = crit_colors.get(crit, _BLUE)
        stat = str(e.get("statut","En service"))
        sc   = stat_colors.get(stat, _BLUE)
        eq_rows += (
            "<tr>"
            + _td(e.get("code_equipement",""), bg=bg, bold=True, color=_BLUE)
            + _td(e.get("designation",""), bg=bg)
            + _td(e.get("famille",""), bg=bg)
            + f'<td style="background:{cc}22;color:{cc};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{crit}</td>'
            + _td(e.get("site_zone",""), bg=bg)
            + _td(e.get("emplacement",""), bg=bg)
            + _td(e.get("marque",""), bg=bg)
            + _td(e.get("modele",""), bg=bg)
            + _td(e.get("date_mise_en_service",""), bg=bg, align="center")
            + _td(e.get("capacite_puissance",""), bg=bg, align="center")
            + _td(_fmt(e.get("valeur_remplacement",0)) + " F", bg=bg, align="right",
                  bold=True, color=_GOLD)
            + f'<td style="background:{sc}22;color:{sc};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{_xe(stat)}</td>'
            + "</tr>"
        )

    # ── Plan PM ───────────────────────────────────────────────────────────────
    today_iso = date.today().isoformat()
    pm_rows = ""
    freq_colors = {
        "Journalier":"#148F77","Hebdomadaire":"#2E86C1","Mensuel":"#6C3483",
        "Trimestriel":"#E67E22","Semestriel":"#C0392B","Annuel":"#1A5276",
    }
    for i, p in enumerate(plan_pm):
        proch = str(p.get("prochaine_echeance") or "")
        echu  = proch and proch < today_iso
        bg    = _LRED if echu else (_LBLU if i % 2 == 0 else _WHITE)
        stat  = "⚠ ÉCHU" if echu else "✓ OK"
        sc    = _RED if echu else _GREEN
        freq  = str(p.get("frequence",""))
        fc    = freq_colors.get(freq, _BLUE)
        pm_rows += (
            "<tr>"
            + _td(p.get("code_equipement",""), bg=bg, bold=True, color=_BLUE)
            + _td(p.get("designation_eq",""), bg=bg)
            + _td(p.get("tache",""), bg=bg)
            + f'<td style="background:{fc}22;color:{fc};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{_xe(freq)}</td>'
            + _td(p.get("derniere_realisation",""), bg=bg, align="center")
            + _td(proch, bg=bg, align="center",
                  bold=echu, color=_RED if echu else "#1A252F")
            + _td(str(p.get("duree_h","")), bg=bg, align="center")
            + _td(p.get("responsable",""), bg=bg)
            + _td(p.get("pieces_necessaires",""), bg=bg)
            + f'<td style="background:{sc}22;color:{sc};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{stat}</td>'
            + "</tr>"
        )

    # ── Interventions ─────────────────────────────────────────────────────────
    type_colors = {
        "Préventive systématique": _GREEN, "Préventive conditionnelle": "#148F77",
        "Corrective urgente": _RED, "Corrective planifiée": _ORANGE,
        "Améliorative": "#6C3483", "Prédictive": _BLUE,
    }
    ot_rows = ""
    tot_arret = tot_mo = tot_pieces_c = tot_total = 0.0
    for i, o in enumerate(interventions):
        t   = str(o.get("type_maintenance",""))
        tc  = type_colors.get(t, _BLUE)
        st  = str(o.get("statut",""))
        sc  = _GREEN if "lôt" in st else (_BLUE if "cours" in st else _ORANGE)
        bg  = _LRED if "urgente" in t and "cours" in st else (_LBLU if i % 2 == 0 else _WHITE)
        arret = float(o.get("temps_arret") or 0)
        mo    = float(o.get("cout_mo") or 0)
        pic   = float(o.get("cout_pieces") or 0)
        tot   = float(o.get("cout_total") or 0)
        tot_arret += arret; tot_mo += mo; tot_pieces_c += pic; tot_total += tot
        ot_rows += (
            "<tr>"
            + _td(o.get("numero_ot",""), bg=bg, bold=True, color=tc)
            + _td(o.get("date_ouverture","")[:10], bg=bg, align="center")
            + _td(o.get("date_cloture","")[:10] if o.get("date_cloture") else "—", bg=bg, align="center")
            + _td(o.get("code_equipement",""), bg=bg, color=_BLUE)
            + _td(o.get("designation_eq",""), bg=bg)
            + f'<td style="background:{tc}22;color:{tc};font-size:9px;font-weight:bold;'
              f'padding:6px;border:1px solid #D5D8DC;text-align:center">{_xe(t[:22])}</td>'
            + _td(o.get("nature_panne",""), bg=bg)
            + _td(o.get("technicien",""), bg=bg)
            + _td(f"{arret:.0f} h", bg=bg, align="right",
                  bold=arret > 8, color=_RED if arret > 8 else "#1A252F")
            + _td(f"{float(o.get('duree_intervention') or 0):.0f} h", bg=bg, align="right")
            + _td(_fmt(mo) + " F", bg=bg, align="right")
            + _td(_fmt(pic) + " F", bg=bg, align="right")
            + _td(_fmt(tot) + " F", bg=bg, align="right", bold=True, color=_GOLD)
            + f'<td style="background:{sc}22;color:{sc};font-weight:bold;'
              f'padding:6px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{_xe(st)}</td>'
            + "</tr>"
        )
    # Ligne totaux
    ot_rows += (
        f'<tr style="background:{_GOLD};font-weight:bold">'
        + f'<td colspan="8" style="padding:8px 10px;color:{_NAVY};font-size:11px;border:1px solid #aaa">TOTAUX</td>'
        + _td(f"{tot_arret:.0f} h", bg=_GOLD, bold=True, color=_NAVY, align="right")
        + _td("", bg=_GOLD)
        + _td(_fmt(tot_mo) + " F", bg=_GOLD, bold=True, color=_NAVY, align="right")
        + _td(_fmt(tot_pieces_c) + " F", bg=_GOLD, bold=True, color=_NAVY, align="right")
        + _td(_fmt(tot_total) + " F", bg=_GOLD, bold=True, color=_NAVY, align="right")
        + _td("", bg=_GOLD)
        + "</tr>"
    )

    # ── Pièces de rechange ────────────────────────────────────────────────────
    pr_rows = ""
    val_stock = 0.0
    for i, p in enumerate(pieces):
        stk = float(p.get("stock_actuel") or 0)
        mn  = float(p.get("stock_min") or 0)
        pu  = float(p.get("prix_unitaire") or 0)
        val = stk * pu
        val_stock += val
        alerte = stk <= mn
        bg     = _LRED if alerte else (_LBLU if i % 2 == 0 else _WHITE)
        crit   = str(p.get("criticite","B"))
        cc     = crit_colors.get(crit, _BLUE)
        stk_c  = _RED if alerte else "#1A252F"
        pr_rows += (
            "<tr>"
            + f'<td style="background:{cc}22;color:{cc};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{crit}</td>'
            + _td(p.get("code_piece",""), bg=bg, bold=True, color=_GOLD)
            + _td(p.get("designation",""), bg=bg)
            + _td(p.get("reference_fabricant",""), bg=bg)
            + _td(p.get("unite",""), bg=bg, align="center")
            + _td(f"{stk:.0f}", bg=bg, bold=alerte, color=stk_c, align="right")
            + _td(f"{mn:.0f}", bg=bg, align="right")
            + _td(f"{float(p.get('stock_max') or 0):.0f}", bg=bg, align="right")
            + _td(p.get("emplacement_magasin",""), bg=bg)
            + _td(_fmt(pu) + " F", bg=bg, align="right")
            + _td(_fmt(val) + " F", bg=bg, align="right", bold=True, color=_GOLD)
            + _td(p.get("fournisseur",""), bg=bg)
            + _td(str(p.get("delai_appro","—")), bg=bg, align="center")
            + "</tr>"
        )

    # ── Indicateurs MTBF ─────────────────────────────────────────────────────
    ind_rows = ""
    for i, r in enumerate(indicateurs):
        dispo = float(r.get("disponibilite") or 100)
        dispo_c = _GREEN if dispo >= 95 else (_ORANGE if dispo >= 90 else _RED)
        crit = str(r.get("criticite","B"))
        cc   = crit_colors.get(crit, _BLUE)
        bg   = _LBLU if i % 2 == 0 else _WHITE
        ind_rows += (
            "<tr>"
            + f'<td style="background:{cc}22;color:{cc};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{crit}</td>'
            + _td(r.get("code_equipement",""), bg=bg, bold=True, color=_BLUE)
            + _td(r.get("designation",""), bg=bg)
            + _td(r.get("famille",""), bg=bg)
            + _td(str(r.get("nb_pannes",0)), bg=bg, align="center",
                  bold=int(r.get("nb_pannes",0)) > 3, color=_RED if int(r.get("nb_pannes",0)) > 3 else "#1A252F")
            + _td(f"{float(r.get('total_arret') or 0):.0f} h", bg=bg, align="right", color=_RED)
            + _td(f"{float(r.get('mtbf') or 0):.0f} h", bg=bg, align="right",
                  bold=True, color=_GREEN)
            + _td(f"{float(r.get('mttr') or 0):.1f} h", bg=bg, align="right", color=_ORANGE)
            + f'<td style="background:{dispo_c}22;color:{dispo_c};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:11px;text-align:center">'
              f'{dispo:.1f}%</td>'
            + "</tr>"
        )
    if not ind_rows:
        ind_rows = (
            f'<tr><td colspan="9" style="padding:12px;color:{_MUTED};'
            f'font-style:italic;text-align:center;background:{_WHITE}">'
            'Aucune intervention enregistrée — saisir des OT pour voir les indicateurs.</td></tr>'
        )

    # ── Prestataires ──────────────────────────────────────────────────────────
    prest_rows = ""
    for i, p in enumerate(prestataires):
        bg  = _LBLU if i % 2 == 0 else _WHITE
        cont = str(p.get("contrat","Non"))
        cc   = _GREEN if cont == "Oui" else _MUTED
        note = float(p.get("note_qualite") or 0)
        stars = "★" * int(note) + "☆" * (5 - int(note))
        note_c = _GOLD if note >= 4.5 else (_ORANGE if note >= 3.5 else _RED)
        prest_rows += (
            "<tr>"
            + _td(p.get("code_prestataire",""), bg=bg, bold=True, color=_BLUE)
            + _td(p.get("raison_sociale",""), bg=bg)
            + _td(p.get("specialite",""), bg=bg)
            + _td(p.get("contact",""), bg=bg)
            + _td(p.get("telephone",""), bg=bg)
            + f'<td style="background:{cc}22;color:{cc};font-weight:bold;'
              f'padding:6px 10px;border:1px solid #D5D8DC;font-size:10px;text-align:center">{_xe(cont)}</td>'
            + _td(p.get("type_contrat",""), bg=bg, align="center")
            + _td(p.get("debut_contrat",""), bg=bg, align="center")
            + _td(p.get("fin_contrat",""), bg=bg, align="center")
            + _td(_fmt(p.get("montant_contrat",0)) + " F", bg=bg, align="right", bold=True, color=_GOLD)
            + f'<td style="background:{_WHITE};color:{note_c};font-weight:bold;'
              f'padding:6px;border:1px solid #D5D8DC;font-size:13px;text-align:center">{stars}</td>'
            + "</tr>"
        )

    # ── HTML complet ──────────────────────────────────────────────────────────
    html_content = f"""
<html xmlns:x="urn:schemas-microsoft-com:office:excel">
<head><meta charset="utf-8">
<style>
body{{font-family:Calibri,Arial,sans-serif;background:{_NAVY};margin:0;padding:20px}}
h1{{color:{_GOLD};font-size:20px;margin:0 0 4px 0}}
h2{{color:{_WHITE};font-size:13px;margin:0 0 16px 0;font-weight:normal}}
.section{{margin-bottom:28px}}
table{{border-collapse:collapse;width:100%;margin-bottom:4px}}
</style></head>
<body>
<h1>MAINTENANCE INDUSTRIELLE — DIAMOND DRILLING — {year}</h1>
<h2>Export du {today} &nbsp;|&nbsp; {len(equipements)} équipements &nbsp;|&nbsp;
{len(plan_pm)} tâches PM &nbsp;|&nbsp; {len(interventions)} OT &nbsp;|&nbsp;
{len(pieces)} pièces &nbsp;|&nbsp; {len(prestataires)} prestataires</h2>

<div style="margin-bottom:20px">{kpi_html}</div>

<!-- ÉQUIPEMENTS -->
<div class="section">
<table>
<tr><td colspan="12" style="background:{_NAVY};color:{_GOLD};font-size:14px;
  font-weight:bold;padding:10px 14px;border-top:3px solid {_GOLD}">
  REGISTRE DES ÉQUIPEMENTS — Valeur parc :
  {_fmt(sum(float(e.get('valeur_remplacement',0)) for e in equipements))} FCFA
</td></tr>
<tr>
{_th("Code")} {_th("Désignation")} {_th("Famille")} {_th("Crit.")}
{_th("Zone")} {_th("Emplacement")} {_th("Marque")} {_th("Modèle")}
{_th("Date MES")} {_th("Capacité")} {_th("Valeur remplacement")} {_th("Statut")}
</tr>
{eq_rows if eq_rows else f'<tr><td colspan="12" style="padding:12px;color:{_MUTED};font-style:italic">Aucun équipement enregistré.</td></tr>'}
</table></div>

<!-- PLAN PM -->
<div class="section">
<table>
<tr><td colspan="10" style="background:{_NAVY};color:{_GOLD};font-size:14px;
  font-weight:bold;padding:10px 14px;border-top:3px solid {_GOLD}">
  PLAN DE MAINTENANCE PRÉVENTIVE — {len([p for p in plan_pm if str(p.get('prochaine_echeance','')) < today_iso and p.get('prochaine_echeance')])} tâches échues
</td></tr>
<tr>
{_th("Code équip.")} {_th("Désignation")} {_th("Tâche")} {_th("Fréquence")}
{_th("Dernière réal.")} {_th("Prochaine éch.")} {_th("Durée")}
{_th("Responsable")} {_th("Pièces nécessaires")} {_th("Statut")}
</tr>
{pm_rows if pm_rows else f'<tr><td colspan="10" style="padding:12px;color:{_MUTED};font-style:italic">Aucune tâche PM.</td></tr>'}
</table></div>

<!-- INTERVENTIONS -->
<div class="section">
<table>
<tr><td colspan="14" style="background:{_NAVY};color:{_GOLD};font-size:14px;
  font-weight:bold;padding:10px 14px;border-top:3px solid {_GOLD}">
  REGISTRE DES INTERVENTIONS (OT) — Total coût : {_fmt(tot_total)} FCFA &nbsp;|&nbsp; Arrêts : {tot_arret:.0f} h
</td></tr>
<tr>
{_th("N° OT")} {_th("Ouverture")} {_th("Clôture")} {_th("Équipement")}
{_th("Désignation")} {_th("Type")} {_th("Nature panne")} {_th("Technicien")}
{_th("Arrêt (h)")} {_th("Durée (h)")} {_th("Coût MO")} {_th("Coût pièces")}
{_th("Coût total")} {_th("Statut")}
</tr>
{ot_rows}
</table></div>

<!-- PIÈCES DE RECHANGE -->
<div class="section">
<table>
<tr><td colspan="13" style="background:{_NAVY};color:{_GOLD};font-size:14px;
  font-weight:bold;padding:10px 14px;border-top:3px solid {_GOLD}">
  PIÈCES DE RECHANGE — Valeur stock : {_fmt(val_stock)} FCFA &nbsp;|&nbsp;
  Alertes : {len([p for p in pieces if float(p.get('stock_actuel',0)) <= float(p.get('stock_min',0))])}
</td></tr>
<tr>
{_th("Crit.")} {_th("Code")} {_th("Désignation")} {_th("Réf. Fab.")}
{_th("Unité")} {_th("Stock act.")} {_th("Stock min")} {_th("Stock max")}
{_th("Emplacement")} {_th("Prix unit.")} {_th("Valeur stock")}
{_th("Fournisseur")} {_th("Délai appro")}
</tr>
{pr_rows if pr_rows else f'<tr><td colspan="13" style="padding:12px;color:{_MUTED};font-style:italic">Aucune pièce.</td></tr>'}
</table></div>

<!-- INDICATEURS MTBF/MTTR -->
<div class="section">
<table>
<tr><td colspan="9" style="background:{_NAVY};color:{_GOLD};font-size:14px;
  font-weight:bold;padding:10px 14px;border-top:3px solid {_GOLD}">
  INDICATEURS MTBF / MTTR / DISPONIBILITÉ — Objectif disponibilité ≥ 95%
</td></tr>
<tr>
{_th("Crit.")} {_th("Code")} {_th("Désignation")} {_th("Famille")}
{_th("Nb pannes")} {_th("Arrêt total")} {_th("MTBF")} {_th("MTTR")}
{_th("Disponibilité")}
</tr>
{ind_rows}
</table></div>

<!-- PRESTATAIRES -->
<div class="section">
<table>
<tr><td colspan="11" style="background:{_NAVY};color:{_GOLD};font-size:14px;
  font-weight:bold;padding:10px 14px;border-top:3px solid {_GOLD}">
  PRESTATAIRES & FOURNISSEURS — {len([p for p in prestataires if p.get('contrat')=='Oui'])} contrats actifs
</td></tr>
<tr>
{_th("Code")} {_th("Raison sociale")} {_th("Spécialité")} {_th("Contact")}
{_th("Téléphone")} {_th("Contrat")} {_th("Type")} {_th("Début")} {_th("Fin")}
{_th("Montant/an")} {_th("Note qualité")}
</tr>
{prest_rows if prest_rows else f'<tr><td colspan="11" style="padding:12px;color:{_MUTED};font-style:italic">Aucun prestataire.</td></tr>'}
</table></div>

<p style="color:{_MUTED};font-size:9px;margin-top:24px">
Généré par QHSE Management — Diamond Drilling — {today} &nbsp;|&nbsp; Module Maintenance Industrielle
</p>
</body></html>
"""

    path.write_text(html_content, encoding="utf-8")
    _log.info("[maint_export] -> %s", path)
    return path
