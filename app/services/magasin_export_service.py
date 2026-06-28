"""magasin_export_service.py — Export Excel conforme au modèle Diamond Drilling.

Génère un classeur 6 feuilles : DASHBOARD, CATALOGUE, FOURNISSEURS, ENTRÉES,
SORTIES, STOCK ACTUEL — structure identique à gestion_magasin_diamond_drilling.py.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.services.magasin_service import (
    get_magasin_dashboard,
    get_stock_actuel,
    list_articles,
    list_entrees,
    list_fournisseurs,
    list_sorties,
)

_log = logging.getLogger(__name__)

# ── Export path helper ────────────────────────────────────────────────────────
try:
    from app.services.attendance_export_service import _unique_export_path  # type: ignore
except ImportError:
    from pathlib import Path as _Path

    def _unique_export_path(filename: str) -> Path:  # type: ignore
        from app.db.connection import DATA_DIR  # type: ignore
        base = DATA_DIR / filename
        if not base.exists():
            return base
        stem, suffix = base.stem, base.suffix
        i = 1
        while True:
            candidate = base.with_name(f"{stem}_{i}{suffix}")
            if not candidate.exists():
                return candidate
            i += 1


# ── Palette (same as Excel template) ─────────────────────────────────────────
GOLD        = "C8A400"
NAVY        = "0D1B2A"
GREEN       = "00A86B"
RED_ALERT   = "C0392B"
HEADER_BG   = "1C3557"
WHITE       = "FFFFFF"
LIGHT_GRAY  = "F5F5F5"
DARK_GRAY   = "2C2C2C"
ORANGE      = "E67E22"
BLUE        = "2E86C1"
PURPLE      = "8E44AD"
TEAL        = "1ABC9C"


def _try_openpyxl() -> Any:
    try:
        import openpyxl  # noqa: F401
        return openpyxl
    except ImportError:
        return None


# ── HTML-as-XLS fallback (always available) ───────────────────────────────────

def _xe(v: Any) -> str:
    s = str(v) if v is not None else ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _html_xls(path: Path, data: dict[str, Any]) -> None:
    """Single-sheet HTML-as-XLS with all data sections."""
    arts    = data["articles"]
    fous    = data["fournisseurs"]
    entrees = data["entrees"]
    sorties = data["sorties"]
    stock   = data["stock"]
    dash    = data["dashboard"]
    today   = date.today().strftime("%d/%m/%Y")
    year    = date.today().year

    def _row(*cells: tuple[str, str, str, str]) -> str:
        # cells = (value, bgcolor, color, align)
        tds = ""
        for val, bg, fg, align in cells:
            style = f"background:#{bg};color:#{fg};text-align:{align};padding:4px 6px;border:1px solid #334155;font-size:11px;"
            tds += f"<td style='{style}'>{_xe(val)}</td>"
        return f"<tr>{tds}</tr>"

    html = (
        f"<html><head><meta charset='utf-8'/>"
        f"<style>body{{font-family:Calibri,Arial,sans-serif;background:#0D1B2A;color:#F1F5F9}}"
        f"table{{border-collapse:collapse;width:100%;margin-bottom:20px}}</style></head><body>"
    )

    def _section(title: str) -> str:
        return (
            f"<tr><td colspan='20' style='background:#{HEADER_BG};color:#{GOLD};"
            f"font-size:14px;font-weight:bold;padding:8px;border:1px solid #{GOLD}'>"
            f"■ {_xe(title)}</td></tr>"
        )

    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    html += f"<h2 style='color:#{GOLD}'>GESTION DU MAGASIN — DIAMOND DRILLING — {year}</h2>"
    html += f"<p style='color:#94A3B8'>Généré le {today}</p>"
    html += "<table>"
    html += _section("INDICATEURS CLÉS (KPIs)")
    html += _row(
        ("Valeur Stock Actuel", GOLD, NAVY, "center"),
        ("Valeur Entrées", GREEN, NAVY, "center"),
        ("Valeur Sorties", RED_ALERT, NAVY, "center"),
        ("Nb Références", BLUE, NAVY, "center"),
        ("Bons Entrée", GREEN, NAVY, "center"),
        ("Bons Sortie", RED_ALERT, NAVY, "center"),
    )
    html += _row(
        (f"{dash.get('valeur_stock_actuel',0):,.0f} FCFA", "1B4332", GOLD, "right"),
        (f"{dash.get('total_entrees_valeur',0):,.0f} FCFA", "1B4332", GREEN, "right"),
        (f"{dash.get('total_sorties_valeur',0):,.0f} FCFA", "4A1519", RED_ALERT, "right"),
        (str(dash.get("nb_articles", 0)), "1C2B4A", BLUE, "center"),
        (str(dash.get("nb_entrees", 0)), "1B4332", GREEN, "center"),
        (str(dash.get("nb_sorties", 0)), "4A1519", RED_ALERT, "center"),
    )

    # Monthly
    html += _section(f"MOUVEMENTS MENSUELS {year}")
    months = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
    html += _row(*[(m, HEADER_BG, GOLD, "center") for m in ["Mois", "Entrées (FCFA)", "Sorties (FCFA)", "Solde (FCFA)"]])
    for m_data in dash.get("monthly", []):
        solde = m_data["entrees"] - m_data["sorties"]
        s_color = GREEN if solde >= 0 else RED_ALERT
        html += _row(
            (m_data["mois"], DARK_GRAY, WHITE, "center"),
            (f"{m_data['entrees']:,.0f}", "1B4332", GREEN, "right"),
            (f"{m_data['sorties']:,.0f}", "4A1519", RED_ALERT, "right"),
            (f"{solde:+,.0f}", "2C2C2C", s_color, "right"),
        )

    # Alerts
    alerts = dash.get("alerts", [])
    if alerts:
        html += _section("ALERTES STOCK")
        html += _row(*[(h, HEADER_BG, RED_ALERT, "center")
                       for h in ["Code", "Désignation", "Stock Actuel", "Stock Min", "Stock Alerte", "Unité", "Statut"]])
        for a in alerts:
            stk = float(a.get("stock_actuel") or 0)
            is_crit = stk <= float(a.get("stock_min") or 0)
            status = "CRITIQUE" if is_crit else "ALERTE"
            bg = "4A1519" if is_crit else "4A3800"
            fg = RED_ALERT if is_crit else "F59E0B"
            html += _row(
                (a.get("code_article", ""), bg, GOLD, "center"),
                (a.get("designation", ""), bg, WHITE, "left"),
                (f"{stk:.0f}", bg, fg, "right"),
                (f"{a.get('stock_min',0):.0f}", bg, MUTED := "94A3B8", "right"),
                (f"{a.get('stock_alerte',0):.0f}", bg, MUTED, "right"),
                (a.get("unite", ""), bg, MUTED, "center"),
                (status, bg, fg, "center"),
            )
    html += "</table>"

    # ── CATALOGUE ─────────────────────────────────────────────────────────────
    html += f"<h3 style='color:#{GOLD}'>CATALOGUE DES ARTICLES</h3><table>"
    cat_headers = ["Code Article","Désignation","Catégorie","Sous-catégorie","Unité",
                   "Stock Min","Stock Max","Stock Alerte","Prix Unitaire (FCFA)",
                   "Fournisseur Préféré","Emplacement","Observations"]
    html += _row(*[(h, HEADER_BG, GOLD, "center") for h in cat_headers])
    for a in arts:
        html += _row(
            (a.get("code_article",""), "1C2B4A", GOLD, "center"),
            (a.get("designation",""), DARK_GRAY, WHITE, "left"),
            (a.get("categorie",""), DARK_GRAY, "94A3B8", "center"),
            (a.get("sous_categorie",""), DARK_GRAY, "94A3B8", "center"),
            (a.get("unite",""), DARK_GRAY, WHITE, "center"),
            (f"{float(a.get('stock_min') or 0):.0f}", DARK_GRAY, "94A3B8", "right"),
            (f"{float(a.get('stock_max') or 0):.0f}", DARK_GRAY, "94A3B8", "right"),
            (f"{float(a.get('stock_alerte') or 0):.0f}", "4A3800", "F59E0B", "right"),
            (f"{float(a.get('prix_unitaire') or 0):,.0f}", DARK_GRAY, GOLD, "right"),
            (a.get("fournisseur_prefere",""), DARK_GRAY, "94A3B8", "left"),
            (a.get("emplacement",""), DARK_GRAY, "94A3B8", "center"),
            (a.get("observations",""), DARK_GRAY, "94A3B8", "left"),
        )
    html += "</table>"

    # ── FOURNISSEURS ─────────────────────────────────────────────────────────
    html += f"<h3 style='color:#{GOLD}'>FOURNISSEURS</h3><table>"
    fou_headers = ["Code Fourn.","Raison Sociale","Catégorie","Contact",
                   "Téléphone","Email","Délai Livraison","Conditions Paiement","Note Qualité"]
    html += _row(*[(h, HEADER_BG, GOLD, "center") for h in fou_headers])
    for f in fous:
        html += _row(
            (f.get("code_fournisseur",""), "1C2B4A", GOLD, "center"),
            (f.get("raison_sociale",""), DARK_GRAY, WHITE, "left"),
            (f.get("categorie",""), DARK_GRAY, "94A3B8", "center"),
            (f.get("contact",""), DARK_GRAY, "94A3B8", "left"),
            (f.get("telephone",""), DARK_GRAY, WHITE, "center"),
            (f.get("email",""), DARK_GRAY, "94A3B8", "left"),
            (f.get("delai_livraison",""), DARK_GRAY, "94A3B8", "center"),
            (f.get("conditions_paiement",""), DARK_GRAY, "94A3B8", "left"),
            (f"{float(f.get('note_qualite') or 0):.1f}/5", DARK_GRAY, GOLD, "center"),
        )
    html += "</table>"

    # ── ENTRÉES ───────────────────────────────────────────────────────────────
    html += f"<h3 style='color:#{GREEN}'>REGISTRE DES ENTRÉES</h3><table>"
    ent_headers = ["N° BE","Date Entrée","Code Article","Désignation","Catégorie",
                   "Qté Reçue","Unité","Prix Unitaire","Valeur Totale (FCFA)",
                   "Fournisseur","N° BL","N° Commande","Réceptionné par","Observations"]
    html += _row(*[(h, HEADER_BG, GREEN, "center") for h in ent_headers])
    total_ent_val = 0.0
    for e in entrees:
        v = float(e.get("valeur_totale") or 0)
        total_ent_val += v
        html += _row(
            (e.get("numero_be",""), "1B4332", GREEN, "center"),
            (str(e.get("date_entree",""))[:10], DARK_GRAY, "94A3B8", "center"),
            (e.get("code_article",""), "1C2B4A", GOLD, "center"),
            (e.get("designation",""), DARK_GRAY, WHITE, "left"),
            (e.get("categorie",""), DARK_GRAY, "94A3B8", "center"),
            (f"{float(e.get('quantite') or 0):.0f}", DARK_GRAY, WHITE, "right"),
            (e.get("unite",""), DARK_GRAY, "94A3B8", "center"),
            (f"{float(e.get('prix_unitaire') or 0):,.0f}", DARK_GRAY, GOLD, "right"),
            (f"{v:,.0f}", "1B4332", GREEN, "right"),
            (e.get("fournisseur",""), DARK_GRAY, "94A3B8", "left"),
            (e.get("numero_bl",""), DARK_GRAY, "94A3B8", "center"),
            (e.get("numero_commande",""), DARK_GRAY, "94A3B8", "center"),
            (e.get("receptionne_par",""), DARK_GRAY, "94A3B8", "left"),
            (e.get("observations",""), DARK_GRAY, "94A3B8", "left"),
        )
    html += _row(
        ("TOTAL", GOLD, NAVY, "right"),
        *[("", GOLD, NAVY, "center")] * 7,
        (f"{total_ent_val:,.0f}", GOLD, NAVY, "right"),
        *[("", GOLD, NAVY, "center")] * 5,
    )
    html += "</table>"

    # ── SORTIES ───────────────────────────────────────────────────────────────
    html += f"<h3 style='color:#{RED_ALERT}'>REGISTRE DES SORTIES</h3><table>"
    sor_headers = ["N° BS","Date Sortie","Code Article","Désignation","Catégorie",
                   "Qté Sortie","Unité","Prix Unitaire","Valeur Totale (FCFA)",
                   "Site/Chantier","Réf. Forage","Demandeur","Autorisé par","Motif de Sortie"]
    html += _row(*[(h, HEADER_BG, RED_ALERT, "center") for h in sor_headers])
    total_sor_val = 0.0
    for s in sorties:
        v = float(s.get("valeur_totale") or 0)
        total_sor_val += v
        html += _row(
            (s.get("numero_bs",""), "4A1519", RED_ALERT, "center"),
            (str(s.get("date_sortie",""))[:10], DARK_GRAY, "94A3B8", "center"),
            (s.get("code_article",""), "1C2B4A", GOLD, "center"),
            (s.get("designation",""), DARK_GRAY, WHITE, "left"),
            (s.get("categorie",""), DARK_GRAY, "94A3B8", "center"),
            (f"{float(s.get('quantite') or 0):.0f}", DARK_GRAY, WHITE, "right"),
            (s.get("unite",""), DARK_GRAY, "94A3B8", "center"),
            (f"{float(s.get('prix_unitaire') or 0):,.0f}", DARK_GRAY, GOLD, "right"),
            (f"{v:,.0f}", "4A1519", RED_ALERT, "right"),
            (s.get("site_chantier",""), DARK_GRAY, "94A3B8", "left"),
            (s.get("reference_forage",""), DARK_GRAY, "94A3B8", "center"),
            (s.get("demandeur",""), DARK_GRAY, "94A3B8", "left"),
            (s.get("autorise_par",""), DARK_GRAY, "94A3B8", "left"),
            (s.get("motif_sortie",""), DARK_GRAY, "94A3B8", "left"),
        )
    html += _row(
        ("TOTAL", GOLD, NAVY, "right"),
        *[("", GOLD, NAVY, "center")] * 7,
        (f"{total_sor_val:,.0f}", GOLD, NAVY, "right"),
        *[("", GOLD, NAVY, "center")] * 5,
    )
    html += "</table>"

    # ── STOCK ACTUEL ─────────────────────────────────────────────────────────
    html += f"<h3 style='color:#{GOLD}'>ÉTAT DU STOCK ACTUEL</h3><table>"
    stk_headers = ["Code","Désignation","Catégorie","Unité","Total Entrées",
                   "Total Sorties","Stock Actuel","Stock Min","Stock Alerte","Stock Max",
                   "Prix Unitaire","Valeur Stock (FCFA)"]
    html += _row(*[(h, HEADER_BG, GOLD, "center") for h in stk_headers])
    total_val_stock = 0.0
    for r in stock:
        stk_val = float(r.get("stock_actuel") or 0)
        val_stk = float(r.get("valeur_stock") or 0)
        total_val_stock += val_stk
        is_crit = stk_val <= float(r.get("stock_min") or 0)
        is_alert = stk_val <= float(r.get("stock_alerte") or 0)
        bg = "4A1519" if is_crit else ("4A3800" if is_alert else DARK_GRAY)
        fg = RED_ALERT if is_crit else ("F59E0B" if is_alert else GREEN)
        html += _row(
            (r.get("code_article",""), "1C2B4A", GOLD, "center"),
            (r.get("designation",""), bg, WHITE, "left"),
            (r.get("categorie",""), bg, "94A3B8", "center"),
            (r.get("unite",""), bg, "94A3B8", "center"),
            (f"{float(r.get('total_entrees') or 0):.0f}", bg, GREEN, "right"),
            (f"{float(r.get('total_sorties') or 0):.0f}", bg, RED_ALERT, "right"),
            (f"{stk_val:.0f}", bg, fg, "right"),
            (f"{float(r.get('stock_min') or 0):.0f}", bg, "94A3B8", "right"),
            (f"{float(r.get('stock_alerte') or 0):.0f}", bg, "F59E0B", "right"),
            (f"{float(r.get('stock_max') or 0):.0f}", bg, "94A3B8", "right"),
            (f"{float(r.get('prix_unitaire') or 0):,.0f}", bg, GOLD, "right"),
            (f"{val_stk:,.0f}", bg, GOLD, "right"),
        )
    html += _row(
        ("TOTAL VALEUR STOCK", GOLD, NAVY, "right"),
        *[("", GOLD, NAVY, "center")] * 10,
        (f"{total_val_stock:,.0f}", GOLD, NAVY, "right"),
    )
    html += "</table>"

    html += "</body></html>"
    path.write_text(html, encoding="utf-8")


# ── Public API ────────────────────────────────────────────────────────────────

def export_magasin_xlsx() -> Path:
    """Export complet magasin en HTML-as-XLS (ouvert par Excel)."""
    tag = date.today().strftime("%Y%m%d")
    path = _unique_export_path(f"Magasin_DiamondDrilling_{tag}.xls")

    try:
        dash    = get_magasin_dashboard()
        arts    = list_articles()
        fous    = list_fournisseurs()
        entrees = list_entrees()
        sorties = list_sorties()
        stock   = get_stock_actuel()

        data = {
            "dashboard": dash,
            "articles": arts,
            "fournisseurs": fous,
            "entrees": entrees,
            "sorties": sorties,
            "stock": stock,
        }
        _html_xls(path, data)
        _log.info("[magasin] export XLS => %s", path)
        return path
    except Exception as exc:
        _log.error("[magasin] export_magasin_xlsx failed: %s", exc)
        raise
