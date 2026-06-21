from __future__ import annotations
from datetime import date, datetime
from typing import Any
from app.db.connection import db_session

PERMIT_TYPES = {
    "hauteur":        "Travail en Hauteur",
    "feu":            "Permis Feu",
    "espace_confine": "Espace Confiné",
    "electrique":     "Travail Électrique",
    "levage":         "Opération de Levage",
    "excavation":     "Fouille / Excavation",
    "general":        "Permis Général",
}

STATUTS = {
    "brouillon":     ("Brouillon",      "#64748B"),
    "en_validation": ("En validation",  "#F59E0B"),
    "valide":        ("Validé",         "#3B82F6"),
    "actif":         ("Actif",          "#10B981"),
    "suspendu":      ("Suspendu",       "#F97316"),
    "clos":          ("Clos",           "#94A3B8"),
}

VALIDATION_ROLES = ["HSE", "Chef des travaux", "Responsable site", "Sécurité"]


def _auto_numero(type_permis: str) -> str:
    prefix = {"hauteur":"PTH","feu":"PTF","espace_confine":"PEC","electrique":"PEL","levage":"PLV","excavation":"PEX"}.get(type_permis, "PTG")
    today = date.today()
    with db_session() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM permis_travail WHERE substr(numero,1,3)=? AND substr(date_emission,1,7)=?",
            (prefix, today.strftime("%Y-%m")),
        ).fetchone()[0]
    return f"{prefix}-{today.strftime('%Y%m')}-{int(count)+1:03d}"


def create_permit(data: dict[str, Any]) -> int:
    type_p = str(data.get("type_permis") or "general")
    numero = _auto_numero(type_p)
    with db_session() as conn:
        cursor = conn.execute(
            """INSERT INTO permis_travail (numero, type_permis, titre, lieu, zone,
               date_emission, date_debut, date_fin, heure_debut, heure_fin,
               description_travaux, effectif, entreprise, responsable_travaux,
               risques, precautions, equipements_requis, statut)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                numero, type_p,
                str(data.get("titre") or "").strip(),
                str(data.get("lieu") or "") or None,
                str(data.get("zone") or "") or None,
                str(data.get("date_emission") or date.today().isoformat()),
                str(data.get("date_debut") or date.today().isoformat()),
                str(data.get("date_fin") or date.today().isoformat()),
                str(data.get("heure_debut") or "") or None,
                str(data.get("heure_fin") or "") or None,
                str(data.get("description_travaux") or "") or None,
                int(data.get("effectif") or 1),
                str(data.get("entreprise") or "") or None,
                str(data.get("responsable_travaux") or "") or None,
                str(data.get("risques") or "") or None,
                str(data.get("precautions") or "") or None,
                str(data.get("equipements_requis") or "") or None,
                str(data.get("statut") or "brouillon"),
            ),
        )
        permit_id = int(cursor.lastrowid)
        for role in VALIDATION_ROLES:
            conn.execute(
                "INSERT INTO validations_permis (permis_id, role_validateur) VALUES (?,?)",
                (permit_id, role),
            )
        return permit_id


def update_permit(permit_id: int, data: dict[str, Any]) -> None:
    with db_session() as conn:
        conn.execute(
            """UPDATE permis_travail SET type_permis=?, titre=?, lieu=?, zone=?,
               date_debut=?, date_fin=?, heure_debut=?, heure_fin=?,
               description_travaux=?, effectif=?, entreprise=?, responsable_travaux=?,
               risques=?, precautions=?, equipements_requis=?, statut=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (
                str(data.get("type_permis") or "general"),
                str(data.get("titre") or "").strip(),
                str(data.get("lieu") or "") or None,
                str(data.get("zone") or "") or None,
                str(data.get("date_debut") or date.today().isoformat()),
                str(data.get("date_fin") or date.today().isoformat()),
                str(data.get("heure_debut") or "") or None,
                str(data.get("heure_fin") or "") or None,
                str(data.get("description_travaux") or "") or None,
                int(data.get("effectif") or 1),
                str(data.get("entreprise") or "") or None,
                str(data.get("responsable_travaux") or "") or None,
                str(data.get("risques") or "") or None,
                str(data.get("precautions") or "") or None,
                str(data.get("equipements_requis") or "") or None,
                str(data.get("statut") or "brouillon"),
                permit_id,
            ),
        )


def delete_permit(permit_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM permis_travail WHERE id=?", (permit_id,))


def get_permit(permit_id: int) -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM permis_travail WHERE id=?", (permit_id,)).fetchone()
        return dict(row) if row else None


def list_permits(type_permis: str | None = None, statut: str | None = None) -> list[dict[str, Any]]:
    wheres, params = [], []
    if type_permis:
        wheres.append("type_permis=?"); params.append(type_permis)
    if statut:
        wheres.append("statut=?"); params.append(statut)
    where_sql = f"WHERE {' AND '.join(wheres)}" if wheres else ""
    with db_session() as conn:
        rows = conn.execute(
            f"SELECT * FROM permis_travail {where_sql} ORDER BY date_emission DESC, id DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def get_permit_summary() -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS total,
               SUM(CASE WHEN statut='actif' THEN 1 ELSE 0 END) AS actifs,
               SUM(CASE WHEN statut='en_validation' THEN 1 ELSE 0 END) AS en_attente,
               SUM(CASE WHEN statut='brouillon' THEN 1 ELSE 0 END) AS brouillons,
               SUM(CASE WHEN statut='suspendu' THEN 1 ELSE 0 END) AS suspendus,
               SUM(CASE WHEN statut='clos' THEN 1 ELSE 0 END) AS clos
               FROM permis_travail"""
        ).fetchone()
    return dict(row) if row else {}


def list_validations(permit_id: int) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM validations_permis WHERE permis_id=? ORDER BY id",
            (permit_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def validate_permit(validation_id: int, nom_validateur: str, statut: str, commentaire: str = "") -> None:
    if statut not in ("valide", "refuse"):
        raise ValueError("Statut invalide.")
    with db_session() as conn:
        conn.execute(
            """UPDATE validations_permis SET nom_validateur=?, statut=?, commentaire=?,
               date_validation=CURRENT_TIMESTAMP WHERE id=?""",
            (nom_validateur.strip(), statut, commentaire.strip() or None, validation_id),
        )
        vrow = conn.execute("SELECT permis_id FROM validations_permis WHERE id=?", (validation_id,)).fetchone()
        if vrow:
            pid = vrow["permis_id"]
            all_v = conn.execute(
                "SELECT statut FROM validations_permis WHERE permis_id=?", (pid,)
            ).fetchall()
            statuts_list = [v["statut"] for v in all_v]
            if "refuse" in statuts_list:
                conn.execute("UPDATE permis_travail SET statut='brouillon', updated_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
            elif all(s == "valide" for s in statuts_list):
                conn.execute("UPDATE permis_travail SET statut='valide', updated_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
            else:
                conn.execute("UPDATE permis_travail SET statut='en_validation', updated_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))


def set_permit_status(permit_id: int, new_statut: str) -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE permis_travail SET statut=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_statut, permit_id),
        )


def get_expiring_permits(days: int = 2) -> list[dict[str, Any]]:
    from datetime import timedelta
    today = date.today()
    deadline = (today + timedelta(days=days)).isoformat()
    with db_session() as conn:
        rows = conn.execute(
            """SELECT * FROM permis_travail
               WHERE statut IN ('actif','valide') AND date_fin<=?
               ORDER BY date_fin""",
            (deadline,),
        ).fetchall()
    return [dict(r) for r in rows]
