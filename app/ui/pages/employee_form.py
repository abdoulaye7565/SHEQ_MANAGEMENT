from __future__ import annotations

from typing import Any

import flet as ft

from app.services import create_employee, get_employee, get_employee_form_options, update_employee
from app.services.employee_service import BADGE_STATUSES, EMPLOYEE_STATUSES, EMPLOYEE_TYPES
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, SUCCESS


def employee_form_page(
    employee_id: int | None = None,
    on_saved: Any | None = None,
) -> ft.Control:
    options = get_employee_form_options()
    controls: dict[str, ft.Control] = {}
    status = ft.Text("", size=12, color=MUTED)
    form_area = ft.Column(spacing=14)
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
        notify("Fiche rechargee." if is_edit else "Formulaire vide pret.", MUTED)
        root.update()

    def save_employee(event: ft.ControlEvent) -> None:
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
            if on_saved is not None:
                root.update()
                on_saved()
                return
        except ValueError as exc:
            notify(str(exc), DANGER)
        root.update()

    def render_form(values: dict[str, Any]) -> None:
        controls.clear()
        controls["matricule"] = ft.TextField(label="Matricule", value=str(values.get("matricule") or ""))
        controls["nom"] = ft.TextField(label="Nom *", value=str(values.get("nom") or ""))
        controls["prenom"] = ft.TextField(label="Prenom *", value=str(values.get("prenom") or ""))
        controls["nom_complet"] = ft.TextField(label="Nom complet", value="", visible=False)
        controls["numero_badge"] = ft.TextField(label="Numero badge", value=str(values.get("numero_badge") or ""))
        controls["fonction_id"] = _dropdown("Fonction *", options["fonctions"], values.get("fonction_id"))
        controls["site_id"] = _dropdown("Site *", options["sites"], values.get("site_id"))
        controls["groupe_id"] = _dropdown("Groupe", options["groupes"], values.get("groupe_id"), optional=True)
        controls["shift_id"] = _dropdown("Shift *", options["shifts"], values.get("shift_id"))
        controls["type_employe"] = _choice("Type employe *", EMPLOYEE_TYPES, values.get("type_employe"))
        controls["statut_employe"] = _choice("Statut employe *", EMPLOYEE_STATUSES, values.get("statut_employe"))
        controls["statut_badge"] = _choice("Statut badge", BADGE_STATUSES, values.get("statut_badge"))
        controls["date_remise"] = ft.TextField(
            label="Date remise badge",
            hint_text="AAAA-MM-JJ",
            value=str(values.get("date_remise") or ""),
        )
        controls["date_expiration_badge"] = ft.TextField(
            label="Expiration badge",
            value=str(values.get("date_expiration_badge") or "Automatique: date remise + 2 ans"),
            disabled=True,
        )

        form_area.controls = [
            ft.ResponsiveRow(
                controls=[
                    ft.Container(controls["matricule"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["nom"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["prenom"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["numero_badge"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["fonction_id"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["site_id"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["groupe_id"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["shift_id"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["type_employe"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["statut_employe"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["statut_badge"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["date_remise"], col={"sm": 12, "md": 4}),
                    ft.Container(controls["date_expiration_badge"], col={"sm": 12, "md": 4}),
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.Row(
                controls=[
                    ft.ElevatedButton(
                        "Enregistrer" if is_edit else "Ajouter",
                        icon=ft.Icons.SAVE_OUTLINED if is_edit else ft.Icons.PERSON_ADD_ALT_1_OUTLINED,
                        on_click=save_employee,
                    ),
                    ft.OutlinedButton(
                        "Recharger" if is_edit else "Effacer",
                        icon=ft.Icons.REFRESH_OUTLINED if is_edit else ft.Icons.CLEAR_OUTLINED,
                        on_click=clear_form,
                    ),
                    status,
                ],
                spacing=10,
                wrap=True,
            ),
        ]

    root = ft.Column(
        controls=[
            module_header(
                "Modifier un employe" if is_edit else "Ajouter un employe",
                "Mise a jour d'une fiche, du site, du shift, du statut et du badge."
                if is_edit
                else "Creation d'une nouvelle fiche employe.",
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=18,
                content=form_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    render_form(initial_values())
    return root


def _first_option(options: list[dict[str, Any]]) -> str | None:
    return str(options[0]["value"]) if options else None


def _dropdown(label: str, options: list[dict[str, Any]], value: Any, optional: bool = False) -> ft.Dropdown:
    dropdown_options = [ft.dropdown.Option("", "-")] if optional else []
    dropdown_options.extend(ft.dropdown.Option(str(option["value"]), str(option["label"])) for option in options)
    return ft.Dropdown(
        label=label,
        value=str(value) if value not in ("", None) else ("" if optional else None),
        options=dropdown_options,
    )


def _choice(label: str, choices: list[str], value: Any) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=str(value or choices[0]),
        options=[ft.dropdown.Option(choice) for choice in choices],
    )
