from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    export_attendance_pdf,
    export_attendance_records_xlsx,
    export_rows_xlsx,
    get_attendance_day_lock,
    get_attendance_list,
    get_monthly_attendance_summary,
    list_attendance_audit,
    lock_attendance_day,
    save_attendance_day,
    set_day_activity,
    today_iso,
    unlock_attendance_day,
    validate_attendance_day,
)
from app.ui.components.module_header import module_header
from app.ui.components.feedback import show_feedback
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


ATTENDANCE_TIME_PRESETS = {
    "drilling": {
        "kind": "drilling",
        "label": "Drilling",
        "libelle": "Travaux drilling 06-18",
        "heure_entree": "06:00",
        "heure_sortie": "18:00",
    },
    "standard": {
        "kind": "standard",
        "label": "Sans drilling",
        "libelle": "Sans drilling 06-14",
        "heure_entree": "06:00",
        "heure_sortie": "14:00",
    },
}


def attendance_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {
        "rows": [],
        "switches": {},
        "time_controls": {},
        "selected_ids": set(),
        "locked": None,
    }
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=12, wrap=True)
    list_area = ft.Column(spacing=10)
    control_area = ft.Column(spacing=10)
    monthly_area = ft.Column(spacing=10)
    audit_area = ft.Column(spacing=10)

    date_field = ft.TextField(label="Date", value=today_iso(), hint_text="AAAA-MM-JJ", width=170)
    search_field = ft.TextField(
        label="Recherche",
        prefix_icon=ft.Icons.SEARCH,
        width=280,
        on_submit=lambda event: refresh_filters(),
    )
    status_filter = ft.Dropdown(
        label="Presence",
        value="all",
        width=170,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("present", "Presents"),
            ft.dropdown.Option("absent", "Absents"),
            ft.dropdown.Option("missing_hours", "Heures incompletes"),
            ft.dropdown.Option("overtime", "Plus de 12h"),
        ],
    )
    function_filter = ft.Dropdown(label="Fonction", value="all", width=220)
    shift_filter = ft.Dropdown(label="Shift", value="all", width=170)
    badge_filter = ft.Dropdown(
        label="Badge",
        value="all",
        width=170,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("with_badge", "Avec badge"),
            ft.dropdown.Option("without_badge", "Sans badge"),
        ],
    )
    time_case_filter = ft.Dropdown(
        label="Cas",
        value="drilling",
        width=220,
        options=[
            ft.dropdown.Option(
                key,
                f"{preset['label']} ({preset['heure_entree']}-{preset['heure_sortie']})",
            )
            for key, preset in ATTENDANCE_TIME_PRESETS.items()
        ],
    )
    apply_entry_field = ft.TextField(
        label="Entree",
        value=ATTENDANCE_TIME_PRESETS["drilling"]["heure_entree"],
        hint_text="HH:MM",
        width=105,
        dense=True,
    )
    apply_exit_field = ft.TextField(
        label="Sortie",
        value=ATTENDANCE_TIME_PRESETS["drilling"]["heure_sortie"],
        hint_text="HH:MM",
        width=105,
        dense=True,
    )

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color
        show_feedback(page, message, color)

    def selected_date() -> str:
        return str(date_field.value or "").strip()

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def sync_selected_hours(event: ft.ControlEvent | None = None) -> None:
        template = selected_time_template()
        if template is None:
            return
        apply_entry_field.value = template["heure_entree"]
        apply_exit_field.value = template["heure_sortie"]
        apply_hours_to_selected_rows(template["heure_entree"], template["heure_sortie"])
        notify(f"Horaire {template['label']} charge automatiquement.", PRIMARY)
        _update()

    time_case_filter.on_change = sync_selected_hours

    def apply_hours_to_selected_rows(entry_time: str, exit_time: str) -> None:
        selected_ids: set[int] = state["selected_ids"]
        if not selected_ids:
            return
        for row in state["rows"]:
            employee_id = int(row["id_employe"])
            if employee_id not in selected_ids:
                continue
            row["heure_entree"] = entry_time
            row["heure_sortie"] = exit_time
            controls = state["time_controls"].get(employee_id, {})
            if controls:
                controls["heure_entree"].value = entry_time
                controls["heure_sortie"].value = exit_time

    def load_day(event: ft.ControlEvent | None = None) -> None:
        try:
            state["rows"] = get_attendance_list(selected_date())
            state["locked"] = get_attendance_day_lock(selected_date())
            state["selected_ids"] = set()
            refresh_function_filter()
            notify("Liste de presence chargee.", SUCCESS)
            render_summary()
            render_list()
            render_control_panels()
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def time_value(employee_id: int, field: str) -> str:
        controls = state["time_controls"].get(employee_id, {})
        control = controls.get(field)
        return str(control.value or "").strip() if control else ""

    def row_time_value(row: dict[str, Any], field: str) -> str:
        employee_id = int(row["id_employe"])
        return time_value(employee_id, field) or str(row.get(field) or "").strip()

    def persist_day() -> None:
        sync_timesheet_activity()
        attendances = {
            int(row["id_employe"]): {
                "statut_presence": row["statut_presence"],
                "heure_entree": time_value(int(row["id_employe"]), "heure_entree"),
                "heure_sortie": time_value(int(row["id_employe"]), "heure_sortie"),
            }
            for row in state["rows"]
        }
        save_attendance_day(selected_date(), attendances)
        state["rows"] = get_attendance_list(selected_date())
        refresh_function_filter()

    def sync_timesheet_activity() -> None:
        template = selected_time_template()
        if template is None:
            return
        set_day_activity(
            selected_date(),
            template["kind"] == "drilling",
            f"Synchronise depuis la liste de presence: {template['label']}",
        )

    def save_day(event: ft.ControlEvent | None = None) -> None:
        try:
            persist_day()
            notify("Liste de presence enregistree.", SUCCESS)
            render_summary()
            render_list()
            render_control_panels()
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def export_day(event: ft.ControlEvent | None = None) -> None:
        try:
            if not state.get("locked"):
                persist_day()
            records = list(state["rows"])
            output = export_attendance_records_xlsx(
                selected_date(),
                [
                    {
                        "nom": row.get("nom") or row.get("nom_complet") or "",
                        "prenom": row.get("prenom") or "",
                        "numero_badge": row.get("numero_badge") or "",
                        "fonction": row.get("fonction") or "",
                        "shift": _shift_filter_label(str(row.get("shift_code") or "")),
                        "statut": "Present" if row.get("statut_presence") == "present" else "Absent",
                        "heure_entree": row_time_value(row, "heure_entree"),
                        "heure_sortie": row_time_value(row, "heure_sortie"),
                        "heures": preview_hours(row),
                        "controle": _control_label(row, preview_hours(row)),
                    }
                    for row in records
                ],
            )
            notify(f"Fichier Excel pret: {len(records)} employe(s) exporte(s) - {output}", SUCCESS)
            render_summary()
            render_list()
            render_control_panels()
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def export_monthly_summary(event: ft.ControlEvent | None = None) -> None:
        try:
            month_summary = get_monthly_attendance_summary(selected_date()[:7])
            output = export_rows_xlsx(
                f"synthese_presence_{month_summary['month']}.xlsx",
                "Synthese mensuelle",
                ["Nom", "Prenom", "Badge", "Fonction", "Jours suivis", "Jours presents", "Jours absents", "Heures"],
                [
                    [
                        row.get("nom") or "",
                        row.get("prenom") or "",
                        row.get("numero_badge") or "",
                        row.get("fonction") or "",
                        row.get("jours_suivis") or 0,
                        row.get("jours_presents") or 0,
                        row.get("jours_absents") or 0,
                        row.get("heures") or 0,
                    ]
                    for row in month_summary["rows"]
                ],
            )
            notify(f"Export mensuel cree: {len(month_summary['rows'])} employe(s) - {output}", SUCCESS)
        except Exception as exc:
            notify(f"Export mensuel impossible: {exc}", DANGER)
        _update()

    def export_audit_list(event: ft.ControlEvent | None = None) -> None:
        try:
            rows = list_attendance_audit(selected_date(), limit=500)
            output = export_rows_xlsx(
                f"audit_presence_{selected_date()}.xlsx",
                "Audit presence",
                ["Date changement", "Employe", "Champ", "Ancienne valeur", "Nouvelle valeur", "Utilisateur"],
                [
                    [
                        row.get("changed_at") or "",
                        f"{row.get('nom') or '-'} {row.get('prenom') or ''}".strip(),
                        row.get("champ") or "",
                        row.get("ancienne_valeur") or "",
                        row.get("nouvelle_valeur") or "",
                        row.get("changed_by") or "",
                    ]
                    for row in rows
                ],
            )
            notify(f"Export audit cree: {len(rows)} action(s) - {output}", SUCCESS)
        except Exception as exc:
            notify(f"Export audit impossible: {exc}", DANGER)
        _update()

    def export_pdf_day(event: ft.ControlEvent | None = None) -> None:
        try:
            if not state.get("locked"):
                persist_day()
            output = export_attendance_pdf(selected_date())
            notify(f"Fichier PDF pret: liste complete du {selected_date()} - {output}", SUCCESS)
            render_summary()
            render_list()
            render_control_panels()
        except Exception as exc:
            notify(f"Export PDF impossible: {exc}", DANGER)
        _update()

    def refresh_function_filter() -> None:
        functions = sorted({str(row.get("fonction") or "-") for row in state["rows"]})
        shifts = sorted({str(row.get("shift_code") or "-") for row in state["rows"]})
        current = function_filter.value
        current_shift = shift_filter.value
        function_filter.options = [ft.dropdown.Option("all", "Toutes les fonctions")]
        function_filter.options.extend(ft.dropdown.Option(name, name) for name in functions)
        function_filter.value = current if current in {"all", *functions} else "all"
        shift_filter.options = [ft.dropdown.Option("all", "Tous les shifts")]
        shift_filter.options.extend(ft.dropdown.Option(item, _shift_filter_label(item)) for item in shifts)
        shift_filter.value = current_shift if current_shift in {"all", *shifts} else "all"

    def filtered_rows() -> list[dict[str, Any]]:
        query = str(search_field.value or "").strip().lower()
        selected_status = str(status_filter.value or "all")
        selected_function = str(function_filter.value or "all")
        selected_shift = str(shift_filter.value or "all")
        selected_badge = str(badge_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for row in state["rows"]:
            searchable = " ".join(
                str(row.get(key) or "")
                for key in ("nom", "prenom", "nom_complet", "numero_badge", "fonction")
            ).lower()
            hours = preview_hours(row)
            has_badge = bool(row.get("numero_badge"))
            missing_hours = row["statut_presence"] == "present" and (
                not row_time_value(row, "heure_entree")
                or not row_time_value(row, "heure_sortie")
            )

            if query and query not in searchable:
                continue
            if selected_status in ("present", "absent") and row["statut_presence"] != selected_status:
                continue
            if selected_status == "missing_hours" and not missing_hours:
                continue
            if selected_status == "overtime" and hours <= 12:
                continue
            if selected_function != "all" and str(row.get("fonction") or "-") != selected_function:
                continue
            if selected_shift != "all" and str(row.get("shift_code") or "-") != selected_shift:
                continue
            if selected_badge == "with_badge" and not has_badge:
                continue
            if selected_badge == "without_badge" and has_badge:
                continue
            rows.append(row)
        return rows

    def refresh_filters(event: ft.ControlEvent | None = None) -> None:
        render_summary()
        render_list()
        _update()

    def reset_filters(event: ft.ControlEvent | None = None) -> None:
        search_field.value = ""
        status_filter.value = "all"
        function_filter.value = "all"
        shift_filter.value = "all"
        badge_filter.value = "all"
        refresh_filters()

    def mark_visible(present: bool) -> None:
        if state.get("locked"):
            notify("Journee verrouillee: modification impossible.", DANGER)
            _update()
            return
        visible_ids = {int(row["id_employe"]) for row in filtered_rows()}
        for row in state["rows"]:
            if int(row["id_employe"]) in visible_ids:
                row["statut_presence"] = "present" if present else "absent"
                switch = state["switches"].get(int(row["id_employe"]))
                if switch:
                    switch.value = present
        notify(
            "Les lignes affichees sont marquees presentes."
            if present
            else "Les lignes affichees sont marquees absentes.",
            WARNING,
        )
        render_summary()
        render_list()
        _update()

    def select_visible(selected: bool) -> None:
        visible_ids = {int(row["id_employe"]) for row in filtered_rows()}
        selected_ids: set[int] = state["selected_ids"]
        if selected:
            selected_ids.update(visible_ids)
            notify(f"{len(visible_ids)} ligne(s) affichee(s) selectionnee(s).", PRIMARY)
        else:
            selected_ids.difference_update(visible_ids)
            notify("Selection des lignes affichees retiree.", MUTED)
        render_list()
        _update()

    def confirm_selected_presence(event: ft.ControlEvent | None = None) -> None:
        confirm_selected_status("present")

    def confirm_selected_absence(event: ft.ControlEvent | None = None) -> None:
        confirm_selected_status("absent")

    def confirm_selected_status(status_value: str) -> None:
        if state.get("locked"):
            notify("Journee verrouillee: modification impossible.", DANGER)
            _update()
            return
        selected_ids: set[int] = state["selected_ids"]
        if not selected_ids:
            notify("Selectionne au moins un employe.", DANGER)
            _update()
            return
        entry_time = str(apply_entry_field.value or "").strip()
        exit_time = str(apply_exit_field.value or "").strip()
        if status_value == "present" and (not _valid_time(entry_time) or not _valid_time(exit_time)):
            notify("Format heure invalide. Utilise HH:MM.", DANGER)
            _update()
            return

        for row in state["rows"]:
            employee_id = int(row["id_employe"])
            if employee_id not in selected_ids:
                continue
            row["statut_presence"] = status_value
            row["heure_entree"] = entry_time if status_value == "present" else ""
            row["heure_sortie"] = exit_time if status_value == "present" else ""
            controls = state["time_controls"].get(employee_id, {})
            if controls:
                controls["heure_entree"].value = row["heure_entree"]
                controls["heure_sortie"].value = row["heure_sortie"]
            switch = state["switches"].get(employee_id)
            if switch:
                switch.value = status_value == "present"

        confirmed = len(selected_ids)
        try:
            persist_day()
        except ValueError as exc:
            notify(str(exc), DANGER)
            render_summary()
            render_list()
            _update()
            return
        state["selected_ids"] = set()
        if status_value == "present":
            notify(f"{confirmed} employe(s) confirme(s) present(s) ({entry_time}-{exit_time}).", SUCCESS)
        else:
            notify(f"{confirmed} employe(s) confirme(s) absent(s).", WARNING)
        render_summary()
        render_list()
        render_control_panels()
        _update()

    def apply_standard_hours() -> None:
        if state.get("locked"):
            notify("Journee verrouillee: modification impossible.", DANGER)
            _update()
            return
        template = selected_time_template()
        if template is None:
            notify("Aucun modele horaire selectionne.", DANGER)
            _update()
            return
        entry_time = str(apply_entry_field.value or "").strip()
        exit_time = str(apply_exit_field.value or "").strip()
        if not _valid_time(entry_time) or not _valid_time(exit_time):
            notify("Format heure invalide. Utilise HH:MM.", DANGER)
            _update()
            return
        for row in filtered_rows():
            employee_id = int(row["id_employe"])
            row["statut_presence"] = "present"
            controls = state["time_controls"].get(employee_id, {})
            if controls:
                controls["heure_entree"].value = entry_time
                controls["heure_sortie"].value = exit_time
            row["heure_entree"] = entry_time
            row["heure_sortie"] = exit_time
        notify(f"{template['libelle']} applique aux lignes affichees ({entry_time}-{exit_time}).", PRIMARY)
        render_summary()
        render_list()
        _update()

    def selected_time_template() -> dict[str, Any] | None:
        return ATTENDANCE_TIME_PRESETS.get(str(time_case_filter.value or ""))

    def validate_and_lock_day(event: ft.ControlEvent | None = None) -> None:
        try:
            persist_day()
            lock_attendance_day(selected_date(), locked_by="superviseur")
            state["locked"] = get_attendance_day_lock(selected_date())
            notify("Journee validee et verrouillee.", SUCCESS)
            render_summary()
            render_list()
            render_control_panels()
        except ValueError as exc:
            notify(str(exc), DANGER)
            render_control_panels()
        _update()

    def unlock_day(event: ft.ControlEvent | None = None) -> None:
        unlock_attendance_day(selected_date())
        state["locked"] = None
        notify("Journee deverrouillee.", WARNING)
        render_control_panels()
        _update()

    def update_row_status(employee_id: int, present: bool) -> None:
        if state.get("locked"):
            notify("Journee verrouillee: modification impossible.", DANGER)
            _update()
            return
        for row in state["rows"]:
            if int(row["id_employe"]) == employee_id:
                row["statut_presence"] = "present" if present else "absent"
                if not present:
                    controls = state["time_controls"].get(employee_id, {})
                    if controls:
                        controls["heure_entree"].value = ""
                        controls["heure_sortie"].value = ""
                break
        render_summary()
        render_list()
        _update()

    def preview_hours(row: dict[str, Any]) -> float:
        employee_id = int(row["id_employe"])
        entry = row_time_value(row, "heure_entree")
        exit_ = row_time_value(row, "heure_sortie")
        if row.get("statut_presence") != "present" or not entry or not exit_:
            return 0
        try:
            start = datetime.strptime(entry, "%H:%M")
            end = datetime.strptime(exit_, "%H:%M")
        except ValueError:
            return float(row.get("heures_travaillees") or 0)
        if end < start:
            end += timedelta(days=1)
        return round((end - start).seconds / 3600, 2)

    def render_summary() -> None:
        records = filtered_rows()
        total = len(records)
        present = sum(1 for row in records if row["statut_presence"] == "present")
        absent = total - present
        rate = round((present / total) * 100) if total else 0
        hours = round(sum(preview_hours(row) for row in records), 2)
        missing = sum(
            1
            for row in records
            if row["statut_presence"] == "present"
            and (
                not row_time_value(row, "heure_entree")
                or not row_time_value(row, "heure_sortie")
            )
        )
        summary_row.controls = [
            _summary_card("Lignes", total, PRIMARY, ft.Icons.FILTER_ALT_OUTLINED),
            _summary_card("Presents", present, SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _summary_card("Absents", absent, DANGER, ft.Icons.CANCEL_OUTLINED),
            _summary_card("Taux", f"{rate}%", WARNING, ft.Icons.QUERY_STATS_OUTLINED),
            _summary_card("Heures", hours, PRIMARY, ft.Icons.ACCESS_TIME_OUTLINED),
            _summary_card("A completer", missing, DANGER if missing else SUCCESS, ft.Icons.EDIT_CALENDAR_OUTLINED),
        ]

    def render_control_panels() -> None:
        lock = state.get("locked")
        validation = validate_attendance_day(selected_date())
        month_summary = get_monthly_attendance_summary(selected_date()[:7])
        audit_rows = list_attendance_audit(selected_date())
        control_area.controls = [
            ft.Row(
                controls=[
                    _status_chip(
                        "Journee verrouillee" if lock else "Journee modifiable",
                        SUCCESS if lock else WARNING,
                        ft.Icons.LOCK_OUTLINE if lock else ft.Icons.LOCK_OPEN_OUTLINED,
                    ),
                    ft.Text(
                        f"{len(validation['blocking'])} bloquant(s), {len(validation['warnings'])} alerte(s)",
                        color=DANGER if validation["blocking"] else MUTED,
                        size=12,
                    ),
                    ft.ElevatedButton(
                        "Valider et verrouiller",
                        icon=ft.Icons.VERIFIED_OUTLINED,
                        disabled=bool(lock),
                        on_click=validate_and_lock_day,
                    ),
                    ft.OutlinedButton(
                        "Deverrouiller",
                        icon=ft.Icons.LOCK_OPEN_OUTLINED,
                        disabled=not bool(lock),
                        on_click=unlock_day,
                    ),
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{issue.get('nom') or '-'} {issue.get('prenom') or ''}: {issue['message']}",
                        size=12,
                        color=DANGER if issue["niveau"] == "bloquant" else WARNING,
                    )
                    for issue in validation["issues"][:5]
                ],
                spacing=4,
            )
            if validation["issues"]
            else ft.Text("Controle pret: aucune anomalie detectee.", size=12, color=SUCCESS),
        ]
        monthly_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Synthese mensuelle", size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_monthly_summary),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    _summary_card("Mois", month_summary["month"], PRIMARY, ft.Icons.DATE_RANGE_OUTLINED),
                    _summary_card("Jours presents", month_summary["jours_presents"], SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
                    _summary_card("Jours absents", month_summary["jours_absents"], DANGER, ft.Icons.CANCEL_OUTLINED),
                    _summary_card("Heures", month_summary["heures"], PRIMARY, ft.Icons.ACCESS_TIME_OUTLINED),
                ],
                wrap=True,
                spacing=10,
            ),
        ]
        audit_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Historique des modifications", size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_audit_list),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{row['changed_at']} - {row.get('nom') or '-'} {row.get('prenom') or ''}: "
                        f"{row['champ']} {row.get('ancienne_valeur') or '-'} -> {row.get('nouvelle_valeur') or '-'}",
                        size=12,
                        color=MUTED,
                    )
                    for row in audit_rows[:8]
                ],
                spacing=4,
            )
            if audit_rows
            else ft.Text("Aucune modification auditee pour cette date.", size=12, color=MUTED),
        ]

    def render_list() -> None:
        state["switches"] = {}
        previous_time_controls = state["time_controls"]
        state["time_controls"] = {}
        rows_to_show = filtered_rows()
        if not state["rows"]:
            list_area.controls = [
                ft.Container(
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, "#BFDBFE"),
                    border_radius=8,
                    padding=18,
                    content=ft.Text(
                        "Aucun employe actif disponible pour cette date. Les employes en break sont exclus automatiquement.",
                        color=MUTED,
                    ),
                )
            ]
            return

        table = professional_data_table(
            columns=[
                ft.DataColumn(ft.Text("Sel.")),
                ft.DataColumn(ft.Text("Employe")),
                ft.DataColumn(ft.Text("Badge")),
                ft.DataColumn(ft.Text("Fonction")),
                ft.DataColumn(ft.Text("Shift")),
                ft.DataColumn(ft.Text("Statut")),
                ft.DataColumn(ft.Text("Entree")),
                ft.DataColumn(ft.Text("Sortie")),
                ft.DataColumn(ft.Text("Heures")),
                ft.DataColumn(ft.Text("Controle")),
            ],
            rows=[_attendance_row(row, previous_time_controls) for row in rows_to_show],
            border=ft.border.all(1, "#BFDBFE"),
            border_radius=8,
            heading_row_color="#DBEAFE",
        )

        list_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(
                        f"{len(rows_to_show)} ligne(s) affichee(s) | {len(state['selected_ids'])} selectionnee(s)",
                        color=MUTED,
                        size=12,
                    ),
                    status,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(controls=[table], scroll=ft.ScrollMode.AUTO),
        ]

    def _attendance_row(
        row: dict[str, Any],
        previous_time_controls: dict[int, dict[str, ft.Control]],
    ) -> ft.DataRow:
        employee_id = int(row["id_employe"])
        existing_controls = previous_time_controls.get(employee_id, {})
        entry_value = (
            str(existing_controls.get("heure_entree").value or "")
            if existing_controls.get("heure_entree")
            else str(row.get("heure_entree") or "")
        )
        exit_value = (
            str(existing_controls.get("heure_sortie").value or "")
            if existing_controls.get("heure_sortie")
            else str(row.get("heure_sortie") or "")
        )
        status_label = ft.Text(
            "Present" if row["statut_presence"] == "present" else "Absent",
            color=SUCCESS if row["statut_presence"] == "present" else DANGER,
            size=12,
            width=58,
        )

        def switch_changed(event: ft.ControlEvent, target_id: int = employee_id, label: ft.Text = status_label) -> None:
            present = bool(event.control.value)
            label.value = "Present" if present else "Absent"
            label.color = SUCCESS if present else DANGER
            update_row_status(target_id, present)

        def selection_changed(event: ft.ControlEvent, target_id: int = employee_id) -> None:
            selected_ids: set[int] = state["selected_ids"]
            if bool(event.control.value):
                selected_ids.add(target_id)
                template = selected_time_template()
                if template is not None:
                    row["heure_entree"] = template["heure_entree"]
                    row["heure_sortie"] = template["heure_sortie"]
                    entry_field.value = template["heure_entree"]
                    exit_field.value = template["heure_sortie"]
            else:
                selected_ids.discard(target_id)
            render_list()
            _update()

        entry_field = ft.TextField(
            value=entry_value,
            hint_text="HH:MM",
            width=86,
            dense=True,
            disabled=bool(state.get("locked")),
            on_submit=lambda event: refresh_filters(),
        )
        exit_field = ft.TextField(
            value=exit_value,
            hint_text="HH:MM",
            width=86,
            dense=True,
            disabled=bool(state.get("locked")),
            on_submit=lambda event: refresh_filters(),
        )
        state["time_controls"][employee_id] = {
            "heure_entree": entry_field,
            "heure_sortie": exit_field,
        }
        switch = ft.Switch(
            value=row["statut_presence"] == "present",
            active_color=SUCCESS,
            inactive_thumb_color=DANGER,
            disabled=bool(state.get("locked")),
            on_change=switch_changed,
        )
        state["switches"][employee_id] = switch
        selection = ft.Checkbox(
            value=employee_id in state["selected_ids"],
            disabled=bool(state.get("locked")),
            on_change=selection_changed,
        )
        hours = preview_hours(row)
        return ft.DataRow(
            cells=[
                ft.DataCell(selection),
                ft.DataCell(
                    ft.Column(
                        controls=[
                            ft.Text(_employee_name(row), color=TEXT, weight=ft.FontWeight.BOLD),
                            ft.Text(str(row.get("nom_complet") or ""), color=MUTED, size=11),
                        ],
                        spacing=1,
                    )
                ),
                ft.DataCell(ft.Text(str(row.get("numero_badge") or "-"))),
                ft.DataCell(ft.Text(str(row.get("fonction") or "-"))),
                ft.DataCell(_shift_badge(row.get("shift_code"), row.get("shift"))),
                ft.DataCell(ft.Row(controls=[switch, status_label], spacing=4, width=128)),
                ft.DataCell(entry_field),
                ft.DataCell(exit_field),
                ft.DataCell(ft.Text(str(hours), color=DANGER if hours > 12 else TEXT, weight=ft.FontWeight.BOLD)),
                ft.DataCell(_control_badge(row, hours)),
            ]
        )

    root = ft.Column(
        controls=[
            module_header(
                "Liste de presence",
                "Pointage journalier, controle des heures et export pour impression.",
            ),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                date_field,
                                ft.ElevatedButton("Charger", icon=ft.Icons.CALENDAR_MONTH_OUTLINED, on_click=load_day),
                                ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED, on_click=save_day),
                                ft.ElevatedButton("Confirmer presents", icon=ft.Icons.DONE_ALL_OUTLINED, on_click=confirm_selected_presence),
                                ft.PopupMenuButton(
                                    content=ft.OutlinedButton("Exports", icon=ft.Icons.DOWNLOAD_OUTLINED),
                                    items=[
                                        ft.PopupMenuItem(content=ft.Text("Liste complete Excel"), on_click=export_day),
                                        ft.PopupMenuItem(content=ft.Text("Liste complete PDF"), on_click=export_pdf_day),
                                        ft.PopupMenuItem(content=ft.Text("Synthese mensuelle"), on_click=export_monthly_summary),
                                        ft.PopupMenuItem(content=ft.Text("Audit presence"), on_click=export_audit_list),
                                    ],
                                ),
                                status,
                            ],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        summary_row,
                        ft.ExpansionTile(
                            title="Filtres",
                            leading=ft.Icons.FILTER_ALT_OUTLINED,
                            expanded=True,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[
                                ft.Row(
                                    controls=[
                                        search_field,
                                        status_filter,
                                        function_filter,
                                        shift_filter,
                                        badge_filter,
                                        ft.ElevatedButton("Appliquer", icon=ft.Icons.FILTER_ALT_OUTLINED, on_click=refresh_filters),
                                        ft.OutlinedButton("Reinitialiser", icon=ft.Icons.RESTART_ALT_OUTLINED, on_click=reset_filters),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                )
                            ],
                        ),
                        ft.ExpansionTile(
                            title="Actions groupees",
                            leading=ft.Icons.GROUP_WORK_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.OutlinedButton("Selectionner affiches", icon=ft.Icons.SELECT_ALL_OUTLINED, on_click=lambda event: select_visible(True)),
                                        ft.OutlinedButton("Vider selection", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=lambda event: select_visible(False)),
                                        ft.OutlinedButton("Presents affiches", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda event: mark_visible(True)),
                                        ft.OutlinedButton("Absents affiches", icon=ft.Icons.CANCEL_OUTLINED, on_click=lambda event: mark_visible(False)),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    controls=[
                                        time_case_filter,
                                        apply_entry_field,
                                        apply_exit_field,
                                        ft.OutlinedButton("Appliquer horaire", icon=ft.Icons.ACCESS_TIME_OUTLINED, on_click=lambda event: apply_standard_hours()),
                                        ft.ElevatedButton("Confirmer presents", icon=ft.Icons.DONE_ALL_OUTLINED, on_click=confirm_selected_presence),
                                        ft.OutlinedButton("Confirmer absents", icon=ft.Icons.PERSON_OFF_OUTLINED, on_click=confirm_selected_absence),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                        ),
                        ft.ExpansionTile(
                            title="Validation",
                            leading=ft.Icons.VERIFIED_OUTLINED,
                            controls_padding=ft.padding.only(left=10, right=10, bottom=10),
                            controls=[control_area],
                        ),
                    ],
                    spacing=14,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=list_area,
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=8,
                content=ft.ExpansionTile(
                    title="Syntheses et historique",
                    leading=ft.Icons.QUERY_STATS_OUTLINED,
                    controls_padding=ft.padding.only(left=8, right=8, bottom=8),
                    controls=[
                        ft.ResponsiveRow(
                            controls=[
                                ft.Container(content=monthly_area, col={"sm": 12, "lg": 6}),
                                ft.Container(content=audit_area, col={"sm": 12, "lg": 6}),
                            ],
                            spacing=14,
                            run_spacing=14,
                        )
                    ],
                ),
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    load_day()
    return root


def _employee_name(row: dict[str, Any]) -> str:
    if row.get("nom") or row.get("prenom"):
        return f"{row.get('nom') or ''} {row.get('prenom') or ''}".strip()
    return str(row.get("nom_complet") or "-")


def _summary_card(label: str, value: Any, color: str, icon: str) -> ft.Control:
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


def _status_chip(label: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=7),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=18),
                ft.Text(label, color=color, weight=ft.FontWeight.BOLD, size=12),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _shift_badge(shift_code: str | None, shift_label: str | None) -> ft.Control:
    color = PRIMARY if shift_code == "DAY" else WARNING if shift_code == "NIGHT" else MUTED
    label = "Day" if shift_code == "DAY" else "Night" if shift_code == "NIGHT" else str(shift_label or "-")
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color),
    )


def _shift_filter_label(shift_code: str) -> str:
    return {"DAY": "Day Shift", "NIGHT": "Night Shift", "BREAK": "Break"}.get(shift_code, shift_code)


def _control_badge(row: dict[str, Any], hours: float) -> ft.Control:
    label, color = _control_label_color(row, hours)
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color),
    )


def _control_label(row: dict[str, Any], hours: float) -> str:
    label, _ = _control_label_color(row, hours)
    return label


def _control_label_color(row: dict[str, Any], hours: float) -> tuple[str, str]:
    if row["statut_presence"] == "absent":
        label, color = "Absence", DANGER
    elif hours > 12:
        label, color = "A verifier", DANGER
    elif hours == 0:
        label, color = "A completer", WARNING
    else:
        label, color = "OK", SUCCESS
    return label, color


def _valid_time(value: str) -> bool:
    try:
        datetime.strptime(str(value or "").strip(), "%H:%M")
    except ValueError:
        return False
    return True

