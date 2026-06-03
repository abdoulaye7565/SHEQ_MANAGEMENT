from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    assign_ppe,
    create_ppe_item,
    delete_ppe_item,
    delete_ppe_requirement,
    export_ppe_inventory_xls,
    get_ppe_options,
    get_ppe_summary,
    list_ppe_alerts,
    list_ppe_assignments,
    list_ppe_compliance,
    list_ppe_inspections,
    list_ppe_items,
    list_ppe_requirements,
    list_stock_movements,
    record_ppe_inspection,
    record_stock_movement,
    return_ppe_assignment,
    save_ppe_requirement,
    update_ppe_item,
    today_iso,
)
from app.ui.components.confirm import confirm_action
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def ppe_page(page: ft.Page | None = None) -> ft.Control:
    status = ft.Text("", size=12, color=MUTED)
    selected_item_id: int | None = None
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    catalog_area = ft.Column(spacing=10)
    movement_area = ft.Column(spacing=10)
    assignment_area = ft.Column(spacing=10)
    requirement_area = ft.Column(spacing=8)
    compliance_area = ft.Column(spacing=8)
    inspection_area = ft.Column(spacing=8)
    alert_area = ft.Column(spacing=8)

    search_field = ft.TextField(label="Recherche EPI", prefix_icon=ft.Icons.SEARCH, width=260)
    type_field = ft.Dropdown(label="Type EPI", width=220)
    item_name_field = ft.TextField(label="Nom EPI", width=220)
    size_field = ft.TextField(label="Taille", width=120)
    standard_field = ft.TextField(label="Norme", width=160)
    brand_field = ft.TextField(label="Marque", width=160)
    model_field = ft.TextField(label="Modele", width=160)
    condition_field = ft.Dropdown(
        label="Etat",
        value="neuf",
        width=140,
        options=[
            ft.dropdown.Option("neuf", "Neuf"),
            ft.dropdown.Option("bon", "Bon"),
            ft.dropdown.Option("usage", "Usage"),
            ft.dropdown.Option("endommage", "Endommage"),
        ],
    )
    expiry_field = ft.TextField(label="Expiration", hint_text="AAAA-MM-JJ", width=160)
    initial_quantity_field = ft.TextField(label="Stock initial", value="0", width=130)
    threshold_field = ft.TextField(label="Seuil min.", value="0", width=130)
    save_item_button = ft.ElevatedButton("Creer", icon=ft.Icons.ADD_OUTLINED)
    cancel_edit_button = ft.OutlinedButton(
        "Annuler",
        icon=ft.Icons.CLOSE_OUTLINED,
        visible=False,
    )

    movement_item_field = ft.Dropdown(label="EPI", width=300)
    movement_type_field = ft.Dropdown(
        label="Mouvement",
        value="entree",
        width=150,
        options=[
            ft.dropdown.Option("entree", "Entree"),
            ft.dropdown.Option("sortie", "Sortie"),
            ft.dropdown.Option("ajustement", "Ajustement"),
        ],
    )
    movement_quantity_field = ft.TextField(label="Quantite", value="1", width=120)
    movement_motif_field = ft.TextField(label="Motif", width=220)
    movement_reference_field = ft.TextField(label="Reference", width=160)

    assignment_employee_field = ft.Dropdown(label="Employe", width=320)
    assignment_item_field = ft.Dropdown(label="EPI", width=300)
    assignment_quantity_field = ft.TextField(label="Quantite", value="1", width=120)
    assignment_date_field = ft.TextField(label="Date remise", value=today_iso(), width=160)
    assignment_observation_field = ft.TextField(label="Observation", width=260)

    requirement_function_field = ft.Dropdown(label="Fonction", width=260)
    requirement_type_field = ft.Dropdown(label="Type EPI requis", width=240)
    requirement_quantity_field = ft.TextField(label="Quantite", value="1", width=120)
    requirement_mandatory_field = ft.Checkbox(label="Obligatoire", value=True)

    inspection_item_field = ft.Dropdown(label="EPI inspecte", width=300)
    inspection_status_field = ft.Dropdown(
        label="Statut inspection",
        value="ok",
        width=170,
        options=[
            ft.dropdown.Option("ok", "OK"),
            ft.dropdown.Option("a_surveiller", "A surveiller"),
            ft.dropdown.Option("endommage", "Endommage"),
            ft.dropdown.Option("hors_service", "Hors service"),
        ],
    )
    inspection_date_field = ft.TextField(label="Date inspection", value=today_iso(), width=160)
    inspection_next_field = ft.TextField(label="Prochaine inspection", hint_text="AAAA-MM-JJ", width=180)
    inspection_inspector_field = ft.TextField(label="Inspecteur", width=160)
    inspection_observation_field = ft.TextField(label="Observation", width=260)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        refresh_options()
        render_summary()
        render_catalog()
        render_movements()
        render_assignments()
        render_requirements()
        render_inspections()
        render_alerts()
        _update()

    def refresh_options() -> None:
        options = get_ppe_options()
        type_field.options = [ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["types"]]
        item_options = [ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["items"]]
        movement_item_field.options = item_options
        assignment_item_field.options = item_options
        inspection_item_field.options = item_options
        requirement_type_field.options = [ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["types"]]
        requirement_function_field.options = [
            ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["functions"]
        ]
        assignment_employee_field.options = [
            ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["employees"]
        ]
        if type_field.options and not type_field.value:
            type_field.value = type_field.options[0].key
        if requirement_type_field.options and not requirement_type_field.value:
            requirement_type_field.value = requirement_type_field.options[0].key
        if requirement_function_field.options and not requirement_function_field.value:
            requirement_function_field.value = requirement_function_field.options[0].key
        if item_options:
            movement_item_field.value = movement_item_field.value or item_options[0].key
            assignment_item_field.value = assignment_item_field.value or item_options[0].key
            inspection_item_field.value = inspection_item_field.value or item_options[0].key
        if assignment_employee_field.options and not assignment_employee_field.value:
            assignment_employee_field.value = assignment_employee_field.options[0].key

    def reset_item_form() -> None:
        nonlocal selected_item_id
        selected_item_id = None
        item_name_field.value = ""
        size_field.value = ""
        standard_field.value = ""
        brand_field.value = ""
        model_field.value = ""
        expiry_field.value = ""
        initial_quantity_field.value = "0"
        initial_quantity_field.disabled = False
        threshold_field.value = "0"
        save_item_button.text = "Creer"
        save_item_button.icon = ft.Icons.ADD_OUTLINED
        cancel_edit_button.visible = False

    def save_item(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = {
                "type_epi_id": type_field.value,
                "nom": item_name_field.value,
                "taille": size_field.value,
                "norme": standard_field.value,
                "marque": brand_field.value,
                "modele": model_field.value,
                "etat": condition_field.value,
                "date_expiration": expiry_field.value,
                "quantite_initiale": initial_quantity_field.value,
                "seuil_minimum": threshold_field.value,
            }
            if selected_item_id is None:
                create_ppe_item(payload)
                notify("EPI cree avec stock initialise.", SUCCESS)
            else:
                update_ppe_item(selected_item_id, payload)
                notify("EPI modifie.", SUCCESS)
            reset_item_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_item(row: dict[str, Any]) -> None:
        nonlocal selected_item_id
        selected_item_id = int(row["id_epi"])
        type_field.value = str(row["type_epi_id"])
        item_name_field.value = str(row.get("nom") or "")
        size_field.value = str(row.get("taille") or "")
        standard_field.value = str(row.get("norme") or "")
        brand_field.value = str(row.get("marque") or "")
        model_field.value = str(row.get("modele") or "")
        condition_field.value = str(row.get("etat") or "neuf")
        expiry_field.value = str(row.get("date_expiration") or "")
        initial_quantity_field.value = str(row.get("quantite_disponible") or 0)
        initial_quantity_field.disabled = True
        threshold_field.value = str(row.get("seuil_minimum") or 0)
        save_item_button.text = "Enregistrer"
        save_item_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_edit_button.visible = True
        notify("Mode modification active.", PRIMARY)
        _update()

    def delete_item(item_id: int) -> None:
        confirm_action(
            page,
            "Supprimer ou desactiver l'EPI",
            "Le systeme supprimera l'EPI si possible, sinon il sera desactive pour conserver l'historique.",
            lambda: _delete_item(item_id),
            confirm_label="Continuer",
            danger=True,
        )

    def _delete_item(item_id: int) -> None:
        try:
            result = delete_ppe_item(item_id)
            reset_item_form()
            notify("EPI supprime." if result == "supprime" else "EPI desactive pour conserver l'historique.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_movement(event: ft.ControlEvent | None = None) -> None:
        try:
            record_stock_movement(
                {
                    "epi_id": movement_item_field.value,
                    "type_mouvement": movement_type_field.value,
                    "quantite": movement_quantity_field.value,
                    "motif": movement_motif_field.value,
                    "reference": movement_reference_field.value,
                }
            )
            notify("Mouvement de stock enregistre.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_assignment(event: ft.ControlEvent | None = None) -> None:
        try:
            assign_ppe(
                {
                    "employe_id": assignment_employee_field.value,
                    "epi_id": assignment_item_field.value,
                    "quantite": assignment_quantity_field.value,
                    "date_remise": assignment_date_field.value,
                    "observations": assignment_observation_field.value,
                }
            )
            notify("EPI affecte a l'employe.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def close_assignment(assignment_id: int, close_status: str) -> None:
        confirm_action(
            page,
            "Cloturer l'affectation EPI",
            "Cette affectation sera marquee comme retournee ou cloturee.",
            lambda: _close_assignment(assignment_id, close_status),
            confirm_label="Cloturer",
        )

    def _close_assignment(assignment_id: int, close_status: str) -> None:
        try:
            return_ppe_assignment(assignment_id, status=close_status)
            notify("Affectation cloturee.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_requirement(event: ft.ControlEvent | None = None) -> None:
        try:
            save_ppe_requirement(
                {
                    "fonction_id": requirement_function_field.value,
                    "type_epi_id": requirement_type_field.value,
                    "quantite": requirement_quantity_field.value,
                    "obligatoire": requirement_mandatory_field.value,
                }
            )
            notify("Dotation obligatoire mise a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def remove_requirement(requirement_id: int) -> None:
        confirm_action(
            page,
            "Supprimer la dotation obligatoire",
            "Cette regle de dotation EPI sera supprimee.",
            lambda: _remove_requirement(requirement_id),
            confirm_label="Supprimer",
            danger=True,
        )

    def _remove_requirement(requirement_id: int) -> None:
        try:
            delete_ppe_requirement(requirement_id)
            notify("Dotation obligatoire supprimee.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_inspection(event: ft.ControlEvent | None = None) -> None:
        try:
            record_ppe_inspection(
                {
                    "epi_id": inspection_item_field.value,
                    "date_inspection": inspection_date_field.value,
                    "statut": inspection_status_field.value,
                    "prochaine_inspection": inspection_next_field.value,
                    "inspecteur": inspection_inspector_field.value,
                    "observations": inspection_observation_field.value,
                }
            )
            inspection_observation_field.value = ""
            notify("Inspection EPI enregistree.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_inventory(event: ft.ControlEvent | None = None) -> None:
        output = export_ppe_inventory_xls()
        notify(f"Export Gestion des EPI cree: {output}", SUCCESS)
        _update()

    def render_summary() -> None:
        summary = get_ppe_summary()
        summary_row.controls = [
            _summary_chip("Articles", summary["items"], PRIMARY, ft.Icons.INVENTORY_2_OUTLINED),
            _summary_chip("Stock total", summary["stock_total"], SUCCESS, ft.Icons.WAREHOUSE_OUTLINED),
            _summary_chip("Affectes", summary["assigned"], PRIMARY, ft.Icons.ASSIGNMENT_IND_OUTLINED),
            _summary_chip("Stock bas", summary["low_stock"], DANGER if summary["low_stock"] else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
        ]

    def render_catalog() -> None:
        rows = list_ppe_items(search=str(search_field.value or ""))
        catalog_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"Catalogue EPI ({len(rows)})", size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Type")),
                            ft.DataColumn(ft.Text("EPI")),
                            ft.DataColumn(ft.Text("Taille")),
                            ft.DataColumn(ft.Text("Etat")),
                            ft.DataColumn(ft.Text("Stock")),
                            ft.DataColumn(ft.Text("Seuil")),
                            ft.DataColumn(ft.Text("Alerte")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(str(row.get("type_epi") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("nom") or "-"), weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row.get("taille") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("etat") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("quantite_disponible") or 0), color=SUCCESS if not row.get("stock_bas") else DANGER, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row.get("seuil_minimum") or 0))),
                                    ft.DataCell(_status_badge("Stock bas", DANGER) if row.get("stock_bas") else _status_badge("OK", SUCCESS)),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(
                                                    icon=ft.Icons.EDIT_OUTLINED,
                                                    tooltip="Modifier",
                                                    icon_color=PRIMARY,
                                                    on_click=lambda event, item=row: edit_item(item),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.DELETE_OUTLINE,
                                                    tooltip="Supprimer",
                                                    icon_color=DANGER,
                                                    on_click=lambda event, item_id=row["id_epi"]: delete_item(int(item_id)),
                                                ),
                                            ],
                                            spacing=0,
                                        )
                                    ),
                                ]
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

    def render_movements() -> None:
        rows = list_stock_movements()
        movement_area.controls = [
            ft.Text("Derniers mouvements", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{row['date_mouvement']} - {row['type_mouvement']} {row['quantite']} | {row['type_epi']} - {row['epi']} | {row.get('motif') or '-'}",
                        size=12,
                        color=MUTED,
                    )
                    for row in rows[:10]
                ],
                spacing=4,
            )
            if rows
            else ft.Text("Aucun mouvement de stock.", size=12, color=MUTED),
        ]

    def render_assignments() -> None:
        rows = list_ppe_assignments(active_only=True)
        assignment_area.controls = [
            ft.Text("Affectations en service", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"{row.get('nom') or '-'} {row.get('prenom') or ''} | {row['type_epi']} - {row['epi']} x{row['quantite']} | {row['date_remise']}",
                                size=12,
                                color=TEXT,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.KEYBOARD_RETURN_OUTLINED,
                                tooltip="Retour stock",
                                icon_color=SUCCESS,
                                on_click=lambda event, assignment_id=row["id_affectation"]: close_assignment(assignment_id, "retourne"),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.BLOCK_OUTLINED,
                                tooltip="Perdu",
                                icon_color=DANGER,
                                on_click=lambda event, assignment_id=row["id_affectation"]: close_assignment(assignment_id, "perdu"),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                    for row in rows[:12]
                ],
                spacing=4,
            )
            if rows
            else ft.Text("Aucune affectation en service.", size=12, color=MUTED),
        ]

    def render_requirements() -> None:
        rows = list_ppe_requirements()
        compliance = list_ppe_compliance()
        missing = [row for row in compliance if row.get("statut") == "manquant"]
        requirement_area.controls = [
            ft.Text("Dotation obligatoire par fonction", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"{row['fonction']} | {row['type_epi']} x{row['quantite']} | {'obligatoire' if row['obligatoire'] else 'optionnel'}",
                                size=12,
                                color=TEXT,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Supprimer exigence",
                                icon_color=DANGER,
                                on_click=lambda event, requirement_id=row["id_requis"]: remove_requirement(int(requirement_id)),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                    for row in rows
                ],
                spacing=4,
            )
            if rows
            else ft.Text("Aucune dotation obligatoire parametree.", size=12, color=MUTED),
        ]
        compliance_area.controls = [
            ft.Text(f"Conformite employees ({len(missing)} manquant)", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{row.get('nom') or '-'} {row.get('prenom') or ''} | {row['fonction']} | {row['type_epi']}: {row['affecte']}/{row['requis']} - {row['statut']}",
                        size=12,
                        color=DANGER if row.get("statut") == "manquant" else SUCCESS,
                    )
                    for row in compliance[:12]
                ],
                spacing=4,
            )
            if compliance
            else ft.Text("La conformite apparaitra apres parametrage des dotations.", size=12, color=MUTED),
        ]

    def render_inspections() -> None:
        rows = list_ppe_inspections()
        inspection_area.controls = [
            ft.Text("Dernieres inspections", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{row['date_inspection']} | {row['type_epi']} - {row['epi']} | {row['statut']} | prochaine: {row.get('prochaine_inspection') or '-'}",
                        size=12,
                        color=DANGER if row.get("statut") in ("endommage", "hors_service") else TEXT,
                    )
                    for row in rows[:10]
                ],
                spacing=4,
            )
            if rows
            else ft.Text("Aucune inspection enregistree.", size=12, color=MUTED),
        ]

    def render_alerts() -> None:
        rows = list_ppe_alerts()
        alert_area.controls = [
            ft.Text("Alertes stock", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{row.get('alerte') or 'Alerte'} | {row['type_epi']} - {row['nom']}: stock {row.get('quantite_disponible', '')} / seuil {row.get('seuil_minimum', '')}",
                        size=12,
                        color=DANGER,
                    )
                    for row in rows
                ],
                spacing=4,
            )
            if rows
            else ft.Text("Aucune alerte stock.", size=12, color=SUCCESS),
        ]

    root = ft.Column(
        controls=[
            module_header(
                "Gestion des EPI",
                "Catalogue drilling, stock, mouvements, dotations, retours et alertes.",
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
                                search_field,
                                ft.ElevatedButton("Actualiser", icon=ft.Icons.SYNC_OUTLINED, on_click=refresh),
                                ft.OutlinedButton("Exporter Excel", icon=ft.Icons.TABLE_CHART_OUTLINED, on_click=export_inventory),
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
                        ft.Text("Ameliorations recommandees", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.ResponsiveRow(
                            controls=[
                                _recommendation_card(
                                    "Dotation par fonction",
                                    "Verifier automatiquement les EPI obligatoires selon le poste drilling.",
                                    ft.Icons.FACT_CHECK_OUTLINED,
                                ),
                                _recommendation_card(
                                    "Expiration et inspections",
                                    "Suivre les dates de validite, controles periodiques et EPI endommages.",
                                    ft.Icons.EVENT_REPEAT_OUTLINED,
                                ),
                                _recommendation_card(
                                    "Export professionnel",
                                    "Produire une fiche de dotation et un inventaire signe au format Excel/PDF.",
                                    ft.Icons.FILE_DOWNLOAD_OUTLINED,
                                ),
                            ],
                            spacing=10,
                            run_spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        bgcolor="#FFFFFF",
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        padding=16,
                        col={"sm": 12, "lg": 6},
                        content=ft.Column(
                            controls=[
                                ft.Text("Parametrage dotation", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                                ft.Row(
                                    controls=[
                                        requirement_function_field,
                                        requirement_type_field,
                                        requirement_quantity_field,
                                        requirement_mandatory_field,
                                        ft.ElevatedButton("Enregistrer", icon=ft.Icons.FACT_CHECK_OUTLINED, on_click=save_requirement),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                ),
                                requirement_area,
                            ],
                            spacing=10,
                        ),
                    ),
                    ft.Container(
                        bgcolor="#FFFFFF",
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        padding=16,
                        col={"sm": 12, "lg": 6},
                        content=compliance_area,
                    ),
                ],
                spacing=14,
                run_spacing=14,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Inspection et suivi etat", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[
                                inspection_item_field,
                                inspection_status_field,
                                inspection_date_field,
                                inspection_next_field,
                                inspection_inspector_field,
                                inspection_observation_field,
                                ft.ElevatedButton("Enregistrer inspection", icon=ft.Icons.EVENT_REPEAT_OUTLINED, on_click=save_inspection),
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                        inspection_area,
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Nouvel EPI", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[
                                type_field,
                                item_name_field,
                                size_field,
                                standard_field,
                                brand_field,
                                model_field,
                                condition_field,
                                expiry_field,
                                initial_quantity_field,
                                threshold_field,
                                save_item_button,
                                cancel_edit_button,
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(bgcolor="#FFFFFF", border=ft.border.all(1, "#BFDBFE"), border_radius=8, padding=16, content=catalog_area),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        bgcolor="#FFFFFF",
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        padding=16,
                        col={"sm": 12, "lg": 6},
                        content=ft.Column(
                            controls=[
                                ft.Text("Mouvement stock", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                                ft.Row(
                                    controls=[
                                        movement_item_field,
                                        movement_type_field,
                                        movement_quantity_field,
                                        movement_motif_field,
                                        movement_reference_field,
                                        ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED, on_click=save_movement),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                ),
                                movement_area,
                            ],
                            spacing=10,
                        ),
                    ),
                    ft.Container(
                        bgcolor="#FFFFFF",
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        padding=16,
                        col={"sm": 12, "lg": 6},
                        content=ft.Column(
                            controls=[
                                ft.Text("Affectation employe", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                                ft.Row(
                                    controls=[
                                        assignment_employee_field,
                                        assignment_item_field,
                                        assignment_quantity_field,
                                        assignment_date_field,
                                        assignment_observation_field,
                                        ft.ElevatedButton("Affecter", icon=ft.Icons.ASSIGNMENT_IND_OUTLINED, on_click=save_assignment),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                ),
                                assignment_area,
                            ],
                            spacing=10,
                        ),
                    ),
                ],
                spacing=14,
                run_spacing=14,
            ),
            ft.Container(bgcolor="#FFFFFF", border=ft.border.all(1, "#BFDBFE"), border_radius=8, padding=16, content=alert_area),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    save_item_button.on_click = save_item
    cancel_edit_button.on_click = lambda event: (reset_item_form(), refresh())
    return root


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _status_badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color, weight=ft.FontWeight.BOLD),
    )


def _recommendation_card(title: str, description: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"sm": 12, "md": 4},
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=PRIMARY, size=20),
                ft.Column(
                    controls=[
                        ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(description, size=12, color=MUTED),
                    ],
                    spacing=3,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )
