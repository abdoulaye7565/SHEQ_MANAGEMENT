from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    create_training,
    create_training_department,
    create_training_type,
    create_trainings_for_employees,
    delete_training,
    export_styled_rows_xlsx,
    get_training_options,
    list_trainings,
    today_iso,
    update_training,
    update_trainings_bulk,
)
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def training_page() -> ft.Control:
    options = get_training_options()
    state: dict[str, Any] = {
        "records": [],
        "editing_id": None,
        "selected": set(),
        "bulk_employee_ids": set(),
        "bulk_training_type_ids": set(),
        "options": options,
    }
    status = ft.Text("", size=12, color=MUTED)
    table_area = ft.Column(spacing=10)
    summary_row = ft.Row(spacing=8, wrap=True)

    employee_field = ft.Dropdown(label="Employe", width=360)
    training_field = ft.Dropdown(label="Nom de la formation", width=280)
    department_field = ft.Dropdown(label="Departement", width=240)
    facilitator_field = ft.TextField(label="Facilitateur", width=240)
    date_field = ft.TextField(label="Date de formation", value=today_iso(), hint_text="AAAA-MM-JJ", width=180)
    new_training_field = ft.TextField(label="Nouvelle formation", width=260)
    new_department_field = ft.TextField(label="Nouveau departement", width=260)
    bulk_employee_area = ft.Column(spacing=6)
    bulk_training_area = ft.Column(spacing=6)

    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=260)
    state_filter = ft.Dropdown(
        label="Etat",
        value="all",
        width=180,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("valide", "Valides"),
            ft.dropdown.Option("bientot_expiree", "Bientot expirees"),
            ft.dropdown.Option("expiree", "Expirees"),
        ],
    )
    training_filter = ft.Dropdown(label="Formation", value="all", width=220)
    department_filter = ft.Dropdown(label="Departement", value="all", width=220)
    date_from_filter = ft.TextField(label="Du", hint_text="AAAA-MM-JJ", width=150)
    date_to_filter = ft.TextField(label="Au", hint_text="AAAA-MM-JJ", width=150)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def load_options() -> None:
        fresh = get_training_options()
        state["options"] = fresh
        employee_field.options = [ft.dropdown.Option(str(item["value"]), str(item["label"])) for item in fresh["employees"]]
        training_field.options = [
            ft.dropdown.Option(str(item["value"]), f"{item['label']} - {item.get('department') or 'Sans departement'}")
            for item in fresh["training_types"]
        ]
        department_field.options = [ft.dropdown.Option(str(item["value"]), str(item["label"])) for item in fresh["departments"]]
        employee_field.value = employee_field.value or (str(fresh["employees"][0]["value"]) if fresh["employees"] else None)
        training_field.value = training_field.value or (str(fresh["training_types"][0]["value"]) if fresh["training_types"] else None)
        department_field.value = department_field.value or (fresh["departments"][0]["value"] if fresh["departments"] else None)
        sync_department_from_training()
        state["bulk_employee_ids"] = state["bulk_employee_ids"] & {int(item["value"]) for item in fresh["employees"]}
        state["bulk_training_type_ids"] = state["bulk_training_type_ids"] & {int(item["value"]) for item in fresh["training_types"]}
        render_bulk_selection()

    def sync_department_from_training(event: ft.ControlEvent | None = None) -> None:
        selected = int(training_field.value or 0)
        for item in state.get("options", {}).get("training_types", []):
            if int(item["value"]) == selected and item.get("department"):
                department_field.value = str(item["department"])
                break
        if event is not None:
            _update()

    training_field.on_change = sync_department_from_training

    def refresh(event: ft.ControlEvent | None = None) -> None:
        state["records"] = list_trainings(search_field.value or "")
        current_ids = {int(record["id_formation"]) for record in state["records"]}
        state["selected"] = state["selected"] & current_ids
        refresh_filter_options()
        render_summary()
        render_table()
        _update()

    def refresh_filter_options() -> None:
        trainings = sorted({str(row.get("formation") or "-") for row in state["records"]})
        departments = sorted({str(row.get("training_department") or row.get("structure_responsable") or "-") for row in state["records"]})
        current_training = training_filter.value
        current_department = department_filter.value
        training_filter.options = [ft.dropdown.Option("all", "Toutes les formations")]
        training_filter.options.extend(ft.dropdown.Option(item, item) for item in trainings)
        department_filter.options = [ft.dropdown.Option("all", "Tous les departements")]
        department_filter.options.extend(ft.dropdown.Option(item, item) for item in departments)
        training_filter.value = current_training if current_training in {"all", *trainings} else "all"
        department_filter.value = current_department if current_department in {"all", *departments} else "all"

    def filtered_records() -> list[dict[str, Any]]:
        selected_state = str(state_filter.value or "all")
        selected_training = str(training_filter.value or "all")
        selected_department = str(department_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for record in state["records"]:
            if selected_state != "all" and record.get("etat") != selected_state:
                continue
            if selected_training != "all" and str(record.get("formation") or "-") != selected_training:
                continue
            record_department = str(record.get("training_department") or record.get("structure_responsable") or "-")
            if selected_department != "all" and record_department != selected_department:
                continue
            training_date = str(record.get("date_formation") or "")
            if date_from_filter.value and training_date < date_from_filter.value.strip():
                continue
            if date_to_filter.value and training_date > date_to_filter.value.strip():
                continue
            rows.append(record)
        return rows

    def clear_form(event: ft.ControlEvent | None = None) -> None:
        state["editing_id"] = None
        state["selected"].clear()
        date_field.value = today_iso()
        facilitator_field.value = ""
        department_field.value = department_field.options[0].key if department_field.options else None
        notify("Formulaire pret pour une nouvelle formation.", MUTED)
        render_form_actions()
        _update()

    def save(event: ft.ControlEvent | None = None) -> None:
        values = {
            "employe_id": employee_field.value,
            "type_training_id": training_field.value,
            "date_formation": date_field.value,
            "facilitateur": facilitator_field.value,
            "structure_responsable": department_field.value,
        }
        try:
            if state["editing_id"] is None:
                create_training(values)
                notify("Formation enregistree ou reconduite si elle existait deja.", SUCCESS)
            else:
                update_training(int(state["editing_id"]), values)
                notify("Formation mise a jour.", SUCCESS)
                state["editing_id"] = None
            refresh()
            render_form_actions()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def selected_ids() -> list[int]:
        return sorted(int(item) for item in state["selected"])

    def toggle_selected(training_id: int, selected: bool) -> None:
        if selected:
            state["selected"].add(training_id)
        else:
            state["selected"].discard(training_id)
        render_form_actions()
        render_summary()
        render_table()
        _update()

    def select_visible(selected: bool) -> None:
        visible_ids = {int(record["id_formation"]) for record in filtered_records()}
        if selected:
            state["selected"].update(visible_ids)
        else:
            state["selected"].difference_update(visible_ids)
        render_form_actions()
        render_summary()
        render_table()
        _update()

    def bulk_update(event: ft.ControlEvent | None = None) -> None:
        try:
            updated = update_trainings_bulk(
                selected_ids(),
                {
                    "type_training_id": training_field.value,
                    "date_formation": date_field.value,
                    "facilitateur": facilitator_field.value,
                    "structure_responsable": department_field.value,
                },
            )
            state["selected"].clear()
            state["editing_id"] = None
            notify(f"{updated} formation(s) mise(s) a jour.", SUCCESS)
            refresh()
            render_form_actions()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def bulk_validate_training(event: ft.ControlEvent | None = None) -> None:
        try:
            total = create_trainings_for_employees(
                {
                    "employee_ids": sorted(state["bulk_employee_ids"]),
                    "training_type_ids": sorted(state["bulk_training_type_ids"]),
                    "date_formation": date_field.value,
                    "facilitateur": facilitator_field.value,
                    "structure_responsable": department_field.value,
                }
            )
            notify(f"{total} validation(s) formation creee(s) ou mise(s) a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def toggle_bulk_employee(employee_id: int, selected: bool) -> None:
        if selected:
            state["bulk_employee_ids"].add(employee_id)
        else:
            state["bulk_employee_ids"].discard(employee_id)
        render_bulk_selection()
        render_form_actions()
        _update()

    def toggle_bulk_training(training_type_id: int, selected: bool) -> None:
        if selected:
            state["bulk_training_type_ids"].add(training_type_id)
        else:
            state["bulk_training_type_ids"].discard(training_type_id)
        render_bulk_selection()
        render_form_actions()
        _update()

    def select_bulk_employees(selected: bool) -> None:
        employees = state.get("options", {}).get("employees", [])
        state["bulk_employee_ids"] = {int(item["value"]) for item in employees} if selected else set()
        render_bulk_selection()
        render_form_actions()
        _update()

    def select_bulk_trainings(selected: bool) -> None:
        training_types = state.get("options", {}).get("training_types", [])
        state["bulk_training_type_ids"] = {int(item["value"]) for item in training_types} if selected else set()
        render_bulk_selection()
        render_form_actions()
        _update()

    def edit_record(record: dict[str, Any]) -> None:
        state["editing_id"] = int(record["id_formation"])
        employee_field.value = str(record["employe_id"])
        training_field.value = str(record["type_training_id"])
        date_field.value = str(record["date_formation"] or "")
        facilitator_field.value = str(record["facilitateur"] or "")
        department_field.value = str(record["structure_responsable"] or "")
        notify("Formation chargee pour modification.", PRIMARY)
        render_form_actions()
        _update()

    def renew_record(record: dict[str, Any]) -> None:
        state["editing_id"] = None
        employee_field.value = str(record["employe_id"])
        training_field.value = str(record["type_training_id"])
        date_field.value = today_iso()
        facilitator_field.value = str(record["facilitateur"] or "")
        department_field.value = str(record["structure_responsable"] or "")
        notify("Nouvelle mise a jour preparee. L'historique sera conserve.", PRIMARY)
        render_form_actions()
        _update()

    def remove(training_id: int) -> None:
        delete_training(training_id)
        notify("Formation supprimee.", MUTED)
        if state["editing_id"] == training_id:
            state["editing_id"] = None
        refresh()

    def add_training_type(event: ft.ControlEvent | None = None) -> None:
        try:
            created_id = create_training_type(new_training_field.value, department_field.value)
            load_options()
            training_field.value = str(created_id)
            sync_department_from_training()
            new_training_field.value = ""
            notify("Nom de formation cree et selectionne.", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def add_department(event: ft.ControlEvent | None = None) -> None:
        try:
            created_name = create_training_department(new_department_field.value)
            load_options()
            department_field.value = created_name
            new_department_field.value = ""
            notify("Departement cree et selectionne.", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def render_bulk_selection() -> None:
        fresh = state.get("options", {})
        employees = fresh.get("employees", [])
        training_types = fresh.get("training_types", [])
        selected_employees = set(state["bulk_employee_ids"])
        selected_trainings = set(state["bulk_training_type_ids"])
        bulk_employee_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"{len(selected_employees)} employe(s) selectionne(s)", color=MUTED, size=12, expand=True),
                    ft.OutlinedButton("Tous", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=lambda event: select_bulk_employees(True)),
                    ft.OutlinedButton("Aucun", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=lambda event: select_bulk_employees(False)),
                ],
                wrap=True,
                spacing=8,
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        width=280,
                        content=ft.Checkbox(
                            label=str(item["label"]),
                            value=int(item["value"]) in selected_employees,
                            on_change=lambda event, current=item: toggle_bulk_employee(
                                int(current["value"]),
                                bool(event.control.value),
                            ),
                        ),
                    )
                    for item in employees
                ],
                wrap=True,
                spacing=4,
            )
            if employees
            else ft.Text("Aucun employe actif disponible.", color=MUTED, size=12),
        ]
        bulk_training_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"{len(selected_trainings)} formation(s) selectionnee(s)", color=MUTED, size=12, expand=True),
                    ft.OutlinedButton("Toutes", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=lambda event: select_bulk_trainings(True)),
                    ft.OutlinedButton("Aucune", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=lambda event: select_bulk_trainings(False)),
                ],
                wrap=True,
                spacing=8,
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        width=260,
                        content=ft.Checkbox(
                            label=f"{item['label']} - {item.get('department') or 'Sans departement'}",
                            value=int(item["value"]) in selected_trainings,
                            on_change=lambda event, current=item: toggle_bulk_training(
                                int(current["value"]),
                                bool(event.control.value),
                            ),
                        ),
                    )
                    for item in training_types
                ],
                wrap=True,
                spacing=4,
            )
            if training_types
            else ft.Text("Aucun type de formation disponible.", color=MUTED, size=12),
        ]

    def export_list(event: ft.ControlEvent | None = None) -> None:
        records = filtered_records()
        rows = [
            [
                f"{record.get('nom') or '-'} {record.get('prenom') or ''}".strip(),
                record.get("numero_badge") or "",
                record.get("fonction") or "",
                record.get("formation") or "",
                record.get("date_formation") or "",
                record.get("date_expiration") or "",
                record.get("facilitateur") or "",
                record.get("training_department") or record.get("structure_responsable") or "",
                _state_text(record.get("etat")),
            ]
            for record in records
        ]
        styles = [[None, None, None, None, None, None, None, None, _excel_state(record.get("etat"))] for record in records]
        rows.extend(
            [
                ["", "", "", "", "", "", "", "", ""],
                ["Legende", "Bleu", "Formation faite / valide", "", "", "", "", "", ""],
                ["Legende", "Jaune", "Formation bientot expiree", "", "", "", "", "", ""],
                ["Legende", "Rouge", "Formation non faite ou expiree", "", "", "", "", "", ""],
            ]
        )
        styles.extend(
            [
                [None] * 9,
                [None, "done", None, None, None, None, None, None, None],
                [None, "soon", None, None, None, None, None, None, None],
                [None, "expired", None, None, None, None, None, None, None],
            ]
        )
        output = export_styled_rows_xlsx(
            "liste_formations.xlsx",
            "Formations",
            ["Employe", "Badge", "Fonction", "Formation", "Date formation", "Expiration", "Facilitateur", "Departement", "Etat"],
            rows,
            styles,
        )
        notify(f"Export Excel cree: {output}", SUCCESS)
        _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        state_filter.value = "all"
        training_filter.value = "all"
        department_filter.value = "all"
        date_from_filter.value = ""
        date_to_filter.value = ""
        refresh()

    form_actions = ft.Row(spacing=10, wrap=True)

    def render_form_actions() -> None:
        selected_count = len(state["selected"])
        bulk_ready = bool(state["bulk_employee_ids"]) and bool(state["bulk_training_type_ids"])
        form_actions.controls = [
            ft.ElevatedButton(
                "Mettre a jour" if state["editing_id"] else "Enregistrer",
                icon=ft.Icons.SAVE_OUTLINED,
                on_click=save,
            ),
            ft.OutlinedButton(
                f"Maj selection ({selected_count})",
                icon=ft.Icons.DONE_ALL_OUTLINED,
                on_click=bulk_update,
                disabled=selected_count == 0,
            ),
            ft.ElevatedButton(
                "Valider groupe",
                icon=ft.Icons.DONE_ALL_OUTLINED,
                on_click=bulk_validate_training,
                disabled=not bulk_ready,
            ),
            ft.OutlinedButton("Nouveau", icon=ft.Icons.ADD_OUTLINED, on_click=clear_form),
            ft.Text(
                "Expiration automatique selon la validite du type de formation.",
                size=12,
                color=MUTED,
            ),
        ]

    def render_summary() -> None:
        records = filtered_records()
        summary_row.controls = [
            _summary_chip("Affichees", len(records), PRIMARY, ft.Icons.FILTER_ALT_OUTLINED),
            _summary_chip("Selection", len(state["selected"]), SUCCESS, ft.Icons.CHECKLIST_OUTLINED),
            _summary_chip("Valides", sum(1 for row in records if row.get("etat") == "valide"), PRIMARY, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _summary_chip("Bientot", sum(1 for row in records if row.get("etat") == "bientot_expiree"), WARNING, ft.Icons.SCHEDULE_OUTLINED),
            _summary_chip("Expirees", sum(1 for row in records if row.get("etat") == "expiree"), DANGER, ft.Icons.CANCEL_OUTLINED),
        ]

    def render_table() -> None:
        records = filtered_records()
        table_area.controls = [
            ft.Row(
                controls=[
                    search_field,
                    state_filter,
                    training_filter,
                    department_filter,
                    date_from_filter,
                    date_to_filter,
                    ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Appliquer", on_click=refresh),
                    ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_filters),
                    ft.OutlinedButton("Tout selectionner", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=lambda event: select_visible(True)),
                    ft.OutlinedButton("Deselectionner", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=lambda event: select_visible(False)),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_list),
                    status,
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            summary_row,
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("")),
                            ft.DataColumn(ft.Text("Employe")),
                            ft.DataColumn(ft.Text("Badge")),
                            ft.DataColumn(ft.Text("Formation")),
                            ft.DataColumn(ft.Text("Date")),
                            ft.DataColumn(ft.Text("Expiration")),
                            ft.DataColumn(ft.Text("Facilitateur")),
                            ft.DataColumn(ft.Text("Departement")),
                            ft.DataColumn(ft.Text("Etat")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                selected=record["id_formation"] == state["editing_id"],
                                cells=[
                                    ft.DataCell(
                                        ft.Checkbox(
                                            value=int(record["id_formation"]) in state["selected"],
                                            on_change=lambda event, current=record: toggle_selected(
                                                int(current["id_formation"]),
                                                bool(event.control.value),
                                            ),
                                        )
                                    ),
                                    ft.DataCell(ft.Text(f"{record.get('nom') or '-'} {record.get('prenom') or ''}")),
                                    ft.DataCell(ft.Text(str(record.get("numero_badge") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("formation") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("date_formation") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("date_expiration") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("facilitateur") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("training_department") or record.get("structure_responsable") or "-"))),
                                    ft.DataCell(_state_badge(record.get("etat"))),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(
                                                    icon=ft.Icons.EDIT_OUTLINED,
                                                    tooltip="Modifier cette ligne",
                                                    icon_color=PRIMARY,
                                                    on_click=lambda event, current=record: edit_record(current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.ADD_OUTLINED,
                                                    tooltip="Renouveler sans perdre l'historique",
                                                    icon_color=SUCCESS,
                                                    on_click=lambda event, current=record: renew_record(current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.DELETE_OUTLINE,
                                                    tooltip="Supprimer",
                                                    icon_color=DANGER,
                                                    on_click=lambda event, current=record: remove(int(current["id_formation"])),
                                                ),
                                            ],
                                            spacing=0,
                                        )
                                    ),
                                ]
                            )
                            for record in records
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    load_options()
    render_form_actions()

    root = ft.Column(
        controls=[
            module_header("Formations", "Enregistrer, corriger et suivre les formations employees."),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(controls=[employee_field, training_field, date_field, facilitator_field, department_field], wrap=True, spacing=10),
                        ft.Row(
                            controls=[
                                new_training_field,
                                ft.OutlinedButton("Creer formation", icon=ft.Icons.ADD_OUTLINED, on_click=add_training_type),
                                new_department_field,
                                ft.OutlinedButton("Creer departement", icon=ft.Icons.ADD_BUSINESS_OUTLINED, on_click=add_department),
                            ],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        form_actions,
                        ft.ExpansionTile(
                            title="Validation groupee: plusieurs employes et plusieurs formations",
                            leading=ft.Icons.PEOPLE_ALT_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[
                                ft.Text(
                                    "Selectionne les employes, les formations, puis clique sur Valider groupe.",
                                    color=MUTED,
                                    size=12,
                                ),
                                ft.Text("Employes", color=TEXT, weight=ft.FontWeight.BOLD),
                                bulk_employee_area,
                                ft.Text("Formations", color=TEXT, weight=ft.FontWeight.BOLD),
                                bulk_training_area,
                            ],
                        ),
                    ],
                    spacing=12,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=table_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    refresh()
    return root


def _state_badge(state: str | None) -> ft.Control:
    color = {"valide": PRIMARY, "bientot_expiree": WARNING, "expiree": DANGER}.get(str(state), MUTED)
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(_state_text(state), size=12, color=color),
    )


def _summary_chip(label: str, value: int, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=15),
                ft.Text(label, color=MUTED, size=11),
                ft.Text(str(value), color=TEXT, size=12, weight=ft.FontWeight.BOLD),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _state_text(state: str | None) -> str:
    return {
        "valide": "Faite",
        "bientot_expiree": "Bientot expiree",
        "expiree": "Non faite / expiree",
    }.get(str(state), "-")


def _excel_state(state: str | None) -> str:
    return {"valide": "done", "bientot_expiree": "soon", "expiree": "expired"}.get(str(state), "expired")

