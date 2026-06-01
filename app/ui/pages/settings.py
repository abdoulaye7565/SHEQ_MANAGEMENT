from __future__ import annotations

from typing import Any

import flet as ft

from app.services import create_settings_backup, ensure_runtime_directories, get_application_settings
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.components.tables import professional_data_table
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def settings_page(current_user: dict[str, Any] | None = None, page: ft.Page | None = None) -> ft.Control:
    actor = str((current_user or {}).get("username") or "system")
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=8, wrap=True)
    table_area = ft.Column(spacing=10)

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

    def render() -> None:
        data = get_application_settings()
        summary_row.controls = [
            _summary_chip("Version", data["version"], PRIMARY, ft.Icons.INFO_OUTLINED),
            _summary_chip("Mode", data["mode"], SUCCESS if data["mode"] == "Installee" else WARNING, ft.Icons.DESKTOP_WINDOWS_OUTLINED),
            _summary_chip("Exports", data["exports_count"], PRIMARY, ft.Icons.DOWNLOAD_OUTLINED),
            _summary_chip("Backups", data["backups_count"], SUCCESS, ft.Icons.BACKUP_OUTLINED),
            _summary_chip("SQLite", "OK" if data["database_exists"] else "Absent", SUCCESS if data["database_exists"] else DANGER, ft.Icons.STORAGE_OUTLINED),
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
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=15),
                ft.Text(label, color=MUTED, size=11),
                ft.Text(str(value), color=TEXT, size=12, weight=ft.FontWeight.BOLD),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
