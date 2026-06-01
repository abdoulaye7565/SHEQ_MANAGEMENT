from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import create_break, delete_break, export_rows_xlsx, list_break_alerts, list_breaks, list_employees
from app.services.break_service import BREAK_STATUSES, BREAK_TYPES
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def breaks_page() -> ft.Control:
    employees = list_employees()
    state: dict[str, Any] = {"records": []}
    controls: dict[str, ft.Control] = {}
    status = ft.Text("", size=12, color=MUTED)
    alerts_area = ft.Column(spacing=10)
    history_area = ft.Column(spacing=12)
    form_area = ft.Column(spacing=14)
    history_search = ft.TextField(label="Recherche historique", prefix_icon=ft.Icons.SEARCH, width=280)
    history_type_filter = ft.Dropdown(
        label="Type",
        value="all",
        width=170,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("break", "Break"),
            ft.dropdown.Option("annual", "Break annuel"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Maladie"),
        ],
    )
    history_status_filter = ft.Dropdown(
        label="Statut",
        value="all",
        width=170,
        options=[ft.dropdown.Option("all", "Tous")]
        + [ft.dropdown.Option(item, item) for item in BREAK_STATUSES],
    )

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def default_values() -> dict[str, Any]:
        start = date.today()
        end = start + timedelta(days=7)
        return {
            "employe_id": str(employees[0]["id_employe"]) if employees else None,
            "type_break": "break",
            "date_debut": start.isoformat(),
            "date_fin": end.isoformat(),
            "statut": "planifie",
            "commentaire": "",
        }

    def save(event: ft.ControlEvent | None = None) -> None:
        try:
            create_break({name: control.value for name, control in controls.items()})
            notify("Break/conge planifie.", SUCCESS)
            render_form(default_values())
            render_alerts()
            render_history()
        except ValueError as exc:
            notify(str(exc), DANGER)
        root.update()

    def filtered_history() -> list[dict[str, Any]]:
        query = str(history_search.value or "").strip().lower()
        selected_type = str(history_type_filter.value or "all")
        selected_status = str(history_status_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for record in state["records"]:
            searchable = " ".join(
                str(record.get(key) or "")
                for key in ("nom", "prenom", "numero_badge", "fonction", "commentaire")
            ).lower()
            if query and query not in searchable:
                continue
            if selected_type != "all" and str(record.get("type_break") or "") != selected_type:
                continue
            if selected_status != "all" and str(record.get("statut") or "") != selected_status:
                continue
            rows.append(record)
        return rows

    def refresh_history_filters(event: ft.ControlEvent | None = None) -> None:
        render_history()
        root.update()

    def reset_history_filters(event: ft.ControlEvent | None = None) -> None:
        history_search.value = ""
        history_type_filter.value = "all"
        history_status_filter.value = "all"
        render_history()
        root.update()

    def export_history(event: ft.ControlEvent | None = None) -> None:
        records = filtered_history()
        output = export_rows_xlsx(
            "historique_breaks_permissions_filtre.xlsx",
            "Breaks permissions",
            ["Employe", "Badge", "Fonction", "Type", "Debut", "Fin", "Statut", "Commentaire"],
            [
                [
                    f"{record.get('nom') or '-'} {record.get('prenom') or ''}".strip(),
                    record.get("numero_badge") or "",
                    record.get("fonction") or "",
                    _break_type_label(str(record.get("type_break") or "")),
                    record.get("date_debut") or "",
                    record.get("date_fin") or "",
                    record.get("statut") or "",
                    record.get("commentaire") or "",
                ]
                for record in records
            ],
        )
        notify(f"Export Excel cree: {output}", SUCCESS)
        root.update()

    def remove(break_id: int) -> None:
        delete_break(break_id)
        notify("Break/conge supprime.", MUTED)
        render_alerts()
        render_history()
        root.update()

    def plan_for_alert(employee: dict[str, Any]) -> None:
        controls["employe_id"].value = str(employee["id_employe"])
        controls["type_break"].value = "break"
        controls["date_debut"].value = employee["date_break_suggeree"]
        controls["date_fin"].value = employee["date_retour_suggeree"]
        controls["statut"].value = "planifie"
        controls["commentaire"].value = "Break apres deux semaines de travail"
        notify("Proposition chargee dans le formulaire.", PRIMARY)
        root.update()

    def render_form(values: dict[str, Any]) -> None:
        employee_options = [
            ft.dropdown.Option(
                str(employee["id_employe"]),
                f"{employee.get('nom') or employee.get('nom_complet') or '-'} {employee.get('prenom') or ''} - {employee.get('numero_badge') or 'sans badge'}",
            )
            for employee in employees
        ]
        controls.clear()
        controls["employe_id"] = ft.Dropdown(label="Employe", value=values["employe_id"], options=employee_options)
        controls["type_break"] = ft.Dropdown(
            label="Type",
            value=values["type_break"],
            options=[ft.dropdown.Option(kind, _break_type_label(kind)) for kind in BREAK_TYPES],
        )
        controls["date_debut"] = ft.TextField(label="Date debut", value=values["date_debut"], hint_text="AAAA-MM-JJ")
        controls["date_fin"] = ft.TextField(label="Date fin", value=values["date_fin"], hint_text="AAAA-MM-JJ")
        controls["statut"] = ft.Dropdown(
            label="Statut",
            value=values["statut"],
            options=[ft.dropdown.Option(item) for item in BREAK_STATUSES],
        )
        controls["commentaire"] = ft.TextField(label="Commentaire", value=values["commentaire"])

        form_area.controls = [
            ft.ResponsiveRow(
                controls=[
                    ft.Container(controls["employe_id"], col={"sm": 12, "md": 6}),
                    ft.Container(controls["type_break"], col={"sm": 12, "md": 3}),
                    ft.Container(controls["statut"], col={"sm": 12, "md": 3}),
                    ft.Container(controls["date_debut"], col={"sm": 12, "md": 3}),
                    ft.Container(controls["date_fin"], col={"sm": 12, "md": 3}),
                    ft.Container(controls["commentaire"], col={"sm": 12, "md": 6}),
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.Row(
                controls=[
                    ft.ElevatedButton("Planifier", icon=ft.Icons.EVENT_AVAILABLE_OUTLINED, on_click=save),
                    ft.OutlinedButton("Reinitialiser", icon=ft.Icons.CLEAR_OUTLINED, on_click=lambda event: render_form(default_values())),
                    status,
                ],
                spacing=10,
                wrap=True,
            ),
        ]

    def render_alerts() -> None:
        alerts = list_break_alerts()
        due = alerts["due_breaks"]
        ending = alerts["ending_tomorrow"]
        alerts_area.controls = [
            ft.Text("Alertes", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
            _alert_block(
                "Employes a envoyer en break",
                "Apres deux semaines de travail sans break planifie.",
                due,
                WARNING,
                action=plan_for_alert,
            ),
            _alert_block(
                "Breaks qui finissent demain",
                "Verifier le retour au travail un jour avant la fin.",
                ending,
                DANGER,
            ),
        ]

    def render_history() -> None:
        state["records"] = list_breaks()
        records = filtered_history()
        history_area.controls = [
            ft.Text("Historique des breaks et permissions", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Row(
                controls=[
                    history_search,
                    history_type_filter,
                    history_status_filter,
                    ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Appliquer", on_click=refresh_history_filters),
                    ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_history_filters),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_history),
                    ft.Text(f"{len(records)} ligne(s)", size=12, color=MUTED),
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Employe")),
                            ft.DataColumn(ft.Text("Badge")),
                            ft.DataColumn(ft.Text("Fonction")),
                            ft.DataColumn(ft.Text("Type")),
                            ft.DataColumn(ft.Text("Debut")),
                            ft.DataColumn(ft.Text("Fin")),
                            ft.DataColumn(ft.Text("Statut")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(f"{record.get('nom') or '-'} {record.get('prenom') or ''}")),
                                    ft.DataCell(ft.Text(str(record.get("numero_badge") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("fonction") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("type_break") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("date_debut") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("date_fin") or "-"))),
                                    ft.DataCell(ft.Text(str(record.get("statut") or "-"))),
                                    ft.DataCell(
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            tooltip="Supprimer",
                                            icon_color=DANGER,
                                            on_click=lambda event, current=record: remove(current["id_break"]),
                                        )
                                    ),
                                ]
                            )
                            for record in records
                        ],
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=8,
                        heading_row_color="#F1F5F9",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    root = ft.Column(
        controls=[
            module_header(
                "Breaks et permissions",
                "Planification des breaks, permissions et conges annuels avec regles de duree.",
            ),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=14,
                content=ft.Column(
                    controls=[
                        ft.Text("Regles appliquees", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(
                            "Permission: 3 jours maximum comptabilises en permission; a partir du 4e jour, le TimeSheet marque l'employe en absence sans heures.",
                            size=12,
                            color=MUTED,
                        ),
                        ft.Text(
                            "Break annuel / annual leave: duree maximale autorisee de 30 jours.",
                            size=12,
                            color=MUTED,
                        ),
                    ],
                    spacing=4,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=18,
                content=form_area,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=18,
                content=alerts_area,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=18,
                content=history_area,
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    render_form(default_values())
    render_alerts()
    render_history()
    return root


def _alert_block(
    title: str,
    subtitle: str,
    rows: list[dict[str, Any]],
    color: str,
    action: Any | None = None,
) -> ft.Control:
    if not rows:
        content = ft.Text("Aucune alerte.", color=MUTED)
    else:
        content = ft.Column(
            controls=[
                ft.Container(
                    border=ft.border.all(1, "#E2E8F0"),
                    border_radius=8,
                    padding=10,
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=color),
                            ft.Text(f"{row.get('nom') or '-'} {row.get('prenom') or ''}", width=180),
                            ft.Text(str(row.get("numero_badge") or "-"), width=120),
                            ft.Text(str(row.get("fonction") or "-"), expand=True),
                            ft.Text(_alert_detail(row), width=180, color=MUTED),
                            ft.ElevatedButton(
                                "Planifier",
                                icon=ft.Icons.ADD_OUTLINED,
                                visible=action is not None,
                                on_click=lambda event, current=row: action(current) if action else None,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
                for row in rows
            ],
            spacing=8,
        )
    return ft.Column(
        controls=[
            ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text(subtitle, size=12, color=MUTED),
            content,
        ],
        spacing=8,
    )


def _alert_detail(row: dict[str, Any]) -> str:
    if "jours_travailles" in row:
        return f"{row['jours_travailles']} jours travailles"
    if row.get("date_fin"):
        return f"Fin: {row['date_fin']}"
    return "-"


def _break_type_label(kind: str) -> str:
    labels = {"break": "Break", "annual": "Break annuel", "permission": "Permission", "sick": "Malade"}
    return labels.get(kind, kind)

