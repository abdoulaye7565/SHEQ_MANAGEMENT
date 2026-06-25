from __future__ import annotations

import getpass
import socket
from datetime import date, timedelta
from typing import Any

import flet as ft

from app.services.lock_service import acquire_lock, get_lock_info, release_lock

from app.ui.components.tables import professional_data_table
from app.ui.components.confirm import confirm_action

from app.services import (
    create_break,
    create_break_for_employees,
    export_daily_lineup_pdf,
    export_daily_lineup_xlsx,
    list_employees,
    mark_employee_departure,
    return_employees_to_service,
    update_employee_shift,
)
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


from app.ui.components.dark_styles import BG, CARD, DARK_BORDER, DARK_MUTED, DARK_TEXT, ROW

PAGE_SIZE = 10
INNER = "#081525"


def employees_page(page: ft.Page | None = None, on_edit_employee: Any | None = None) -> ft.Control:
    state: dict[str, Any] = {"records": [], "selected": set(), "page": 0}
    status = ft.Text("", size=12, color=MUTED)
    table_area = ft.Column(spacing=10)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    right_area = ft.Column(spacing=12)
    loading_overlay = ft.Container(
        visible=False,
        alignment=ft.Alignment(0, 0),
        content=ft.Row(
            controls=[
                ft.ProgressRing(color=PRIMARY, width=22, height=22, stroke_width=2.5),
                ft.Text("Chargement...", color=DARK_MUTED, size=12),
            ],
            spacing=10,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    search_field = ft.TextField(
        label="Recherche",
        prefix_icon=ft.Icons.SEARCH,
        width=280,
        on_submit=lambda event: refresh_table(),
    )
    state_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Situation",
        value="all",
        width=190,
        options=[
            ft.dropdown.Option("all", "Toutes"),
            ft.dropdown.Option("work", "Au travail"),
            ft.dropdown.Option("break", "En break"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Malade"),
            ft.dropdown.Option("due", "Break du"),
            ft.dropdown.Option("planned", "Break planifie"),
        ],
    )
    site_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Site", value="all", width=180)
    function_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Fonction", value="all", width=220)
    shift_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Shift", value="all", width=170)
    badge_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Badge",
        value="all",
        width=170,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("with_badge", "Avec badge"),
            ft.dropdown.Option("without_badge", "Sans badge"),
            ft.dropdown.Option("valid", "Badge valide"),
            ft.dropdown.Option("soon", "Expire bientot"),
            ft.dropdown.Option("expired", "Expire"),
        ],
    )
    for control in (search_field, state_filter, site_filter, function_filter, shift_filter, badge_filter):
        control.bgcolor = ROW
        control.color = DARK_TEXT
        control.border_color = DARK_BORDER
        control.focused_border_color = PRIMARY
        control.label_style = ft.TextStyle(color=DARK_MUTED)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def selected_ids() -> list[int]:
        return sorted(int(item) for item in state["selected"])

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh_table(event: ft.ControlEvent | None = None) -> None:
        loading_overlay.visible = True
        try:
            loading_overlay.update()
        except RuntimeError:
            pass
        state["page"] = 0
        state["records"] = list_employees(search_field.value or "")
        current_ids = {int(record["id_employe"]) for record in state["records"]}
        state["selected"] = state["selected"] & current_ids
        refresh_filter_options()
        render_summary()
        render_table()
        loading_overlay.visible = False
        try:
            loading_overlay.update()
        except RuntimeError:
            pass
        _update()

    def refresh_filter_options() -> None:
        sites = sorted({str(record.get("site") or "-") for record in state["records"]})
        functions = sorted({str(record.get("fonction") or "-") for record in state["records"]})
        shifts = sorted({str(record.get("shift_code") or "-") for record in state["records"]})
        site_filter.options = [ft.dropdown.Option("all", "Tous les sites")]
        site_filter.options.extend(ft.dropdown.Option(item, item) for item in sites)
        function_filter.options = [ft.dropdown.Option("all", "Toutes les fonctions")]
        function_filter.options.extend(ft.dropdown.Option(item, item) for item in functions)
        shift_filter.options = [ft.dropdown.Option("all", "Tous les shifts")]
        shift_filter.options.extend(ft.dropdown.Option(item, _shift_filter_label(item)) for item in shifts)
        if site_filter.value not in {"all", *sites}:
            site_filter.value = "all"
        if function_filter.value not in {"all", *functions}:
            function_filter.value = "all"
        if shift_filter.value not in {"all", *shifts}:
            shift_filter.value = "all"

    def filtered_records() -> list[dict[str, Any]]:
        selected_state = str(state_filter.value or "all")
        selected_site = str(site_filter.value or "all")
        selected_function = str(function_filter.value or "all")
        selected_shift = str(shift_filter.value or "all")
        selected_badge = str(badge_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for record in state["records"]:
            current_state = str(record.get("current_state") or "work")
            days_until_break = record.get("days_until_break_due")
            has_badge = bool(record.get("numero_badge"))
            due = days_until_break is not None and int(days_until_break) <= 0
            planned = bool(record.get("next_planned_break_start"))

            if selected_state not in ("all", "due", "planned") and current_state != selected_state:
                continue
            if selected_state == "due" and not due:
                continue
            if selected_state == "planned" and not planned:
                continue
            if selected_site != "all" and str(record.get("site") or "-") != selected_site:
                continue
            if selected_function != "all" and str(record.get("fonction") or "-") != selected_function:
                continue
            if selected_shift != "all" and str(record.get("shift_code") or "-") != selected_shift:
                continue
            if selected_badge == "with_badge" and not has_badge:
                continue
            if selected_badge == "without_badge" and has_badge:
                continue
            if selected_badge == "valid" and record.get("badge_validity_state") != "valid":
                continue
            if selected_badge == "soon" and record.get("badge_validity_state") != "soon":
                continue
            if selected_badge == "expired" and record.get("badge_validity_state") != "expired":
                continue
            rows.append(record)
        return rows

    def toggle_selected(employee_id: int, selected: bool) -> None:
        if selected:
            state["selected"].add(employee_id)
        else:
            state["selected"].discard(employee_id)
        render_summary()
        render_table()
        _update()

    def select_visible(selected: bool) -> None:
        visible_ids = {int(record["id_employe"]) for record in filtered_records()}
        if selected:
            state["selected"].update(visible_ids)
        else:
            state["selected"].difference_update(visible_ids)
        render_summary()
        render_table()
        _update()

    def change_page(delta: int) -> None:
        rows = filtered_records()
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"]) + delta))
        render_table()
        _update()

    def _try_edit_employee(employee_id: int) -> None:
        """Acquire lock then open the employee editor."""
        current_user = getpass.getuser()
        if not acquire_lock("employes", str(employee_id), current_user, socket.gethostname()):
            lock_info = get_lock_info("employes", str(employee_id))
            if lock_info:
                msg = (
                    f"Fiche en cours de modification par {lock_info['utilisateur']}"
                    f" depuis {lock_info['verrouille_depuis']}"
                )
            else:
                msg = "Fiche verrouilee par un autre utilisateur."
            if page is not None:
                page.show_snack_bar(ft.SnackBar(ft.Text(msg), bgcolor=DANGER))
                page.update()
            else:
                notify(msg, DANGER)
                _update()
            return
        if on_edit_employee is not None:
            on_edit_employee(employee_id)

    def edit_selected_employee(event: ft.ControlEvent | None = None) -> None:
        ids = selected_ids()
        if len(ids) != 1:
            notify("Selectionne un seul employe pour le modifier.", DANGER)
            _update()
            return
        if on_edit_employee is None:
            notify("Edition indisponible depuis cet ecran.", DANGER)
            _update()
            return
        _try_edit_employee(ids[0])

    def exit_employee(
        employee_id: int,
        departure_type: str,
        departure_date: str,
        comment: str | None = None,
    ) -> None:
        try:
            mark_employee_departure(employee_id, departure_type, departure_date, comment)
            state["selected"].discard(employee_id)
            notify("Employe transfere dans les anciens employes.", SUCCESS)
            refresh_table()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def open_exit_dialog(record: dict[str, Any] | None = None) -> None:
        ids = [int(record["id_employe"])] if record else selected_ids()
        if not ids:
            notify("Selectionne au moins un employe.", DANGER)
            _update()
            return

        if page is None:
            for employee_id in ids:
                mark_employee_departure(employee_id, "autre", date.today().isoformat(), "Sortie depuis la liste")
            state["selected"].difference_update(ids)
            notify(f"{len(ids)} employe(s) transfere(s) dans les anciens employes.", SUCCESS)
            refresh_table()
            return

        type_field = ft.Dropdown(
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
            label="Motif",
            value="demissionne",
            options=[
                ft.dropdown.Option("demissionne", "Demission"),
                ft.dropdown.Option("licencie", "Licenciement"),
                ft.dropdown.Option("autre", "Autre sortie"),
            ],
            width=260,
        )
        date_field = ft.TextField(label="Date de sortie", value=date.today().isoformat(), hint_text="AAAA-MM-JJ")
        comment_field = ft.TextField(label="Commentaire", multiline=True, min_lines=2, max_lines=3)
        dialog_status = ft.Text("", size=12, color=MUTED)

        def close_dialog(event: ft.ControlEvent | None = None) -> None:
            page.pop_dialog()
            page.update()

        def confirm(event: ft.ControlEvent) -> None:
            try:
                for employee_id in ids:
                    mark_employee_departure(
                        employee_id,
                        str(type_field.value or ""),
                        str(date_field.value or ""),
                        str(comment_field.value or ""),
                    )
                close_dialog()
                state["selected"].difference_update(ids)
                notify(f"{len(ids)} employe(s) transfere(s) dans les anciens employes.", SUCCESS)
                refresh_table()
            except ValueError as exc:
                dialog_status.value = str(exc)
                dialog_status.color = DANGER
                page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Sortie d'effectif"),
                content=ft.Column(
                    controls=[
                        ft.Text(f"{len(ids)} employe(s) seront retires de la liste active et conserves dans les anciens employes."),
                        type_field,
                        date_field,
                        comment_field,
                        dialog_status,
                    ],
                    width=430,
                    tight=True,
                    spacing=12,
                ),
                actions=[
                    ft.TextButton("Annuler", on_click=close_dialog),
                    ft.TextButton("Valider la sortie", icon=ft.Icons.PERSON_OFF_OUTLINED, on_click=confirm),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def open_break_dialog(record: dict[str, Any] | None = None) -> None:
        ids = [int(record["id_employe"])] if record else selected_ids()
        if not ids:
            notify("Selectionne au moins un employe.", DANGER)
            _update()
            return

        start = _suggested_break_start(record)
        end = start + timedelta(days=7)
        title = (
            f"Mettre en break: {_employee_name(record)}"
            if record
            else f"Action groupe sur {len(ids)} employe(s)"
        )

        if page is None:
            _create_break_for_ids(ids, "break", start.isoformat(), end.isoformat(), "Action depuis la liste")
            return

        type_field = ft.Dropdown(
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
            label="Type",
            value="break",
            options=[
                ft.dropdown.Option("break", "Break"),
                ft.dropdown.Option("permission", "Permission"),
                ft.dropdown.Option("sick", "Maladie"),
            ],
            width=200,
        )
        start_field = ft.TextField(label="Date debut", value=start.isoformat(), hint_text="AAAA-MM-JJ")
        end_field = ft.TextField(label="Date fin", value=end.isoformat(), hint_text="AAAA-MM-JJ")
        comment_field = ft.TextField(label="Commentaire", value="Action depuis la liste des employes")
        dialog_status = ft.Text("", size=12, color=MUTED)

        def close_dialog(event: ft.ControlEvent | None = None) -> None:
            page.pop_dialog()
            page.update()

        def confirm(event: ft.ControlEvent) -> None:
            try:
                if record:
                    create_break(
                        {
                            "employe_id": ids[0],
                            "type_break": type_field.value,
                            "date_debut": start_field.value,
                            "date_fin": end_field.value,
                            "statut": "planifie",
                            "commentaire": comment_field.value,
                        }
                    )
                    created = 1
                else:
                    created = create_break_for_employees(
                        {
                            "employee_ids": ids,
                            "type_break": type_field.value,
                            "date_debut": start_field.value,
                            "date_fin": end_field.value,
                            "statut": "planifie",
                            "commentaire": comment_field.value,
                        }
                    )
                close_dialog()
                state["selected"].clear()
                notify(f"{created} employe(s) mis a jour.", SUCCESS)
                refresh_table()
            except ValueError as exc:
                dialog_status.value = str(exc)
                dialog_status.color = DANGER
                page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(title),
                content=ft.Column(
                    controls=[type_field, start_field, end_field, comment_field, dialog_status],
                    width=430,
                    tight=True,
                    spacing=12,
                ),
                actions=[
                    ft.TextButton("Annuler", on_click=close_dialog),
                    ft.TextButton("Planifier", icon=ft.Icons.BEACH_ACCESS_OUTLINED, on_click=confirm),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _create_break_for_ids(
        ids: list[int],
        break_type: str,
        start: str,
        end: str,
        comment: str,
    ) -> None:
        created = create_break_for_employees(
            {
                "employee_ids": ids,
                "type_break": break_type,
                "date_debut": start,
                "date_fin": end,
                "statut": "planifie",
                "commentaire": comment,
            }
        )
        state["selected"].clear()
        notify(f"{created} employe(s) mis a jour.", SUCCESS)
        refresh_table()

    def bulk_return_to_service(record: dict[str, Any] | None = None) -> None:
        ids = [int(record["id_employe"])] if record else selected_ids()
        confirm_action(
            page,
            "Remettre en service",
            f"{len(ids)} employe(s) seront remis au statut de travail.",
            lambda: _bulk_return_to_service(ids),
            confirm_label="Remettre en service",
        )

    def _bulk_return_to_service(ids: list[int]) -> None:
        try:
            updated = return_employees_to_service(ids)
            state["selected"].clear()
            notify(f"{updated} employe(s) remis en service.", SUCCESS)
            refresh_table()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_list(event: ft.ControlEvent | None = None) -> None:
        records = filtered_records()
        output = export_daily_lineup_xlsx(records)
        notify(f"List of OREZONE Employee cree: {output}", SUCCESS)
        _update()

    def export_list_pdf(event: ft.ControlEvent | None = None) -> None:
        records = filtered_records()
        output = export_daily_lineup_pdf(records)
        notify(f"PDF List of OREZONE Employee pret: {output}", SUCCESS)
        _update()

    def change_shift(shift_code: str, record: dict[str, Any] | None = None) -> None:
        ids = [int(record["id_employe"])] if record else selected_ids()
        if len(ids) > 1:
            label = "Day Shift" if shift_code == "DAY" else "Night Shift"
            confirm_action(
                page,
                "Changer le shift",
                f"{len(ids)} employe(s) seront affectes a {label}.",
                lambda: _change_shift(ids, shift_code),
                confirm_label="Appliquer",
            )
            return
        _change_shift(ids, shift_code)

    def _change_shift(ids: list[int], shift_code: str) -> None:
        try:
            updated = update_employee_shift(ids, shift_code)
            state["selected"].clear()
            label = "Day Shift" if shift_code == "DAY" else "Night Shift"
            notify(f"{updated} employe(s) affecte(s) a {label}.", SUCCESS)
            refresh_table()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        state_filter.value = "all"
        site_filter.value = "all"
        function_filter.value = "all"
        shift_filter.value = "all"
        badge_filter.value = "all"
        refresh_table()

    def render_summary() -> None:
        records = filtered_records()
        active_breaks = sum(1 for record in records if record.get("current_state") != "work")
        planned = sum(1 for record in records if record.get("next_planned_break_start"))
        day_shift = sum(1 for record in records if record.get("shift_code") == "DAY")
        night_shift = sum(1 for record in records if record.get("shift_code") == "NIGHT")
        badge_risk = sum(1 for record in records if record.get("badge_validity_state") in {"soon", "expired", "unknown", "invalid", "missing"})
        summary_row.controls = [
            _summary_chip("Employes affiches", len(records), PRIMARY, ft.Icons.PEOPLE_ALT_OUTLINED, f"Sur {len(state['records'])} employes"),
            _summary_chip("Day shift", day_shift, SUCCESS, ft.Icons.WB_SUNNY_OUTLINED, "Equipe de jour"),
            _summary_chip("Night shift", night_shift, PRIMARY, ft.Icons.NIGHTLIGHT_OUTLINED, "Equipe de nuit"),
            _summary_chip("En break", active_breaks, WARNING, ft.Icons.FREE_BREAKFAST_OUTLINED, "Actuellement"),
            _summary_chip("Badges a voir", badge_risk, DANGER, ft.Icons.REPORT_PROBLEM_OUTLINED, "Action requise"),
            _summary_chip("Planning", planned, "#8B5CF6", ft.Icons.CALENDAR_MONTH_OUTLINED, "Breaks planifies"),
        ]
        work_count = sum(1 for record in records if record.get("current_state") == "work")
        absent_count = max(len(records) - work_count - active_breaks, 0)
        right_area.controls = [
            _side_panel(
                "Informations rapides",
                [
                    _info_line(ft.Icons.PEOPLE_ALT_OUTLINED, "Employes actifs", len(records), DARK_TEXT),
                    _info_line(ft.Icons.FREE_BREAKFAST_OUTLINED, "En break", active_breaks, WARNING),
                    _info_line(ft.Icons.BADGE_OUTLINED, "Badges a renouveler", badge_risk, DANGER),
                    _info_line(ft.Icons.CALENDAR_MONTH_OUTLINED, "Breaks planifies", planned, PRIMARY),
                ],
            ),
            _distribution_panel(work_count, active_breaks, absent_count, len(records)),
            _assistant_panel(),
        ]

    def render_table() -> None:
        records = filtered_records()
        max_page = max((len(records) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"])))
        start = int(state["page"]) * PAGE_SIZE
        page_records = records[start : start + PAGE_SIZE]
        if not records:
            table_content: ft.Control = ft.Container(
                bgcolor=ROW,
                border=ft.border.all(1, DARK_BORDER),
                border_radius=8,
                padding=18,
                content=ft.Text("Aucun employe ne correspond aux filtres.", color=DARK_MUTED),
            )
        else:
            table_content = ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("")),
                            ft.DataColumn(ft.Text("Employe")),
                            ft.DataColumn(ft.Text("Badge")),
                            ft.DataColumn(ft.Text("Validite badge")),
                            ft.DataColumn(ft.Text("Fonction")),
                            ft.DataColumn(ft.Text("Site")),
                            ft.DataColumn(ft.Text("Shift")),
                            ft.DataColumn(ft.Text("Situation")),
                            ft.DataColumn(ft.Text("Prochain break")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                selected=int(record["id_employe"]) in state["selected"],
                                color="#123B46" if int(record["id_employe"]) in state["selected"] else None,
                                cells=[
                                    ft.DataCell(
                                        ft.Checkbox(
                                            value=int(record["id_employe"]) in state["selected"],
                                            on_change=lambda event, current=record: toggle_selected(
                                                int(current["id_employe"]),
                                                bool(event.control.value),
                                            ),
                                        )
                                    ),
                                    ft.DataCell(
                                        ft.Column(
                                            controls=[
                                                ft.Text(_employee_name(record), color=DARK_TEXT, weight=ft.FontWeight.BOLD),
                                                ft.Text(str(record.get("matricule") or "-"), size=11, color=DARK_MUTED),
                                            ],
                                            spacing=1,
                                        )
                                    ),
                                    ft.DataCell(ft.Text(str(record.get("numero_badge") or "-"), color=DARK_MUTED)),
                                    ft.DataCell(_badge_validity_badge(record)),
                                    ft.DataCell(ft.Text(str(record.get("fonction") or "-"), color=DARK_TEXT)),
                                    ft.DataCell(ft.Text(str(record.get("site") or "-"), color=DARK_MUTED)),
                                    ft.DataCell(_shift_badge(record.get("shift_code"), record.get("shift"))),
                                    ft.DataCell(_state_badge(record.get("current_state"))),
                                    ft.DataCell(ft.Text(_break_due_text(record), color=_break_due_color(record))),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(
                                                    icon=ft.Icons.EDIT_OUTLINED,
                                                    tooltip="Modifier la fiche employe",
                                                    icon_color=TEXT,
                                                    on_click=lambda event, current=record: _try_edit_employee(int(current["id_employe"])),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.WB_SUNNY_OUTLINED,
                                                    tooltip="Affecter au Day Shift",
                                                    icon_color=PRIMARY,
                                                    on_click=lambda event, current=record: change_shift("DAY", current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.NIGHTLIGHT_OUTLINED,
                                                    tooltip="Affecter au Night Shift",
                                                    icon_color=PRIMARY,
                                                    on_click=lambda event, current=record: change_shift("NIGHT", current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.BEACH_ACCESS_OUTLINED,
                                                    tooltip="Planifier un break, une permission ou une maladie",
                                                    icon_color=PRIMARY,
                                                    on_click=lambda event, current=record: open_break_dialog(current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.WORK_OUTLINE,
                                                    tooltip="Remettre en service",
                                                    icon_color=SUCCESS,
                                                    on_click=lambda event, current=record: bulk_return_to_service(current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.DELETE_OUTLINE,
                                                    tooltip="Sortie d'effectif",
                                                    icon_color=DANGER,
                                                    on_click=lambda event, current=record: open_exit_dialog(current),
                                                ),
                                            ],
                                            spacing=0,
                                        )
                                    ),
                                ],
                            )
                            for record in page_records
                        ],
                        bgcolor=ROW,
                        border=ft.border.all(1, DARK_BORDER),
                        border_radius=8,
                        heading_row_color="#142B45",
                        horizontal_lines=ft.BorderSide(1, DARK_BORDER),
                        vertical_lines=ft.BorderSide(1, DARK_BORDER),
                        heading_text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                        data_text_style=ft.TextStyle(size=12, color=DARK_MUTED),
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            )

        table_area.controls = [
            ft.Row(
                controls=[
                    ft.OutlinedButton(
                        "Tout selectionner",
                        icon=ft.Icons.SELECT_ALL_OUTLINED,
                        on_click=lambda event: select_visible(True),
                    ),
                    ft.OutlinedButton(
                        "Deselectionner",
                        icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                        on_click=lambda event: select_visible(False),
                    ),
                    ft.OutlinedButton(
                        "Modifier selection",
                        icon=ft.Icons.EDIT_OUTLINED,
                        on_click=edit_selected_employee,
                    ),
                    ft.ElevatedButton(
                        "Mettre en break",
                        icon=ft.Icons.BEACH_ACCESS_OUTLINED,
                        on_click=lambda event: open_break_dialog(),
                    ),
                    ft.OutlinedButton(
                        "Day Shift",
                        icon=ft.Icons.WB_SUNNY_OUTLINED,
                        on_click=lambda event: change_shift("DAY"),
                    ),
                    ft.OutlinedButton(
                        "Night Shift",
                        icon=ft.Icons.NIGHTLIGHT_OUTLINED,
                        on_click=lambda event: change_shift("NIGHT"),
                    ),
                    ft.OutlinedButton(
                        "Remettre en service",
                        icon=ft.Icons.WORK_OUTLINE,
                        on_click=lambda event: bulk_return_to_service(),
                    ),
                    ft.OutlinedButton(
                        "Sortie d'effectif",
                        icon=ft.Icons.PERSON_OFF_OUTLINED,
                        on_click=lambda event: open_exit_dialog(),
                    ),
                    ft.OutlinedButton(
                        "Liste Excel",
                        icon=ft.Icons.DOWNLOAD_OUTLINED,
                        on_click=export_list,
                    ),
                    ft.OutlinedButton(
                        "Liste PDF",
                        icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                        on_click=export_list_pdf,
                    ),
                    status,
                ],
                spacing=8,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.Text(
                        f"{start + 1 if records else 0}-{start + len(page_records)} / {len(records)} ligne(s) | {len(state['selected'])} selectionne(s)",
                        size=12,
                        color=MUTED,
                    ),
                    ft.OutlinedButton(
                        "Precedent",
                        icon=ft.Icons.ARROW_BACK,
                        disabled=int(state["page"]) <= 0,
                        on_click=lambda event: change_page(-1),
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=6),
                        bgcolor=PRIMARY,
                        border=ft.border.all(1, PRIMARY),
                        border_radius=8,
                        content=ft.Text(f"Page {int(state['page']) + 1}/{max_page + 1}", size=12, color="#FFFFFF"),
                    ),
                    ft.OutlinedButton(
                        "Suivant",
                        icon=ft.Icons.ARROW_FORWARD,
                        disabled=int(state["page"]) >= max_page,
                        on_click=lambda event: change_page(1),
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            table_content,
        ]

    root = ft.Container(
        bgcolor=BG,
        expand=True,
        content=ft.Column(
        controls=[
            summary_row,
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, DARK_BORDER),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Recherche & filtres", color=DARK_TEXT, size=15, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                search_field,
                                state_filter,
                                site_filter,
                                function_filter,
                                shift_filter,
                                badge_filter,
                                ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, tooltip="Appliquer", on_click=refresh_table),
                                ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, tooltip="Reinitialiser", on_click=reset_filters),
                                loading_overlay,
                            ],
                            spacing=10,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=14,
                ),
            ),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        col={"xs": 12, "xl": 9},
                        bgcolor=CARD,
                        border=ft.border.all(1, DARK_BORDER),
                        border_radius=8,
                        padding=14,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Column(
                                            controls=[
                                                ft.Text("Liste des employes", color=DARK_TEXT, size=16, weight=ft.FontWeight.BOLD),
                                                ft.Text("Situation, badges, shifts et prochaines actions.", color=DARK_MUTED, size=11),
                                            ],
                                            spacing=2,
                                        ),
                                        ft.Container(expand=True),
                                    ]
                                ),
                                table_area,
                            ],
                            spacing=12,
                        ),
                    ),
                    ft.Container(col={"xs": 12, "xl": 3}, content=right_area),
                ],
                spacing=12,
                run_spacing=12,
            ),
        ],
        spacing=12,
        ),
    )

    refresh_table()
    return root


def _employee_name(record: dict[str, Any] | None) -> str:
    if not record:
        return "-"
    if record.get("nom") or record.get("prenom"):
        return f"{record.get('nom') or ''} {record.get('prenom') or ''}".strip()
    return str(record.get("nom_complet") or "-")


def _suggested_break_start(record: dict[str, Any] | None = None) -> date:
    if record and record.get("next_break_due_date"):
        due = date.fromisoformat(str(record["next_break_due_date"]))
        return max(due, date.today())
    return date.today()


def _summary_chip(label: str, value: int, color: str, icon: str, detail: str = "") -> ft.Control:
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4, "xl": 2},
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    border_radius=8,
                    bgcolor=color,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color="#FFFFFF", size=22),
                ),
                ft.Column(
                    controls=[
                        ft.Text(label, color=DARK_MUTED, size=11),
                        ft.Text(str(value), color=DARK_TEXT, size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(detail, color=DARK_MUTED, size=9),
                    ],
                    spacing=0,
                ),
            ],
            spacing=10,
        ),
    )


def _shift_badge(shift_code: str | None, shift_label: str | None) -> ft.Control:
    color = PRIMARY if shift_code == "DAY" else WARNING if shift_code == "NIGHT" else MUTED
    label = "Day" if shift_code == "DAY" else "Night" if shift_code == "NIGHT" else str(shift_label or "-")
    return ft.Container(
        bgcolor=ROW,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color),
    )


def _shift_filter_label(shift_code: str) -> str:
    return {"DAY": "Day Shift", "NIGHT": "Night Shift", "BREAK": "Break"}.get(shift_code, shift_code)


def _state_badge(state: str | None) -> ft.Control:
    labels = {
        "work": ("Au travail", SUCCESS),
        "break": ("En break", WARNING),
        "permission": ("Permission", PRIMARY),
        "sick": ("Malade", DANGER),
    }
    label, color = labels.get(str(state or "work"), ("Au travail", SUCCESS))
    return ft.Container(
        bgcolor=ROW,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color),
    )


def _badge_validity_badge(record: dict[str, Any]) -> ft.Control:
    state = str(record.get("badge_validity_state") or "unknown")
    color = {
        "valid": SUCCESS,
        "soon": WARNING,
        "expired": DANGER,
        "missing": DANGER,
        "invalid": DANGER,
        "unknown": WARNING,
    }.get(state, MUTED)
    text_color = DARK_TEXT
    label = str(record.get("badge_validity_label") or "-")
    return ft.Container(
        bgcolor=color,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=text_color),
    )


def _state_text(state: str | None) -> str:
    labels = {
        "work": "Au travail",
        "break": "En break",
        "permission": "Permission",
        "sick": "Malade",
    }
    return labels.get(str(state or "work"), "Au travail")


def _break_due_text(record: dict[str, Any]) -> str:
    if record.get("next_planned_break_start"):
        return f"Planifie: {record['next_planned_break_start']}"
    due_date = str(record.get("next_break_due_date") or "-")
    days = record.get("days_until_break_due")
    if days is None:
        return due_date
    days_int = int(days)
    if days_int < 0:
        return f"En retard: {due_date}"
    if days_int == 0:
        return f"Aujourd'hui: {due_date}"
    return f"{due_date} ({days_int} j)"


def _break_due_color(record: dict[str, Any]) -> str:
    if record.get("next_planned_break_start"):
        return PRIMARY
    days = record.get("days_until_break_due")
    if days is None:
        return MUTED
    if int(days) <= 0:
        return DANGER
    if int(days) <= 3:
        return WARNING
    return DARK_TEXT


def _side_panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[
                ft.Text(title, color=DARK_TEXT, size=14, weight=ft.FontWeight.BOLD),
                ft.Divider(height=1, color=DARK_BORDER),
                *controls,
            ],
            spacing=10,
        ),
    )


def _info_line(icon: str, label: str, value: Any, color: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Icon(icon, color=color, size=17),
            ft.Text(label, color=DARK_MUTED, size=11, expand=True),
            ft.Text(str(value), color=color, size=13, weight=ft.FontWeight.BOLD),
        ],
        spacing=8,
    )


def _distribution_panel(work: int, breaks: int, absent: int, total: int) -> ft.Control:
    safe_total = max(total, 1)
    return _side_panel(
        "Repartition par situation",
        [
            ft.Container(
                height=14,
                border_radius=7,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Row(
                    controls=[
                        ft.Container(expand=max(work, 1), bgcolor=SUCCESS),
                        ft.Container(expand=max(breaks, 1), bgcolor=WARNING),
                        ft.Container(expand=max(absent, 1), bgcolor=DANGER),
                    ],
                    spacing=0,
                ),
            ),
            _info_line(ft.Icons.WORK_OUTLINE, "Au travail", f"{work} ({round(work / safe_total * 100)}%)", SUCCESS),
            _info_line(ft.Icons.FREE_BREAKFAST_OUTLINED, "En break", f"{breaks} ({round(breaks / safe_total * 100)}%)", WARNING),
            _info_line(ft.Icons.PERSON_OFF_OUTLINED, "Autres situations", absent, DANGER),
        ],
    )


def _assistant_panel() -> ft.Control:
    return _side_panel(
        "Assistant IA",
        [
            ft.Row(
                controls=[
                    ft.Container(
                        width=42,
                        height=42,
                        border_radius=8,
                        bgcolor="#123B46",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.SMART_TOY_OUTLINED, color="#5EEAD4", size=24),
                    ),
                    ft.Text("Analyse RH rapide", color=DARK_TEXT, size=12, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            ft.Text("Qui est en break actuellement ?", color=DARK_MUTED, size=10),
            ft.Text("Montre les badges qui expirent bientot.", color=DARK_MUTED, size=10),
            ft.Text("Liste les employes par fonction.", color=DARK_MUTED, size=10),
        ],
    )
