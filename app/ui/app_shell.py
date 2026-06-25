import flet as ft
from datetime import date, datetime, timedelta

from app.services import authenticate_user, create_user, get_dashboard_summary, get_role_modules, has_users, list_roles
from app.services.settings_service import APP_VERSION
from app.services.app_logger import log_exception
from app.services.automation_service import run_startup_automations
from app.services.equipment_check_service import confirm_monthly_equipment_check, get_monthly_equipment_check_status
from app.services.mobile_sync_service import ensure_mobile_sync_server
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
from app.ui.pages.risk_analysis import risk_analysis_page
from app.ui.pages.accidents import accidents_page
from app.ui.pages.permits import permits_page
from app.ui.pages.drilling import drilling_page
from app.ui.pages.qhse_dashboard import qhse_dashboard_page
from app.ui.pages.notifications import notifications_page
from app.ui.pages.statistics import statistics_page
from app.ui.theme import BORDER, DANGER, MUTED, PANEL, PRIMARY, SIDEBAR, SIDEBAR_ACTIVE, SIDEBAR_MUTED, SUCCESS, SURFACE, TEXT, WARNING, dark_page_theme, page_theme

# Quand un module est rechargé (force_reload), ces écrans dépendants sont aussi invalidés.
_CACHE_DEPS: dict[str, list[str]] = {
    "MaintenanceActions": ["Alerts", "Dashboard", "QHSEDashboard"],
    "Attendance": ["Dashboard", "QHSEDashboard", "MonthlyTimesheet", "Timesheet"],
    "Training": ["Alerts", "Dashboard", "QHSEDashboard"],
    "PPE": ["Alerts", "Dashboard"],
    "Breaks": ["Alerts"],
    "ToolboxTalk": ["Dashboard", "QHSEDashboard"],
    "RiskAnalysis": ["Dashboard", "QHSEDashboard"],
    "Accidents": ["Dashboard", "QHSEDashboard", "Alerts"],
    "Permits": ["Dashboard", "QHSEDashboard"],
    "EmployeeManagement": ["Dashboard", "QHSEDashboard", "Attendance", "Training", "PPE", "Breaks"],
    "Referentials": ["EmployeeManagement", "Attendance"],
    "Admin": ["Dashboard"],
}


NAV_ITEMS = [
    ("QHSEDashboard", "Tableau de bord QHSE", ft.Icons.SHIELD_OUTLINED),
    ("Notifications", "Notifications", ft.Icons.NOTIFICATIONS_OUTLINED),
    ("Statistics", "Statistiques QHSE", ft.Icons.ANALYTICS_OUTLINED),
    ("Dashboard", "Tableau de bord", ft.Icons.DASHBOARD_OUTLINED),
    ("Referentials", "Referentiels", ft.Icons.TUNE_OUTLINED),
    ("EmployeeManagement", "Gestion employes", ft.Icons.PEOPLE_ALT_OUTLINED),
    ("TrainingManagement", "Gestion formation", ft.Icons.SCHOOL_OUTLINED),
    ("ToolboxTalk", "Toolbox Talk", ft.Icons.FORUM_OUTLINED),
    ("TimeSheet", "TimeSheets", ft.Icons.CALENDAR_MONTH_OUTLINED),
    ("Drilling", "Drilling Reports", ft.Icons.HARDWARE_OUTLINED),
    ("Ppe", "Gestion des EPI", ft.Icons.INVENTORY_2_OUTLINED),
    ("MaintenanceActions", "Maintenance & Actions", ft.Icons.HANDYMAN_OUTLINED),
    ("RiskAnalysis", "Analyse des Risques", ft.Icons.CRISIS_ALERT_OUTLINED),
    ("Accidents", "Accidents & Incidents", ft.Icons.PERSONAL_INJURY_OUTLINED),
    ("Permits", "Permis de Travail", ft.Icons.ASSIGNMENT_OUTLINED),
    ("Alerts", "Alertes & Rapports", ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
    ("AiAssistant", "Assistant IA", ft.Icons.AUTO_AWESOME_OUTLINED),
    ("Settings", "Parametres", ft.Icons.SETTINGS_OUTLINED),
    ("Admin", "Administrateur", ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED),
]

_NAV_SECTIONS: list[tuple[str, list[str]]] = [
    ("SYNTHÈSE", ["QHSEDashboard", "Notifications", "Statistics"]),
    ("SUPERVISION", ["Dashboard", "Alerts"]),
    ("RESSOURCES", ["EmployeeManagement", "TrainingManagement", "ToolboxTalk", "Ppe"]),
    ("OPERATIONS", ["MaintenanceActions", "RiskAnalysis", "Accidents", "Permits", "TimeSheet", "Drilling"]),
    ("SYSTEME", ["AiAssistant", "Referentials", "Settings", "Admin"]),
]


def build_app(page: ft.Page) -> None:
    page.title = "OREZONE QHSE"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = page_theme()
    page.dark_theme = dark_page_theme()
    page.bgcolor = SURFACE
    page.padding = 0
    page.window.min_width = 760
    page.window.min_height = 680
    session: dict[str, object] = {"user": None}
    login_guard: dict[str, object] = {"failures": 0, "locked_until": None}
    root = ft.Container(expand=True)
    page.add(root)

    def show_login(message: str = "") -> None:
        root.content = _login_view(page, session, show_app, show_setup, login_guard, message)
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
    run_startup_automations()
    try:
        ensure_mobile_sync_server()
    except Exception as exc:
        log_exception("Mobile sync autostart failed", exc)
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
    active_title = ft.Text("", size=17, weight=ft.FontWeight.BOLD, color="#FFFFFF")
    active_subtitle = ft.Text("", size=12, color="#9DB0C5")
    active_module_icon: ft.Container | None = None
    top_header: ft.Container | None = None
    sync_badge: ft.Container | None = None
    sync_icon: ft.Icon | None = None
    sync_text: ft.Text | None = None
    refresh_button: ft.IconButton | None = None
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
                for dep_key in _CACHE_DEPS.get(key, []):
                    screen_cache.pop(dep_key, None)
            if key not in screen_cache:
                screen_cache[key] = _build_screen(key, label, page, user, render_key)
            screen_switcher.content = screen_cache[key]
            active_title.value = label
            active_subtitle.value = _module_subtitle(key)
            current_key = key
        except Exception as exc:
            log_exception(f"Module load failed: {label}", exc)
            screen_switcher.content = _error_view(label, exc)
            active_title.value = label
            active_subtitle.value = "Erreur de chargement du module."
            current_key = key
        content.padding = 10
        content.bgcolor = "#071321"
        active_title.color = "#FFFFFF"
        active_subtitle.color = "#9DB0C5"
        if top_header is not None:
            top_header.bgcolor = "#071321"
            top_header.border = ft.border.only(bottom=ft.BorderSide(1, "#1E3A56"))
        if sync_badge is not None:
            sync_badge.bgcolor = "#10243A"
            sync_badge.border = ft.border.all(1, "#1E3A56")
        if sync_icon is not None:
            sync_icon.color = "#60A5FA"
        if sync_text is not None:
            sync_text.color = "#FFFFFF"
        if refresh_button is not None:
            refresh_button.icon_color = "#C7D4E3"
        if active_module_icon is not None:
            nav_icon = next((ic for k, _, ic in visible_nav_items if k == key), ft.Icons.APPS_OUTLINED)
            active_module_icon.content = ft.Icon(nav_icon, size=20, color="#60A5FA")
            active_module_icon.bgcolor = "#10243A"
        refresh_nav_styles()
        try:
            page.update()
        except IndexError:
            # Flet DiffBuilder can raise IndexError on complex control tree diffs;
            # force a clean page rebuild by clearing the cache and retrying once.
            screen_cache.clear()
            try:
                screen_cache[key] = _build_screen(key, label, page, user, render_key)
                screen_switcher.content = screen_cache[key]
                page.update()
            except Exception:
                pass

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

    def nav_style(selected: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            color="#FFFFFF" if selected else SIDEBAR_MUTED,
            bgcolor=SIDEBAR_ACTIVE if selected else "transparent",
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.only(left=6, right=12, top=9, bottom=9),
        )

    def refresh_nav_styles() -> None:
        for button in nav_buttons:
            selected = button.data == current_key
            button.style = nav_style(selected)
            if isinstance(button.content, ft.Row) and len(button.content.controls) >= 3:
                button.content.controls[0].bgcolor = "#FFFFFF" if selected else "transparent"
                button.content.controls[1].color = "#FFFFFF" if selected else SIDEBAR_MUTED
                button.content.controls[2].color = "#FFFFFF" if selected else SIDEBAR_MUTED

    nav_buttons = [
        ft.TextButton(
            data=key,
            content=ft.Row(
                controls=[
                    ft.Container(width=3, height=24, bgcolor="transparent", border_radius=2),
                    ft.Icon(icon, size=18, color=SIDEBAR_MUTED),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_600 if key in {"Admin", "AiAssistant"} else ft.FontWeight.W_500,
                        color=SIDEBAR_MUTED,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        width=160,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            style=nav_style(False),
            on_click=lambda event, nav_index=index: render(nav_index),
        )
        for index, (key, label, icon) in enumerate(visible_nav_items)
    ]

    _btn_map = {btn.data: btn for btn in nav_buttons}
    _nav_controls: list[ft.Control] = []
    for _sec_label, _sec_keys in _NAV_SECTIONS:
        _sec_btns = [_btn_map[k] for k in _sec_keys if k in _btn_map]
        if _sec_btns:
            _nav_controls.append(ft.Container(
                padding=ft.padding.only(left=16, top=14, bottom=3, right=10),
                content=ft.Text(
                    _sec_label, size=9, color="#4B5563",
                    weight=ft.FontWeight.BOLD,
                ),
            ))
            _nav_controls.extend(_sec_btns)

    nav_list = ft.Column(
        controls=_nav_controls,
        spacing=2,
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

    sync_icon = ft.Icon(ft.Icons.STORAGE_OUTLINED, size=15, color="#60A5FA")
    sync_text = ft.Text("Local DB", size=11, color="#FFFFFF", weight=ft.FontWeight.W_600)
    sync_badge = ft.Container(
        bgcolor="#10243A",
        border=ft.border.all(1, "#1E3A56"),
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        content=ft.Row(
            controls=[sync_icon, sync_text],
            spacing=6,
            tight=True,
        ),
    )
    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH_OUTLINED,
        tooltip="Rafraichir le module",
        icon_size=20,
        icon_color="#C7D4E3",
        on_click=refresh_current,
    )
    active_module_icon = ft.Container(
        width=36, height=36,
        bgcolor="#10243A",
        border_radius=8,
        alignment=ft.Alignment(0, 0),
        content=ft.Icon(ft.Icons.DASHBOARD_OUTLINED, size=20, color="#60A5FA"),
    )
    top_header = ft.Container(
        bgcolor="#071321",
        border=ft.border.only(bottom=ft.BorderSide(1, "#1E3A56")),
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        content=ft.Row(
            controls=[
                active_module_icon,
                ft.Column(
                    controls=[active_title, active_subtitle],
                    spacing=1,
                    expand=True,
                ),
                sync_badge,
                refresh_button,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
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
                            padding=ft.padding.only(left=16, right=16, top=16, bottom=12),
                            border=ft.border.only(bottom=ft.BorderSide(1, "#1F2937")),
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        width=38, height=38,
                                        bgcolor=SIDEBAR_ACTIVE,
                                        border_radius=10,
                                        alignment=ft.Alignment(0, 0),
                                        content=ft.Icon(ft.Icons.SHIELD_OUTLINED, color="#FFFFFF", size=20),
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text("OREZONE", size=14, weight=ft.FontWeight.BOLD, color="#F9FAFB"),
                                            ft.Text("QHSE Platform", size=10, color=SIDEBAR_MUTED),
                                        ],
                                        spacing=1,
                                        tight=True,
                                    ),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ),
                        ft.Container(
                            padding=ft.padding.only(left=8, right=4, top=6, bottom=6),
                            content=nav_list,
                            expand=True,
                        ),
                        ft.Container(
                            bgcolor="#0B1220",
                            border=ft.border.only(top=ft.BorderSide(1, "#1F2937")),
                            padding=ft.padding.symmetric(horizontal=12, vertical=10),
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        width=34, height=34,
                                        bgcolor=SIDEBAR_ACTIVE,
                                        border_radius=17,
                                        alignment=ft.Alignment(0, 0),
                                        content=ft.Text(
                                            (str(user.get("username") or "?")[0]).upper(),
                                            size=14, color="#FFFFFF", weight=ft.FontWeight.BOLD,
                                        ),
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text(
                                                str(user.get("username") or "-"),
                                                size=12, color="#F9FAFB",
                                                weight=ft.FontWeight.W_600,
                                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                str(user.get("role") or "-"),
                                                size=10, color=SIDEBAR_MUTED,
                                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                        ],
                                        spacing=1,
                                        tight=True,
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.LOGOUT_OUTLINED,
                                        icon_color=DANGER,
                                        icon_size=18,
                                        tooltip="Deconnexion",
                                        on_click=lambda event: logout(),
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
            ),
            ft.Column(
                controls=[
                    top_header,
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
        "QHSEDashboard": "Synthese temps reel de tous les indicateurs QHSE — risques, accidents, permis, EPI.",
        "Notifications": "Alertes centralisees de tous les modules QHSE avec suivi de prise en charge.",
        "Statistics": "Tendances, distributions et indicateurs de performance QHSE.",
        "Dashboard": "KPI, alertes et supervision terrain en temps reel local.",
        "Referentials": "Donnees de base partagees par les autres modules.",
        "EmployeeManagement": "RH, affectations, badges et statut operationnel.",
        "TrainingManagement": "Formations, conformite et matrice des competences.",
        "ToolboxTalk": "Themes securite journaliers et suivi HSE terrain.",
        "TimeSheet": "TimeSheet 21-20 et TimeSheet 1-25 regroupes en onglets.",
        "Ppe": "Stock EPI, dotations, inspections et seuils critiques.",
        "MaintenanceActions": "Maintenance equipements, action tracker, echeances et responsabilites.",
        "RiskAnalysis": "Identification, evaluation et maitrise des risques HSE (ISO 31000:2018).",
        "Accidents": "Enregistrement, analyse des causes et actions correctives (ISO 45001).",
        "Permits": "Emission, validation multi-niveaux et archivage des permis de travail.",
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


def _screen_registry(
    page: ft.Page,
    user: dict[str, object],
    render_key: object,
) -> dict[str, object]:
    return {
        "QHSEDashboard":      lambda: qhse_dashboard_page(page),
        "Notifications":      lambda: notifications_page(page),
        "Statistics":         lambda: statistics_page(page),
        "Dashboard":          lambda: dashboard_page(navigate=render_key, user=user),
        "Referentials":       lambda: referentials_page(page),
        "EmployeeManagement": lambda: employee_management_page(page),
        "TrainingManagement": lambda: training_management_page(page),
        "ToolboxTalk":        lambda: toolbox_talk_page(page),
        "TimeSheet":          lambda: timesheet_management_page(page),
        "Drilling":           lambda: drilling_page(page),
        "Ppe":                lambda: ppe_page(page),
        "MaintenanceActions": lambda: maintenance_actions_page(page),
        "RiskAnalysis":       lambda: risk_analysis_page(page),
        "Accidents":          lambda: accidents_page(page),
        "Permits":            lambda: permits_page(page),
        "Alerts":             lambda: alerts_reports_page(navigate=render_key),
        "AiAssistant":        lambda: ai_assistant_page(page),
        "Settings":           lambda: settings_page(user, page),
        "Admin":              lambda: admin_page(user, page),
        "MonthlyTimesheet":   lambda: placeholder_page("Feuille mensuelle"),
    }


def _build_screen(
    key: str,
    label: str,
    page: ft.Page,
    user: dict[str, object],
    render_key: object,
) -> ft.Control:
    registry = _screen_registry(page, user, render_key)
    builder = registry.get(key)
    if builder is not None:
        return builder()
    return placeholder_page(label)


def _is_admin_user(user: dict[str, object]) -> bool:
    role = str(user.get("role") or "").strip().lower()
    return role == "administrateur"


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
    login_guard: dict[str, object],
    message: str = "",
) -> ft.Control:
    username = _login_text_field("Nom d'utilisateur", ft.Icons.PERSON_OUTLINE, autofocus=True)
    password = _login_text_field("Mot de passe", ft.Icons.LOCK_OUTLINE, password=True)
    remember = ft.Checkbox(label="Se souvenir de moi", value=True, active_color=PRIMARY)
    status = ft.Text(message, color="#64748B", size=12)

    def login(event: ft.ControlEvent | None = None) -> None:
        try:
            locked_until = login_guard.get("locked_until")
            if isinstance(locked_until, datetime) and datetime.now() < locked_until:
                remaining = max(1, int((locked_until - datetime.now()).total_seconds()))
                raise ValueError(f"Trop de tentatives. Reessaie dans {remaining} secondes.")
            session["user"] = authenticate_user(username.value, password.value)
            login_guard["failures"] = 0
            login_guard["locked_until"] = None
            show_app()
        except ValueError as exc:
            failures = int(login_guard.get("failures") or 0) + 1
            login_guard["failures"] = failures
            if failures >= 5:
                delay = min(120, 15 * (failures - 4))
                login_guard["locked_until"] = datetime.now() + timedelta(seconds=delay)
            status.value = str(exc)
            status.color = "#DC2626"
            page.update()

    return _login_shell(
        title="Bienvenue !",
        subtitle="Connectez-vous a votre compte OREZONE QHSE",
        controls=[
            username,
            password,
            ft.Row(
                controls=[
                    remember,
                    ft.TextButton(
                        "Mot de passe oublie ?",
                        on_click=lambda event: _set_login_status(
                            page,
                            status,
                            "Contacte un administrateur pour reinitialiser ton mot de passe.",
                            WARNING,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.ElevatedButton(
                "Se connecter",
                icon=ft.Icons.LOGIN_OUTLINED,
                on_click=login,
                width=520,
                height=48,
                style=ft.ButtonStyle(
                    bgcolor=PRIMARY,
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=8),
                    text_style=ft.TextStyle(size=15, weight=ft.FontWeight.BOLD),
                ),
            ),
            ft.OutlinedButton(
                "Connexion hors ligne",
                icon=ft.Icons.OFFLINE_BOLT_OUTLINED,
                width=520,
                height=44,
                on_click=lambda event: _set_login_status(
                    page,
                    status,
                    "Mode hors ligne: connecte-toi avec un compte local existant.",
                    MUTED,
                ),
                style=ft.ButtonStyle(
                    color=TEXT,
                    side=ft.BorderSide(1, "#CBD5E1"),
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
            ),
            ft.TextButton(
                "Creer le premier administrateur",
                on_click=lambda event: show_setup(),
                visible=not has_users(),
            ),
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
    return _login_shell(title, subtitle, controls)


def _login_shell(title: str, subtitle: str, controls: list[ft.Control]) -> ft.Control:
    summary = _safe_dashboard_summary()
    today = date.today()
    return ft.Container(
        expand=True,
        bgcolor="#DDEAF7",
        content=ft.Stack(
            expand=True,
            controls=[
                _login_background(),
                ft.Row(
                    expand=True,
                    controls=[
                        ft.Container(
                            expand=4,
                            padding=ft.padding.only(left=40, right=36, top=42, bottom=26),
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment(-1, -1),
                                end=ft.Alignment(1, 1),
                                colors=["#061525", "#0B2136", "#07111F"],
                            ),
                            content=ft.Column(
                                controls=[
                                    _brand_block(large=True),
                                    ft.Container(height=18),
                                    ft.Text(
                                        "Integrated Mining\nQHSE Management System",
                                        size=30,
                                        weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF",
                                    ),
                                    ft.Container(width=74, height=3, bgcolor="#F5B83D", border_radius=8),
                                    ft.Row(
                                        controls=[
                                            _dot_label("Securite", DANGER),
                                            _dot_label("Qualite", PRIMARY),
                                            _dot_label("Environnement", SUCCESS),
                                            _dot_label("Operations", WARNING),
                                        ],
                                        wrap=True,
                                        spacing=12,
                                    ),
                                    ft.Text(
                                        "Une gestion integree pour des operations minieres sures, durables et performantes.",
                                        size=15,
                                        color="#D7E2EF",
                                        width=520,
                                    ),
                                    ft.Container(expand=True),
                                    ft.Text("CONFORMITE & NORMES", color="#F5B83D", size=13, weight=ft.FontWeight.BOLD),
                                    ft.ResponsiveRow(
                                        controls=[
                                            _compliance_card("ISO 45001", "Sante & Securite\nau Travail", SUCCESS, ft.Icons.HEALTH_AND_SAFETY_OUTLINED),
                                            _compliance_card("ISO 14001", "Management\nEnvironnemental", "#84CC16", ft.Icons.PARK_OUTLINED),
                                            _compliance_card("ISO 9001", "Management\nde la Qualite", PRIMARY, ft.Icons.VERIFIED_OUTLINED),
                                        ],
                                        spacing=8,
                                        run_spacing=8,
                                    ),
                                    ft.Text("INDICATEURS CLES EN TEMPS REEL", color="#F5B83D", size=13, weight=ft.FontWeight.BOLD),
                                    ft.ResponsiveRow(
                                        controls=[
                                            _login_kpi("Employes\nactifs", summary["employees"], ft.Icons.GROUP_OUTLINED, PRIMARY),
                                            _login_kpi("Formations\nvalides", summary["trainings"], ft.Icons.SCHOOL_OUTLINED, SUCCESS),
                                            _login_kpi("Toolbox Talks\nce mois", summary["toolbox"], ft.Icons.FORUM_OUTLINED, WARNING),
                                            _login_kpi("Conformite\nQHSE", f"{summary['compliance']}%", ft.Icons.SHIELD_OUTLINED, "#A855F7"),
                                        ],
                                        spacing=8,
                                        run_spacing=8,
                                    ),
                                    _site_date_strip(today),
                                    ft.Text(
                                        "(c) 2026 OREZONE QHSE Management System. Tous droits reserves.",
                                        size=11,
                                        color="#8EA2B8",
                                    ),
                                ],
                                spacing=16,
                            ),
                        ),
                        ft.Container(
                            expand=6,
                            padding=ft.padding.symmetric(horizontal=38, vertical=30),
                            content=ft.Column(
                                controls=[
                                    _login_topbar(),
                                    ft.Container(expand=True),
                                    ft.Container(
                                        width=590,
                                        bgcolor="#FFFFFF",
                                        border_radius=22,
                                        padding=ft.padding.symmetric(horizontal=40, vertical=34),
                                        shadow=ft.BoxShadow(
                                            spread_radius=0,
                                            blur_radius=34,
                                            color="#330F172A",
                                            offset=ft.Offset(0, 16),
                                        ),
                                        content=ft.Column(
                                            controls=[
                                                ft.Row(
                                                    controls=[
                                                        ft.Container(
                                                            width=58,
                                                            height=58,
                                                            bgcolor="#FFF7E6",
                                                            border_radius=16,
                                                            alignment=ft.Alignment(0, 0),
                                                            content=ft.Icon(ft.Icons.GPP_GOOD_OUTLINED, color="#E7A72F", size=36),
                                                        ),
                                                        ft.Column(
                                                            controls=[
                                                                ft.Text(title, size=33, weight=ft.FontWeight.BOLD, color="#0F172A"),
                                                                ft.Text(subtitle, size=14, color="#52627A"),
                                                            ],
                                                            spacing=4,
                                                            tight=True,
                                                        ),
                                                    ],
                                                    spacing=22,
                                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                                ),
                                                ft.Container(height=8),
                                                *controls,
                                                ft.Row(
                                                    controls=[
                                                        ft.Container(expand=True, height=1, bgcolor="#E2E8F0"),
                                                        ft.Text("INFORMATIONS SYSTEME", color="#94A3B8", size=12, weight=ft.FontWeight.BOLD),
                                                        ft.Container(expand=True, height=1, bgcolor="#E2E8F0"),
                                                    ],
                                                    spacing=12,
                                                ),
                                                ft.Row(
                                                    controls=[
                                                        _system_info("Derniere connexion", "Locale", "Compte securise", ft.Icons.ACCESS_TIME_OUTLINED, PRIMARY),
                                                        _system_info("Base de donnees", "Connectee", "SQLite", ft.Icons.STORAGE_OUTLINED, SUCCESS),
                                                        _system_info("Version systeme", APP_VERSION, f"Build {APP_VERSION}", ft.Icons.CODE_OUTLINED, "#0F172A"),
                                                    ],
                                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                                ),
                                            ],
                                            spacing=16,
                                        ),
                                    ),
                                    ft.Container(expand=True),
                                    _security_footer(),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=18,
                            ),
                        ),
                    ],
                    spacing=0,
                ),
            ],
        ),
    )


def _login_text_field(label: str, icon: str, autofocus: bool = False, password: bool = False) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=f"Entrez votre {label.lower()}",
        prefix_icon=icon,
        password=password,
        can_reveal_password=password,
        autofocus=autofocus,
        height=56,
        border_radius=10,
        border_color="#CBD5E1",
        focused_border_color=PRIMARY,
        bgcolor="#FFFFFF",
        color=TEXT,
        label_style=ft.TextStyle(color=PRIMARY, weight=ft.FontWeight.BOLD),
    )


def _set_login_status(page: ft.Page, status: ft.Text, message: str, color: str) -> None:
    status.value = message
    status.color = color
    page.update()


def _login_background() -> ft.Control:
    return ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#D8EAFB", "#F8FBFF", "#D6E7F5"],
        ),
    )


def _brand_block(large: bool = False) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Image(src="orezone_qhse_icon.png", width=86 if large else 46, height=86 if large else 46),
            ft.Column(
                controls=[
                    ft.Text("OREZONE", size=42 if large else 18, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ft.Text("QHSE", size=32 if large else 14, weight=ft.FontWeight.BOLD, color="#F5B83D"),
                ],
                spacing=-8 if large else -3,
                tight=True,
            ),
        ],
        spacing=16 if large else 10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _dot_label(label: str, color: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Container(width=7, height=7, bgcolor=color, border_radius=10),
            ft.Text(label, color="#FFFFFF", size=14),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _compliance_card(title: str, subtitle: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"sm": 12, "md": 4},
        padding=14,
        border_radius=10,
        border=ft.border.all(1, "#1F3A54"),
        bgcolor="#13283B",
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=28),
                ft.Column(
                    controls=[
                        ft.Text(title, color="#FFFFFF", size=14, weight=ft.FontWeight.BOLD),
                        ft.Container(width=50, height=2, bgcolor="#EAB308", border_radius=6),
                        ft.Text(subtitle, color="#D7E2EF", size=11),
                    ],
                    spacing=4,
                    tight=True,
                ),
            ],
            spacing=10,
        ),
    )


def _login_kpi(label: str, value: object, icon: str, color: str) -> ft.Control:
    return ft.Container(
        col={"sm": 6, "md": 3},
        padding=14,
        border_radius=10,
        border=ft.border.all(1, "#1F3A54"),
        bgcolor="#102234",
        content=ft.Column(
            controls=[
                ft.Icon(icon, color=color, size=28),
                ft.Text(str(value), color="#FFFFFF", size=25, weight=ft.FontWeight.BOLD),
                ft.Text(label, color="#E2E8F0", size=12, text_align=ft.TextAlign.CENTER),
                ft.Text("+ stable", color="#8BD450", size=11),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _site_date_strip(today: date) -> ft.Control:
    return ft.Container(
        padding=16,
        border_radius=10,
        border=ft.border.all(1, "#1F3A54"),
        bgcolor="#13283B",
        content=ft.Row(
            controls=[
                _mini_info(ft.Icons.LOCATION_ON_OUTLINED, "Site actif", "SYAMA", "Mine d'Or"),
                _mini_info(ft.Icons.CALENDAR_MONTH_OUTLINED, "Date", today.strftime("%d/%m/%Y"), _weekday_fr(today)),
                _mini_info(ft.Icons.ACCESS_TIME_OUTLINED, "Heure", datetime.now().strftime("%H:%M"), "UTC local"),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )


def _mini_info(icon: str, label: str, value: str, subtitle: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Icon(icon, color=PRIMARY, size=24),
            ft.Column(
                controls=[
                    ft.Text(label, color="#9DB0C5", size=11),
                    ft.Text(value, color="#FFFFFF", size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(subtitle, color="#B7C6D6", size=11),
                ],
                spacing=1,
                tight=True,
            ),
        ],
        spacing=8,
        tight=True,
    )


def _login_topbar() -> ft.Control:
    return ft.Row(
        controls=[
            ft.Text("Theme", color="#0F172A", size=13, weight=ft.FontWeight.BOLD),
            ft.Container(
                border=ft.border.all(1, "#F59E0B"),
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=8, vertical=5),
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WB_SUNNY_OUTLINED, color=PRIMARY, size=20),
                        ft.Container(width=32, height=26, bgcolor="#334155", border_radius=16, content=ft.Icon(ft.Icons.DARK_MODE_OUTLINED, color="#FFFFFF", size=16)),
                    ],
                    spacing=6,
                    tight=True,
                ),
            ),
            ft.Container(width=1, height=32, bgcolor="#94A3B8"),
            ft.Text("Site", color="#0F172A", size=13, weight=ft.FontWeight.BOLD),
            ft.Dropdown(
                value="SYAMA",
                width=155,
                options=[ft.dropdown.Option("SYAMA", "SYAMA")],
                border_radius=8,
                bgcolor="#FFFFFF",
                border_color="#E2E8F0",
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
    )


def _system_info(title: str, value: str, subtitle: str, icon: str, color: str) -> ft.Control:
    return ft.Container(
        width=155,
        content=ft.Column(
            controls=[
                ft.Icon(icon, color=color, size=28),
                ft.Text(title, color="#475569", size=12, text_align=ft.TextAlign.CENTER),
                ft.Text(value, color=color, size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text(subtitle, color="#64748B", size=11, text_align=ft.TextAlign.CENTER),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _security_footer() -> ft.Control:
    return ft.Container(
        width=820,
        bgcolor="#0B1B2B",
        border_radius=12,
        padding=18,
        content=ft.Row(
            controls=[
                _footer_item(ft.Icons.LOCK_OUTLINE, "Securise", "Connexion locale protegee", SUCCESS),
                _footer_item(ft.Icons.ASSIGNMENT_TURNED_IN_OUTLINED, "Audit active", "Toutes les connexions sont tracees", PRIMARY),
                _footer_item(ft.Icons.SECURITY_OUTLINED, "Protection", "Verrouillage apres 5 tentatives", WARNING),
                _footer_item(ft.Icons.SUPPORT_AGENT_OUTLINED, "Support", "+223 20 22 33 44", "#A855F7"),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )


def _footer_item(icon: str, title: str, subtitle: str, color: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Icon(icon, color=color, size=28),
            ft.Column(
                controls=[
                    ft.Text(title, color="#FFFFFF", size=13, weight=ft.FontWeight.BOLD),
                    ft.Text(subtitle, color="#B7C6D6", size=11, width=145),
                ],
                spacing=2,
                tight=True,
            ),
        ],
        spacing=10,
        tight=True,
    )


def _safe_dashboard_summary() -> dict[str, object]:
    try:
        data = get_dashboard_summary()
        training = data.get("training", {})
        return {
            "employees": data.get("employes", 0),
            "trainings": training.get("soon", 0),
            "toolbox": data.get("maintenance_actions", {}).get("actions_open", 0),
            "compliance": data.get("attendance_rate", 0),
        }
    except Exception:
        return {"employees": 0, "trainings": 0, "toolbox": 0, "compliance": 0}


def _weekday_fr(value: date) -> str:
    return ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][value.weekday()]


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
                    "Le detail technique est enregistre dans les journaux. Ferme les fichiers Excel ouverts, puis actualise le module.",
                    color=MUTED,
                    size=12,
                ),
            ],
            spacing=10,
        ),
    )
