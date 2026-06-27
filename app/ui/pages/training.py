from __future__ import annotations

import getpass
import socket
from typing import Any

import flet as ft

from app.services.lock_service import acquire_lock, get_lock_info, release_lock

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
from app.ui.components.confirm import confirm_action
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


PAGE_SIZE = 10
from app.ui.components.dark_styles import BG, CARD, DARK_BORDER, DARK_MUTED, DARK_TEXT, FIELD


def training_page(page: ft.Page | None = None) -> ft.Control:
    options = get_training_options()
    state: dict[str, Any] = {
        "records": [],
        "editing_id": None,
        "selected": set(),
        "bulk_employee_ids": set(),
        "bulk_training_type_ids": set(),
        "options": options,
        "page": 0,
    }
    status = ft.Text("", size=12, color=MUTED)
    table_area = ft.Column(spacing=10)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)

    employee_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Employe", width=360)
    training_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Nom de la formation", width=280)
    department_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Departement", width=240)
    facilitator_field = ft.TextField(label="Facilitateur", width=240)
    date_field = ft.TextField(label="Date de formation", value=today_iso(), hint_text="AAAA-MM-JJ", width=180)
    new_training_field = ft.TextField(label="Nouvelle formation", width=260)
    new_department_field = ft.TextField(label="Nouveau departement", width=260)
    bulk_employee_area = ft.Column(spacing=6)
    bulk_training_area = ft.Column(spacing=6)
    bulk_preview_area = ft.Container()
    employee_info = ft.Text("", size=10, color=DARK_MUTED)
    expiration_preview = ft.Text("", size=10, color=SUCCESS)

    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=260)
    state_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
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
    training_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Formation", value="all", width=220)
    department_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Departement", value="all", width=220)
    date_from_filter = ft.TextField(label="Du", hint_text="AAAA-MM-JJ", width=150)
    date_to_filter = ft.TextField(label="Au", hint_text="AAAA-MM-JJ", width=150)
    _style_dark_inputs(
        employee_field,
        training_field,
        department_field,
        facilitator_field,
        date_field,
        new_training_field,
        new_department_field,
        search_field,
        state_filter,
        training_filter,
        department_filter,
        date_from_filter,
        date_to_filter,
    )

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
                validity = int(item.get("validite_mois") or 0)
                expiration_preview.value = (
                    f"Expiration calculee automatiquement: date formation + {validity} mois."
                )
                break
        if event is not None:
            _update()

    def sync_employee_info(event: ft.ControlEvent | None = None) -> None:
        selected = int(employee_field.value or 0)
        for item in state.get("options", {}).get("employees", []):
            if int(item["value"]) == selected:
                employee_info.value = (
                    f"Fonction: {item.get('fonction') or '-'} | "
                    f"Site: {item.get('site') or '-'} | "
                    f"Badge: {item.get('numero_badge') or 'sans badge'}"
                )
                break
        if event is not None:
            _update()

    training_field.on_select = sync_department_from_training
    employee_field.on_select = sync_employee_info

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            state["page"] = 0
            state["records"] = list_trainings(search_field.value or "")
            current_ids = {int(record["id_formation"]) for record in state["records"]}
            state["selected"] = state["selected"] & current_ids
            refresh_filter_options()
            render_summary()
            render_table()
        except Exception as exc:
            notify(str(exc), DANGER)
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
        if state["editing_id"] is not None:
            release_lock("formations", str(state["editing_id"]), getpass.getuser())
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
                release_lock("formations", str(state["editing_id"]), getpass.getuser())
                state["editing_id"] = None
            refresh()
            render_form_actions()
        except Exception as exc:
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

    def change_page(delta: int) -> None:
        records = filtered_records()
        max_page = max((len(records) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"]) + delta))
        render_table()
        _update()

    def bulk_update(event: ft.ControlEvent | None = None) -> None:
        count = len(selected_ids())
        confirm_action(
            page,
            "Modifier plusieurs formations",
            f"{count} formation(s) selectionnee(s) seront mises a jour avec les valeurs du formulaire.",
            _bulk_update,
            confirm_label="Mettre a jour",
            danger=count > 5,
        )

    def _bulk_update() -> None:
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
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def bulk_validate_training(event: ft.ControlEvent | None = None) -> None:
        employees_count = len(state["bulk_employee_ids"])
        trainings_count = len(state["bulk_training_type_ids"])
        confirm_action(
            page,
            "Valider des formations en groupe",
            f"{employees_count} employe(s) x {trainings_count} formation(s) seront valides ou mis a jour.",
            _bulk_validate_training,
            confirm_label="Valider le groupe",
            danger=employees_count * trainings_count > 10,
        )

    def _bulk_validate_training() -> None:
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
            employees_count = len(state["bulk_employee_ids"])
            trainings_count = len(state["bulk_training_type_ids"])
            state["bulk_employee_ids"].clear()
            state["bulk_training_type_ids"].clear()
            notify(
                f"Campagne terminee: {employees_count} employe(s), "
                f"{trainings_count} formation(s), {total} mise(s) a jour.",
                SUCCESS,
            )
            refresh()
        except Exception as exc:
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
        record_id = str(record["id_formation"])
        current_user = getpass.getuser()
        if not acquire_lock("formations", record_id, current_user, socket.gethostname()):
            lock_info = get_lock_info("formations", record_id)
            if lock_info:
                msg = (
                    f"Fiche en cours de modification par {lock_info['utilisateur']}"
                    f" depuis {lock_info['verrouille_depuis']}"
                )
            else:
                msg = "Fiche verrouilee par un autre utilisateur."
            if page is not None:
                page.show_snack_bar(ft.SnackBar(ft.Text(msg), bgcolor=DANGER))
                page.update()
            else:
                notify(msg, DANGER)
                _update()
            return
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
        confirm_action(
            page,
            "Supprimer la formation",
            "Cette ligne de formation sera supprimee definitivement de la base locale.",
            lambda: _remove(training_id),
            confirm_label="Supprimer",
            danger=True,
        )

    def _remove(training_id: int) -> None:
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
            sync_employee_info()
            new_training_field.value = ""
            notify("Nom de formation cree et selectionne.", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def add_department(event: ft.ControlEvent | None = None) -> None:
        try:
            created_name = create_training_department(new_department_field.value)
            load_options()
            department_field.value = created_name
            new_department_field.value = ""
            notify("Departement cree et selectionne.", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def render_bulk_selection() -> None:
        fresh = state.get("options", {})
        employees = fresh.get("employees", [])
        training_types = fresh.get("training_types", [])
        selected_employees = set(state["bulk_employee_ids"])
        selected_trainings = set(state["bulk_training_type_ids"])
        operation_count = len(selected_employees) * len(selected_trainings)
        bulk_preview_area.content = ft.ResponsiveRow(
            controls=[
                ft.Container(
                    _bulk_metric("Employes selectionnes", len(selected_employees), PRIMARY, ft.Icons.GROUPS_OUTLINED),
                    col={"xs": 12, "sm": 4},
                ),
                ft.Container(
                    _bulk_metric("Formations selectionnees", len(selected_trainings), WARNING, ft.Icons.SCHOOL_OUTLINED),
                    col={"xs": 12, "sm": 4},
                ),
                ft.Container(
                    _bulk_metric("Mises a jour prevues", operation_count, SUCCESS, ft.Icons.DONE_ALL_OUTLINED),
                    col={"xs": 12, "sm": 4},
                ),
            ],
            spacing=8,
            run_spacing=8,
        )
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
        max_page = max((len(records) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"])))
        start = int(state["page"]) * PAGE_SIZE
        page_records = records[start : start + PAGE_SIZE]
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
                    ft.Text(
                        f"{start + 1 if records else 0}-{start + len(page_records)} / {len(records)} formation(s)",
                        size=12,
                        color=MUTED,
                    ),
                    ft.OutlinedButton(
                        "Precedent",
                        icon=ft.Icons.ARROW_BACK,
                        disabled=int(state["page"]) <= 0,
                        on_click=lambda event: change_page(-1),
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=6),
                        bgcolor="#EFF6FF",
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        content=ft.Text(f"Page {int(state['page']) + 1}/{max_page + 1}", size=12, color=TEXT),
                    ),
                    ft.OutlinedButton(
                        "Suivant",
                        icon=ft.Icons.ARROW_FORWARD,
                        disabled=int(state["page"]) >= max_page,
                        on_click=lambda event: change_page(1),
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
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
                            for record in page_records
                        ],
                        bgcolor=FIELD,
                        border=ft.border.all(1, DARK_BORDER),
                        border_radius=8,
                        heading_row_color=CARD,
                        horizontal_lines=ft.BorderSide(1, DARK_BORDER),
                        vertical_lines=ft.BorderSide(1, DARK_BORDER),
                        heading_text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color="#60A5FA"),
                        data_text_style=ft.TextStyle(size=12, color=DARK_TEXT),
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    load_options()
    render_form_actions()

    root = ft.Column(
        controls=[
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, DARK_BORDER),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Enregistrer une formation", color=DARK_TEXT, size=14, weight=ft.FontWeight.BOLD),
                        ft.Row(controls=[employee_field, training_field, date_field, facilitator_field, department_field], wrap=True, spacing=10),
                        ft.Row([employee_info, expiration_preview], wrap=True, spacing=16),
                        form_actions,
                        ft.ExpansionTile(
                            title="Options avancees",
                            subtitle="Creer de nouveaux types de formation ou departements.",
                            leading=ft.Icons.TUNE_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[
                                ft.Row(
                                    controls=[
                                        new_training_field,
                                        ft.OutlinedButton("Creer formation", icon=ft.Icons.ADD_OUTLINED, on_click=add_training_type),
                                        new_department_field,
                                        ft.OutlinedButton("Creer departement", icon=ft.Icons.ADD_BUSINESS_OUTLINED, on_click=add_department),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                ),
                            ],
                            expanded=False,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, DARK_BORDER),
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
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _state_badge(state: str | None) -> ft.Control:
    color = {"valide": PRIMARY, "bientot_expiree": WARNING, "expiree": DANGER}.get(str(state), MUTED)
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(_state_text(state), size=12, color=color),
    )


def _summary_chip(label: str, value: int, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=10,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=36,
                    height=36,
                    bgcolor=f"{color}30",
                    border_radius=7,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=color, size=19),
                ),
                ft.Column(
                    controls=[
                        ft.Text(label, size=10, color=DARK_MUTED),
                        ft.Text(str(value), size=20, color=DARK_TEXT, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=1,
                ),
            ],
            spacing=9,
        ),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _style_dark_inputs(*controls: ft.Control) -> None:
    for control in controls:
        control.bgcolor = FIELD
        control.color = DARK_TEXT
        control.border_color = DARK_BORDER
        control.focused_border_color = PRIMARY
        control.label_style = ft.TextStyle(color=DARK_MUTED)
        control.hint_style = ft.TextStyle(color="#6F849A")


def _bulk_metric(label: str, value: int, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=7,
        padding=10,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=20),
                ft.Column(
                    controls=[
                        ft.Text(label, color=DARK_MUTED, size=10),
                        ft.Text(str(value), color=DARK_TEXT, size=18, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=1,
                ),
            ],
            spacing=8,
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
