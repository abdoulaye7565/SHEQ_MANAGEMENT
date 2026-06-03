from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    create_action,
    create_equipment_maintenance,
    create_risk_assessment,
    delete_action,
    delete_equipment_maintenance,
    delete_risk_assessment,
    export_action_tracker_xlsx,
    export_equipment_maintenance_xlsx,
    export_risk_assessments_xlsx,
    get_maintenance_action_options,
    get_maintenance_action_summary,
    list_action_tracker,
    list_equipment_maintenance,
    list_risk_assessments,
    today_iso,
    update_action,
    update_equipment_maintenance,
    update_risk_assessment,
)
from app.services.ai_service import AIConfigurationError, suggest_risk_assessment
from app.ui.components.confirm import confirm_action
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def maintenance_actions_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, int | None] = {"maintenance_id": None, "action_id": None, "risk_id": None}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    maintenance_table = ft.Column(spacing=8)
    action_table = ft.Column(spacing=8)
    risk_table = ft.Column(spacing=8)

    options = get_maintenance_action_options()
    site_options = [ft.dropdown.Option("", "Site non renseigne")] + [
        ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["sites"]
    ]
    employee_options = [ft.dropdown.Option("", "Responsable non renseigne")] + [
        ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["employees"]
    ]

    maintenance_search = ft.TextField(label="Recherche maintenance", prefix_icon=ft.Icons.SEARCH, width=260)
    maintenance_status_filter = ft.Dropdown(
        label="Statut",
        value="all",
        width=190,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("planifiee", "Planifiee"),
            ft.dropdown.Option("en_cours", "En cours"),
            ft.dropdown.Option("terminee", "Terminee"),
            ft.dropdown.Option("en_retard", "En retard"),
            ft.dropdown.Option("annulee", "Annulee"),
        ],
    )
    equipment_code = ft.TextField(label="Code equipement", width=160)
    equipment_name = ft.TextField(label="Equipement", width=240)
    equipment_category = ft.TextField(label="Categorie", width=170)
    maintenance_site = ft.Dropdown(label="Site", width=190, options=site_options)
    maintenance_responsible = ft.Dropdown(label="Responsable", width=240, options=employee_options)
    maintenance_type = ft.Dropdown(
        label="Type",
        value="preventive",
        width=160,
        options=[
            ft.dropdown.Option("preventive", "Preventive"),
            ft.dropdown.Option("corrective", "Corrective"),
            ft.dropdown.Option("inspection", "Inspection"),
            ft.dropdown.Option("calibration", "Calibration"),
        ],
    )
    maintenance_priority = _priority_dropdown()
    maintenance_status = ft.Dropdown(
        label="Statut",
        value="planifiee",
        width=160,
        options=[
            ft.dropdown.Option("planifiee", "Planifiee"),
            ft.dropdown.Option("en_cours", "En cours"),
            ft.dropdown.Option("terminee", "Terminee"),
            ft.dropdown.Option("annulee", "Annulee"),
        ],
    )
    planned_date = ft.TextField(label="Date planifiee", value=today_iso(), hint_text="AAAA-MM-JJ", width=160)
    completed_date = ft.TextField(label="Date terminee", hint_text="AAAA-MM-JJ", width=160)
    next_due_date = ft.TextField(label="Prochaine echeance", hint_text="AAAA-MM-JJ", width=180)
    maintenance_cost = ft.TextField(label="Cout", value="0", width=110)
    maintenance_observations = ft.TextField(label="Observations", width=260)
    save_maintenance_button = ft.ElevatedButton("Creer", icon=ft.Icons.ADD_OUTLINED)
    cancel_maintenance_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)

    action_search = ft.TextField(label="Recherche action", prefix_icon=ft.Icons.SEARCH, width=260)
    action_status_filter = ft.Dropdown(
        label="Statut",
        value="all",
        width=190,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("ouverte", "Ouverte"),
            ft.dropdown.Option("en_cours", "En cours"),
            ft.dropdown.Option("terminee", "Terminee"),
            ft.dropdown.Option("en_retard", "En retard"),
            ft.dropdown.Option("annulee", "Annulee"),
        ],
    )
    action_source = ft.TextField(label="Source", value="HSE", width=150)
    action_title = ft.TextField(label="Action", width=260)
    action_description = ft.TextField(label="Description", width=320)
    action_site = ft.Dropdown(label="Site", width=190, options=site_options)
    action_owner = ft.Dropdown(label="Responsable", width=240, options=employee_options)
    action_priority = _priority_dropdown()
    action_status = ft.Dropdown(
        label="Statut",
        value="ouverte",
        width=160,
        options=[
            ft.dropdown.Option("ouverte", "Ouverte"),
            ft.dropdown.Option("en_cours", "En cours"),
            ft.dropdown.Option("terminee", "Terminee"),
            ft.dropdown.Option("annulee", "Annulee"),
        ],
    )
    action_due_date = ft.TextField(label="Echeance", value=today_iso(), hint_text="AAAA-MM-JJ", width=150)
    action_closed_date = ft.TextField(label="Cloture", hint_text="AAAA-MM-JJ", width=150)
    action_progress = ft.TextField(label="Avancement %", value="0", width=140)
    save_action_button = ft.ElevatedButton("Creer", icon=ft.Icons.ADD_TASK_OUTLINED)
    cancel_action_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)

    risk_search = ft.TextField(label="Recherche risque", prefix_icon=ft.Icons.SEARCH, width=260)
    risk_status_filter = ft.Dropdown(
        label="Statut risque",
        value="all",
        width=190,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("open", "Open"),
            ft.dropdown.Option("in_progress", "In progress"),
            ft.dropdown.Option("controlled", "Controlled"),
            ft.dropdown.Option("closed", "Closed"),
        ],
    )
    risk_activity = ft.TextField(label="Activite / zone", width=220)
    risk_task = ft.TextField(label="Tache", width=220)
    risk_hazard = ft.TextField(label="Danger", width=240)
    risk_event = ft.TextField(label="Evenement redoute", width=260)
    risk_consequences = ft.TextField(label="Consequences", width=300)
    risk_existing_controls = ft.TextField(label="Controles existants", width=300)
    risk_site = ft.Dropdown(label="Site", width=190, options=site_options)
    risk_owner = ft.Dropdown(label="Responsable", width=240, options=employee_options)
    risk_probability_initial = _scale_dropdown("Prob. initiale", "3")
    risk_severity_initial = _scale_dropdown("Gravite initiale", "3")
    risk_hierarchy = ft.Dropdown(
        label="Controle ISO",
        value="administrative",
        width=190,
        options=[
            ft.dropdown.Option("elimination", "Elimination"),
            ft.dropdown.Option("substitution", "Substitution"),
            ft.dropdown.Option("engineering", "Engineering"),
            ft.dropdown.Option("administrative", "Administrative"),
            ft.dropdown.Option("ppe", "PPE / EPI"),
        ],
    )
    risk_additional_controls = ft.TextField(label="Mesures de maitrise", width=320)
    risk_probability_residual = _scale_dropdown("Prob. residuelle", "2")
    risk_severity_residual = _scale_dropdown("Gravite residuelle", "2")
    risk_status = ft.Dropdown(
        label="Statut",
        value="open",
        width=160,
        options=[
            ft.dropdown.Option("open", "Open"),
            ft.dropdown.Option("in_progress", "In progress"),
            ft.dropdown.Option("controlled", "Controlled"),
            ft.dropdown.Option("closed", "Closed"),
        ],
    )
    risk_due_date = ft.TextField(label="Echeance action", hint_text="AAAA-MM-JJ", width=160)
    risk_review_date = ft.TextField(label="Date revue", value=today_iso(), hint_text="AAAA-MM-JJ", width=160)
    save_risk_button = ft.ElevatedButton("Creer", icon=ft.Icons.ADD_OUTLINED)
    cancel_risk_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)
    risk_ai_button = ft.OutlinedButton("Suggestion IA", icon=ft.Icons.AUTO_AWESOME_OUTLINED)
    risk_ai_output = ft.TextField(
        label="Suggestion IA QHSE",
        multiline=True,
        min_lines=4,
        max_lines=8,
        read_only=True,
        expand=True,
        value="",
    )

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        render_summary()
        render_maintenance()
        render_actions()
        render_risks()
        _update()

    def reset_maintenance_form() -> None:
        state["maintenance_id"] = None
        equipment_code.value = ""
        equipment_name.value = ""
        equipment_category.value = ""
        maintenance_site.value = ""
        maintenance_responsible.value = ""
        maintenance_type.value = "preventive"
        maintenance_priority.value = "moyenne"
        maintenance_status.value = "planifiee"
        planned_date.value = today_iso()
        completed_date.value = ""
        next_due_date.value = ""
        maintenance_cost.value = "0"
        maintenance_observations.value = ""
        save_maintenance_button.text = "Creer"
        save_maintenance_button.icon = ft.Icons.ADD_OUTLINED
        cancel_maintenance_button.visible = False

    def reset_action_form() -> None:
        state["action_id"] = None
        action_source.value = "HSE"
        action_title.value = ""
        action_description.value = ""
        action_site.value = ""
        action_owner.value = ""
        action_priority.value = "moyenne"
        action_status.value = "ouverte"
        action_due_date.value = today_iso()
        action_closed_date.value = ""
        action_progress.value = "0"
        save_action_button.text = "Creer"
        save_action_button.icon = ft.Icons.ADD_TASK_OUTLINED
        cancel_action_button.visible = False

    def reset_risk_form() -> None:
        state["risk_id"] = None
        risk_activity.value = ""
        risk_task.value = ""
        risk_hazard.value = ""
        risk_event.value = ""
        risk_consequences.value = ""
        risk_existing_controls.value = ""
        risk_site.value = ""
        risk_owner.value = ""
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
        save_risk_button.text = "Creer"
        save_risk_button.icon = ft.Icons.ADD_OUTLINED
        cancel_risk_button.visible = False

    def risk_payload() -> dict[str, Any]:
        return {
            "activity": risk_activity.value,
            "task": risk_task.value,
            "hazard": risk_hazard.value,
            "risk_event": risk_event.value,
            "consequences": risk_consequences.value,
            "existing_controls": risk_existing_controls.value,
            "site_id": risk_site.value,
            "owner_employee_id": risk_owner.value,
            "probability_initial": risk_probability_initial.value,
            "severity_initial": risk_severity_initial.value,
            "hierarchy_control": risk_hierarchy.value,
            "additional_controls": risk_additional_controls.value,
            "probability_residual": risk_probability_residual.value,
            "severity_residual": risk_severity_residual.value,
            "status": risk_status.value,
            "due_date": risk_due_date.value,
            "review_date": risk_review_date.value,
        }

    def save_maintenance(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = {
                "equipment_code": equipment_code.value,
                "equipment_name": equipment_name.value,
                "category": equipment_category.value,
                "site_id": maintenance_site.value,
                "responsible_employee_id": maintenance_responsible.value,
                "maintenance_type": maintenance_type.value,
                "priority": maintenance_priority.value,
                "status": maintenance_status.value,
                "planned_date": planned_date.value,
                "completed_date": completed_date.value,
                "next_due_date": next_due_date.value,
                "cost": maintenance_cost.value,
                "observations": maintenance_observations.value,
            }
            if state["maintenance_id"] is None:
                create_equipment_maintenance(payload)
                notify("Maintenance creee.", SUCCESS)
            else:
                update_equipment_maintenance(int(state["maintenance_id"]), payload)
                notify("Maintenance modifiee.", SUCCESS)
            reset_maintenance_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_maintenance(row: dict[str, Any]) -> None:
        state["maintenance_id"] = int(row["id_maintenance"])
        equipment_code.value = str(row.get("equipment_code") or "")
        equipment_name.value = str(row.get("equipment_name") or "")
        equipment_category.value = str(row.get("category") or "")
        maintenance_site.value = str(row.get("site_id") or "")
        maintenance_responsible.value = str(row.get("responsible_employee_id") or "")
        maintenance_type.value = str(row.get("maintenance_type") or "preventive")
        maintenance_priority.value = str(row.get("priority") or "moyenne")
        maintenance_status.value = "en_cours" if row.get("status") == "en_retard" else str(row.get("status") or "planifiee")
        planned_date.value = str(row.get("planned_date") or today_iso())
        completed_date.value = str(row.get("completed_date") or "")
        next_due_date.value = str(row.get("next_due_date") or "")
        maintenance_cost.value = str(row.get("cost") or 0)
        maintenance_observations.value = str(row.get("observations") or "")
        save_maintenance_button.text = "Enregistrer"
        save_maintenance_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_maintenance_button.visible = True
        notify("Mode modification maintenance.", PRIMARY)
        _update()

    def remove_maintenance(maintenance_id: int) -> None:
        confirm_action(
            page,
            "Supprimer la maintenance",
            "Cette intervention de maintenance sera supprimee definitivement.",
            lambda: _remove_maintenance(maintenance_id),
            confirm_label="Supprimer",
            danger=True,
        )

    def _remove_maintenance(maintenance_id: int) -> None:
        try:
            delete_equipment_maintenance(maintenance_id)
            notify("Maintenance supprimee.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_action(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = {
                "source": action_source.value,
                "title": action_title.value,
                "description": action_description.value,
                "site_id": action_site.value,
                "owner_employee_id": action_owner.value,
                "priority": action_priority.value,
                "status": action_status.value,
                "due_date": action_due_date.value,
                "closed_date": action_closed_date.value,
                "progress": action_progress.value,
            }
            if state["action_id"] is None:
                create_action(payload)
                notify("Action creee.", SUCCESS)
            else:
                update_action(int(state["action_id"]), payload)
                notify("Action modifiee.", SUCCESS)
            reset_action_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_action(row: dict[str, Any]) -> None:
        state["action_id"] = int(row["id_action"])
        action_source.value = str(row.get("source") or "HSE")
        action_title.value = str(row.get("title") or "")
        action_description.value = str(row.get("description") or "")
        action_site.value = str(row.get("site_id") or "")
        action_owner.value = str(row.get("owner_employee_id") or "")
        action_priority.value = str(row.get("priority") or "moyenne")
        action_status.value = "en_cours" if row.get("status") == "en_retard" else str(row.get("status") or "ouverte")
        action_due_date.value = str(row.get("due_date") or today_iso())
        action_closed_date.value = str(row.get("closed_date") or "")
        action_progress.value = str(row.get("progress") or 0)
        save_action_button.text = "Enregistrer"
        save_action_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_action_button.visible = True
        notify("Mode modification action.", PRIMARY)
        _update()

    def remove_action(action_id: int) -> None:
        confirm_action(
            page,
            "Supprimer l'action",
            "Cette action du tracker sera supprimee definitivement.",
            lambda: _remove_action(action_id),
            confirm_label="Supprimer",
            danger=True,
        )

    def _remove_action(action_id: int) -> None:
        try:
            delete_action(action_id)
            notify("Action supprimee.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_risk(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = risk_payload()
            if state["risk_id"] is None:
                create_risk_assessment(payload)
                notify("Evaluation des risques creee.", SUCCESS)
            else:
                update_risk_assessment(int(state["risk_id"]), payload)
                notify("Evaluation des risques modifiee.", SUCCESS)
            reset_risk_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def ask_risk_ai(event: ft.ControlEvent | None = None) -> None:
        try:
            risk_ai_output.value = "Generation IA en cours..."
            notify("Analyse IA du risque en cours.", PRIMARY)
            _update()
            risk_ai_output.value = suggest_risk_assessment(risk_payload())
            notify("Suggestion IA generee. A valider avant enregistrement.", SUCCESS)
        except (ValueError, AIConfigurationError) as exc:
            risk_ai_output.value = ""
            notify(str(exc), DANGER)
        _update()

    def edit_risk(row: dict[str, Any]) -> None:
        state["risk_id"] = int(row["id_risk"])
        risk_activity.value = str(row.get("activity") or "")
        risk_task.value = str(row.get("task") or "")
        risk_hazard.value = str(row.get("hazard") or "")
        risk_event.value = str(row.get("risk_event") or "")
        risk_consequences.value = str(row.get("consequences") or "")
        risk_existing_controls.value = str(row.get("existing_controls") or "")
        risk_site.value = str(row.get("site_id") or "")
        risk_owner.value = str(row.get("owner_employee_id") or "")
        risk_probability_initial.value = str(row.get("probability_initial") or 3)
        risk_severity_initial.value = str(row.get("severity_initial") or 3)
        risk_hierarchy.value = str(row.get("hierarchy_control") or "administrative")
        risk_additional_controls.value = str(row.get("additional_controls") or "")
        risk_probability_residual.value = str(row.get("probability_residual") or 2)
        risk_severity_residual.value = str(row.get("severity_residual") or 2)
        risk_status.value = str(row.get("status") or "open")
        risk_due_date.value = str(row.get("due_date") or "")
        risk_review_date.value = str(row.get("review_date") or today_iso())
        save_risk_button.text = "Enregistrer"
        save_risk_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_risk_button.visible = True
        notify("Mode modification evaluation des risques.", PRIMARY)
        _update()

    def remove_risk(risk_id: int) -> None:
        confirm_action(
            page,
            "Supprimer l'evaluation",
            "Cette evaluation des risques sera supprimee definitivement.",
            lambda: _remove_risk(risk_id),
            confirm_label="Supprimer",
            danger=True,
        )

    def _remove_risk(risk_id: int) -> None:
        try:
            delete_risk_assessment(risk_id)
            notify("Evaluation des risques supprimee.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_maintenance(event: ft.ControlEvent | None = None) -> None:
        output = export_equipment_maintenance_xlsx()
        notify(f"Export maintenance cree: {output}", SUCCESS)
        _update()

    def export_actions(event: ft.ControlEvent | None = None) -> None:
        output = export_action_tracker_xlsx()
        notify(f"Export action tracker cree: {output}", SUCCESS)
        _update()

    def export_risks(event: ft.ControlEvent | None = None) -> None:
        output = export_risk_assessments_xlsx()
        notify(f"Export evaluation des risques cree: {output}", SUCCESS)
        _update()

    def render_summary() -> None:
        summary = get_maintenance_action_summary()
        summary_row.controls = [
            _summary_chip("Maintenances ouvertes", summary["maintenance_open"], PRIMARY, ft.Icons.HANDYMAN_OUTLINED),
            _summary_chip("Maint. retard", summary["maintenance_late"], DANGER if summary["maintenance_late"] else SUCCESS, ft.Icons.WARNING_AMBER_OUTLINED),
            _summary_chip("Actions ouvertes", summary["actions_open"], PRIMARY, ft.Icons.TASK_ALT_OUTLINED),
            _summary_chip("Actions retard", summary["actions_late"], DANGER if summary["actions_late"] else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _summary_chip("Critiques", int(summary["maintenance_critical"]) + int(summary["actions_critical"]), WARNING, ft.Icons.PRIORITY_HIGH_OUTLINED),
            _summary_chip("Risques ouverts", summary["risks_open"], PRIMARY, ft.Icons.HEALTH_AND_SAFETY_OUTLINED),
            _summary_chip("Risques residuels hauts", summary["risks_high_residual"], DANGER if summary["risks_high_residual"] else SUCCESS, ft.Icons.SHIELD_OUTLINED),
        ]

    def render_maintenance() -> None:
        rows = list_equipment_maintenance(str(maintenance_search.value or ""), str(maintenance_status_filter.value or "all"))
        maintenance_table.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"Planning maintenance ({len(rows)})", size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Equipement")),
                            ft.DataColumn(ft.Text("Site")),
                            ft.DataColumn(ft.Text("Type")),
                            ft.DataColumn(ft.Text("Priorite")),
                            ft.DataColumn(ft.Text("Statut")),
                            ft.DataColumn(ft.Text("Date")),
                            ft.DataColumn(ft.Text("Responsable")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                color=_row_color(row.get("status"), row.get("priority")),
                                cells=[
                                    ft.DataCell(ft.Text(_equipment_label(row), weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row.get("site") or "-"))),
                                    ft.DataCell(ft.Text(_type_label(row.get("maintenance_type")))),
                                    ft.DataCell(_badge(str(row.get("priority") or "-"), _priority_color(row.get("priority")))),
                                    ft.DataCell(_badge(_status_label(row.get("status")), _status_color(row.get("status")))),
                                    ft.DataCell(ft.Text(str(row.get("planned_date") or "-"))),
                                    ft.DataCell(ft.Text(_person_name(row, "responsable_nom", "responsable_prenom") or "-")),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Modifier", icon_color=PRIMARY, on_click=lambda event, item=row: edit_maintenance(item)),
                                                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", icon_color=DANGER, on_click=lambda event, item_id=row["id_maintenance"]: remove_maintenance(int(item_id))),
                                            ],
                                            spacing=0,
                                        )
                                    ),
                                ],
                            )
                            for row in rows
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    def render_actions() -> None:
        rows = list_action_tracker(str(action_search.value or ""), str(action_status_filter.value or "all"))
        action_table.controls = [
            ft.Text(f"Action tracker ({len(rows)})", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Source")),
                            ft.DataColumn(ft.Text("Action")),
                            ft.DataColumn(ft.Text("Site")),
                            ft.DataColumn(ft.Text("Responsable")),
                            ft.DataColumn(ft.Text("Priorite")),
                            ft.DataColumn(ft.Text("Statut")),
                            ft.DataColumn(ft.Text("Echeance")),
                            ft.DataColumn(ft.Text("%")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                color=_row_color(row.get("status"), row.get("priority")),
                                cells=[
                                    ft.DataCell(ft.Text(str(row.get("source") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("title") or "-"), weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row.get("site") or "-"))),
                                    ft.DataCell(ft.Text(_person_name(row, "owner_nom", "owner_prenom") or "-")),
                                    ft.DataCell(_badge(str(row.get("priority") or "-"), _priority_color(row.get("priority")))),
                                    ft.DataCell(_badge(_status_label(row.get("status")), _status_color(row.get("status")))),
                                    ft.DataCell(ft.Text(str(row.get("due_date") or "-"))),
                                    ft.DataCell(ft.Text(f"{row.get('progress') or 0}%")),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Modifier", icon_color=PRIMARY, on_click=lambda event, item=row: edit_action(item)),
                                                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", icon_color=DANGER, on_click=lambda event, item_id=row["id_action"]: remove_action(int(item_id))),
                                            ],
                                            spacing=0,
                                        )
                                    ),
                                ],
                            )
                            for row in rows
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    def render_risks() -> None:
        rows = list_risk_assessments(str(risk_search.value or ""), str(risk_status_filter.value or "all"))
        risk_table.controls = [
            ft.Text(f"Evaluation des risques ISO ({len(rows)})", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Activite / Danger")),
                            ft.DataColumn(ft.Text("Site")),
                            ft.DataColumn(ft.Text("Risque initial")),
                            ft.DataColumn(ft.Text("Controle ISO")),
                            ft.DataColumn(ft.Text("Risque residuel")),
                            ft.DataColumn(ft.Text("Responsable")),
                            ft.DataColumn(ft.Text("Statut")),
                            ft.DataColumn(ft.Text("Revue")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                color=_risk_row_color(row.get("level_residual"), row.get("status")),
                                cells=[
                                    ft.DataCell(ft.Text(_risk_activity_label(row), weight=ft.FontWeight.BOLD, width=260)),
                                    ft.DataCell(ft.Text(str(row.get("site") or "-"))),
                                    ft.DataCell(_badge(_risk_score_label(row, "initial"), _risk_level_color(row.get("level_initial")))),
                                    ft.DataCell(ft.Text(_control_label(row.get("hierarchy_control")))),
                                    ft.DataCell(_badge(_risk_score_label(row, "residual"), _risk_level_color(row.get("level_residual")))),
                                    ft.DataCell(ft.Text(_person_name(row, "owner_nom", "owner_prenom") or "-")),
                                    ft.DataCell(_badge(_risk_status_label(row.get("status")), _risk_status_color(row.get("status")))),
                                    ft.DataCell(ft.Text(str(row.get("review_date") or "-"))),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Modifier", icon_color=PRIMARY, on_click=lambda event, item=row: edit_risk(item)),
                                                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", icon_color=DANGER, on_click=lambda event, item_id=row["id_risk"]: remove_risk(int(item_id))),
                                            ],
                                            spacing=0,
                                        )
                                    ),
                                ],
                            )
                            for row in rows
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    for control in (maintenance_search, maintenance_status_filter, action_search, action_status_filter, risk_search, risk_status_filter):
        control.on_change = refresh
    save_maintenance_button.on_click = save_maintenance
    cancel_maintenance_button.on_click = lambda event: (reset_maintenance_form(), refresh())
    save_action_button.on_click = save_action
    cancel_action_button.on_click = lambda event: (reset_action_form(), refresh())
    save_risk_button.on_click = save_risk
    risk_ai_button.on_click = ask_risk_ai
    cancel_risk_button.on_click = lambda event: (reset_risk_form(), refresh())

    root = ft.Column(
        controls=[
            module_header(
                "Maintenance & Action Tracker",
                "Suivi maintenance equipements, actions HSE, echeances, priorites et exports Excel.",
            ),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                maintenance_search,
                                maintenance_status_filter,
                                action_search,
                                action_status_filter,
                                ft.IconButton(ft.Icons.REFRESH, tooltip="Actualiser", on_click=refresh),
                                ft.OutlinedButton("Export maintenance", icon=ft.Icons.TABLE_CHART_OUTLINED, on_click=export_maintenance),
                                ft.OutlinedButton("Export actions", icon=ft.Icons.FILE_DOWNLOAD_OUTLINED, on_click=export_actions),
                                ft.OutlinedButton("Export risques", icon=ft.Icons.SHIELD_OUTLINED, on_click=export_risks),
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                        summary_row,
                    ],
                    spacing=12,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Nouvelle maintenance equipement", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[
                                equipment_code,
                                equipment_name,
                                equipment_category,
                                maintenance_site,
                                maintenance_responsible,
                                maintenance_type,
                                maintenance_priority,
                                maintenance_status,
                                planned_date,
                                completed_date,
                                next_due_date,
                                maintenance_cost,
                                maintenance_observations,
                                save_maintenance_button,
                                cancel_maintenance_button,
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(bgcolor="#FFFFFF", border=ft.border.all(1, "#BFDBFE"), border_radius=8, padding=16, content=maintenance_table),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Nouvelle action", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[
                                action_source,
                                action_title,
                                action_description,
                                action_site,
                                action_owner,
                                action_priority,
                                action_status,
                                action_due_date,
                                action_closed_date,
                                action_progress,
                                save_action_button,
                                cancel_action_button,
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(bgcolor="#FFFFFF", border=ft.border.all(1, "#BFDBFE"), border_radius=8, padding=16, content=action_table),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Nouvelle evaluation des risques", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text("Methodologie ISO: identifier le danger, evaluer le risque initial, definir la maitrise selon la hierarchie des controles, puis suivre le risque residuel.", size=12, color=MUTED),
                        ft.Row(
                            controls=[
                                risk_activity,
                                risk_task,
                                risk_hazard,
                                risk_event,
                                risk_consequences,
                                risk_existing_controls,
                                risk_site,
                                risk_owner,
                                risk_probability_initial,
                                risk_severity_initial,
                                risk_hierarchy,
                                risk_additional_controls,
                                risk_probability_residual,
                                risk_severity_residual,
                                risk_status,
                                risk_due_date,
                                risk_review_date,
                                risk_ai_button,
                                save_risk_button,
                                cancel_risk_button,
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                        risk_ai_output,
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(bgcolor="#FFFFFF", border=ft.border.all(1, "#BFDBFE"), border_radius=8, padding=16, content=risk_table),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    return root


def _priority_dropdown() -> ft.Dropdown:
    return ft.Dropdown(
        label="Priorite",
        value="moyenne",
        width=150,
        options=[
            ft.dropdown.Option("basse", "Basse"),
            ft.dropdown.Option("moyenne", "Moyenne"),
            ft.dropdown.Option("haute", "Haute"),
            ft.dropdown.Option("critique", "Critique"),
        ],
    )


def _scale_dropdown(label: str, value: str) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        width=145,
        options=[ft.dropdown.Option(str(index), f"{index}") for index in range(1, 6)],
    )


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color, weight=ft.FontWeight.BOLD),
    )


def _equipment_label(row: dict[str, Any]) -> str:
    code = str(row.get("equipment_code") or "").strip()
    name = str(row.get("equipment_name") or "-")
    return f"{code} - {name}" if code else name


def _person_name(row: dict[str, Any], last_key: str, first_key: str) -> str:
    return f"{row.get(last_key) or ''} {row.get(first_key) or ''}".strip()


def _type_label(value: Any) -> str:
    return {
        "preventive": "Preventive",
        "corrective": "Corrective",
        "inspection": "Inspection",
        "calibration": "Calibration",
    }.get(str(value or ""), str(value or "-"))


def _status_label(value: Any) -> str:
    return {
        "planifiee": "Planifiee",
        "ouverte": "Ouverte",
        "en_cours": "En cours",
        "terminee": "Terminee",
        "annulee": "Annulee",
        "en_retard": "En retard",
    }.get(str(value or ""), str(value or "-"))


def _status_color(value: Any) -> str:
    return {
        "terminee": SUCCESS,
        "annulee": MUTED,
        "en_retard": DANGER,
        "en_cours": PRIMARY,
        "planifiee": WARNING,
        "ouverte": WARNING,
    }.get(str(value or ""), MUTED)


def _priority_color(value: Any) -> str:
    return {
        "critique": DANGER,
        "haute": WARNING,
        "moyenne": PRIMARY,
        "basse": SUCCESS,
    }.get(str(value or ""), MUTED)


def _row_color(status: Any, priority: Any) -> str | None:
    if status == "en_retard":
        return "#FEF2F2"
    if priority == "critique":
        return "#FFF7ED"
    return None


def _risk_activity_label(row: dict[str, Any]) -> str:
    activity = str(row.get("activity") or "-")
    hazard = str(row.get("hazard") or "-")
    event = str(row.get("risk_event") or "-")
    return f"{activity} | {hazard} | {event}"


def _risk_score_label(row: dict[str, Any], prefix: str) -> str:
    score = row.get(f"risk_{prefix}") or 0
    level = _risk_level_label(row.get(f"level_{prefix}"))
    return f"{score} - {level}"


def _risk_level_label(value: Any) -> str:
    return {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    }.get(str(value or ""), str(value or "-"))


def _risk_level_color(value: Any) -> str:
    return {
        "low": SUCCESS,
        "medium": PRIMARY,
        "high": WARNING,
        "critical": DANGER,
    }.get(str(value or ""), MUTED)


def _risk_status_label(value: Any) -> str:
    return {
        "open": "Open",
        "in_progress": "In progress",
        "controlled": "Controlled",
        "closed": "Closed",
    }.get(str(value or ""), str(value or "-"))


def _risk_status_color(value: Any) -> str:
    return {
        "open": WARNING,
        "in_progress": PRIMARY,
        "controlled": SUCCESS,
        "closed": MUTED,
    }.get(str(value or ""), MUTED)


def _control_label(value: Any) -> str:
    return {
        "elimination": "Elimination",
        "substitution": "Substitution",
        "engineering": "Engineering",
        "administrative": "Administrative",
        "ppe": "PPE / EPI",
    }.get(str(value or ""), str(value or "-"))


def _risk_row_color(level: Any, status: Any) -> str | None:
    if status == "closed":
        return "#F8FAFC"
    if level == "critical":
        return "#FEF2F2"
    if level == "high":
        return "#FFF7ED"
    return None
