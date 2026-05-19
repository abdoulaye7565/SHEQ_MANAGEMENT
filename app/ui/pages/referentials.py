from __future__ import annotations

from typing import Any

import flet as ft

from app.services import (
    create_record,
    delete_record,
    export_rows_xlsx,
    get_config,
    get_foreign_key_options,
    list_config_keys,
    list_records,
    update_record,
)
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT


def referentials_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"key": "sites", "selected_id": None}
    form_controls: dict[str, ft.Control] = {}
    category_area = ft.Column(spacing=6)
    form_area = ft.Column(spacing=14)
    table_area = ft.Column(spacing=12)
    title = ft.Text(size=18, weight=ft.FontWeight.BOLD, color=TEXT)
    status = ft.Text("", size=12, color=MUTED)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def selected_config() -> dict[str, Any]:
        return get_config(state["key"])

    def select_category(key: str) -> None:
        state["key"] = key
        state["selected_id"] = None
        notify("")
        render_all()

    def clear_form(event: ft.ControlEvent | None = None) -> None:
        state["selected_id"] = None
        render_form()
        notify("Nouveau formulaire pret.", MUTED)
        root.update()

    def collect_values() -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field in selected_config()["fields"]:
            control = form_controls[field["name"]]
            if field["type"] == "bool":
                values[field["name"]] = control.value
            else:
                values[field["name"]] = control.value
        return values

    def save_record(event: ft.ControlEvent) -> None:
        try:
            values = collect_values()
            if state["selected_id"] is None:
                created_id = create_record(state["key"], values)
                state["selected_id"] = created_id
                notify("Element cree avec succes.", SUCCESS)
            else:
                update_record(state["key"], int(state["selected_id"]), values)
                notify("Element mis a jour.", SUCCESS)
            render_form()
            render_table()
        except ValueError as exc:
            notify(str(exc), DANGER)
        root.update()

    def remove_record(record_id: int | None = None) -> None:
        target_id = record_id or state["selected_id"]
        if target_id is None:
            notify("Selectionne d'abord un element a supprimer.", DANGER)
            root.update()
            return

        try:
            delete_record(state["key"], int(target_id))
            state["selected_id"] = None
            notify("Element supprime.", SUCCESS)
            render_form()
            render_table()
        except ValueError as exc:
            notify(str(exc), DANGER)
        root.update()

    def confirm_delete(record_id: int | None = None) -> None:
        if page is None:
            remove_record(record_id)
            return

        target_id = record_id or state["selected_id"]
        if target_id is None:
            notify("Selectionne d'abord un element a supprimer.", DANGER)
            root.update()
            return

        def close_dialog(event: ft.ControlEvent | None = None) -> None:
            page.pop_dialog()
            page.update()

        def confirm(event: ft.ControlEvent) -> None:
            close_dialog()
            remove_record(int(target_id))

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmer la suppression"),
                content=ft.Text(
                    "Cette action supprimera l'element selectionne si aucune autre donnee ne l'utilise."
                ),
                actions=[
                    ft.TextButton("Annuler", on_click=close_dialog),
                    ft.TextButton("Supprimer", icon=ft.Icons.DELETE_OUTLINE, on_click=confirm),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def select_record(record: dict[str, Any]) -> None:
        config = selected_config()
        state["selected_id"] = record[config["pk"]]
        render_form(record)
        notify("Element charge pour modification.", PRIMARY)
        root.update()

    def export_current_referential(event: ft.ControlEvent | None = None) -> None:
        config = selected_config()
        records = list_records(state["key"])
        headers = [field["label"] for field in config["fields"]]
        rows = [
            [
                _format_cell(state["key"], field, record.get(field["name"]))
                for field in config["fields"]
            ]
            for record in records
        ]
        output = export_rows_xlsx(
            f"referentiel_{state['key']}.xlsx",
            config["label"],
            headers,
            rows,
        )
        notify(f"Export Excel cree: {output}", SUCCESS)
        root.update()

    def render_categories() -> None:
        category_area.controls = []
        for key in list_config_keys():
            config = get_config(key)
            is_selected = key == state["key"]
            category_area.controls.append(
                ft.TextButton(
                    content=config["label"],
                    icon=ft.Icons.CHEVRON_RIGHT if is_selected else None,
                    style=ft.ButtonStyle(
                        color=PRIMARY if is_selected else TEXT,
                        bgcolor="#EFF6FF" if is_selected else "#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda event, current_key=key: select_category(current_key),
                )
            )

    def render_form(record: dict[str, Any] | None = None) -> None:
        config = selected_config()
        form_controls.clear()
        title.value = config["label"]

        fields: list[ft.Control] = []
        for field in config["fields"]:
            value = _field_value(field, record)
            control = _build_field_control(state["key"], field, value)
            form_controls[field["name"]] = control
            fields.append(ft.Container(control, col={"sm": 12, "md": 6}))

        form_area.controls = [
            ft.ResponsiveRow(controls=fields, spacing=12, run_spacing=12),
            ft.Row(
                controls=[
                    ft.ElevatedButton(
                        "Enregistrer",
                        icon=ft.Icons.SAVE_OUTLINED,
                        on_click=save_record,
                    ),
                    ft.OutlinedButton(
                        "Nouveau",
                        icon=ft.Icons.ADD_OUTLINED,
                        on_click=clear_form,
                    ),
                    ft.OutlinedButton(
                        "Supprimer",
                        icon=ft.Icons.DELETE_OUTLINE,
                        disabled=state["selected_id"] is None,
                        on_click=lambda event: confirm_delete(),
                    ),
                ],
                wrap=True,
                spacing=10,
            ),
        ]

    def render_table() -> None:
        config = selected_config()
        records = list_records(state["key"])
        columns = [
            ft.DataColumn(ft.Text(field["label"]))
            for field in config["fields"]
        ]
        columns.append(ft.DataColumn(ft.Text("Actions")))

        table_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"{len(records)} element(s)", size=12, color=MUTED, expand=True),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_current_referential),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.DataTable(
                        columns=columns,
                        rows=[
                            ft.DataRow(
                                selected=record[config["pk"]] == state["selected_id"],
                                cells=[
                                    ft.DataCell(ft.Text(_format_cell(state["key"], field, record.get(field["name"]))))
                                    for field in config["fields"]
                                ]
                                + [
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(
                                                    icon=ft.Icons.EDIT_OUTLINED,
                                                    tooltip="Modifier",
                                                    on_click=lambda event, current=record: select_record(current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.DELETE_OUTLINE,
                                                    tooltip="Supprimer",
                                                    icon_color=DANGER,
                                                    on_click=lambda event, current=record: confirm_delete(current[config["pk"]]),
                                                ),
                                            ],
                                            spacing=0,
                                        )
                                    )
                                ],
                            )
                            for record in records
                        ],
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=8,
                        heading_row_color="#F1F5F9",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    def render_all() -> None:
        render_categories()
        render_form()
        render_table()
        root.update()

    root = ft.Column(
        controls=[
            module_header(
                "Referentiels",
                "Module 1: parametrage des donnees de base utilisees par tous les autres modules.",
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        width=235,
                        bgcolor="#FFFFFF",
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=8,
                        padding=12,
                        content=category_area,
                    ),
                    ft.Container(
                        expand=True,
                        bgcolor="#FFFFFF",
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=8,
                        padding=18,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[title, status],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                form_area,
                                ft.Divider(height=24),
                                table_area,
                            ],
                            spacing=14,
                        ),
                    ),
                ],
                spacing=16,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        spacing=22,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    render_categories()
    render_form()
    render_table()
    return root


def _field_value(field: dict[str, Any], record: dict[str, Any] | None) -> Any:
    if record is not None:
        return record.get(field["name"])
    return field.get("default", 0 if field["type"] == "bool" else "")


def _build_field_control(key: str, field: dict[str, Any], value: Any) -> ft.Control:
    label = field["label"] + (" *" if field.get("required") else "")

    if field["type"] == "bool":
        return ft.Checkbox(label=label, value=bool(value))

    if field["type"] == "choice":
        return ft.Dropdown(
            label=label,
            value=str(value) if value not in ("", None) else None,
            options=[ft.dropdown.Option(choice) for choice in field["choices"]],
        )

    if field["type"] == "fk":
        options = get_foreign_key_options(key, field["name"])
        return ft.Dropdown(
            label=label,
            value=str(value) if value not in ("", None) else None,
            options=[ft.dropdown.Option(str(option["value"]), str(option["label"])) for option in options],
        )

    if field["type"] == "int":
        return ft.TextField(label=label, value=str(value or ""), keyboard_type=ft.KeyboardType.NUMBER)

    return ft.TextField(label=label, value=str(value or ""))


def _format_cell(key: str, field: dict[str, Any], value: Any) -> str:
    if field["type"] == "bool":
        return "Oui" if value else "Non"
    if field["type"] == "fk" and value:
        options = get_foreign_key_options(key, field["name"])
        labels = {int(option["value"]): str(option["label"]) for option in options}
        return labels.get(int(value), str(value))
    return str(value or "-")
