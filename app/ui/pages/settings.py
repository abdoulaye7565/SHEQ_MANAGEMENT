from __future__ import annotations

from typing import Any

import flet as ft

from app.services import create_settings_backup, ensure_runtime_directories, get_application_settings
from app.services.ai_service import AIConfigurationError, get_ai_settings, record_ai_test_status, save_ai_settings, test_ai_connection
from app.services.email_service import (
    EmailConfigurationError,
    get_email_settings,
    record_email_test_status,
    save_email_settings,
    test_email_connection,
)
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.components.tables import professional_data_table
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def settings_page(current_user: dict[str, Any] | None = None, page: ft.Page | None = None) -> ft.Control:
    actor = str((current_user or {}).get("username") or "system")
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    table_area = ft.Column(spacing=10)
    ai_enabled = ft.Switch(label="Activer IA", value=False, active_color=PRIMARY)
    ai_model = ft.TextField(label="Modele OpenAI", value="", width=220)
    ai_api_key = ft.TextField(
        label="Cle API OpenAI",
        hint_text="Laisser vide pour conserver",
        password=True,
        can_reveal_password=True,
        width=320,
    )
    ai_clear_key = ft.Checkbox(label="Supprimer la cle locale", value=False)
    email_enabled = ft.Switch(label="Activer email", value=False, active_color=PRIMARY)
    email_host = ft.TextField(label="Serveur SMTP", hint_text="smtp.office365.com", width=230)
    email_port = ft.TextField(label="Port", value="587", width=90)
    email_tls = ft.Checkbox(label="TLS", value=True)
    email_sender = ft.TextField(label="Email expediteur", width=260)
    email_sender_name = ft.TextField(label="Nom expediteur", value="OREZONE QHSE", width=200)
    email_password = ft.TextField(
        label="Mot de passe / App password",
        hint_text="Laisser vide pour conserver",
        password=True,
        can_reveal_password=True,
        width=260,
    )
    email_clear_password = ft.Checkbox(label="Supprimer le mot de passe local", value=False)
    email_manager = ft.TextField(label="Email manager", width=280)
    email_somisy = ft.TextField(label="Email SOMISY", width=280)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color
        show_feedback(page, message, color)

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        render()
        _update()

    def ensure_dirs(event: ft.ControlEvent | None = None) -> None:
        ensure_runtime_directories()
        notify("Dossiers runtime verifies et crees si necessaire.", SUCCESS)
        render()
        _update()

    def backup_database(event: ft.ControlEvent | None = None) -> None:
        try:
            output = create_settings_backup("sauvegarde_parametres", changed_by=actor)
            notify(f"Sauvegarde creee: {output}", SUCCESS)
            render()
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def save_ai_config(event: ft.ControlEvent | None = None) -> None:
        try:
            save_ai_settings(
                {
                    "enabled": ai_enabled.value,
                    "model": ai_model.value,
                    "api_key": ai_api_key.value,
                    "clear_api_key": ai_clear_key.value,
                }
            )
            ai_api_key.value = ""
            ai_clear_key.value = False
            notify("Configuration IA enregistree.", SUCCESS)
            render()
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def test_ai_config(event: ft.ControlEvent | None = None) -> None:
        try:
            save_ai_settings(
                {
                    "enabled": ai_enabled.value,
                    "model": ai_model.value,
                    "api_key": ai_api_key.value,
                    "clear_api_key": ai_clear_key.value,
                }
            )
            ai_api_key.value = ""
            ai_clear_key.value = False
            notify("Test IA en cours...", PRIMARY)
            _update()
            message = test_ai_connection()
            record_ai_test_status("ok", message)
            notify(f"IA operationnelle: {message}", SUCCESS)
            render()
        except (ValueError, AIConfigurationError) as exc:
            record_ai_test_status("error", str(exc))
            notify(str(exc), DANGER)
        _update()

    def save_email_config(event: ft.ControlEvent | None = None) -> None:
        try:
            save_email_settings(_email_values())
            email_password.value = ""
            email_clear_password.value = False
            notify("Configuration email enregistree.", SUCCESS)
            render()
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def test_email_config(event: ft.ControlEvent | None = None) -> None:
        try:
            save_email_settings(_email_values())
            email_password.value = ""
            email_clear_password.value = False
            notify("Test email en cours...", PRIMARY)
            _update()
            message = test_email_connection()
            record_email_test_status("ok", message)
            notify(message, SUCCESS)
            render()
        except (ValueError, EmailConfigurationError) as exc:
            record_email_test_status("error", str(exc))
            notify(str(exc), DANGER)
        _update()

    def _email_values() -> dict[str, Any]:
        return {
            "enabled": email_enabled.value,
            "smtp_host": email_host.value,
            "smtp_port": email_port.value,
            "use_tls": email_tls.value,
            "sender_email": email_sender.value,
            "sender_name": email_sender_name.value,
            "password": email_password.value,
            "clear_password": email_clear_password.value,
            "manager_email": email_manager.value,
            "somisy_email": email_somisy.value,
        }

    def render() -> None:
        data = get_application_settings()
        ai = get_ai_settings()
        email = get_email_settings()
        ai_enabled.value = bool(ai["enabled"])
        ai_model.value = str(ai["model"])
        email_enabled.value = bool(email["enabled"])
        email_host.value = str(email["smtp_host"])
        email_port.value = str(email["smtp_port"])
        email_tls.value = bool(email["use_tls"])
        email_sender.value = str(email["sender_email"])
        email_sender_name.value = str(email["sender_name"])
        email_manager.value = str(email["manager_email"])
        email_somisy.value = str(email["somisy_email"])
        summary_row.controls = [
            _summary_chip("Version", data["version"], PRIMARY, ft.Icons.INFO_OUTLINED),
            _summary_chip("Mode", data["mode"], SUCCESS if data["mode"] == "Installee" else WARNING, ft.Icons.DESKTOP_WINDOWS_OUTLINED),
            _summary_chip("Exports", data["exports_count"], PRIMARY, ft.Icons.DOWNLOAD_OUTLINED),
            _summary_chip("Backups", data["backups_count"], SUCCESS, ft.Icons.BACKUP_OUTLINED),
            _summary_chip("SQLite", "OK" if data["database_exists"] else "Absent", SUCCESS if data["database_exists"] else DANGER, ft.Icons.STORAGE_OUTLINED),
            _summary_chip("IA", _ai_status_label(ai), _ai_status_color(ai), ft.Icons.AUTO_AWESOME_OUTLINED),
            _summary_chip("Email", _email_status_label(email), _email_status_color(email), ft.Icons.MAIL_OUTLINED),
        ]
        rows = [
            ("Application", "Version", data["version"]),
            ("Application", "Mode execution", data["mode"]),
            ("Application", "Python", data["python"]),
            ("Application", "Plateforme", data["platform"]),
            ("Chemins", "Dossier application", data["base_dir"]),
            ("Chemins", "Dossier package", data["package_dir"]),
            ("Chemins", "Dossier data", data["data_dir"]),
            ("Chemins", "Dossier exports", data["exports_dir"]),
            ("Chemins", "Dossier sauvegardes", data["backups_dir"]),
            ("SQLite", "Base active", data["database_path"]),
            ("SQLite", "Schema", data["schema_path"]),
            ("SQLite", "Taille base", f"{data['database_size']} octets"),
            ("IA", "Fournisseur", ai["provider"]),
            ("IA", "Modele", ai["model"]),
            ("IA", "Etat", _ai_status_label(ai)),
            ("IA", "Cle API", "Configuree" if ai["api_key_configured"] else "Non configuree"),
            ("IA", "Source cle", ai["api_key_source"] if ai["api_key_configured"] else "-"),
            ("IA", "Dernier test", ai["last_test_message"] or "-"),
            ("IA", "Date test", ai["last_test_at"] or "-"),
            ("IA", "Fichier config", ai["config_path"]),
            ("Email", "Serveur SMTP", email["smtp_host"] or "-"),
            ("Email", "Port", str(email["smtp_port"])),
            ("Email", "TLS", "Oui" if email["use_tls"] else "Non"),
            ("Email", "Expediteur", email["sender_email"] or "-"),
            ("Email", "Manager", email["manager_email"] or "-"),
            ("Email", "SOMISY", email["somisy_email"] or "-"),
            ("Email", "Mot de passe", "Configure" if email["password_configured"] else "Non configure"),
            ("Email", "Etat", _email_status_label(email)),
            ("Email", "Dernier test", email["last_test_message"] or "-"),
            ("Email", "Date test", email["last_test_at"] or "-"),
            ("Email", "Fichier config", email["config_path"]),
        ]
        table_area.controls = [
            ft.Row(
                controls=[
                    ft.OutlinedButton("Rafraichir", icon=ft.Icons.REFRESH_OUTLINED, on_click=refresh),
                    ft.OutlinedButton("Verifier les dossiers", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=ensure_dirs),
                    ft.ElevatedButton("Sauvegarder la base", icon=ft.Icons.BACKUP_OUTLINED, on_click=backup_database),
                    status,
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(
                bgcolor="#F8FAFC",
                border=ft.border.all(1, "#CBD5E1"),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Text("Configuration IA", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[
                                ai_enabled,
                                ai_model,
                                ai_api_key,
                                ai_clear_key,
                                ft.ElevatedButton("Enregistrer IA", icon=ft.Icons.SAVE_OUTLINED, on_click=save_ai_config),
                                ft.OutlinedButton("Tester IA", icon=ft.Icons.TASK_ALT_OUTLINED, on_click=test_ai_config),
                            ],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            "La cle reste stockee localement sur cet ordinateur. Les suggestions IA doivent etre validees par un responsable QHSE.",
                            size=12,
                            color=MUTED,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(
                bgcolor="#F8FAFC",
                border=ft.border.all(1, "#CBD5E1"),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Text("Configuration email TimeSheet", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row(
                            controls=[email_enabled, email_host, email_port, email_tls, email_sender, email_sender_name],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[email_password, email_clear_password, email_manager, email_somisy],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("Enregistrer email", icon=ft.Icons.SAVE_OUTLINED, on_click=save_email_config),
                                ft.OutlinedButton("Tester email", icon=ft.Icons.MARK_EMAIL_READ_OUTLINED, on_click=test_email_config),
                            ],
                            spacing=10,
                            wrap=True,
                        ),
                        ft.Text(
                            "SMTP envoie directement. L'option Outlook prepare un brouillon avec piece jointe en utilisant Outlook installe sur ce PC.",
                            size=12,
                            color=MUTED,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(
                bgcolor="#ECFDF5",
                border=ft.border.all(1, "#86EFAC"),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.MAIL_OUTLINED, color=SUCCESS, size=20),
                                ft.Text("Outlook Desktop", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            "Pour utiliser Outlook, renseigne seulement Email manager et Email SOMISY ci-dessus, puis clique sur le bouton Outlook dans le TimeSheet. Outlook doit etre installe et connecte sur ce PC.",
                            size=12,
                            color=MUTED,
                        ),
                        ft.Text(
                            "Cette option prepare le message avec le fichier Excel deja attache; l'utilisateur verifie puis clique Envoyer dans Outlook.",
                            size=12,
                            color=MUTED,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Section")),
                            ft.DataColumn(ft.Text("Parametre")),
                            ft.DataColumn(ft.Text("Valeur")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(section, weight=ft.FontWeight.BOLD, color=TEXT)),
                                    ft.DataCell(ft.Text(label, color=MUTED)),
                                    ft.DataCell(ft.Text(value, color=TEXT, width=620, selectable=True)),
                                ],
                            )
                            for section, label, value in rows
                        ],
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    root = ft.Column(
        controls=[
            module_header(
                "Parametres application",
                "Chemins runtime, exports, base SQLite, sauvegardes et verification installation.",
            ),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=summary_row,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=table_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render()
    return root


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _ai_status_label(ai: dict[str, Any]) -> str:
    if ai.get("operational"):
        return "Operationnelle"
    if ai.get("last_test_status") == "error":
        return "Erreur test"
    if ai.get("ready"):
        return "A tester"
    if ai.get("enabled"):
        return "Cle requise"
    return "Off"


def _ai_status_color(ai: dict[str, Any]) -> str:
    if ai.get("operational"):
        return SUCCESS
    if ai.get("last_test_status") == "error":
        return DANGER
    return WARNING


def _email_status_label(email: dict[str, Any]) -> str:
    if email.get("operational"):
        return "Operationnel"
    if email.get("last_test_status") == "error":
        return "Erreur test"
    if email.get("ready"):
        return "A tester"
    if email.get("enabled"):
        return "Config requise"
    return "Off"


def _email_status_color(email: dict[str, Any]) -> str:
    if email.get("operational"):
        return SUCCESS
    if email.get("last_test_status") == "error":
        return DANGER
    return WARNING
