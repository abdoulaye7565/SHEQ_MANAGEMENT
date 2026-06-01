from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.db.connection import db_session
from app.services.break_service import list_break_alerts
from app.services.maintenance_action_service import list_maintenance_action_alerts
from app.services.ppe_service import list_ppe_alerts


ALERT_LEVELS = ["bas", "moyen", "haut", "critique"]
ALERT_STATUSES = ["ouverte", "traitee", "ignoree"]


def get_alert_summary() -> dict[str, Any]:
    alerts = list_alerts()
    open_alerts = [row for row in alerts if row["statut"] == "ouverte"]
    return {
        "total": len(alerts),
        "open": len(open_alerts),
        "critical": sum(1 for row in open_alerts if row["niveau"] == "critique"),
        "high": sum(1 for row in open_alerts if row["niveau"] == "haut"),
        "medium": sum(1 for row in open_alerts if row["niveau"] == "moyen"),
        "low": sum(1 for row in open_alerts if row["niveau"] == "bas"),
        "by_source": _count_by(open_alerts, "source"),
    }


def list_alerts(
    source: str = "all",
    niveau: str = "all",
    statut: str = "ouverte",
    search: str = "",
) -> list[dict[str, Any]]:
    source_filter = str(source or "all")
    level_filter = str(niveau or "all")
    status_filter = str(statut or "ouverte")
    query = str(search or "").strip().lower()

    rows = [
        *_manual_alerts(),
        *_break_alerts(),
        *_ppe_alerts(),
        *_maintenance_action_alerts(),
        *_training_alerts(),
        *_attendance_alerts(),
    ]
    rows.sort(key=lambda row: (_level_rank(row["niveau"]), str(row["date_creation"])), reverse=True)

    filtered = []
    for row in rows:
        if source_filter != "all" and row["source_key"] != source_filter:
            continue
        if level_filter != "all" and row["niveau"] != level_filter:
            continue
        if status_filter != "all" and row["statut"] != status_filter:
            continue
        haystack = " ".join(
            str(row.get(key) or "")
            for key in ("type_alerte", "message", "source", "reference_label", "niveau", "statut")
        ).lower()
        if query and query not in haystack:
            continue
        filtered.append(row)
    return filtered


def create_manual_alert(
    type_alerte: str,
    message: str,
    niveau: str = "moyen",
    reference_id: int | None = None,
) -> int:
    alert_type = str(type_alerte or "").strip()
    text = str(message or "").strip()
    level = str(niveau or "moyen").strip()
    if not alert_type:
        raise ValueError("Type d'alerte obligatoire.")
    if not text:
        raise ValueError("Message d'alerte obligatoire.")
    if level not in ALERT_LEVELS:
        raise ValueError("Niveau d'alerte invalide.")

    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO alertes (type_alerte, reference_id, message, niveau, statut)
            VALUES (?, ?, ?, ?, 'ouverte')
            """,
            (alert_type, reference_id, text, level),
        )
        return int(cursor.lastrowid)


def update_manual_alert_status(alert_id: int, statut: str) -> None:
    status = str(statut or "").strip()
    if status not in ALERT_STATUSES:
        raise ValueError("Statut d'alerte invalide.")
    with db_session() as connection:
        cursor = connection.execute(
            "UPDATE alertes SET statut = ? WHERE id_alerte = ?",
            (status, int(alert_id)),
        )
        if not cursor.rowcount:
            raise ValueError("Alerte introuvable.")


def delete_manual_alert(alert_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute("DELETE FROM alertes WHERE id_alerte = ?", (int(alert_id),))
        if not cursor.rowcount:
            raise ValueError("Alerte introuvable.")


def get_alert_filter_options() -> dict[str, list[dict[str, str]]]:
    return {
        "sources": [
            {"value": "all", "label": "Toutes les sources"},
            {"value": "manual", "label": "Alertes manuelles"},
            {"value": "breaks", "label": "Breaks"},
            {"value": "ppe", "label": "EPI et stock"},
            {"value": "maintenance", "label": "Maintenance et actions"},
            {"value": "training", "label": "Formations"},
            {"value": "attendance", "label": "Presence"},
        ],
        "levels": [{"value": "all", "label": "Tous les niveaux"}]
        + [{"value": item, "label": _level_label(item)} for item in ALERT_LEVELS],
        "statuses": [
            {"value": "ouverte", "label": "Ouvertes"},
            {"value": "all", "label": "Tous les statuts"},
            {"value": "traitee", "label": "Traitees"},
            {"value": "ignoree", "label": "Ignorees"},
        ],
    }


def _manual_alerts() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id_alerte, type_alerte, reference_id, message, niveau, date_creation, statut
            FROM alertes
            ORDER BY date_creation DESC, id_alerte DESC
            """
        ).fetchall()
    return [
        _alert(
            alert_id=f"manual:{row['id_alerte']}",
            source_key="manual",
            source="Manuelle",
            type_alerte=row["type_alerte"],
            message=row["message"],
            niveau=row["niveau"],
            statut=row["statut"],
            date_creation=row["date_creation"],
            reference_id=row["reference_id"],
            reference_label=f"Alerte #{row['id_alerte']}",
            can_close=True,
        )
        for row in rows
    ]


def _break_alerts() -> list[dict[str, Any]]:
    current_date = date.today().isoformat()
    data = list_break_alerts(current_date)
    alerts: list[dict[str, Any]] = []
    for row in data["due_breaks"]:
        name = _employee_name(row)
        alerts.append(
            _alert(
                alert_id=f"break-due:{row['id_employe']}",
                source_key="breaks",
                source="Breaks",
                type_alerte="Break a planifier",
                message=f"{name} a travaille {row['jours_travailles']} jours sans break planifie.",
                niveau="haut",
                date_creation=current_date,
                reference_id=row["id_employe"],
                reference_label=name,
                action_hint="Planifier dans le module Breaks",
            )
        )
    for row in data["ending_tomorrow"]:
        name = _employee_name(row)
        alerts.append(
            _alert(
                alert_id=f"break-ending:{row['id_break']}",
                source_key="breaks",
                source="Breaks",
                type_alerte="Retour a verifier",
                message=f"{name} termine son {row['type_break']} demain ({row['date_fin']}).",
                niveau="moyen",
                date_creation=current_date,
                reference_id=row["id_break"],
                reference_label=name,
                action_hint="Verifier le retour au travail",
            )
        )
    return alerts


def _ppe_alerts() -> list[dict[str, Any]]:
    current_date = date.today().isoformat()
    alerts = []
    for row in list_ppe_alerts():
        alert_text = str(row.get("alerte") or "Alerte EPI")
        name = f"{row.get('type_epi') or '-'} - {row.get('nom') or '-'}"
        if alert_text == "Stock bas":
            level = "haut"
            detail = f"Stock {row.get('quantite_disponible', 0)} / seuil {row.get('seuil_minimum', 0)}."
        elif "Expiration" in alert_text:
            level = "haut"
            detail = f"Expiration: {row.get('date_expiration') or '-'}."
        else:
            level = "moyen"
            detail = f"Etat: {row.get('etat') or '-'}."
        alerts.append(
            _alert(
                alert_id=f"ppe:{row.get('id_epi')}:{alert_text}",
                source_key="ppe",
                source="EPI et stock",
                type_alerte=alert_text,
                message=f"{name} - {detail}",
                niveau=level,
                date_creation=current_date,
                reference_id=row.get("id_epi"),
                reference_label=name,
                action_hint="Traiter dans le module EPI",
            )
        )
    return alerts


def _maintenance_action_alerts() -> list[dict[str, Any]]:
    current_date = date.today().isoformat()
    data = list_maintenance_action_alerts()
    alerts: list[dict[str, Any]] = []
    for row in data["maintenance"]:
        equipment = _equipment_label(row)
        late = str(row.get("planned_date") or "") < current_date
        alerts.append(
            _alert(
                alert_id=f"maintenance:{row.get('id_maintenance')}",
                source_key="maintenance",
                source="Maintenance",
                type_alerte="Maintenance en retard" if late else "Maintenance critique",
                message=f"{equipment} - site {row.get('site') or '-'} - planifiee le {row.get('planned_date') or '-'}.",
                niveau="critique" if late or row.get("priority") == "critique" else "haut",
                date_creation=str(row.get("planned_date") or current_date),
                reference_id=row.get("id_maintenance"),
                reference_label=equipment,
                action_hint="Traiter dans Maintenance & Actions",
            )
        )
    for row in data["actions"]:
        title = str(row.get("title") or "Action")
        late = str(row.get("due_date") or "") < current_date
        alerts.append(
            _alert(
                alert_id=f"action:{row.get('id_action')}",
                source_key="maintenance",
                source="Action Tracker",
                type_alerte="Action en retard" if late else "Action critique",
                message=f"{title} - site {row.get('site') or '-'} - echeance {row.get('due_date') or '-'}.",
                niveau="critique" if late or row.get("priority") == "critique" else "haut",
                date_creation=str(row.get("due_date") or current_date),
                reference_id=row.get("id_action"),
                reference_label=title,
                action_hint="Traiter dans Maintenance & Actions",
            )
        )
    return alerts


def _training_alerts() -> list[dict[str, Any]]:
    today = date.today()
    soon = today + timedelta(days=30)
    alerts: list[dict[str, Any]] = []
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                f.id_formation,
                f.date_expiration,
                tt.nom AS formation,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                b.numero_badge
            FROM formations f
            JOIN employes e ON e.id_employe = f.employe_id
            JOIN training_types tt ON tt.id_training_type = f.type_training_id
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
              AND f.date_expiration <= ?
            ORDER BY f.date_expiration
            """,
            (soon.isoformat(),),
        ).fetchall()
        missing_rows = connection.execute(
            """
            SELECT
                e.id_employe,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom,
                tt.nom AS formation
            FROM employes e
            JOIN formations_requises_fonction req ON req.fonction_id = e.fonction_id
            JOIN training_types tt ON tt.id_training_type = req.type_training_id
            WHERE e.statut = 'actif'
              AND req.obligatoire = 1
              AND NOT EXISTS (
                  SELECT 1
                  FROM formations f
                  WHERE f.employe_id = e.id_employe
                    AND f.type_training_id = req.type_training_id
                    AND f.date_expiration >= ?
              )
            ORDER BY nom, prenom, formation
            """,
            (today.isoformat(),),
        ).fetchall()

    for row in rows:
        expiration = date.fromisoformat(str(row["date_expiration"]))
        expired = expiration < today
        name = _employee_name(row)
        alerts.append(
            _alert(
                alert_id=f"training:{row['id_formation']}",
                source_key="training",
                source="Formations",
                type_alerte="Formation expiree" if expired else "Formation bientot expiree",
                message=f"{name} - {row['formation']} expire le {row['date_expiration']}.",
                niveau="critique" if expired else "moyen",
                date_creation=row["date_expiration"],
                reference_id=row["id_formation"],
                reference_label=name,
                action_hint="Renouveler dans le module Formation",
            )
        )
    for row in missing_rows:
        name = _employee_name(row)
        alerts.append(
            _alert(
                alert_id=f"training-missing:{row['id_employe']}:{row['formation']}",
                source_key="training",
                source="Formations",
                type_alerte="Formation obligatoire manquante",
                message=f"{name} - {row['formation']} n'est pas valide ou non renseignee.",
                niveau="haut",
                date_creation=today.isoformat(),
                reference_id=row["id_employe"],
                reference_label=name,
                action_hint="Completer la matrice formation",
            )
        )
    return alerts


def _attendance_alerts() -> list[dict[str, Any]]:
    today = date.today().isoformat()
    alerts: list[dict[str, Any]] = []
    with db_session() as connection:
        missing_badges = connection.execute(
            """
            SELECT e.id_employe, COALESCE(e.nom, e.nom_complet) AS nom, COALESCE(e.prenom, '') AS prenom
            FROM employes e
            LEFT JOIN badges b ON b.employe_id = e.id_employe
            WHERE e.statut = 'actif'
              AND b.id_badge IS NULL
            ORDER BY nom, prenom
            """
        ).fetchall()
        badge_expiration_rows = connection.execute(
            """
            SELECT
                b.id_badge,
                b.numero_badge,
                b.date_expiration,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom
            FROM badges b
            JOIN employes e ON e.id_employe = b.employe_id
            WHERE e.statut = 'actif'
              AND b.statut = 'valide'
              AND b.date_expiration IS NOT NULL
              AND b.date_expiration <= ?
            ORDER BY b.date_expiration
            """,
            ((date.today() + timedelta(days=30)).isoformat(),),
        ).fetchall()
        presence_rows = connection.execute(
            """
            SELECT
                p.id_presence,
                p.heures_travaillees,
                p.heure_entree,
                p.heure_sortie,
                COALESCE(e.nom, e.nom_complet) AS nom,
                COALESCE(e.prenom, '') AS prenom
            FROM presences p
            JOIN employes e ON e.id_employe = p.employe_id
            WHERE p.date_presence = ?
              AND p.statut_presence = 'present'
              AND (
                  p.heure_entree IS NULL
                  OR p.heure_sortie IS NULL
                  OR p.heures_travaillees = 0
                  OR p.heures_travaillees > 12
              )
            ORDER BY nom, prenom
            """,
            (today,),
        ).fetchall()

    for row in missing_badges:
        name = _employee_name(row)
        alerts.append(
            _alert(
                alert_id=f"badge-missing:{row['id_employe']}",
                source_key="attendance",
                source="Presence",
                type_alerte="Badge manquant",
                message=f"{name} n'a pas de badge affecte.",
                niveau="moyen",
                date_creation=today,
                reference_id=row["id_employe"],
                reference_label=name,
                action_hint="Completer la fiche employe",
            )
        )
    for row in badge_expiration_rows:
        expiration = date.fromisoformat(str(row["date_expiration"]))
        expired = expiration < date.today()
        name = _employee_name(row)
        alerts.append(
            _alert(
                alert_id=f"badge-expiration:{row['id_badge']}",
                source_key="attendance",
                source="Presence",
                type_alerte="Badge expire" if expired else "Badge bientot expire",
                message=f"{name} - badge {row['numero_badge']} expire le {row['date_expiration']}.",
                niveau="haut" if expired else "moyen",
                date_creation=row["date_expiration"],
                reference_id=row["id_badge"],
                reference_label=name,
                action_hint="Mettre a jour la fiche employe",
            )
        )
    for row in presence_rows:
        name = _employee_name(row)
        hours = float(row["heures_travaillees"] or 0)
        if hours > 12:
            message = f"{name} depasse 12h aujourd'hui ({hours:g}h)."
            level = "haut"
        else:
            message = f"{name} est present avec des heures incompletes aujourd'hui."
            level = "moyen"
        alerts.append(
            _alert(
                alert_id=f"attendance:{row['id_presence']}",
                source_key="attendance",
                source="Presence",
                type_alerte="Presence a verifier",
                message=message,
                niveau=level,
                date_creation=today,
                reference_id=row["id_presence"],
                reference_label=name,
                action_hint="Verifier la presence du jour",
            )
        )
    return alerts


def _alert(
    alert_id: str,
    source_key: str,
    source: str,
    type_alerte: str,
    message: str,
    niveau: str,
    date_creation: str,
    reference_id: Any = None,
    reference_label: str = "",
    statut: str = "ouverte",
    action_hint: str = "",
    can_close: bool = False,
) -> dict[str, Any]:
    return {
        "id": alert_id,
        "source_key": source_key,
        "source": source,
        "type_alerte": type_alerte,
        "message": message,
        "niveau": niveau,
        "niveau_label": _level_label(niveau),
        "statut": statut,
        "date_creation": date_creation,
        "reference_id": reference_id,
        "reference_label": reference_label,
        "action_hint": action_hint,
        "can_close": can_close,
    }


def _employee_name(row: dict[str, Any]) -> str:
    data = dict(row)
    return f"{data.get('nom') or '-'} {data.get('prenom') or ''}".strip()


def _equipment_label(row: dict[str, Any]) -> str:
    code = str(row.get("equipment_code") or "").strip()
    name = str(row.get("equipment_name") or "-")
    return f"{code} - {name}" if code else name


def _level_label(level: str) -> str:
    return {
        "bas": "Bas",
        "moyen": "Moyen",
        "haut": "Haut",
        "critique": "Critique",
    }.get(level, level)


def _level_rank(level: str) -> int:
    return {"bas": 1, "moyen": 2, "haut": 3, "critique": 4}.get(level, 0)


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "-")
        counts[value] = counts.get(value, 0) + 1
    return counts
