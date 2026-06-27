from __future__ import annotations

from typing import Any

import flet as ft

from app.services import create_trainings_for_employees, get_training_options, today_iso
from app.ui.components.confirm import confirm_action
from app.ui.theme import DANGER, PRIMARY, SUCCESS, WARNING


CARD = "#10243A"
FIELD = "#0C1C2E"
BORDER = "#1E3A56"
TEXT = "#FFFFFF"
MUTED = "#9DB0C5"


def training_bulk_page(page: ft.Page | None = None) -> ft.Control:
    options = get_training_options()
    state: dict[str, Any] = {"employees": set(), "trainings": set()}
    employee_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
    training_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
    summary = ft.ResponsiveRow(spacing=8, run_spacing=8)
    status = ft.Text("", color=MUTED, size=11)
    employee_search = ft.TextField(label="Rechercher employe", prefix_icon=ft.Icons.SEARCH, width=300)
    training_search = ft.TextField(label="Rechercher formation", prefix_icon=ft.Icons.SEARCH, width=300)
    date_field = ft.TextField(label="Date formation", value=today_iso(), width=180)
    facilitator_field = ft.TextField(label="Facilitateur", width=220)
    department_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Departement", width=220)
    duplicate_policy = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Si la formation existe deja",
        value="update",
        width=250,
        options=[
            ft.dropdown.Option("update", "Mettre a jour"),
            ft.dropdown.Option("ignore", "Ignorer"),
        ],
    )
    apply_button = ft.ElevatedButton("Appliquer a tous", icon=ft.Icons.DONE_ALL_OUTLINED)
    _style_inputs(employee_search, training_search, date_field, facilitator_field, department_field, duplicate_policy)

    def update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def render() -> None:
        employee_query = (employee_search.value or "").strip().lower()
        training_query = (training_search.value or "").strip().lower()
        employees = [
            item
            for item in options["employees"]
            if employee_query in " ".join(str(value or "") for value in item.values()).lower()
        ]
        trainings = [
            item
            for item in options["training_types"]
            if training_query in " ".join(str(value or "") for value in item.values()).lower()
        ]
        employee_list.controls = [
            _selection_row(
                title=f"{item.get('nom') or '-'} {item.get('prenom') or ''}".strip(),
                subtitle=f"{item.get('fonction') or '-'} | {item.get('site') or '-'} | {item.get('numero_badge') or 'sans badge'}",
                selected=int(item["value"]) in state["employees"],
                on_change=lambda event, current=item: toggle("employees", int(current["value"]), bool(event.control.value)),
            )
            for item in employees
        ]
        training_list.controls = [
            _selection_row(
                title=str(item["label"]),
                subtitle=f"{item.get('department') or 'Sans departement'} | validite {item.get('validite_mois') or 0} mois",
                selected=int(item["value"]) in state["trainings"],
                on_change=lambda event, current=item: toggle("trainings", int(current["value"]), bool(event.control.value)),
            )
            for item in trainings
        ]
        operation_count = len(state["employees"]) * len(state["trainings"])
        summary.controls = [
            ft.Container(_metric("Employes selectionnes", len(state["employees"]), PRIMARY), col={"xs": 12, "sm": 4}),
            ft.Container(_metric("Formations selectionnees", len(state["trainings"]), WARNING), col={"xs": 12, "sm": 4}),
            ft.Container(_metric("Mises a jour prevues", operation_count, SUCCESS), col={"xs": 12, "sm": 4}),
        ]
        apply_button.content = f"Appliquer a tous ({operation_count})"
        apply_button.disabled = operation_count == 0

    def toggle(key: str, item_id: int, selected: bool) -> None:
        if selected:
            state[key].add(item_id)
        else:
            state[key].discard(item_id)
        render()
        update()

    def select_all(key: str, selected: bool) -> None:
        source = options["employees"] if key == "employees" else options["training_types"]
        state[key] = {int(item["value"]) for item in source} if selected else set()
        render()
        update()

    def apply(event: ft.ControlEvent | None = None) -> None:
        operations = len(state["employees"]) * len(state["trainings"])
        confirm_action(
            page,
            "Confirmer la mise a jour groupee",
            (
                f"{len(state['employees'])} employe(s) x {len(state['trainings'])} formation(s) "
                f"= {operations} operation(s). Politique doublon: "
                f"{'mettre a jour' if duplicate_policy.value == 'update' else 'ignorer'}."
            ),
            execute,
            confirm_label="Appliquer a tous",
            danger=operations > 50,
        )

    def execute() -> None:
        try:
            total = create_trainings_for_employees(
                {
                    "employee_ids": sorted(state["employees"]),
                    "training_type_ids": sorted(state["trainings"]),
                    "date_formation": date_field.value,
                    "facilitateur": facilitator_field.value,
                    "structure_responsable": department_field.value,
                    "duplicate_policy": duplicate_policy.value,
                }
            )
            status.value = f"Campagne terminee: {total} mise(s) a jour enregistree(s)."
            status.color = SUCCESS
            state["employees"].clear()
            state["trainings"].clear()
            render()
        except Exception as exc:
            status.value = str(exc)
            status.color = DANGER
        update()

    department_field.options = [ft.dropdown.Option(str(item["value"]), str(item["label"])) for item in options["departments"]]
    if options["departments"]:
        department_field.value = str(options["departments"][0]["value"])
    employee_search.on_change = lambda event: (render(), update())
    training_search.on_change = lambda event: (render(), update())
    apply_button.on_click = apply
    apply_button.style = ft.ButtonStyle(bgcolor=PRIMARY, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6))

    root = ft.Column(
        controls=[
            _steps(),
            summary,
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        _selection_panel(
                            "1. Selection des employes",
                            employee_search,
                            employee_list,
                            lambda event: select_all("employees", True),
                            lambda event: select_all("employees", False),
                        ),
                        col={"xs": 12, "lg": 6},
                    ),
                    ft.Container(
                        _selection_panel(
                            "2. Selection des formations",
                            training_search,
                            training_list,
                            lambda event: select_all("trainings", True),
                            lambda event: select_all("trainings", False),
                        ),
                        col={"xs": 12, "lg": 6},
                    ),
                ],
                spacing=10,
                run_spacing=10,
            ),
            _panel(
                "3. Parametres communs",
                [
                    ft.Row(
                        controls=[date_field, facilitator_field, department_field, duplicate_policy],
                        spacing=8,
                        wrap=True,
                    ),
                    ft.Text(
                        "La date d'expiration est calculee automatiquement. Les doublons ne sont jamais crees.",
                        color=MUTED,
                        size=10,
                    ),
                ],
            ),
            _panel("4. Confirmation", [ft.Row([apply_button, status], spacing=10, wrap=True)]),
        ],
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _steps() -> ft.Control:
    return ft.Row(
        controls=[
            _step(index, label, color)
            for index, label, color in [
                (1, "Employes", PRIMARY),
                (2, "Formations", "#8B5CF6"),
                (3, "Informations", WARNING),
                (4, "Confirmer", SUCCESS),
            ]
        ],
        spacing=8,
        wrap=True,
    )


def _step(index: int, label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=7,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=24,
                    height=24,
                    bgcolor=color,
                    border_radius=12,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(str(index), color=TEXT, size=10, weight=ft.FontWeight.BOLD),
                ),
                ft.Text(label, color=TEXT, size=11),
            ],
            spacing=6,
        ),
    )


def _selection_panel(title: str, search: ft.Control, listing: ft.Control, select_all: Any, clear: Any) -> ft.Control:
    return _panel(
        title,
        [
            ft.Row(
                controls=[
                    search,
                    ft.OutlinedButton("Tout selectionner", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=select_all),
                    ft.IconButton(icon=ft.Icons.CLEAR_ALL_OUTLINED, tooltip="Vider", on_click=clear),
                ],
                wrap=True,
                spacing=6,
            ),
            ft.Container(content=listing, height=330),
        ],
    )


def _selection_row(title: str, subtitle: str, selected: bool, on_change: Any) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, PRIMARY if selected else BORDER),
        border_radius=6,
        padding=6,
        content=ft.Checkbox(
            value=selected,
            on_change=on_change,
            label=f"{title}\n{subtitle}",
            label_style=ft.TextStyle(color=TEXT, size=10),
        ),
    )


def _metric(label: str, value: int, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=7,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Text(label, color=MUTED, size=10),
                ft.Text(str(value), color=color, size=22, weight=ft.FontWeight.BOLD),
            ],
            spacing=1,
        ),
    )


def _panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=12,
        content=ft.Column(
            controls=[ft.Text(title, color=TEXT, size=13, weight=ft.FontWeight.BOLD), *controls],
            spacing=8,
        ),
    )


def _style_inputs(*controls: ft.Control) -> None:
    for control in controls:
        control.bgcolor = FIELD
        control.color = TEXT
        control.border_color = BORDER
        control.focused_border_color = PRIMARY
        control.label_style = ft.TextStyle(color=MUTED)
        control.hint_style = ft.TextStyle(color="#6F849A")
