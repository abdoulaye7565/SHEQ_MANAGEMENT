from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    create_training,
    create_training_department,
    export_training_matrix_xls,
    get_training_matrix,
    get_training_options,
    today_iso,
)
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def training_matrix_page() -> ft.Control:
    state: dict[str, Any] = {"matrix": {"training_types": [], "rows": []}, "quick": None}
    status = ft.Text("", size=12, color=MUTED)
    matrix_area = ft.Column(spacing=10)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    training_stats_area = ft.Column(spacing=8)
    quick_area = ft.Container(visible=False)

    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=260)
    status_filter = ft.Dropdown(
        label="Etat",
        value="all",
        width=210,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("done", "Tout est fait"),
            ft.dropdown.Option("risk", "A traiter"),
            ft.dropdown.Option("soon", "Bientot expiree"),
            ft.dropdown.Option("missing", "Non faite / expiree"),
        ],
    )
    function_filter = ft.Dropdown(label="Fonction", value="all", width=220)
    quick_employee_text = ft.Text("", size=13, color=TEXT, weight=ft.FontWeight.BOLD)
    quick_training_text = ft.Text("", size=13, color=TEXT, weight=ft.FontWeight.BOLD)
    quick_date_field = ft.TextField(label="Date de mise a jour", value=today_iso(), hint_text="AAAA-MM-JJ", width=180)
    quick_facilitator_field = ft.TextField(label="Facilitateur", width=220)
    quick_department_field = ft.Dropdown(label="Departement", width=240)
    quick_new_department_field = ft.TextField(label="Nouveau departement", width=240)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        state["matrix"] = get_training_matrix()
        refresh_function_options()
        load_quick_departments()
        render_matrix()
        _update()

    def load_quick_departments() -> None:
        options = get_training_options()
        quick_department_field.options = [
            ft.dropdown.Option(str(item["value"]), str(item["label"]))
            for item in options["departments"]
        ]
        quick_department_field.value = quick_department_field.value or (
            str(options["departments"][0]["value"]) if options["departments"] else None
        )

    def refresh_function_options() -> None:
        rows = state["matrix"]["rows"]
        functions = sorted({str(row["employee"].get("fonction") or "-") for row in rows})
        current = function_filter.value
        function_filter.options = [ft.dropdown.Option("all", "Toutes les fonctions")]
        function_filter.options.extend(ft.dropdown.Option(item, item) for item in functions)
        function_filter.value = current if current in {"all", *functions} else "all"

    def filtered_rows() -> list[dict[str, Any]]:
        query = (search_field.value or "").strip().lower()
        selected_status = str(status_filter.value or "all")
        selected_function = str(function_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for row in state["matrix"]["rows"]:
            employee = row["employee"]
            haystack = " ".join(
                str(employee.get(key) or "")
                for key in ("nom", "prenom", "numero_badge", "fonction")
            ).lower()
            statuses = {cell["status"] for cell in row["cells"]}
            if query and query not in haystack:
                continue
            if selected_function != "all" and str(employee.get("fonction") or "-") != selected_function:
                continue
            if selected_status == "done" and any(item != "done" for item in statuses):
                continue
            if selected_status == "risk" and not any(item in {"soon", "missing", "expired"} for item in statuses):
                continue
            if selected_status == "soon" and "soon" not in statuses:
                continue
            if selected_status == "missing" and not any(item in {"missing", "expired"} for item in statuses):
                continue
            rows.append(row)
        return rows

    def export_matrix(event: ft.ControlEvent | None = None) -> None:
        matrix = state["matrix"]
        rows = filtered_rows()
        output = export_training_matrix_xls(matrix["training_types"], rows)
        notify(f"Export Excel cree: {output}", SUCCESS)
        _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        status_filter.value = "all"
        function_filter.value = "all"
        render_matrix()
        _update()

    def start_quick_update(employee: dict[str, Any], cell: dict[str, Any]) -> None:
        state["quick"] = {
            "employe_id": employee["id_employe"],
            "type_training_id": cell["type_training_id"],
        }
        quick_employee_text.value = f"{employee.get('nom') or '-'} {employee.get('prenom') or ''}".strip()
        quick_training_text.value = str(cell.get("training_name") or "-")
        quick_date_field.value = today_iso()
        quick_facilitator_field.value = ""
        quick_area.visible = True
        notify("Mise a jour preparee. Elle sera ajoutee comme nouvelle ligne d'historique.", PRIMARY)
        _update()

    def save_quick_update(event: ft.ControlEvent | None = None) -> None:
        quick = state.get("quick")
        if not quick:
            notify("Selectionne d'abord une cellule de la matrice.", DANGER)
            _update()
            return
        try:
            create_training(
                {
                    "employe_id": quick["employe_id"],
                    "type_training_id": quick["type_training_id"],
                    "date_formation": quick_date_field.value,
                    "facilitateur": quick_facilitator_field.value,
                    "structure_responsable": quick_department_field.value,
                }
            )
            notify("Formation mise a jour. L'historique precedent est conserve.", SUCCESS)
            state["quick"] = None
            quick_area.visible = False
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def cancel_quick_update(event: ft.ControlEvent | None = None) -> None:
        state["quick"] = None
        quick_area.visible = False
        notify("Mise a jour rapide annulee.", MUTED)
        _update()

    def add_quick_department(event: ft.ControlEvent | None = None) -> None:
        try:
            created_name = create_training_department(quick_new_department_field.value)
            load_quick_departments()
            quick_department_field.value = created_name
            quick_new_department_field.value = ""
            notify("Departement cree et selectionne.", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def render_matrix() -> None:
        matrix = state["matrix"]
        rows = filtered_rows()
        render_summary(rows, len(matrix["training_types"]))
        render_training_stats(rows, matrix["training_types"])
        columns = [
            ft.DataColumn(ft.Text("Employe")),
            ft.DataColumn(ft.Text("Badge")),
            ft.DataColumn(ft.Text("Fonction")),
            *[ft.DataColumn(ft.Text(item["nom"], size=12)) for item in matrix["training_types"]],
        ]
        matrix_area.controls = [
            ft.Row(
                controls=[
                    search_field,
                    status_filter,
                    function_filter,
                    ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Appliquer", on_click=lambda event: render_and_update()),
                    ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_filters),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_matrix),
                    status,
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    _legend("Faite", PRIMARY),
                    _legend("Bientot expiree", WARNING),
                    _legend("Non faite / expiree", DANGER),
                ],
                wrap=True,
                spacing=12,
            ),
            summary_row,
            training_stats_area,
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=columns,
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(f"{row['employee'].get('nom') or '-'} {row['employee'].get('prenom') or ''}")),
                                    ft.DataCell(ft.Text(str(row["employee"].get("numero_badge") or "-"))),
                                    ft.DataCell(ft.Text(str(row["employee"].get("fonction") or "-"))),
                                    *[
                                        ft.DataCell(
                                            _matrix_cell(
                                                cell,
                                                lambda event, current_employee=row["employee"], current_cell=cell: start_quick_update(
                                                    current_employee,
                                                    current_cell,
                                                ),
                                            )
                                        )
                                        for cell in row["cells"]
                                    ],
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

    def render_and_update() -> None:
        render_matrix()
        _update()

    def render_summary(rows: list[dict[str, Any]], training_count: int) -> None:
        total_cells = len(rows) * training_count
        done = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "done")
        soon = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "soon")
        expired = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "expired")
        missing = sum(1 for row in rows for cell in row["cells"] if cell["status"] == "missing")
        completion = round(done * 100 / total_cells) if total_cells else 0
        summary_row.controls = [
            _summary_chip("Employes", len(rows), PRIMARY, ft.Icons.GROUP_OUTLINED),
            _summary_chip("Conformite", f"{completion}%", SUCCESS, ft.Icons.INSIGHTS_OUTLINED),
            _summary_chip("Bientot", soon, WARNING, ft.Icons.SCHEDULE_OUTLINED),
            _summary_chip("Expirees", expired, DANGER, ft.Icons.EVENT_BUSY_OUTLINED),
            _summary_chip("Non faites", missing, DANGER, ft.Icons.REPORT_PROBLEM_OUTLINED),
        ]

    def render_training_stats(rows: list[dict[str, Any]], training_types: list[dict[str, Any]]) -> None:
        if not training_types:
            training_stats_area.controls = []
            return
        stats_rows: list[ft.DataRow] = []
        for index, training_type in enumerate(training_types):
            valid = soon = expired = missing = 0
            for row in rows:
                cells = row.get("cells", [])
                if index >= len(cells):
                    continue
                status_value = cells[index].get("status")
                if status_value == "done":
                    valid += 1
                elif status_value == "soon":
                    soon += 1
                elif status_value == "expired":
                    expired += 1
                elif status_value == "missing":
                    missing += 1
            total = valid + soon + expired + missing
            compliance = round(valid * 100 / total) if total else 0
            stats_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(training_type.get("nom") or "-"))),
                        ft.DataCell(ft.Text(str(valid), color=SUCCESS)),
                        ft.DataCell(ft.Text(str(soon), color=WARNING)),
                        ft.DataCell(ft.Text(str(expired), color=DANGER)),
                        ft.DataCell(ft.Text(str(missing), color=DANGER)),
                        ft.DataCell(ft.Text(f"{compliance}%", color=TEXT, weight=ft.FontWeight.BOLD)),
                    ]
                )
            )
        training_stats_area.controls = [
            ft.Text("Statistiques par formation", color=TEXT, weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Formation")),
                            ft.DataColumn(ft.Text("Valides")),
                            ft.DataColumn(ft.Text("Bientot")),
                            ft.DataColumn(ft.Text("Expirees")),
                            ft.DataColumn(ft.Text("Non faites")),
                            ft.DataColumn(ft.Text("Conformite")),
                        ],
                        rows=stats_rows,
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    root = ft.Column(
        controls=[
            module_header("Matrice formation", "Vue globale des formations par employe."),
            quick_area,
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=matrix_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    quick_area.bgcolor = "#FFFFFF"
    quick_area.border = ft.border.all(1, "#BFDBFE")
    quick_area.border_radius = 8
    quick_area.padding = 14
    quick_area.content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.UPDATE_OUTLINED, color=PRIMARY, size=18),
                    ft.Text("Mise a jour rapide avec historique", color=TEXT, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.Container(content=ft.Column([ft.Text("Employe", size=11, color=MUTED), quick_employee_text], spacing=2), width=260),
                    ft.Container(content=ft.Column([ft.Text("Formation", size=11, color=MUTED), quick_training_text], spacing=2), width=260),
                    quick_date_field,
                    quick_facilitator_field,
                    quick_department_field,
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    quick_new_department_field,
                    ft.OutlinedButton("Creer departement", icon=ft.Icons.ADD_BUSINESS_OUTLINED, on_click=add_quick_department),
                    ft.ElevatedButton("Enregistrer la mise a jour", icon=ft.Icons.SAVE_OUTLINED, on_click=save_quick_update),
                    ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, on_click=cancel_quick_update),
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=10,
    )
    refresh()
    return root


def _matrix_cell(cell: dict[str, Any], on_update: Any) -> ft.Control:
    color = {
        "done": PRIMARY,
        "soon": WARNING,
        "missing": DANGER,
        "expired": DANGER,
    }.get(cell["status"], MUTED)
    text_color = TEXT if cell["status"] == "soon" else "#FFFFFF"
    tooltip = _cell_tooltip(cell)
    return ft.Row(
        controls=[
            ft.Container(
                bgcolor=color,
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=5),
                width=118,
                tooltip=tooltip,
                content=ft.Text(
                    _cell_display_text(cell),
                    color=text_color,
                    size=11,
                    text_align=ft.TextAlign.CENTER,
                    no_wrap=False,
                ),
            ),
            ft.IconButton(
                icon=ft.Icons.ADD_OUTLINED,
                tooltip="Mettre a jour sans supprimer l'historique",
                icon_color=SUCCESS,
                on_click=on_update,
            ),
        ],
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _cell_display_text(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    expiration = str(cell.get("date_expiration") or "")
    if status == "done":
        return expiration or "Valide"
    if status == "soon":
        return f"J-{cell.get('days_left')}\n{expiration}" if expiration else "Bientot"
    if status == "expired":
        return f"Expiree\n{expiration}" if expiration else "Expiree"
    return "Non faite"


def _cell_tooltip(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    expiration = str(cell.get("date_expiration") or "")
    date_formation = str(cell.get("date_formation") or "")
    if status == "done":
        return f"Valide jusqu'au {expiration}" if expiration else "Formation valide"
    if status == "soon":
        return f"Expiration proche: {expiration}. Formation du {date_formation or '-'}."
    if status == "expired":
        return f"Formation expiree depuis le {expiration}."
    return "Formation non faite"


def _legend_rows(training_count: int) -> list[list[str]]:
    tail = ["" for _ in range(training_count)]
    return [
        ["", "", "", *tail],
        ["Legende", "Bleu", "Formation faite / valide", *tail],
        ["Legende", "Jaune", "Formation bientot expiree", *tail],
        ["Legende", "Rouge", "Formation non faite ou expiree", *tail],
    ]


def _legend_styles(training_count: int) -> list[list[str | None]]:
    tail = [None for _ in range(training_count)]
    return [
        [None, None, None, *tail],
        [None, "done", None, *tail],
        [None, "soon", None, *tail],
        [None, "expired", None, *tail],
    ]


def _summary_chip(label: str, value: int | str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _legend(label: str, color: str) -> ft.Control:
    text_color = TEXT if color == WARNING else "#FFFFFF"
    return ft.Container(
        bgcolor=color,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
        content=ft.Text(label, size=12, color=text_color),
    )
