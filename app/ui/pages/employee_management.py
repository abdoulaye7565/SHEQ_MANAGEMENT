from __future__ import annotations

import flet as ft

from app.ui.pages.active_breaks import active_breaks_page
from app.ui.pages.attendance import attendance_page
from app.ui.pages.breaks import breaks_page
from app.ui.pages.employee_form import employee_form_page
from app.ui.pages.employee_import import employee_import_page
from app.ui.pages.employees import employees_page
from app.ui.pages.former_employees import former_employees_page
from app.ui.theme import PRIMARY


from app.ui.components.dark_styles import BG, BORDER, CARD
MUTED = "#9DB0C5"


def employee_management_page(page: ft.Page | None = None) -> ft.Control:
    content = ft.Container()
    state: dict[str, object] = {"view": "employees", "editing_employee_id": None}

    employees_button = ft.TextButton()
    former_employees_button = ft.TextButton()
    add_employee_button = ft.TextButton()
    import_employee_button = ft.TextButton()
    attendance_button = ft.TextButton()
    breaks_button = ft.TextButton()
    active_breaks_button = ft.TextButton()

    def render() -> None:
        view = str(state["view"])
        employees_button.style = _button_style(view == "employees")
        former_employees_button.style = _button_style(view == "former_employees")
        add_employee_button.style = _button_style(view in {"add_employee", "edit_employee"})
        import_employee_button.style = _button_style(view == "import_employees")
        attendance_button.style = _button_style(view == "attendance")
        breaks_button.style = _button_style(view == "breaks")
        active_breaks_button.style = _button_style(view == "active_breaks")
        content.content = _build_view(
            view,
            page,
            open_employee_editor,
            state.get("editing_employee_id"),
            back_to_list,
        )
        try:
            root.update()
        except RuntimeError:
            pass

    def set_view(view: str) -> None:
        state["view"] = view
        if view != "edit_employee":
            state["editing_employee_id"] = None
        render()

    def open_employee_editor(employee_id: int) -> None:
        state["editing_employee_id"] = int(employee_id)
        state["view"] = "edit_employee"
        render()

    def back_to_list() -> None:
        state["view"] = "employees"
        state["editing_employee_id"] = None

    employees_button.content = "Liste des employes"
    employees_button.icon = ft.Icons.PEOPLE_ALT_OUTLINED
    employees_button.on_click = lambda event: set_view("employees")

    former_employees_button.content = "Anciens employes"
    former_employees_button.icon = ft.Icons.PERSON_OFF_OUTLINED
    former_employees_button.on_click = lambda event: set_view("former_employees")

    add_employee_button.content = "Ajouter un employe"
    add_employee_button.icon = ft.Icons.PERSON_ADD_ALT_1_OUTLINED
    add_employee_button.on_click = lambda event: set_view("add_employee")

    import_employee_button.content = "Importer"
    import_employee_button.icon = ft.Icons.UPLOAD_FILE_OUTLINED
    import_employee_button.on_click = lambda event: set_view("import_employees")

    attendance_button.content = "Liste de presence"
    attendance_button.icon = ft.Icons.EVENT_AVAILABLE_OUTLINED
    attendance_button.on_click = lambda event: set_view("attendance")

    breaks_button.content = "Breaks et permissions"
    breaks_button.icon = ft.Icons.BEACH_ACCESS_OUTLINED
    breaks_button.on_click = lambda event: set_view("breaks")

    active_breaks_button.content = "Employes en break"
    active_breaks_button.icon = ft.Icons.FREE_BREAKFAST_OUTLINED
    active_breaks_button.on_click = lambda event: set_view("active_breaks")

    root = ft.Container(
        bgcolor=BG,
        padding=8,
        expand=True,
        content=ft.Column(
        controls=[
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=16,
                content=ft.Row(
                    controls=[
                        ft.Container(
                            width=44,
                            height=44,
                            border_radius=8,
                            bgcolor=PRIMARY,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.PEOPLE_ALT_OUTLINED, color="#FFFFFF", size=24),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("Gestion employes", color="#FFFFFF", size=20, weight=ft.FontWeight.BOLD),
                                ft.Text("RH, affectations, badges et statut operationnel.", color=MUTED, size=12),
                            ],
                            spacing=2,
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Nouvel employe",
                            icon=ft.Icons.PERSON_ADD_ALT_1_OUTLINED,
                            style=ft.ButtonStyle(color="#FFFFFF", bgcolor=PRIMARY),
                            on_click=lambda event: set_view("add_employee"),
                        ),
                    ]
                ),
            ),
            ft.Container(
                bgcolor="#081525",
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=10,
                content=ft.Row(
                    controls=[
                        employees_button,
                        former_employees_button,
                        add_employee_button,
                        import_employee_button,
                        attendance_button,
                        active_breaks_button,
                        breaks_button,
                    ],
                    spacing=8,
                    wrap=True,
                ),
            ),
            content,
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        ),
    )

    render()
    return root


def _button_style(selected: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color="#FFFFFF" if selected else "#C7D4E3",
        bgcolor=PRIMARY if selected else "#10243A",
        shape=ft.RoundedRectangleBorder(radius=8),
    )


def _build_view(
    view: str,
    page: ft.Page | None,
    on_edit_employee: object,
    editing_employee_id: object = None,
    on_saved: object | None = None,
) -> ft.Control:
    if view == "employees":
        return employees_page(page, on_edit_employee=on_edit_employee)
    if view == "former_employees":
        return former_employees_page()
    if view == "add_employee":
        return employee_form_page(on_saved=on_saved)
    if view == "edit_employee":
        return employee_form_page(int(editing_employee_id or 0), on_saved=on_saved)
    if view == "import_employees":
        return employee_import_page(page)
    if view == "attendance":
        return attendance_page(page)
    if view == "active_breaks":
        return active_breaks_page()
    return breaks_page(page)
