from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.db.connection import db_session


def get_dashboard_summary() -> dict[str, Any]:
    today = date.today()
    today_text = today.isoformat()
    trend_start = today - timedelta(days=13)
    summary: dict[str, Any] = {}

    with db_session() as connection:
        summary["sites"] = _count(connection, "sites")
        summary["groupes"] = _count(connection, "groupes")
        summary["fonctions"] = _count(connection, "fonctions")
        summary["types_formations"] = _count(connection, "training_types")
        summary["types_epi"] = _count(connection, "types_epi")
        summary["employes"] = _scalar(
            connection,
            "SELECT COUNT(*) FROM employes WHERE statut = 'actif'",
        )
        summary["alertes_ouvertes"] = _scalar(
            connection,
            "SELECT COUNT(*) FROM alertes WHERE statut = 'ouverte'",
        )
        summary["employes_hors_service"] = _scalar(
            connection,
            """
            SELECT COUNT(DISTINCT employe_id)
            FROM employee_breaks
            WHERE statut IN ('planifie', 'en_cours')
              AND date_debut <= ?
              AND date_fin >= ?
            """,
            (today_text, today_text),
        )
        summary["breaks_planifies"] = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM employee_breaks
            WHERE statut IN ('planifie', 'en_cours')
              AND date_fin >= ?
            """,
            (today_text,),
        )
        summary["breaks_dus"] = _breaks_due_count(connection, today_text)
        summary["presence_today"] = _presence_for_day(connection, today_text)
        summary["presence_trend"] = _presence_trend(connection, trend_start.isoformat(), today_text)
        summary["presence_by_shift"] = _presence_by_shift(connection, today_text)
        summary["workforce_by_state"] = _workforce_by_state(connection, today_text)
        summary["workforce_by_team"] = _workforce_by_team(connection, today_text)
        summary["ppe"] = _ppe_summary(connection)
        summary["training"] = _training_summary(connection, today_text)
        summary["maintenance_actions"] = _maintenance_action_summary(connection, today_text)
        summary["attendance_rate"] = summary["presence_today"]["rate"]
        summary["workforce_rate"] = _percent(
            max(summary["employes"] - summary["employes_hors_service"], 0),
            summary["employes"],
        )
        summary["trend_average_rate"] = _average(
            [item["rate"] for item in summary["presence_trend"] if item["total"]]
        )
        summary["trend_total_hours"] = round(
            sum(float(item["hours"] or 0) for item in summary["presence_trend"]),
            2,
        )
        summary["workforce_at_work"] = _state_value(summary["workforce_by_state"], "Au travail")
        summary["workforce_on_break"] = _state_value(summary["workforce_by_state"], "Break")
        summary["performance_indicators"] = _performance_indicators(summary)

    return summary


def _count(connection: Any, table: str) -> int:
    return _scalar(connection, f"SELECT COUNT(*) FROM {table}")


def _scalar(connection: Any, query: str, params: tuple[Any, ...] = ()) -> int:
    row = connection.execute(query, params).fetchone()
    return int(row[0] or 0)


def _presence_for_day(connection: Any, target_date: str) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN statut_presence = 'present' THEN 1 ELSE 0 END) AS presents,
            SUM(CASE WHEN statut_presence = 'absent' THEN 1 ELSE 0 END) AS absents,
            SUM(heures_travaillees) AS hours
        FROM presences
        JOIN employes e ON e.id_employe = presences.employe_id
        WHERE date_presence = ?
          AND e.statut = 'actif'
          AND NOT EXISTS (
              SELECT 1
              FROM employee_breaks eb
              WHERE eb.employe_id = e.id_employe
                AND eb.statut IN ('planifie', 'en_cours')
                AND eb.date_debut <= ?
                AND eb.date_fin >= ?
          )
        """,
        (target_date, target_date, target_date),
    ).fetchone()
    total = int(row["total"] or 0)
    presents = int(row["presents"] or 0)
    absents = int(row["absents"] or 0)
    return {
        "date": target_date,
        "total": total,
        "present": presents,
        "absent": absents,
        "hours": round(float(row["hours"] or 0), 2),
        "rate": _percent(presents, total),
    }


def _presence_trend(connection: Any, start_date: str, end_date: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            p.date_presence,
            COUNT(*) AS total,
            SUM(CASE WHEN p.statut_presence = 'present' THEN 1 ELSE 0 END) AS presents,
            SUM(CASE WHEN p.statut_presence = 'absent' THEN 1 ELSE 0 END) AS absents,
            SUM(p.heures_travaillees) AS hours
        FROM presences p
        JOIN employes e ON e.id_employe = p.employe_id
        WHERE p.date_presence >= ?
          AND p.date_presence <= ?
          AND e.statut = 'actif'
          AND NOT EXISTS (
              SELECT 1
              FROM employee_breaks eb
              WHERE eb.employe_id = e.id_employe
                AND eb.statut IN ('planifie', 'en_cours')
                AND eb.date_debut <= p.date_presence
                AND eb.date_fin >= p.date_presence
          )
        GROUP BY p.date_presence
        """,
        (start_date, end_date),
    ).fetchall()
    by_date = {str(row["date_presence"]): row for row in rows}
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    days = (end - start).days + 1
    trend = []
    for offset in range(days):
        current = (start + timedelta(days=offset)).isoformat()
        row = by_date.get(current)
        total = int(row["total"] or 0) if row else 0
        presents = int(row["presents"] or 0) if row else 0
        absents = int(row["absents"] or 0) if row else 0
        hours = float(row["hours"] or 0) if row else 0
        trend.append(
            {
                "date": current,
                "total": total,
                "present": presents,
                "absent": absents,
                "hours": round(hours, 2),
                "rate": _percent(presents, total),
            }
        )
    return trend


def _breaks_due_count(connection: Any, current_date: str) -> int:
    rows = connection.execute(
        """
        SELECT
            e.id_employe,
            DATE(COALESCE(last_break.date_fin, DATE(e.created_at)), '+14 days') AS due_date
        FROM employes e
        LEFT JOIN employee_breaks last_break
          ON last_break.id_break = (
            SELECT eb.id_break
            FROM employee_breaks eb
            WHERE eb.employe_id = e.id_employe
              AND eb.type_break = 'break'
              AND eb.statut IN ('planifie', 'en_cours', 'termine')
              AND eb.date_fin < ?
            ORDER BY eb.date_fin DESC, eb.id_break DESC
            LIMIT 1
          )
        WHERE e.statut = 'actif'
          AND NOT EXISTS (
            SELECT 1
            FROM employee_breaks eb
            WHERE eb.employe_id = e.id_employe
              AND eb.statut IN ('planifie', 'en_cours')
              AND eb.date_fin >= ?
          )
        """,
        (current_date, current_date),
    ).fetchall()
    return sum(1 for row in rows if str(row["due_date"]) <= current_date)


def _presence_by_shift(connection: Any, target_date: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            s.libelle AS shift,
            COUNT(*) AS total,
            SUM(CASE WHEN p.statut_presence = 'present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN p.statut_presence = 'absent' THEN 1 ELSE 0 END) AS absent
        FROM presences p
        JOIN employes e ON e.id_employe = p.employe_id
        JOIN shifts s ON s.id_shift = p.shift_id
        WHERE p.date_presence = ?
          AND e.statut = 'actif'
        GROUP BY s.libelle
        ORDER BY s.libelle
        """,
        (target_date,),
    ).fetchall()
    return [
        {
            "label": row["shift"],
            "total": int(row["total"] or 0),
            "present": int(row["present"] or 0),
            "absent": int(row["absent"] or 0),
        }
        for row in rows
    ]


def _workforce_by_state(connection: Any, current_date: str) -> list[dict[str, Any]]:
    active = _scalar(connection, "SELECT COUNT(*) FROM employes WHERE statut = 'actif'")
    break_rows = connection.execute(
        """
        SELECT type_break, COUNT(DISTINCT employe_id) AS total
        FROM employee_breaks
        WHERE statut IN ('planifie', 'en_cours')
          AND date_debut <= ?
          AND date_fin >= ?
        GROUP BY type_break
        """,
        (current_date, current_date),
    ).fetchall()
    by_break = {str(row["type_break"]): int(row["total"] or 0) for row in break_rows}
    unavailable = sum(by_break.values())
    return [
        {"label": "Au travail", "value": max(active - unavailable, 0), "color": "#16A34A"},
        {"label": "Break", "value": by_break.get("break", 0), "color": "#F59E0B"},
        {"label": "Permission", "value": by_break.get("permission", 0), "color": "#8B5CF6"},
        {"label": "Sick", "value": by_break.get("sick", 0), "color": "#DC2626"},
    ]


def _workforce_by_team(connection: Any, current_date: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            COALESCE(g.nom, 'Sans equipe') AS equipe,
            COUNT(DISTINCT e.id_employe) AS total,
            COUNT(DISTINCT CASE
                WHEN active_break.type_break IS NULL THEN e.id_employe
            END) AS au_travail,
            COUNT(DISTINCT CASE
                WHEN active_break.type_break = 'break' THEN e.id_employe
            END) AS break_count,
            COUNT(DISTINCT CASE
                WHEN active_break.type_break = 'permission' THEN e.id_employe
            END) AS permission_count,
            COUNT(DISTINCT CASE
                WHEN active_break.type_break = 'sick' THEN e.id_employe
            END) AS sick_count,
            COUNT(DISTINCT CASE
                WHEN p.statut_presence = 'present' THEN e.id_employe
            END) AS present,
            COUNT(DISTINCT CASE
                WHEN p.statut_presence = 'absent' THEN e.id_employe
            END) AS absent
        FROM employes e
        LEFT JOIN groupes g ON g.id_groupe = e.groupe_id
        LEFT JOIN presences p
          ON p.employe_id = e.id_employe
         AND p.date_presence = ?
        LEFT JOIN employee_breaks active_break
          ON active_break.id_break = (
              SELECT eb.id_break
              FROM employee_breaks eb
              WHERE eb.employe_id = e.id_employe
                AND eb.statut IN ('planifie', 'en_cours')
                AND eb.date_debut <= ?
                AND eb.date_fin >= ?
              ORDER BY eb.date_debut DESC, eb.id_break DESC
              LIMIT 1
          )
        WHERE e.statut = 'actif'
        GROUP BY COALESCE(g.nom, 'Sans equipe')
        ORDER BY equipe
        """,
        (current_date, current_date, current_date),
    ).fetchall()
    teams = []
    for row in rows:
        total = int(row["total"] or 0)
        present = int(row["present"] or 0)
        au_travail = int(row["au_travail"] or 0)
        teams.append(
            {
                "label": row["equipe"],
                "total": total,
                "au_travail": au_travail,
                "break": int(row["break_count"] or 0),
                "permission": int(row["permission_count"] or 0),
                "sick": int(row["sick_count"] or 0),
                "present": present,
                "absent": int(row["absent"] or 0),
                "attendance_rate": _percent(present, present + int(row["absent"] or 0)),
                "availability_rate": _percent(au_travail, total),
            }
        )
    return teams


def _ppe_summary(connection: Any) -> dict[str, int]:
    row = connection.execute(
        """
        SELECT
            COUNT(e.id_epi) AS items,
            COALESCE(SUM(s.quantite_disponible), 0) AS stock_total,
            SUM(CASE WHEN COALESCE(s.quantite_disponible, 0) <= COALESCE(s.seuil_minimum, 0) THEN 1 ELSE 0 END) AS low_stock
        FROM epi e
        LEFT JOIN stock_epi s ON s.epi_id = e.id_epi
        WHERE e.actif = 1
        """
    ).fetchone()
    assigned = _scalar(
        connection,
        "SELECT COALESCE(SUM(quantite), 0) FROM affectations_epi WHERE statut = 'en_service'",
    )
    return {
        "items": int(row["items"] or 0),
        "stock_total": int(row["stock_total"] or 0),
        "low_stock": int(row["low_stock"] or 0),
        "assigned": assigned,
    }


def _training_summary(connection: Any, current_date: str) -> dict[str, int]:
    soon_date = (date.fromisoformat(current_date) + timedelta(days=30)).isoformat()
    expired = _scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM formations
        WHERE date_expiration < ?
          AND statut != 'expiree'
        """,
        (current_date,),
    )
    soon = _scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM formations
        WHERE date_expiration >= ?
          AND date_expiration <= ?
        """,
        (current_date, soon_date),
    )
    return {"expired": expired, "soon": soon}


def _maintenance_action_summary(connection: Any, current_date: str) -> dict[str, int]:
    maintenance = connection.execute(
        """
        SELECT
            SUM(CASE WHEN status IN ('planifiee', 'en_cours') THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN status IN ('planifiee', 'en_cours') AND planned_date < ? THEN 1 ELSE 0 END) AS late_count,
            SUM(CASE WHEN priority = 'critique' AND status NOT IN ('terminee', 'annulee') THEN 1 ELSE 0 END) AS critical_count
        FROM equipment_maintenance
        """,
        (current_date,),
    ).fetchone()
    actions = connection.execute(
        """
        SELECT
            SUM(CASE WHEN status IN ('ouverte', 'en_cours') THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN status IN ('ouverte', 'en_cours') AND due_date < ? THEN 1 ELSE 0 END) AS late_count,
            SUM(CASE WHEN priority = 'critique' AND status NOT IN ('terminee', 'annulee') THEN 1 ELSE 0 END) AS critical_count
        FROM action_tracker
        """,
        (current_date,),
    ).fetchone()
    return {
        "maintenance_open": int(maintenance["open_count"] or 0),
        "maintenance_late": int(maintenance["late_count"] or 0),
        "maintenance_critical": int(maintenance["critical_count"] or 0),
        "actions_open": int(actions["open_count"] or 0),
        "actions_late": int(actions["late_count"] or 0),
        "actions_critical": int(actions["critical_count"] or 0),
    }


def _average(values: list[int]) -> int:
    if not values:
        return 0
    return round(sum(values) / len(values))


def _state_value(rows: list[dict[str, Any]], label: str) -> int:
    for row in rows:
        if row.get("label") == label:
            return int(row.get("value") or 0)
    return 0


def _performance_indicators(summary: dict[str, Any]) -> list[dict[str, Any]]:
    critical_alerts = (
        summary["alertes_ouvertes"]
        + summary["breaks_dus"]
        + summary["ppe"]["low_stock"]
        + summary["training"]["expired"]
        + summary["maintenance_actions"]["maintenance_late"]
        + summary["maintenance_actions"]["actions_late"]
        + summary["maintenance_actions"]["maintenance_critical"]
        + summary["maintenance_actions"]["actions_critical"]
    )
    return [
        {
            "label": "Taux de presence",
            "value": summary["attendance_rate"],
            "suffix": "%",
            "target": 95,
            "status": _kpi_status(summary["attendance_rate"], 95, higher_is_better=True),
        },
        {
            "label": "Disponibilite workforce",
            "value": summary["workforce_rate"],
            "suffix": "%",
            "target": 90,
            "status": _kpi_status(summary["workforce_rate"], 90, higher_is_better=True),
        },
        {
            "label": "Breaks dus",
            "value": summary["breaks_dus"],
            "suffix": "",
            "target": 0,
            "status": _kpi_status(summary["breaks_dus"], 0, higher_is_better=False),
        },
        {
            "label": "Alertes critiques",
            "value": critical_alerts,
            "suffix": "",
            "target": 0,
            "status": _kpi_status(critical_alerts, 0, higher_is_better=False),
        },
    ]


def _kpi_status(value: int, target: int, higher_is_better: bool) -> str:
    if higher_is_better:
        if value >= target:
            return "bon"
        if value >= max(target - 10, 0):
            return "attention"
        return "critique"
    if value <= target:
        return "bon"
    if value <= target + 2:
        return "attention"
    return "critique"


def _percent(value: int, total: int) -> int:
    if not total:
        return 0
    return round((value / total) * 100)
