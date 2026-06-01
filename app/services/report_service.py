from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.alert_service import list_alerts
from app.services.attendance_export_service import (
    export_active_breaks_xlsx,
    export_attendance_pdf,
    export_attendance_xlsx,
    export_daily_lineup_xlsx,
    export_monthly_10h_timesheet_xlsx,
    export_ppe_inventory_xls,
    export_rows_xlsx,
    export_styled_rows_xlsx,
    export_timesheet_selected_employees_xls,
    export_timesheet_xls,
    export_toolbox_talk_xlsx,
    export_training_matrix_xls,
)
from app.services.maintenance_action_service import export_action_tracker_xlsx, export_equipment_maintenance_xlsx
from app.services.attendance_service import get_monthly_attendance_summary, today_iso
from app.services.employee_service import list_employees, list_former_employees
from app.services.timesheet_service import current_timesheet_month
from app.services.training_service import get_training_matrix, list_trainings


def list_report_definitions() -> list[dict[str, Any]]:
    return [
        {
            "key": "attendance_excel",
            "title": "Liste de presence Excel",
            "category": "Presence",
            "description": "Liste journaliere avec statuts, heures et controles.",
            "date_param": True,
            "month_param": False,
        },
        {
            "key": "attendance_pdf",
            "title": "Liste de presence PDF",
            "category": "Presence",
            "description": "Version imprimable simple de la presence du jour.",
            "date_param": True,
            "month_param": False,
        },
        {
            "key": "attendance_month",
            "title": "Synthese mensuelle presence",
            "category": "Presence",
            "description": "Jours presents, absents et heures par employe.",
            "date_param": False,
            "month_param": True,
        },
        {
            "key": "employees",
            "title": "Liste employees operationnelle",
            "category": "Employes",
            "description": "Effectif actif avec badge, fonction, shift et prochain break.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "former_employees",
            "title": "Anciens employes",
            "category": "Employes",
            "description": "Employes sortis avec motif, date et commentaire.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "active_breaks",
            "title": "Employes en break",
            "category": "Breaks",
            "description": "Employes actuellement en break, permission ou maladie.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "training_list",
            "title": "Liste des formations",
            "category": "Formations",
            "description": "Historique formation avec expiration et code couleur.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "training_matrix",
            "title": "Matrice formation",
            "category": "Formations",
            "description": "Matrice employees x formations avec legende.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "timesheet",
            "title": "TimeSheet mensuel global",
            "category": "TimeSheet",
            "description": "Un seul fichier Excel pour tous les employes du mois TimeSheet.",
            "date_param": False,
            "month_param": True,
        },
        {
            "key": "timesheet_employee",
            "title": "TimeSheet mensuel par employe",
            "category": "TimeSheet",
            "description": "Un ou plusieurs fichiers Excel individuels selon les employes selectionnes.",
            "date_param": False,
            "month_param": True,
            "employee_param": True,
        },
        {
            "key": "monthly_10h_timesheet",
            "title": "TimeSheet 1-25 / 10H",
            "category": "TimeSheet",
            "description": "TimeSheet du 1er au 25: 10H, repos, break normal, leave et section expatriés.",
            "date_param": False,
            "month_param": True,
        },
        {
            "key": "toolbox_talk",
            "title": "Toolbox Talk Meeting",
            "category": "Toolbox",
            "description": "Planning mensuel Toolbox Talk avec description OREZONE et etat de renseignement.",
            "date_param": False,
            "month_param": True,
        },
        {
            "key": "ppe_inventory",
            "title": "Inventaire EPI",
            "category": "EPI",
            "description": "Stock, dotations, conformite, inspections et alertes.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "equipment_maintenance",
            "title": "Maintenance equipements",
            "category": "Maintenance",
            "description": "Planning maintenance, priorites, responsables et echeances.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "action_tracker",
            "title": "Action Tracker",
            "category": "Actions",
            "description": "Actions ouvertes, retards, responsables, avancement et priorites.",
            "date_param": False,
            "month_param": False,
        },
        {
            "key": "alerts",
            "title": "Alertes QHSE",
            "category": "Alertes",
            "description": "Extraction des alertes ouvertes et signaux automatiques.",
            "date_param": False,
            "month_param": False,
        },
    ]


def get_report_summary() -> dict[str, Any]:
    definitions = list_report_definitions()
    categories = sorted({row["category"] for row in definitions})
    return {
        "reports": len(definitions),
        "categories": len(categories),
        "category_names": categories,
        "default_date": today_iso(),
        "default_month": current_timesheet_month(),
    }


def generate_report(report_key: str, params: dict[str, Any] | None = None) -> Path:
    values = params or {}
    key = str(report_key or "").strip()
    date_value = str(values.get("date") or today_iso()).strip()
    month_value = str(values.get("month") or current_timesheet_month()).strip()

    if key == "attendance_excel":
        return export_attendance_xlsx(date_value)
    if key == "attendance_pdf":
        return export_attendance_pdf(date_value)
    if key == "attendance_month":
        return _export_attendance_month(month_value)
    if key == "employees":
        return export_daily_lineup_xlsx(list_employees())
    if key == "former_employees":
        return _export_former_employees()
    if key == "active_breaks":
        return export_active_breaks_xlsx()
    if key == "training_list":
        return _export_training_list()
    if key == "training_matrix":
        matrix = get_training_matrix()
        return export_training_matrix_xls(matrix["training_types"], matrix["rows"])
    if key == "timesheet":
        return export_timesheet_xls(month_value)
    if key == "timesheet_employee":
        employee_ids = _employee_ids_from_params(values)
        return export_timesheet_selected_employees_xls(month_value, employee_ids)
    if key == "monthly_10h_timesheet":
        return export_monthly_10h_timesheet_xlsx(month_value)
    if key == "toolbox_talk":
        return export_toolbox_talk_xlsx(month_value)
    if key == "ppe_inventory":
        return export_ppe_inventory_xls()
    if key == "equipment_maintenance":
        return export_equipment_maintenance_xlsx()
    if key == "action_tracker":
        return export_action_tracker_xlsx()
    if key == "alerts":
        return _export_alerts()
    raise ValueError("Rapport inconnu.")


def _export_attendance_month(month: str) -> Path:
    summary = get_monthly_attendance_summary(month)
    return export_rows_xlsx(
        f"synthese_presence_{summary['month']}.xlsx",
        "Synthese mensuelle",
        ["Nom", "Prenom", "Badge", "Fonction", "Jours suivis", "Jours presents", "Jours absents", "Heures"],
        [
            [
                row.get("nom") or "",
                row.get("prenom") or "",
                row.get("numero_badge") or "",
                row.get("fonction") or "",
                row.get("jours_suivis") or 0,
                row.get("jours_presents") or 0,
                row.get("jours_absents") or 0,
                row.get("heures") or 0,
            ]
            for row in summary["rows"]
        ],
    )


def _employee_ids_from_params(values: dict[str, Any]) -> list[int]:
    raw_ids = values.get("employee_ids")
    if raw_ids is None:
        raw_ids = values.get("employee_id")
    if isinstance(raw_ids, (list, tuple, set)):
        return [int(item) for item in raw_ids if int(item or 0)]
    if isinstance(raw_ids, str) and "," in raw_ids:
        return [int(item.strip()) for item in raw_ids.split(",") if int(item.strip() or 0)]
    employee_id = int(raw_ids or 0)
    return [employee_id] if employee_id else []


def _export_former_employees() -> Path:
    rows = list_former_employees()
    return export_rows_xlsx(
        "anciens_employes.xlsx",
        "Anciens employes",
        ["Nom", "Prenom", "Badge", "Fonction", "Site", "Motif sortie", "Date sortie", "Commentaire"],
        [
            [
                row.get("nom") or row.get("nom_complet") or "",
                row.get("prenom") or "",
                row.get("numero_badge") or "",
                row.get("fonction") or "",
                row.get("site") or "",
                row.get("departure_type") or "",
                row.get("departure_date") or "",
                row.get("departure_comment") or "",
            ]
            for row in rows
        ],
    )


def _export_training_list() -> Path:
    records = list_trainings()
    rows = [
        [
            f"{record.get('nom') or '-'} {record.get('prenom') or ''}".strip(),
            record.get("numero_badge") or "",
            record.get("fonction") or "",
            record.get("formation") or "",
            record.get("date_formation") or "",
            record.get("date_expiration") or "",
            record.get("facilitateur") or "",
            record.get("structure_responsable") or "",
            _training_state_text(record.get("etat")),
        ]
        for record in records
    ]
    styles = [[None, None, None, None, None, None, None, None, _training_excel_state(record.get("etat"))] for record in records]
    return export_styled_rows_xlsx(
        "liste_formations.xlsx",
        "Formations",
        ["Employe", "Badge", "Fonction", "Formation", "Date formation", "Expiration", "Facilitateur", "Departement", "Etat"],
        rows,
        styles,
    )


def _export_alerts() -> Path:
    rows = list_alerts(statut="ouverte")
    return export_rows_xlsx(
        "alertes_qhse_ouvertes.xlsx",
        "Alertes QHSE",
        ["Date", "Source", "Type", "Niveau", "Statut", "Reference", "Message", "Action"],
        [
            [
                row.get("date_creation") or "",
                row.get("source") or "",
                row.get("type_alerte") or "",
                row.get("niveau_label") or "",
                row.get("statut") or "",
                row.get("reference_label") or "",
                row.get("message") or "",
                row.get("action_hint") or "",
            ]
            for row in rows
        ],
    )


def _training_state_text(state: str | None) -> str:
    return {
        "valide": "Faite",
        "bientot_expiree": "Bientot expiree",
        "expiree": "Non faite / expiree",
    }.get(str(state), "-")


def _training_excel_state(state: str | None) -> str:
    return {"valide": "done", "bientot_expiree": "soon", "expiree": "expired"}.get(str(state), "expired")
