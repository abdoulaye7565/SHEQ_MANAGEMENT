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
from app.services.mobile_sync_service import (
    MobileSyncConfigurationError,
    create_mobile_pairing_package,
    generate_mobile_pairing_token,
    generate_pairing_qr_path,
    get_mobile_token_raw,
    get_pairing_compact_code,
    write_pairing_file,
    get_mobile_sync_settings,
    list_mobile_devices,
    list_mobile_sync_events,
    save_mobile_sync_settings,
    start_mobile_sync_server,
    stop_mobile_sync_server,
    MOBILE_ROLES,
    update_mobile_device_role,
    update_mobile_device_status,
)
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.components.tables import professional_data_table
from app.services.network_client import is_network_mode, _load_config as _load_network_config
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def _build_pairing_panel(mobile: dict, on_copy=None, on_whatsapp=None, on_sms=None, on_copy_token=None) -> list:
    """Build QR + pairing instructions. Evaluated lazily to avoid crashing at import time."""
    qr_path = generate_pairing_qr_path()
    server_url = mobile.get("server_url") or ""
    token_ok = bool(mobile.get("token_configured"))
    if qr_path:
        return [ft.Container(
            bgcolor="#FFFFFF",
            border_radius=12,
            border=ft.border.all(1, "#BFDBFE"),
            padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Image(src=qr_path, width=180, height=180),
                        ft.Text("Scanner avec l'app mobile", size=10, color="#64748B",
                                text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.QR_CODE_SCANNER_OUTLINED, color=PRIMARY, size=18),
                            ft.Text("Appairage rapide", size=14, weight=ft.FontWeight.BOLD, color="#0F172A"),
                        ], spacing=6),
                        ft.Text(
                            "1. Démarrer le serveur mobile ci-dessus\n"
                            "2. Cliquer « Copier le code » ou scanner le QR\n"
                            "3. App mobile → « Coller le code d'appairage »\n"
                            "4. Connexion automatique — zéro saisie manuelle",
                            size=12, color="#475569",
                        ),
                        ft.Container(height=6),
                        ft.ElevatedButton(
                            "Copier le code d'appairage",
                            icon=ft.Icons.CONTENT_COPY_OUTLINED,
                            on_click=on_copy,
                            style=ft.ButtonStyle(bgcolor=PRIMARY, color="#FFFFFF"),
                        ),
                        ft.Container(height=4),
                        ft.Text(f"URL : {server_url or '(serveur non démarré)'}",
                                size=11, color="#64748B", selectable=True),
                        ft.Text("Le téléphone doit être sur le même réseau Wi-Fi.",
                                size=11, color="#D97706", weight=ft.FontWeight.BOLD),
                    ], spacing=4, expand=True),
                ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Divider(height=1, color="#E2E8F0"),
                ft.Text("Partager le code de connexion :", size=12,
                        weight=ft.FontWeight.BOLD, color="#0F172A"),
                ft.Text(
                    "Envoyez le token via WhatsApp/SMS pour que l'agent le saisisse "
                    "sur son téléphone sans erreur de frappe.",
                    size=11, color="#64748B",
                ),
                ft.Row([
                    ft.ElevatedButton(
                        "Copier le token seul",
                        icon=ft.Icons.KEY_OUTLINED,
                        on_click=on_copy_token,
                        style=ft.ButtonStyle(bgcolor="#0F172A", color="#FFFFFF"),
                        tooltip="Copie uniquement le token dans le presse-papier",
                    ),
                    ft.ElevatedButton(
                        "Partager via WhatsApp",
                        icon=ft.Icons.CHAT_OUTLINED,
                        on_click=on_whatsapp,
                        style=ft.ButtonStyle(bgcolor="#25D366", color="#FFFFFF"),
                        tooltip="Ouvre WhatsApp Web avec le message pré-rempli",
                    ),
                    ft.ElevatedButton(
                        "Envoyer par SMS",
                        icon=ft.Icons.SMS_OUTLINED,
                        on_click=on_sms,
                        style=ft.ButtonStyle(bgcolor="#0891B2", color="#FFFFFF"),
                        tooltip="Ouvre l'application SMS avec le message pré-rempli",
                    ),
                ], spacing=8, wrap=True),
            ], spacing=8),
        )]
    return [ft.Text(
        f"URL serveur : {server_url or 'Démarrer le serveur pour obtenir l URL'}  |  "
        f"Token : {'Configuré' if token_ok else 'Non configuré'}  |  "
        "Même réseau Wi-Fi requis.",
        size=12, color=MUTED, selectable=True,
    )]


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
    _df = dict(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"))
    email_somisy = ft.TextField(**_df, label="Email SOMISY", width=280)
    whatsapp_manager = ft.TextField(**_df, label="WhatsApp manager", hint_text="Ex: 2250700000000", width=230)
    whatsapp_somisy = ft.TextField(**_df, label="WhatsApp SOMISY", hint_text="Ex: 2250700000000", width=230)
    whatsapp_group = ft.TextField(**_df, label="Lien groupe WhatsApp", hint_text="https://chat.whatsapp.com/...", width=320)
    mobile_enabled = ft.Switch(label="Activer serveur mobile", value=False, active_color=PRIMARY)
    mobile_host = ft.TextField(**_df, label="Adresse serveur", value="0.0.0.0", width=170)
    mobile_port = ft.TextField(**_df, label="Port mobile", value="8765", width=120)
    mobile_token = ft.TextField(
        **_df,
        label="Token mobile",
        hint_text="Laisser vide pour conserver",
        password=True,
        can_reveal_password=False,
        width=260,
    )
    mobile_clear_token = ft.Checkbox(label="Supprimer token", value=False)
    mobile_events_area = ft.Column(spacing=6)
    mobile_devices_area = ft.Column(spacing=6)

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
        try:
            render()
        except Exception as exc:
            notify(str(exc), DANGER)
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
        except Exception as exc:
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
        except Exception as exc:
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
        except Exception as exc:
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

    def save_mobile_config(event: ft.ControlEvent | None = None) -> None:
        try:
            save_mobile_sync_settings(_mobile_values())
            mobile_token.value = ""
            mobile_clear_token.value = False
            notify("Configuration serveur mobile enregistree.", SUCCESS)
            render()
        except (ValueError, MobileSyncConfigurationError) as exc:
            notify(str(exc), DANGER)
        _update()

    def generate_mobile_token(event: ft.ControlEvent | None = None) -> None:
        token = generate_mobile_pairing_token()
        notify(
            f"Nouveau token genere: {token} | Il remplace immediatement tous les anciens tokens.",
            WARNING,
        )
        mobile_token.value = ""
        render()
        _update()

    def start_mobile_server(event: ft.ControlEvent | None = None) -> None:
        try:
            save_mobile_sync_settings(_mobile_values())
            server = start_mobile_sync_server()
            notify(f"Serveur mobile demarre: {server['server_url']}", SUCCESS)
            render()
        except (ValueError, MobileSyncConfigurationError) as exc:
            notify(str(exc), DANGER)
        _update()

    def stop_mobile_server(event: ft.ControlEvent | None = None) -> None:
        stop_mobile_sync_server()
        notify("Serveur mobile arrete.", WARNING)
        render()
        _update()

    def export_pairing(event: ft.ControlEvent | None = None) -> None:
        try:
            package = create_mobile_pairing_package()
            notify(f"Pack appairage cree: {package['path']}", SUCCESS)
            render()
        except (ValueError, MobileSyncConfigurationError, OSError) as exc:
            notify(str(exc), DANGER)
        _update()

    def copy_pairing_code(event: ft.ControlEvent | None = None) -> None:
        import subprocess
        code = get_pairing_compact_code()
        if not code:
            notify("Serveur non démarré ou token absent — impossible de copier le code.", DANGER)
            _update()
            return
        # Write to shared file (primary method — works between two apps on same PC)
        fpath = write_pairing_file()
        # Also try clipboard as bonus
        try:
            subprocess.run("clip", input=code.encode("utf-16-le"), check=True, shell=True)
        except Exception:
            pass
        if fpath:
            notify(f"Code d'appairage prêt. Cliquez maintenant sur « Coller le code d'appairage » dans l'app mobile.", SUCCESS)
        else:
            notify("Impossible d'écrire le fichier d'appairage.", DANGER)
        _update()

    def copy_token_only(event: ft.ControlEvent | None = None) -> None:
        import subprocess
        token = get_mobile_token_raw()
        if not token:
            notify("Token non configuré — générez un token d'abord.", DANGER)
            _update()
            return
        try:
            subprocess.run("clip", input=token.encode("utf-16-le"), check=True, shell=True)
            notify(f"Token copié : {token[:8]}...  (collez-le dans l'app mobile → Paramètres)", SUCCESS)
        except Exception:
            notify(f"Token : {token}  (copiez-le manuellement)", WARNING)
        _update()

    def _build_share_message() -> str | None:
        token = get_mobile_token_raw()
        mobile_cfg = get_mobile_sync_settings()
        url = mobile_cfg.get("server_url") or ""
        if not token or not url:
            return None
        return (
            "🔗 OREZONE QHSE Mobile — Code de connexion\n\n"
            f"Serveur : {url}\n"
            f"Token   : {token}\n\n"
            "📱 Comment configurer l'app mobile :\n"
            "  App mobile → Paramètres → saisir l'URL et le Token\n\n"
            "Ou utiliser le code d'appairage automatique :\n"
            "  Bureau → « Copier le code d'appairage »\n"
            "  Mobile → « Coller le code d'appairage »\n\n"
            "⚠️ Même réseau Wi-Fi requis."
        )

    def share_via_whatsapp(event: ft.ControlEvent | None = None) -> None:
        import webbrowser, urllib.parse
        msg = _build_share_message()
        if not msg:
            notify("Serveur non démarré ou token absent.", DANGER)
            _update()
            return
        encoded = urllib.parse.quote(msg)
        # Try WhatsApp Desktop first, fallback to WhatsApp Web
        try:
            import subprocess
            subprocess.Popen(f'start "" "whatsapp://send?text={encoded}"', shell=True)
        except Exception:
            pass
        webbrowser.open(f"https://web.whatsapp.com/send?text={encoded}")
        notify("WhatsApp ouvert avec le message pré-rempli. Choisissez le destinataire.", SUCCESS)
        _update()

    def share_via_sms(event: ft.ControlEvent | None = None) -> None:
        import webbrowser, urllib.parse
        msg = _build_share_message()
        if not msg:
            notify("Serveur non démarré ou token absent.", DANGER)
            _update()
            return
        encoded = urllib.parse.quote(msg)
        # sms: URI — works with Windows Phone Link (Link to Windows) if configured
        try:
            webbrowser.open(f"sms:?body={encoded}")
            notify("Application SMS ouverte. Si rien ne s'ouvre, utilisez WhatsApp.", SUCCESS)
        except Exception:
            notify("SMS non disponible sur ce PC. Utilisez WhatsApp à la place.", WARNING)
        _update()

    def set_device_status(device_id: str, device_status: str) -> None:
        try:
            update_mobile_device_status(device_id, device_status)
            notify("Statut appareil mobile mis a jour.", SUCCESS)
            render()
        except MobileSyncConfigurationError as exc:
            notify(str(exc), DANGER)
        _update()

    def set_device_role(device_id: str, mobile_role: str) -> None:
        try:
            update_mobile_device_role(device_id, mobile_role)
            notify("Role mobile mis a jour. Le telephone le recevra au prochain telechargement.", SUCCESS)
            render()
        except MobileSyncConfigurationError as exc:
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
            "manager_whatsapp": whatsapp_manager.value,
            "somisy_whatsapp": whatsapp_somisy.value,
            "whatsapp_group_link": whatsapp_group.value,
        }

    def _mobile_values() -> dict[str, Any]:
        return {
            "enabled": mobile_enabled.value,
            "host": mobile_host.value,
            "port": mobile_port.value,
            "token": mobile_token.value,
            "clear_token": mobile_clear_token.value,
        }

    def render() -> None:
        data = get_application_settings()
        ai = get_ai_settings()
        email = get_email_settings()
        mobile = get_mobile_sync_settings()
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
        whatsapp_manager.value = str(email["manager_whatsapp"])
        whatsapp_somisy.value = str(email["somisy_whatsapp"])
        whatsapp_group.value = str(email["whatsapp_group_link"])
        mobile_enabled.value = bool(mobile["enabled"])
        mobile_host.value = str(mobile["host"])
        mobile_port.value = str(mobile["port"])
        summary_row.controls = [
            _summary_chip("Version", data["version"], PRIMARY, ft.Icons.INFO_OUTLINED),
            _summary_chip("Mode", data["mode"], SUCCESS if data["mode"] == "Installee" else WARNING, ft.Icons.DESKTOP_WINDOWS_OUTLINED),
            _summary_chip("Exports", data["exports_count"], PRIMARY, ft.Icons.DOWNLOAD_OUTLINED),
            _summary_chip("Backups", data["backups_count"], SUCCESS, ft.Icons.BACKUP_OUTLINED),
            _summary_chip("SQLite", "OK" if data["database_exists"] else "Absent", SUCCESS if data["database_exists"] else DANGER, ft.Icons.STORAGE_OUTLINED),
            _summary_chip("IA", _ai_status_label(ai), _ai_status_color(ai), ft.Icons.AUTO_AWESOME_OUTLINED),
            _summary_chip("Email", _email_status_label(email), _email_status_color(email), ft.Icons.MAIL_OUTLINED),
            _summary_chip("Mobile", _mobile_status_label(mobile), _mobile_status_color(mobile), ft.Icons.PHONE_ANDROID_OUTLINED),
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
            ("WhatsApp", "Manager", email["manager_whatsapp"] or "-"),
            ("WhatsApp", "SOMISY", email["somisy_whatsapp"] or "-"),
            ("WhatsApp", "Groupe", email["whatsapp_group_link"] or "-"),
            ("Email", "Mot de passe", "Configure" if email["password_configured"] else "Non configure"),
            ("Email", "Etat", _email_status_label(email)),
            ("Email", "Dernier test", email["last_test_message"] or "-"),
            ("Email", "Date test", email["last_test_at"] or "-"),
            ("Email", "Fichier config", email["config_path"]),
            ("Mobile", "Serveur active", "Oui" if mobile["enabled"] else "Non"),
            ("Mobile", "Serveur demarre", "Oui" if mobile["running"] else "Non"),
            ("Mobile", "URL serveur", mobile["server_url"] or "-"),
            ("Mobile", "Token", "Configure" if mobile["token_configured"] else "Non configure"),
            ("Mobile", "Source token", mobile["token_source"]),
            ("Mobile", "Fichier config", mobile["config_path"]),
        ]
        mobile_events = list_mobile_sync_events(limit=6)
        mobile_devices = list_mobile_devices(limit=8)
        mobile_urls = list(mobile.get("server_urls") or [])
        mobile_devices_area.controls = [
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=9,
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.PHONE_ANDROID_OUTLINED,
                            color=SUCCESS if row["status"] == "active" else DANGER,
                            size=16,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(str(row["device_name"] or row["device_id"]), color=TEXT, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(str(row["device_id"]), color=MUTED, size=10, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Text(str(row["status"]), color=SUCCESS if row["status"] == "active" else DANGER, width=70, weight=ft.FontWeight.BOLD),
                        ft.Dropdown(
                            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
                            value=str(row.get("mobile_role") or "hse"),
                            width=190,
                            dense=True,
                            options=[
                                ft.dropdown.Option(key, str(profile["label"]))
                                for key, profile in MOBILE_ROLES.items()
                            ],
                            on_select=lambda event, item=row: set_device_role(
                                str(item["device_id"]),
                                str(event.control.value or "hse"),
                            ),
                        ),
                        ft.Text(f"{row['sync_count'] or 0} sync", color=MUTED, width=58, size=11),
                        ft.OutlinedButton(
                            "Bloquer" if row["status"] == "active" else "Activer",
                            icon=ft.Icons.BLOCK_OUTLINED if row["status"] == "active" else ft.Icons.CHECK_CIRCLE_OUTLINED,
                            on_click=lambda event, item=row: set_device_status(
                                str(item["device_id"]),
                                "blocked" if item["status"] == "active" else "active",
                            ),
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            for row in mobile_devices
        ] or [ft.Text("Aucun telephone appaire pour le moment.", size=12, color=MUTED)]
        mobile_events_area.controls = [
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=9,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SYNC_OUTLINED, color=SUCCESS if row["status"] == "applied" else WARNING, size=16),
                                ft.Text(str(row["device_name"] or row["device_id"]), color=TEXT, width=160, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(str(row.get("operator_username") or "-"), color=TEXT, width=110, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(str(row["event_type"]), color=MUTED, width=90),
                                ft.Text(str(row["records_count"]), color=PRIMARY, width=50, weight=ft.FontWeight.BOLD),
                                ft.Text(str(row["status"]), color=SUCCESS if row["status"] == "applied" else WARNING, width=80),
                                ft.Text(str(row["created_at"]), color=MUTED, expand=True),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            str(row["message"] or "Synchronisation sans message."),
                            color=MUTED if row["status"] == "applied" else DANGER,
                            size=11,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=8,
                ),
            )
            for row in mobile_events
        ] or [ft.Text("Aucune synchronisation mobile pour le moment.", size=12, color=MUTED)]
        _net_mode = is_network_mode()
        _net_cfg = _load_network_config()
        _net_server = f"{_net_cfg.get('host', '')}:{_net_cfg.get('port', '')}" if _net_mode else ""
        table_area.controls = [
            ft.Row(
                controls=[
                    ft.OutlinedButton("Rafraichir", icon=ft.Icons.REFRESH_OUTLINED, on_click=refresh),
                    ft.OutlinedButton("Verifier les dossiers", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=ensure_dirs),
                    ft.ElevatedButton("Sauvegarder la base", icon=ft.Icons.BACKUP_OUTLINED, on_click=backup_database),
                    ft.ElevatedButton(
                        "Configuration Reseau Multi-PC",
                        icon=ft.Icons.NETWORK_WIFI,
                        on_click=lambda event: page.go("/network_settings") if page else None,
                        style=ft.ButtonStyle(
                            bgcolor="#1E3A5F",
                            color="#FFFFFF",
                        ),
                        tooltip="Configurer le mode reseau multi-PC (serveur, IP, port, token)",
                    ),
                    status,
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(
                bgcolor="#0D2A1F" if _net_mode else "#0F172A",
                border=ft.border.all(1, "#34D399" if _net_mode else "#334155"),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.NETWORK_WIFI if _net_mode else ft.Icons.STORAGE_OUTLINED,
                                    color="#34D399" if _net_mode else "#60A5FA",
                                    size=20,
                                ),
                                ft.Text(
                                    "Mode de connexion",
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color="#F1F5F9",
                                ),
                                ft.Container(
                                    bgcolor="#34D399" if _net_mode else "#1E3A5F",
                                    border_radius=12,
                                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                    content=ft.Text(
                                        "🌐 Mode Reseau" if _net_mode else "💻 Mode Local",
                                        size=12,
                                        color="#FFFFFF",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            f"Mode Reseau actif — Serveur: {_net_server}" if _net_mode
                            else "Mode Local (SQLite direct) — Toutes les donnees sont stockees localement sur ce PC.",
                            size=12,
                            color="#94A3B8",
                        ),
                        ft.ElevatedButton(
                            "Ouvrir la configuration reseau",
                            icon=ft.Icons.SETTINGS_ETHERNET_OUTLINED,
                            on_click=lambda event: page.go("/network_settings") if page else None,
                            style=ft.ButtonStyle(
                                bgcolor="#1E3A5F",
                                color="#FFFFFF",
                            ),
                        ),
                    ],
                    spacing=8,
                ),
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
                            controls=[whatsapp_manager, whatsapp_somisy, whatsapp_group],
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
                        ft.Text(
                            "WhatsApp ouvre une conversation avec un message pret. La piece jointe Excel doit etre ajoutee manuellement dans WhatsApp.",
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
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.PHONE_ANDROID_OUTLINED, color=PRIMARY, size=20),
                                ft.Text("Serveur local pour application mobile offline", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                                ft.Text(_mobile_status_label(mobile), color=_mobile_status_color(mobile), weight=ft.FontWeight.BOLD),
                            ],
                            spacing=8,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[mobile_enabled, mobile_host, mobile_port, mobile_token, mobile_clear_token],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED, on_click=save_mobile_config),
                                ft.OutlinedButton("Generer token", icon=ft.Icons.KEY_OUTLINED, on_click=generate_mobile_token),
                                ft.OutlinedButton("Demarrer", icon=ft.Icons.PLAY_CIRCLE_OUTLINED, on_click=start_mobile_server),
                                ft.OutlinedButton("Arreter", icon=ft.Icons.STOP_CIRCLE_OUTLINED, on_click=stop_mobile_server),
                                ft.OutlinedButton("Pack JSON", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_pairing),
                            ],
                            spacing=8,
                            wrap=True,
                        ),
                        # ── QR code d'appairage ──────────────────────────────────
                        *_build_pairing_panel(
                            mobile,
                            on_copy=copy_pairing_code,
                            on_copy_token=copy_token_only,
                            on_whatsapp=share_via_whatsapp,
                            on_sms=share_via_sms,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("Adresses possibles", size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                                *[
                                    ft.Container(
                                        bgcolor="#FFFFFF",
                                        border=ft.border.all(1, "#E2E8F0"),
                                        border_radius=8,
                                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                                        content=ft.Text(url, size=12, color=TEXT, selectable=True),
                                    )
                                    for url in mobile_urls
                                ],
                            ],
                            spacing=6,
                            visible=bool(mobile_urls),
                        ),
                        ft.Text(
                            "Attribue un role a chaque telephone. Le mobile adapte ses ecrans et le serveur refuse les operations non autorisees.",
                            size=12,
                            color=MUTED,
                        ),
                        ft.Text("Telephones appaires", size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                        mobile_devices_area,
                        ft.Text("Dernieres synchronisations", size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                        mobile_events_area,
                    ],
                    spacing=10,
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
    return ft.Container(bgcolor="#071321", expand=True, content=root)


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


def _mobile_status_label(mobile: dict[str, Any]) -> str:
    if mobile.get("running"):
        return "Serveur actif"
    if mobile.get("enabled") and mobile.get("token_configured"):
        return "Pret"
    if mobile.get("enabled"):
        return "Token requis"
    return "Off"


def _mobile_status_color(mobile: dict[str, Any]) -> str:
    if mobile.get("running"):
        return SUCCESS
    if mobile.get("enabled") and not mobile.get("token_configured"):
        return DANGER
    return WARNING
