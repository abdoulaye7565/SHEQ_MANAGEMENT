from __future__ import annotations

from typing import Any

import flet as ft

from app.services import create_employee, get_employee, get_employee_form_options, update_employee
from app.services.employee_service import BADGE_STATUSES, EMPLOYEE_STATUSES, EMPLOYEE_TYPES
from app.ui.theme import DANGER, PRIMARY, SUCCESS


from app.ui.components.dark_styles import BG, BORDER, CARD, FIELD
TEXT = "#FFFFFF"
MUTED = "#9DB0C5"


def employee_form_page(
    employee_id: int | None = None,
    on_saved: Any | None = None,
) -> ft.Control:
    options = get_employee_form_options()
    controls: dict[str, ft.Control] = {}
    status = ft.Text("", size=11, color=MUTED)
    form_area = ft.Column(spacing=12)
    is_edit = employee_id is not None

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def default_values() -> dict[str, Any]:
        return {
            "matricule": "",
            "nom": "",
            "prenom": "",
            "nom_complet": "",
            "fonction_id": _first_option(options["fonctions"]),
            "site_id": _first_option(options["sites"]),
            "groupe_id": None,
            "shift_id": _first_option(options["shifts"]),
            "type_employe": "national",
            "statut_employe": "actif",
            "numero_badge": "",
            "statut_badge": "valide",
            "date_remise": "",
            "date_expiration_badge": "",
        }

    def initial_values() -> dict[str, Any]:
        if employee_id is None:
            return default_values()
        employee = get_employee(int(employee_id))
        if employee is None:
            notify("Employe introuvable.", DANGER)
            return default_values()
        values = default_values()
        values.update(employee)
        return values

    def clear_form(event: ft.ControlEvent | None = None) -> None:
        render_form(initial_values() if is_edit else default_values())
        notify("Fiche rechargee." if is_edit else "Nouveau formulaire pret.", MUTED)
        root.update()

    def save_employee(event: ft.ControlEvent | None = None, keep_open: bool = False) -> None:
        try:
            values = {name: control.value for name, control in controls.items()}
            if employee_id is None:
                create_employee(values)
                render_form(default_values())
                notify("Employe ajoute avec succes.", SUCCESS)
            else:
                update_employee(int(employee_id), values)
                render_form(initial_values())
                notify("Fiche employe mise a jour.", SUCCESS)
            if on_saved is not None and not keep_open:
                root.update()
                on_saved()
                return
        except Exception as exc:
            notify(str(exc), DANGER)
        root.update()

    def render_form(values: dict[str, Any]) -> None:
        controls.clear()
        controls["matricule"] = _text_field("Matricule *", values.get("matricule"), "Ex: EMP-000123")
        controls["nom"] = _text_field("Nom *", values.get("nom"), "Entrez le nom de famille")
        controls["prenom"] = _text_field("Prenom *", values.get("prenom"), "Entrez le prenom")
        controls["nom_complet"] = ft.TextField(value="", visible=False)
        controls["fonction_id"] = _dropdown("Fonction *", options["fonctions"], values.get("fonction_id"))
        controls["groupe_id"] = _dropdown("Groupe", options["groupes"], values.get("groupe_id"), optional=True)
        controls["type_employe"] = _choice("Type employe *", EMPLOYEE_TYPES, values.get("type_employe"))
        controls["statut_employe"] = _choice("Statut employe *", EMPLOYEE_STATUSES, values.get("statut_employe"))
        controls["numero_badge"] = _text_field("Numero badge", values.get("numero_badge"), "Entrez le numero badge")
        controls["statut_badge"] = _choice("Statut badge *", BADGE_STATUSES, values.get("statut_badge"))
        controls["date_remise"] = _text_field("Date remise badge", values.get("date_remise"), "AAAA-MM-JJ")
        controls["date_expiration_badge"] = _text_field(
            "Expiration badge",
            values.get("date_expiration_badge") or "Automatique: date remise + 2 ans",
            disabled=True,
        )
        controls["site_id"] = _dropdown("Site *", options["sites"], values.get("site_id"))
        controls["shift_id"] = _dropdown("Shift *", options["shifts"], values.get("shift_id"))

        form_area.controls = [
            _section(
                "Informations personnelles",
                ft.Icons.BADGE_OUTLINED,
                [
                    _cell(controls["matricule"], 4),
                    _cell(controls["nom"], 4),
                    _cell(controls["prenom"], 4),
                ],
            ),
            _section(
                "Informations professionnelles",
                ft.Icons.WORK_OUTLINE,
                [
                    _cell(controls["fonction_id"], 6),
                    _cell(controls["groupe_id"], 6),
                    _cell(controls["type_employe"], 6),
                    _cell(controls["statut_employe"], 6),
                ],
            ),
            _section(
                "Badge & acces",
                ft.Icons.SHIELD_OUTLINED,
                [
                    _cell(controls["numero_badge"], 3),
                    _cell(controls["statut_badge"], 3),
                    _cell(controls["date_remise"], 3),
                    _cell(controls["date_expiration_badge"], 3),
                    ft.Container(
                        col=12,
                        bgcolor="#0B3158",
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=10, vertical=7),
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.INFO_OUTLINE, color="#60A5FA", size=16),
                                ft.Text("Expiration automatique: date remise badge + 2 ans.", color="#60A5FA", size=10),
                            ],
                            spacing=7,
                        ),
                    ),
                ],
            ),
            _section(
                "Affectation & planning",
                ft.Icons.CALENDAR_MONTH_OUTLINED,
                [
                    _cell(controls["site_id"], 6),
                    _cell(controls["shift_id"], 6),
                ],
            ),
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=12,
                content=ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            col={"xs": 12, "md": 5},
                            content=ft.Row(
                                controls=[
                                    ft.OutlinedButton(
                                        "Annuler" if on_saved is not None else ("Recharger" if is_edit else "Effacer"),
                                        icon=ft.Icons.CLOSE if on_saved is not None else ft.Icons.REFRESH_OUTLINED,
                                        style=ft.ButtonStyle(color="#C7D4E3"),
                                        on_click=(lambda event: on_saved()) if on_saved is not None else clear_form,
                                    ),
                                    status,
                                ],
                                spacing=10,
                                wrap=True,
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "md": 7},
                            content=ft.Row(
                                controls=[
                                    ft.OutlinedButton(
                                        "Enregistrer & ajouter un autre",
                                        icon=ft.Icons.PERSON_ADD_ALT_1_OUTLINED,
                                        visible=not is_edit,
                                        style=ft.ButtonStyle(color="#60A5FA"),
                                        on_click=lambda event: save_employee(event, keep_open=True),
                                    ),
                                    ft.ElevatedButton(
                                        "Enregistrer",
                                        icon=ft.Icons.SAVE_OUTLINED,
                                        bgcolor=PRIMARY,
                                        color="#FFFFFF",
                                        on_click=save_employee,
                                    ),
                                ],
                                spacing=10,
                                wrap=True,
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ),
                    ],
                    spacing=10,
                    run_spacing=10,
                ),
            ),
        ]

    root = ft.Container(
        bgcolor=BG,
        expand=True,
        content=ft.Column(
            controls=[
                _form_header(is_edit, on_saved),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            col={"xs": 12, "lg": 3, "xl": 2},
                            content=_form_navigation(),
                        ),
                        ft.Container(
                            col={"xs": 12, "lg": 9, "xl": 10},
                            content=form_area,
                        ),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    render_form(initial_values())
    return root


def _form_header(is_edit: bool, on_saved: Any | None) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Retour",
                    icon_color="#C7D4E3",
                    visible=on_saved is not None,
                    on_click=(lambda event: on_saved()) if on_saved is not None else None,
                ),
                ft.Column(
                    controls=[
                        ft.Text("Modifier un employe" if is_edit else "Ajouter un employe", color=TEXT, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Mise a jour de la fiche employe." if is_edit else "Creation d'une nouvelle fiche employe.",
                            color=MUTED,
                            size=11,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.OutlinedButton(
                    "Historique des employes",
                    icon=ft.Icons.HISTORY_OUTLINED,
                    style=ft.ButtonStyle(color="#C7D4E3"),
                    visible=on_saved is not None,
                    on_click=(lambda event: on_saved()) if on_saved is not None else None,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _form_navigation() -> ft.Control:
    entries = [
        ("Informations personnelles", ft.Icons.PERSON_OUTLINE, True),
        ("Informations professionnelles", ft.Icons.WORK_OUTLINE, False),
        ("Badge & acces", ft.Icons.BADGE_OUTLINED, False),
        ("Affectation & planning", ft.Icons.CALENDAR_MONTH_OUTLINED, False),
        ("Resume", ft.Icons.FACT_CHECK_OUTLINED, False),
    ]
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[
                ft.Text("Informations rapides", color=TEXT, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Champs obligatoires *", color=MUTED, size=10),
                ft.Divider(height=1, color=BORDER),
                *[
                    ft.Container(
                        bgcolor=PRIMARY if active else FIELD,
                        border_radius=7,
                        padding=ft.padding.symmetric(horizontal=10, vertical=10),
                        content=ft.Row(
                            controls=[
                                ft.Icon(icon, color="#FFFFFF" if active else MUTED, size=17),
                                ft.Text(label, color="#FFFFFF" if active else "#C7D4E3", size=11),
                            ],
                            spacing=8,
                        ),
                    )
                    for label, icon, active in entries
                ],
                ft.Container(height=10),
                ft.Container(
                    bgcolor=FIELD,
                    border=ft.border.all(1, BORDER),
                    border_radius=8,
                    padding=14,
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, color="#60A5FA", size=28),
                            ft.Text("Donnees securisees", color="#60A5FA", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Les informations sont protegees et conservees dans la base locale.",
                                color=MUTED,
                                size=9,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=7,
                    ),
                ),
            ],
            spacing=8,
        ),
    )


def _section(title: str, icon: str, fields: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icon, color="#60A5FA", size=18),
                        ft.Text(title, color=TEXT, size=14, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=8,
                ),
                ft.Divider(height=1, color=BORDER),
                ft.ResponsiveRow(controls=fields, spacing=12, run_spacing=12),
            ],
            spacing=10,
        ),
    )


def _cell(control: ft.Control, columns: int) -> ft.Control:
    return ft.Container(control, col={"xs": 12, "md": columns})


def _first_option(options: list[dict[str, Any]]) -> str | None:
    return str(options[0]["value"]) if options else None


def _text_field(label: str, value: Any, hint: str = "", disabled: bool = False) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=str(value or ""),
        hint_text=hint,
        disabled=disabled,
        bgcolor=FIELD,
        color=TEXT,
        border_color=BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=MUTED),
        hint_style=ft.TextStyle(color="#647A91"),
    )


def _dropdown(label: str, options: list[dict[str, Any]], value: Any, optional: bool = False) -> ft.Dropdown:
    dropdown_options = [ft.dropdown.Option("", "-")] if optional else []
    dropdown_options.extend(ft.dropdown.Option(str(option["value"]), str(option["label"])) for option in options)
    return ft.Dropdown(
        label=label,
        value=str(value) if value not in ("", None) else ("" if optional else None),
        options=dropdown_options,
        bgcolor=FIELD,
        color=TEXT,
        border_color=BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=MUTED),
    )


def _choice(label: str, choices: list[str], value: Any) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=str(value or choices[0]),
        options=[ft.dropdown.Option(choice) for choice in choices],
        bgcolor=FIELD,
        color=TEXT,
        border_color=BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=MUTED),
    )
