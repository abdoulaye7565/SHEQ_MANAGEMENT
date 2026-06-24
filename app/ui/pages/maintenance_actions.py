from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.pagination import PAGE_SIZE, pagination_row
from app.ui.components.tables import professional_data_table

from app.services import (
    create_action,
    create_equipment_maintenance,
    create_risk_assessment,
    delete_action,
    delete_equipment_maintenance,
    delete_maintenance_inspection,
    delete_maintenance_part,
    delete_risk_assessment,
    export_action_tracker_xlsx,
    export_equipment_maintenance_xlsx,
    export_risk_assessments_xlsx,
    get_maintenance_action_options,
    get_maintenance_action_summary,
    get_maintenance_cost_analysis,
    list_action_tracker,
    list_equipment_maintenance,
    list_maintenance_audit_events,
    list_maintenance_action_alerts,
    list_maintenance_equipment_catalog,
    list_maintenance_inspections,
    list_maintenance_parts,
    list_maintenance_plans,
    list_risk_assessments,
    synchronize_maintenance_management,
    record_maintenance_inspection,
    save_maintenance_part,
    today_iso,
    update_action,
    update_equipment_maintenance,
    update_maintenance_inspection,
    update_risk_assessment,
)
from app.services.ai_service import AIConfigurationError, suggest_risk_assessment
from app.ui.components.confirm import confirm_action
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"
_DK_TRACK  = "#1A3050"

_PAGE_SIZE = PAGE_SIZE


def maintenance_actions_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {
        "tab": "dashboard",
        "suivi_tab": "actions",
        "selected_eq": None,
        "maintenance_id": None, "action_id": None, "risk_id": None,
        "part_id": None, "inspection_id": None,
        "page_actions": 0, "page_risks": 0,
    }

    status = ft.Text("", size=12, color=_DK_MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)

    dashboard_content    = ft.Column(spacing=14)
    alerts_content       = ft.Column(spacing=12)
    costs_content        = ft.Column(spacing=12)
    parts_content        = ft.Column(spacing=12)
    inspections_content  = ft.Column(spacing=12)
    action_kpi_row       = ft.ResponsiveRow(spacing=8, run_spacing=8)
    action_table         = ft.Column(spacing=8)
    risk_kpi_row         = ft.ResponsiveRow(spacing=8, run_spacing=8)
    risk_table           = ft.Column(spacing=8)
    risk_matrix_container = ft.Column(spacing=0)

    _df = dict(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F",
        focused_border_color="#2563EB",
        label_style=ft.TextStyle(color="#9DB0C5"),
        text_style=ft.TextStyle(color="#E2E8F0"),
    )
    _dd = dict(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F",
        focused_border_color="#2563EB",
        label_style=ft.TextStyle(color="#9DB0C5"),
        text_style=ft.TextStyle(color="#E2E8F0"),
    )

    part_search_field = ft.TextField(
        **_df, label="Recherche pièce / référence", prefix_icon=ft.Icons.SEARCH, width=280,
    )
    inspection_search_field = ft.TextField(
        **_df, label="Recherche inspection", prefix_icon=ft.Icons.SEARCH, width=280,
    )
    action_search = ft.TextField(
        **_df, label="Recherche action", prefix_icon=ft.Icons.SEARCH, width=260,
    )
    action_status_filter = ft.Dropdown(
        **_dd, label="Statut", value="all", width=190,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("ouverte", "Ouverte"),
            ft.dropdown.Option("en_cours", "En cours"),
            ft.dropdown.Option("terminee", "Terminee"),
            ft.dropdown.Option("en_retard", "En retard"),
            ft.dropdown.Option("annulee", "Annulee"),
        ],
    )
    risk_search = ft.TextField(
        **_df, label="Recherche risque", prefix_icon=ft.Icons.SEARCH, width=260,
    )
    risk_status_filter = ft.Dropdown(
        **_dd, label="Statut risque", value="all", width=190,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("open", "Open"),
            ft.dropdown.Option("in_progress", "In progress"),
            ft.dropdown.Option("controlled", "Controlled"),
            ft.dropdown.Option("closed", "Closed"),
        ],
    )
    eq_search_field = ft.TextField(
        **_df, label="Rechercher un équipement...", prefix_icon=ft.Icons.SEARCH, width=300,
    )

    options = get_maintenance_action_options()
    site_options = [ft.dropdown.Option("", "Site non renseigné")] + [
        ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["sites"]
    ]
    employee_options = [ft.dropdown.Option("", "Responsable non renseigné")] + [
        ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["employees"]
    ]

    # ── Maintenance form fields ─────────────────────────────────────────────────────────
    equipment_code       = ft.TextField(**_df, label="Code équipement", width=160)
    equipment_name       = ft.TextField(**_df, label="Équipement", width=240)
    equipment_category   = ft.TextField(**_df, label="Catégorie", width=170)
    maintenance_site     = ft.Dropdown(**_dd, label="Site", width=190, options=site_options)
    maintenance_responsible = ft.Dropdown(**_dd, label="Responsable", width=240, options=employee_options)
    maintenance_type     = ft.Dropdown(
        **_dd, label="Type", value="preventive", width=160,
        options=[
            ft.dropdown.Option("preventive", "Préventive"),
            ft.dropdown.Option("oil_change", "Vidange / Oil change"),
            ft.dropdown.Option("corrective", "Corrective"),
            ft.dropdown.Option("inspection", "Inspection"),
            ft.dropdown.Option("calibration", "Calibration"),
        ],
    )
    maintenance_priority = _priority_dropdown()
    maintenance_status   = ft.Dropdown(
        **_dd, label="Statut", value="planifiee", width=160,
        options=[
            ft.dropdown.Option("planifiee", "Planifiée"),
            ft.dropdown.Option("en_cours", "En cours"),
            ft.dropdown.Option("terminee", "Terminée"),
            ft.dropdown.Option("annulee", "Annulée"),
        ],
    )
    planned_date          = ft.TextField(**_df, label="Date planifiée", value=today_iso(), hint_text="AAAA-MM-JJ", width=160)
    completed_date        = ft.TextField(**_df, label="Date terminée", hint_text="AAAA-MM-JJ", width=160)
    next_due_date         = ft.TextField(**_df, label="Prochaine échéance", hint_text="AAAA-MM-JJ", width=180)
    current_odometer      = ft.TextField(**_df, label="Compteur réel actuel (km)", width=190)
    last_service_odometer = ft.TextField(**_df, label="Dernier KM maintenance", width=190)
    service_interval_km   = ft.TextField(**_df, label="KM à ajouter", width=150)
    next_due_odometer     = ft.TextField(**_df, label="Prochain KM auto", width=165, read_only=True)
    maintenance_cost      = ft.TextField(**_df, label="Coût", value="0", width=110)
    maintenance_observations = ft.TextField(**_df, label="Observations", width=260)
    save_maintenance_button   = ft.ElevatedButton("Créer", icon=ft.Icons.ADD_OUTLINED)
    cancel_maintenance_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)

    # ── Parts form fields ───────────────────────────────────────────────────────────────
    part_reference  = ft.TextField(**_df, label="Référence pièce", width=160)
    part_name       = ft.TextField(**_df, label="Pièce", width=220)
    part_category   = ft.TextField(**_df, label="Catégorie", width=170)
    part_quantity   = ft.TextField(**_df, label="Stock disponible", value="0", width=150)
    part_threshold  = ft.TextField(**_df, label="Seuil minimum", value="0", width=140)
    part_cost       = ft.TextField(**_df, label="Coût unitaire", value="0", width=140)
    save_part_button   = ft.ElevatedButton("Synchroniser le stock", icon=ft.Icons.SYNC_OUTLINED)
    cancel_part_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)

    # ── Inspection form fields ──────────────────────────────────────────────────────────
    inspection_equipment_code = ft.TextField(**_df, label="Code équipement", width=160)
    inspection_equipment_name = ft.TextField(**_df, label="Équipement", width=220)
    inspection_date     = ft.TextField(**_df, label="Date inspection", value=today_iso(), width=160)
    inspection_status   = ft.Dropdown(
        **_dd, label="Statut", value="ok", width=170,
        options=[
            ft.dropdown.Option("ok", "OK"),
            ft.dropdown.Option("a_surveiller", "À surveiller"),
            ft.dropdown.Option("critique", "Critique"),
            ft.dropdown.Option("hors_service", "Hors service"),
        ],
    )
    next_inspection_date  = ft.TextField(**_df, label="Prochaine inspection", width=180)
    inspection_inspector  = ft.TextField(**_df, label="Inspecteur", width=190)
    inspection_observations = ft.TextField(**_df, label="Observations", width=260)
    save_inspection_button   = ft.ElevatedButton("Enregistrer l'inspection", icon=ft.Icons.SAVE_OUTLINED)
    cancel_inspection_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)

    # ── Action form fields ──────────────────────────────────────────────────────────────
    action_source      = ft.TextField(**_df, label="Source", value="HSE", width=150)
    action_title       = ft.TextField(**_df, label="Action", width=260)
    action_description = ft.TextField(**_df, label="Description", width=320)
    action_site        = ft.Dropdown(**_dd, label="Site", width=190, options=site_options)
    action_owner       = ft.Dropdown(**_dd, label="Responsable", width=240, options=employee_options)
    action_priority    = _priority_dropdown()
    action_status      = ft.Dropdown(
        **_dd, label="Statut", value="ouverte", width=160,
        options=[
            ft.dropdown.Option("ouverte", "Ouverte"),
            ft.dropdown.Option("en_cours", "En cours"),
            ft.dropdown.Option("terminee", "Terminée"),
            ft.dropdown.Option("annulee", "Annulée"),
        ],
    )
    action_due_date    = ft.TextField(**_df, label="Échéance", value=today_iso(), hint_text="AAAA-MM-JJ", width=150)
    action_closed_date = ft.TextField(**_df, label="Clôture", hint_text="AAAA-MM-JJ", width=150)
    action_progress    = ft.TextField(**_df, label="Avancement %", value="0", width=140)
    save_action_button   = ft.ElevatedButton("Créer", icon=ft.Icons.ADD_TASK_OUTLINED)
    cancel_action_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)

    # ── Risk form fields ────────────────────────────────────────────────────────────────
    risk_activity          = ft.TextField(**_df, label="Activité / zone", width=220)
    risk_task              = ft.TextField(**_df, label="Tâche", width=220)
    risk_hazard            = ft.TextField(**_df, label="Danger", width=240)
    risk_event             = ft.TextField(**_df, label="Événement redouté", width=260)
    risk_consequences      = ft.TextField(**_df, label="Conséquences", width=300)
    risk_existing_controls = ft.TextField(**_df, label="Contrôles existants", width=300)
    risk_site              = ft.Dropdown(**_dd, label="Site", width=190, options=site_options)
    risk_owner             = ft.Dropdown(**_dd, label="Responsable", width=240, options=employee_options)
    risk_probability_initial  = _scale_dropdown("Prob. initiale", "3")
    risk_severity_initial     = _scale_dropdown("Gravité initiale", "3")
    risk_hierarchy = ft.Dropdown(
        **_dd, label="Contrôle ISO", value="administrative", width=190,
        options=[
            ft.dropdown.Option("elimination", "Élimination"),
            ft.dropdown.Option("substitution", "Substitution"),
            ft.dropdown.Option("engineering", "Engineering"),
            ft.dropdown.Option("administrative", "Administrative"),
            ft.dropdown.Option("ppe", "PPE / EPI"),
        ],
    )
    risk_additional_controls   = ft.TextField(**_df, label="Mesures de maîtrise", width=320)
    risk_probability_residual  = _scale_dropdown("Prob. résiduelle", "2")
    risk_severity_residual     = _scale_dropdown("Gravité résiduelle", "2")
    risk_status = ft.Dropdown(
        **_dd, label="Statut", value="open", width=160,
        options=[
            ft.dropdown.Option("open", "Open"),
            ft.dropdown.Option("in_progress", "In progress"),
            ft.dropdown.Option("controlled", "Controlled"),
            ft.dropdown.Option("closed", "Closed"),
        ],
    )
    risk_due_date    = ft.TextField(**_df, label="Échéance action", hint_text="AAAA-MM-JJ", width=160)
    risk_review_date = ft.TextField(**_df, label="Date revue", value=today_iso(), hint_text="AAAA-MM-JJ", width=160)
    save_risk_button   = ft.ElevatedButton("Créer", icon=ft.Icons.ADD_OUTLINED)
    cancel_risk_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)
    risk_ai_button     = ft.OutlinedButton("Suggestion IA", icon=ft.Icons.AUTO_AWESOME_OUTLINED)
    risk_ai_output     = ft.TextField(
        **_df, label="Suggestion IA QHSE", multiline=True,
        min_lines=4, max_lines=8, read_only=True, expand=True, value="",
    )

    # ── Helpers ─────────────────────────────────────────────────────────────────────────

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def _set_page(key: str, value: int) -> None:
        state[key] = max(0, value)

    def update_next_due_odometer(event: ft.ControlEvent | None = None) -> None:
        try:
            last_val = float(str(last_service_odometer.value or "").replace(",", "."))
            add_val  = float(str(service_interval_km.value or "").replace(",", "."))
        except ValueError:
            next_due_odometer.value = ""
        else:
            next_due_odometer.value = f"{last_val + add_val:g}"
        if event is not None:
            _update()

    # ── Reset helpers ───────────────────────────────────────────────────────────────────

    def reset_maintenance_form() -> None:
        state["maintenance_id"] = None
        equipment_code.value = equipment_name.value = equipment_category.value = ""
        maintenance_site.value = maintenance_responsible.value = ""
        maintenance_type.value = "preventive"
        maintenance_priority.value = "moyenne"
        maintenance_status.value = "planifiee"
        planned_date.value = today_iso()
        completed_date.value = next_due_date.value = ""
        current_odometer.value = last_service_odometer.value = service_interval_km.value = next_due_odometer.value = ""
        maintenance_cost.value = "0"
        maintenance_observations.value = ""
        save_maintenance_button.text = "Créer"
        save_maintenance_button.icon = ft.Icons.ADD_OUTLINED
        cancel_maintenance_button.visible = False

    def reset_action_form() -> None:
        state["action_id"] = None
        action_source.value = "HSE"
        action_title.value = action_description.value = ""
        action_site.value = action_owner.value = ""
        action_priority.value = "moyenne"
        action_status.value = "ouverte"
        action_due_date.value = today_iso()
        action_closed_date.value = ""
        action_progress.value = "0"
        save_action_button.text = "Créer"
        save_action_button.icon = ft.Icons.ADD_TASK_OUTLINED
        cancel_action_button.visible = False

    def reset_risk_form() -> None:
        state["risk_id"] = None
        risk_activity.value = risk_task.value = risk_hazard.value = risk_event.value = ""
        risk_consequences.value = risk_existing_controls.value = ""
        risk_site.value = risk_owner.value = ""
        risk_probability_initial.value = "3"
        risk_severity_initial.value = "3"
        risk_hierarchy.value = "administrative"
        risk_additional_controls.value = ""
        risk_probability_residual.value = "2"
        risk_severity_residual.value = "2"
        risk_status.value = "open"
        risk_due_date.value = ""
        risk_review_date.value = today_iso()
        risk_ai_output.value = ""
        save_risk_button.text = "Créer"
        save_risk_button.icon = ft.Icons.ADD_OUTLINED
        cancel_risk_button.visible = False

    def reset_part_form() -> None:
        state["part_id"] = None
        part_reference.value = part_name.value = part_category.value = ""
        part_quantity.value = part_threshold.value = part_cost.value = "0"
        part_reference.read_only = False
        save_part_button.text = "Synchroniser le stock"
        save_part_button.icon = ft.Icons.SYNC_OUTLINED
        cancel_part_button.visible = False

    def reset_inspection_form() -> None:
        state["inspection_id"] = None
        inspection_equipment_code.value = inspection_equipment_name.value = ""
        inspection_date.value = today_iso()
        inspection_status.value = "ok"
        next_inspection_date.value = inspection_inspector.value = inspection_observations.value = ""
        save_inspection_button.text = "Enregistrer l'inspection"
        save_inspection_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_inspection_button.visible = False

    def risk_payload() -> dict[str, Any]:
        return {
            "activity": risk_activity.value, "task": risk_task.value,
            "hazard": risk_hazard.value, "risk_event": risk_event.value,
            "consequences": risk_consequences.value, "existing_controls": risk_existing_controls.value,
            "site_id": risk_site.value, "owner_employee_id": risk_owner.value,
            "probability_initial": risk_probability_initial.value,
            "severity_initial": risk_severity_initial.value,
            "hierarchy_control": risk_hierarchy.value,
            "additional_controls": risk_additional_controls.value,
            "probability_residual": risk_probability_residual.value,
            "severity_residual": risk_severity_residual.value,
            "status": risk_status.value, "due_date": risk_due_date.value,
            "review_date": risk_review_date.value,
        }

    # ── CRUD ────────────────────────────────────────────────────────────────────────────

    def save_maintenance(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = {
                "equipment_code": equipment_code.value, "equipment_name": equipment_name.value,
                "category": equipment_category.value, "site_id": maintenance_site.value,
                "responsible_employee_id": maintenance_responsible.value,
                "maintenance_type": maintenance_type.value, "priority": maintenance_priority.value,
                "status": maintenance_status.value, "planned_date": planned_date.value,
                "completed_date": completed_date.value, "next_due_date": next_due_date.value,
                "current_odometer": current_odometer.value,
                "last_service_odometer": last_service_odometer.value,
                "service_interval_km": service_interval_km.value,
                "next_due_odometer": next_due_odometer.value,
                "cost": maintenance_cost.value, "observations": maintenance_observations.value,
            }
            if state["maintenance_id"] is None:
                create_equipment_maintenance(payload)
                notify("Intervention créée.", SUCCESS)
            else:
                update_equipment_maintenance(int(state["maintenance_id"]), payload)
                notify("Intervention modifiée.", SUCCESS)
            reset_maintenance_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_part(event: ft.ControlEvent | None = None) -> None:
        try:
            save_maintenance_part({
                "reference": part_reference.value, "name": part_name.value,
                "category": part_category.value, "quantity_available": part_quantity.value,
                "minimum_threshold": part_threshold.value, "unit_cost": part_cost.value,
            })
            notify("Pièce mise à jour." if state["part_id"] else "Pièce créée.", SUCCESS)
            reset_part_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_part(row: dict[str, Any]) -> None:
        state["part_id"] = int(row["id_part"])
        part_reference.value = str(row.get("reference") or "")
        part_name.value      = str(row.get("name") or "")
        part_category.value  = str(row.get("category") or "")
        part_quantity.value  = str(row.get("quantity_available") or 0)
        part_threshold.value = str(row.get("minimum_threshold") or 0)
        part_cost.value      = str(row.get("unit_cost") or 0)
        part_reference.read_only = True
        save_part_button.text = "Enregistrer la pièce"
        save_part_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_part_button.visible = True
        notify("Mode modification pièce. Référence verrouillée.", PRIMARY)
        _update()

    def remove_part(part_id: int) -> None:
        confirm_action(page, "Supprimer la pièce", "Cette pièce sera supprimée du stock définitivement.",
            lambda: _remove_part(part_id), confirm_label="Supprimer", danger=True)

    def _remove_part(part_id: int) -> None:
        try:
            delete_maintenance_part(part_id)
            notify("Pièce supprimée.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_inspection(event: ft.ControlEvent | None = None) -> None:
        payload = {
            "equipment_code": inspection_equipment_code.value,
            "equipment_name": inspection_equipment_name.value,
            "inspection_date": inspection_date.value, "status": inspection_status.value,
            "next_inspection_date": next_inspection_date.value,
            "inspector": inspection_inspector.value, "observations": inspection_observations.value,
        }
        try:
            if state["inspection_id"] is None:
                record_maintenance_inspection(payload)
                notify("Inspection enregistrée.", SUCCESS)
            else:
                update_maintenance_inspection(int(state["inspection_id"]), payload)
                notify("Inspection modifiée.", SUCCESS)
            reset_inspection_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_inspection(row: dict[str, Any]) -> None:
        state["inspection_id"] = int(row["id_inspection"])
        inspection_equipment_code.value = str(row.get("equipment_code") or "")
        inspection_equipment_name.value = str(row.get("equipment_name") or "")
        inspection_date.value           = str(row.get("inspection_date") or today_iso())
        inspection_status.value         = str(row.get("status") or "ok")
        next_inspection_date.value      = str(row.get("next_inspection_date") or "")
        inspection_inspector.value      = str(row.get("inspector") or "")
        inspection_observations.value   = str(row.get("observations") or "")
        save_inspection_button.text = "Enregistrer la modification"
        save_inspection_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_inspection_button.visible = True
        notify("Mode modification inspection.", PRIMARY)
        _update()

    def remove_inspection(inspection_id: int) -> None:
        confirm_action(page, "Supprimer l'inspection", "Cette inspection sera supprimée définitivement.",
            lambda: _remove_inspection(inspection_id), confirm_label="Supprimer", danger=True)

    def _remove_inspection(inspection_id: int) -> None:
        try:
            delete_maintenance_inspection(inspection_id)
            notify("Inspection supprimée.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_maintenance(row: dict[str, Any]) -> None:
        state["maintenance_id"] = int(row["id_maintenance"])
        equipment_code.value        = str(row.get("equipment_code") or "")
        equipment_name.value        = str(row.get("equipment_name") or "")
        equipment_category.value    = str(row.get("category") or "")
        maintenance_site.value      = str(row.get("site_id") or "")
        maintenance_responsible.value = str(row.get("responsible_employee_id") or "")
        maintenance_type.value      = str(row.get("maintenance_type") or "preventive")
        maintenance_priority.value  = str(row.get("priority") or "moyenne")
        maintenance_status.value    = "en_cours" if row.get("status") == "en_retard" else str(row.get("status") or "planifiee")
        planned_date.value          = str(row.get("planned_date") or today_iso())
        completed_date.value        = str(row.get("completed_date") or "")
        next_due_date.value         = str(row.get("next_due_date") or "")
        current_odometer.value      = _number_text(row.get("current_odometer"))
        last_service_odometer.value = _number_text(row.get("last_service_odometer"))
        service_interval_km.value   = _number_text(row.get("service_interval_km"))
        update_next_due_odometer()
        if not next_due_odometer.value:
            next_due_odometer.value = _number_text(row.get("next_due_odometer"))
        maintenance_cost.value         = str(row.get("cost") or 0)
        maintenance_observations.value = str(row.get("observations") or "")
        save_maintenance_button.text = "Enregistrer"
        save_maintenance_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_maintenance_button.visible = True
        notify("Mode modification intervention.", PRIMARY)
        _update()

    def remove_maintenance(maintenance_id: int) -> None:
        confirm_action(page, "Supprimer l'intervention",
            "Cette intervention de maintenance sera supprimée définitivement.",
            lambda: _remove_maintenance(maintenance_id), confirm_label="Supprimer", danger=True)

    def _remove_maintenance(maintenance_id: int) -> None:
        try:
            delete_equipment_maintenance(maintenance_id)
            notify("Intervention supprimée.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_action(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = {
                "source": action_source.value, "title": action_title.value,
                "description": action_description.value, "site_id": action_site.value,
                "owner_employee_id": action_owner.value, "priority": action_priority.value,
                "status": action_status.value, "due_date": action_due_date.value,
                "closed_date": action_closed_date.value, "progress": action_progress.value,
            }
            if state["action_id"] is None:
                create_action(payload)
                notify("Action créée.", SUCCESS)
            else:
                update_action(int(state["action_id"]), payload)
                notify("Action modifiée.", SUCCESS)
            reset_action_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_action(row: dict[str, Any]) -> None:
        state["action_id"] = int(row["id_action"])
        action_source.value      = str(row.get("source") or "HSE")
        action_title.value       = str(row.get("title") or "")
        action_description.value = str(row.get("description") or "")
        action_site.value        = str(row.get("site_id") or "")
        action_owner.value       = str(row.get("owner_employee_id") or "")
        action_priority.value    = str(row.get("priority") or "moyenne")
        action_status.value      = "en_cours" if row.get("status") == "en_retard" else str(row.get("status") or "ouverte")
        action_due_date.value    = str(row.get("due_date") or today_iso())
        action_closed_date.value = str(row.get("closed_date") or "")
        action_progress.value    = str(row.get("progress") or 0)
        save_action_button.text = "Enregistrer"
        save_action_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_action_button.visible = True
        notify("Mode modification action.", PRIMARY)
        _update()

    def remove_action(action_id: int) -> None:
        confirm_action(page, "Supprimer l'action", "Cette action du tracker sera supprimée définitivement.",
            lambda: _remove_action(action_id), confirm_label="Supprimer", danger=True)

    def _remove_action(action_id: int) -> None:
        try:
            delete_action(action_id)
            notify("Action supprimée.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_risk(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = risk_payload()
            if state["risk_id"] is None:
                create_risk_assessment(payload)
                notify("Évaluation des risques créée.", SUCCESS)
            else:
                update_risk_assessment(int(state["risk_id"]), payload)
                notify("Évaluation des risques modifiée.", SUCCESS)
            reset_risk_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def ask_risk_ai(event: ft.ControlEvent | None = None) -> None:
        try:
            risk_ai_output.value = "Génération IA en cours..."
            notify("Analyse IA du risque en cours.", PRIMARY)
            _update()
            risk_ai_output.value = suggest_risk_assessment(risk_payload())
            notify("Suggestion IA générée. À valider avant enregistrement.", SUCCESS)
        except (ValueError, AIConfigurationError) as exc:
            risk_ai_output.value = ""
            notify(str(exc), DANGER)
        _update()

    def edit_risk(row: dict[str, Any]) -> None:
        state["risk_id"] = int(row["id_risk"])
        risk_activity.value          = str(row.get("activity") or "")
        risk_task.value              = str(row.get("task") or "")
        risk_hazard.value            = str(row.get("hazard") or "")
        risk_event.value             = str(row.get("risk_event") or "")
        risk_consequences.value      = str(row.get("consequences") or "")
        risk_existing_controls.value = str(row.get("existing_controls") or "")
        risk_site.value              = str(row.get("site_id") or "")
        risk_owner.value             = str(row.get("owner_employee_id") or "")
        risk_probability_initial.value  = str(row.get("probability_initial") or 3)
        risk_severity_initial.value     = str(row.get("severity_initial") or 3)
        risk_hierarchy.value            = str(row.get("hierarchy_control") or "administrative")
        risk_additional_controls.value  = str(row.get("additional_controls") or "")
        risk_probability_residual.value = str(row.get("probability_residual") or 2)
        risk_severity_residual.value    = str(row.get("severity_residual") or 2)
        risk_status.value    = str(row.get("status") or "open")
        risk_due_date.value  = str(row.get("due_date") or "")
        risk_review_date.value = str(row.get("review_date") or today_iso())
        save_risk_button.text = "Enregistrer"
        save_risk_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_risk_button.visible = True
        notify("Mode modification évaluation des risques.", PRIMARY)
        _update()

    def remove_risk(risk_id: int) -> None:
        confirm_action(page, "Supprimer l'évaluation",
            "Cette évaluation des risques sera supprimée définitivement.",
            lambda: _remove_risk(risk_id), confirm_label="Supprimer", danger=True)

    def _remove_risk(risk_id: int) -> None:
        try:
            delete_risk_assessment(risk_id)
            notify("Évaluation des risques supprimée.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_maintenance(event: ft.ControlEvent | None = None) -> None:
        out = export_equipment_maintenance_xlsx()
        notify(f"Export maintenance créé: {out}", SUCCESS)
        _update()

    def export_actions(event: ft.ControlEvent | None = None) -> None:
        out = export_action_tracker_xlsx()
        notify(f"Export actions créé: {out}", SUCCESS)
        _update()

    def export_risks(event: ft.ControlEvent | None = None) -> None:
        out = export_risk_assessments_xlsx()
        notify(f"Export risques créé: {out}", SUCCESS)
        _update()

    # ── Render: Tab 1 – Vue d'ensemble ──────────────────────────────────────────────────

    def render_summary() -> None:
        summary = get_maintenance_action_summary()
        summary_row.controls = [
            _summary_chip("Équipements suivis",      summary["maintenance_total"],     PRIMARY, ft.Icons.PRECISION_MANUFACTURING_OUTLINED),
            _summary_chip("Interventions réalisées", summary["maintenance_completed"], SUCCESS, ft.Icons.TASK_ALT_OUTLINED),
            _summary_chip("Interventions ouvertes",  summary["maintenance_open"],      PRIMARY, ft.Icons.HANDYMAN_OUTLINED),
            _summary_chip("En retard",               summary["maintenance_late"],      DANGER if summary["maintenance_late"] else SUCCESS, ft.Icons.WARNING_AMBER_OUTLINED),
            _summary_chip("Critiques",               int(summary["maintenance_critical"]) + int(summary["actions_critical"]), WARNING, ft.Icons.PRIORITY_HIGH_OUTLINED),
            _summary_chip("Coût total (FCFA)",       f"{summary['maintenance_cost']:,.0f}", WARNING, ft.Icons.PAID_OUTLINED),
        ]

    def render_dashboard() -> None:
        summary = get_maintenance_action_summary()
        rows = list_equipment_maintenance(limit=1000)
        alerts = [
            r for r in rows
            if r.get("status") == "en_retard"
            or r.get("priority") == "critique"
            or (r.get("remaining_km") is not None and float(r["remaining_km"]) <= 500)
        ][:6]
        upcoming = sorted(
            [r for r in rows if r.get("status") not in ("terminee", "annulee")],
            key=lambda r: str(r.get("planned_date") or r.get("next_due_date") or "9999"),
        )[:6]
        type_counts: dict[str, int] = {}
        responsible_counts: dict[str, int] = {}
        for row in rows:
            type_counts[_type_label(row.get("maintenance_type"))] = type_counts.get(_type_label(row.get("maintenance_type")), 0) + 1
            resp = _person_name(row, "responsable_nom", "responsable_prenom") or "Non affecté"
            responsible_counts[resp] = responsible_counts.get(resp, 0) + 1
        dashboard_content.controls = [
            ft.ResponsiveRow([
                ft.Container(_analysis_panel("Répartition par type",
                    [_metric_bar(l, v, len(rows), c) for (l, v), c in zip(type_counts.items(), [PRIMARY, SUCCESS, WARNING, "#7C3AED", MUTED], strict=False)]),
                    col={"xs": 12, "lg": 6}),
                ft.Container(_analysis_panel("Par responsable",
                    [_metric_bar(l, v, len(rows), PRIMARY) for l, v in sorted(responsible_counts.items(), key=lambda i: i[1], reverse=True)[:5]]),
                    col={"xs": 12, "lg": 6}),
            ], spacing=12, run_spacing=12),
            ft.ResponsiveRow([
                ft.Container(_maintenance_preview_panel("Prochaines interventions", upcoming, False), col={"xs": 12, "lg": 7}),
                ft.Container(_maintenance_preview_panel("Alertes automatiques", alerts, True), col={"xs": 12, "lg": 5}),
            ], spacing=12, run_spacing=12),
            _analysis_panel("Analyse rapide", [
                _insight_line(ft.Icons.CHECK_CIRCLE_OUTLINE, f"Taux de completion : {summary['maintenance_completion_rate']}%", SUCCESS),
                _insight_line(ft.Icons.SPEED_OUTLINED, f"{summary['maintenance_odometer_due']} maintenance(s) arrivée(s) au compteur.", DANGER if summary["maintenance_odometer_due"] else SUCCESS),
                _insight_line(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, f"{summary['maintenance_due_soon']} maintenance(s) à moins de 500 km.", WARNING if summary["maintenance_due_soon"] else SUCCESS),
                _insight_line(ft.Icons.PAID_OUTLINED, f"Coût cumulé : {summary['maintenance_cost']:,.0f} FCFA.", PRIMARY),
            ]),
            _audit_trail_panel(),
        ]

    def _audit_trail_panel() -> ft.Control:
        audit_rows = list_maintenance_audit_events(limit=15)
        _action_icons: dict[str, str] = {
            "save_maintenance_part": ft.Icons.INVENTORY_2_OUTLINED,
            "delete_maintenance_part": ft.Icons.DELETE_OUTLINE,
            "record_maintenance_inspection": ft.Icons.FACT_CHECK_OUTLINED,
            "update_maintenance_inspection": ft.Icons.EDIT_OUTLINED,
            "delete_maintenance_inspection": ft.Icons.DELETE_OUTLINE,
            "create_equipment_maintenance": ft.Icons.ADD_OUTLINED,
            "update_equipment_maintenance": ft.Icons.EDIT_OUTLINED,
            "delete_equipment_maintenance": ft.Icons.DELETE_OUTLINE,
            "create_action": ft.Icons.ADD_TASK_OUTLINED,
            "update_action": ft.Icons.EDIT_OUTLINED,
            "delete_action": ft.Icons.DELETE_OUTLINE,
            "create_risk_assessment": ft.Icons.HEALTH_AND_SAFETY_OUTLINED,
            "update_risk_assessment": ft.Icons.EDIT_OUTLINED,
            "delete_risk_assessment": ft.Icons.DELETE_OUTLINE,
        }
        _type_labels: dict[str, str] = {
            "maintenance_part": "Stock", "maintenance_inspection": "Inspection",
            "equipment_maintenance": "Maintenance", "action_tracker": "Action",
            "risk_assessment": "Risque",
        }
        if not audit_rows:
            return _analysis_panel("Journal des opérations", [ft.Text("Aucune opération enregistrée.", color=_DK_MUTED, size=12)])
        rows_ctrl: list[ft.Control] = []
        for audit in audit_rows:
            action_key = str(audit.get("action") or "")
            cible_type = str(audit.get("cible_type") or "")
            icon   = _action_icons.get(action_key, ft.Icons.HISTORY_OUTLINED)
            color  = DANGER if "delete" in action_key else (SUCCESS if "create" in action_key else PRIMARY)
            rows_ctrl.append(ft.Container(
                border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                padding=ft.padding.symmetric(vertical=6),
                content=ft.Row([
                    ft.Container(bgcolor=_DK_HEAD, border_radius=6, padding=5, content=ft.Icon(icon, color=color, size=14)),
                    ft.Column([
                        ft.Text(f"[{_type_labels.get(cible_type, cible_type)}] {action_key.replace('_', ' ')}", size=11, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                        ft.Text(f"ID: {audit.get('cible_id') or '-'} | {str(audit.get('nouvelle_valeur') or '')[:80]}", size=10, color=_DK_MUTED),
                    ], spacing=1, expand=True),
                    ft.Text(str(audit.get("changed_at") or "-")[:16], size=10, color=_DK_MUTED),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        return _analysis_panel("Journal des opérations (15 dernières)", rows_ctrl)

    def render_alerts() -> None:
        rows = list_maintenance_action_alerts()
        maintenance_alerts = rows.get("maintenance") or []
        action_alerts      = rows.get("actions") or []
        part_alerts        = rows.get("parts") or []
        inspection_alerts  = rows.get("inspections") or []
        alerts_content.controls = [
            _section_toolbar("Alertes maintenance",
                f"{len(maintenance_alerts)} maintenance(s), {len(action_alerts)} action(s), "
                f"{len(part_alerts)} stock(s) et {len(inspection_alerts)} inspection(s) nécessitent une attention.",
                ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            *[_synchronous_alert_card(_equipment_label(r),
                f"{_status_label(r.get('status'))} | {_equipment_next_label(r)}",
                DANGER if r.get("status") == "en_retard" or r.get("priority") == "critique" else WARNING)
              for r in maintenance_alerts],
            *[_synchronous_alert_card(str(r.get("title") or "Action corrective"),
                f"{r.get('site') or '-'} | Échéance {r.get('due_date') or '-'}",
                DANGER if r.get("priority") == "critique" else WARNING)
              for r in action_alerts],
            *[_synchronous_alert_card(f"Stock bas | {r.get('reference')} - {r.get('name')}",
                f"Disponible {r.get('quantity_available') or 0} | Seuil {r.get('minimum_threshold') or 0}", DANGER)
              for r in part_alerts],
            *[_synchronous_alert_card(f"Inspection | {_equipment_label(r)}",
                f"{_inspection_status_label(r.get('computed_status'))} | Prochaine {r.get('next_inspection_date') or '-'}",
                DANGER if r.get("computed_status") in {"critique", "hors_service"} else WARNING)
              for r in inspection_alerts],
        ] or [ft.Text("Aucune alerte maintenance.", color=SUCCESS)]

    def render_costs() -> None:
        analysis = get_maintenance_cost_analysis()
        costs_content.controls = [
            _section_toolbar("Coûts & analyses", "Analyse des coûts par catégorie, type et équipement.", ft.Icons.QUERY_STATS_OUTLINED),
            ft.ResponsiveRow([
                _summary_chip("Coût total FCFA", f"{analysis['total']:,.0f}", WARNING, ft.Icons.PAID_OUTLINED),
                _summary_chip("Coût moyen", f"{analysis['average']:,.0f}", PRIMARY, ft.Icons.ANALYTICS_OUTLINED),
                _summary_chip("Interventions", analysis["interventions"], SUCCESS, ft.Icons.HANDYMAN_OUTLINED),
            ], spacing=12, run_spacing=12),
            ft.ResponsiveRow([
                ft.Container(_analysis_panel("Coûts par catégorie",
                    [_metric_value_line(l, v, analysis["total"]) for l, v in analysis["by_category"].items()]),
                    col={"xs": 12, "lg": 6}),
                ft.Container(_analysis_panel("Équipements les plus coûteux",
                    [_metric_value_line(l, v, analysis["total"]) for l, v in list(analysis["by_equipment"].items())[:8]]),
                    col={"xs": 12, "lg": 6}),
            ], spacing=12, run_spacing=12),
        ]

    # ── Render: Tab 3 sub-sections ───────────────────────────────────────────────────────

    def render_parts() -> None:
        rows = list_maintenance_parts()
        search = str(part_search_field.value or "").strip().lower()
        if search:
            rows = [r for r in rows if any(search in str(r.get(k) or "").lower() for k in ("reference", "name", "category"))]
        low_stock   = sum(1 for r in rows if r.get("low_stock"))
        stock_value = sum(float(r.get("stock_value") or 0) for r in rows)
        parts_content.controls = [
            _section_toolbar("Pièces & stocks",
                "Stock synchronisé avec les seuils critiques et le centre d'alertes.", ft.Icons.INVENTORY_2_OUTLINED),
            ft.ResponsiveRow([
                _summary_chip("Références", len(rows), PRIMARY, ft.Icons.CATEGORY_OUTLINED),
                _summary_chip("Stock bas", low_stock, DANGER if low_stock else SUCCESS, ft.Icons.WARNING_AMBER_OUTLINED),
                _summary_chip("Valeur du stock", f"{stock_value:,.0f} FCFA", WARNING, ft.Icons.PAID_OUTLINED),
            ], spacing=12, run_spacing=12),
            _form_panel("Gestion du stock pièces", ft.Icons.INVENTORY_2_OUTLINED, WARNING, [
                _field_group("Identification", [part_reference, part_name, part_category],
                    hint="Une référence existante est mise à jour automatiquement (upsert)."),
                _field_group("Stock & coûts", [part_quantity, part_threshold, part_cost, save_part_button, cancel_part_button]),
            ]),
            ft.Row([professional_data_table(
                columns=[
                    ft.DataColumn(ft.Text("Référence / Pièce", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Catégorie", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Disponible", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Seuil min.", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Coût unit.", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Valeur stock", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Statut", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Mis à jour", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Actions", color=_DK_TEXT)),
                ],
                rows=[ft.DataRow(
                    color="#4B1111" if r.get("low_stock") else None,
                    cells=[
                        ft.DataCell(ft.Text(f"{r.get('reference')} | {r.get('name')}", weight=ft.FontWeight.BOLD, color=_DK_TEXT)),
                        ft.DataCell(ft.Text(str(r.get("category") or "-"), color=_DK_TEXT)),
                        ft.DataCell(ft.Text(str(r.get("quantity_available") or 0), color=_DK_TEXT)),
                        ft.DataCell(ft.Text(str(r.get("minimum_threshold") or 0), color=_DK_TEXT)),
                        ft.DataCell(ft.Text(f"{float(r.get('unit_cost') or 0):,.0f}", color=_DK_TEXT)),
                        ft.DataCell(ft.Text(f"{float(r.get('stock_value') or 0):,.0f}", color=_DK_TEXT)),
                        ft.DataCell(_badge("Stock bas", DANGER) if r.get("low_stock") else _badge("Disponible", SUCCESS)),
                        ft.DataCell(ft.Text(str(r.get("updated_at") or "-"), color=_DK_TEXT)),
                        ft.DataCell(ft.Row([
                            ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Modifier", icon_color=PRIMARY, on_click=lambda e, item=r: edit_part(item)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", icon_color=DANGER, on_click=lambda e, pid=r["id_part"]: remove_part(int(pid))),
                        ], spacing=0)),
                    ]) for r in rows],
                border=ft.border.all(1, _DK_BORDER),
                border_radius=8, heading_row_color=_DK_HEAD,
            )], scroll=ft.ScrollMode.AUTO),
        ]

    def render_inspections() -> None:
        rows = list_maintenance_inspections()
        search = str(inspection_search_field.value or "").strip().lower()
        if search:
            rows = [r for r in rows if any(search in str(r.get(k) or "").lower() for k in ("equipment_code", "equipment_name", "inspector", "observations"))]
        overdue  = sum(1 for r in rows if r.get("computed_status") == "en_retard")
        critical = sum(1 for r in rows if r.get("computed_status") in {"critique", "hors_service"})
        inspections_content.controls = [
            _section_toolbar("Inspections équipements",
                "Les inspections critiques et échues remontent automatiquement dans les alertes.", ft.Icons.FACT_CHECK_OUTLINED),
            ft.ResponsiveRow([
                _summary_chip("Inspections", len(rows), PRIMARY, ft.Icons.FACT_CHECK_OUTLINED),
                _summary_chip("En retard", overdue, WARNING if overdue else SUCCESS, ft.Icons.EVENT_BUSY_OUTLINED),
                _summary_chip("Critiques", critical, DANGER if critical else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            ], spacing=12, run_spacing=12),
            _form_panel("Enregistrer une inspection", ft.Icons.FACT_CHECK_OUTLINED, PRIMARY, [
                _field_group("Équipement inspecté", [inspection_equipment_code, inspection_equipment_name]),
                _field_group("Résultats", [inspection_date, inspection_status, next_inspection_date]),
                _field_group("Détails", [inspection_inspector, inspection_observations, save_inspection_button, cancel_inspection_button]),
            ]),
            ft.Row([professional_data_table(
                columns=[
                    ft.DataColumn(ft.Text("Équipement", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Date", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Statut", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Prochaine", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Inspecteur", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Observations", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Actions", color=_DK_TEXT)),
                ],
                rows=[ft.DataRow(cells=[
                    ft.DataCell(ft.Text(_equipment_label(r), weight=ft.FontWeight.BOLD, color=_DK_TEXT)),
                    ft.DataCell(ft.Text(str(r.get("inspection_date") or "-"), color=_DK_TEXT)),
                    ft.DataCell(_badge(_inspection_status_label(r.get("computed_status")), _inspection_status_color(r.get("computed_status")))),
                    ft.DataCell(ft.Text(str(r.get("next_inspection_date") or "-"), color=_DK_TEXT)),
                    ft.DataCell(ft.Text(str(r.get("inspector") or "-"), color=_DK_TEXT)),
                    ft.DataCell(ft.Text(str(r.get("observations") or "-")[:60], color=_DK_TEXT)),
                    ft.DataCell(ft.Row([
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Modifier", icon_color=PRIMARY, on_click=lambda e, item=r: edit_inspection(item)),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", icon_color=DANGER, on_click=lambda e, iid=r["id_inspection"]: remove_inspection(int(iid))),
                    ], spacing=0)),
                ]) for r in rows],
                border=ft.border.all(1, _DK_BORDER), border_radius=8, heading_row_color=_DK_HEAD,
            )], scroll=ft.ScrollMode.AUTO),
        ]

    def render_actions() -> None:
        all_rows = list_action_tracker(str(action_search.value or ""), str(action_status_filter.value or "all"))
        _open    = sum(1 for r in all_rows if r.get("status") in {"ouverte", "en_cours"})
        _overdue = sum(1 for r in all_rows if r.get("status") == "en_retard")
        _crit    = sum(1 for r in all_rows if r.get("priority") == "critique")
        _done    = sum(1 for r in all_rows if r.get("status") == "terminee")
        action_kpi_row.controls = [
            _summary_chip("Total", len(all_rows), PRIMARY, ft.Icons.LIST_ALT_OUTLINED),
            _summary_chip("En cours / ouvertes", _open, WARNING if _open else SUCCESS, ft.Icons.PENDING_ACTIONS_OUTLINED),
            _summary_chip("En retard", _overdue, DANGER if _overdue else SUCCESS, ft.Icons.EVENT_BUSY_OUTLINED),
            _summary_chip("Critiques", _crit, DANGER if _crit else SUCCESS, ft.Icons.PRIORITY_HIGH_OUTLINED),
            _summary_chip("Terminées", _done, SUCCESS, ft.Icons.TASK_ALT_OUTLINED),
        ]
        page_idx    = state.get("page_actions", 0)
        total_pages = max(1, (len(all_rows) + _PAGE_SIZE - 1) // _PAGE_SIZE)
        page_idx    = min(page_idx, total_pages - 1)
        state["page_actions"] = page_idx
        rows = all_rows[page_idx * _PAGE_SIZE : (page_idx + 1) * _PAGE_SIZE]
        action_table.controls = [
            ft.Row([
                ft.Text(f"Action tracker ({len(all_rows)})", size=15, weight=ft.FontWeight.BOLD, color=_DK_TEXT, expand=True),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([professional_data_table(
                columns=[
                    ft.DataColumn(ft.Text("Source", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Action", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Site", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Responsable", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Priorité", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Statut", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Échéance", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("%", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Actions", color=_DK_TEXT)),
                ],
                rows=[ft.DataRow(
                    color=_dk_row_color(r.get("status"), r.get("priority")),
                    cells=[
                        ft.DataCell(ft.Text(str(r.get("source") or "-"), color=_DK_TEXT)),
                        ft.DataCell(ft.Text(str(r.get("title") or "-"), weight=ft.FontWeight.BOLD, color=_DK_TEXT)),
                        ft.DataCell(ft.Text(str(r.get("site") or "-"), color=_DK_TEXT)),
                        ft.DataCell(ft.Text(_person_name(r, "owner_nom", "owner_prenom") or "-", color=_DK_TEXT)),
                        ft.DataCell(_badge(str(r.get("priority") or "-"), _priority_color(r.get("priority")))),
                        ft.DataCell(_badge(_status_label(r.get("status")), _status_color(r.get("status")))),
                        ft.DataCell(ft.Text(str(r.get("due_date") or "-"), color=_DK_TEXT)),
                        ft.DataCell(ft.Text(f"{r.get('progress') or 0}%", color=_DK_TEXT)),
                        ft.DataCell(ft.Row([
                            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, on_click=lambda e, item=r: edit_action(item)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, on_click=lambda e, aid=r["id_action"]: remove_action(int(aid))),
                        ], spacing=0)),
                    ]) for r in rows],
                border=ft.border.all(1, _DK_BORDER), border_radius=8, heading_row_color=_DK_HEAD,
            )], scroll=ft.ScrollMode.AUTO),
            pagination_row(
                current_page=page_idx,
                max_page=total_pages - 1,
                total=len(all_rows),
                shown_start=page_idx * _PAGE_SIZE + 1 if rows else 0,
                shown_end=page_idx * _PAGE_SIZE + len(rows),
                item_label="action(s)",
                on_prev=lambda: (_set_page("page_actions", state.get("page_actions", 0) - 1), render_actions(), _update()),
                on_next=lambda: (_set_page("page_actions", state.get("page_actions", 0) + 1), render_actions(), _update()),
                on_page=lambda p: (_set_page("page_actions", p), render_actions(), _update()),
            ),
        ]

    def render_risks() -> None:
        all_rows  = list_risk_assessments(str(risk_search.value or ""), str(risk_status_filter.value or "all"))
        _crit     = sum(1 for r in all_rows if r.get("level_residual") == "critical")
        _high     = sum(1 for r in all_rows if r.get("level_residual") == "high")
        _ctrl     = sum(1 for r in all_rows if r.get("status") in {"controlled", "closed"})
        _open     = sum(1 for r in all_rows if r.get("status") == "open")
        risk_kpi_row.controls = [
            _summary_chip("Total risques", len(all_rows), PRIMARY, ft.Icons.HEALTH_AND_SAFETY_OUTLINED),
            _summary_chip("Critiques", _crit, DANGER if _crit else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _summary_chip("Élevés", _high, WARNING if _high else SUCCESS, ft.Icons.WARNING_AMBER_OUTLINED),
            _summary_chip("Contrôlés", _ctrl, SUCCESS, ft.Icons.VERIFIED_OUTLINED),
            _summary_chip("Ouverts", _open, WARNING if _open else SUCCESS, ft.Icons.RADIO_BUTTON_UNCHECKED),
        ]
        risk_matrix_container.controls = [_build_risk_matrix(list_risk_assessments())]
        page_idx    = state.get("page_risks", 0)
        total_pages = max(1, (len(all_rows) + _PAGE_SIZE - 1) // _PAGE_SIZE)
        page_idx    = min(page_idx, total_pages - 1)
        state["page_risks"] = page_idx
        rows = all_rows[page_idx * _PAGE_SIZE : (page_idx + 1) * _PAGE_SIZE]
        risk_table.controls = [
            ft.Row([
                ft.Text(f"Évaluation des risques ({len(all_rows)})", size=15, weight=ft.FontWeight.BOLD, color=_DK_TEXT, expand=True),
                ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_color=PRIMARY if page_idx > 0 else MUTED,
                    on_click=lambda e: (_set_page("page_risks", state.get("page_risks", 0) - 1), render_risks(), _update())),
                ft.Text(f"{page_idx + 1}/{total_pages}", size=12, color=_DK_MUTED),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=PRIMARY if page_idx < total_pages - 1 else MUTED,
                    on_click=lambda e: (_set_page("page_risks", state.get("page_risks", 0) + 1), render_risks(), _update())),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([professional_data_table(
                columns=[
                    ft.DataColumn(ft.Text("Activité / Danger", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Site", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Risque initial", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Contrôle ISO", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Risque résiduel", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Responsable", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Statut", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Revue", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Action auto", color=_DK_TEXT)),
                    ft.DataColumn(ft.Text("Actions", color=_DK_TEXT)),
                ],
                rows=[ft.DataRow(
                    color=_dk_risk_row_color(r.get("level_residual"), r.get("status")),
                    cells=[
                        ft.DataCell(ft.Text(_risk_activity_label(r), weight=ft.FontWeight.BOLD, width=260, color=_DK_TEXT)),
                        ft.DataCell(ft.Text(str(r.get("site") or "-"), color=_DK_TEXT)),
                        ft.DataCell(_badge(_risk_score_label(r, "initial"), _risk_level_color(r.get("level_initial")))),
                        ft.DataCell(ft.Text(_control_label(r.get("hierarchy_control")), color=_DK_TEXT)),
                        ft.DataCell(_badge(_risk_score_label(r, "residual"), _risk_level_color(r.get("level_residual")))),
                        ft.DataCell(ft.Text(_person_name(r, "owner_nom", "owner_prenom") or "-", color=_DK_TEXT)),
                        ft.DataCell(_badge(_risk_status_label(r.get("status")), _risk_status_color(r.get("status")))),
                        ft.DataCell(ft.Text(str(r.get("review_date") or "-"), color=_DK_TEXT)),
                        ft.DataCell(
                            _badge(f"Action #{r['auto_action_id']}", WARNING) if r.get("auto_action_id")
                            else ft.Text("-", color=_DK_MUTED, size=12)
                        ),
                        ft.DataCell(ft.Row([
                            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, on_click=lambda e, item=r: edit_risk(item)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, on_click=lambda e, rid=r["id_risk"]: remove_risk(int(rid))),
                        ], spacing=0)),
                    ]) for r in rows],
                border=ft.border.all(1, _DK_BORDER), border_radius=8, heading_row_color=_DK_HEAD,
            )], scroll=ft.ScrollMode.AUTO),
        ]

    # ── Tab 2: Equipment browser / fiche ─────────────────────────────────────────────────

    tab2_col = ft.Column(spacing=14, visible=False)

    def _eq_color(eq: dict[str, Any]) -> str:
        return DANGER if eq.get("status") == "maintenance_due" else SUCCESS

    def _eq_card(eq: dict[str, Any]) -> ft.Control:
        color = _eq_color(eq)

        def on_select(e: ft.ControlEvent, eq: dict[str, Any] = eq) -> None:
            state["selected_eq"] = eq
            equipment_code.value     = str(eq.get("equipment_code") or "")
            equipment_name.value     = str(eq.get("equipment_name") or "")
            equipment_category.value = str(eq.get("category") or "")
            render_tab2()
            _update()

        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
            bgcolor=_DK_CARD,
            border=ft.border.all(2, color),
            border_radius=10,
            padding=14,
            on_click=on_select,
            ink=True,
            content=ft.Column([
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                    ft.Text(_equipment_label(eq), size=12, weight=ft.FontWeight.BOLD, color=_DK_TEXT, expand=True,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ], spacing=6),
                ft.Text(str(eq.get("category") or "-"), size=10, color=_DK_MUTED),
                ft.Text(f"Prochaine: {_equipment_next_label(eq)}", size=10,
                        color=DANGER if color == DANGER else _DK_MUTED),
                ft.Text(f"Compteur: {_number_unit(eq.get('current_odometer'), 'km')}", size=10, color=_DK_MUTED),
                ft.Row([
                    _badge(f"{eq.get('interventions', 0)} interv.", PRIMARY),
                    _badge("Due!", DANGER) if color == DANGER else _badge("OK", SUCCESS),
                ], spacing=4, wrap=True),
            ], spacing=5),
        )

    def render_equipment_browser() -> None:
        search   = str(eq_search_field.value or "").strip()
        eq_list  = list_maintenance_equipment_catalog(search)
        due_count = sum(1 for e in eq_list if e.get("status") == "maintenance_due")
        tab2_col.controls = [
            ft.Container(
                bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=8, padding=12,
                content=ft.Row([
                    ft.Container(bgcolor=_DK_HEAD, border_radius=8, padding=8,
                        content=ft.Icon(ft.Icons.PRECISION_MANUFACTURING_OUTLINED, color=PRIMARY, size=20)),
                    ft.Column([
                        ft.Text("Parc équipements", size=14, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                        ft.Text(f"{len(eq_list)} équipement(s)  •  {due_count} maintenance(s) due(s)", size=11, color=_DK_MUTED),
                    ], spacing=1, expand=True),
                    eq_search_field,
                    ft.ElevatedButton("Nouvelle intervention", icon=ft.Icons.ADD_OUTLINED,
                        on_click=lambda e: _show_new_intervention_form(),
                        style=ft.ButtonStyle(bgcolor=PRIMARY, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=7))),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            ft.ResponsiveRow([_eq_card(eq) for eq in eq_list], spacing=10, run_spacing=10)
            if eq_list else ft.Container(
                bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=10, padding=40,
                content=ft.Column([
                    ft.Icon(ft.Icons.PRECISION_MANUFACTURING_OUTLINED, size=48, color=_DK_MUTED),
                    ft.Text("Aucun équipement enregistré.", color=_DK_MUTED, size=14),
                    ft.Text("Cliquez 'Nouvelle intervention' pour commencer.", color=_DK_MUTED, size=11),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.center,
            ),
        ]

    def render_equipment_fiche(eq: dict[str, Any]) -> None:
        eq_code  = str(eq.get("equipment_code") or "")
        eq_name  = str(eq.get("equipment_name") or "")
        all_rows = list_equipment_maintenance(eq_code if eq_code else eq_name, "all")
        if eq_code:
            fiche_rows = [r for r in all_rows if str(r.get("equipment_code") or "") == eq_code]
        else:
            fiche_rows = [r for r in all_rows if str(r.get("equipment_name") or "") == eq_name]
        recent   = sorted(fiche_rows, key=lambda r: str(r.get("planned_date") or ""), reverse=True)[:5]
        eq_color = _eq_color(eq)

        back_btn = ft.TextButton("← Retour au catalogue",
            style=ft.ButtonStyle(color=_DK_MUTED), on_click=lambda e: _back_to_browser())

        eq_header = ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.only(
                left=ft.BorderSide(4, eq_color),
                top=ft.BorderSide(1, _DK_BORDER), right=ft.BorderSide(1, _DK_BORDER), bottom=ft.BorderSide(1, _DK_BORDER),
            ),
            border_radius=10, padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Container(bgcolor=_DK_CARD2, border=ft.border.all(1, eq_color), border_radius=10, padding=10,
                        content=ft.Icon(ft.Icons.PRECISION_MANUFACTURING_OUTLINED, color=eq_color, size=24)),
                    ft.Column([
                        ft.Text(_equipment_label(eq), size=16, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                        ft.Row([
                            _badge("Maintenance due" if eq_color == DANGER else "Actif", eq_color),
                            ft.Text(f"Catégorie: {eq.get('category') or '-'}", size=11, color=_DK_MUTED),
                        ], spacing=8),
                    ], spacing=4, expand=True),
                    ft.Column([
                        ft.Text(f"Site: {eq.get('site') or '-'}", size=11, color=_DK_MUTED),
                        ft.Text(f"Responsable: {eq.get('responsible') or '-'}", size=11, color=_DK_MUTED),
                    ], spacing=2),
                ], spacing=12),
                ft.Row([
                    _info_chip(ft.Icons.SPEED_OUTLINED, "Compteur", _number_unit(eq.get("current_odometer"), "km")),
                    _info_chip(ft.Icons.EVENT_OUTLINED, "Prochaine maintenance", _equipment_next_label(eq)),
                    _info_chip(ft.Icons.HANDYMAN_OUTLINED, "Interventions",
                        f"{eq.get('interventions', 0)} total  ({eq.get('open_interventions', 0)} ouverte(s))"),
                ], spacing=10, wrap=True),
            ], spacing=12),
        )

        timeline_items: list[ft.Control] = []
        if not recent:
            timeline_items = [ft.Text("Aucune intervention enregistrée pour cet équipement.", color=_DK_MUTED, size=12)]
        else:
            for row in recent:
                item_color = _status_color(row.get("status"))
                timeline_items.append(ft.Container(
                    border=ft.border.only(
                        left=ft.BorderSide(3, item_color), bottom=ft.BorderSide(1, _DK_BORDER)),
                    padding=ft.padding.only(left=12, top=8, bottom=8, right=8),
                    content=ft.Row([
                        ft.Column([
                            ft.Text(_type_label(row.get("maintenance_type")), size=12, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                            ft.Text(f"Date: {row.get('planned_date') or '-'}  |  Coût: {float(row.get('cost') or 0):,.0f} FCFA", size=10, color=_DK_MUTED),
                            ft.Text(f"Responsable: {_person_name(row, 'responsable_nom', 'responsable_prenom') or '-'}", size=10, color=_DK_MUTED),
                        ], spacing=2, expand=True),
                        ft.Row([
                            _badge(_status_label(row.get("status")), item_color),
                            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=16, tooltip="Modifier",
                                on_click=lambda e, r=row: (edit_maintenance(r), _update())),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=16, tooltip="Supprimer",
                                on_click=lambda e, mid=row["id_maintenance"]: remove_maintenance(int(mid))),
                        ], spacing=2),
                    ], vertical_alignment=ft.CrossAxisAlignment.START),
                ))

        intervention_form = _form_panel(
            f"Nouvelle intervention — {_equipment_label(eq)}",
            ft.Icons.HANDYMAN_OUTLINED, PRIMARY,
            [
                ft.Row([
                    _maintenance_hint_card(ft.Icons.SPEED_OUTLINED, "Compteur", "Alertes km calculées auto.", PRIMARY),
                    _maintenance_hint_card(ft.Icons.CALCULATE_OUTLINED, "Calcul auto", "Prochain KM = dernier + intervalle.", SUCCESS),
                ], spacing=10, wrap=True),
                _field_group("Équipement (pré-rempli depuis la fiche)", [equipment_code, equipment_name, equipment_category]),
                _field_group("Planification", [maintenance_type, maintenance_priority, maintenance_status]),
                _field_group("Dates", [planned_date, completed_date, next_due_date]),
                _field_group("Odométrie", [current_odometer, last_service_odometer, service_interval_km, next_due_odometer],
                    hint="Prochain KM calculé auto depuis dernier KM + intervalle."),
                _field_group("Site & Responsable", [maintenance_site, maintenance_responsible]),
                _field_group("Coûts & observations", [maintenance_cost, maintenance_observations]),
                ft.Row([save_maintenance_button, cancel_maintenance_button, status], spacing=10, wrap=True),
            ],
        )

        tab2_col.controls = [
            back_btn,
            eq_header,
            ft.ResponsiveRow([
                ft.Container(_panel("Interventions récentes", timeline_items), col={"xs": 12, "lg": 5}),
                ft.Container(intervention_form, col={"xs": 12, "lg": 7}),
            ], spacing=12, run_spacing=12),
        ]

    def _back_to_browser() -> None:
        state["selected_eq"] = None
        reset_maintenance_form()
        render_tab2()
        _update()

    def _show_new_intervention_form() -> None:
        state["selected_eq"] = {"_generic": True}
        reset_maintenance_form()
        form = _form_panel("Nouvelle intervention", ft.Icons.HANDYMAN_OUTLINED, PRIMARY, [
            ft.Row([
                _maintenance_hint_card(ft.Icons.SPEED_OUTLINED, "Compteur", "Alertes km calculées auto.", PRIMARY),
                _maintenance_hint_card(ft.Icons.CALCULATE_OUTLINED, "Calcul auto", "Prochain KM = dernier + intervalle.", SUCCESS),
                _maintenance_hint_card(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, "Rappel", "Échéances date et km surveillées.", WARNING),
            ], wrap=True, spacing=10, run_spacing=8),
            _field_group("Équipement", [equipment_code, equipment_name, equipment_category, maintenance_site, maintenance_responsible]),
            _field_group("Planification", [maintenance_type, maintenance_priority, maintenance_status, planned_date, completed_date, next_due_date]),
            _field_group("Odométrie", [current_odometer, last_service_odometer, service_interval_km, next_due_odometer],
                hint="Le prochain KM est calculé auto depuis le dernier KM + intervalle."),
            _field_group("Coûts & observations", [maintenance_cost, maintenance_observations]),
            ft.Row([save_maintenance_button, cancel_maintenance_button, status], spacing=10, wrap=True),
        ])
        tab2_col.controls = [
            ft.TextButton("← Retour au catalogue", style=ft.ButtonStyle(color=_DK_MUTED), on_click=lambda e: _back_to_browser()),
            form,
        ]
        _update()

    def render_tab2() -> None:
        eq = state.get("selected_eq")
        if eq is None:
            render_equipment_browser()
        elif not eq.get("_generic"):
            render_equipment_fiche(eq)

    # ── Tab 3: Suivi HSE ─────────────────────────────────────────────────────────────────

    suivi_actions_section = ft.Column(controls=[
        action_kpi_row,
        _form_panel("Enregistrer une action corrective", ft.Icons.ADD_TASK_OUTLINED, SUCCESS, [
            _field_group("Identification", [action_source, action_title, action_description]),
            _field_group("Responsabilité & site", [action_site, action_owner]),
            _field_group("Suivi", [action_priority, action_status, action_due_date, action_closed_date, action_progress, save_action_button, cancel_action_button]),
        ]),
        _form_panel("Action tracker", ft.Icons.LIST_ALT_OUTLINED, MUTED, [
            ft.Row([action_search, action_status_filter], spacing=10, wrap=True),
            action_table,
        ]),
    ], spacing=14, visible=True)

    suivi_risques_section = ft.Column(controls=[
        risk_kpi_row,
        _form_panel("Évaluation des risques ISO 12100", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, DANGER, [
            ft.Text("Identifier le danger, évaluer le risque initial, appliquer la hiérarchie des contrôles puis suivre le risque résiduel.",
                size=12, color=_DK_MUTED, italic=True),
            _field_group("Identification du danger", [risk_activity, risk_task, risk_hazard, risk_event, risk_consequences, risk_existing_controls]),
            _field_group("Site & responsable", [risk_site, risk_owner]),
            _field_group("Évaluation initiale", [risk_probability_initial, risk_severity_initial]),
            _field_group("Contrôles de maîtrise ISO", [risk_hierarchy, risk_additional_controls]),
            _field_group("Évaluation résiduelle", [risk_probability_residual, risk_severity_residual]),
            _field_group("Statut & échéances", [risk_status, risk_due_date, risk_review_date]),
            ft.Row([risk_ai_button, save_risk_button, cancel_risk_button], spacing=8),
            risk_ai_output,
        ]),
        risk_matrix_container,
        _form_panel("Registre des risques", ft.Icons.LIST_ALT_OUTLINED, MUTED, [
            ft.Row([risk_search, risk_status_filter], spacing=10, wrap=True),
            risk_table,
        ]),
    ], spacing=14, visible=False)

    suivi_pieces_section = ft.Column(controls=[
        ft.Container(bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row([part_search_field], spacing=10, wrap=True)),
        parts_content,
    ], spacing=14, visible=False)

    suivi_inspections_section = ft.Column(controls=[
        ft.Container(bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row([inspection_search_field], spacing=10, wrap=True)),
        inspections_content,
    ], spacing=14, visible=False)

    _suivi_defs = [
        ("actions",      "Actions correctives",    ft.Icons.TASK_ALT_OUTLINED,         SUCCESS),
        ("risques",      "Évaluation des risques", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, DANGER),
        ("pieces",       "Pièces & Stocks",        ft.Icons.INVENTORY_2_OUTLINED,       WARNING),
        ("inspections",  "Inspections",            ft.Icons.FACT_CHECK_OUTLINED,        PRIMARY),
    ]
    _suivi_sections = {
        "actions":     suivi_actions_section,
        "risques":     suivi_risques_section,
        "pieces":      suivi_pieces_section,
        "inspections": suivi_inspections_section,
    }
    _suivi_btns: dict[str, ft.ElevatedButton] = {}

    def switch_suivi_tab(key: str) -> None:
        state["suivi_tab"] = key
        for k, sec in _suivi_sections.items():
            sec.visible = k == key
        for k, btn in _suivi_btns.items():
            _, _, _, accent = next(d for d in _suivi_defs if d[0] == k)
            btn.style = (
                ft.ButtonStyle(bgcolor=accent, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=7), elevation=2)
                if k == key else
                ft.ButtonStyle(bgcolor=_DK_CARD, color=_DK_MUTED, shape=ft.RoundedRectangleBorder(radius=7), side=ft.BorderSide(1, _DK_BORDER), elevation=0)
            )
        _update()

    for key, label, icon, accent in _suivi_defs:
        _suivi_btns[key] = ft.ElevatedButton(
            label, icon=icon,
            on_click=lambda e, k=key: switch_suivi_tab(k),
            style=ft.ButtonStyle(bgcolor=_DK_CARD, color=_DK_MUTED, shape=ft.RoundedRectangleBorder(radius=7),
                side=ft.BorderSide(1, _DK_BORDER), elevation=0),
        )

    suivi_bar = ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row([
            ft.Row([_suivi_btns[k] for k, *_ in _suivi_defs], spacing=6, wrap=True, expand=True),
            ft.Row([
                ft.IconButton(ft.Icons.DOWNLOAD_OUTLINED, tooltip="Export actions Excel", icon_color=PRIMARY, on_click=export_actions),
                ft.IconButton(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, tooltip="Export risques Excel", icon_color=DANGER, on_click=export_risks),
            ], spacing=4),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    tab3_col = ft.Column(controls=[
        suivi_bar,
        suivi_actions_section,
        suivi_risques_section,
        suivi_pieces_section,
        suivi_inspections_section,
    ], spacing=14, visible=False)

    # ── Tab 1: Vue d'ensemble ────────────────────────────────────────────────────────────

    tab1_col = ft.Column(controls=[
        dashboard_content,
        _form_panel("Centre des alertes maintenance", ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, DANGER, [alerts_content]),
        _form_panel("Pilotage financier", ft.Icons.QUERY_STATS_OUTLINED, WARNING, [costs_content]),
    ], spacing=14, visible=True)

    # ── Main tab bar ─────────────────────────────────────────────────────────────────────

    _main_defs = [
        ("dashboard", "Vue d'ensemble",  ft.Icons.DASHBOARD_OUTLINED,               "#6366F1"),
        ("equipment", "Équipements",     ft.Icons.PRECISION_MANUFACTURING_OUTLINED, PRIMARY),
        ("suivi",     "Suivi HSE",       ft.Icons.HEALTH_AND_SAFETY_OUTLINED,       SUCCESS),
    ]
    _main_btns: dict[str, ft.ElevatedButton] = {}
    _main_cols = {"dashboard": tab1_col, "equipment": tab2_col, "suivi": tab3_col}

    def switch_main_tab(key: str) -> None:
        state["tab"] = key
        for k, col in _main_cols.items():
            col.visible = k == key
        for k, btn in _main_btns.items():
            _, _, _, accent = next(d for d in _main_defs if d[0] == k)
            btn.style = (
                ft.ButtonStyle(bgcolor=accent, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=8), elevation=2)
                if k == key else
                ft.ButtonStyle(bgcolor=_DK_CARD, color=_DK_MUTED, shape=ft.RoundedRectangleBorder(radius=8),
                    side=ft.BorderSide(1, _DK_BORDER), elevation=0)
            )
        _update()

    for key, label, icon, accent in _main_defs:
        _main_btns[key] = ft.ElevatedButton(
            label, icon=icon,
            on_click=lambda e, k=key: switch_main_tab(k),
            style=ft.ButtonStyle(bgcolor=_DK_CARD, color=_DK_MUTED, shape=ft.RoundedRectangleBorder(radius=8),
                side=ft.BorderSide(1, _DK_BORDER), elevation=0),
        )

    tab_bar = ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=10, padding=12,
        content=ft.Column([
            ft.Row([
                ft.Row([_main_btns[k] for k, *_ in _main_defs], spacing=8, wrap=True, expand=True),
                ft.Row([
                    ft.IconButton(ft.Icons.REFRESH, tooltip="Actualiser", icon_color=PRIMARY, on_click=lambda e: refresh(e)),
                    ft.ElevatedButton("Export Excel", icon=ft.Icons.TABLE_CHART_OUTLINED, on_click=export_maintenance,
                        style=ft.ButtonStyle(bgcolor=PRIMARY, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=7))),
                    status,
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            summary_row,
        ], spacing=12),
    )

    # ── Event bindings ───────────────────────────────────────────────────────────────────

    for control in (action_search, action_status_filter, risk_search, risk_status_filter,
                    part_search_field, inspection_search_field):
        control.on_change = lambda e: (refresh(), None)[1]
    eq_search_field.on_change = lambda e: (render_tab2(), _update())
    for control in (last_service_odometer, service_interval_km):
        control.on_change = update_next_due_odometer
    save_maintenance_button.on_click   = save_maintenance
    cancel_maintenance_button.on_click = lambda e: (reset_maintenance_form(), refresh())
    save_action_button.on_click        = save_action
    cancel_action_button.on_click      = lambda e: (reset_action_form(), refresh())
    save_risk_button.on_click          = save_risk
    risk_ai_button.on_click            = ask_risk_ai
    cancel_risk_button.on_click        = lambda e: (reset_risk_form(), refresh())
    save_part_button.on_click          = save_part
    cancel_part_button.on_click        = lambda e: (reset_part_form(), refresh())
    save_inspection_button.on_click    = save_inspection
    cancel_inspection_button.on_click  = lambda e: (reset_inspection_form(), refresh())

    # ── refresh() ────────────────────────────────────────────────────────────────────────

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            sync = synchronize_maintenance_management()
            if event is not None:
                notify(
                    f"Synchronisation: {sync['maintenance']} retard(s), {sync['odometers']} compteur(s) recalculés.",
                    SUCCESS,
                )
            render_summary()
            render_dashboard()
            render_alerts()
            render_costs()
            render_parts()
            render_inspections()
            render_actions()
            render_risks()
            render_tab2()
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    # ── Root layout ──────────────────────────────────────────────────────────────────────

    root = ft.Column(
        controls=[
            module_header(
                "Equipment Maintenance Management",
                "Pilotage des équipements, interventions, coûts, alertes et risques.",
            ),
            tab_bar,
            tab1_col,
            tab2_col,
            tab3_col,
        ],
        spacing=14,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    switch_main_tab("dashboard")
    switch_suivi_tab("actions")
    refresh()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


# ── Module-level utilities ────────────────────────────────────────────────────────────────


def _priority_dropdown() -> ft.Dropdown:
    return ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F",
        focused_border_color="#2563EB",
        label_style=ft.TextStyle(color="#9DB0C5"),
        text_style=ft.TextStyle(color="#E2E8F0"),
        label="Priorité", value="moyenne", width=150,
        options=[
            ft.dropdown.Option("basse", "Basse"),
            ft.dropdown.Option("moyenne", "Moyenne"),
            ft.dropdown.Option("haute", "Haute"),
            ft.dropdown.Option("critique", "Critique"),
        ],
    )


def _scale_dropdown(label: str, value: str) -> ft.Dropdown:
    return ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F",
        focused_border_color="#2563EB",
        label_style=ft.TextStyle(color="#9DB0C5"),
        text_style=ft.TextStyle(color="#E2E8F0"),
        label=label, value=value, width=145,
        options=[ft.dropdown.Option(str(i), str(i)) for i in range(1, 6)],
    )


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Row([
            ft.Container(width=4, bgcolor=color, expand=False),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10), expand=True,
                content=ft.Row([
                    ft.Icon(icon, color=color, size=20),
                    ft.Column([
                        ft.Text(str(value), size=18, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                        ft.Text(label, size=11, color=_DK_MUTED),
                    ], spacing=1, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
        ], spacing=0),
    )


def _maintenance_hint_card(icon: str, title: str, description: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=10), width=310,
        content=ft.Row([
            ft.Container(bgcolor=_DK_CARD2, border=ft.border.all(1, color), border_radius=8, padding=8,
                content=ft.Icon(icon, color=color, size=18)),
            ft.Column([
                ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                ft.Text(description, size=11, color=_DK_MUTED),
            ], spacing=2, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )


def _panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=8,
        padding=0, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column([
            ft.Container(bgcolor=_DK_HEAD, border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                content=ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=_DK_TEXT)),
            ft.Container(padding=16, content=ft.Column(controls, spacing=12)),
        ], spacing=0),
    )


def _analysis_panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return _panel(title, controls or [ft.Text("Aucune donnée disponible.", color=_DK_MUTED, size=12)])


def _section_toolbar(title: str, subtitle: str, icon: str) -> ft.Control:
    return ft.Row([
        ft.Container(bgcolor=_DK_HEAD, border_radius=7, padding=8, content=ft.Icon(icon, color=PRIMARY, size=20)),
        ft.Column([
            ft.Text(title, color=_DK_TEXT, size=16, weight=ft.FontWeight.BOLD),
            ft.Text(subtitle, color=_DK_MUTED, size=11),
        ], spacing=1, expand=True),
    ], spacing=10)


def _info_chip(icon: str, label: str, value: str) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD2, border=ft.border.all(1, _DK_BORDER), border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row([
            ft.Icon(icon, color=_DK_MUTED, size=14),
            ft.Column([
                ft.Text(label, size=9, color=_DK_MUTED),
                ft.Text(value, size=11, color=_DK_TEXT, weight=ft.FontWeight.W_600),
            ], spacing=1),
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )


def _metric_bar(label: str, value: int, total: int, color: str) -> ft.Control:
    percent = min(max(value / max(total, 1), 0), 1)
    return ft.Column([
        ft.Row([
            ft.Text(label, size=12, color=_DK_TEXT, expand=True),
            ft.Text(f"{value} ({round(percent * 100)}%)", size=12, color=color, weight=ft.FontWeight.BOLD),
        ]),
        ft.ProgressBar(value=percent, color=color, bgcolor=_DK_TRACK, height=7),
    ], spacing=4)


def _metric_value_line(label: str, value: float, total: float) -> ft.Control:
    percent = float(value or 0) / max(float(total or 0), 1)
    return ft.Column([
        ft.Row([
            ft.Text(label, color=_DK_TEXT, size=12, expand=True),
            ft.Text(f"{value:,.0f} FCFA", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD),
        ]),
        ft.ProgressBar(value=min(percent, 1), color=PRIMARY, bgcolor=_DK_TRACK, height=7),
    ], spacing=4)


def _maintenance_preview_panel(title: str, rows: list[dict[str, Any]], alert: bool) -> ft.Control:
    controls: list[ft.Control] = []
    for row in rows:
        color = _next_due_color(row) if alert else _status_color(row.get("status"))
        controls.append(ft.Container(
            border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
            padding=ft.padding.symmetric(vertical=8),
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED if alert else ft.Icons.HANDYMAN_OUTLINED, color=color, size=18),
                ft.Column([
                    ft.Text(_equipment_label(row), size=12, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                    ft.Text(f"{_type_label(row.get('maintenance_type'))} | {_next_due_label(row)}", size=10, color=_DK_MUTED),
                ], spacing=1, expand=True),
                _badge(_status_label(row.get("status")), color),
            ], spacing=8),
        ))
    return _analysis_panel(title, controls)


def _synchronous_alert_card(title: str, detail: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, color), border_radius=8, padding=11,
        content=ft.Row([
            ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=color, size=20),
            ft.Column([
                ft.Text(title, color=_DK_TEXT, size=12, weight=ft.FontWeight.BOLD),
                ft.Text(detail, color=_DK_MUTED, size=11),
            ], spacing=2, expand=True),
            _badge("Ouverte", color),
        ], spacing=9),
    )


def _insight_line(icon: str, text: str, color: str) -> ft.Control:
    return ft.Row([ft.Icon(icon, color=color, size=18), ft.Text(text, size=12, color=_DK_TEXT, expand=True)], spacing=8)


def _badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD2, border=ft.border.all(1, color), border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
        content=ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_600),
    )


def _form_panel(title: str, icon: str, accent: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=10,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column([
            ft.Container(
                bgcolor=_DK_HEAD,
                border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER), left=ft.BorderSide(4, accent)),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                content=ft.Row([
                    ft.Container(bgcolor=_DK_CARD2, border_radius=8, padding=8,
                        content=ft.Icon(icon, color=accent, size=18)),
                    ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            ft.Container(padding=16, content=ft.Column(controls, spacing=14)),
        ], spacing=0),
    )


def _field_group(label: str, controls: list[ft.Control], hint: str = "") -> ft.Control:
    header: list[ft.Control] = [ft.Text(label.upper(), size=10, color=_DK_MUTED, weight=ft.FontWeight.W_700)]
    if hint:
        header.append(ft.Text(hint, size=10, color=_DK_MUTED, italic=True))
    return ft.Column([
        ft.Container(
            content=ft.Row(header, spacing=8),
            border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
            padding=ft.padding.only(bottom=5),
        ),
        ft.Row(controls, wrap=True, spacing=8, run_spacing=8),
    ], spacing=7)


def _equipment_label(row: dict[str, Any]) -> str:
    code = str(row.get("equipment_code") or "").strip()
    name = str(row.get("equipment_name") or "-")
    return f"{code} - {name}" if code else name


def _person_name(row: dict[str, Any], last_key: str, first_key: str) -> str:
    return f"{row.get(last_key) or ''} {row.get(first_key) or ''}".strip()


def _type_label(value: Any) -> str:
    return {
        "preventive": "Préventive", "oil_change": "Vidange / Oil change",
        "corrective": "Corrective", "inspection": "Inspection", "calibration": "Calibration",
    }.get(str(value or ""), str(value or "-"))


def _number_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _number_unit(value: Any, unit: str) -> str:
    text = _number_text(value)
    return f"{text} {unit}" if text else "-"


def _equipment_next_label(row: dict[str, Any]) -> str:
    values = []
    if row.get("next_due_date"):
        values.append(str(row["next_due_date"]))
    if row.get("next_due_odometer") is not None:
        values.append(_number_unit(row["next_due_odometer"], "km"))
    return " | ".join(values) if values else "-"


def _odometer_label(row: dict[str, Any]) -> str:
    current = row.get("current_odometer")
    if current in (None, ""):
        return "-"
    remaining = row.get("remaining_km")
    if remaining in (None, ""):
        return f"{float(current):g} km"
    return f"{float(current):g} km | reste {float(remaining):g}"


def _next_due_label(row: dict[str, Any]) -> str:
    labels = []
    if row.get("next_due_date"):
        labels.append(str(row.get("next_due_date")))
    if row.get("next_due_odometer") not in (None, ""):
        labels.append(f"{float(row.get('next_due_odometer')):g} km")
    return " | ".join(labels) if labels else "-"


def _next_due_color(row: dict[str, Any]) -> str:
    if row.get("status") == "en_retard":
        return DANGER
    remaining = row.get("remaining_km")
    if remaining not in (None, ""):
        value = float(remaining)
        if value <= 0:
            return DANGER
        if value <= 500:
            return WARNING
    return SUCCESS


def _status_label(value: Any) -> str:
    return {
        "planifiee": "Planifiée", "ouverte": "Ouverte", "en_cours": "En cours",
        "terminee": "Terminée", "annulee": "Annulée", "en_retard": "En retard",
    }.get(str(value or ""), str(value or "-"))


def _status_color(value: Any) -> str:
    return {
        "terminee": SUCCESS, "annulee": MUTED, "en_retard": DANGER,
        "en_cours": PRIMARY, "planifiee": WARNING, "ouverte": WARNING,
    }.get(str(value or ""), MUTED)


def _inspection_status_label(value: Any) -> str:
    return {
        "ok": "OK", "a_surveiller": "À surveiller", "en_retard": "En retard",
        "critique": "Critique", "hors_service": "Hors service",
    }.get(str(value or ""), str(value or "-"))


def _inspection_status_color(value: Any) -> str:
    return {"ok": SUCCESS, "a_surveiller": WARNING, "en_retard": WARNING, "critique": DANGER, "hors_service": DANGER}.get(str(value or ""), MUTED)


def _priority_color(value: Any) -> str:
    return {"critique": DANGER, "haute": WARNING, "moyenne": PRIMARY, "basse": SUCCESS}.get(str(value or ""), MUTED)


def _dk_row_color(status: Any, priority: Any) -> str | None:
    if status == "en_retard":
        return "#3B1111"
    if priority == "critique":
        return "#2D1700"
    return None


def _dk_risk_row_color(level: Any, status: Any) -> str | None:
    if status == "closed":
        return _DK_CARD2
    if level == "critical":
        return "#3B1111"
    if level == "high":
        return "#2D1700"
    return None


def _risk_activity_label(row: dict[str, Any]) -> str:
    return f"{row.get('activity') or '-'} | {row.get('hazard') or '-'} | {row.get('risk_event') or '-'}"


def _risk_score_label(row: dict[str, Any], prefix: str) -> str:
    score = row.get(f"risk_{prefix}") or 0
    level = _risk_level_label(row.get(f"level_{prefix}"))
    return f"{score} - {level}"


def _risk_level_label(value: Any) -> str:
    return {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}.get(str(value or ""), str(value or "-"))


def _risk_level_color(value: Any) -> str:
    return {"low": SUCCESS, "medium": PRIMARY, "high": WARNING, "critical": DANGER}.get(str(value or ""), MUTED)


def _risk_status_label(value: Any) -> str:
    return {"open": "Open", "in_progress": "In progress", "controlled": "Controlled", "closed": "Closed"}.get(str(value or ""), str(value or "-"))


def _risk_status_color(value: Any) -> str:
    return {"open": WARNING, "in_progress": PRIMARY, "controlled": SUCCESS, "closed": MUTED}.get(str(value or ""), MUTED)


def _control_label(value: Any) -> str:
    return {
        "elimination": "Élimination", "substitution": "Substitution",
        "engineering": "Engineering", "administrative": "Administrative", "ppe": "PPE / EPI",
    }.get(str(value or ""), str(value or "-"))


def _build_risk_matrix(risks: list[dict[str, Any]]) -> ft.Control:
    cell_counts: dict[tuple[int, int], int] = {}
    for risk in risks:
        if risk.get("status") in {"controlled", "closed"}:
            continue
        prob = int(risk.get("probability_residual") or 0)
        sev  = int(risk.get("severity_residual") or 0)
        if 1 <= prob <= 5 and 1 <= sev <= 5:
            cell_counts[(prob, sev)] = cell_counts.get((prob, sev), 0) + 1

    def _score_border(score: int) -> str:
        if score >= 17: return DANGER
        if score >= 13: return "#EF4444"
        if score >= 7:  return WARNING
        return SUCCESS

    def _score_bg(score: int) -> str:
        if score >= 17: return "#3B1111"
        if score >= 13: return "#2D1400"
        if score >= 7:  return "#2D2000"
        return "#0D2A12"

    def _score_level(score: int) -> str:
        if score >= 17: return "Critical"
        if score >= 13: return "High"
        if score >= 7:  return "Medium"
        return "Low"

    header_row = ft.Row([
        ft.Container(width=36, height=30),
        *[ft.Container(width=58, height=30, bgcolor=_DK_HEAD, border_radius=4,
            alignment=ft.Alignment(0, 0),
            content=ft.Text(f"G{s}", size=11, color=PRIMARY, weight=ft.FontWeight.W_700))
          for s in range(1, 6)],
    ], spacing=3)

    matrix_rows: list[ft.Control] = []
    for prob in range(5, 0, -1):
        row_cells: list[ft.Control] = [
            ft.Container(width=36, height=50, bgcolor=_DK_HEAD, border_radius=4,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(f"P{prob}", size=11, color=PRIMARY, weight=ft.FontWeight.W_700))
        ]
        for sev in range(1, 6):
            score = prob * sev
            count = cell_counts.get((prob, sev), 0)
            bc    = _score_border(score)
            bg    = _score_bg(score)
            row_cells.append(ft.Container(
                width=58, height=50, bgcolor=bg,
                border=ft.border.all(2 if count > 0 else 1, bc if count > 0 else _DK_BORDER),
                border_radius=6, alignment=ft.Alignment(0, 0),
                tooltip=f"P{prob} × G{sev} = {score} ({_score_level(score)}) — {count} risque(s) actif(s)",
                content=ft.Column([
                    ft.Text(str(count) if count > 0 else "", size=16, color=bc, weight=ft.FontWeight.BOLD),
                    ft.Text(str(score), size=9, color=bc if count > 0 else _DK_MUTED),
                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        matrix_rows.append(ft.Row(row_cells, spacing=3))

    legend = ft.Row([
        *[ft.Row([
            ft.Container(width=14, height=14, bgcolor=bg, border=ft.border.all(1, col), border_radius=3),
            ft.Text(lbl, size=10, color=_DK_MUTED),
        ], spacing=4) for lbl, col, bg in (
            ("Low  1–6", SUCCESS, "#0D2A12"),
            ("Medium  7–12", WARNING, "#2D2000"),
            ("High  13–16", "#EF4444", "#2D1400"),
            ("Critical  17–25", DANGER, "#3B1111"),
        )],
        ft.Text(f"  |  {sum(cell_counts.values())} risque(s) non contrôlé(s) sur {len(risks)} total",
            size=10, color=_DK_MUTED),
    ], spacing=14, wrap=True)

    return _form_panel("Matrice des risques résiduels — ISO 12100", ft.Icons.GRID_VIEW_OUTLINED, DANGER, [
        ft.Text(
            "Distribution des risques actifs par probabilité (P) et gravité (G). "
            "Les cellules colorées indiquent des risques non contrôlés.",
            size=11, color=_DK_MUTED, italic=True),
        ft.Column([header_row, *matrix_rows], spacing=3),
        legend,
    ])
