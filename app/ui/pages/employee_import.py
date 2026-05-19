from __future__ import annotations

from pathlib import Path
from typing import Any

import flet as ft

from app.config import EXPORTS_DIR
from app.services import import_employees_from_file
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


TEMPLATE_PATH = EXPORTS_DIR / "modele_import_employes_orezone.xlsx"


def employee_import_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"path": "", "last_result": None}
    status = ft.Text("Selectionne un fichier, puis lance la verification avant import.", size=12, color=MUTED)
    result_area = ft.Column(spacing=10)
    picker = ft.FilePicker() if page is not None else None
    if page is not None and picker not in page.services:
        page.services.append(picker)

    path_field = ft.TextField(
        label="Fichier a importer",
        hint_text="Chemin du fichier CSV ou XLSX",
        width=620,
        dense=True,
    )

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def set_path(path: str) -> None:
        state["path"] = path
        state["last_result"] = None
        path_field.value = path
        notify("Fichier selectionne. Lance la verification avant d'importer.", PRIMARY)
        render_result(None)
        _update()

    async def pick_file(event: ft.ControlEvent | None = None) -> None:
        if page is None or picker is None:
            notify("Selection fichier indisponible ici. Colle le chemin dans le champ.", WARNING)
            _update()
            return
        files = await picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["csv", "xlsx"],
            dialog_title="Importer une liste des employes",
            file_type=ft.FilePickerFileType.CUSTOM,
        )
        if not files:
            notify("Aucun fichier selectionne.", MUTED)
            _update()
            return
        selected_path = str(files[0].path or "")
        if not selected_path:
            notify("Chemin fichier introuvable. Utilise un fichier local CSV ou XLSX.", DANGER)
            _update()
            return
        set_path(selected_path)

    def verify(event: ft.ControlEvent | None = None) -> None:
        run_import(dry_run=True)

    def import_file(event: ft.ControlEvent | None = None) -> None:
        run_import(dry_run=False)

    def clear_selection(event: ft.ControlEvent | None = None) -> None:
        state["path"] = ""
        state["last_result"] = None
        path_field.value = ""
        notify("Selection effacee.", MUTED)
        render_result(None)
        _update()

    def run_import(dry_run: bool) -> None:
        path = str(path_field.value or state["path"] or "").strip()
        if not path:
            notify("Selectionne un fichier CSV ou XLSX.", DANGER)
            _update()
            return
        try:
            result = import_employees_from_file(Path(path), dry_run=dry_run)
            state["last_result"] = result
            if result["errors"]:
                notify(f"{len(result['errors'])} erreur(s) detectee(s). Aucun employe importe.", DANGER)
            elif dry_run:
                notify(f"Verification OK: {result['rows']} ligne(s) prete(s) a importer.", SUCCESS)
            else:
                notify(f"Import termine: {result['created']} employe(s) ajoute(s).", SUCCESS)
            render_result(result)
        except (OSError, ValueError) as exc:
            notify(str(exc), DANGER)
            render_result(None)
        _update()

    def render_result(result: dict[str, Any] | None) -> None:
        if not result:
            result_area.controls = [
                ft.Row(
                    controls=[
                        _step_card("1", "Choisir", "Selectionne le fichier CSV ou XLSX.", PRIMARY),
                        _step_card("2", "Verifier", "Controle les lignes et les referentiels.", WARNING),
                        _step_card("3", "Importer", "Ajoute les employes valides dans la base.", SUCCESS),
                    ],
                    spacing=10,
                    wrap=True,
                )
            ]
            return

        errors = result.get("errors") or []
        if errors:
            result_area.controls = [
                _result_header("Import bloque", f"{len(errors)} erreur(s) a corriger.", DANGER, ft.Icons.ERROR_OUTLINE),
                ft.Column(
                    controls=[
                        ft.Container(
                            bgcolor="#FEF2F2",
                            border=ft.border.all(1, "#FECACA"),
                            border_radius=8,
                            padding=10,
                            content=ft.Row(
                                controls=[
                                    ft.Text(f"Ligne {item.get('line')}", width=80, color=DANGER, weight=ft.FontWeight.BOLD),
                                    ft.Text(str(item.get("message") or ""), color="#991B1B", expand=True),
                                ],
                                spacing=8,
                            ),
                        )
                        for item in errors[:20]
                    ],
                    spacing=6,
                ),
            ]
            if len(errors) > 20:
                result_area.controls.append(ft.Text(f"+ {len(errors) - 20} autre(s) erreur(s).", color=MUTED, size=12))
            return

        preview = result.get("preview") or []
        result_area.controls = [
            _result_header("Fichier valide", f"{result.get('rows', 0)} ligne(s) controlee(s).", SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
        ]
        if preview:
            result_area.controls.append(
                ft.Row(
                    controls=[
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("Nom")),
                                ft.DataColumn(ft.Text("Matricule")),
                                ft.DataColumn(ft.Text("Badge")),
                                ft.DataColumn(ft.Text("Type")),
                            ],
                            rows=[
                                ft.DataRow(
                                    cells=[
                                        ft.DataCell(ft.Text(str(row.get("nom_complet") or "-"))),
                                        ft.DataCell(ft.Text(str(row.get("matricule") or "-"))),
                                        ft.DataCell(ft.Text(str(row.get("numero_badge") or "-"))),
                                        ft.DataCell(ft.Text(str(row.get("type_employe") or "-"))),
                                    ]
                                )
                                for row in preview
                            ],
                            border=ft.border.all(1, "#BFDBFE"),
                            border_radius=8,
                            heading_row_color="#DBEAFE",
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                )
            )

    root = ft.Column(
        controls=[
            module_header(
                "Importer des employes",
                "Import massif depuis CSV ou XLSX avec controle des referentiels et doublons.",
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.UPLOAD_FILE_OUTLINED, color=PRIMARY, size=26),
                                ft.Column(
                                    controls=[
                                        ft.Text("Fichier d'import", color=TEXT, size=16, weight=ft.FontWeight.BOLD),
                                        ft.Text("Utilise le modele Excel recommande ou un CSV avec les memes colonnes.", color=MUTED, size=12),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Container(
                                    bgcolor="#EFF6FF",
                                    border=ft.border.all(1, "#BFDBFE"),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                                    content=ft.Text("CSV / XLSX", color=PRIMARY, weight=ft.FontWeight.BOLD, size=12),
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            controls=[
                                path_field,
                                ft.OutlinedButton("Parcourir", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=pick_file),
                                ft.OutlinedButton("Verifier", icon=ft.Icons.FACT_CHECK_OUTLINED, on_click=verify),
                                ft.ElevatedButton("Importer", icon=ft.Icons.CLOUD_UPLOAD_OUTLINED, on_click=import_file),
                                ft.IconButton(icon=ft.Icons.CLEAR_OUTLINED, tooltip="Effacer", on_click=clear_selection),
                            ],
                            spacing=8,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        status,
                    ],
                    spacing=12,
                ),
            ),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        col={"sm": 12, "md": 5},
                        content=_requirements_panel(),
                    ),
                    ft.Container(
                        col={"sm": 12, "md": 7},
                        content=_template_panel(),
                    ),
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Resultat", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        result_area,
                    ],
                    spacing=10,
                ),
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render_result(None)
    return root


def _requirements_panel() -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=16,
        content=ft.Column(
            controls=[
                ft.Text("Donnees obligatoires", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                _requirement_line("Nom + Prenom", "ou Nom complet"),
                _requirement_line("Fonction", "doit exister dans les referentiels"),
                _requirement_line("Site", "doit exister dans les referentiels"),
                _requirement_line("Shift", "DAY, NIGHT, Day Shift ou Night Shift"),
            ],
            spacing=8,
        ),
    )


def _template_panel() -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#BFDBFE"),
        border_radius=8,
        padding=16,
        content=ft.Column(
            controls=[
                ft.Text("Modele Excel", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text(str(TEMPLATE_PATH), size=12, color=MUTED, selectable=True),
                ft.Text(
                    "Le modele contient une feuille vide a remplir, une feuille d'exemples et une feuille d'aide.",
                    size=12,
                    color=MUTED,
                ),
                ft.Row(
                    controls=[
                        _small_badge("Matricule optionnel", WARNING),
                        _small_badge("Badge unique", PRIMARY),
                        _small_badge("Referentiels requis", SUCCESS),
                    ],
                    spacing=8,
                    wrap=True,
                ),
            ],
            spacing=8,
        ),
    )


def _requirement_line(title: str, detail: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=18),
            ft.Text(title, color=TEXT, weight=ft.FontWeight.BOLD, width=120),
            ft.Text(detail, color=MUTED, expand=True, size=12),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _step_card(number: str, title: str, detail: str, color: str) -> ft.Control:
    return ft.Container(
        width=230,
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=30,
                    height=30,
                    bgcolor=color,
                    border_radius=15,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(number, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                ),
                ft.Column(
                    controls=[
                        ft.Text(title, color=TEXT, weight=ft.FontWeight.BOLD),
                        ft.Text(detail, color=MUTED, size=11),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _result_header(title: str, detail: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=22),
                ft.Text(title, color=color, weight=ft.FontWeight.BOLD),
                ft.Text(detail, color=MUTED),
            ],
            spacing=8,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _small_badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, color=color, size=11, weight=ft.FontWeight.BOLD),
    )
