from __future__ import annotations

from datetime import date, timedelta
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
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


MODULE_LABELS = {
    "Dashboard": "Tableau de bord",
    "Referentials": "Referentiels",
    "EmployeeManagement": "Gestion employes",
    "TrainingManagement": "Gestion formation",
    "ToolboxTalk": "Toolbox Talk",
    "TimeSheet": "TimeSheet",
    "MonthlyTimesheet": "TimeSheet 1-25",
    "Ppe": "Gestion des EPI",
    "MaintenanceActions": "Maintenance & Actions",
    "Alerts": "Alertes & Rapports",
    "AiAssistant": "Assistant IA",
    "Settings": "Parametres",
    "Admin": "Administrateur",
}


def admin_page(current_user: dict[str, Any] | None = None, page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"editing_id": None, "role_checks": {}, "view": "overview"}
    actor = str((current_user or {}).get("username") or "system")
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    users_area = ft.Column(spacing=10)
    roles_area = ft.Column(spacing=8)
    backups_area = ft.Column(spacing=8)
    audit_area = ft.Column(spacing=8)
    overview_activity = ft.Column(spacing=6)
    overview_users = ft.Column(spacing=6)
    overview_backups = ft.Column(spacing=6)
    content_area = ft.Container()
    nav_buttons: dict[str, ft.TextButton] = {}

    search_field = ft.TextField(
        label="Recherche utilisateur",
        prefix_icon=ft.Icons.SEARCH,
        width=260,
        bgcolor="#0C1C2E",
        color="#FFFFFF",
        border_color="#1E3A56",
    )
    role_filter = _dark_dropdown("Role", 180)
    role_filter.value = "all"
    status_filter = _dark_dropdown("Statut", 160)
    status_filter.value = "all"
    status_filter.options = [
        ft.dropdown.Option("all", "Tous"),
        ft.dropdown.Option("actif", "Actifs"),
        ft.dropdown.Option("inactif", "Inactifs"),
    ]
    username_field = _dark_text_field("Nom utilisateur", None)
    password_field = _dark_text_field("Mot de passe", None, password=True)
    role_field = _dark_dropdown("Role", None)
    status_field = ft.Dropdown(
        label="Statut",
        value="actif",
        width=None,
        bgcolor="#0C1C2E",
        color="#FFFFFF",
        border_color="#1E3A56",
        options=[
            ft.dropdown.Option("actif", "Actif"),
            ft.dropdown.Option("inactif", "Inactif"),
        ],
    )
    backup_label_field = _dark_text_field("Libelle sauvegarde", 260)

    save_button = ft.ElevatedButton(
        "Creer",
        icon=ft.Icons.PERSON_ADD_ALT_1_OUTLINED,
        bgcolor=PRIMARY,
        color="#FFFFFF",
    )
    reset_button = ft.OutlinedButton(
        "Nouveau",
        icon=ft.Icons.ADD_OUTLINED,
        style=ft.ButtonStyle(color="#C7D4E3"),
    )

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
        role_filter.options = [ft.dropdown.Option("all", "Tous"), *[ft.dropdown.Option(str(role["nom"]), str(role["nom"])) for role in roles]]
        if roles and not role_field.value:
            role_field.value = str(roles[0]["id_role"])

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            render_summary()
            render_users()
            render_roles()
            render_backups()
            render_audit()
            render_overview()
            render_view()
        except Exception as exc:
            notify(str(exc), DANGER)
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

    def export_users(event: ft.ControlEvent | None = None) -> None:
        rows = list_users(str(search_field.value or ""))
        output = export_rows_xlsx(
            "utilisateurs_orezone.xlsx",
            "Utilisateurs",
            ["Utilisateur", "Role", "Statut", "Creation", "Mise a jour"],
            [
                [
                    row.get("username") or "",
                    row.get("role") or "",
                    row.get("statut") or "",
                    row.get("created_at") or "",
                    row.get("updated_at") or "",
                ]
                for row in rows
            ],
        )
        notify(f"Export utilisateurs cree: {output}", SUCCESS)
        _update()

    def render_summary() -> None:
        summary = get_admin_summary()
        users = list_users()
        admin_count = sum(1 for row in users if row.get("role") == "Administrateur")
        latest = max((str(row.get("created_at") or "") for row in users), default="-")
        summary_row.controls = [
            _summary_chip("Total utilisateurs", summary["users"], PRIMARY, ft.Icons.PEOPLE_ALT_OUTLINED, "Tous les comptes", 100),
            _summary_chip("Utilisateurs actifs", summary["active_users"], SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE, "Comptes operationnels", _ratio(summary["active_users"], summary["users"])),
            _summary_chip("Utilisateurs inactifs", summary["inactive_users"], DANGER, ft.Icons.PERSON_OFF_OUTLINED, "Acces suspendus", _ratio(summary["inactive_users"], summary["users"])),
            _summary_chip("Administrateurs", admin_count, "#8B5CF6", ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, "Comptes privilegies", _ratio(admin_count, summary["users"])),
            _summary_chip("Roles definis", summary["roles"], WARNING, ft.Icons.KEY_OUTLINED, "Total des roles", 100),
            _summary_chip("Derniere creation", latest[:10] if latest != "-" else "-", "#0891B2", ft.Icons.CALENDAR_MONTH_OUTLINED, "Compte le plus recent", 100),
        ]

    def render_users() -> None:
        rows = list_users(str(search_field.value or ""))
        selected_role = str(role_filter.value or "all")
        selected_status = str(status_filter.value or "all")
        rows = [
            row
            for row in rows
            if (selected_role == "all" or row.get("role") == selected_role)
            and (selected_status == "all" or row.get("statut") == selected_status)
        ]
        users_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"Utilisateurs ({len(rows)})", size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF", expand=True),
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            _user_list_header(),
            ft.Column(
                controls=[
                    _user_management_row(
                        row,
                        edit_user,
                        reset_password,
                        set_user_status,
                    )
                    for row in rows
                ],
                spacing=6,
            )
            if rows
            else ft.Text("Aucun utilisateur trouve.", size=12, color="#9DB0C5"),
        ]

    def render_backups() -> None:
        rows = list_backups()
        backups_area.controls = [
            ft.Text("Sauvegardes locales", size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Column(
                controls=[
                    ft.Container(
                        bgcolor="#0C1C2E",
                        border=ft.border.all(1, "#1E3A56"),
                        border_radius=8,
                        padding=10,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.STORAGE_OUTLINED, color=PRIMARY, size=18),
                                ft.Text(str(row["name"]), color="#FFFFFF", weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"{int(row['size']) // 1024} Ko", color="#9DB0C5", width=70),
                                ft.Text(str(row["created_at"]), color="#9DB0C5", width=150),
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
            else ft.Text("Aucune sauvegarde locale.", size=12, color="#9DB0C5"),
        ]

    def render_roles() -> None:
        rows = list_role_permissions()
        roles_area.controls = [
            ft.Text("Roles et acces modules", size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Column(
                controls=[_role_permissions_panel(row, save_role_permissions, state) for row in rows],
                spacing=8,
            )
            if rows
            else ft.Text("Aucun role configure.", size=12, color="#9DB0C5"),
        ]

    def render_audit() -> None:
        rows = list_admin_audit(limit=30)
        audit_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Audit administration", size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF", expand=True),
                    ft.OutlinedButton("Exporter audit", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_admin_audit),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Container(
                        bgcolor="#0C1C2E",
                        border=ft.border.all(1, "#1E3A56"),
                        border_radius=8,
                        padding=10,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.MANAGE_SEARCH_OUTLINED, color=PRIMARY, size=18),
                                ft.Text(str(row.get("changed_at") or ""), color="#9DB0C5", width=145),
                                ft.Text(str(row.get("action") or ""), color="#FFFFFF", weight=ft.FontWeight.BOLD, width=130),
                                ft.Text(f"{row.get('cible_type') or '-'}:{row.get('cible_id') or '-'}", color="#9DB0C5", width=120),
                                ft.Text(str(row.get("changed_by") or "-"), color=PRIMARY, width=95),
                                ft.Text(str(row.get("nouvelle_valeur") or ""), color="#9DB0C5", expand=True),
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
            else ft.Text("Aucune action auditee.", size=12, color="#9DB0C5"),
        ]

    def render_overview() -> None:
        audit_rows = list_admin_audit(limit=6)
        user_rows = list_users()[:6]
        backup_rows = list_backups()[:6]
        overview_activity.controls = [
            _overview_line(
                str(row.get("action") or "Activite"),
                f"{row.get('changed_by') or 'systeme'} | {row.get('cible_type') or '-'}",
                str(row.get("changed_at") or "")[-8:-3],
                PRIMARY,
                ft.Icons.HISTORY_OUTLINED,
                dark=True,
            )
            for row in audit_rows
        ] or [ft.Text("Aucune activite recente.", color=MUTED, size=11)]
        overview_users.controls = [
            _overview_line(
                str(row.get("username") or "-"),
                str(row.get("role") or "-"),
                str(row.get("statut") or "-").upper(),
                SUCCESS if row.get("statut") == "actif" else WARNING,
                ft.Icons.PERSON_OUTLINE,
                dark=True,
            )
            for row in user_rows
        ] or [ft.Text("Aucun utilisateur.", color=MUTED, size=11)]
        overview_backups.controls = [
            _overview_line(
                str(row.get("name") or "-"),
                str(row.get("created_at") or "-"),
                f"{int(row.get('size') or 0) // 1024} Ko",
                SUCCESS,
                ft.Icons.STORAGE_OUTLINED,
                dark=True,
            )
            for row in backup_rows
        ] or [ft.Text("Aucune sauvegarde.", color=MUTED, size=11)]

    def open_view(key: str) -> None:
        state["view"] = key
        render_view()
        _update()

    def render_view() -> None:
        key = str(state["view"])
        for button_key, button in nav_buttons.items():
            selected = button_key == key
            button.style = ft.ButtonStyle(
                bgcolor=PRIMARY if selected else "#10243A",
                color="#FFFFFF" if selected else "#C7D4E3",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
            )
        builders = {
            "overview": build_overview,
            "users": build_users_view,
            "roles": build_roles_view,
            "backups": build_backups_view,
            "audit": build_audit_view,
        }
        content_area.content = builders.get(key, build_overview)()

    def build_overview() -> ft.Control:
        summary = get_admin_summary()
        activity_trend = _activity_trend(list_admin_audit(limit=500))
        security_items = [
            ("Comptes inactifs", summary["inactive_users"], WARNING, ft.Icons.PERSON_OFF_OUTLINED),
            ("Administrateurs actifs", _active_admin_count(), SUCCESS, ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED),
            ("Actions auditees", summary["audit"], PRIMARY, ft.Icons.SHIELD_OUTLINED),
            ("Derniere sauvegarde", "Disponible" if summary["backups"] else "Absente", SUCCESS if summary["backups"] else DANGER, ft.Icons.BACKUP_OUTLINED),
            ("Statut systeme", "Securise", SUCCESS, ft.Icons.VERIFIED_USER_OUTLINED),
        ]
        return ft.Column(
            controls=[
                ft.Container(
                    bgcolor="#081525",
                    border_radius=8,
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(_admin_dark_panel("Activites recentes", "Dernieres actions administratives.", overview_activity), col={"sm": 12, "lg": 4}),
                                    ft.Container(_admin_dark_panel("Activite systeme - 7 jours", "Volume quotidien des operations auditees.", activity_trend), col={"sm": 12, "lg": 5}),
                                    ft.Container(_admin_dark_panel("Securite systeme", "Etat des acces et protections.", ft.Column([_security_line(*item, dark=True) for item in security_items], spacing=6)), col={"sm": 12, "lg": 3}),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(_admin_dark_panel("Utilisateurs recents", "Comptes et roles actuellement configures.", overview_users), col={"sm": 12, "lg": 7}),
                                    ft.Container(_admin_dark_panel("Sauvegardes recentes", "Copies locales disponibles.", overview_backups), col={"sm": 12, "lg": 5}),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(_quick_admin_actions(open_view, create_backup, dark=True), col={"sm": 12, "lg": 7}),
                                    ft.Container(_admin_assistant_panel(dark=True), col={"sm": 12, "lg": 5}),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=10,
        )

    def build_users_view() -> ft.Control:
        users = list_users()
        summary = get_admin_summary()
        latest = max(users, key=lambda row: str(row.get("created_at") or ""), default={})
        return ft.Column(
            controls=[
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            _admin_dark_panel(
                                "Gestion utilisateur",
                                "Creer ou modifier un compte et son role.",
                                ft.Column(
                                    controls=[
                                        ft.ResponsiveRow(
                                            controls=[
                                                ft.Container(username_field, col={"sm": 12, "md": 6}),
                                                ft.Container(password_field, col={"sm": 12, "md": 6}),
                                                ft.Container(role_field, col={"sm": 12, "md": 6}),
                                                ft.Container(status_field, col={"sm": 12, "md": 6}),
                                            ],
                                            spacing=8,
                                            run_spacing=8,
                                        ),
                                        ft.Row(
                                            controls=[
                                                save_button,
                                                reset_button,
                                                ft.OutlinedButton(
                                                    "Reinitialiser mot de passe",
                                                    icon=ft.Icons.LOCK_RESET_OUTLINED,
                                                    style=ft.ButtonStyle(color=WARNING),
                                                    on_click=lambda event: reset_password(int(state["editing_id"])) if state["editing_id"] else notify("Selectionne un utilisateur.", WARNING),
                                                ),
                                                ft.OutlinedButton(
                                                    "Activer / Desactiver",
                                                    icon=ft.Icons.PERSON_OFF_OUTLINED,
                                                    style=ft.ButtonStyle(color=DANGER),
                                                    on_click=lambda event: _toggle_selected_user(state, list_users(), set_user_status, notify),
                                                ),
                                            ],
                                            spacing=8,
                                            wrap=True,
                                        ),
                                        ft.Text(
                                            "Selectionne une ligne pour modifier le compte ou reinitialiser son mot de passe.",
                                            size=10,
                                            color="#9DB0C5",
                                        ),
                                    ],
                                    spacing=8,
                                ),
                            ),
                            col={"sm": 12, "lg": 7},
                        ),
                        ft.Container(
                            _admin_dark_panel(
                                "Informations rapides",
                                "Synthese des comptes utilisateurs.",
                                _user_quick_info(summary, latest),
                            ),
                            col={"sm": 12, "lg": 5},
                        ),
                    ],
                    spacing=10,
                    run_spacing=10,
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            _admin_dark_panel(
                                "Liste des utilisateurs",
                                "Liste des comptes, roles et statuts.",
                                ft.Column(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                search_field,
                                                role_filter,
                                                status_filter,
                                                ft.ElevatedButton("Filtrer", icon=ft.Icons.FILTER_ALT_OUTLINED, on_click=refresh),
                                                ft.OutlinedButton("Exporter", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_users),
                                            ],
                                            spacing=8,
                                            wrap=True,
                                        ),
                                        users_area,
                                    ],
                                    spacing=10,
                                ),
                            ),
                            col={"sm": 12, "lg": 9},
                        ),
                        ft.Container(
                            ft.Column(
                                controls=[
                                    _user_actions_panel(open_view, create_backup),
                                    _admin_assistant_panel(dark=True),
                                ],
                                spacing=10,
                            ),
                            col={"sm": 12, "lg": 3},
                        ),
                    ],
                    spacing=10,
                    run_spacing=10,
                ),
            ],
            spacing=10,
        )

    def build_roles_view() -> ft.Control:
        return _admin_dark_panel("Roles et permissions", "Configurer les modules accessibles a chaque role.", roles_area)

    def build_backups_view() -> ft.Control:
        return _admin_dark_panel(
            "Sauvegardes base de donnees",
            "Creer, consulter ou restaurer une sauvegarde locale.",
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            backup_label_field,
                            ft.ElevatedButton("Creer sauvegarde", icon=ft.Icons.BACKUP_OUTLINED, on_click=create_backup),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    backups_area,
                ],
                spacing=10,
            ),
        )

    def build_audit_view() -> ft.Control:
        return _admin_dark_panel("Audit et activites", "Journal complet des operations administratives.", audit_area)

    save_button.on_click = save_user
    reset_button.on_click = clear_form
    search_field.on_change = refresh
    role_filter.on_select = refresh
    status_filter.on_select = refresh
    nav_items = [
        ("overview", "Vue d'ensemble", ft.Icons.SPACE_DASHBOARD_OUTLINED),
        ("users", "Utilisateurs", ft.Icons.PEOPLE_ALT_OUTLINED),
        ("roles", "Roles & permissions", ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED),
        ("backups", "Sauvegardes", ft.Icons.BACKUP_OUTLINED),
        ("audit", "Audit & activites", ft.Icons.MANAGE_SEARCH_OUTLINED),
    ]
    nav_buttons = {
        key: ft.TextButton(
            width=170,
            content=ft.Row(
                controls=[ft.Icon(icon, size=17), ft.Text(label, size=11, weight=ft.FontWeight.BOLD)],
                spacing=6,
            ),
            on_click=lambda event, target=key: open_view(target),
        )
        for key, label, icon in nav_items
    }
    root = ft.Container(
        bgcolor="#071321",
        border_radius=8,
        padding=10,
        expand=True,
        content=ft.Column(
            controls=[
                _admin_header(actor, open_view),
                ft.Container(
                    bgcolor="#081525",
                    border_radius=8,
                    padding=8,
                    content=ft.Row(
                        controls=list(nav_buttons.values()),
                        spacing=6,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ),
                ft.Container(
                    bgcolor="#081525",
                    border=ft.border.all(1, "#1E3A56"),
                    border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "Supervision des comptes et des acces",
                                        color="#C7D4E3",
                                        size=11,
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.SYNC_OUTLINED,
                                        tooltip="Actualiser",
                                        icon_color="#C7D4E3",
                                        on_click=refresh,
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            summary_row,
                        ],
                        spacing=10,
                    ),
                ),
                content_area,
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
    load_roles()
    refresh()
    return root


def _summary_chip(
    label: str,
    value: Any,
    color: str,
    icon: str,
    subtitle: str,
    progress: int,
) -> ft.Control:
    return ft.Container(
        bgcolor="#10243A",
        border=ft.border.all(1, "#1E3A56"),
        border_radius=8,
        padding=11,
        content=ft.Column(
            controls=[
                ft.Row(
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
                                ft.Text(label, size=9, color="#9DB0C5"),
                                ft.Text(str(value), size=18, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Text(subtitle, size=8, color="#7F94AA", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.ProgressBar(value=max(min(progress, 100), 0) / 100, color=color, bgcolor="#0C1C2E", height=4),
            ],
            spacing=5,
        ),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _ratio(value: int, total: int) -> int:
    return round((value / total) * 100) if total else 0


def _active_admin_count() -> int:
    return sum(1 for row in list_users() if row.get("role") == "Administrateur" and row.get("statut") == "actif")


def _dark_text_field(label: str, width: int | None, password: bool = False) -> ft.TextField:
    return ft.TextField(
        label=label,
        width=width,
        password=password,
        can_reveal_password=password,
        bgcolor="#0C1C2E",
        color="#FFFFFF",
        border_color="#1E3A56",
        focused_border_color=PRIMARY,
    )


def _dark_dropdown(label: str, width: int | None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        width=width,
        bgcolor="#0C1C2E",
        color="#FFFFFF",
        border_color="#1E3A56",
        focused_border_color=PRIMARY,
    )


def _admin_header(actor: str, open_view: Any) -> ft.Control:
    return ft.Container(
        bgcolor="#0F1F33",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=18, vertical=14),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=42,
                            height=42,
                            bgcolor="#1D4ED8",
                            border_radius=8,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, color="#FFFFFF", size=24),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("Centre de controle Administrateur", color="#FFFFFF", size=20, weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    f"Session : {actor} | Utilisateurs, roles, permissions, securite et sauvegardes.",
                                    color="#B6C5D8",
                                    size=11,
                                ),
                            ],
                            spacing=2,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.ElevatedButton(
                    "Nouvel utilisateur",
                    icon=ft.Icons.PERSON_ADD_ALT_OUTLINED,
                    on_click=lambda event: open_view("users"),
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def _admin_panel(title: str, subtitle: str, content: ft.Control) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[
                ft.Text(title, color=TEXT, size=14, weight=ft.FontWeight.BOLD),
                ft.Text(subtitle, color=MUTED, size=10),
                content,
            ],
            spacing=9,
        ),
    )


def _admin_dark_panel(title: str, subtitle: str, content: ft.Control) -> ft.Control:
    return ft.Container(
        bgcolor="#10243A",
        border=ft.border.all(1, "#1E3A56"),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[
                ft.Text(title, color="#FFFFFF", size=14, weight=ft.FontWeight.BOLD),
                ft.Text(subtitle, color="#9DB0C5", size=10),
                content,
            ],
            spacing=9,
        ),
    )


def _overview_line(title: str, subtitle: str, value: str, color: str, icon: str, dark: bool = False) -> ft.Control:
    return ft.Container(
        bgcolor="#0C1C2E" if dark else "#F8FAFC",
        border=ft.border.all(1, "#1E3A56" if dark else "#E2E8F0"),
        border_radius=8,
        padding=8,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=17),
                ft.Column(
                    controls=[
                        ft.Text(title, color="#FFFFFF" if dark else TEXT, size=11, weight=ft.FontWeight.BOLD, max_lines=1),
                        ft.Text(subtitle, color="#9DB0C5" if dark else MUTED, size=9, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.Text(value, color=color, size=9, weight=ft.FontWeight.BOLD),
            ],
            spacing=7,
        ),
    )


def _security_line(label: str, value: Any, color: str, icon: str, dark: bool = False) -> ft.Control:
    return ft.Container(
        bgcolor="#0C1C2E" if dark else "#F8FAFC",
        border=ft.border.all(1, "#1E3A56" if dark else "#E2E8F0"),
        border_radius=8,
        padding=9,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=17),
                ft.Text(label, color="#E5EDF6" if dark else TEXT, size=11, expand=True),
                ft.Text(str(value), color=color, size=11, weight=ft.FontWeight.BOLD),
            ],
            spacing=7,
        ),
    )


def _activity_trend(rows: list[dict[str, Any]]) -> ft.Control:
    today = date.today()
    days = [(today - timedelta(days=offset)) for offset in range(6, -1, -1)]
    counts = {day.isoformat(): 0 for day in days}
    for row in rows:
        changed_at = str(row.get("changed_at") or "")[:10]
        if changed_at in counts:
            counts[changed_at] += 1
    maximum = max([*counts.values(), 1])
    return ft.Container(
        height=150,
        padding=ft.padding.only(top=8),
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(str(counts[day.isoformat()]), color="#C7D4E3", size=9),
                        ft.Container(
                            width=28,
                            height=max(8, round((counts[day.isoformat()] / maximum) * 92)),
                            bgcolor=PRIMARY,
                            border_radius=4,
                        ),
                        ft.Text(day.strftime("%d/%m"), color="#9DB0C5", size=8),
                    ],
                    spacing=3,
                    alignment=ft.MainAxisAlignment.END,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
                for day in days
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
    )


def _audit_snapshot(summary: dict[str, int], dark: bool = False) -> ft.Control:
    items = [
        ("Actions enregistrees", summary["audit"], PRIMARY),
        ("Utilisateurs actifs", summary["active_users"], SUCCESS),
        ("Utilisateurs inactifs", summary["inactive_users"], WARNING),
        ("Roles configures", summary["roles"], PRIMARY),
        ("Sauvegardes", summary["backups"], SUCCESS),
    ]
    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text(label, color="#9DB0C5" if dark else MUTED, size=11, expand=True),
                    ft.Text(str(value), color=color, size=13, weight=ft.FontWeight.BOLD),
                ]
            )
            for label, value, color in items
        ],
        spacing=8,
    )


def _quick_admin_actions(open_view: Any, create_backup: Any, dark: bool = False) -> ft.Control:
    actions = [
        ("Nouvel utilisateur", ft.Icons.PERSON_ADD_ALT_OUTLINED, lambda event: open_view("users"), PRIMARY),
        ("Gerer permissions", ft.Icons.LOCK_OUTLINED, lambda event: open_view("roles"), WARNING),
        ("Sauvegarder", ft.Icons.BACKUP_OUTLINED, create_backup, SUCCESS),
        ("Voir audit", ft.Icons.MANAGE_SEARCH_OUTLINED, lambda event: open_view("audit"), PRIMARY),
    ]
    panel_builder = _admin_dark_panel if dark else _admin_panel
    return panel_builder(
        "Actions rapides",
        "Operations administratives frequentes.",
        ft.Row(
            controls=[
                ft.Container(
                    width=140,
                    height=72,
                    bgcolor="#0C1C2E" if dark else "#F8FAFC",
                    border=ft.border.all(1, "#1E3A56" if dark else "#E2E8F0"),
                    border_radius=8,
                    ink=True,
                    on_click=handler,
                    padding=9,
                    content=ft.Column(
                        controls=[
                            ft.Icon(icon, color=color, size=21),
                            ft.Text(label, color="#FFFFFF" if dark else TEXT, size=10, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
                for label, icon, handler, color in actions
            ],
            spacing=7,
            wrap=True,
        ),
    )


def _admin_assistant_panel(dark: bool = False) -> ft.Control:
    prompts = [
        "Combien d'utilisateurs actifs aujourd'hui ?",
        "Montre les sauvegardes du mois.",
        "Quels roles ont acces aux Timesheets ?",
        "Genere le rapport d'audit.",
    ]
    panel_builder = _admin_dark_panel if dark else _admin_panel
    return panel_builder(
        "Assistant IA Administrateur",
        "Questions suggerees pour le pilotage.",
        ft.Column(
            controls=[
                ft.Container(
                    bgcolor="#17213D" if dark else "#F5F3FF",
                    border=ft.border.all(1, "#4338CA" if dark else "#DDD6FE"),
                    border_radius=8,
                    padding=9,
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color="#8B5CF6", size=17),
                            ft.Text(prompt, color="#E5EDF6" if dark else TEXT, size=10, expand=True),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color="#8B5CF6", size=17),
                        ],
                        spacing=7,
                    ),
                )
                for prompt in prompts
            ],
            spacing=6,
        ),
    )


def _status_badge(status: str) -> ft.Control:
    color = SUCCESS if status == "actif" else WARNING
    return ft.Container(
        bgcolor="#0C1C2E",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(status, size=12, color=color, weight=ft.FontWeight.BOLD),
    )


def _user_list_header() -> ft.Control:
    return ft.Container(
        bgcolor="#17304A",
        border=ft.border.all(1, "#28506F"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
        content=ft.Row(
            controls=[
                ft.Container(width=38),
                _user_header_cell("Utilisateur", 3),
                _user_header_cell("Role & acces", 3),
                _user_header_cell("Statut", 2),
                _user_header_cell("Creation / mise a jour", 3),
                ft.Container(width=136, content=ft.Text("Actions", color="#FFFFFF", size=10, weight=ft.FontWeight.BOLD)),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _user_header_cell(label: str, expand: int) -> ft.Control:
    return ft.Container(
        expand=expand,
        content=ft.Text(label, color="#FFFFFF", size=10, weight=ft.FontWeight.BOLD),
    )


def _user_management_row(
    row: dict[str, Any],
    edit_callback: Any,
    reset_callback: Any,
    status_callback: Any,
) -> ft.Control:
    active = str(row.get("statut") or "") == "actif"
    username = str(row.get("username") or "-")
    role = str(row.get("role") or "-")
    created = str(row.get("created_at") or "-")
    updated = str(row.get("updated_at") or "-")
    return ft.Container(
        bgcolor="#0C1C2E",
        border=ft.border.all(1, "#1E3A56"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
        ink=True,
        on_click=lambda event: edit_callback(row),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=38,
                    height=38,
                    bgcolor="#17304A",
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        username[:2].upper(),
                        color="#60A5FA",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                _user_value_cell(username, "Compte OREZONE", 3, "#FFFFFF"),
                _user_value_cell(role, str(row.get("role_description") or "Acces configure"), 3, "#C7D4E3"),
                ft.Container(expand=2, content=_status_badge("actif" if active else "inactif")),
                _user_value_cell(created, f"Maj: {updated}", 3, "#C7D4E3"),
                ft.Container(
                    width=136,
                    content=ft.Row(
                        controls=[
                            _compact_action(
                                ft.Icons.EDIT_OUTLINED,
                                "Modifier",
                                PRIMARY,
                                lambda event: edit_callback(row),
                            ),
                            _compact_action(
                                ft.Icons.LOCK_RESET_OUTLINED,
                                "Reinitialiser le mot de passe",
                                WARNING,
                                lambda event: reset_callback(int(row["id_user"])),
                            ),
                            _compact_action(
                                ft.Icons.PERSON_OFF_OUTLINED if active else ft.Icons.PERSON_OUTLINED,
                                "Desactiver" if active else "Activer",
                                DANGER if active else SUCCESS,
                                lambda event: status_callback(int(row["id_user"]), not active),
                            ),
                        ],
                        spacing=2,
                    ),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _user_value_cell(title: str, subtitle: str, expand: int, color: str) -> ft.Control:
    return ft.Container(
        expand=expand,
        content=ft.Column(
            controls=[
                ft.Text(title, color=color, size=11, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(subtitle, color="#7F94AA", size=9, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ],
            spacing=1,
        ),
    )


def _compact_action(icon: str, tooltip: str, color: str, handler: Any) -> ft.Control:
    return ft.IconButton(
        icon=icon,
        tooltip=tooltip,
        icon_color=color,
        icon_size=17,
        width=38,
        height=38,
        on_click=handler,
    )


def _toggle_selected_user(
    state: dict[str, Any],
    users: list[dict[str, Any]],
    status_callback: Any,
    notify: Any,
) -> None:
    selected_id = state.get("editing_id")
    selected = next((row for row in users if int(row["id_user"]) == int(selected_id or 0)), None)
    if selected is None:
        notify("Selectionne un utilisateur.", WARNING)
        return
    status_callback(int(selected["id_user"]), str(selected.get("statut") or "") != "actif")


def _user_quick_info(summary: dict[str, int], latest: dict[str, Any]) -> ft.Control:
    items = [
        ("Total utilisateurs", summary["users"], PRIMARY, ft.Icons.PEOPLE_ALT_OUTLINED),
        ("Utilisateurs actifs", summary["active_users"], SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
        ("Utilisateurs inactifs", summary["inactive_users"], DANGER, ft.Icons.PERSON_OFF_OUTLINED),
        ("Derniere creation", str(latest.get("created_at") or "-"), "#0891B2", ft.Icons.CALENDAR_MONTH_OUTLINED),
        ("Roles configures", summary["roles"], WARNING, ft.Icons.KEY_OUTLINED),
    ]
    return ft.Column(
        controls=[_security_line(*item, dark=True) for item in items],
        spacing=6,
    )


def _user_actions_panel(open_view: Any, create_backup: Any) -> ft.Control:
    actions = [
        ("Nouvel utilisateur", ft.Icons.PERSON_ADD_ALT_OUTLINED, lambda event: open_view("users"), PRIMARY),
        ("Permissions", ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, lambda event: open_view("roles"), "#8B5CF6"),
        ("Sauvegarder", ft.Icons.BACKUP_OUTLINED, create_backup, SUCCESS),
        ("Audit", ft.Icons.MANAGE_SEARCH_OUTLINED, lambda event: open_view("audit"), WARNING),
    ]
    return _admin_dark_panel(
        "Actions rapides",
        "Operations liees aux comptes.",
        ft.ResponsiveRow(
            controls=[
                ft.Container(
                    col={"sm": 6},
                    bgcolor="#0C1C2E",
                    border=ft.border.all(1, "#1E3A56"),
                    border_radius=8,
                    ink=True,
                    on_click=handler,
                    padding=9,
                    content=ft.Column(
                        controls=[
                            ft.Icon(icon, color=color, size=20),
                            ft.Text(label, color="#FFFFFF", size=9, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
                for label, icon, handler, color in actions
            ],
            spacing=6,
            run_spacing=6,
        ),
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
            label_style=ft.TextStyle(color="#C7D4E3", size=11),
            active_color=PRIMARY,
            check_color="#FFFFFF",
        )
    state["role_checks"][role_id] = checks
    return ft.ExpansionTile(
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, color=PRIMARY, size=18),
                ft.Text(role_name, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(modules)} module(s)", color="#9DB0C5", size=12),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        subtitle=ft.Text(str(row.get("description") or "-"), color="#9DB0C5", size=11),
        bgcolor="#0C1C2E",
        collapsed_bgcolor="#0C1C2E",
        text_color="#FFFFFF",
        icon_color="#C7D4E3",
        collapsed_text_color="#FFFFFF",
        collapsed_icon_color="#C7D4E3",
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
