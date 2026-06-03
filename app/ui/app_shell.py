import flet as ft

from app.services import authenticate_user, create_user, get_role_modules, has_users, list_roles
from app.services.equipment_check_service import confirm_monthly_equipment_check, get_monthly_equipment_check_status
from app.ui.pages.admin import admin_page
from app.ui.pages.ai_assistant import ai_assistant_page
from app.ui.pages.dashboard import dashboard_page
from app.ui.pages.alerts_reports import alerts_reports_page
from app.ui.pages.employee_management import employee_management_page
from app.ui.pages.placeholders import placeholder_page
from app.ui.pages.ppe import ppe_page
from app.ui.pages.referentials import referentials_page
from app.ui.pages.settings import settings_page
from app.ui.pages.maintenance_actions import maintenance_actions_page
from app.ui.pages.timesheet_management import timesheet_management_page
from app.ui.pages.toolbox_talk import toolbox_talk_page
from app.ui.pages.training_management import training_management_page
from app.ui.theme import BORDER, DANGER, MUTED, PANEL, PRIMARY, SIDEBAR, SIDEBAR_ACTIVE, SIDEBAR_MUTED, SURFACE, TEXT


NAV_ITEMS = [
    ("Dashboard", "Tableau de bord", ft.Icons.DASHBOARD_OUTLINED),
    ("Referentials", "Referentiels", ft.Icons.TUNE_OUTLINED),
    ("EmployeeManagement", "Gestion employes", ft.Icons.PEOPLE_ALT_OUTLINED),
    ("TrainingManagement", "Gestion formation", ft.Icons.SCHOOL_OUTLINED),
    ("ToolboxTalk", "Toolbox Talk", ft.Icons.FORUM_OUTLINED),
    ("TimeSheet", "TimeSheets", ft.Icons.CALENDAR_MONTH_OUTLINED),
    ("Ppe", "Gestion des EPI", ft.Icons.INVENTORY_2_OUTLINED),
    ("MaintenanceActions", "Maintenance & Actions", ft.Icons.HANDYMAN_OUTLINED),
    ("Alerts", "Alertes & Rapports", ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
    ("AiAssistant", "Assistant IA", ft.Icons.AUTO_AWESOME_OUTLINED),
    ("Settings", "Parametres", ft.Icons.SETTINGS_OUTLINED),
    ("Admin", "Administrateur", ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED),
]


def build_app(page: ft.Page) -> None:
    page.title = "OREZONE QHSE"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = SURFACE
    page.padding = 0
    page.window.min_width = 1000
    page.window.min_height = 680
    session: dict[str, object] = {"user": None, "dark_mode": False}
    root = ft.Container(expand=True)
    page.add(root)

    def show_login(message: str = "") -> None:
        root.content = _login_view(page, session, show_app, show_setup, message)
        page.update()

    def show_setup(message: str = "") -> None:
        root.content = _setup_view(page, session, show_app, show_login, message)
        page.update()

    def logout() -> None:
        session["user"] = None
        show_login("Session fermee.")

    def show_app() -> None:
        root.content = _app_view(page, session, logout)
        page.update()

    if has_users():
        show_login()
    else:
        show_setup()


def _app_view(page: ft.Page, session: dict[str, object], logout: object) -> ft.Control:
    user = dict(session.get("user") or {})
    allowed_keys = set(get_role_modules(str(user.get("role") or "")))
    if "MonthlyTimesheet" in allowed_keys:
        allowed_keys.add("TimeSheet")
    if "Reports" in allowed_keys:
        allowed_keys.add("Alerts")
    if _is_admin_user(user):
        allowed_keys.update(key for key, _, _ in NAV_ITEMS)
    visible_nav_items = [item for item in NAV_ITEMS if item[0] in allowed_keys]
    if "Admin" in allowed_keys:
        visible_nav_items = _promote_admin_nav_item(visible_nav_items)
    if not visible_nav_items:
        visible_nav_items = [NAV_ITEMS[0]]

    screen_switcher = ft.AnimatedSwitcher(
        content=ft.Container(),
        duration=260,
        reverse_duration=160,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
        transition=ft.AnimatedSwitcherTransition.FADE,
        expand=True,
    )
    content = ft.Container(expand=True, padding=24, content=screen_switcher)
    active_title = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color=TEXT)
    active_subtitle = ft.Text("", size=12, color=MUTED)
    current_key: str | None = None
    nav_buttons: list[ft.TextButton] = []
    screen_cache: dict[str, ft.Control] = {}
    startup_reminder_shown = False

    def render(index: int, force_reload: bool = False) -> None:
        nonlocal current_key
        key, label, _ = visible_nav_items[index]
        try:
            if force_reload:
                screen_cache.pop(key, None)
            if key not in screen_cache:
                screen_cache[key] = _build_screen(key, label, page, user, render_key)
            screen_switcher.content = screen_cache[key]
            active_title.value = label
            active_subtitle.value = _module_subtitle(key)
            current_key = key
        except Exception as exc:
            screen_switcher.content = _error_view(label, exc)
            active_title.value = label
            active_subtitle.value = "Erreur de chargement du module."
            current_key = key
        refresh_nav_styles()
        page.update()

    def render_key(key: str) -> None:
        for index, item in enumerate(visible_nav_items):
            if item[0] == key:
                render(index)
                return

    def refresh_current(event: ft.ControlEvent | None = None) -> None:
        if current_key is None:
            render(0)
            return
        for index, item in enumerate(visible_nav_items):
            if item[0] == current_key:
                render(index, force_reload=True)
                return

    def toggle_dark_mode(event: ft.ControlEvent) -> None:
        enabled = bool(event.control.value)
        session["dark_mode"] = enabled
        page.theme_mode = ft.ThemeMode.DARK if enabled else ft.ThemeMode.LIGHT
        page.bgcolor = "#0B1220" if enabled else SURFACE
        page.update()

    def nav_style(selected: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            color="#FFFFFF" if selected else SIDEBAR_MUTED,
            bgcolor=SIDEBAR_ACTIVE if selected else SIDEBAR,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
        )

    def refresh_nav_styles() -> None:
        for button in nav_buttons:
            selected = button.data == current_key
            button.style = nav_style(selected)
            if isinstance(button.content, ft.Row):
                for control in button.content.controls:
                    if isinstance(control, ft.Icon):
                        control.color = "#FFFFFF" if selected else SIDEBAR_MUTED
                    if isinstance(control, ft.Text):
                        control.color = "#FFFFFF" if selected else SIDEBAR_MUTED

    nav_buttons = [
        ft.TextButton(
            data=key,
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=19, color=SIDEBAR_MUTED),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_600 if key in {"Admin", "AiAssistant"} else ft.FontWeight.W_500,
                        color=SIDEBAR_MUTED,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        width=168,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            style=nav_style(False),
            on_click=lambda event, nav_index=index: render(nav_index),
        )
        for index, (key, label, icon) in enumerate(visible_nav_items)
    ]

    nav_list = ft.Column(
        controls=nav_buttons,
        spacing=6,
        scroll=ft.ScrollMode.ALWAYS,
        expand=True,
    )

    def show_monthly_equipment_reminder() -> None:
        nonlocal startup_reminder_shown
        if startup_reminder_shown:
            return
        status = get_monthly_equipment_check_status()
        if status["confirmed"]:
            return
        startup_reminder_shown = True
        can_open_maintenance = any(item[0] == "MaintenanceActions" for item in visible_nav_items)

        def close_dialog(event: ft.ControlEvent | None = None) -> None:
            page.pop_dialog()
            page.update()

        def open_maintenance(event: ft.ControlEvent | None = None) -> None:
            close_dialog()
            render_key("MaintenanceActions")

        def confirm_check(event: ft.ControlEvent | None = None) -> None:
            confirm_monthly_equipment_check(
                str(status["month"]),
                confirmed_by=str(user.get("username") or "system"),
                commentaire="Verification mensuelle confirmee depuis le rappel au demarrage.",
            )
            screen_cache.pop("Alerts", None)
            screen_cache.pop("MaintenanceActions", None)
            close_dialog()
            refresh_current()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    controls=[
                        ft.Container(
                            bgcolor="#FEF3C7",
                            border_radius=8,
                            padding=8,
                            content=ft.Icon(ft.Icons.HANDYMAN_OUTLINED, color="#B45309", size=22),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("Verification mensuelle des engins", color=TEXT, weight=ft.FontWeight.BOLD, size=17),
                                ft.Text(f"Mois concerne: {status['month']}", color=MUTED, size=12),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                content=ft.Container(
                    width=520,
                    content=ft.Column(
                        controls=[
                            ft.Text(str(status["message"]), color=TEXT, size=13),
                            ft.Container(
                                bgcolor="#F8FAFC",
                                border=ft.border.all(1, BORDER),
                                border_radius=8,
                                padding=12,
                                content=ft.Row(
                                    controls=[
                                        _startup_metric("Ouvertes", status["open_maintenance"], PRIMARY),
                                        _startup_metric("Dues", status["due_maintenance"], DANGER if status["due_maintenance"] else PRIMARY),
                                        _startup_metric("Statut", "Non confirme", DANGER),
                                    ],
                                    spacing=10,
                                    wrap=True,
                                ),
                            ),
                            ft.Text(
                                "Ce rappel continuera a s'afficher a chaque ouverture tant que la verification mensuelle n'est pas confirmee.",
                                color=MUTED,
                                size=12,
                            ),
                        ],
                        spacing=12,
                        tight=True,
                    ),
                ),
                actions=[
                    ft.TextButton("Plus tard", on_click=close_dialog),
                    ft.OutlinedButton(
                        "Ouvrir Maintenance",
                        icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                        on_click=open_maintenance,
                        visible=can_open_maintenance,
                    ),
                    ft.ElevatedButton(
                        "Confirmer la verification du mois",
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINED,
                        bgcolor=PRIMARY,
                        color="#FFFFFF",
                        on_click=confirm_check,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    app = ft.Row(
        controls=[
            ft.Container(
                width=252,
                bgcolor=SIDEBAR,
                border=ft.border.only(right=ft.BorderSide(1, "#1F2937")),
                content=ft.Column(
                    controls=[
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=20, vertical=18),
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        "OREZONE QHSE",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color="#F9FAFB",
                                    ),
                                    ft.Text(
                                        "Industrial QHSE Dashboard",
                                        size=11,
                                        color=SIDEBAR_MUTED,
                                    ),
                                ],
                                spacing=3,
                            ),
                        ),
                        ft.Container(
                            padding=ft.padding.only(left=10, right=4, top=8, bottom=8),
                            content=nav_list,
                            expand=True,
                        ),
                        ft.Container(
                            bgcolor="#0B1220",
                            border=ft.border.only(top=ft.BorderSide(1, "#1F2937")),
                            padding=ft.padding.symmetric(horizontal=14, vertical=14),
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        "Session",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=SIDEBAR_MUTED,
                                    ),
                                    ft.Text(
                                        str(user.get("username") or "-"),
                                        size=12,
                                        color="#F9FAFB",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        str(user.get("role") or "-"),
                                        size=11,
                                        color=SIDEBAR_MUTED,
                                    ),
                                    ft.OutlinedButton(
                                        content=ft.Row(
                                            controls=[
                                                ft.Icon(ft.Icons.LOGOUT_OUTLINED, color=DANGER, size=18),
                                                ft.Text("Deconnexion", color=DANGER),
                                            ],
                                            spacing=8,
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            tight=True,
                                        ),
                                        on_click=lambda event: logout(),
                                        width=214,
                                    ),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
            ),
            ft.Column(
                controls=[
                    ft.Container(
                        bgcolor=PANEL,
                        border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                        padding=ft.padding.symmetric(horizontal=24, vertical=12),
                        content=ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[active_title, active_subtitle],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Container(
                                    bgcolor="#F8FAFC",
                                    border=ft.border.all(1, BORDER),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=10, vertical=7),
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.SYNC, size=16, color=PRIMARY),
                                            ft.Text("SQLite sync", size=12, color=TEXT, weight=ft.FontWeight.BOLD),
                                        ],
                                        spacing=7,
                                        tight=True,
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH,
                                    tooltip="Rafraichir le module",
                                    on_click=refresh_current,
                                ),
                                ft.Switch(
                                    label="Dark",
                                    value=bool(session.get("dark_mode")),
                                    active_color=PRIMARY,
                                    on_change=toggle_dark_mode,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=12,
                        ),
                    ),
                    content,
                ],
                spacing=0,
                expand=True,
            ),
        ],
        spacing=0,
        expand=True,
    )
    render(0)
    show_monthly_equipment_reminder()
    return app


def _module_subtitle(key: str) -> str:
    subtitles = {
        "Dashboard": "KPI, alertes et supervision terrain en temps reel local.",
        "Referentials": "Donnees de base partagees par les autres modules.",
        "EmployeeManagement": "RH, affectations, badges et statut operationnel.",
        "TrainingManagement": "Formations, conformite et matrice des competences.",
        "ToolboxTalk": "Themes securite journaliers et suivi HSE terrain.",
        "TimeSheet": "TimeSheet 21-20 et TimeSheet 1-25 regroupes en onglets.",
        "Ppe": "Stock EPI, dotations, inspections et seuils critiques.",
        "MaintenanceActions": "Maintenance equipements, action tracker, echeances et responsabilites.",
        "Alerts": "Signaux QHSE et rapports operationnels consolides.",
        "AiAssistant": "Assistant QHSE pour analyses, priorites et aide a la decision.",
        "Settings": "Chemins, exports, base SQLite, sauvegardes et installation.",
        "Admin": "Utilisateurs, roles, permissions, audits et sauvegardes.",
    }
    return subtitles.get(key, "Module OREZONE QHSE.")


def _startup_metric(label: str, value: object, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Column(
            controls=[
                ft.Text(label, size=11, color=MUTED, weight=ft.FontWeight.BOLD),
                ft.Text(str(value), size=16, color=color, weight=ft.FontWeight.BOLD),
            ],
            spacing=2,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _build_screen(
    key: str,
    label: str,
    page: ft.Page,
    user: dict[str, object],
    render_key: object,
) -> ft.Control:
    if key == "Dashboard":
        return dashboard_page()
    if key == "Referentials":
        return referentials_page(page)
    if key == "EmployeeManagement":
        return employee_management_page(page)
    if key == "TrainingManagement":
        return training_management_page(page)
    if key == "ToolboxTalk":
        return toolbox_talk_page(page)
    if key == "TimeSheet":
        return timesheet_management_page(page)
    if key == "Ppe":
        return ppe_page(page)
    if key == "MaintenanceActions":
        return maintenance_actions_page(page)
    if key == "Alerts":
        return alerts_reports_page(navigate=render_key)
    if key == "AiAssistant":
        return ai_assistant_page(page)
    if key == "Settings":
        return settings_page(user, page)
    if key == "Admin":
        return admin_page(user, page)
    return placeholder_page(label)


def _is_admin_user(user: dict[str, object]) -> bool:
    role = str(user.get("role") or "").strip().lower()
    username = str(user.get("username") or "").strip().lower()
    return role == "administrateur" or username == "admin"


def _promote_admin_nav_item(items: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    admin_items = [item for item in items if item[0] == "Admin"]
    other_items = [item for item in items if item[0] != "Admin"]
    if not admin_items:
        return items
    insert_at = 1 if other_items and other_items[0][0] == "Dashboard" else 0
    return other_items[:insert_at] + admin_items + other_items[insert_at:]


def _login_view(
    page: ft.Page,
    session: dict[str, object],
    show_app: object,
    show_setup: object,
    message: str = "",
) -> ft.Control:
    username = ft.TextField(label="Nom utilisateur", width=320, autofocus=True)
    password = ft.TextField(label="Mot de passe", password=True, can_reveal_password=True, width=320)
    status = ft.Text(message, color="#64748B", size=12)

    def login(event: ft.ControlEvent | None = None) -> None:
        try:
            session["user"] = authenticate_user(username.value, password.value)
            show_app()
        except ValueError as exc:
            status.value = str(exc)
            status.color = "#DC2626"
            page.update()

    return _auth_panel(
        title="Connexion",
        subtitle="Acces securise a OREZONE QHSE.",
        controls=[
            username,
            password,
            ft.ElevatedButton("Se connecter", icon=ft.Icons.LOGIN_OUTLINED, on_click=login, width=320),
            ft.TextButton("Creer le premier administrateur", on_click=lambda event: show_setup(), visible=not has_users()),
            status,
        ],
    )


def _setup_view(
    page: ft.Page,
    session: dict[str, object],
    show_app: object,
    show_login: object,
    message: str = "",
) -> ft.Control:
    username = ft.TextField(label="Administrateur", value="admin", width=320, autofocus=True)
    password = ft.TextField(label="Mot de passe", password=True, can_reveal_password=True, width=320)
    confirm = ft.TextField(label="Confirmer", password=True, can_reveal_password=True, width=320)
    status = ft.Text(message or "Aucun utilisateur detecte: cree le premier administrateur.", color="#64748B", size=12)

    def create_admin(event: ft.ControlEvent | None = None) -> None:
        try:
            if password.value != confirm.value:
                raise ValueError("Les mots de passe ne correspondent pas.")
            roles = list_roles()
            admin_role = next((role for role in roles if role["nom"] == "Administrateur"), None)
            if admin_role is None:
                raise ValueError("Role Administrateur introuvable.")
            create_user(
                {
                    "username": username.value,
                    "password": password.value,
                    "role_id": admin_role["id_role"],
                    "statut": "actif",
                }
            )
            session["user"] = authenticate_user(username.value, password.value)
            show_app()
        except ValueError as exc:
            status.value = str(exc)
            status.color = "#DC2626"
            page.update()

    return _auth_panel(
        title="Premier demarrage",
        subtitle="Creation du compte administrateur local.",
        controls=[
            username,
            password,
            confirm,
            ft.ElevatedButton("Creer et ouvrir", icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, on_click=create_admin, width=320),
            ft.TextButton("Retour connexion", on_click=lambda event: show_login(), visible=has_users()),
            status,
        ],
    )


def _auth_panel(title: str, subtitle: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        expand=True,
        bgcolor=SURFACE,
        alignment=ft.Alignment(0, 0),
        content=ft.Container(
            width=430,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#BFDBFE"),
            border_radius=8,
            padding=28,
            content=ft.Column(
                controls=[
                    ft.Text("OREZONE QHSE", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Text(title, size=26, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Text(subtitle, size=13, color="#64748B"),
                    ft.Divider(height=18, color="#BFDBFE"),
                    *controls,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        ),
    )


def _error_view(module_name: str, error: Exception) -> ft.Control:
    return ft.Container(
        bgcolor="#FEF2F2",
        border=ft.border.all(1, "#FECACA"),
        border_radius=8,
        padding=18,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=DANGER, size=24),
                        ft.Text(
                            f"Erreur dans {module_name}",
                            color=DANGER,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(str(error), color="#991B1B", size=12, selectable=True),
                ft.Text(
                    "Ferme le fichier Excel concerne s'il est ouvert, puis actualise le module.",
                    color=MUTED,
                    size=12,
                ),
            ],
            spacing=10,
        ),
    )
