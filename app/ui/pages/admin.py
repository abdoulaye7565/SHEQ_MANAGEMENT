from __future__ import annotations

from typing import Any

import flet as ft

from app.services import (
    create_database_backup,
    create_user,
    export_rows_xlsx,
    get_admin_summary,
    get_role_modules,
    list_admin_audit,
    list_backups,
    list_role_permissions,
    list_roles,
    list_users,
    reset_user_password,
    restore_database_backup,
    update_role_modules,
    update_user,
    update_user_status,
)
from app.services.admin_service import ALL_MODULES
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


MODULE_LABELS = {
    "Dashboard": "Tableau de bord",
    "Referentials": "Referentiels",
    "EmployeeManagement": "Gestion employes",
    "TrainingManagement": "Gestion formation",
    "TimeSheet": "TimeSheet",
    "Ppe": "Gestion des EPI",
    "Alerts": "Alertes",
    "Reports": "Rapports",
    "Admin": "Administration",
}


def admin_page(current_user: dict[str, Any] | None = None, page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"editing_id": None, "role_checks": {}}
    actor = str((current_user or {}).get("username") or "system")
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=8, wrap=True)
    users_area = ft.Column(spacing=10)
    roles_area = ft.Column(spacing=8)
    backups_area = ft.Column(spacing=8)
    audit_area = ft.Column(spacing=8)

    search_field = ft.TextField(label="Recherche utilisateur", prefix_icon=ft.Icons.SEARCH, width=260)
    username_field = ft.TextField(label="Nom utilisateur", width=220)
    password_field = ft.TextField(label="Mot de passe", password=True, can_reveal_password=True, width=220)
    role_field = ft.Dropdown(label="Role", width=240)
    status_field = ft.Dropdown(
        label="Statut",
        value="actif",
        width=150,
        options=[
            ft.dropdown.Option("actif", "Actif"),
            ft.dropdown.Option("inactif", "Inactif"),
        ],
    )
    backup_label_field = ft.TextField(label="Libelle sauvegarde", width=260)

    save_button = ft.ElevatedButton("Creer", icon=ft.Icons.PERSON_ADD_ALT_1_OUTLINED)
    reset_button = ft.OutlinedButton("Nouveau", icon=ft.Icons.ADD_OUTLINED)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color
        show_feedback(page, message, color)

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def load_roles() -> None:
        roles = list_roles()
        role_field.options = [ft.dropdown.Option(str(role["id_role"]), str(role["nom"])) for role in roles]
        if roles and not role_field.value:
            role_field.value = str(roles[0]["id_role"])

    def refresh(event: ft.ControlEvent | None = None) -> None:
        render_summary()
        render_users()
        render_roles()
        render_backups()
        render_audit()
        _update()

    def clear_form(event: ft.ControlEvent | None = None) -> None:
        state["editing_id"] = None
        username_field.value = ""
        password_field.value = ""
        password_field.disabled = False
        status_field.value = "actif"
        save_button.text = "Creer"
        save_button.icon = ft.Icons.PERSON_ADD_ALT_1_OUTLINED
        notify("Formulaire pret.", MUTED)
        _update()

    def save_user(event: ft.ControlEvent | None = None) -> None:
        values = {
            "username": username_field.value,
            "password": password_field.value,
            "role_id": role_field.value,
            "statut": status_field.value,
        }
        try:
            if state["editing_id"] is None:
                create_user(values, changed_by=actor)
                notify("Utilisateur cree.", SUCCESS)
            else:
                update_user(int(state["editing_id"]), values, changed_by=actor)
                notify("Utilisateur modifie.", SUCCESS)
            clear_form()
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_user(row: dict[str, Any]) -> None:
        state["editing_id"] = int(row["id_user"])
        username_field.value = str(row["username"])
        role_field.value = str(row["role_id"])
        status_field.value = str(row["statut"])
        password_field.value = ""
        password_field.disabled = True
        save_button.text = "Enregistrer"
        save_button.icon = ft.Icons.SAVE_OUTLINED
        notify("Utilisateur charge pour modification.", PRIMARY)
        _update()

    def set_user_status(user_id: int, active: bool) -> None:
        try:
            update_user_status(user_id, "actif" if active else "inactif", changed_by=actor)
            notify("Statut utilisateur mis a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def reset_password(user_id: int) -> None:
        try:
            password = str(password_field.value or "")
            reset_user_password(user_id, password, changed_by=actor)
            password_field.value = ""
            notify("Mot de passe reinitialise avec la valeur du champ mot de passe.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def create_backup(event: ft.ControlEvent | None = None) -> None:
        try:
            output = create_database_backup(backup_label_field.value, changed_by=actor)
            backup_label_field.value = ""
            notify(f"Sauvegarde creee: {output}", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def restore_backup(name: str) -> None:
        try:
            safety = restore_database_backup(name, changed_by=actor)
            notify(f"Base restauree. Copie avant restauration: {safety}", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_role_permissions(role_id: int) -> None:
        controls = state["role_checks"].get(role_id, {})
        selected = [module for module, control in controls.items() if bool(control.value)]
        try:
            update_role_modules(role_id, selected, changed_by=actor)
            notify("Permissions du role mises a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_admin_audit(event: ft.ControlEvent | None = None) -> None:
        rows = list_admin_audit(limit=10000)
        output = export_rows_xlsx(
            "audit_administration_orezone.xlsx",
            "Audit Admin",
            ["Date", "Action", "Cible", "Ancienne valeur", "Nouvelle valeur", "Utilisateur", "Commentaire"],
            [
                [
                    row.get("changed_at") or "",
                    row.get("action") or "",
                    f"{row.get('cible_type') or ''}:{row.get('cible_id') or ''}",
                    row.get("ancienne_valeur") or "",
                    row.get("nouvelle_valeur") or "",
                    row.get("changed_by") or "",
                    row.get("commentaire") or "",
                ]
                for row in rows
            ],
        )
        notify(f"Export audit cree: {output}", SUCCESS)
        _update()

    def render_summary() -> None:
        summary = get_admin_summary()
        summary_row.controls = [
            _summary_chip("Utilisateurs", summary["users"], PRIMARY, ft.Icons.PEOPLE_ALT_OUTLINED),
            _summary_chip("Actifs", summary["active_users"], SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _summary_chip("Inactifs", summary["inactive_users"], WARNING, ft.Icons.PERSON_OFF_OUTLINED),
            _summary_chip("Roles", summary["roles"], PRIMARY, ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED),
            _summary_chip("Backups", summary["backups"], SUCCESS, ft.Icons.BACKUP_OUTLINED),
            _summary_chip("Audit", summary["audit"], WARNING, ft.Icons.MANAGE_SEARCH_OUTLINED),
        ]

    def render_users() -> None:
        rows = list_users(str(search_field.value or ""))
        users_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"Utilisateurs ({len(rows)})", size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Utilisateur")),
                            ft.DataColumn(ft.Text("Role")),
                            ft.DataColumn(ft.Text("Statut")),
                            ft.DataColumn(ft.Text("Creation")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(str(row["username"]), weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row["role"]))),
                                    ft.DataCell(_status_badge(str(row["statut"]))),
                                    ft.DataCell(ft.Text(str(row.get("created_at") or "-"))),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(
                                                    icon=ft.Icons.EDIT_OUTLINED,
                                                    tooltip="Modifier",
                                                    icon_color=PRIMARY,
                                                    on_click=lambda event, current=row: edit_user(current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.LOCK_RESET_OUTLINED,
                                                    tooltip="Reinitialiser le mot de passe avec le champ mot de passe",
                                                    icon_color=WARNING,
                                                    on_click=lambda event, current=row: reset_password(int(current["id_user"])),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.PERSON_OFF_OUTLINED if row["statut"] == "actif" else ft.Icons.PERSON_OUTLINED,
                                                    tooltip="Desactiver" if row["statut"] == "actif" else "Activer",
                                                    icon_color=DANGER if row["statut"] == "actif" else SUCCESS,
                                                    on_click=lambda event, current=row: set_user_status(
                                                        int(current["id_user"]),
                                                        str(current["statut"]) != "actif",
                                                    ),
                                                ),
                                            ],
                                            spacing=0,
                                        )
                                    ),
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
            )
            if rows
            else ft.Text("Aucun utilisateur trouve.", size=12, color=MUTED),
        ]

    def render_backups() -> None:
        rows = list_backups()
        backups_area.controls = [
            ft.Text("Sauvegardes locales", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[
                    ft.Container(
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=8,
                        padding=10,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.STORAGE_OUTLINED, color=PRIMARY, size=18),
                                ft.Text(str(row["name"]), color=TEXT, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"{int(row['size']) // 1024} Ko", color=MUTED, width=70),
                                ft.Text(str(row["created_at"]), color=MUTED, width=150),
                                ft.IconButton(
                                    icon=ft.Icons.RESTORE_OUTLINED,
                                    tooltip="Restaurer cette sauvegarde",
                                    icon_color=WARNING,
                                    on_click=lambda event, current=row: restore_backup(str(current["name"])),
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                    for row in rows[:10]
                ],
                spacing=8,
            )
            if rows
            else ft.Text("Aucune sauvegarde locale.", size=12, color=MUTED),
        ]

    def render_roles() -> None:
        rows = list_role_permissions()
        roles_area.controls = [
            ft.Text("Roles et acces modules", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Column(
                controls=[_role_permissions_panel(row, save_role_permissions, state) for row in rows],
                spacing=8,
            )
            if rows
            else ft.Text("Aucun role configure.", size=12, color=MUTED),
        ]

    def render_audit() -> None:
        rows = list_admin_audit(limit=30)
        audit_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Audit administration", size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    ft.OutlinedButton("Exporter audit", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_admin_audit),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Container(
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=8,
                        padding=10,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.MANAGE_SEARCH_OUTLINED, color=PRIMARY, size=18),
                                ft.Text(str(row.get("changed_at") or ""), color=MUTED, width=145),
                                ft.Text(str(row.get("action") or ""), color=TEXT, weight=ft.FontWeight.BOLD, width=130),
                                ft.Text(f"{row.get('cible_type') or '-'}:{row.get('cible_id') or '-'}", color=MUTED, width=120),
                                ft.Text(str(row.get("changed_by") or "-"), color=PRIMARY, width=95),
                                ft.Text(str(row.get("nouvelle_valeur") or ""), color=MUTED, expand=True),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                    for row in rows
                ],
                spacing=8,
            )
            if rows
            else ft.Text("Aucune action auditee.", size=12, color=MUTED),
        ]

    save_button.on_click = save_user
    reset_button.on_click = clear_form
    search_field.on_change = refresh

    root = ft.Column(
        controls=[
            module_header(
                "Administration",
                "Gestion des utilisateurs, roles et sauvegardes locales.",
            ),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                search_field,
                                ft.IconButton(icon=ft.Icons.SYNC_OUTLINED, tooltip="Actualiser", on_click=refresh),
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        summary_row,
                    ],
                    spacing=12,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Utilisateur", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[
                                username_field,
                                password_field,
                                role_field,
                                status_field,
                                save_button,
                                reset_button,
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            "Pour reinitialiser un mot de passe, saisir le nouveau mot de passe puis cliquer sur l'icone reset de la ligne.",
                            size=12,
                            color=MUTED,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=users_area,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=roles_area,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Sauvegarde base de donnees", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[
                                backup_label_field,
                                ft.ElevatedButton("Creer sauvegarde", icon=ft.Icons.BACKUP_OUTLINED, on_click=create_backup),
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        backups_area,
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=audit_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    load_roles()
    refresh()
    return root


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=16),
                ft.Text(label, color=MUTED, size=11),
                ft.Text(str(value), color=color, size=13, weight=ft.FontWeight.BOLD),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _status_badge(status: str) -> ft.Control:
    color = SUCCESS if status == "actif" else WARNING
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(status, size=12, color=color, weight=ft.FontWeight.BOLD),
    )


def _role_card(row: dict[str, Any]) -> ft.Control:
    role_name = str(row["nom"])
    modules = get_role_modules(role_name)
    return ft.Container(
        width=260,
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=12,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, color=PRIMARY, size=18),
                        ft.Text(role_name, color=TEXT, weight=ft.FontWeight.BOLD, expand=True),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(str(row.get("description") or "-"), size=11, color=MUTED),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=14),
                                ft.Text(MODULE_LABELS.get(module, module), size=12, color=TEXT),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        )
                        for module in modules
                    ],
                    spacing=4,
                ),
            ],
            spacing=8,
            tight=True,
        ),
    )


def _role_permissions_panel(row: dict[str, Any], save_callback: object, state: dict[str, Any]) -> ft.Control:
    role_id = int(row["id_role"])
    role_name = str(row["nom"])
    modules = set(row.get("modules") or get_role_modules(role_name))
    checks: dict[str, ft.Checkbox] = {}
    for module in ALL_MODULES:
        disabled = module == "Dashboard" or (role_name == "Administrateur" and module == "Admin")
        checks[module] = ft.Checkbox(
            label=MODULE_LABELS.get(module, module),
            value=module in modules or disabled,
            disabled=disabled,
        )
    state["role_checks"][role_id] = checks
    return ft.ExpansionTile(
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, color=PRIMARY, size=18),
                ft.Text(role_name, color=TEXT, weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(modules)} module(s)", color=MUTED, size=12),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        subtitle=str(row.get("description") or "-"),
        controls_padding=ft.padding.only(left=12, right=12, bottom=12),
        controls=[
            ft.Row(
                controls=list(checks.values()),
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.ElevatedButton(
                        "Enregistrer acces",
                        icon=ft.Icons.SAVE_OUTLINED,
                        on_click=lambda event, target=role_id: save_callback(target),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
    )
