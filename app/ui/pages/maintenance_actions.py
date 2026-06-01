from __future__ import annotations

from typing import Any

import flet as ft

from app.services import (
    create_action,
    create_equipment_maintenance,
    delete_action,
    delete_equipment_maintenance,
    export_action_tracker_xlsx,
    export_equipment_maintenance_xlsx,
    get_maintenance_action_options,
    get_maintenance_action_summary,
    list_action_tracker,
    list_equipment_maintenance,
    today_iso,
    update_action,
    update_equipment_maintenance,
)
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def maintenance_actions_page() -> ft.Control:
    state: dict[str, int | None] = {"maintenance_id": None, "action_id": None}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=8, wrap=True)
    maintenance_table = ft.Column(spacing=8)
    action_table = ft.Column(spacing=8)

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
        try:
            delete_action(action_id)
            notify("Action supprimee.", SUCCESS)
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

    def render_summary() -> None:
        summary = get_maintenance_action_summary()
        summary_row.controls = [
            _summary_chip("Maintenances ouvertes", summary["maintenance_open"], PRIMARY, ft.Icons.HANDYMAN_OUTLINED),
            _summary_chip("Maint. retard", summary["maintenance_late"], DANGER if summary["maintenance_late"] else SUCCESS, ft.Icons.WARNING_AMBER_OUTLINED),
            _summary_chip("Actions ouvertes", summary["actions_open"], PRIMARY, ft.Icons.TASK_ALT_OUTLINED),
            _summary_chip("Actions retard", summary["actions_late"], DANGER if summary["actions_late"] else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _summary_chip("Critiques", int(summary["maintenance_critical"]) + int(summary["actions_critical"]), WARNING, ft.Icons.PRIORITY_HIGH_OUTLINED),
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
                    ft.DataTable(
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
                    ft.DataTable(
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

    for control in (maintenance_search, maintenance_status_filter, action_search, action_status_filter):
        control.on_change = refresh
    save_maintenance_button.on_click = save_maintenance
    cancel_maintenance_button.on_click = lambda event: (reset_maintenance_form(), refresh())
    save_action_button.on_click = save_action
    cancel_action_button.on_click = lambda event: (reset_action_form(), refresh())

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


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=16),
                ft.Text(label, color=MUTED, size=11),
                ft.Text(str(value), color=color, size=13, weight=ft.FontWeight.BOLD),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
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
