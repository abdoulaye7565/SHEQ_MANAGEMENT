"""maintenance_indus_service.py — Gestion complète de la maintenance industrielle.

Tables : maint_equipements, maint_plan_pm, maint_interventions,
         maint_pieces, maint_prestataires
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from app.db.connection import db_session

_log = logging.getLogger(__name__)

# ── Articles (Équipements) ────────────────────────────────────────────────────

def list_equipements(search: str = "", famille: str = "",
                     criticite: str = "", statut: str = "") -> list[dict]:
    q = "SELECT * FROM maint_equipements WHERE 1=1"
    p: list[Any] = []
    if search:
        q += " AND (code_equipement LIKE ? OR designation LIKE ? OR marque LIKE ?)"
        p += [f"%{search}%"] * 3
    if famille:
        q += " AND famille = ?"
        p.append(famille)
    if criticite:
        q += " AND criticite = ?"
        p.append(criticite)
    if statut:
        q += " AND statut = ?"
        p.append(statut)
    q += " ORDER BY criticite, famille, designation"
    try:
        with db_session() as conn:
            return [dict(r) for r in conn.execute(q, p).fetchall()]
    except Exception as exc:
        _log.warning("[maint] list_equipements: %s", exc)
        return []


def get_equipement(code: str) -> dict | None:
    try:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM maint_equipements WHERE code_equipement=?", (code,)
            ).fetchone()
            return dict(row) if row else None
    except Exception as exc:
        _log.warning("[maint] get_equipement: %s", exc)
        return None


def save_equipement(data: dict) -> str:
    code = str(data["code_equipement"]).strip().upper()
    now  = datetime.now().isoformat(timespec="seconds")
    with db_session() as conn:
        ex = conn.execute(
            "SELECT 1 FROM maint_equipements WHERE code_equipement=?", (code,)
        ).fetchone()
        if ex:
            conn.execute(
                """UPDATE maint_equipements SET
                   designation=?,famille=?,sous_famille=?,criticite=?,
                   site_zone=?,emplacement=?,marque=?,modele=?,
                   numero_serie=?,date_mise_en_service=?,capacite_puissance=?,
                   fournisseur=?,valeur_remplacement=?,statut=?,observations=?,updated_at=?
                WHERE code_equipement=?""",
                (data.get("designation",""), data.get("famille",""),
                 data.get("sous_famille",""), data.get("criticite","A"),
                 data.get("site_zone",""), data.get("emplacement",""),
                 data.get("marque",""), data.get("modele",""),
                 data.get("numero_serie",""), data.get("date_mise_en_service",""),
                 data.get("capacite_puissance",""), data.get("fournisseur",""),
                 float(data.get("valeur_remplacement") or 0),
                 data.get("statut","En service"), data.get("observations",""), now, code),
            )
        else:
            conn.execute(
                """INSERT INTO maint_equipements
                   (code_equipement,designation,famille,sous_famille,criticite,
                    site_zone,emplacement,marque,modele,numero_serie,
                    date_mise_en_service,capacite_puissance,fournisseur,
                    valeur_remplacement,statut,observations,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, data.get("designation",""), data.get("famille",""),
                 data.get("sous_famille",""), data.get("criticite","A"),
                 data.get("site_zone",""), data.get("emplacement",""),
                 data.get("marque",""), data.get("modele",""),
                 data.get("numero_serie",""), data.get("date_mise_en_service",""),
                 data.get("capacite_puissance",""), data.get("fournisseur",""),
                 float(data.get("valeur_remplacement") or 0),
                 data.get("statut","En service"), data.get("observations",""), now),
            )
    return code


def delete_equipement(code: str) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM maint_equipements WHERE code_equipement=?", (code,))


def list_familles() -> list[str]:
    try:
        with db_session() as conn:
            rows = conn.execute(
                "SELECT DISTINCT famille FROM maint_equipements "
                "WHERE famille IS NOT NULL AND famille!='' ORDER BY famille"
            ).fetchall()
            return [r[0] for r in rows]
    except Exception:
        return []


# ── Plan PM ───────────────────────────────────────────────────────────────────

def list_plan_pm(code_eq: str = "", frequence: str = "",
                 echu_seulement: bool = False) -> list[dict]:
    q = "SELECT * FROM maint_plan_pm WHERE 1=1"
    p: list[Any] = []
    if code_eq:
        q += " AND code_equipement=?"
        p.append(code_eq)
    if frequence:
        q += " AND frequence=?"
        p.append(frequence)
    q += " ORDER BY code_equipement, frequence"
    try:
        with db_session() as conn:
            rows = [dict(r) for r in conn.execute(q, p).fetchall()]
        if echu_seulement:
            today = date.today().isoformat()
            rows = [r for r in rows if r.get("prochaine_echeance","") and
                    r["prochaine_echeance"] < today]
        return rows
    except Exception as exc:
        _log.warning("[maint] list_plan_pm: %s", exc)
        return []


def save_plan_pm(data: dict) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with db_session() as conn:
        pid = data.get("id_plan")
        if pid:
            conn.execute(
                """UPDATE maint_plan_pm SET
                   code_equipement=?,designation_eq=?,tache=?,frequence=?,
                   derniere_realisation=?,prochaine_echeance=?,duree_h=?,
                   ressources=?,pieces_necessaires=?,instructions=?,
                   responsable=?,actif=?
                WHERE id_plan=?""",
                (data.get("code_equipement",""), data.get("designation_eq",""),
                 data.get("tache",""), data.get("frequence","Mensuel"),
                 data.get("derniere_realisation",""), data.get("prochaine_echeance",""),
                 float(data.get("duree_h") or 0),
                 data.get("ressources",""), data.get("pieces_necessaires",""),
                 data.get("instructions",""), data.get("responsable",""),
                 int(data.get("actif",1)), pid),
            )
            return int(pid)
        else:
            cur = conn.execute(
                """INSERT INTO maint_plan_pm
                   (code_equipement,designation_eq,tache,frequence,
                    derniere_realisation,prochaine_echeance,duree_h,
                    ressources,pieces_necessaires,instructions,responsable,actif,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (data.get("code_equipement",""), data.get("designation_eq",""),
                 data.get("tache",""), data.get("frequence","Mensuel"),
                 data.get("derniere_realisation",""), data.get("prochaine_echeance",""),
                 float(data.get("duree_h") or 0),
                 data.get("ressources",""), data.get("pieces_necessaires",""),
                 data.get("instructions",""), data.get("responsable",""),
                 1, now),
            )
            return cur.lastrowid


def delete_plan_pm(id_plan: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM maint_plan_pm WHERE id_plan=?", (id_plan,))


def _calc_prochaine_echeance(derniere: str, frequence: str) -> str:
    """Calcule la prochaine échéance à partir de la dernière réalisation."""
    deltas = {
        "Journalier": 1, "Hebdomadaire": 7, "Mensuel": 30,
        "Trimestriel": 90, "Semestriel": 180, "Annuel": 365,
        "1 000 h": 45, "2 500 h": 90, "5 000 h": 180, "10 000 h": 365,
    }
    try:
        d = date.fromisoformat(derniere)
        delta = deltas.get(frequence, 30)
        return (d + timedelta(days=delta)).isoformat()
    except Exception:
        return ""


def valider_pm(id_plan: int, date_realisation: str = "") -> None:
    """Marque un PM comme réalisé et calcule la prochaine échéance."""
    real = date_realisation or date.today().isoformat()
    with db_session() as conn:
        row = conn.execute(
            "SELECT frequence FROM maint_plan_pm WHERE id_plan=?", (id_plan,)
        ).fetchone()
        if not row:
            return
        prochaine = _calc_prochaine_echeance(real, row[0])
        conn.execute(
            """UPDATE maint_plan_pm
               SET derniere_realisation=?, prochaine_echeance=?
               WHERE id_plan=?""",
            (real, prochaine, id_plan),
        )


# ── Interventions (OT) ────────────────────────────────────────────────────────

def _next_ot_number() -> str:
    try:
        with db_session() as conn:
            row = conn.execute(
                "SELECT numero_ot FROM maint_interventions ORDER BY id_intervention DESC LIMIT 1"
            ).fetchone()
        if row:
            digits = "".join(c for c in str(row[0]) if c.isdigit())
            n = int(digits[-4:]) + 1 if len(digits) >= 4 else 1
        else:
            n = 1
        return f"OT-{date.today().year}-{n:04d}"
    except Exception:
        return f"OT-{date.today().year}-0001"


def list_interventions(search: str = "", code_eq: str = "",
                       type_maint: str = "", statut: str = "",
                       date_debut: str = "", date_fin: str = "") -> list[dict]:
    q = "SELECT * FROM maint_interventions WHERE 1=1"
    p: list[Any] = []
    if search:
        q += " AND (numero_ot LIKE ? OR designation_eq LIKE ? OR technicien LIKE ? OR nature_panne LIKE ?)"
        p += [f"%{search}%"] * 4
    if code_eq:
        q += " AND code_equipement=?"
        p.append(code_eq)
    if type_maint:
        q += " AND type_maintenance=?"
        p.append(type_maint)
    if statut:
        q += " AND statut=?"
        p.append(statut)
    if date_debut:
        q += " AND date_ouverture>=?"
        p.append(date_debut)
    if date_fin:
        q += " AND date_ouverture<=?"
        p.append(date_fin)
    q += " ORDER BY date_ouverture DESC, id_intervention DESC"
    try:
        with db_session() as conn:
            return [dict(r) for r in conn.execute(q, p).fetchall()]
    except Exception as exc:
        _log.warning("[maint] list_interventions: %s", exc)
        return []


def save_intervention(data: dict) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    cout_mo  = float(data.get("cout_mo") or 0)
    cout_pi  = float(data.get("cout_pieces") or 0)
    cout_tot = round(cout_mo + cout_pi, 2)
    with db_session() as conn:
        eid = data.get("id_intervention")
        vals_common = (
            data.get("numero_ot",""), data.get("date_ouverture",""),
            data.get("date_cloture",""), data.get("code_equipement",""),
            data.get("designation_eq",""), data.get("type_maintenance","Corrective urgente"),
            data.get("nature_panne",""), data.get("description_travaux",""),
            data.get("technicien",""),
            float(data.get("temps_arret") or 0),
            float(data.get("duree_intervention") or 0),
            data.get("pieces_utilisees",""),
            cout_mo, cout_pi, cout_tot,
            data.get("statut","Ouvert"), data.get("observations",""),
        )
        if eid:
            conn.execute(
                """UPDATE maint_interventions SET
                   numero_ot=?,date_ouverture=?,date_cloture=?,
                   code_equipement=?,designation_eq=?,type_maintenance=?,
                   nature_panne=?,description_travaux=?,technicien=?,
                   temps_arret=?,duree_intervention=?,pieces_utilisees=?,
                   cout_mo=?,cout_pieces=?,cout_total=?,statut=?,observations=?
                WHERE id_intervention=?""",
                (*vals_common, eid),
            )
            return int(eid)
        else:
            cur = conn.execute(
                """INSERT INTO maint_interventions
                   (numero_ot,date_ouverture,date_cloture,code_equipement,
                    designation_eq,type_maintenance,nature_panne,description_travaux,
                    technicien,temps_arret,duree_intervention,pieces_utilisees,
                    cout_mo,cout_pieces,cout_total,statut,observations,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*vals_common, now),
            )
            return cur.lastrowid


def cloture_intervention(id_intervention: int, date_cloture: str = "") -> None:
    d = date_cloture or date.today().isoformat()
    with db_session() as conn:
        conn.execute(
            "UPDATE maint_interventions SET statut='Cloture', date_cloture=? WHERE id_intervention=?",
            (d, id_intervention),
        )


def delete_intervention(id_intervention: int) -> None:
    with db_session() as conn:
        conn.execute(
            "DELETE FROM maint_interventions WHERE id_intervention=?", (id_intervention,)
        )


def next_numero_ot() -> str:
    return _next_ot_number()


# ── Pièces de rechange ────────────────────────────────────────────────────────

def list_pieces(search: str = "", criticite: str = "",
                alerte_seulement: bool = False) -> list[dict]:
    q = "SELECT * FROM maint_pieces WHERE 1=1"
    p: list[Any] = []
    if search:
        q += " AND (code_piece LIKE ? OR designation LIKE ? OR reference_fabricant LIKE ?)"
        p += [f"%{search}%"] * 3
    if criticite:
        q += " AND criticite=?"
        p.append(criticite)
    q += " ORDER BY criticite, designation"
    try:
        with db_session() as conn:
            rows = [dict(r) for r in conn.execute(q, p).fetchall()]
        if alerte_seulement:
            rows = [r for r in rows if float(r.get("stock_actuel") or 0) <= float(r.get("stock_min") or 0)]
        return rows
    except Exception as exc:
        _log.warning("[maint] list_pieces: %s", exc)
        return []


def save_piece(data: dict) -> str:
    code = str(data["code_piece"]).strip().upper()
    now  = datetime.now().isoformat(timespec="seconds")
    with db_session() as conn:
        ex = conn.execute(
            "SELECT 1 FROM maint_pieces WHERE code_piece=?", (code,)
        ).fetchone()
        fields = (
            data.get("designation",""), data.get("reference_fabricant",""),
            data.get("equipements_concernes",""), data.get("unite","Pièce"),
            float(data.get("stock_actuel") or 0),
            float(data.get("stock_min") or 0),
            float(data.get("stock_max") or 0),
            data.get("emplacement_magasin",""),
            float(data.get("prix_unitaire") or 0),
            data.get("fournisseur",""),
            int(data.get("delai_appro") or 0),
            data.get("criticite","B"),
            data.get("observations",""),
        )
        if ex:
            conn.execute(
                """UPDATE maint_pieces SET
                   designation=?,reference_fabricant=?,equipements_concernes=?,
                   unite=?,stock_actuel=?,stock_min=?,stock_max=?,
                   emplacement_magasin=?,prix_unitaire=?,fournisseur=?,
                   delai_appro=?,criticite=?,observations=?,updated_at=?
                WHERE code_piece=?""",
                (*fields, now, code),
            )
        else:
            conn.execute(
                """INSERT INTO maint_pieces
                   (code_piece,designation,reference_fabricant,equipements_concernes,
                    unite,stock_actuel,stock_min,stock_max,emplacement_magasin,
                    prix_unitaire,fournisseur,delai_appro,criticite,observations,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, *fields, now),
            )
    return code


def delete_piece(code: str) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM maint_pieces WHERE code_piece=?", (code,))


def ajuster_stock_piece(code: str, delta: float) -> None:
    """Augmente (+) ou diminue (-) le stock d'une pièce."""
    with db_session() as conn:
        conn.execute(
            "UPDATE maint_pieces SET stock_actuel=MAX(0, stock_actuel+?) WHERE code_piece=?",
            (delta, code),
        )


# ── Prestataires ──────────────────────────────────────────────────────────────

def list_prestataires(search: str = "") -> list[dict]:
    q = "SELECT * FROM maint_prestataires WHERE 1=1"
    p: list[Any] = []
    if search:
        q += " AND (code_prestataire LIKE ? OR raison_sociale LIKE ? OR specialite LIKE ?)"
        p += [f"%{search}%"] * 3
    q += " ORDER BY raison_sociale"
    try:
        with db_session() as conn:
            return [dict(r) for r in conn.execute(q, p).fetchall()]
    except Exception as exc:
        _log.warning("[maint] list_prestataires: %s", exc)
        return []


def save_prestataire(data: dict) -> str:
    code = str(data["code_prestataire"]).strip().upper()
    now  = datetime.now().isoformat(timespec="seconds")
    with db_session() as conn:
        ex = conn.execute(
            "SELECT 1 FROM maint_prestataires WHERE code_prestataire=?", (code,)
        ).fetchone()
        fields = (
            data.get("raison_sociale",""), data.get("specialite",""),
            data.get("contact",""), data.get("telephone",""),
            data.get("email",""), data.get("contrat","Non"),
            data.get("type_contrat",""), data.get("debut_contrat",""),
            data.get("fin_contrat",""),
            float(data.get("montant_contrat") or 0),
            float(data.get("note_qualite") or 0),
            data.get("observations",""),
        )
        if ex:
            conn.execute(
                """UPDATE maint_prestataires SET
                   raison_sociale=?,specialite=?,contact=?,telephone=?,email=?,
                   contrat=?,type_contrat=?,debut_contrat=?,fin_contrat=?,
                   montant_contrat=?,note_qualite=?,observations=?
                WHERE code_prestataire=?""",
                (*fields, code),
            )
        else:
            conn.execute(
                """INSERT INTO maint_prestataires
                   (code_prestataire,raison_sociale,specialite,contact,telephone,
                    email,contrat,type_contrat,debut_contrat,fin_contrat,
                    montant_contrat,note_qualite,observations,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, *fields, now),
            )
    return code


def delete_prestataire(code: str) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM maint_prestataires WHERE code_prestataire=?", (code,))


# ── Dashboard & Indicateurs ───────────────────────────────────────────────────

def get_maintenance_dashboard() -> dict:
    try:
        year = date.today().year
        month = date.today().strftime("%Y-%m")
        with db_session() as conn:
            nb_eq       = conn.execute("SELECT COUNT(*) FROM maint_equipements").fetchone()[0]
            nb_eq_actif = conn.execute("SELECT COUNT(*) FROM maint_equipements WHERE statut='En service'").fetchone()[0]
            nb_pm_echus = conn.execute(
                "SELECT COUNT(*) FROM maint_plan_pm WHERE prochaine_echeance<? AND actif=1",
                (date.today().isoformat(),)
            ).fetchone()[0]
            nb_ot_open  = conn.execute(
                "SELECT COUNT(*) FROM maint_interventions WHERE statut IN ('Ouvert','En cours')"
            ).fetchone()[0]
            cout_ytd    = conn.execute(
                f"SELECT COALESCE(SUM(cout_total),0) FROM maint_interventions "
                f"WHERE strftime('%Y',date_ouverture)='{year}'"
            ).fetchone()[0]
            nb_ot_ytd   = conn.execute(
                f"SELECT COUNT(*) FROM maint_interventions "
                f"WHERE strftime('%Y',date_ouverture)='{year}'"
            ).fetchone()[0]
            nb_cm_ytd   = conn.execute(
                f"SELECT COUNT(*) FROM maint_interventions "
                f"WHERE strftime('%Y',date_ouverture)='{year}' "
                f"AND type_maintenance LIKE 'Corrective%'"
            ).fetchone()[0]
            nb_pm_ytd   = nb_ot_ytd - nb_cm_ytd
            h_arret_ytd = conn.execute(
                f"SELECT COALESCE(SUM(temps_arret),0) FROM maint_interventions "
                f"WHERE strftime('%Y',date_ouverture)='{year}'"
            ).fetchone()[0]
            nb_alerte_pieces = conn.execute(
                "SELECT COUNT(*) FROM maint_pieces WHERE stock_actuel<=stock_min"
            ).fetchone()[0]
            valeur_parc = conn.execute(
                "SELECT COALESCE(SUM(valeur_remplacement),0) FROM maint_equipements"
            ).fetchone()[0]

            # Dernières interventions
            recent_ot = conn.execute(
                """SELECT numero_ot,date_ouverture,designation_eq,type_maintenance,
                          technicien,statut,cout_total
                   FROM maint_interventions ORDER BY date_ouverture DESC, id_intervention DESC LIMIT 6"""
            ).fetchall()

            # PM échus
            pm_echus = conn.execute(
                """SELECT p.id_plan, p.code_equipement, p.designation_eq, p.tache,
                          p.frequence, p.prochaine_echeance, e.criticite
                   FROM maint_plan_pm p
                   LEFT JOIN maint_equipements e ON e.code_equipement=p.code_equipement
                   WHERE p.prochaine_echeance<? AND p.actif=1
                   ORDER BY e.criticite, p.prochaine_echeance
                   LIMIT 10""",
                (date.today().isoformat(),)
            ).fetchall()

            # Alertes pièces
            alerte_pieces = conn.execute(
                "SELECT code_piece,designation,stock_actuel,stock_min,criticite,fournisseur "
                "FROM maint_pieces WHERE stock_actuel<=stock_min ORDER BY criticite LIMIT 8"
            ).fetchall()

            # Mouvements mensuels
            monthly = conn.execute(
                f"""
                SELECT m, COALESCE(nb_pm,0), COALESCE(nb_cm,0),
                       COALESCE(h_arr,0), COALESCE(cout,0)
                FROM (SELECT value AS m FROM json_each('[1,2,3,4,5,6,7,8,9,10,11,12]')) months
                LEFT JOIN (
                    SELECT CAST(strftime('%m',date_ouverture) AS INTEGER) AS m,
                           SUM(CASE WHEN type_maintenance LIKE 'Preventive%' OR type_maintenance LIKE 'Préventive%' THEN 1 ELSE 0 END) AS nb_pm,
                           SUM(CASE WHEN type_maintenance LIKE 'Corrective%' THEN 1 ELSE 0 END) AS nb_cm,
                           SUM(temps_arret) AS h_arr,
                           SUM(cout_total) AS cout
                    FROM maint_interventions WHERE strftime('%Y',date_ouverture)='{year}'
                    GROUP BY m
                ) mv USING(m) ORDER BY m
                """
            ).fetchall()

        month_names = ["Jan","Fév","Mar","Avr","Mai","Jun",
                       "Jul","Aoû","Sep","Oct","Nov","Déc"]
        ratio_pm = round(nb_pm_ytd / nb_ot_ytd * 100, 1) if nb_ot_ytd > 0 else 0

        return {
            "nb_equipements":     int(nb_eq),
            "nb_eq_actif":        int(nb_eq_actif),
            "nb_pm_echus":        int(nb_pm_echus),
            "nb_ot_open":         int(nb_ot_open),
            "cout_ytd":           float(cout_ytd),
            "nb_ot_ytd":          int(nb_ot_ytd),
            "nb_pm_ytd":          int(nb_pm_ytd),
            "nb_cm_ytd":          int(nb_cm_ytd),
            "h_arret_ytd":        float(h_arret_ytd),
            "nb_alerte_pieces":   int(nb_alerte_pieces),
            "valeur_parc":        float(valeur_parc),
            "ratio_pm":           ratio_pm,
            "recent_ot":          [dict(r) for r in recent_ot],
            "pm_echus":           [dict(r) for r in pm_echus],
            "alerte_pieces":      [dict(r) for r in alerte_pieces],
            "monthly":            [
                {"mois": month_names[r[0]-1], "nb_pm": r[1], "nb_cm": r[2],
                 "h_arret": float(r[3]), "cout": float(r[4])}
                for r in monthly
            ],
        }
    except Exception as exc:
        _log.warning("[maint] get_maintenance_dashboard: %s", exc)
        return {k: 0 for k in [
            "nb_equipements","nb_eq_actif","nb_pm_echus","nb_ot_open",
            "cout_ytd","nb_ot_ytd","nb_pm_ytd","nb_cm_ytd","h_arret_ytd",
            "nb_alerte_pieces","valeur_parc","ratio_pm",
        ]} | {"recent_ot":[], "pm_echus":[], "alerte_pieces":[], "monthly":[]}


def get_indicateurs_mtbf() -> list[dict]:
    """Calcule MTBF, MTTR, Disponibilité par équipement (pannes YTD)."""
    try:
        year = date.today().year
        with db_session() as conn:
            rows = conn.execute(
                f"""
                SELECT e.code_equipement, e.designation, e.famille, e.criticite,
                       COUNT(i.id_intervention) AS nb_pannes,
                       COALESCE(SUM(i.temps_arret),0) AS total_arret,
                       COALESCE(SUM(i.duree_intervention),0) AS total_interv
                FROM maint_equipements e
                LEFT JOIN maint_interventions i
                    ON i.code_equipement=e.code_equipement
                    AND i.type_maintenance LIKE 'Corrective%'
                    AND strftime('%Y',i.date_ouverture)='{year}'
                GROUP BY e.code_equipement
                ORDER BY e.criticite, nb_pannes DESC
                """
            ).fetchall()
        result = []
        heures_annee = 8760
        for r in rows:
            nb = int(r[4])
            arret = float(r[5])
            mtbf = round((heures_annee - arret) / nb, 1) if nb > 0 else heures_annee
            mttr = round(arret / nb, 1) if nb > 0 else 0
            dispo = round(mtbf / (mtbf + mttr) * 100, 1) if (mtbf + mttr) > 0 else 100.0
            result.append({
                "code_equipement": r[0], "designation": r[1],
                "famille": r[2], "criticite": r[3],
                "nb_pannes": nb, "total_arret": arret,
                "mtbf": mtbf, "mttr": mttr, "disponibilite": dispo,
            })
        return result
    except Exception as exc:
        _log.warning("[maint] get_indicateurs_mtbf: %s", exc)
        return []
