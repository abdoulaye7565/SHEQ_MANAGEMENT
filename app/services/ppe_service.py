from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.db.connection import db_session


MOVEMENT_TYPES = {"entree", "sortie", "ajustement"}
AFFECTATION_STATUSES = {"en_service", "retourne", "perdu", "endommage"}
INSPECTION_STATUSES = {"ok", "a_surveiller", "endommage", "hors_service"}


def get_ppe_summary() -> dict[str, int]:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(e.id_epi) AS total_items,
                COALESCE(SUM(s.quantite_disponible), 0) AS stock_total,
                SUM(CASE WHEN COALESCE(s.quantite_disponible, 0) <= COALESCE(s.seuil_minimum, 0) THEN 1 ELSE 0 END) AS low_stock
            FROM epi e
            LEFT JOIN stock_epi s ON s.epi_id = e.id_epi
            WHERE e.actif = 1
            """
        ).fetchone()
        assigned = connection.execute(
            """
            SELECT COALESCE(SUM(quantite), 0) AS total
            FROM affectations_epi
            WHERE statut = 'en_service'
            """
        ).fetchone()
    return {
        "items": int(row["total_items"] or 0),
        "stock_total": int(row["stock_total"] or 0),
        "low_stock": int(row["low_stock"] or 0),
        "assigned": int(assigned["total"] or 0),
    }


def list_ppe_items(search: str = "", include_inactive: bool = False) -> list[dict[str, Any]]:
    pattern = f"%{search.strip()}%"
    where = [] if include_inactive else ["e.actif = 1"]
    params: list[Any] = []
    if search.strip():
        where.append(
            """
            (e.nom LIKE ? OR te.nom LIKE ? OR COALESCE(e.taille, '') LIKE ?
             OR COALESCE(e.marque, '') LIKE ? OR COALESCE(e.modele, '') LIKE ?)
            """
        )
        params.extend([pattern, pattern, pattern, pattern, pattern])
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                e.id_epi,
                e.type_epi_id,
                te.nom AS type_epi,
                e.nom,
                e.taille,
                e.norme,
                e.marque,
                e.modele,
                e.etat,
                e.date_expiration,
                e.actif,
                COALESCE(s.quantite_disponible, 0) AS quantite_disponible,
                COALESCE(s.seuil_minimum, 0) AS seuil_minimum,
                CASE
                    WHEN COALESCE(s.quantite_disponible, 0) <= COALESCE(s.seuil_minimum, 0) THEN 1
                    ELSE 0
                END AS stock_bas
            FROM epi e
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            LEFT JOIN stock_epi s ON s.epi_id = e.id_epi
            {where_sql}
            ORDER BY te.nom, e.nom, e.taille
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def create_ppe_item(values: dict[str, Any]) -> int:
    payload = _clean_item_payload(values)
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO epi (
                type_epi_id, nom, taille, norme, marque, modele, etat, date_expiration, actif
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["type_epi_id"],
                payload["nom"],
                payload["taille"],
                payload["norme"],
                payload["marque"],
                payload["modele"],
                payload["etat"],
                payload["date_expiration"],
                payload["actif"],
            ),
        )
        item_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO stock_epi (epi_id, quantite_disponible, seuil_minimum, date_mise_a_jour)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (item_id, payload["quantite_initiale"], payload["seuil_minimum"]),
        )
        if payload["quantite_initiale"] > 0:
            connection.execute(
                """
                INSERT INTO mouvements_stock_epi (epi_id, type_mouvement, quantite, motif, reference)
                VALUES (?, 'entree', ?, 'Stock initial', ?)
                """,
                (item_id, payload["quantite_initiale"], "INIT"),
            )
        return item_id


def update_ppe_item(item_id: int, values: dict[str, Any]) -> None:
    payload = _clean_item_payload(values, include_stock=False)
    with db_session() as connection:
        cursor = connection.execute(
            """
            UPDATE epi
            SET type_epi_id = ?, nom = ?, taille = ?, norme = ?, marque = ?,
                modele = ?, etat = ?, date_expiration = ?, actif = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_epi = ?
            """,
            (
                payload["type_epi_id"],
                payload["nom"],
                payload["taille"],
                payload["norme"],
                payload["marque"],
                payload["modele"],
                payload["etat"],
                payload["date_expiration"],
                payload["actif"],
                item_id,
            ),
        )
        if not cursor.rowcount:
            raise ValueError("EPI introuvable.")
        if "seuil_minimum" in values:
            threshold = _optional_int(values.get("seuil_minimum")) or 0
            if threshold < 0:
                raise ValueError("Le seuil minimum ne peut pas etre negatif.")
            connection.execute(
                """
                INSERT INTO stock_epi (epi_id, quantite_disponible, seuil_minimum, date_mise_a_jour)
                VALUES (?, 0, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(epi_id) DO UPDATE SET
                    seuil_minimum = excluded.seuil_minimum,
                    date_mise_a_jour = CURRENT_TIMESTAMP
                """,
                (item_id, threshold),
            )


def delete_ppe_item(item_id: int) -> str:
    with db_session() as connection:
        row = connection.execute(
            "SELECT id_epi FROM epi WHERE id_epi = ?",
            (item_id,),
        ).fetchone()
        if not row:
            raise ValueError("EPI introuvable.")
        usage = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM affectations_epi WHERE epi_id = ?) AS assignments,
                (SELECT COUNT(*) FROM mouvements_stock_epi WHERE epi_id = ?) AS movements
            """,
            (item_id, item_id),
        ).fetchone()
        if int(usage["assignments"] or 0) or int(usage["movements"] or 0):
            connection.execute(
                """
                UPDATE epi
                SET actif = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id_epi = ?
                """,
                (item_id,),
            )
            return "desactive"
        connection.execute("DELETE FROM stock_epi WHERE epi_id = ?", (item_id,))
        connection.execute("DELETE FROM epi WHERE id_epi = ?", (item_id,))
        return "supprime"


def record_stock_movement(values: dict[str, Any]) -> None:
    payload = _clean_movement_payload(values)
    with db_session() as connection:
        current = _stock_for_update(connection, payload["epi_id"])
        quantity = payload["quantite"]
        if payload["type_mouvement"] == "entree":
            new_quantity = current + quantity
        elif payload["type_mouvement"] == "sortie":
            if current < quantity:
                raise ValueError("Stock insuffisant pour cette sortie.")
            new_quantity = current - quantity
        else:
            new_quantity = quantity
        connection.execute(
            """
            UPDATE stock_epi
            SET quantite_disponible = ?, date_mise_a_jour = CURRENT_TIMESTAMP
            WHERE epi_id = ?
            """,
            (new_quantity, payload["epi_id"]),
        )
        connection.execute(
            """
            INSERT INTO mouvements_stock_epi (
                epi_id, type_mouvement, quantite, motif, reference
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["epi_id"],
                payload["type_mouvement"],
                quantity,
                payload["motif"],
                payload["reference"],
            ),
        )


def assign_ppe(values: dict[str, Any]) -> int:
    payload = _clean_assignment_payload(values)
    with db_session() as connection:
        current = _stock_for_update(connection, payload["epi_id"])
        if current < payload["quantite"]:
            raise ValueError("Stock insuffisant pour cette affectation.")
        cursor = connection.execute(
            """
            INSERT INTO affectations_epi (
                employe_id, epi_id, quantite, date_remise, statut, observations
            ) VALUES (?, ?, ?, ?, 'en_service', ?)
            """,
            (
                payload["employe_id"],
                payload["epi_id"],
                payload["quantite"],
                payload["date_remise"],
                payload["observations"],
            ),
        )
        assignment_id = int(cursor.lastrowid)
        connection.execute(
            """
            UPDATE stock_epi
            SET quantite_disponible = quantite_disponible - ?,
                date_mise_a_jour = CURRENT_TIMESTAMP
            WHERE epi_id = ?
            """,
            (payload["quantite"], payload["epi_id"]),
        )
        connection.execute(
            """
            INSERT INTO mouvements_stock_epi (
                epi_id, type_mouvement, quantite, motif, reference
            ) VALUES (?, 'sortie', ?, 'Affectation employe', ?)
            """,
            (payload["epi_id"], payload["quantite"], f"AFF-{assignment_id}"),
        )
        return assignment_id


def return_ppe_assignment(
    assignment_id: int,
    return_date: str | None = None,
    status: str = "retourne",
) -> None:
    if status not in AFFECTATION_STATUSES - {"en_service"}:
        raise ValueError("Statut de retour invalide.")
    date_retour = _date_text(return_date or date.today().isoformat(), "Date retour")
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT id_affectation, epi_id, quantite, statut
            FROM affectations_epi
            WHERE id_affectation = ?
            """,
            (assignment_id,),
        ).fetchone()
        if not row:
            raise ValueError("Affectation introuvable.")
        if row["statut"] != "en_service":
            raise ValueError("Cette affectation est deja cloturee.")
        connection.execute(
            """
            UPDATE affectations_epi
            SET statut = ?, date_retour = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id_affectation = ?
            """,
            (status, date_retour, assignment_id),
        )
        if status == "retourne":
            connection.execute(
                """
                UPDATE stock_epi
                SET quantite_disponible = quantite_disponible + ?,
                    date_mise_a_jour = CURRENT_TIMESTAMP
                WHERE epi_id = ?
                """,
                (row["quantite"], row["epi_id"]),
            )
            connection.execute(
                """
                INSERT INTO mouvements_stock_epi (
                    epi_id, type_mouvement, quantite, motif, reference
                ) VALUES (?, 'entree', ?, 'Retour employe', ?)
                """,
                (row["epi_id"], row["quantite"], f"RET-{assignment_id}"),
            )


def list_ppe_assignments(active_only: bool = False) -> list[dict[str, Any]]:
    where = "WHERE ae.statut = 'en_service'" if active_only else ""
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                ae.id_affectation,
                ae.employe_id,
                COALESCE(emp.nom, emp.nom_complet) AS nom,
                COALESCE(emp.prenom, '') AS prenom,
                b.numero_badge,
                ae.epi_id,
                e.nom AS epi,
                te.nom AS type_epi,
                ae.quantite,
                ae.date_remise,
                ae.date_retour,
                ae.statut,
                ae.observations
            FROM affectations_epi ae
            JOIN employes emp ON emp.id_employe = ae.employe_id
            LEFT JOIN badges b ON b.employe_id = emp.id_employe
            JOIN epi e ON e.id_epi = ae.epi_id
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            {where}
            ORDER BY ae.date_remise DESC, nom, prenom
            """
        ).fetchall()
        return [dict(row) for row in rows]


def list_stock_movements(limit: int = 50) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                ms.id_mouvement,
                ms.epi_id,
                e.nom AS epi,
                te.nom AS type_epi,
                ms.type_mouvement,
                ms.quantite,
                ms.date_mouvement,
                ms.motif,
                ms.reference
            FROM mouvements_stock_epi ms
            JOIN epi e ON e.id_epi = ms.epi_id
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            ORDER BY ms.date_mouvement DESC, ms.id_mouvement DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_ppe_alerts() -> list[dict[str, Any]]:
    alerts = [
        {**row, "alerte": "Stock bas"}
        for row in list_ppe_items()
        if int(row.get("stock_bas") or 0)
    ]
    alerts.extend(list_ppe_expiration_alerts())
    return alerts


def get_ppe_options() -> dict[str, list[dict[str, Any]]]:
    with db_session() as connection:
        types = connection.execute(
            """
            SELECT id_type_epi AS value, nom AS label
            FROM types_epi
            WHERE actif = 1
            ORDER BY nom
            """
        ).fetchall()
        employees = connection.execute(
            """
            SELECT e.id_employe AS value,
                   COALESCE(e.nom, e.nom_complet) || ' ' || COALESCE(e.prenom, '') ||
                   ' - ' || COALESCE(b.numero_badge, 'sans badge') AS label
            FROM employes e
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
            ORDER BY label
            """
        ).fetchall()
        items = connection.execute(
            """
            SELECT e.id_epi AS value,
                   te.nom || ' - ' || e.nom || ' (' || COALESCE(e.taille, '-') || ')' AS label
            FROM epi e
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            WHERE e.actif = 1
            ORDER BY te.nom, e.nom
            """
        ).fetchall()
        functions = connection.execute(
            """
            SELECT id_fonction AS value, nom AS label
            FROM fonctions
            WHERE actif = 1
            ORDER BY nom
            """
        ).fetchall()
    return {
        "types": [dict(row) for row in types],
        "employees": [dict(row) for row in employees],
        "items": [dict(row) for row in items],
        "functions": [dict(row) for row in functions],
    }


def list_ppe_requirements() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                req.id_requis,
                req.fonction_id,
                f.nom AS fonction,
                req.type_epi_id,
                te.nom AS type_epi,
                req.quantite,
                req.obligatoire
            FROM epi_requis_fonction req
            JOIN fonctions f ON f.id_fonction = req.fonction_id
            JOIN types_epi te ON te.id_type_epi = req.type_epi_id
            ORDER BY f.nom, te.nom
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_ppe_requirement(values: dict[str, Any]) -> None:
    function_id = _required_int(values.get("fonction_id"), "Fonction")
    type_id = _required_int(values.get("type_epi_id"), "Type EPI")
    quantity = _required_int(values.get("quantite"), "Quantite")
    if quantity <= 0:
        raise ValueError("La quantite requise doit etre superieure a zero.")
    mandatory = 1 if values.get("obligatoire", True) in (1, True, "1", "true", "True", "on") else 0
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO epi_requis_fonction (fonction_id, type_epi_id, quantite, obligatoire)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fonction_id, type_epi_id) DO UPDATE SET
                quantite = excluded.quantite,
                obligatoire = excluded.obligatoire
            """,
            (function_id, type_id, quantity, mandatory),
        )


def delete_ppe_requirement(requirement_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute(
            "DELETE FROM epi_requis_fonction WHERE id_requis = ?",
            (requirement_id,),
        )
        if not cursor.rowcount:
            raise ValueError("Exigence EPI introuvable.")


def list_ppe_compliance() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                emp.id_employe,
                COALESCE(emp.nom, emp.nom_complet) AS nom,
                COALESCE(emp.prenom, '') AS prenom,
                f.nom AS fonction,
                te.nom AS type_epi,
                req.quantite AS requis,
                COALESCE(SUM(CASE WHEN ae.statut = 'en_service' THEN ae.quantite ELSE 0 END), 0) AS affecte,
                CASE
                    WHEN COALESCE(SUM(CASE WHEN ae.statut = 'en_service' THEN ae.quantite ELSE 0 END), 0) >= req.quantite THEN 'conforme'
                    ELSE 'manquant'
                END AS statut
            FROM employes emp
            JOIN fonctions f ON f.id_fonction = emp.fonction_id
            JOIN epi_requis_fonction req ON req.fonction_id = emp.fonction_id
            JOIN types_epi te ON te.id_type_epi = req.type_epi_id
            LEFT JOIN epi e ON e.type_epi_id = req.type_epi_id AND e.actif = 1
            LEFT JOIN affectations_epi ae
                ON ae.epi_id = e.id_epi
               AND ae.employe_id = emp.id_employe
               AND ae.statut = 'en_service'
            WHERE emp.statut = 'actif'
              AND req.obligatoire = 1
            GROUP BY emp.id_employe, emp.nom, emp.prenom, emp.nom_complet, f.nom,
                     te.nom, req.quantite
            ORDER BY statut DESC, fonction, nom, prenom, type_epi
            """
        ).fetchall()
    return [dict(row) for row in rows]


def record_ppe_inspection(values: dict[str, Any]) -> int:
    status = _required_text(values.get("statut"), "Statut")
    if status not in INSPECTION_STATUSES:
        raise ValueError("Statut inspection invalide.")
    inspection_date = _date_text(values.get("date_inspection") or date.today().isoformat(), "Date inspection")
    next_date = _optional_date(values.get("prochaine_inspection"), "Prochaine inspection")
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO epi_inspections (
                epi_id, date_inspection, statut, prochaine_inspection, inspecteur, observations
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _required_int(values.get("epi_id"), "EPI"),
                inspection_date,
                status,
                next_date,
                _optional_text(values.get("inspecteur")),
                _optional_text(values.get("observations")),
            ),
        )
        inspection_id = int(cursor.lastrowid)
        if status in {"endommage", "hors_service"}:
            connection.execute(
                """
                UPDATE epi
                SET etat = ?, actif = CASE WHEN ? = 'hors_service' THEN 0 ELSE actif END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_epi = ?
                """,
                ("endommage", status, _required_int(values.get("epi_id"), "EPI")),
            )
        return inspection_id


def list_ppe_inspections(limit: int = 50) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                pi.id_inspection,
                pi.epi_id,
                e.nom AS epi,
                te.nom AS type_epi,
                pi.date_inspection,
                pi.statut,
                pi.prochaine_inspection,
                pi.inspecteur,
                pi.observations
            FROM epi_inspections pi
            JOIN epi e ON e.id_epi = pi.epi_id
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            ORDER BY pi.date_inspection DESC, pi.id_inspection DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_ppe_expiration_alerts(days: int = 30) -> list[dict[str, Any]]:
    today = date.today()
    limit = today + timedelta(days=days)
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                e.id_epi,
                te.nom AS type_epi,
                e.nom,
                e.date_expiration,
                e.etat,
                COALESCE(s.quantite_disponible, 0) AS quantite_disponible,
                COALESCE(s.seuil_minimum, 0) AS seuil_minimum,
                CASE
                    WHEN e.etat IN ('endommage', 'usage') THEN 'Etat a verifier'
                    WHEN e.date_expiration IS NOT NULL AND e.date_expiration <= ? THEN 'Expiration proche'
                    ELSE 'Inspection a planifier'
                END AS alerte
            FROM epi e
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            LEFT JOIN stock_epi s ON s.epi_id = e.id_epi
            WHERE e.actif = 1
              AND (
                  e.etat IN ('endommage', 'usage')
                  OR (e.date_expiration IS NOT NULL AND e.date_expiration <= ?)
              )
            ORDER BY e.date_expiration, te.nom, e.nom
            """,
            (limit.isoformat(), limit.isoformat()),
        ).fetchall()
    return [dict(row) for row in rows]


def get_ppe_export_data() -> dict[str, list[dict[str, Any]] | dict[str, int]]:
    return {
        "summary": get_ppe_summary(),
        "items": list_ppe_items(),
        "assignments": list_ppe_assignments(active_only=False),
        "requirements": list_ppe_requirements(),
        "compliance": list_ppe_compliance(),
        "inspections": list_ppe_inspections(),
        "alerts": list_ppe_alerts(),
    }


def _stock_for_update(connection: Any, epi_id: int) -> int:
    row = connection.execute(
        "SELECT quantite_disponible FROM stock_epi WHERE epi_id = ?",
        (epi_id,),
    ).fetchone()
    if row is None:
        connection.execute(
            """
            INSERT INTO stock_epi (epi_id, quantite_disponible, seuil_minimum, date_mise_a_jour)
            VALUES (?, 0, 0, CURRENT_TIMESTAMP)
            """,
            (epi_id,),
        )
        return 0
    return int(row["quantite_disponible"] or 0)


def _clean_item_payload(values: dict[str, Any], include_stock: bool = True) -> dict[str, Any]:
    payload = {
        "type_epi_id": _required_int(values.get("type_epi_id"), "Type EPI"),
        "nom": _required_text(values.get("nom"), "Nom EPI"),
        "taille": _optional_text(values.get("taille")),
        "norme": _optional_text(values.get("norme")),
        "marque": _optional_text(values.get("marque")),
        "modele": _optional_text(values.get("modele")),
        "etat": _required_text(values.get("etat", "neuf"), "Etat"),
        "date_expiration": _optional_date(values.get("date_expiration"), "Date expiration"),
        "actif": 1 if values.get("actif", True) in (1, True, "1", "true", "True", "on") else 0,
    }
    if include_stock:
        payload["quantite_initiale"] = _optional_int(values.get("quantite_initiale")) or 0
        payload["seuil_minimum"] = _optional_int(values.get("seuil_minimum")) or 0
        if payload["quantite_initiale"] < 0 or payload["seuil_minimum"] < 0:
            raise ValueError("Les quantites ne peuvent pas etre negatives.")
    return payload


def _clean_movement_payload(values: dict[str, Any]) -> dict[str, Any]:
    movement = _required_text(values.get("type_mouvement"), "Type mouvement")
    if movement not in MOVEMENT_TYPES:
        raise ValueError("Type de mouvement invalide.")
    quantity = _required_int(values.get("quantite"), "Quantite")
    if quantity < 0:
        raise ValueError("La quantite ne peut pas etre negative.")
    return {
        "epi_id": _required_int(values.get("epi_id"), "EPI"),
        "type_mouvement": movement,
        "quantite": quantity,
        "motif": _optional_text(values.get("motif")),
        "reference": _optional_text(values.get("reference")),
    }


def _clean_assignment_payload(values: dict[str, Any]) -> dict[str, Any]:
    quantity = _required_int(values.get("quantite"), "Quantite")
    if quantity <= 0:
        raise ValueError("La quantite doit etre superieure a zero.")
    return {
        "employe_id": _required_int(values.get("employe_id"), "Employe"),
        "epi_id": _required_int(values.get("epi_id"), "EPI"),
        "quantite": quantity,
        "date_remise": _date_text(values.get("date_remise") or date.today().isoformat(), "Date remise"),
        "observations": _optional_text(values.get("observations")),
    }


def _required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Champ obligatoire: {label}")
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _required_int(value: Any, label: str) -> int:
    if value in ("", None):
        raise ValueError(f"Champ obligatoire: {label}")
    return int(value)


def _optional_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    return int(value)


def _optional_date(value: Any, label: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _date_text(text, label)


def _date_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{label}: format invalide AAAA-MM-JJ.") from exc
    return text
