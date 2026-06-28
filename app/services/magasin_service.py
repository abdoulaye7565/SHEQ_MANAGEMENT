"""magasin_service.py — Gestion du Magasin Diamond Drilling.

Tables : magasin_articles, magasin_fournisseurs, magasin_entrees, magasin_sorties
Toutes les opérations passent par db_session.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.db.connection import db_session

_log = logging.getLogger(__name__)


# ── Articles (Catalogue) ─────────────────────────────────────────────────────

def list_articles(search: str = "", categorie: str = "") -> list[dict[str, Any]]:
    q = "SELECT * FROM magasin_articles WHERE 1=1"
    params: list[Any] = []
    if search:
        q += " AND (code_article LIKE ? OR designation LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if categorie:
        q += " AND categorie = ?"
        params.append(categorie)
    q += " ORDER BY categorie, designation"
    try:
        with db_session() as conn:
            return [dict(r) for r in conn.execute(q, params).fetchall()]
    except Exception as exc:
        _log.warning("[magasin] list_articles failed: %s", exc)
        return []


def get_article(code_article: str) -> dict[str, Any] | None:
    try:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM magasin_articles WHERE code_article = ?", (code_article,)
            ).fetchone()
            return dict(row) if row else None
    except Exception as exc:
        _log.warning("[magasin] get_article failed: %s", exc)
        return None


def save_article(data: dict[str, Any]) -> str:
    code = str(data["code_article"]).strip().upper()
    now = datetime.now().isoformat(timespec="seconds")
    with db_session() as conn:
        existing = conn.execute(
            "SELECT id_article FROM magasin_articles WHERE code_article = ?", (code,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE magasin_articles SET
                    designation=?, categorie=?, sous_categorie=?, unite=?,
                    stock_min=?, stock_max=?, stock_alerte=?, prix_unitaire=?,
                    fournisseur_prefere=?, emplacement=?, observations=?, updated_at=?
                WHERE code_article=?""",
                (
                    data.get("designation", ""),
                    data.get("categorie", ""),
                    data.get("sous_categorie", ""),
                    data.get("unite", ""),
                    float(data.get("stock_min") or 0),
                    float(data.get("stock_max") or 0),
                    float(data.get("stock_alerte") or 0),
                    float(data.get("prix_unitaire") or 0),
                    data.get("fournisseur_prefere", ""),
                    data.get("emplacement", ""),
                    data.get("observations", ""),
                    now,
                    code,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO magasin_articles
                   (code_article, designation, categorie, sous_categorie, unite,
                    stock_min, stock_max, stock_alerte, prix_unitaire,
                    fournisseur_prefere, emplacement, observations, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    code,
                    data.get("designation", ""),
                    data.get("categorie", ""),
                    data.get("sous_categorie", ""),
                    data.get("unite", ""),
                    float(data.get("stock_min") or 0),
                    float(data.get("stock_max") or 0),
                    float(data.get("stock_alerte") or 0),
                    float(data.get("prix_unitaire") or 0),
                    data.get("fournisseur_prefere", ""),
                    data.get("emplacement", ""),
                    data.get("observations", ""),
                    now,
                ),
            )
    return code


def delete_article(code_article: str) -> None:
    with db_session() as conn:
        conn.execute(
            "DELETE FROM magasin_articles WHERE code_article = ?", (code_article,)
        )


def list_categories_articles() -> list[str]:
    try:
        with db_session() as conn:
            rows = conn.execute(
                "SELECT DISTINCT categorie FROM magasin_articles WHERE categorie IS NOT NULL AND categorie != '' ORDER BY categorie"
            ).fetchall()
            return [r[0] for r in rows]
    except Exception as exc:
        _log.warning("[magasin] list_categories_articles failed: %s", exc)
        return []


# ── Fournisseurs ──────────────────────────────────────────────────────────────

def list_fournisseurs(search: str = "") -> list[dict[str, Any]]:
    q = "SELECT * FROM magasin_fournisseurs WHERE 1=1"
    params: list[Any] = []
    if search:
        q += " AND (code_fournisseur LIKE ? OR raison_sociale LIKE ? OR contact LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    q += " ORDER BY raison_sociale"
    try:
        with db_session() as conn:
            return [dict(r) for r in conn.execute(q, params).fetchall()]
    except Exception as exc:
        _log.warning("[magasin] list_fournisseurs failed: %s", exc)
        return []


def save_fournisseur(data: dict[str, Any]) -> str:
    code = str(data["code_fournisseur"]).strip().upper()
    now = datetime.now().isoformat(timespec="seconds")
    with db_session() as conn:
        existing = conn.execute(
            "SELECT id_fournisseur FROM magasin_fournisseurs WHERE code_fournisseur = ?", (code,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE magasin_fournisseurs SET
                    raison_sociale=?, categorie=?, contact=?, telephone=?, email=?,
                    delai_livraison=?, conditions_paiement=?, note_qualite=?
                WHERE code_fournisseur=?""",
                (
                    data.get("raison_sociale", ""),
                    data.get("categorie", ""),
                    data.get("contact", ""),
                    data.get("telephone", ""),
                    data.get("email", ""),
                    data.get("delai_livraison", ""),
                    data.get("conditions_paiement", ""),
                    float(data.get("note_qualite") or 0),
                    code,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO magasin_fournisseurs
                   (code_fournisseur, raison_sociale, categorie, contact, telephone,
                    email, delai_livraison, conditions_paiement, note_qualite, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    code,
                    data.get("raison_sociale", ""),
                    data.get("categorie", ""),
                    data.get("contact", ""),
                    data.get("telephone", ""),
                    data.get("email", ""),
                    data.get("delai_livraison", ""),
                    data.get("conditions_paiement", ""),
                    float(data.get("note_qualite") or 0),
                    now,
                ),
            )
    return code


def delete_fournisseur(code_fournisseur: str) -> None:
    with db_session() as conn:
        conn.execute(
            "DELETE FROM magasin_fournisseurs WHERE code_fournisseur = ?", (code_fournisseur,)
        )


# ── Entrées (Bons d'Entrée) ───────────────────────────────────────────────────

def list_entrees(
    search: str = "",
    code_article: str = "",
    date_debut: str = "",
    date_fin: str = "",
) -> list[dict[str, Any]]:
    q = "SELECT * FROM magasin_entrees WHERE 1=1"
    params: list[Any] = []
    if search:
        q += " AND (numero_be LIKE ? OR designation LIKE ? OR fournisseur LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if code_article:
        q += " AND code_article = ?"
        params.append(code_article)
    if date_debut:
        q += " AND date_entree >= ?"
        params.append(date_debut)
    if date_fin:
        q += " AND date_entree <= ?"
        params.append(date_fin)
    q += " ORDER BY date_entree DESC, numero_be DESC"
    try:
        with db_session() as conn:
            return [dict(r) for r in conn.execute(q, params).fetchall()]
    except Exception as exc:
        _log.warning("[magasin] list_entrees failed: %s", exc)
        return []


def save_entree(data: dict[str, Any]) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    qte   = float(data.get("quantite") or 0)
    prix  = float(data.get("prix_unitaire") or 0)
    valeur = round(qte * prix, 2)
    with db_session() as conn:
        eid = data.get("id_entree")
        if eid:
            conn.execute(
                """UPDATE magasin_entrees SET
                    numero_be=?, date_entree=?, code_article=?, designation=?,
                    categorie=?, quantite=?, unite=?, prix_unitaire=?, valeur_totale=?,
                    fournisseur=?, numero_bl=?, numero_commande=?, receptionne_par=?, observations=?
                WHERE id_entree=?""",
                (
                    data.get("numero_be", ""), data.get("date_entree", ""),
                    data.get("code_article", ""), data.get("designation", ""),
                    data.get("categorie", ""), qte, data.get("unite", ""),
                    prix, valeur,
                    data.get("fournisseur", ""), data.get("numero_bl", ""),
                    data.get("numero_commande", ""), data.get("receptionne_par", ""),
                    data.get("observations", ""), eid,
                ),
            )
            return int(eid)
        else:
            cur = conn.execute(
                """INSERT INTO magasin_entrees
                   (numero_be, date_entree, code_article, designation, categorie,
                    quantite, unite, prix_unitaire, valeur_totale, fournisseur,
                    numero_bl, numero_commande, receptionne_par, observations, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data.get("numero_be", ""), data.get("date_entree", ""),
                    data.get("code_article", ""), data.get("designation", ""),
                    data.get("categorie", ""), qte, data.get("unite", ""),
                    prix, valeur,
                    data.get("fournisseur", ""), data.get("numero_bl", ""),
                    data.get("numero_commande", ""), data.get("receptionne_par", ""),
                    data.get("observations", ""), now,
                ),
            )
            return cur.lastrowid


def delete_entree(id_entree: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM magasin_entrees WHERE id_entree = ?", (id_entree,))


def next_numero_be() -> str:
    try:
        with db_session() as conn:
            row = conn.execute(
                "SELECT numero_be FROM magasin_entrees ORDER BY id_entree DESC LIMIT 1"
            ).fetchone()
        if row:
            last = str(row[0])
            digits = "".join(c for c in last if c.isdigit())
            n = int(digits) + 1 if digits else 1
        else:
            n = 1
        return f"BE-{date.today().year}-{n:04d}"
    except Exception:
        return f"BE-{date.today().year}-0001"


# ── Sorties (Bons de Sortie) ──────────────────────────────────────────────────

def list_sorties(
    search: str = "",
    code_article: str = "",
    date_debut: str = "",
    date_fin: str = "",
) -> list[dict[str, Any]]:
    q = "SELECT * FROM magasin_sorties WHERE 1=1"
    params: list[Any] = []
    if search:
        q += " AND (numero_bs LIKE ? OR designation LIKE ? OR demandeur LIKE ? OR site_chantier LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"]
    if code_article:
        q += " AND code_article = ?"
        params.append(code_article)
    if date_debut:
        q += " AND date_sortie >= ?"
        params.append(date_debut)
    if date_fin:
        q += " AND date_sortie <= ?"
        params.append(date_fin)
    q += " ORDER BY date_sortie DESC, numero_bs DESC"
    try:
        with db_session() as conn:
            return [dict(r) for r in conn.execute(q, params).fetchall()]
    except Exception as exc:
        _log.warning("[magasin] list_sorties failed: %s", exc)
        return []


def save_sortie(data: dict[str, Any]) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    qte   = float(data.get("quantite") or 0)
    prix  = float(data.get("prix_unitaire") or 0)
    valeur = round(qte * prix, 2)
    with db_session() as conn:
        sid = data.get("id_sortie")
        if sid:
            conn.execute(
                """UPDATE magasin_sorties SET
                    numero_bs=?, date_sortie=?, code_article=?, designation=?,
                    categorie=?, quantite=?, unite=?, prix_unitaire=?, valeur_totale=?,
                    site_chantier=?, reference_forage=?, demandeur=?, autorise_par=?, motif_sortie=?
                WHERE id_sortie=?""",
                (
                    data.get("numero_bs", ""), data.get("date_sortie", ""),
                    data.get("code_article", ""), data.get("designation", ""),
                    data.get("categorie", ""), qte, data.get("unite", ""),
                    prix, valeur,
                    data.get("site_chantier", ""), data.get("reference_forage", ""),
                    data.get("demandeur", ""), data.get("autorise_par", ""),
                    data.get("motif_sortie", ""), sid,
                ),
            )
            return int(sid)
        else:
            cur = conn.execute(
                """INSERT INTO magasin_sorties
                   (numero_bs, date_sortie, code_article, designation, categorie,
                    quantite, unite, prix_unitaire, valeur_totale, site_chantier,
                    reference_forage, demandeur, autorise_par, motif_sortie, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data.get("numero_bs", ""), data.get("date_sortie", ""),
                    data.get("code_article", ""), data.get("designation", ""),
                    data.get("categorie", ""), qte, data.get("unite", ""),
                    prix, valeur,
                    data.get("site_chantier", ""), data.get("reference_forage", ""),
                    data.get("demandeur", ""), data.get("autorise_par", ""),
                    data.get("motif_sortie", ""), now,
                ),
            )
            return cur.lastrowid


def delete_sortie(id_sortie: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM magasin_sorties WHERE id_sortie = ?", (id_sortie,))


def next_numero_bs() -> str:
    try:
        with db_session() as conn:
            row = conn.execute(
                "SELECT numero_bs FROM magasin_sorties ORDER BY id_sortie DESC LIMIT 1"
            ).fetchone()
        if row:
            last = str(row[0])
            digits = "".join(c for c in last if c.isdigit())
            n = int(digits) + 1 if digits else 1
        else:
            n = 1
        return f"BS-{date.today().year}-{n:04d}"
    except Exception:
        return f"BS-{date.today().year}-0001"


# ── Stock calculé ─────────────────────────────────────────────────────────────

def get_stock_actuel() -> list[dict[str, Any]]:
    """Return all articles with computed stock = total_entrees - total_sorties."""
    try:
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.code_article,
                    a.designation,
                    a.categorie,
                    a.sous_categorie,
                    a.unite,
                    a.stock_min,
                    a.stock_max,
                    a.stock_alerte,
                    a.prix_unitaire,
                    a.fournisseur_prefere,
                    a.emplacement,
                    COALESCE(e.total_entrees, 0)  AS total_entrees,
                    COALESCE(s.total_sorties, 0)  AS total_sorties,
                    COALESCE(e.total_entrees, 0) - COALESCE(s.total_sorties, 0) AS stock_actuel,
                    (COALESCE(e.total_entrees, 0) - COALESCE(s.total_sorties, 0))
                        * a.prix_unitaire AS valeur_stock
                FROM magasin_articles a
                LEFT JOIN (
                    SELECT code_article, SUM(quantite) AS total_entrees
                    FROM magasin_entrees GROUP BY code_article
                ) e ON e.code_article = a.code_article
                LEFT JOIN (
                    SELECT code_article, SUM(quantite) AS total_sorties
                    FROM magasin_sorties GROUP BY code_article
                ) s ON s.code_article = a.code_article
                ORDER BY a.categorie, a.designation
                """
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        _log.warning("[magasin] get_stock_actuel failed: %s", exc)
        return []


def get_stock_alerts() -> list[dict[str, Any]]:
    """Articles where stock_actuel <= stock_alerte."""
    rows = get_stock_actuel()
    return [
        r for r in rows
        if r["stock_actuel"] <= r["stock_alerte"] and r["code_article"]
    ]


# ── Dashboard KPIs ────────────────────────────────────────────────────────────

def get_magasin_dashboard() -> dict[str, Any]:
    try:
        with db_session() as conn:
            nb_articles = conn.execute(
                "SELECT COUNT(*) FROM magasin_articles"
            ).fetchone()[0]
            nb_fournisseurs = conn.execute(
                "SELECT COUNT(*) FROM magasin_fournisseurs"
            ).fetchone()[0]
            total_entrees_valeur = conn.execute(
                "SELECT COALESCE(SUM(valeur_totale), 0) FROM magasin_entrees"
            ).fetchone()[0]
            total_sorties_valeur = conn.execute(
                "SELECT COALESCE(SUM(valeur_totale), 0) FROM magasin_sorties"
            ).fetchone()[0]
            nb_entrees = conn.execute(
                "SELECT COUNT(*) FROM magasin_entrees"
            ).fetchone()[0]
            nb_sorties = conn.execute(
                "SELECT COUNT(*) FROM magasin_sorties"
            ).fetchone()[0]

            # Stock value
            stock_rows = conn.execute(
                """
                SELECT COALESCE(SUM(
                    (COALESCE(e.qte,0) - COALESCE(s.qte,0)) * a.prix_unitaire
                ), 0)
                FROM magasin_articles a
                LEFT JOIN (SELECT code_article, SUM(quantite) qte FROM magasin_entrees GROUP BY code_article) e
                    ON e.code_article = a.code_article
                LEFT JOIN (SELECT code_article, SUM(quantite) qte FROM magasin_sorties GROUP BY code_article) s
                    ON s.code_article = a.code_article
                """
            ).fetchone()[0]

            # Monthly movements (current year)
            year = date.today().year
            monthly = conn.execute(
                f"""
                SELECT m, COALESCE(ent,0), COALESCE(sor,0)
                FROM (
                    SELECT value AS m FROM json_each('[1,2,3,4,5,6,7,8,9,10,11,12]')
                ) months
                LEFT JOIN (
                    SELECT CAST(strftime('%m', date_entree) AS INTEGER) AS m, SUM(valeur_totale) AS ent
                    FROM magasin_entrees WHERE strftime('%Y', date_entree) = '{year}'
                    GROUP BY m
                ) e USING(m)
                LEFT JOIN (
                    SELECT CAST(strftime('%m', date_sortie) AS INTEGER) AS m, SUM(valeur_totale) AS sor
                    FROM magasin_sorties WHERE strftime('%Y', date_sortie) = '{year}'
                    GROUP BY m
                ) s USING(m)
                ORDER BY m
                """
            ).fetchall()

            # Recent movements
            recent_entrees = conn.execute(
                """SELECT numero_be, date_entree, designation, quantite, unite, valeur_totale
                   FROM magasin_entrees ORDER BY date_entree DESC, id_entree DESC LIMIT 5"""
            ).fetchall()
            recent_sorties = conn.execute(
                """SELECT numero_bs, date_sortie, designation, quantite, unite, valeur_totale, demandeur
                   FROM magasin_sorties ORDER BY date_sortie DESC, id_sortie DESC LIMIT 5"""
            ).fetchall()

        alerts = get_stock_alerts()
        nb_critiques = sum(1 for a in alerts if a["stock_actuel"] <= a["stock_min"])

        month_names = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
        monthly_data = [
            {
                "mois": month_names[r[0] - 1],
                "entrees": float(r[1]),
                "sorties": float(r[2]),
                "solde": float(r[1]) - float(r[2]),
            }
            for r in monthly
        ]

        return {
            "nb_articles":          int(nb_articles),
            "nb_fournisseurs":      int(nb_fournisseurs),
            "nb_entrees":           int(nb_entrees),
            "nb_sorties":           int(nb_sorties),
            "total_entrees_valeur": float(total_entrees_valeur),
            "total_sorties_valeur": float(total_sorties_valeur),
            "valeur_stock_actuel":  float(stock_rows),
            "nb_alertes":           len(alerts),
            "nb_critiques":         int(nb_critiques),
            "monthly":              monthly_data,
            "recent_entrees":       [dict(r) for r in recent_entrees],
            "recent_sorties":       [dict(r) for r in recent_sorties],
            "alerts":               alerts[:10],
        }
    except Exception as exc:
        _log.warning("[magasin] get_magasin_dashboard failed: %s", exc)
        return {
            "nb_articles": 0, "nb_fournisseurs": 0,
            "nb_entrees": 0, "nb_sorties": 0,
            "total_entrees_valeur": 0, "total_sorties_valeur": 0,
            "valeur_stock_actuel": 0, "nb_alertes": 0, "nb_critiques": 0,
            "monthly": [], "recent_entrees": [], "recent_sorties": [], "alerts": [],
        }
