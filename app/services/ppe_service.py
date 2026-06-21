from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.db.connection import db_session
from app.services.audit_service import record_system_audit


MOVEMENT_TYPES = {"entree", "sortie", "ajustement"}
AFFECTATION_STATUSES = {"en_service", "retourne", "perdu", "endommage"}
INSPECTION_STATUSES = {"ok", "a_surveiller", "endommage", "hors_service"}


def get_ppe_summary() -> dict[str, int]:
    today = date.today().isoformat()
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
        expired = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM epi
            WHERE actif = 1
              AND date_expiration IS NOT NULL
              AND date_expiration < ?
            """,
            (today,),
        ).fetchone()
        overdue = connection.execute(
            """
            SELECT COUNT(DISTINCT epi_id) AS total
            FROM epi_inspections
            WHERE prochaine_inspection IS NOT NULL
              AND prochaine_inspection < ?
            """,
            (today,),
        ).fetchone()
    compliance = list_ppe_employee_compliance_summary()
    compliant = sum(1 for item in compliance if item.get("statut") == "conforme")
    compliance_rate = round(compliant / len(compliance) * 100) if compliance else 100
    stock_total = int(row["stock_total"] or 0)
    assigned_total = int(assigned["total"] or 0)
    return {
        "items": int(row["total_items"] or 0),
        "stock_total": stock_total,
        "low_stock": int(row["low_stock"] or 0),
        "assigned": assigned_total,
        "available": stock_total,
        "expired": int(expired["total"] or 0),
        "overdue_inspections": int(overdue["total"] or 0),
        "compliance_rate": compliance_rate,
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
        result = item_id
    record_system_audit("create_ppe_item", "ppe", str(result), f"nom={payload['nom']};stock={payload['quantite_initiale']}")
    return result


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
    record_system_audit("update_ppe_item", "ppe", str(item_id), f"nom={payload['nom']}")


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
            result = "desactive"
        else:
            connection.execute("DELETE FROM stock_epi WHERE epi_id = ?", (item_id,))
            connection.execute("DELETE FROM epi WHERE id_epi = ?", (item_id,))
            result = "supprime"
    record_system_audit("delete_ppe_item", "ppe", str(item_id), f"resultat={result}")
    return result


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
    record_system_audit(
        "ppe_stock_movement",
        "ppe",
        str(payload["epi_id"]),
        f"type={payload['type_mouvement']};quantite={payload['quantite']};motif={payload['motif'] or '-'}",
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
        result = assignment_id
    record_system_audit("assign_ppe", "ppe_assignment", str(result), f"employe={payload['employe_id']};epi={payload['epi_id']};quantite={payload['quantite']}")
    return result


def assign_multiple_ppe(
    employee_id: Any,
    items: list[dict[str, Any]],
    issue_date: Any = None,
    observations: Any = None,
) -> list[int]:
    employe_id = _required_int(employee_id, "Employe")
    date_remise = _date_text(issue_date or date.today().isoformat(), "Date remise")
    if not items:
        raise ValueError("Ajoute au moins un EPI a la dotation.")
    quantities: dict[int, int] = {}
    for item in items:
        epi_id = _required_int(item.get("epi_id"), "EPI")
        quantity = _required_int(item.get("quantite"), "Quantite")
        if quantity <= 0:
            raise ValueError("La quantite doit etre superieure a zero.")
        quantities[epi_id] = quantities.get(epi_id, 0) + quantity

    assignment_ids: list[int] = []
    with db_session() as connection:
        for epi_id, quantity in quantities.items():
            if _stock_for_update(connection, epi_id) < quantity:
                row = connection.execute("SELECT nom FROM epi WHERE id_epi = ?", (epi_id,)).fetchone()
                raise ValueError(f"Stock insuffisant pour {row['nom'] if row else 'cet EPI'}.")
        for item in items:
            epi_id = _required_int(item.get("epi_id"), "EPI")
            quantity = _required_int(item.get("quantite"), "Quantite")
            item_date = _date_text(item.get("date_remise") or date_remise, "Date remise")
            cursor = connection.execute(
                """
                INSERT INTO affectations_epi (
                    employe_id, epi_id, quantite, date_remise, statut, observations
                ) VALUES (?, ?, ?, ?, 'en_service', ?)
                """,
                (employe_id, epi_id, quantity, item_date, _optional_text(observations)),
            )
            assignment_id = int(cursor.lastrowid)
            assignment_ids.append(assignment_id)
            connection.execute(
                """
                UPDATE stock_epi
                SET quantite_disponible = quantite_disponible - ?,
                    date_mise_a_jour = CURRENT_TIMESTAMP
                WHERE epi_id = ?
                """,
                (quantity, epi_id),
            )
            connection.execute(
                """
                INSERT INTO mouvements_stock_epi (
                    epi_id, type_mouvement, quantite, motif, reference
                ) VALUES (?, 'sortie', ?, 'Dotation multiple employe', ?)
                """,
                (epi_id, quantity, f"AFF-{assignment_id}"),
            )
    record_system_audit(
        "assign_multiple_ppe",
        "ppe_assignment",
        ",".join(str(item) for item in assignment_ids),
        f"employe={employe_id};items={len(assignment_ids)};date={date_remise}",
    )
    return assignment_ids


def get_employee_ppe_profile(employee_id: Any) -> dict[str, Any]:
    employe_id = _required_int(employee_id, "Employe")
    with db_session() as connection:
        employee = connection.execute(
            """
            SELECT e.id_employe, e.matricule, COALESCE(e.nom, e.nom_complet) AS nom,
                   COALESCE(e.prenom, '') AS prenom, e.fonction_id, f.nom AS fonction,
                   e.site_id, s.nom AS site, b.numero_badge
            FROM employes e
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            JOIN sites s ON s.id_site = e.site_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.id_employe = ?
            """,
            (employe_id,),
        ).fetchone()
    if employee is None:
        raise ValueError("Employe introuvable.")
    return {**dict(employee), "requirements": prepare_required_ppe_assignment(employe_id)}


def prepare_required_ppe_assignment(employee_id: Any) -> list[dict[str, Any]]:
    employe_id = _required_int(employee_id, "Employe")
    with db_session() as connection:
        employee = connection.execute(
            "SELECT fonction_id FROM employes WHERE id_employe = ? AND statut = 'actif'",
            (employe_id,),
        ).fetchone()
        if employee is None:
            raise ValueError("Employe actif introuvable.")
        requirements = connection.execute(
            """
            SELECT req.type_epi_id, te.nom AS type_epi, req.quantite AS requis
            FROM epi_requis_fonction req
            JOIN types_epi te ON te.id_type_epi = req.type_epi_id
            WHERE req.fonction_id = ? AND req.obligatoire = 1
            ORDER BY te.nom
            """,
            (employee["fonction_id"],),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for requirement in requirements:
            assigned = connection.execute(
                """
                SELECT COALESCE(SUM(ae.quantite), 0) AS total
                FROM affectations_epi ae
                JOIN epi e ON e.id_epi = ae.epi_id
                WHERE ae.employe_id = ? AND ae.statut = 'en_service' AND e.type_epi_id = ?
                """,
                (employe_id, requirement["type_epi_id"]),
            ).fetchone()
            items = connection.execute(
                """
                SELECT e.id_epi, e.nom AS epi, COALESCE(s.quantite_disponible, 0) AS disponible
                FROM epi e
                LEFT JOIN stock_epi s ON s.epi_id = e.id_epi
                WHERE e.type_epi_id = ? AND e.actif = 1
                ORDER BY COALESCE(s.quantite_disponible, 0) DESC, e.nom
                """,
                (requirement["type_epi_id"],),
            ).fetchall()
            assigned_count = int(assigned["total"] or 0)
            required_count = int(requirement["requis"] or 0)
            missing = max(required_count - assigned_count, 0)
            available = sum(int(item["disponible"] or 0) for item in items)
            remaining = missing
            allocations: list[dict[str, Any]] = []
            for item in items:
                quantity = min(int(item["disponible"] or 0), remaining)
                if quantity > 0:
                    allocations.append(
                        {
                            "epi_id": int(item["id_epi"]),
                            "epi": item["epi"],
                            "quantite": quantity,
                        }
                    )
                    remaining -= quantity
                if remaining <= 0:
                    break
            if missing == 0:
                status = "deja_attribue"
            elif not items:
                status = "manquant"
            elif available < missing:
                status = "stock_insuffisant"
            else:
                status = "disponible"
            result.append(
                {
                    "type_epi_id": int(requirement["type_epi_id"]),
                    "type_epi": requirement["type_epi"],
                    "requis": required_count,
                    "attribue": assigned_count,
                    "manquant": missing,
                    "epi_id": allocations[0]["epi_id"] if allocations else None,
                    "epi": ", ".join(str(item["epi"]) for item in allocations) or None,
                    "allocations": allocations,
                    "stock_disponible": available,
                    "statut": status,
                }
            )
    return result


def assign_required_ppe(employee_id: Any, issue_date: Any = None, observations: Any = None) -> list[int]:
    prepared = prepare_required_ppe_assignment(employee_id)
    blockers = [row for row in prepared if row["statut"] in {"manquant", "stock_insuffisant"}]
    if blockers:
        labels = ", ".join(str(row["type_epi"]) for row in blockers)
        raise ValueError(f"Dotation bloquee. EPI obligatoires indisponibles: {labels}.")
    items = [
        allocation
        for row in prepared
        if row["statut"] == "disponible"
        for allocation in row["allocations"]
    ]
    if not items:
        raise ValueError("Tous les EPI obligatoires sont deja attribues.")
    return assign_multiple_ppe(employee_id, items, issue_date, observations or "Dotation automatique par fonction")


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
    record_system_audit("return_ppe_assignment", "ppe_assignment", str(assignment_id), f"statut={status};date={date_retour}")


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
                emp.matricule,
                f.nom AS fonction,
                s.nom AS site,
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
            JOIN fonctions f ON f.id_fonction = emp.fonction_id
            JOIN sites s ON s.id_site = emp.site_id
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
                ,COALESCE(emp.nom, emp.nom_complet) AS employe_nom
                ,COALESCE(emp.prenom, '') AS employe_prenom
            FROM mouvements_stock_epi ms
            JOIN epi e ON e.id_epi = ms.epi_id
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            LEFT JOIN affectations_epi ae ON ms.reference = 'AFF-' || ae.id_affectation
            LEFT JOIN employes emp ON emp.id_employe = ae.employe_id
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
    record_system_audit(
        "save_ppe_requirement",
        "ppe_requirement",
        f"{function_id}:{type_id}",
        f"quantite={quantity};obligatoire={mandatory}",
    )


def delete_ppe_requirement(requirement_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute(
            "DELETE FROM epi_requis_fonction WHERE id_requis = ?",
            (requirement_id,),
        )
        if not cursor.rowcount:
            raise ValueError("Exigence EPI introuvable.")
    record_system_audit("delete_ppe_requirement", "ppe_requirement", str(requirement_id), "suppression")


def list_ppe_compliance() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                emp.id_employe,
                COALESCE(emp.nom, emp.nom_complet) AS nom,
                COALESCE(emp.prenom, '') AS prenom,
                f.nom AS fonction,
                s.nom AS site,
                te.nom AS type_epi,
                req.quantite AS requis,
                COALESCE(SUM(CASE WHEN ae.statut = 'en_service' THEN ae.quantite ELSE 0 END), 0) AS affecte,
                CASE
                    WHEN COALESCE(SUM(CASE WHEN ae.statut = 'en_service' THEN ae.quantite ELSE 0 END), 0) >= req.quantite THEN 'conforme'
                    ELSE 'manquant'
                END AS statut
            FROM employes emp
            JOIN fonctions f ON f.id_fonction = emp.fonction_id
            JOIN sites s ON s.id_site = emp.site_id
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
                     s.nom, te.nom, req.quantite
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
        result = inspection_id
    record_system_audit("record_ppe_inspection", "ppe_inspection", str(result), f"epi={values.get('epi_id')};statut={status};prochaine={next_date or '-'}")
    refresh_ppe_alerts()
    return result


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


def list_ppe_employee_compliance_summary() -> list[dict[str, Any]]:
    rows = list_ppe_compliance()
    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        item = grouped.setdefault(
            int(row["id_employe"]),
            {
                "id_employe": int(row["id_employe"]),
                "nom": row.get("nom") or "",
                "prenom": row.get("prenom") or "",
                "fonction": row.get("fonction") or "",
                "site": row.get("site") or "",
                "requis": 0,
                "recus": 0,
                "manquants": [],
            },
        )
        item["requis"] += int(row.get("requis") or 0)
        item["recus"] += min(int(row.get("affecte") or 0), int(row.get("requis") or 0))
        if row.get("statut") == "manquant":
            item["manquants"].append(str(row.get("type_epi") or "-"))
    for item in grouped.values():
        item["pourcentage"] = round(item["recus"] / item["requis"] * 100) if item["requis"] else 100
        item["statut"] = "conforme" if item["pourcentage"] >= 100 else "manquant"
        item["epi_manquants"] = ", ".join(item.pop("manquants")) or "-"
    return list(grouped.values())


def refresh_ppe_alerts() -> list[dict[str, Any]]:
    desired: dict[str, dict[str, Any]] = {}
    today = date.today()
    for item in list_ppe_items():
        stock = int(item.get("quantite_disponible") or 0)
        threshold = int(item.get("seuil_minimum") or 0)
        if stock <= threshold:
            category = "stock_nul" if stock == 0 else "stock_bas"
            level = "critique" if stock == 0 else "haut"
            key = f"ppe_auto:{category}:{item['id_epi']}"
            desired[key] = {"reference_id": item["id_epi"], "niveau": level, "message": f"{item['type_epi']} - {item['nom']}: stock {stock}, seuil {threshold}."}
        expiration = item.get("date_expiration")
        if expiration:
            days = (date.fromisoformat(str(expiration)) - today).days
            if days <= 30:
                category = "expire" if days < 0 else "expiration"
                key = f"ppe_auto:{category}:{item['id_epi']}"
                desired[key] = {"reference_id": item["id_epi"], "niveau": "critique" if days < 0 else "haut", "message": f"{item['type_epi']} - {item['nom']}: expiration {expiration}."}
    for inspection in list_ppe_inspections(limit=10000):
        next_date = inspection.get("prochaine_inspection")
        if next_date and str(next_date) < today.isoformat():
            key = f"ppe_auto:inspection:{inspection['epi_id']}"
            desired[key] = {"reference_id": inspection["epi_id"], "niveau": "haut", "message": f"Inspection en retard: {inspection['type_epi']} - {inspection['epi']} ({next_date})."}
        if inspection.get("statut") in {"a_surveiller", "endommage", "hors_service"}:
            key = f"ppe_auto:etat:{inspection['epi_id']}"
            desired[key] = {"reference_id": inspection["epi_id"], "niveau": "critique" if inspection["statut"] in {"endommage", "hors_service"} else "moyen", "message": f"{inspection['type_epi']} - {inspection['epi']}: {inspection['statut']}."}
    for employee in list_ppe_employee_compliance_summary():
        if employee["statut"] != "conforme":
            key = f"ppe_auto:conformite:{employee['id_employe']}"
            desired[key] = {"reference_id": employee["id_employe"], "niveau": "haut", "message": f"{employee['nom']} {employee['prenom']}: EPI manquants - {employee['epi_manquants']}."}
    with db_session() as connection:
        existing = connection.execute("SELECT id_alerte, type_alerte FROM alertes WHERE type_alerte LIKE 'ppe_auto:%' AND statut = 'ouverte'").fetchall()
        existing_keys = {str(row["type_alerte"]): int(row["id_alerte"]) for row in existing}
        for key, alert in desired.items():
            if key not in existing_keys:
                connection.execute(
                    "INSERT INTO alertes(type_alerte, reference_id, message, niveau, statut) VALUES (?, ?, ?, ?, 'ouverte')",
                    (key, alert["reference_id"], alert["message"], alert["niveau"]),
                )
        stale = set(existing_keys) - set(desired)
        for key in stale:
            connection.execute("UPDATE alertes SET statut = 'traitee' WHERE id_alerte = ?", (existing_keys[key],))
    return [
        {"categorie": key.split(":")[1], "cle": key, **value, "statut": "ouverte"}
        for key, value in desired.items()
    ]


def get_employees_dotation_list() -> list[dict[str, Any]]:
    """Return all employees with their active PPE assignments, grouped per employee."""
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                emp.id_employe,
                COALESCE(emp.nom, emp.nom_complet) AS nom,
                COALESCE(emp.prenom, '') AS prenom,
                emp.matricule,
                b.numero_badge,
                f.nom AS fonction,
                s.nom AS site,
                ae.id_affectation,
                e.nom AS epi_nom,
                te.nom AS type_epi,
                COALESCE(e.taille, '-') AS taille,
                COALESCE(e.norme, '-') AS norme,
                COALESCE(e.marque, '') AS marque,
                ae.quantite,
                ae.date_remise,
                ae.statut,
                ae.observations,
                COALESCE(e.date_expiration, '') AS date_expiration,
                e.etat
            FROM affectations_epi ae
            JOIN employes emp ON emp.id_employe = ae.employe_id
            JOIN fonctions f ON f.id_fonction = emp.fonction_id
            JOIN sites s ON s.id_site = emp.site_id
            LEFT JOIN badges b ON b.employe_id = emp.id_employe
            JOIN epi e ON e.id_epi = ae.epi_id
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            WHERE ae.statut = 'en_service'
            ORDER BY nom, prenom, ae.date_remise DESC
            """
        ).fetchall()

    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        emp_id = int(row["id_employe"])
        if emp_id not in grouped:
            grouped[emp_id] = {
                "id_employe": emp_id,
                "nom": row["nom"] or "",
                "prenom": row["prenom"] or "",
                "matricule": row["matricule"] or "",
                "badge": row["numero_badge"] or "",
                "fonction": row["fonction"] or "",
                "site": row["site"] or "",
                "derniere_dotation": row["date_remise"] or "",
                "epi_list": [],
            }
        grouped[emp_id]["epi_list"].append({
            "id_affectation": row["id_affectation"],
            "type_epi": row["type_epi"] or "",
            "epi_nom": row["epi_nom"] or "",
            "taille": row["taille"] or "-",
            "norme": row["norme"] or "-",
            "marque": row["marque"] or "",
            "quantite": row["quantite"] or 1,
            "date_remise": row["date_remise"] or "",
            "statut": row["statut"] or "en_service",
            "date_expiration": row["date_expiration"] or "",
            "etat": row["etat"] or "",
        })
        if (row["date_remise"] or "") > grouped[emp_id]["derniere_dotation"]:
            grouped[emp_id]["derniere_dotation"] = row["date_remise"] or ""

    result = list(grouped.values())
    for item in result:
        item["nb_epi"] = len(item["epi_list"])
    return result


def close_all_employee_assignments(employee_id: Any, close_status: str = "retourne", close_date: str | None = None) -> int:
    """Close all active assignments for an employee. Returns count of closed assignments."""
    employe_id = _required_int(employee_id, "Employe")
    if close_status not in AFFECTATION_STATUSES - {"en_service"}:
        raise ValueError("Statut de clôture invalide.")
    from datetime import date as _date
    date_retour = _date_text(close_date or _date.today().isoformat(), "Date retour")
    with db_session() as connection:
        rows = connection.execute(
            "SELECT id_affectation, epi_id, quantite FROM affectations_epi WHERE employe_id=? AND statut='en_service'",
            (employe_id,),
        ).fetchall()
        count = 0
        for row in rows:
            connection.execute(
                "UPDATE affectations_epi SET statut=?, date_retour=?, updated_at=CURRENT_TIMESTAMP WHERE id_affectation=?",
                (close_status, date_retour, row["id_affectation"]),
            )
            if close_status == "retourne":
                connection.execute(
                    "UPDATE stock_epi SET quantite_disponible=quantite_disponible+?, date_mise_a_jour=CURRENT_TIMESTAMP WHERE epi_id=?",
                    (row["quantite"], row["epi_id"]),
                )
                connection.execute(
                    "INSERT INTO mouvements_stock_epi (epi_id, type_mouvement, quantite, motif, reference) VALUES (?, 'entree', ?, 'Retour en masse employe', ?)",
                    (row["epi_id"], row["quantite"], f"RET-{row['id_affectation']}"),
                )
            count += 1
    record_system_audit("close_all_employee_assignments", "ppe_assignment", str(employe_id), f"statut={close_status};count={count};date={date_retour}")
    return count


def get_employee_dotation_history(employee_id: Any) -> list[dict[str, Any]]:
    """Return all assignments (active and closed) for one employee, most recent first."""
    employe_id = _required_int(employee_id, "Employe")
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT ae.id_affectation, ae.epi_id, e.nom AS epi_nom, te.nom AS type_epi,
                   COALESCE(e.taille, '-') AS taille, COALESCE(e.norme, '-') AS norme,
                   ae.quantite, ae.date_remise, ae.date_retour, ae.statut, ae.observations
            FROM affectations_epi ae
            JOIN epi e ON e.id_epi = ae.epi_id
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            WHERE ae.employe_id = ?
            ORDER BY ae.date_remise DESC, ae.id_affectation DESC
            """,
            (employe_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_expiring_assigned_ppe(days: int = 30) -> list[dict[str, Any]]:
    """Return active PPE assignments whose EPI expires within the next `days` days."""
    from datetime import date as _date, timedelta
    today = _date.today()
    deadline = (today + timedelta(days=days)).isoformat()
    today_str = today.isoformat()
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT ae.id_affectation, ae.employe_id,
                   COALESCE(emp.nom, emp.nom_complet) AS nom,
                   COALESCE(emp.prenom, '') AS prenom,
                   emp.matricule, b.numero_badge,
                   f.nom AS fonction, s.nom AS site,
                   ae.epi_id, e.nom AS epi_nom, te.nom AS type_epi,
                   ae.quantite, ae.date_remise,
                   e.date_expiration,
                   CAST(julianday(e.date_expiration) - julianday(?) AS INTEGER) AS jours_restants
            FROM affectations_epi ae
            JOIN employes emp ON emp.id_employe = ae.employe_id
            JOIN fonctions f ON f.id_fonction = emp.fonction_id
            JOIN sites s ON s.id_site = emp.site_id
            LEFT JOIN badges b ON b.employe_id = emp.id_employe
            JOIN epi e ON e.id_epi = ae.epi_id
            JOIN types_epi te ON te.id_type_epi = e.type_epi_id
            WHERE ae.statut = 'en_service'
              AND e.date_expiration IS NOT NULL
              AND e.date_expiration != ''
              AND e.date_expiration <= ?
            ORDER BY e.date_expiration ASC, nom, prenom
            """,
            (today_str, deadline),
        ).fetchall()
    return [dict(r) for r in rows]


def get_employees_with_metadata() -> list[dict[str, Any]]:
    """Return all active employees with fonction_id, site_id, fonction, site for group selection."""
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT e.id_employe, COALESCE(e.nom, e.nom_complet) AS nom,
                   COALESCE(e.prenom, '') AS prenom, e.matricule,
                   COALESCE(b.numero_badge, 'sans badge') AS badge,
                   e.fonction_id, f.nom AS fonction,
                   e.site_id, s.nom AS site
            FROM employes e
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            JOIN fonctions f ON f.id_fonction = e.fonction_id
            JOIN sites s ON s.id_site = e.site_id
            WHERE e.statut = 'actif'
            ORDER BY f.nom, nom, prenom
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_sites_list() -> list[dict[str, Any]]:
    """Return all active sites."""
    with db_session() as connection:
        rows = connection.execute(
            "SELECT id_site AS value, nom AS label FROM sites WHERE actif=1 ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]


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
