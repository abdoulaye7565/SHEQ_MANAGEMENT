from __future__ import annotations
from datetime import date, datetime
from typing import Any
from app.db.connection import db_session


def _auto_numero() -> str:
    from datetime import date
    today = date.today()
    with db_session() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM accidents WHERE substr(numero,1,7)=?",
            (f"ACC-{today.strftime('%Y%m')}",),
        ).fetchone()[0]
    return f"ACC-{today.strftime('%Y%m')}-{int(count)+1:03d}"


def create_accident(data: dict[str, Any]) -> int:
    numero = _auto_numero()
    with db_session() as conn:
        cursor = conn.execute(
            """INSERT INTO accidents (numero, type_evenement, date_evenement, heure_evenement,
               lieu, zone, description, employe_id, tiers_implique, gravite, jours_arret,
               statut, created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                numero,
                str(data.get("type_evenement") or "presquaccident"),
                str(data.get("date_evenement") or date.today().isoformat()),
                str(data.get("heure_evenement") or "") or None,
                str(data.get("lieu") or "") or None,
                str(data.get("zone") or "") or None,
                str(data.get("description") or "").strip(),
                int(data["employe_id"]) if data.get("employe_id") else None,
                str(data.get("tiers_implique") or "") or None,
                str(data.get("gravite") or "benin"),
                int(data.get("jours_arret") or 0),
                str(data.get("statut") or "ouvert"),
                str(data.get("created_by") or "") or None,
            ),
        )
        return int(cursor.lastrowid)


def update_accident(accident_id: int, data: dict[str, Any]) -> None:
    with db_session() as conn:
        conn.execute(
            """UPDATE accidents SET type_evenement=?, date_evenement=?, heure_evenement=?,
               lieu=?, zone=?, description=?, employe_id=?, tiers_implique=?, gravite=?,
               jours_arret=?, statut=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (
                str(data.get("type_evenement") or "presquaccident"),
                str(data.get("date_evenement") or date.today().isoformat()),
                str(data.get("heure_evenement") or "") or None,
                str(data.get("lieu") or "") or None,
                str(data.get("zone") or "") or None,
                str(data.get("description") or "").strip(),
                int(data["employe_id"]) if data.get("employe_id") else None,
                str(data.get("tiers_implique") or "") or None,
                str(data.get("gravite") or "benin"),
                int(data.get("jours_arret") or 0),
                str(data.get("statut") or "ouvert"),
                accident_id,
            ),
        )


def delete_accident(accident_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM accidents WHERE id=?", (accident_id,))


def get_accident(accident_id: int) -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            """SELECT a.*, COALESCE(e.nom, e.nom_complet) AS employe_nom,
               COALESCE(e.prenom,'') AS employe_prenom
               FROM accidents a
               LEFT JOIN employes e ON e.id_employe = a.employe_id
               WHERE a.id=?""",
            (accident_id,),
        ).fetchone()
        return dict(row) if row else None


def list_accidents(type_ev: str | None = None, gravite: str | None = None, statut: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    wheres = []
    params: list[Any] = []
    if type_ev:
        wheres.append("a.type_evenement=?"); params.append(type_ev)
    if gravite:
        wheres.append("a.gravite=?"); params.append(gravite)
    if statut:
        wheres.append("a.statut=?"); params.append(statut)
    where_sql = f"WHERE {' AND '.join(wheres)}" if wheres else ""
    params.append(limit)
    with db_session() as conn:
        rows = conn.execute(
            f"""SELECT a.*, COALESCE(e.nom, e.nom_complet) AS employe_nom,
               COALESCE(e.prenom,'') AS employe_prenom
               FROM accidents a
               LEFT JOIN employes e ON e.id_employe = a.employe_id
               {where_sql}
               ORDER BY a.date_evenement DESC, a.id DESC
               LIMIT ?""",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def get_accident_summary() -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS total,
               SUM(CASE WHEN type_evenement='accident' THEN 1 ELSE 0 END) AS accidents,
               SUM(CASE WHEN type_evenement='presquaccident' THEN 1 ELSE 0 END) AS presquaccidents,
               SUM(CASE WHEN type_evenement='situation_dangereuse' THEN 1 ELSE 0 END) AS situations,
               SUM(CASE WHEN gravite IN ('grave','fatal') THEN 1 ELSE 0 END) AS graves,
               SUM(CASE WHEN statut='ouvert' THEN 1 ELSE 0 END) AS ouverts,
               COALESCE(SUM(jours_arret),0) AS total_jours_arret
               FROM accidents"""
        ).fetchone()
        return dict(row) if row else {}


def compute_kpis(heures_exposees: float = 1000000.0) -> dict[str, float]:
    """Compute TF (frequency rate) and TG (gravity rate) per million hours."""
    with db_session() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS nb_accidents,
               COALESCE(SUM(jours_arret),0) AS total_jours
               FROM accidents
               WHERE type_evenement='accident' AND gravite != 'benin'"""
        ).fetchone()
    nb = int(row["nb_accidents"] or 0)
    jours = float(row["total_jours"] or 0)
    tf = round(nb * 1_000_000 / heures_exposees, 2) if heures_exposees > 0 else 0.0
    tg = round(jours * 1_000 / heures_exposees, 2) if heures_exposees > 0 else 0.0
    return {"tf": tf, "tg": tg, "nb_accidents": nb, "total_jours_arret": jours}


def list_causes(accident_id: int) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM causes_accidents WHERE accident_id=? ORDER BY type_cause, id",
            (accident_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_cause(accident_id: int, type_cause: str, description: str) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO causes_accidents (accident_id, type_cause, description) VALUES (?,?,?)",
            (accident_id, type_cause, description.strip()),
        )
        return int(cursor.lastrowid)


def delete_cause(cause_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM causes_accidents WHERE id=?", (cause_id,))


def list_actions(accident_id: int) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM actions_accident WHERE accident_id=? ORDER BY date_echeance, id",
            (accident_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_action(accident_id: int, data: dict[str, Any]) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO actions_accident (accident_id, description, responsable, date_echeance, statut) VALUES (?,?,?,?,?)",
            (
                accident_id,
                str(data.get("description") or "").strip(),
                str(data.get("responsable") or "") or None,
                str(data.get("date_echeance") or "") or None,
                str(data.get("statut") or "planifie"),
            ),
        )
        return int(cursor.lastrowid)


def update_action(action_id: int, statut: str) -> None:
    with db_session() as conn:
        conn.execute("UPDATE actions_accident SET statut=? WHERE id=?", (statut, action_id))


def delete_action(action_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM actions_accident WHERE id=?", (action_id,))


def get_accident_options() -> dict[str, list[dict[str, Any]]]:
    with db_session() as conn:
        employees = conn.execute(
            """SELECT e.id_employe AS value,
               COALESCE(e.nom, e.nom_complet)||' '||COALESCE(e.prenom,'') AS label
               FROM employes e WHERE e.statut='actif' ORDER BY label"""
        ).fetchall()
    return {"employees": [{"value": str(r["value"]), "label": str(r["label"]).strip()} for r in employees]}
