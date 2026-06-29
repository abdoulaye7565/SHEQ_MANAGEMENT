from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    create_break,
    delete_break,
    export_active_breaks_xlsx,
    export_rows_xlsx,
    list_break_alerts,
    list_active_break_employees,
    list_breaks,
    list_employees,
    postpone_break,
    update_break_status,
)
from app.services.break_service import BREAK_STATUSES, BREAK_TYPES
from app.ui.components.confirm import confirm_action
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING

# Dark cockpit palette
_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"
_DK_TRACK  = "#1A3050"

_dk_overlays = {
    PRIMARY: "#0F2D5E",
    SUCCESS: "#052E16",
    DANGER:  "#3B0F0F",
    WARNING: "#2D1600",
}


def breaks_page(page: ft.Page | None = None) -> ft.Control:
    employees = list_employees()
    state: dict[str, Any] = {"records": []}
    controls: dict[str, ft.Control] = {}
    status = ft.Text("", size=12, color=_DK_MUTED)
    alerts_area = ft.Column(spacing=10)
    history_area = ft.Column(spacing=12)
    form_area = ft.Column(spacing=14)
    history_search = ft.TextField(label="Recherche historique", prefix_icon=ft.Icons.SEARCH, width=280)
    history_type_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
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
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Statut",
        value="all",
        width=170,
        options=[ft.dropdown.Option("all", "Tous")]
        + [ft.dropdown.Option(item, item) for item in BREAK_STATUSES],
    )

    def notify(message: str, color: str = _DK_MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

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
        except Exception as exc:
            notify(str(exc), DANGER)
        root.update()

    def confirm_break(break_id: int) -> None:
        try:
            update_break_status(break_id, "en_cours")
            notify("Break confirme et passe en cours.", SUCCESS)
            render_alerts()
            render_history()
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def cancel_break(break_id: int) -> None:
        confirm_action(
            page,
            "Annuler le break",
            "Ce break sera conserve dans l'historique avec le statut annule.",
            lambda: _cancel_break(break_id),
            confirm_label="Annuler le break",
            danger=True,
        )

    def _cancel_break(break_id: int) -> None:
        try:
            update_break_status(break_id, "annule")
            notify("Break annule.", WARNING)
            render_alerts()
            render_history()
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def open_postpone_dialog(record: dict[str, Any]) -> None:
        current_start = date.fromisoformat(str(record.get("date_debut") or date.today().isoformat()))
        current_end = date.fromisoformat(str(record.get("date_fin") or current_start.isoformat()))
        duration = max((current_end - current_start).days, 0)
        next_start = current_start + timedelta(days=7)
        next_end = next_start + timedelta(days=duration)
        start_field = ft.TextField(label="Nouvelle date debut", value=next_start.isoformat(), hint_text="AAAA-MM-JJ")
        end_field = ft.TextField(label="Nouvelle date fin", value=next_end.isoformat(), hint_text="AAAA-MM-JJ")
        dialog_status = ft.Text("", size=12, color=_DK_MUTED)

        def close(event: ft.ControlEvent | None = None) -> None:
            if page is not None:
                page.pop_dialog()
                page.update()

        def save_postpone(event: ft.ControlEvent | None = None) -> None:
            try:
                postpone_break(int(record["id_break"]), str(start_field.value or ""), str(end_field.value or ""))
                close()
                notify("Break reporte.", SUCCESS)
                render_alerts()
                render_history()
                _update()
            except Exception as exc:
                dialog_status.value = str(exc)
                dialog_status.color = DANGER
                if page is not None:
                    page.update()

        if page is None:
            postpone_break(int(record["id_break"]), str(start_field.value or ""), str(end_field.value or ""))
            notify("Break reporte.", SUCCESS)
            render_alerts()
            render_history()
            _update()
            return

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Reporter le break", color=_DK_TEXT, weight=ft.FontWeight.BOLD),
                content=ft.Column(controls=[start_field, end_field, dialog_status], spacing=10, width=360),
                actions=[
                    ft.TextButton("Fermer", on_click=close),
                    ft.ElevatedButton("Reporter", icon=ft.Icons.EVENT_REPEAT_OUTLINED, on_click=save_postpone),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

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

    def export_active(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_active_breaks_xlsx()
            notify(f"Export actifs cree: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        root.update()

    def remove(break_id: int) -> None:
        confirm_action(
            page,
            "Supprimer le break/conge",
            "Cette planification sera retiree de l'historique.",
            lambda: _remove(break_id),
            confirm_label="Supprimer",
            danger=True,
        )

    def _remove(break_id: int) -> None:
        delete_break(break_id)
        notify("Break/conge supprime.", _DK_MUTED)
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
        controls["employe_id"] = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Employe", value=values["employe_id"], options=employee_options)
        controls["type_break"] = ft.Dropdown(
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
            label="Type",
            value=values["type_break"],
            options=[ft.dropdown.Option(kind, _break_type_label(kind)) for kind in BREAK_TYPES],
        )
        controls["date_debut"] = ft.TextField(label="Date debut", value=values["date_debut"], hint_text="AAAA-MM-JJ")
        controls["date_fin"] = ft.TextField(label="Date fin", value=values["date_fin"], hint_text="AAAA-MM-JJ")
        controls["statut"] = ft.Dropdown(
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
            label="Statut",
            value=values["statut"],
            options=[ft.dropdown.Option(item) for item in BREAK_STATUSES],
        )
        controls["commentaire"] = ft.TextField(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Commentaire", value=values["commentaire"])

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
            ft.Text("Alertes", size=18, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
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
            ft.Text("Historique des breaks et permissions", size=18, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
            ft.Container(
                bgcolor=_DK_CARD,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                content=ft.Row(
                    controls=[
                        history_search,
                        history_type_filter,
                        history_status_filter,
                        ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Appliquer", on_click=refresh_history_filters),
                        ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_history_filters),
                        ft.OutlinedButton("Exporter historique", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_history),
                        ft.OutlinedButton("Exporter actifs", icon=ft.Icons.PEOPLE_OUTLINED, on_click=export_active),
                        ft.Text(f"{len(records)} ligne(s)", size=12, color=_DK_MUTED),
                    ],
                    spacing=10,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            ft.Container(
                bgcolor=_DK_CARD,
                content=ft.Row(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.DataTable(
                            bgcolor=_DK_CARD,
                            heading_row_color=_DK_HEAD,
                            horizontal_lines=ft.BorderSide(1, _DK_BORDER),
                            vertical_lines=ft.BorderSide(0, "transparent"),
                            data_row_color={
                                ft.ControlState.DEFAULT: _DK_CARD,
                                ft.ControlState.HOVERED: _DK_CARD2,
                            },
                            heading_text_style=ft.TextStyle(color=_DK_MUTED, weight=ft.FontWeight.BOLD, size=11),
                            data_text_style=ft.TextStyle(color=_DK_TEXT, size=11),
                            columns=[
                                ft.DataColumn(ft.Text("Employe", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Badge", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Fonction", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Type", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Debut", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Fin", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Statut", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Actions", color=_DK_MUTED, weight=ft.FontWeight.BOLD)),
                            ],
                            rows=[
                                ft.DataRow(
                                    cells=[
                                        ft.DataCell(ft.Text(f"{record.get('nom') or '-'} {record.get('prenom') or ''}", color=_DK_TEXT)),
                                        ft.DataCell(ft.Text(str(record.get("numero_badge") or "-"), color=_DK_TEXT)),
                                        ft.DataCell(ft.Text(str(record.get("fonction") or "-"), color=_DK_TEXT)),
                                        ft.DataCell(ft.Text(str(record.get("type_break") or "-"), color=_DK_TEXT)),
                                        ft.DataCell(ft.Text(str(record.get("date_debut") or "-"), color=_DK_TEXT)),
                                        ft.DataCell(ft.Text(str(record.get("date_fin") or "-"), color=_DK_TEXT)),
                                        ft.DataCell(ft.Text(str(record.get("statut") or "-"), color=_DK_TEXT)),
                                        ft.DataCell(_break_actions(record, confirm_break, cancel_break, open_postpone_dialog, remove)),
                                    ]
                                )
                                for record in records
                            ],
                        )
                    ],
                ),
            ),
        ]

    root = ft.Column(
        controls=[
            module_header(
                "Breaks et permissions",
                "Planification des breaks, permissions et conges annuels avec regles de duree.",
            ),
            # Rules info panel
            ft.Container(
                bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER),
                border_radius=12, padding=0,
                content=ft.Column([
                    ft.Container(
                        bgcolor=_DK_HEAD,
                        border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                        content=ft.Row([
                            ft.Container(width=3, height=14, bgcolor=PRIMARY, border_radius=2),
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=PRIMARY, size=16),
                            ft.Text("Regles appliquees", color=_DK_TEXT, size=14, weight=ft.FontWeight.BOLD),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        content=ft.Column([
                            ft.Text(
                                "Permission: 3 jours maximum comptabilises en permission; a partir du 4e jour, le TimeSheet marque l'employe en absence sans heures.",
                                size=12,
                                color=_DK_MUTED,
                            ),
                            ft.Text(
                                "Break annuel / annual leave: duree maximale autorisee de 30 jours.",
                                size=12,
                                color=_DK_MUTED,
                            ),
                        ], spacing=4),
                    ),
                ], spacing=0),
            ),
            # Form panel
            ft.Container(
                bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER),
                border_radius=12, padding=0,
                content=ft.Column([
                    ft.Container(
                        bgcolor=_DK_HEAD,
                        border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                        content=ft.Row([
                            ft.Container(width=3, height=14, bgcolor=SUCCESS, border_radius=2),
                            ft.Icon(ft.Icons.EVENT_AVAILABLE_OUTLINED, color=SUCCESS, size=16),
                            ft.Text("Planifier un break / permission", color=_DK_TEXT, size=14, weight=ft.FontWeight.BOLD),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        content=form_area,
                    ),
                ], spacing=0),
            ),
            # Alerts panel
            ft.Container(
                bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER),
                border_radius=12, padding=18,
                content=alerts_area,
            ),
            # History panel
            ft.Container(
                bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER),
                border_radius=12, padding=18,
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
    return ft.Container(bgcolor="#071321", expand=True, content=root)


def _break_actions(
    record: dict[str, Any],
    confirm_action_handler: Any,
    cancel_action_handler: Any,
    postpone_action_handler: Any,
    delete_action_handler: Any,
) -> ft.Control:
    break_id = int(record["id_break"])
    statut = str(record.get("statut") or "")
    return ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                tooltip="Confirmer le break",
                icon_color=SUCCESS,
                visible=statut == "planifie",
                on_click=lambda event: confirm_action_handler(break_id),
            ),
            ft.IconButton(
                icon=ft.Icons.CANCEL_OUTLINED,
                tooltip="Annuler le break",
                icon_color=WARNING,
                visible=statut in {"planifie", "en_cours"},
                on_click=lambda event: cancel_action_handler(break_id),
            ),
            ft.IconButton(
                icon=ft.Icons.EVENT_REPEAT_OUTLINED,
                tooltip="Reporter le break",
                icon_color=PRIMARY,
                visible=statut not in {"termine", "annule"},
                on_click=lambda event, current=record: postpone_action_handler(current),
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                tooltip="Supprimer",
                icon_color=DANGER,
                on_click=lambda event: delete_action_handler(break_id),
            ),
        ],
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _alert_block(
    title: str,
    subtitle: str,
    rows: list[dict[str, Any]],
    color: str,
    action: Any | None = None,
) -> ft.Control:
    if not rows:
        content = ft.Text("Aucune alerte.", color=_DK_MUTED)
    else:
        content = ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_DK_CARD2,
                    border=ft.border.all(1, _DK_BORDER),
                    border_radius=8,
                    padding=10,
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=color),
                            ft.Text(f"{row.get('nom') or '-'} {row.get('prenom') or ''}", width=180, color=_DK_TEXT),
                            ft.Text(str(row.get("numero_badge") or "-"), width=120, color=_DK_TEXT),
                            ft.Text(str(row.get("fonction") or "-"), expand=True, color=_DK_TEXT),
                            ft.Text(_alert_detail(row), width=180, color=_DK_MUTED),
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
            ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
            ft.Text(subtitle, size=12, color=_DK_MUTED),
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
