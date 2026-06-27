"""network_settings.py — Page de configuration du mode réseau multi-PC."""
from __future__ import annotations

from typing import Any

import flet as ft

from app.services.network_client import (
    NetworkClient,
    get_client,
    is_network_mode,
    save_network_config,
)
from app.services.lock_service import list_active_locks
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def network_settings_page(page: ft.Page, **_: Any) -> ft.Control:
    """Construit et retourne la page de configuration réseau multi-PC."""

    # ------------------------------------------------------------------
    # Champs de saisie
    # ------------------------------------------------------------------
    field_host = ft.TextField(
        label="Adresse IP du serveur",
        hint_text="ex: 192.168.1.10",
        width=280,
        border_color=PRIMARY,
        focused_border_color=PRIMARY,
    )
    field_port = ft.TextField(
        label="Port",
        hint_text="8765",
        width=120,
        border_color=PRIMARY,
        focused_border_color=PRIMARY,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    field_token = ft.TextField(
        label="Token d'authentification",
        hint_text="Laisser vide si aucun",
        width=420,
        password=True,
        can_reveal_password=True,
        border_color=PRIMARY,
        focused_border_color=PRIMARY,
    )
    switch_enabled = ft.Switch(
        label="Activer le mode réseau (multi-PC)",
        active_color=PRIMARY,
    )

    status_text = ft.Text("", size=13, color=MUTED)
    status_icon = ft.Icon(ft.Icons.CIRCLE, size=12, color=MUTED)
    locks_column = ft.Column([], spacing=4)

    # ------------------------------------------------------------------
    # Chargement de la configuration existante
    # ------------------------------------------------------------------
    try:
        from app.config import DATA_DIR
        import json
        _cfg_path = DATA_DIR / "network_config.json"
        if _cfg_path.exists():
            cfg = json.loads(_cfg_path.read_text(encoding="utf-8"))
            field_host.value = cfg.get("host", "")
            field_port.value = str(cfg.get("port", 8765))
            field_token.value = cfg.get("token", "")
            switch_enabled.value = bool(cfg.get("enabled", False))
    except Exception:
        field_port.value = "8765"

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _set_status(msg: str, color: str, icon_name=ft.Icons.CIRCLE) -> None:
        status_text.value = msg
        status_text.color = color
        status_icon.color = color
        status_icon.name = icon_name
        page.update()

    def _refresh_locks() -> None:
        try:
            locks = list_active_locks()
        except Exception:
            locks = []
        locks_column.controls.clear()
        if not locks:
            locks_column.controls.append(
                ft.Text("Aucun verrou actif.", size=12, color=MUTED)
            )
        else:
            for lk in locks:
                locks_column.controls.append(
                    ft.Container(
                        bgcolor="#FEF2F2",
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.LOCK_OUTLINED, size=14, color=DANGER),
                                ft.Text(
                                    f"{lk.get('table_cible')} #{lk.get('id_enregistrement')} "
                                    f"— {lk.get('utilisateur')} ({lk.get('pc_nom')}) "
                                    f"jusqu'à {lk.get('expire_a', '')[:16]}",
                                    size=12,
                                    color=DANGER,
                                ),
                            ],
                            spacing=6,
                        ),
                    )
                )
        page.update()

    def on_test_connection(_: ft.ControlEvent) -> None:
        host = (field_host.value or "").strip()
        port_str = (field_port.value or "8765").strip()
        token = (field_token.value or "").strip()

        if not host:
            _set_status("Veuillez saisir l'adresse IP du serveur.", WARNING, ft.Icons.WARNING_OUTLINED)
            return

        try:
            port = int(port_str)
        except ValueError:
            _set_status("Le port doit être un nombre entier.", DANGER, ft.Icons.ERROR_OUTLINED)
            return

        _set_status("Test de connexion en cours...", MUTED, ft.Icons.SYNC_OUTLINED)
        try:
            client = NetworkClient(host=host, port=port, token=token, timeout=5)
            ok = client.ping()
            if ok:
                _set_status(
                    f"Connexion réussie à {host}:{port}",
                    SUCCESS,
                    ft.Icons.CHECK_CIRCLE_OUTLINED,
                )
            else:
                _set_status(
                    f"Serveur joignable mais réponse inattendue ({host}:{port}).",
                    WARNING,
                    ft.Icons.WARNING_OUTLINED,
                )
        except ConnectionError as exc:
            _set_status(f"Connexion impossible : {exc}", DANGER, ft.Icons.ERROR_OUTLINED)
        except Exception as exc:
            _set_status(f"Erreur : {exc}", DANGER, ft.Icons.ERROR_OUTLINED)

    def on_save(_: ft.ControlEvent) -> None:
        host = (field_host.value or "").strip()
        port_str = (field_port.value or "8765").strip()
        token = (field_token.value or "").strip()
        enabled = bool(switch_enabled.value)

        try:
            port = int(port_str)
        except ValueError:
            _set_status("Le port doit être un nombre entier.", DANGER, ft.Icons.ERROR_OUTLINED)
            return

        try:
            save_network_config(host=host, port=port, token=token, enabled=enabled)
            mode_label = "mode réseau activé" if enabled else "mode local (réseau désactivé)"
            _set_status(
                f"Configuration sauvegardée — {mode_label}.",
                SUCCESS,
                ft.Icons.CHECK_CIRCLE_OUTLINED,
            )
            show_feedback(page, "Configuration réseau sauvegardée.", success=True)
        except Exception as exc:
            _set_status(f"Erreur lors de la sauvegarde : {exc}", DANGER, ft.Icons.ERROR_OUTLINED)

    def on_refresh_locks(_: ft.ControlEvent) -> None:
        _refresh_locks()

    # Charger les verrous initiaux
    _refresh_locks()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    return ft.Column(
        controls=[
            module_header(
                "Paramètres réseau multi-PC",
                subtitle="Configurez le partage de base de données entre plusieurs postes.",
                icon=ft.Icons.DEVICE_HUB_OUTLINED,
            ),
            ft.Container(height=12),

            # Carte configuration
            ft.Container(
                bgcolor="#FFFFFF",
                border_radius=12,
                border=ft.border.all(1, "#E2E8F0"),
                padding=24,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.SETTINGS_ETHERNET_OUTLINED, color=PRIMARY, size=20),
                            ft.Text("Configuration du serveur", size=15,
                                    weight=ft.FontWeight.BOLD, color=TEXT),
                        ], spacing=8),
                        ft.Divider(height=1, color="#E2E8F0"),
                        ft.Container(height=4),
                        ft.Row(
                            controls=[field_host, ft.Container(width=12), field_port],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        ft.Container(height=8),
                        field_token,
                        ft.Container(height=8),
                        switch_enabled,
                        ft.Container(height=12),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "Tester la connexion",
                                    icon=ft.Icons.NETWORK_CHECK_OUTLINED,
                                    on_click=on_test_connection,
                                    style=ft.ButtonStyle(
                                        bgcolor="#F1F5F9",
                                        color=TEXT,
                                    ),
                                ),
                                ft.Container(width=8),
                                ft.ElevatedButton(
                                    "Sauvegarder",
                                    icon=ft.Icons.SAVE_OUTLINED,
                                    on_click=on_save,
                                    style=ft.ButtonStyle(
                                        bgcolor=PRIMARY,
                                        color="#FFFFFF",
                                    ),
                                ),
                            ],
                        ),
                        ft.Container(height=8),
                        ft.Row(
                            controls=[status_icon, status_text],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=0,
                ),
            ),

            ft.Container(height=16),

            # Carte verrous actifs
            ft.Container(
                bgcolor="#FFFFFF",
                border_radius=12,
                border=ft.border.all(1, "#E2E8F0"),
                padding=24,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Row([
                                    ft.Icon(ft.Icons.LOCK_CLOCK_OUTLINED, color=WARNING, size=20),
                                    ft.Text("Verrous actifs", size=15,
                                            weight=ft.FontWeight.BOLD, color=TEXT),
                                ], spacing=8),
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH_OUTLINED,
                                    tooltip="Rafraîchir",
                                    on_click=on_refresh_locks,
                                    icon_color=PRIMARY,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(height=1, color="#E2E8F0"),
                        ft.Container(height=4),
                        locks_column,
                    ],
                    spacing=0,
                ),
            ),

            ft.Container(height=16),

            # Info box
            ft.Container(
                bgcolor="#EFF6FF",
                border_radius=10,
                border=ft.border.all(1, "#BFDBFE"),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINED, color=PRIMARY, size=16),
                            ft.Text("Comment fonctionne le mode multi-PC ?",
                                    size=13, weight=ft.FontWeight.BOLD, color=PRIMARY),
                        ], spacing=6),
                        ft.Text(
                            "• Un PC fait office de serveur (démarrez le serveur mobile sur ce PC).\n"
                            "• Les autres PCs se connectent en saisissant l'IP et le port du serveur.\n"
                            "• Le token doit correspondre à celui configuré sur le serveur.\n"
                            "• Les verrous empêchent deux utilisateurs de modifier la même fiche simultanément.",
                            size=12, color="#1E40AF",
                        ),
                    ],
                    spacing=4,
                ),
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
        expand=True,
    )
