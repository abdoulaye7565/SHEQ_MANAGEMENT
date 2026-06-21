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
    list_referential_counts,
    list_records,
    update_record,
)
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS


def referentials_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"key": "sites", "selected_id": None, "search": ""}
    form_controls: dict[str, ft.Control] = {}
    category_area = ft.Column(spacing=6)
    form_area = ft.Column(spacing=14)
    table_area = ft.Column(spacing=12)
    title = ft.Text(size=18, weight=ft.FontWeight.BOLD, color="#FFFFFF")
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=10, run_spacing=10)
    search_field = ft.TextField(
        label="Rechercher dans la liste",
        prefix_icon=ft.Icons.SEARCH,
        width=280,
        bgcolor="#0C1C2E",
        color="#FFFFFF",
        border_color="#1E3A56",
    )

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
                    width=210,
                    content=ft.Row(
                        controls=[
                            ft.Icon(_category_icon(key), size=17),
                            ft.Text(config["label"], size=11, weight=ft.FontWeight.BOLD, expand=True),
                        ],
                        spacing=8,
                    ),
                    style=ft.ButtonStyle(
                        color="#FFFFFF" if is_selected else "#C7D4E3",
                        bgcolor=PRIMARY if is_selected else "#10243A",
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=10, vertical=10),
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
                        bgcolor=PRIMARY,
                        color="#FFFFFF",
                        on_click=save_record,
                    ),
                    ft.OutlinedButton(
                        "Nouveau",
                        icon=ft.Icons.ADD_OUTLINED,
                        style=ft.ButtonStyle(color="#60A5FA"),
                        on_click=clear_form,
                    ),
                    ft.OutlinedButton(
                        "Supprimer",
                        icon=ft.Icons.DELETE_OUTLINE,
                        style=ft.ButtonStyle(color=DANGER),
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
        query = str(search_field.value or "").strip().lower()
        if query:
            records = [
                record
                for record in records
                if query in " ".join(
                    _format_cell(state["key"], field, record.get(field["name"]))
                    for field in config["fields"]
                ).lower()
            ]

        table_area.controls = [
            ft.Column(
                controls=[
                    ft.Text(
                        f"Liste des {config['label'].lower()} ({len(records)})",
                        size=15,
                        color="#FFFFFF",
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        controls=[
                            search_field,
                            ft.OutlinedButton(
                                "Exporter Excel",
                                icon=ft.Icons.DOWNLOAD_OUTLINED,
                                on_click=export_current_referential,
                            ),
                        ],
                        spacing=10,
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=8,
            ),
            ft.Column(
                controls=[
                    _referential_record_row(
                        state["key"],
                        config,
                        record,
                        record[config["pk"]] == state["selected_id"],
                        select_record,
                        confirm_delete,
                    )
                    for record in records
                ],
                spacing=6,
            )
            if records
            else ft.Text("Aucun element trouve.", color="#9DB0C5", size=11),
        ]

    def render_summary() -> None:
        counts = list_referential_counts()
        total = sum(int(row["total"]) for row in counts)
        active = sum(
            sum(1 for record in list_records(str(row["key"])) if record.get("actif", 1))
            for row in counts
        )
        summary_row.controls = [
            _reference_metric("Total referentiels", len(counts), PRIMARY, ft.Icons.ACCOUNT_TREE_OUTLINED, "Categories"),
            _reference_metric("Elements actifs", active, SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE, "En base"),
            _reference_metric("Elements en base", total, "#8B5CF6", ft.Icons.DATA_OBJECT_OUTLINED, "Toutes categories"),
            _reference_metric("Categorie active", selected_config()["label"], "#0891B2", ft.Icons.TUNE_OUTLINED, "Selection actuelle"),
        ]

    def render_all() -> None:
        render_categories()
        render_summary()
        render_form()
        render_table()
        root.update()

    search_field.on_change = lambda event: (render_table(), root.update())

    root = ft.Container(
        bgcolor="#071321",
        border_radius=8,
        padding=10,
        expand=True,
        content=ft.Column(
            controls=[
                _reference_header(),
                summary_row,
                ft.Row(
                controls=[
                    ft.Container(
                        width=235,
                        bgcolor="#0C1C2E",
                        border=ft.border.all(1, "#1E3A56"),
                        border_radius=8,
                        padding=12,
                        content=ft.Column(
                            controls=[
                                ft.Text("Categories", color="#FFFFFF", size=15, weight=ft.FontWeight.BOLD),
                                category_area,
                            ],
                            spacing=10,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        bgcolor="#081525",
                        border=ft.border.all(1, "#1E3A56"),
                        border_radius=8,
                        padding=14,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[title, status],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                form_area,
                                ft.Divider(height=18, color="#1E3A56"),
                                table_area,
                            ],
                            spacing=14,
                        ),
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    render_categories()
    render_summary()
    render_form()
    render_table()
    return root


def _reference_header() -> ft.Control:
    return ft.Container(
        bgcolor="#0F1F33",
        border=ft.border.all(1, "#1E3A56"),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=44,
                    height=44,
                    bgcolor=PRIMARY,
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.TUNE_OUTLINED, color="#FFFFFF", size=24),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Referentiels", color="#FFFFFF", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Parametrage des donnees de base partagees par tous les modules QHSE.",
                            color="#9DB0C5",
                            size=11,
                        ),
                    ],
                    spacing=2,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _reference_metric(label: str, value: Any, color: str, icon: str, subtitle: str) -> ft.Control:
    return ft.Container(
        bgcolor="#10243A",
        border=ft.border.all(1, "#1E3A56"),
        border_radius=8,
        padding=11,
        col={"sm": 6, "md": 3},
        content=ft.Row(
            controls=[
                ft.Container(
                    width=36,
                    height=36,
                    bgcolor="#0C1C2E",
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=color, size=19),
                ),
                ft.Column(
                    controls=[
                        ft.Text(label, color="#9DB0C5", size=9),
                        ft.Text(str(value), color="#FFFFFF", size=18, weight=ft.FontWeight.BOLD, max_lines=1),
                        ft.Text(subtitle, color="#7F94AA", size=8),
                    ],
                    spacing=1,
                    expand=True,
                ),
            ],
            spacing=8,
        ),
    )


def _category_icon(key: str) -> str:
    return {
        "sites": ft.Icons.LOCATION_ON_OUTLINED,
        "departments": ft.Icons.ACCOUNT_TREE_OUTLINED,
        "groupes": ft.Icons.GROUPS_OUTLINED,
        "fonctions": ft.Icons.BADGE_OUTLINED,
        "training_types": ft.Icons.SCHOOL_OUTLINED,
        "training_departments": ft.Icons.CORPORATE_FARE_OUTLINED,
        "types_epi": ft.Icons.HEALTH_AND_SAFETY_OUTLINED,
        "shifts": ft.Icons.SCHEDULE_OUTLINED,
        "shift_templates": ft.Icons.ACCESS_TIME_OUTLINED,
        "break_types": ft.Icons.COFFEE_OUTLINED,
        "roles": ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
    }.get(key, ft.Icons.TUNE_OUTLINED)


def _referential_record_row(
    key: str,
    config: dict[str, Any],
    record: dict[str, Any],
    selected: bool,
    select_callback: Any,
    delete_callback: Any,
) -> ft.Control:
    fields = config["fields"]
    primary = _format_cell(key, fields[0], record.get(fields[0]["name"])) if fields else "-"
    details = " | ".join(
        f"{field['label']}: {_format_cell(key, field, record.get(field['name']))}"
        for field in fields[1:]
    )
    active_field = next((field for field in fields if field["name"] == "actif"), None)
    active = bool(record.get("actif", 1)) if active_field else True
    return ft.Container(
        bgcolor="#17304A" if selected else "#0C1C2E",
        border=ft.border.all(1, PRIMARY if selected else "#1E3A56"),
        border_radius=8,
        padding=10,
        ink=True,
        on_click=lambda event: select_callback(record),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=38,
                    height=38,
                    bgcolor="#10243A",
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(_category_icon(key), color="#60A5FA", size=19),
                ),
                ft.Column(
                    controls=[
                        ft.Text(primary, color="#FFFFFF", size=11, weight=ft.FontWeight.BOLD),
                        ft.Text(details or config["label"], color="#9DB0C5", size=9, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Container(
                    bgcolor="#052E24" if active else "#3F1723",
                    border=ft.border.all(1, SUCCESS if active else DANGER),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    content=ft.Text("Actif" if active else "Inactif", color=SUCCESS if active else DANGER, size=9, weight=ft.FontWeight.BOLD),
                ),
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    tooltip="Modifier",
                    icon_color=PRIMARY,
                    on_click=lambda event: select_callback(record),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Supprimer",
                    icon_color=DANGER,
                    on_click=lambda event: delete_callback(record[config["pk"]]),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _field_value(field: dict[str, Any], record: dict[str, Any] | None) -> Any:
    if record is not None:
        return record.get(field["name"])
    return field.get("default", 0 if field["type"] == "bool" else "")


def _build_field_control(key: str, field: dict[str, Any], value: Any) -> ft.Control:
    label = field["label"] + (" *" if field.get("required") else "")

    if field["type"] == "bool":
        return ft.Checkbox(
            label=label,
            value=bool(value),
            label_style=ft.TextStyle(color="#C7D4E3"),
            active_color=SUCCESS,
            check_color="#FFFFFF",
        )

    if field["type"] == "choice":
        return ft.Dropdown(
            label=label,
            value=str(value) if value not in ("", None) else None,
            options=[ft.dropdown.Option(choice) for choice in field["choices"]],
            bgcolor="#0C1C2E",
            color="#FFFFFF",
            border_color="#1E3A56",
            focused_border_color=PRIMARY,
        )

    if field["type"] == "fk":
        options = get_foreign_key_options(key, field["name"])
        return ft.Dropdown(
            label=label,
            value=str(value) if value not in ("", None) else None,
            options=[ft.dropdown.Option(str(option["value"]), str(option["label"])) for option in options],
            bgcolor="#0C1C2E",
            color="#FFFFFF",
            border_color="#1E3A56",
            focused_border_color=PRIMARY,
        )

    if field["type"] == "int":
        return _reference_text_field(label, str(value or ""), ft.KeyboardType.NUMBER)

    return _reference_text_field(label, str(value or ""))


def _reference_text_field(label: str, value: str, keyboard_type: Any = None) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        keyboard_type=keyboard_type,
        bgcolor="#0C1C2E",
        color="#FFFFFF",
        border_color="#1E3A56",
        focused_border_color=PRIMARY,
    )


def _format_cell(key: str, field: dict[str, Any], value: Any) -> str:
    if field["type"] == "bool":
        return "Oui" if value else "Non"
    if field["type"] == "fk" and value:
        options = get_foreign_key_options(key, field["name"])
        labels = {int(option["value"]): str(option["label"]) for option in options}
        return labels.get(int(value), str(value))
    return str(value or "-")

