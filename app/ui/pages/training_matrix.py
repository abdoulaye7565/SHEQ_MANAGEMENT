from __future__ import annotations

from typing import Any

import flet as ft

from app.services import (
    create_training,
    create_trainings_for_employees,
    export_training_matrix_xls,
    get_training_matrix,
    get_training_options,
    today_iso,
)
from app.ui.components.confirm import confirm_action
from app.ui.components.tables import professional_data_table
from app.ui.theme import DANGER, PRIMARY, SUCCESS, WARNING


from app.ui.components.dark_styles import BG, BORDER, CARD, FIELD
TEXT = "#FFFFFF"
MUTED = "#9DB0C5"
PURPLE = "#8B5CF6"
TEAL = "#14B8A6"
PAGE_SIZE = 10


def training_matrix_page(page: ft.Page | None = None) -> ft.Control:
    options = get_training_options()
    state: dict[str, Any] = {
        "matrix": {"training_types": [], "rows": [], "summary": {}},
        "selected": set(),
        "page": 0,
        "mode": "priorities",
    }
    status = ft.Text("", size=11, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=10, run_spacing=10)
    matrix_area = ft.Column(spacing=10)
    preview_area = ft.Container()
    mode_buttons: dict[str, ft.TextButton] = {}

    search_field = ft.TextField(label="Rechercher employe, formation...", prefix_icon=ft.Icons.SEARCH, width=285)
    status_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Etat",
        value="all",
        width=190,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("done", "Conformes"),
            ft.dropdown.Option("risk", "A traiter"),
            ft.dropdown.Option("soon", "Bientot expirees"),
            ft.dropdown.Option("missing", "Non faites / expirees"),
        ],
    )
    function_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Fonction", value="all", width=220)
    department_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Departement", value="all", width=210)
    bulk_training_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Formation a appliquer", width=260)
    bulk_date_field = ft.TextField(label="Date de formation", value=today_iso(), hint_text="AAAA-MM-JJ", width=180)
    bulk_facilitator_field = ft.TextField(label="Facilitateur", width=190)
    bulk_department_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Departement responsable", width=220)
    apply_button = ft.ElevatedButton("Appliquer a 0 employe", icon=ft.Icons.SEND_OUTLINED)
    _style_dark_inputs(
        search_field,
        status_filter,
        function_filter,
        department_filter,
        bulk_training_field,
        bulk_date_field,
        bulk_facilitator_field,
        bulk_department_field,
    )

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def update_root() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def load_options() -> None:
        fresh = get_training_options()
        bulk_training_field.options = [
            ft.dropdown.Option(str(item["value"]), f"{item['label']} - {item.get('department') or 'Sans departement'}")
            for item in fresh["training_types"]
        ]
        bulk_department_field.options = [
            ft.dropdown.Option(str(item["value"]), str(item["label"]))
            for item in fresh["departments"]
        ]
        if not bulk_training_field.value and fresh["training_types"]:
            bulk_training_field.value = str(fresh["training_types"][0]["value"])
        if not bulk_department_field.value and fresh["departments"]:
            bulk_department_field.value = str(fresh["departments"][0]["value"])
        sync_training_department()

    def sync_training_department(event: ft.ControlEvent | None = None) -> None:
        selected = int(bulk_training_field.value or 0)
        for item in options.get("training_types", []):
            if int(item["value"]) == selected and item.get("department"):
                bulk_department_field.value = str(item["department"])
                break
        if event is not None:
            update_root()

    bulk_training_field.on_select = sync_training_department

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            state["matrix"] = get_training_matrix()
            current_ids = {int(row["employee"]["id_employe"]) for row in state["matrix"]["rows"]}
            state["selected"] &= current_ids
            refresh_filter_options()
            render()
        except Exception as exc:
            notify(str(exc), DANGER)
        update_root()

    def refresh_filter_options() -> None:
        rows = state["matrix"]["rows"]
        functions = sorted({str(row["employee"].get("fonction") or "-") for row in rows})
        departments = sorted(
            {
                str(cell.get("training_department") or "Sans departement")
                for row in rows
                for cell in row.get("cells", [])
            }
        )
        function_filter.options = [ft.dropdown.Option("all", "Toutes les fonctions")]
        function_filter.options.extend(ft.dropdown.Option(item, item) for item in functions)
        department_filter.options = [ft.dropdown.Option("all", "Tous les departements")]
        department_filter.options.extend(ft.dropdown.Option(item, item) for item in departments)

    def filtered_rows() -> list[dict[str, Any]]:
        query = (search_field.value or "").strip().lower()
        selected_status = str(status_filter.value or "all")
        selected_function = str(function_filter.value or "all")
        selected_department = str(department_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for row in state["matrix"]["rows"]:
            employee = row["employee"]
            statuses = {cell["status"] for cell in row["cells"]}
            departments = {str(cell.get("training_department") or "Sans departement") for cell in row["cells"]}
            haystack = " ".join(
                [
                    *(str(employee.get(key) or "") for key in ("nom", "prenom", "numero_badge", "fonction")),
                    *(str(cell.get("training_name") or "") for cell in row["cells"]),
                ]
            ).lower()
            if query and query not in haystack:
                continue
            if selected_function != "all" and str(employee.get("fonction") or "-") != selected_function:
                continue
            if selected_department != "all" and selected_department not in departments:
                continue
            if selected_status == "done" and any(item not in {"done", "not_applicable"} for item in statuses):
                continue
            if selected_status == "risk" and not statuses.intersection({"soon", "missing", "expired"}):
                continue
            if selected_status == "soon" and "soon" not in statuses:
                continue
            if selected_status == "missing" and not statuses.intersection({"missing", "expired"}):
                continue
            if state["mode"] == "priorities" and not statuses.intersection({"soon", "missing", "expired"}):
                continue
            rows.append(row)
        return rows

    def set_mode(mode: str) -> None:
        state["mode"] = mode
        state["page"] = 0
        state["selected"].clear()
        render()
        update_root()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        status_filter.value = "all"
        function_filter.value = "all"
        department_filter.value = "all"
        state["page"] = 0
        render()
        update_root()

    def select_employee(employee_id: int, selected: bool) -> None:
        if selected:
            state["selected"].add(employee_id)
        else:
            state["selected"].discard(employee_id)
        render()
        update_root()

    def select_all_visible(event: ft.ControlEvent | None = None) -> None:
        state["selected"] = {int(row["employee"]["id_employe"]) for row in filtered_rows()}
        notify(f"{len(state['selected'])} employe(s) affiche(s) selectionne(s).", PRIMARY)
        render()
        update_root()

    def select_affected_employees(event: ft.ControlEvent | None = None) -> None:
        training_id = int(bulk_training_field.value or 0)
        selected: set[int] = set()
        already_valid = 0
        not_applicable = 0
        for row in filtered_rows():
            cell = next((item for item in row["cells"] if int(item["type_training_id"]) == training_id), None)
            if not cell or cell["status"] == "not_applicable":
                not_applicable += 1
                continue
            if cell["status"] == "done":
                already_valid += 1
                continue
            selected.add(int(row["employee"]["id_employe"]))
        state["selected"] = selected
        state["mode"] = "campaign"
        notify(
            f"Selection intelligente: {len(selected)} a mettre a jour, "
            f"{already_valid} deja conforme(s), {not_applicable} non applicable(s).",
            PRIMARY,
        )
        render()
        update_root()

    def clear_selection(event: ft.ControlEvent | None = None) -> None:
        state["selected"].clear()
        notify("Selection videe.", MUTED)
        render()
        update_root()

    def apply_bulk_update(event: ft.ControlEvent | None = None) -> None:
        selected = sorted(state["selected"])
        if not selected:
            notify("Selectionne au moins un employe ou clique sur Tous les affiches.", DANGER)
            update_root()
            return
        training_label = next(
            (
                str(item.get("label") or "Formation")
                for item in options.get("training_types", [])
                if int(item["value"]) == int(bulk_training_field.value or 0)
            ),
            "Formation",
        )
        confirm_action(
            page,
            "Confirmer la mise a jour globale",
            (
                f"{training_label} sera appliquee a {len(selected)} employe(s) "
                f"a la date du {bulk_date_field.value or '-'}. "
                "L'expiration sera calculee automatiquement."
            ),
            _apply_bulk_update,
            confirm_label="Appliquer la campagne",
            danger=len(selected) > 20,
        )

    def _apply_bulk_update() -> None:
        selected = sorted(state["selected"])
        try:
            total = create_trainings_for_employees(
                {
                    "employee_ids": selected,
                    "training_type_ids": [bulk_training_field.value],
                    "date_formation": bulk_date_field.value,
                    "facilitateur": bulk_facilitator_field.value,
                    "structure_responsable": bulk_department_field.value,
                }
            )
            state["selected"].clear()
            notify(f"Mise a jour globale terminee: {total} employe(s) actualise(s).", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            update_root()

    def quick_update(employee: dict[str, Any], cell: dict[str, Any]) -> None:
        if cell.get("status") == "not_applicable":
            notify("Cette formation n'est pas requise pour la fonction de cet employe.", MUTED)
            update_root()
            return
        employee_name = f"{employee.get('nom') or '-'} {employee.get('prenom') or ''}".strip()
        confirm_action(
            page,
            "Valider cette competence",
            (
                f"Confirmer {cell.get('training_name') or 'cette formation'} pour "
                f"{employee_name} a la date du {today_iso()}."
            ),
            lambda: _quick_update(employee, cell),
            confirm_label="Valider aujourd'hui",
        )

    def _quick_update(employee: dict[str, Any], cell: dict[str, Any]) -> None:
        try:
            create_training(
                {
                    "employe_id": employee["id_employe"],
                    "type_training_id": cell["type_training_id"],
                    "date_formation": today_iso(),
                    "facilitateur": bulk_facilitator_field.value,
                    "structure_responsable": cell.get("training_department") or bulk_department_field.value,
                }
            )
            notify(f"{cell.get('training_name') or 'Formation'} mise a jour pour {employee.get('nom') or 'employe'}.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            update_root()

    def export_matrix(event: ft.ControlEvent | None = None) -> None:
        output = export_training_matrix_xls(state["matrix"]["training_types"], filtered_rows())
        notify(f"Export Excel cree: {output}", SUCCESS)
        update_root()

    def change_page(delta: int) -> None:
        state["page"] = max(0, int(state["page"]) + delta)
        render()
        update_root()

    def render() -> None:
        rows = filtered_rows()
        render_summary(rows)
        render_matrix(rows)
        selected_count = len(state["selected"])
        apply_button.content = f"Appliquer a {selected_count} employe(s)"
        apply_button.disabled = selected_count == 0
        render_preview(rows)
        for key, button in mode_buttons.items():
            selected = state["mode"] == key
            button.style = ft.ButtonStyle(
                color="#60A5FA" if selected else MUTED,
                bgcolor="#0D2540" if selected else FIELD,
                side=ft.BorderSide(1, PRIMARY if selected else BORDER),
                shape=ft.RoundedRectangleBorder(radius=6),
            )

    def render_preview(rows: list[dict[str, Any]]) -> None:
        training_id = int(bulk_training_field.value or 0)
        affected = valid = not_applicable = 0
        for row in rows:
            cell = next((item for item in row["cells"] if int(item["type_training_id"]) == training_id), None)
            if not cell or cell["status"] == "not_applicable":
                not_applicable += 1
            elif cell["status"] == "done":
                valid += 1
            else:
                affected += 1
        preview_area.content = ft.Row(
            controls=[
                _preview_metric("A mettre a jour", affected, WARNING),
                _preview_metric("Deja conformes", valid, SUCCESS),
                _preview_metric("Non applicables", not_applicable, MUTED),
                _preview_metric("Selectionnes", len(state["selected"]), PRIMARY),
            ],
            spacing=8,
            wrap=True,
        )

    def render_summary(rows: list[dict[str, Any]]) -> None:
        training_count = len(state["matrix"]["training_types"])
        total = sum(1 for row in rows for cell in row["cells"] if cell["status"] != "not_applicable")
        valid = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "done")
        soon = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "soon")
        expired = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "expired")
        missing = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "missing")
        compliant_employees = sum(
            1
            for row in rows
            if all(cell["status"] in {"done", "not_applicable"} for cell in row["cells"])
        )
        conformity = round(valid * 100 / total) if total else 0
        summary_row.controls = [
            _summary_chip("Employes actifs", len(rows), f"Sur {state['matrix']['summary'].get('employees') or 0}", PRIMARY, ft.Icons.GROUPS_OUTLINED),
            _summary_chip("Formations", training_count, "Actives", PURPLE, ft.Icons.SCHOOL_OUTLINED),
            _summary_chip("Conformite globale", f"{conformity}%", "Matrice actuelle", TEAL, ft.Icons.QUERY_STATS_OUTLINED),
            _summary_chip("Conformes", compliant_employees, "Employes a jour", SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _summary_chip("Bientot expirees", soon, "A renouveler", WARNING, ft.Icons.SCHEDULE_OUTLINED),
            _summary_chip("Expirees", expired, "Action requise", DANGER, ft.Icons.EVENT_BUSY_OUTLINED),
            _summary_chip("Non conformes", missing, "Competences absentes", DANGER, ft.Icons.CANCEL_OUTLINED),
        ]

    def render_matrix(rows: list[dict[str, Any]]) -> None:
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = min(max(int(state["page"]), 0), max_page)
        start = int(state["page"]) * PAGE_SIZE
        page_rows = rows[start : start + PAGE_SIZE]
        selected = state["selected"]
        type_indexes = _visible_training_indexes(
            rows,
            state["matrix"]["training_types"],
            str(state["mode"]),
            int(bulk_training_field.value or 0),
        )
        columns = [
            ft.DataColumn(ft.Text("")),
            ft.DataColumn(ft.Text("Employe")),
            ft.DataColumn(ft.Text("Badge")),
            ft.DataColumn(ft.Text("Fonction")),
            *[
                ft.DataColumn(
                    ft.Column(
                        controls=[
                            ft.Text(str(item["nom"]), size=10, color=TEXT, weight=ft.FontWeight.BOLD),
                            ft.Text(str(item.get("department") or "-"), size=9, color=MUTED),
                        ],
                        spacing=0,
                    )
                )
                for index, item in enumerate(state["matrix"]["training_types"])
                if index in type_indexes
            ],
            ft.DataColumn(ft.Text("Conformite")),
        ]
        matrix_area.controls = [
            ft.Row(
                controls=[
                    _legend("Fait / valide", SUCCESS),
                    _legend("Bientot expire", WARNING),
                    _legend("Non fait / expire", DANGER),
                    _legend("N/A", MUTED),
                    ft.Text("Un clic sur une competence ouvre une confirmation rapide.", color=MUTED, size=10),
                ],
                wrap=True,
                spacing=8,
            ),
            ft.Row(
                controls=[
                    ft.OutlinedButton("Tous les affiches", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=select_all_visible),
                    ft.OutlinedButton("Vider selection", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=clear_selection),
                    ft.Text(f"{len(selected)} selectionne(s)", color="#60A5FA", size=11, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Affichage {start + 1 if rows else 0}-{start + len(page_rows)} sur {len(rows)}", color=MUTED, size=10),
                    ft.OutlinedButton("Precedent", disabled=int(state["page"]) == 0, on_click=lambda event: change_page(-1)),
                    ft.OutlinedButton("Suivant", disabled=int(state["page"]) >= max_page, on_click=lambda event: change_page(1)),
                ],
                wrap=True,
                spacing=8,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=columns,
                        rows=[
                            ft.DataRow(
                                selected=int(row["employee"]["id_employe"]) in selected,
                                cells=[
                                    ft.DataCell(
                                        ft.Checkbox(
                                            value=int(row["employee"]["id_employe"]) in selected,
                                            on_change=lambda event, current=row: select_employee(
                                                int(current["employee"]["id_employe"]),
                                                bool(event.control.value),
                                            ),
                                        )
                                    ),
                                    ft.DataCell(_employee_cell(row["employee"])),
                                    ft.DataCell(ft.Text(str(row["employee"].get("numero_badge") or "-"))),
                                    ft.DataCell(ft.Text(str(row["employee"].get("fonction") or "-"))),
                                    *[
                                        ft.DataCell(
                                            _matrix_cell(
                                                cell,
                                                lambda event, employee=row["employee"], current=cell: quick_update(employee, current),
                                            )
                                        )
                                        for index, cell in enumerate(row["cells"])
                                        if index in type_indexes
                                    ],
                                    ft.DataCell(_compliance_badge(row["cells"])),
                                ],
                            )
                            for row in page_rows
                        ],
                        bgcolor=FIELD,
                        border=ft.border.all(1, BORDER),
                        border_radius=8,
                        heading_row_color=CARD,
                        horizontal_lines=ft.BorderSide(1, BORDER),
                        vertical_lines=ft.BorderSide(1, BORDER),
                        heading_text_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color="#60A5FA"),
                        data_text_style=ft.TextStyle(size=11, color=TEXT),
                        column_spacing=12,
                        horizontal_margin=10,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    apply_button.on_click = apply_bulk_update
    apply_button.style = ft.ButtonStyle(bgcolor=PRIMARY, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6))

    root = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("Mode d'affichage", color=MUTED, size=10),
                    *[
                        mode_buttons.setdefault(
                            key,
                            ft.TextButton(label, icon=icon, on_click=lambda event, current=key: set_mode(current)),
                        )
                        for key, label, icon in [
                            ("priorities", "Priorites", ft.Icons.PRIORITY_HIGH_OUTLINED),
                            ("full", "Matrice complete", ft.Icons.GRID_VIEW_OUTLINED),
                            ("campaign", "Campagne", ft.Icons.AUTO_AWESOME_OUTLINED),
                        ]
                    ],
                ],
                spacing=6,
                wrap=True,
            ),
            summary_row,
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=10,
                content=ft.Row(
                    controls=[
                        status_filter,
                        function_filter,
                        department_filter,
                        search_field,
                        ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Appliquer filtres", on_click=lambda event: refresh()),
                        ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_filters),
                        ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_matrix),
                    ],
                    wrap=True,
                    spacing=8,
                ),
            ),
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text("Mise a jour globale", color=TEXT, size=14, weight=ft.FontWeight.BOLD),
                                        ft.Text(
                                            "Selectionne les employes, choisis la formation et clique sur appliquer.",
                                            color=MUTED,
                                            size=10,
                                        ),
                                    ],
                                    spacing=1,
                                    width=580,
                                ),
                                ft.OutlinedButton("Tous les employes affiches", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=select_all_visible),
                                ft.ElevatedButton(
                                    "Selection intelligente",
                                    icon=ft.Icons.AUTO_AWESOME_OUTLINED,
                                    on_click=select_affected_employees,
                                    style=ft.ButtonStyle(
                                        bgcolor="#0D4D3A",
                                        color=TEXT,
                                        shape=ft.RoundedRectangleBorder(radius=6),
                                    ),
                                ),
                            ],
                            wrap=True,
                        ),
                        ft.Row(
                            controls=[
                                bulk_training_field,
                                bulk_date_field,
                                bulk_facilitator_field,
                                bulk_department_field,
                                apply_button,
                            ],
                            wrap=True,
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        preview_area,
                        status,
                    ],
                    spacing=8,
                ),
            ),
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=10,
                content=matrix_area,
            ),
        ],
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    load_options()
    refresh()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _employee_cell(employee: dict[str, Any]) -> ft.Control:
    name = f"{employee.get('nom') or '-'} {employee.get('prenom') or ''}".strip()
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "E"
    return ft.Row(
        controls=[
            ft.Container(
                width=30,
                height=30,
                bgcolor="#1D4ED8",
                border_radius=15,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(initials, color=TEXT, size=10, weight=ft.FontWeight.BOLD),
            ),
            ft.Text(name, color=TEXT, size=10, weight=ft.FontWeight.BOLD, width=150, max_lines=2),
        ],
        spacing=7,
    )


def _matrix_cell(cell: dict[str, Any], on_update: Any) -> ft.Control:
    status = str(cell.get("status") or "")
    color = {
        "done": PRIMARY,
        "soon": WARNING,
        "missing": "#475569",
        "expired": DANGER,
        "not_applicable": "#334155",
    }.get(status, MUTED)
    icon = {
        "done": ft.Icons.CHECK,
        "soon": ft.Icons.WARNING_AMBER_OUTLINED,
        "not_applicable": ft.Icons.REMOVE,
    }.get(status, ft.Icons.CLOSE)
    return ft.Container(
        width=112,
        bgcolor=f"{color}B8",
        border=ft.border.all(1, color),
        border_radius=5,
        padding=ft.padding.symmetric(horizontal=6, vertical=5),
        tooltip=_cell_tooltip(cell),
        on_click=on_update,
        content=ft.Row(
            controls=[
                ft.Text(_cell_display_text(cell), color=TEXT, size=9, expand=True, text_align=ft.TextAlign.CENTER),
                ft.Icon(icon, color=SUCCESS if status == "done" else TEXT, size=13),
            ],
            spacing=2,
        ),
    )


def _compliance_badge(cells: list[dict[str, Any]]) -> ft.Control:
    compliance = round(sum(1 for cell in cells if cell["status"] == "done") * 100 / len(cells)) if cells else 0
    color = SUCCESS if compliance >= 80 else WARNING if compliance >= 50 else DANGER
    return ft.Container(
        width=48,
        height=32,
        border=ft.border.all(3, color),
        border_radius=16,
        alignment=ft.Alignment.CENTER,
        content=ft.Text(f"{compliance}%", color=color, size=9, weight=ft.FontWeight.BOLD),
    )


def _summary_chip(label: str, value: Any, detail: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4, "lg": 1.7},
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=10,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=38,
                    height=38,
                    bgcolor=f"{color}30",
                    border_radius=7,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=color, size=20),
                ),
                ft.Column(
                    controls=[
                        ft.Text(label, size=9, color=MUTED, max_lines=1),
                        ft.Text(str(value), size=19, color=TEXT, weight=ft.FontWeight.BOLD),
                        ft.Text(detail, size=8, color=MUTED, max_lines=1),
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=7,
        ),
    )


def _legend(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=f"{color}35",
        border=ft.border.all(1, color),
        border_radius=5,
        padding=ft.padding.symmetric(horizontal=7, vertical=4),
        content=ft.Text(label, size=9, color=TEXT),
    )


def _cell_display_text(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    expiration = str(cell.get("date_expiration") or "")
    if status == "done":
        return expiration or "Valide"
    if status == "soon":
        return expiration or "Bientot"
    if status == "expired":
        return "Expiree"
    if status == "not_applicable":
        return "N/A"
    return "Non fait"


def _cell_tooltip(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    expiration = str(cell.get("date_expiration") or "")
    if status == "done":
        return f"Valide jusqu'au {expiration}. Cliquer pour renouveler."
    if status == "soon":
        return f"Expiration proche: {expiration}. Cliquer pour renouveler."
    if status == "expired":
        return f"Expiree depuis le {expiration}. Cliquer pour renouveler."
    if status == "not_applicable":
        return "Non applicable pour cette fonction."
    return "Formation non faite. Cliquer pour valider aujourd'hui."


def _visible_training_indexes(
    rows: list[dict[str, Any]],
    training_types: list[dict[str, Any]],
    mode: str,
    selected_training_id: int,
) -> set[int]:
    if mode == "full":
        return set(range(len(training_types)))
    if mode == "campaign":
        selected = {
            index
            for index, item in enumerate(training_types)
            if int(item["id_training_type"]) == selected_training_id
        }
        return selected or set(range(min(len(training_types), 1)))
    priority_indexes = {
        index
        for index in range(len(training_types))
        if any(row["cells"][index]["status"] in {"soon", "expired", "missing"} for row in rows)
    }
    return set(sorted(priority_indexes)[:8]) or set(range(min(len(training_types), 8)))


def _preview_metric(label: str, value: int, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, BORDER),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row(
            controls=[
                ft.Container(width=7, height=7, bgcolor=color, border_radius=4),
                ft.Text(label, color=MUTED, size=9),
                ft.Text(str(value), color=TEXT, size=11, weight=ft.FontWeight.BOLD),
            ],
            spacing=5,
        ),
    )


def _style_dark_inputs(*controls: ft.Control) -> None:
    for control in controls:
        control.bgcolor = FIELD
        control.color = TEXT
        control.border_color = BORDER
        control.focused_border_color = PRIMARY
        control.label_style = ft.TextStyle(color=MUTED)
        control.hint_style = ft.TextStyle(color="#6F849A")
