from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    current_timesheet_month,
    export_timesheet_audit_xlsx,
    export_timesheet_all_employees_xls,
    export_timesheet_annual_history_xls,
    export_timesheet_employee_xls,
    export_timesheet_selected_employees_xls,
    export_timesheet_xls,
    EmailConfigurationError,
    get_day_activity,
    get_timesheet,
    get_timesheet_lock,
    is_timesheet_locked,
    list_timesheet_audit,
    list_timesheet_history,
    list_timesheet_site_options,
    lock_timesheet_month,
    prepare_timesheet_outlook_draft,
    prepare_timesheet_whatsapp_share,
    set_day_activity,
    set_day_activity_range,
    send_timesheet_email,
    unlock_timesheet_month,
    update_timesheet_day_status,
)
from app.ui.components.feedback import show_feedback
from app.ui.components.confirm import confirm_action
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


WORK_DRILLING = "#2563EB"
WORK_STANDARD = "#16A34A"
HOLIDAY = "#22C55E"
REST = "#334155"
ABSENT = "#DC4545"
UNFILLED = "#475569"
BREAK = "#F59E0B"
PERMISSION = "#A855F7"
SICK = "#DC2626"
from app.ui.components.dark_styles import BG, BORDER, CARD, FIELD
DARK_TEXT = "#FFFFFF"
DARK_MUTED = "#9DB0C5"
PAGE_SIZE = 10
TIMESHEET_DAY_WIDTH = 38
TIMESHEET_DAY_HEIGHT = 31


def timesheet_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"timesheet": None, "history": [], "active": True, "page": 0, "view": "dashboard", "selected_emp_ids": []}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    calendar_area = ft.Column(spacing=10)
    history_area = ft.Column(spacing=8)
    audit_area = ft.Column(spacing=8)
    validation_area = ft.Column(spacing=6)
    dashboard_area = ft.Column(spacing=12)
    anomalies_area = ft.Column(spacing=10)
    content_area = ft.Container()
    nav_buttons: dict[str, ft.TextButton] = {}
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

    month_field = ft.TextField(
        label="Mois TimeSheet",
        value=current_timesheet_month(),
        hint_text="AAAA-MM",
        width=160,
    )
    site_scope_field = ft.Dropdown(label="TimeSheet site", value="all", width=250)
    activity_date_field = ft.TextField(label="Date activite", hint_text="AAAA-MM-JJ", width=170)
    drilling_switch = ft.Switch(label="Drilling actif", value=False, active_color=PRIMARY)
    day_type_field = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Type de jour",
        value="work",
        width=190,
        options=[
            ft.dropdown.Option("work", "Jour travaille"),
            ft.dropdown.Option("holiday", "Jour chome 8H"),
        ],
    )
    comment_field = ft.TextField(label="Commentaire", width=260)
    search_field = ft.TextField(label="Recherche", prefix_icon=ft.Icons.SEARCH, width=240)
    function_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Fonction", value="all", width=220)
    status_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Statut",
        value="all",
        width=180,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("worked_drilling", "12H drilling"),
            ft.dropdown.Option("worked_standard", "8H"),
            ft.dropdown.Option("holiday", "Jour chome 8H"),
            ft.dropdown.Option("rest", "Repos"),
            ft.dropdown.Option("absent", "Absent"),
            ft.dropdown.Option("unfilled", "Non renseigne"),
            ft.dropdown.Option("break", "Break"),
            ft.dropdown.Option("annual", "Annual leave"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Sick"),
        ],
    )
    week_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Semaine", value="all", width=140)
    site_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Site", value="all", width=160)
    group_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Groupe", value="all", width=180)
    shift_filter = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Shift", value="all", width=150)
    badge_filter = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Badge",
        value="all",
        width=160,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("with_badge", "Avec badge"),
            ft.dropdown.Option("without_badge", "Sans badge"),
        ],
    )
    bulk_start_field = ft.TextField(label="Debut drilling", hint_text="AAAA-MM-JJ", width=170)
    bulk_end_field = ft.TextField(label="Fin drilling", hint_text="AAAA-MM-JJ", width=170)
    bulk_status_start_field = ft.TextField(label="Debut statut", hint_text="AAAA-MM-JJ", width=170)
    bulk_status_end_field = ft.TextField(label="Fin statut", hint_text="AAAA-MM-JJ", width=170)
    bulk_status_value_field = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Statut a appliquer",
        value="rest",
        width=190,
        options=[
            ft.dropdown.Option("present", "Present"),
            ft.dropdown.Option("rest", "Repos"),
            ft.dropdown.Option("absent", "Absent"),
            ft.dropdown.Option("break", "Break"),
            ft.dropdown.Option("annual", "Annual leave"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Sick"),
        ],
    )
    selection_count_text = ft.Text("0 employe(s) dans la selection", size=11, color=MUTED)
    bulk_drilling_switch = ft.Switch(label="Drilling", value=True, active_color=PRIMARY)
    bulk_day_type_field = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Type periode",
        value="work",
        width=190,
        options=[
            ft.dropdown.Option("work", "Jours travailles"),
            ft.dropdown.Option("holiday", "Jours chomes 8H"),
        ],
    )
    edit_employee_field = ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), label="Employe", width=260)
    edit_date_field = ft.TextField(label="Date", hint_text="AAAA-MM-JJ", width=170)
    edit_status_field = ft.Dropdown(
        fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), 
        label="Statut",
        value="present",
        width=170,
        options=[
            ft.dropdown.Option("present", "Present"),
            ft.dropdown.Option("rest", "Repos"),
            ft.dropdown.Option("absent", "Absent"),
            ft.dropdown.Option("break", "Break"),
            ft.dropdown.Option("annual", "Annual leave"),
            ft.dropdown.Option("permission", "Permission"),
            ft.dropdown.Option("sick", "Sick"),
        ],
    )
    for control in (
        month_field,
        site_scope_field,
        activity_date_field,
        day_type_field,
        comment_field,
        search_field,
        function_filter,
        status_filter,
        week_filter,
        site_filter,
        group_filter,
        shift_filter,
        badge_filter,
        bulk_start_field,
        bulk_end_field,
        bulk_day_type_field,
        bulk_status_start_field,
        bulk_status_end_field,
        bulk_status_value_field,
        edit_employee_field,
        edit_date_field,
        edit_status_field,
    ):
        control.bgcolor = FIELD
        control.color = DARK_TEXT
        control.border_color = BORDER
        control.focused_border_color = PRIMARY
        control.label_style = ft.TextStyle(color=DARK_MUTED)

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color
        show_feedback(page, message, color)

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def selected_month() -> str:
        return str(month_field.value or "").strip()

    def selected_site_id() -> int | None:
        value = str(site_scope_field.value or "all")
        return None if value == "all" else int(value)

    def selected_site_label() -> str:
        value = str(site_scope_field.value or "all")
        for option in site_scope_field.options or []:
            if str(option.key) == value:
                return str(option.text or "Tous les sites")
        return "Tous les sites"

    def load_site_scope_options() -> None:
        options = list_timesheet_site_options()
        current = str(site_scope_field.value or "all")
        values = {str(option["value"]) for option in options}
        site_scope_field.options = [ft.dropdown.Option("all", "Tous les sites")]
        site_scope_field.options.extend(
            ft.dropdown.Option(str(option["value"]), str(option["label"]))
            for option in options
        )
        site_scope_field.value = current if current in {"all", *values} else "all"

    def refresh(event: ft.ControlEvent | None = None, automatic: bool = False) -> None:
        loading_overlay.visible = True
        try:
            loading_overlay.update()
        except RuntimeError:
            pass
        try:
            load_site_scope_options()
            state["timesheet"] = get_timesheet(selected_month(), site_id=selected_site_id())
            state["history"] = list_timesheet_history()
            days = state["timesheet"]["days"]
            if days and not activity_date_field.value and not automatic:
                activity_date_field.value = days[0]["date"]
                edit_date_field.value = days[0]["date"]
                bulk_start_field.value = days[0]["date"]
                bulk_end_field.value = days[0]["date"]
                load_activity()
            refresh_edit_options()
            refresh_filter_options()
            render()
            notify(
                "TimeSheet actualise automatiquement depuis la liste de presence."
                if automatic
                else "TimeSheet actualise depuis la liste de presence.",
                SUCCESS,
            )
        except Exception as exc:
            notify(str(exc) or type(exc).__name__, DANGER)
        loading_overlay.visible = False
        try:
            loading_overlay.update()
        except RuntimeError:
            pass
        _update()

    def refresh_filter_options() -> None:
        timesheet = state.get("timesheet") or {"rows": [], "week_labels": []}
        functions = sorted({str(row["employee"].get("fonction") or "-") for row in timesheet["rows"]})
        current_function = str(function_filter.value or "all")
        function_filter.options = [ft.dropdown.Option("all", "Toutes les fonctions")]
        function_filter.options.extend(ft.dropdown.Option(item, item) for item in functions)
        function_filter.value = current_function if current_function in {"all", *functions} else "all"

        weeks = list(timesheet.get("week_labels") or [])
        current_week = str(week_filter.value or "all")
        week_filter.options = [ft.dropdown.Option("all", "Toutes")]
        week_filter.options.extend(ft.dropdown.Option(item, item) for item in weeks)
        week_filter.value = current_week if current_week in {"all", *weeks} else "all"

        filter_specs = [
            (site_filter, "site", "Tous les sites"),
            (group_filter, "groupe", "Tous les groupes"),
            (shift_filter, "shift_code", "Tous les shifts"),
        ]
        for field, key, label in filter_specs:
            values = sorted({str(row["employee"].get(key) or "-") for row in timesheet["rows"]})
            current_value = str(field.value or "all")
            field.options = [ft.dropdown.Option("all", label)]
            field.options.extend(
                ft.dropdown.Option(value, _shift_label(value) if key == "shift_code" else value)
                for value in values
            )
            field.value = current_value if current_value in {"all", *values} else "all"

    def refresh_edit_options() -> None:
        timesheet = state.get("timesheet") or {"rows": []}
        employees = [
            row["employee"]
            for row in timesheet["rows"]
        ]
        current = str(edit_employee_field.value or "")
        edit_employee_field.options = [
            ft.dropdown.Option(
                str(employee["id_employe"]),
                f"{_employee_name(employee)} - {employee.get('numero_badge') or 'sans badge'}",
            )
            for employee in employees
        ]
        values = {str(employee["id_employe"]) for employee in employees}
        edit_employee_field.value = current if current in values else (
            str(employees[0]["id_employe"]) if employees else None
        )

    def load_activity(event: ft.ControlEvent | None = None) -> None:
        try:
            activity = get_day_activity(str(activity_date_field.value or ""))
            drilling_switch.value = bool(activity["has_drilling"])
            day_type_field.value = str(activity.get("day_type") or "work")
            comment_field.value = str(activity.get("commentaire") or "")
            notify("Activite du jour chargee.", MUTED)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def save_activity(event: ft.ControlEvent | None = None) -> None:
        try:
            set_day_activity(
                str(activity_date_field.value or ""),
                bool(drilling_switch.value),
                str(comment_field.value or ""),
                day_type=str(day_type_field.value or "work"),
            )
            notify("Activite du jour mise a jour. Le TimeSheet est recalcule.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def save_bulk_activity(event: ft.ControlEvent | None = None) -> None:
        try:
            updated = set_day_activity_range(
                str(bulk_start_field.value or ""),
                str(bulk_end_field.value or ""),
                bool(bulk_drilling_switch.value),
                str(comment_field.value or ""),
                day_type=str(bulk_day_type_field.value or "work"),
            )
            notify(f"{updated} jour(s) d'activite mis a jour.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def save_timesheet_edit(event: ft.ControlEvent | None = None) -> None:
        try:
            update_timesheet_day_status(
                int(edit_employee_field.value or 0),
                str(edit_date_field.value or ""),
                str(edit_status_field.value or ""),
            )
            notify("Modification enregistree. Le TimeSheet est recalcule depuis les donnees source.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def export_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            timesheet = get_timesheet(selected_month(), site_id=selected_site_id())
            output = export_timesheet_xls(selected_month(), site_id=selected_site_id())
            notify(f"Export Excel TimeSheet complet: {len(timesheet['rows'])} employe(s) exporte(s) - {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def send_timesheet_by_email(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_xls(selected_month(), site_id=selected_site_id())
            result = send_timesheet_email(
                "TimeSheet 21-20",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"TimeSheet envoye par email a {', '.join(result['recipients'])}.", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        _update()

    def prepare_timesheet_in_outlook(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_xls(selected_month(), site_id=selected_site_id())
            result = prepare_timesheet_outlook_draft(
                "TimeSheet 21-20",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"Brouillon Outlook prepare pour {', '.join(result['recipients'])}.", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        _update()

    def prepare_timesheet_in_whatsapp(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_xls(selected_month(), site_id=selected_site_id())
            result = prepare_timesheet_whatsapp_share(
                "TimeSheet 21-20",
                selected_month(),
                output,
                site_label=selected_site_label(),
            )
            notify(f"WhatsApp ouvert pour {len(result['targets'])} destinataire(s). Fichier a joindre: {result['attachment']}", SUCCESS)
        except (ValueError, EmailConfigurationError) as exc:
            notify(str(exc), DANGER)
        _update()

    def export_employee_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            employee_id = int(edit_employee_field.value or 0)
            output = export_timesheet_employee_xls(selected_month(), employee_id)
            employee_label = edit_employee_field.value or employee_id
            notify(f"Export Excel TimeSheet individuel cree pour {employee_label}: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def _update_selection_text() -> None:
        n = len(state["selected_emp_ids"])
        selection_count_text.value = f"{n} employe(s) dans la selection"
        selection_count_text.color = PRIMARY if n else MUTED

    def add_to_selection(event: ft.ControlEvent | None = None) -> None:
        try:
            emp_id = int(edit_employee_field.value or 0)
            if not emp_id:
                notify("Choisis un employe.", DANGER)
                return
            if emp_id not in state["selected_emp_ids"]:
                state["selected_emp_ids"].append(emp_id)
            _update_selection_text()
            notify(f"Employe {emp_id} ajoute a la selection ({len(state['selected_emp_ids'])} total).", SUCCESS)
        except (ValueError, TypeError) as exc:
            notify(str(exc), DANGER)
        _update()

    def clear_selection(event: ft.ControlEvent | None = None) -> None:
        state["selected_emp_ids"].clear()
        _update_selection_text()
        notify("Selection videe.", MUTED)
        _update()

    def export_selection(event: ft.ControlEvent | None = None) -> None:
        try:
            ids = list(state["selected_emp_ids"])
            if not ids:
                notify("La selection est vide. Ajoute au moins un employe.", DANGER)
                return
            output = export_timesheet_selected_employees_xls(selected_month(), ids)
            notify(f"Export Excel pour {len(ids)} employe(s) cree: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def apply_bulk_status_range(event: ft.ControlEvent | None = None) -> None:
        from datetime import date as _date, timedelta
        try:
            start_str = str(bulk_status_start_field.value or "").strip()
            end_str = str(bulk_status_end_field.value or "").strip()
            status_val = str(bulk_status_value_field.value or "rest")
            if not start_str or not end_str:
                raise ValueError("Renseigne la date de debut et la date de fin.")
            start_dt = _date.fromisoformat(start_str)
            end_dt = _date.fromisoformat(end_str)
            if end_dt < start_dt:
                raise ValueError("La date de fin doit etre superieure ou egale a la date de debut.")
            timesheet = state.get("timesheet") or {}
            emp_rows = filtered_rows(timesheet)
            if not emp_rows:
                raise ValueError("Aucun employe dans la vue courante (applique tes filtres).")
            dates = []
            current = start_dt
            while current <= end_dt:
                dates.append(current.isoformat())
                current += timedelta(days=1)
            total = 0
            errors = 0
            for row in emp_rows:
                emp_id = int(row["employee"]["id_employe"])
                for day_str in dates:
                    try:
                        update_timesheet_day_status(emp_id, day_str, status_val)
                        total += 1
                    except Exception:
                        errors += 1
            notify(
                f"Statut '{status_val}' applique sur {total} cellule(s). {errors} erreur(s)."
                if errors else f"Statut '{status_val}' applique sur {total} cellule(s) — {len(emp_rows)} employe(s) x {len(dates)} jour(s).",
                SUCCESS if not errors else WARNING,
            )
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def export_all_employee_excels(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_all_employees_xls(selected_month())
            notify(f"Exports TimeSheet individuels crees pour tous les employes: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def export_audit(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_audit_xlsx(selected_month())
            notify(f"Export audit TimeSheet cree: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def export_annual_history(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_timesheet_annual_history_xls(site_id=selected_site_id())
            notify(f"Historique annuel TimeSheet exporte: {output}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def lock_month(event: ft.ControlEvent | None = None) -> None:
        confirm_action(
            page,
            "Verrouiller le TimeSheet",
            f"Le TimeSheet {selected_month()} sera verrouille. Les modifications directes seront bloquees.",
            _lock_month,
            confirm_label="Verrouiller",
        )

    def _lock_month() -> None:
        try:
            lock_timesheet_month(selected_month(), commentaire=str(comment_field.value or ""))
            notify("TimeSheet verrouille.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def unlock_month(event: ft.ControlEvent | None = None) -> None:
        confirm_action(
            page,
            "Deverrouiller le TimeSheet",
            f"Le TimeSheet {selected_month()} redeviendra modifiable.",
            _unlock_month,
            confirm_label="Deverrouiller",
            danger=True,
        )

    def _unlock_month() -> None:
        try:
            unlock_timesheet_month(selected_month(), commentaire=str(comment_field.value or ""))
            notify("TimeSheet deverrouille.", WARNING)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def open_history(month: str) -> None:
        month_field.value = month
        activity_date_field.value = ""
        refresh()

    def dispose() -> None:
        state["active"] = False

    def render() -> None:
        timesheet = state.get("timesheet")
        if not timesheet:
            return
        render_summary(timesheet)
        render_calendar(timesheet)
        render_history()
        render_validation(timesheet)
        render_audit()
        render_dashboard(timesheet)
        render_anomalies(timesheet)
        render_view()

    def render_summary(timesheet: dict[str, Any]) -> None:
        summary = timesheet["summary"]
        validation = timesheet.get("validation") or {"issues": []}
        synchronization = timesheet.get("synchronization") or {}
        total_controlled = int(summary.get("worked_days", 0)) + int(summary.get("rest_days", 0)) + int(summary.get("break_days", 0)) + int(summary.get("absent_days", 0))
        conformity = round((total_controlled - len(validation["issues"])) / total_controlled * 100) if total_controlled else 100
        summary_row.controls = [
            _summary_chip(
                "Presence synchronisee",
                f"{synchronization.get('days_with_data', 0)} j / {synchronization.get('validated_days', 0)} valides",
                SUCCESS,
                ft.Icons.SYNC_OUTLINED,
            ),
            _summary_chip("Employes", summary["employees"], PRIMARY, ft.Icons.GROUP_OUTLINED),
            _summary_chip("Heures reelles", summary.get("actual_hours", 0), SUCCESS, ft.Icons.TIMER_OUTLINED),
            _summary_chip("Breaks", summary["break_days"], WARNING, ft.Icons.FREE_BREAKFAST_OUTLINED),
            _summary_chip("Absents", summary.get("absent_days", 0), DANGER, ft.Icons.PERSON_OFF_OUTLINED),
            _summary_chip("Anomalies", len(validation["issues"]), DANGER if validation["issues"] else SUCCESS, ft.Icons.WARNING_AMBER_OUTLINED),
            _summary_chip("Taux conformite", f"{conformity}%", SUCCESS if conformity >= 90 else WARNING, ft.Icons.VERIFIED_OUTLINED),
        ]

    def render_dashboard(timesheet: dict[str, Any]) -> None:
        validation = timesheet.get("validation") or {"issues": []}
        weekly: dict[int, float] = {}
        statuses: dict[str, int] = {}
        for row in timesheet["rows"]:
            for cell in row["cells"]:
                weekly[int(cell.get("week_index") or 1)] = weekly.get(int(cell.get("week_index") or 1), 0) + float(cell.get("hours") or 0)
                key = str(cell.get("status") or "unfilled")
                statuses[key] = statuses.get(key, 0) + 1
        max_hours = max(weekly.values(), default=1)
        dashboard_area.controls = [
            summary_row,
            ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        col={"xs": 12, "lg": 7},
                        content=_dark_panel(
                            "Heures travaillees par semaine",
                            [
                                ft.Row(
                                    controls=[
                                        _week_bar(f"S{week}", hours, max_hours)
                                        for week, hours in sorted(weekly.items())
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                )
                            ],
                        ),
                    ),
                    ft.Container(
                        col={"xs": 12, "lg": 5},
                        content=_dark_panel(
                            "Repartition des statuts",
                            [
                                _distribution_line("12h Drilling", statuses.get("worked_drilling", 0), WORK_DRILLING),
                                _distribution_line("8h Standard", statuses.get("worked_standard", 0), WORK_STANDARD),
                                _distribution_line("Break", statuses.get("break", 0), BREAK),
                                _distribution_line("Absences", statuses.get("absent", 0), DANGER),
                                _distribution_line("Non renseigne", statuses.get("unfilled", 0), UNFILLED),
                            ],
                        ),
                    ),
                ],
                spacing=12,
                run_spacing=12,
            ),
            _dark_panel(
                "Alertes critiques",
                [
                    *[
                        _issue_row(str(issue.get("message") or "Anomalie TimeSheet"), DANGER if issue in validation.get("blocking", []) else WARNING)
                        for issue in validation["issues"][:6]
                    ],
                    *([] if validation["issues"] else [ft.Text("Aucune anomalie critique detectee.", color=SUCCESS, size=11)]),
                ],
            ),
        ]

    def render_anomalies(timesheet: dict[str, Any]) -> None:
        validation = timesheet.get("validation") or {"issues": [], "blocking": [], "warnings": []}
        anomalies_area.controls = [
            _dark_panel(
                f"Anomalies detectees ({len(validation['issues'])})",
                [
                    _issue_row(str(issue.get("message") or "-"), DANGER if issue in validation["blocking"] else WARNING)
                    for issue in validation["issues"]
                ] or [ft.Text("Aucune anomalie. Le TimeSheet est coherent.", color=SUCCESS, size=11)],
            )
        ]

    def set_view(view: str) -> None:
        state["view"] = view
        render_view()
        _update()

    def render_view() -> None:
        view = str(state["view"])
        for key, button in nav_buttons.items():
            selected = key == view
            button.style = ft.ButtonStyle(
                color="#FFFFFF" if selected else DARK_MUTED,
                bgcolor=PRIMARY if selected else FIELD,
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        content_area.content = views[view]

    def render_calendar(timesheet: dict[str, Any]) -> None:
        days = timesheet["days"]
        rows = filtered_rows(timesheet)
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"])))
        start = int(state["page"]) * PAGE_SIZE
        page_rows = rows[start : start + PAGE_SIZE]
        columns = [
            ft.DataColumn(ft.Text("Employe")),
            ft.DataColumn(ft.Text("Matricule")),
            ft.DataColumn(ft.Text("Fonction")),
            ft.DataColumn(ft.Text("JT")),
            ft.DataColumn(ft.Text("Repos")),
            ft.DataColumn(ft.Text("Abs.")),
            ft.DataColumn(ft.Text("Break")),
            ft.DataColumn(ft.Text("H. reelles")),
            *[
                ft.DataColumn(_day_header(day))
                for day in days
            ],
        ]

        calendar_area.controls = [
            ft.Row(
                controls=[
                    _legend("12h drilling", WORK_DRILLING, "#FFFFFF"),
                    _legend("8h sans drilling", WORK_STANDARD, "#FFFFFF"),
                    _legend("Jour chome 8h", HOLIDAY, "#FFFFFF"),
                    _legend("Repos", REST, TEXT),
                    _legend("Absent", ABSENT, TEXT),
                    _legend("Non renseigne", UNFILLED, TEXT),
                    _legend("Break", BREAK, TEXT),
                    _legend("Permission", PERMISSION, "#FFFFFF"),
                    _legend("Sick", SICK, "#FFFFFF"),
                    _legend("Debut semaine", "#1E3A8A", "#FFFFFF"),
                    ft.Text(
                        f"{start + 1 if rows else 0}-{start + len(page_rows)} / {len(rows)} employe(s)",
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
                        bgcolor="#EFF6FF",
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        content=ft.Text(f"Page {int(state['page']) + 1}/{max_page + 1}", size=12, color=TEXT),
                    ),
                    ft.OutlinedButton(
                        "Suivant",
                        icon=ft.Icons.ARROW_FORWARD,
                        disabled=int(state["page"]) >= max_page,
                        on_click=lambda event: change_page(1),
                    ),
                    status,
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=columns,
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(_employee_identity(row["employee"])),
                                    ft.DataCell(ft.Text(
                                        str(row["employee"].get("matricule") or row["employee"].get("numero_badge") or "—"),
                                        color=DARK_MUTED, weight=ft.FontWeight.W_500,
                                    )),
                                    ft.DataCell(ft.Text(str(row["employee"].get("fonction") or "-"), color=DARK_MUTED)),
                                    ft.DataCell(ft.Text(str(row["worked_days"]), color=SUCCESS, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row["rest_days"]), color=DARK_MUTED)),
                                    ft.DataCell(ft.Text(str(row.get("absent_days", 0)), color=DANGER, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row["break_days"]), color=WARNING, weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(str(row.get("actual_hours", 0)), color=PRIMARY, weight=ft.FontWeight.BOLD)),
                                    *[
                                        ft.DataCell(_calendar_cell(cell, int(row["employee"]["id_employe"]), quick_edit_status))
                                        for cell in row["cells"]
                                    ],
                                ]
                            )
                            for row in page_rows
                        ],
                        bgcolor=FIELD,
                        border=ft.border.all(1, BORDER),
                        border_radius=8,
                        heading_row_color="#142B45",
                        data_row_min_height=42,
                        data_row_max_height=48,
                        column_spacing=6,
                        horizontal_margin=8,
                        horizontal_lines=ft.BorderSide(1, BORDER),
                        vertical_lines=ft.BorderSide(1, BORDER),
                        heading_text_style=ft.TextStyle(size=10, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                        data_text_style=ft.TextStyle(size=10, color=DARK_MUTED),
                        data_row_color={
                            ft.ControlState.HOVERED: "#142B45",
                            ft.ControlState.PRESSED: "#17304A",
                            ft.ControlState.SELECTED: "#123B46",
                        },
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    def change_page(delta: int) -> None:
        rows = filtered_rows(state.get("timesheet") or {"rows": []})
        max_page = max((len(rows) - 1) // PAGE_SIZE, 0)
        state["page"] = max(0, min(max_page, int(state["page"]) + delta))
        render_calendar(state["timesheet"])
        _update()

    def filtered_rows(timesheet: dict[str, Any]) -> list[dict[str, Any]]:
        query = str(search_field.value or "").strip().lower()
        selected_function = str(function_filter.value or "all")
        selected_status = str(status_filter.value or "all")
        selected_week = str(week_filter.value or "all")
        selected_site = str(site_filter.value or "all")
        selected_group = str(group_filter.value or "all")
        selected_shift = str(shift_filter.value or "all")
        selected_badge = str(badge_filter.value or "all")
        rows: list[dict[str, Any]] = []
        for row in timesheet["rows"]:
            employee = row["employee"]
            haystack = " ".join(
                str(employee.get(key) or "")
                for key in ("nom", "prenom", "nom_complet", "numero_badge", "fonction")
            ).lower()
            cells = row["cells"]
            if selected_week != "all":
                cells = [cell for cell in cells if f"S{cell.get('week_index')}" == selected_week]
            if query and query not in haystack:
                continue
            if selected_function != "all" and str(employee.get("fonction") or "-") != selected_function:
                continue
            if selected_site != "all" and str(employee.get("site") or "-") != selected_site:
                continue
            if selected_group != "all" and str(employee.get("groupe") or "-") != selected_group:
                continue
            if selected_shift != "all" and str(employee.get("shift_code") or "-") != selected_shift:
                continue
            if selected_badge == "with_badge" and not employee.get("numero_badge"):
                continue
            if selected_badge == "without_badge" and employee.get("numero_badge"):
                continue
            if selected_status != "all":
                if selected_status in {"permission", "sick"}:
                    if not any(cell["status"] == "break" and cell["label"].lower() == selected_status[0] for cell in cells):
                        continue
                elif selected_status == "annual":
                    if not any(cell["status"] == "break" and cell["label"] == "AL" for cell in cells):
                        continue
                elif selected_status == "break":
                    if not any(cell["status"] == "break" and cell["label"] == "B" for cell in cells):
                        continue
                elif not any(cell["status"] == selected_status for cell in cells):
                    continue
            rows.append(row)
        return rows

    def quick_edit_status(employee_id: int, day: str, status_value: str) -> None:
        edit_employee_field.value = str(employee_id)
        edit_date_field.value = day
        edit_status_field.value = status_value
        save_timesheet_edit()

    def refresh_filtered(event: ft.ControlEvent | None = None) -> None:
        state["page"] = 0
        render_calendar(state["timesheet"])
        _update()

    def render_history() -> None:
        history_area.controls = [
            ft.Row(
                controls=[
                    ft.Text("Historique des TimeSheets", size=16, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                    ft.OutlinedButton(
                        "Telecharger 12 mois",
                        icon=ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED,
                        on_click=export_annual_history,
                    ),
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.OutlinedButton(
                        item["label"],
                        icon=ft.Icons.HISTORY_OUTLINED,
                        on_click=lambda event, month=item["month"]: open_history(month),
                    )
                    for item in state["history"]
                ],
                wrap=True,
                spacing=8,
            )
            if state["history"]
            else ft.Text("Aucun historique disponible.", size=12, color=DARK_MUTED),
        ]

    def render_validation(timesheet: dict[str, Any]) -> None:
        lock = timesheet.get("lock")
        if not lock:
            try:
                lock = get_timesheet_lock(selected_month())
            except Exception:
                lock = None
        validation = timesheet.get("validation") or {"issues": [], "blocking": [], "warnings": []}
        locked = bool(lock)

        lock_detail_controls: list[ft.Control] = []
        if locked:
            lock_detail_controls = [
                ft.Container(
                    bgcolor="#0F2E1E",
                    border=ft.border.only(left=ft.BorderSide(3, SUCCESS)),
                    border_radius=ft.border_radius.only(top_right=8, bottom_right=8),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.LOCK_OUTLINE, color=SUCCESS, size=16),
                                    ft.Text("TimeSheet verrouille", color=SUCCESS, size=12, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=6,
                            ),
                            ft.Text(
                                f"Verrouille par : {lock.get('locked_by') or 'inconnu'}",
                                size=11, color=DARK_TEXT,
                            ),
                            ft.Text(
                                f"Le : {str(lock.get('locked_at') or '-')[:19]}",
                                size=11, color=DARK_MUTED,
                            ),
                            ft.Text(
                                f"Commentaire : {lock.get('commentaire') or 'Aucun commentaire'}",
                                size=11, color=DARK_MUTED,
                            ),
                        ],
                        spacing=3,
                    ),
                )
            ]

        blocking_count = len(validation.get("blocking") or [])
        warnings_count = len(validation.get("warnings") or [])
        issues_count = len(validation.get("issues") or [])

        validation_area.controls = [
            ft.Row(
                controls=[
                    _status_chip(
                        "Verrouille" if locked else "Modifiable",
                        SUCCESS if locked else WARNING,
                        ft.Icons.LOCK_OUTLINE if locked else ft.Icons.LOCK_OPEN_OUTLINED,
                    ),
                    ft.Container(
                        bgcolor=FIELD,
                        border=ft.border.all(1, DANGER if blocking_count else BORDER),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        content=ft.Text(
                            f"{blocking_count} bloquant(s)  |  {warnings_count} alerte(s)  |  {issues_count} anomalie(s)",
                            size=11,
                            color=DANGER if blocking_count else (WARNING if warnings_count else SUCCESS),
                        ),
                    ),
                    ft.ElevatedButton(
                        "Verrouiller",
                        icon=ft.Icons.LOCK_OUTLINE,
                        disabled=locked,
                        on_click=lock_month,
                    ),
                    ft.OutlinedButton(
                        "Deverrouiller",
                        icon=ft.Icons.LOCK_OPEN_OUTLINED,
                        disabled=not locked,
                        on_click=unlock_month,
                    ),
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            *lock_detail_controls,
            ft.Column(
                controls=[
                    _issue_row(
                        str(issue.get("message") or ""),
                        DANGER if issue in (validation.get("blocking") or []) else WARNING,
                    )
                    for issue in validation["issues"]
                ],
                spacing=4,
            )
            if validation["issues"]
            else ft.Text("Validation OK — aucune anomalie detectee pour ce mois.", size=12, color=SUCCESS),
        ]

    def render_audit() -> None:
        rows = list_timesheet_audit(selected_month(), limit=12)
        audit_area.controls = [
            ft.Text("Audit TimeSheet", size=16, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{row['changed_at']} - {row.get('date_presence') or row.get('action')}: "
                        f"{row.get('nom') or ''} {row.get('prenom') or ''} "
                        f"{row.get('ancienne_valeur') or '-'} -> {row.get('nouvelle_valeur') or '-'}",
                        size=12,
                        color=DARK_MUTED,
                    )
                    for row in rows
                ],
                spacing=4,
            )
            if rows
            else ft.Text("Aucune modification auditee pour ce mois.", size=12, color=DARK_MUTED),
        ]

    filters_panel = _dark_panel(
        "Filtres de la matrice",
        [
            ft.Row(
                controls=[
                    search_field,
                    function_filter,
                    status_filter,
                    week_filter,
                    site_filter,
                    group_filter,
                    shift_filter,
                    badge_filter,
                    ft.ElevatedButton("Appliquer", icon=ft.Icons.FILTER_ALT_OUTLINED, on_click=refresh_filtered),
                ],
                wrap=True,
                spacing=10,
            )
        ],
    )
    configuration_panel = ft.Column(
        controls=[
            _dark_panel(
                "Activite drilling",
                [
                    ft.Row(
                        controls=[
                            activity_date_field,
                            drilling_switch,
                            day_type_field,
                            comment_field,
                            ft.OutlinedButton("Charger jour", icon=ft.Icons.TODAY_OUTLINED, on_click=load_activity),
                            ft.ElevatedButton("Enregistrer jour", icon=ft.Icons.SAVE_OUTLINED, on_click=save_activity),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        controls=[
                            bulk_start_field,
                            bulk_end_field,
                            bulk_drilling_switch,
                            bulk_day_type_field,
                            ft.OutlinedButton("Appliquer periode", icon=ft.Icons.DATE_RANGE_OUTLINED, on_click=save_bulk_activity),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                ],
            ),
            _dark_panel(
                "Modification manuelle — employe / jour",
                [
                    ft.Row(
                        controls=[
                            edit_employee_field,
                            edit_date_field,
                            edit_status_field,
                            ft.ElevatedButton("Modifier", icon=ft.Icons.SAVE_OUTLINED, on_click=save_timesheet_edit),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                ],
            ),
            _dark_panel(
                "Application en masse — statut sur plage de dates",
                [
                    ft.Text(
                        "Applique un statut a tous les employes de la vue courante (respecte les filtres actifs) "
                        "pour chaque jour de la periode choisie.",
                        size=11,
                        color=DARK_MUTED,
                    ),
                    ft.Row(
                        controls=[
                            bulk_status_start_field,
                            bulk_status_end_field,
                            bulk_status_value_field,
                            ft.ElevatedButton(
                                "Appliquer a tous les employes filtres",
                                icon=ft.Icons.GROUPS_OUTLINED,
                                on_click=lambda event: confirm_action(
                                    page,
                                    "Confirmer l'application en masse",
                                    f"Le statut '{bulk_status_value_field.value}' sera applique a tous les employes "
                                    f"de la vue courante du {bulk_status_start_field.value or '?'} au {bulk_status_end_field.value or '?'}. "
                                    "Cette operation est reversible employe par employe.",
                                    apply_bulk_status_range,
                                    confirm_label="Appliquer",
                                ),
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                ],
            ),
            _dark_panel(
                "Selection d'employes — export personnalise",
                [
                    ft.Text(
                        "Selectionne des employes dans le menu deroulant ci-dessus et ajoute-les "
                        "a la selection pour exporter uniquement leurs TimeSheets individuels.",
                        size=11,
                        color=DARK_MUTED,
                    ),
                    selection_count_text,
                    ft.Row(
                        controls=[
                            edit_employee_field,
                            ft.ElevatedButton(
                                "Ajouter a la selection",
                                icon=ft.Icons.PLAYLIST_ADD_OUTLINED,
                                on_click=add_to_selection,
                            ),
                            ft.OutlinedButton(
                                "Vider la selection",
                                icon=ft.Icons.CLEAR_ALL_OUTLINED,
                                on_click=clear_selection,
                            ),
                            ft.ElevatedButton(
                                "Exporter la selection",
                                icon=ft.Icons.TABLE_VIEW_OUTLINED,
                                on_click=export_selection,
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                ],
            ),
        ],
        spacing=12,
    )
    views = {
        "dashboard": dashboard_area,
        "matrix": ft.Column(controls=[filters_panel, _dark_panel("Matrice TimeSheet 21 → 20", [calendar_area])], spacing=12),
        "anomalies": anomalies_area,
        "validation": _dark_panel("Validation du TimeSheet", [validation_area]),
        "history": ft.Column(controls=[_dark_panel("Historique", [history_area]), _dark_panel("Audit et tracabilite", [audit_area])], spacing=12),
        "configuration": configuration_panel,
    }
    for key, label, icon in [
        ("dashboard", "Dashboard", ft.Icons.DASHBOARD_OUTLINED),
        ("matrix", "Matrice", ft.Icons.GRID_VIEW_OUTLINED),
        ("anomalies", "Anomalies", ft.Icons.WARNING_AMBER_OUTLINED),
        ("validation", "Validation", ft.Icons.VERIFIED_OUTLINED),
        ("history", "Historique", ft.Icons.HISTORY_OUTLINED),
        ("configuration", "Configuration", ft.Icons.SETTINGS_OUTLINED),
    ]:
        nav_buttons[key] = ft.TextButton(label, icon=icon, on_click=lambda event, target=key: set_view(target))

    root = ft.Container(
        bgcolor=BG,
        expand=True,
        padding=12,
        content=ft.Column(
        controls=[
            _timesheet_header(
                month_field,
                site_scope_field,
                refresh,
                lock_month,
                export_excel,
                prepare_timesheet_in_outlook,
                prepare_timesheet_in_whatsapp,
                send_timesheet_by_email,
                export_employee_excel,
                export_all_employee_excels,
                export_selection,
                export_audit,
            ),
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=8,
                content=ft.Row(controls=list(nav_buttons.values()), spacing=6, wrap=True),
            ),
            ft.Row(
                controls=[status, loading_overlay],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content_area,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        ),
    )
    root.data = {"dispose": dispose}
    refresh()
    return root


def _employee_name(employee: dict[str, Any]) -> str:
    if employee.get("nom") or employee.get("prenom"):
        return f"{employee.get('nom') or ''} {employee.get('prenom') or ''}".strip()
    return str(employee.get("nom_complet") or "-")


def _employee_identity(employee: dict[str, Any]) -> ft.Control:
    name = _employee_name(employee)
    initials = "".join(part[0] for part in name.split()[:2] if part) or "?"
    return ft.Row(
        controls=[
            ft.Container(
                width=30,
                height=30,
                bgcolor=PRIMARY,
                border_radius=15,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(initials.upper(), color="#FFFFFF", size=9, weight=ft.FontWeight.BOLD),
            ),
            ft.Column(
                controls=[
                    ft.Text(name, color=DARK_TEXT, size=10, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Badge: {employee.get('numero_badge') or '-'}", color=DARK_MUTED, size=8),
                ],
                spacing=0,
            ),
        ],
        spacing=6,
    )


def _calendar_cell(cell: dict[str, Any], employee_id: int, on_status_change: object) -> ft.Control:
    color, text_color, tooltip = _cell_style(cell)
    content = ft.Container(
        width=TIMESHEET_DAY_WIDTH,
        height=TIMESHEET_DAY_HEIGHT,
        bgcolor=color,
        border=ft.border.only(
            left=ft.BorderSide(3 if cell.get("week_start") else 1, "#1E3A8A" if cell.get("week_start") else "#94A3B8"),
            right=ft.BorderSide(1, "#94A3B8"),
            top=ft.BorderSide(1, "#94A3B8"),
            bottom=ft.BorderSide(1, "#94A3B8"),
        ),
        border_radius=4,
        alignment=ft.Alignment(0, 0),
        tooltip=tooltip,
        content=ft.Text(str(cell["label"]), size=10, color=text_color, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
    )
    return ft.PopupMenuButton(
        content=content,
        tooltip=f"{tooltip} - cliquer pour modifier",
        items=[
            ft.PopupMenuItem(content=ft.Text("Present"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "present")),
            ft.PopupMenuItem(content=ft.Text("Repos"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "rest")),
            ft.PopupMenuItem(content=ft.Text("Absent"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "absent")),
            ft.PopupMenuItem(content=ft.Text("Break"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "break")),
            ft.PopupMenuItem(content=ft.Text("Annual leave"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "annual")),
            ft.PopupMenuItem(content=ft.Text("Permission"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "permission")),
            ft.PopupMenuItem(content=ft.Text("Sick"), on_click=lambda event: on_status_change(employee_id, str(cell["date"]), "sick")),
        ],
    )


def _cell_style(cell: dict[str, Any]) -> tuple[str, str, str]:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status == "worked_drilling":
        return WORK_DRILLING, "#FFFFFF", "Present avec activite drilling: 12H"
    if status == "worked_standard":
        return WORK_STANDARD, "#FFFFFF", "Present sans drilling: 8H"
    if status == "holiday":
        return HOLIDAY, "#FFFFFF", "Jour ferie ou chome paye: 8H"
    if status == "break" and label == "P":
        return PERMISSION, "#FFFFFF", "Permission"
    if status == "break" and label == "S":
        return SICK, "#FFFFFF", "Sick / Maladie"
    if status == "break" and label == "AL":
        return "#5B3DB6", "#FFFFFF", "Annual leave"
    if status == "break":
        return BREAK, TEXT, "Break"
    if status == "absent":
        return ABSENT, TEXT, "Absent"
    if status == "unfilled":
        return UNFILLED, TEXT, "Non renseigne"
    if status == "not_assigned":
        return "#F8FAFC", MUTED, "Non affecte a ce site"
    return REST, TEXT, "Repos"


def _break_color(label: str) -> str:
    return {"B": BREAK, "P": PERMISSION, "S": SICK, "AL": "#5B3DB6"}.get(label, BREAK)


def _shift_label(shift_code: str) -> str:
    return {"DAY": "Day Shift", "NIGHT": "Night Shift", "BREAK": "Break"}.get(shift_code, shift_code)


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=12,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    bgcolor=color,
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color="#FFFFFF", size=22),
                ),
                ft.Column(
                    controls=[
                        ft.Text(label, color=DARK_MUTED, size=10),
                        ft.Text(str(value), color=DARK_TEXT, size=20, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=0,
                ),
            ],
            spacing=9,
        ),
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
    )


def _status_chip(label: str, color: str, icon: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
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


def _legend(label: str, color: str, text_color: str) -> ft.Control:
    return ft.Container(
        bgcolor=color,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
        content=ft.Text(label, size=12, color=text_color, weight=ft.FontWeight.BOLD),
    )


def _day_header(day: dict[str, Any]) -> ft.Control:
    activity_color = WORK_DRILLING if day["has_drilling"] else WORK_STANDARD
    return ft.Container(
        width=TIMESHEET_DAY_WIDTH,
        padding=ft.padding.symmetric(horizontal=2, vertical=3),
        bgcolor="#142B45" if int(day["week_index"]) % 2 else FIELD,
        border=ft.border.only(
            left=ft.BorderSide(3 if day.get("week_start") else 1, PRIMARY if day.get("week_start") else BORDER),
            right=ft.BorderSide(1, BORDER),
            top=ft.BorderSide(1, BORDER),
            bottom=ft.BorderSide(1, BORDER),
        ),
        border_radius=4,
        content=ft.Column(
            controls=[
                ft.Text(f"S{day['week_index']}", size=10, color=PRIMARY, weight=ft.FontWeight.BOLD),
                ft.Text(str(day["day"]), size=11, color=DARK_TEXT, weight=ft.FontWeight.BOLD),
                ft.Text(day["weekday"], size=9, color=DARK_MUTED),
                ft.Text("12h" if day["has_drilling"] else "8h", size=9, color=activity_color, weight=ft.FontWeight.BOLD),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _dark_panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[ft.Text(title, color=DARK_TEXT, size=15, weight=ft.FontWeight.BOLD), *controls],
            spacing=11,
        ),
    )


def _week_bar(label: str, value: float, maximum: float) -> ft.Control:
    height = max(16, int(130 * value / maximum)) if maximum else 16
    return ft.Column(
        controls=[
            ft.Text(str(round(value)), color=DARK_TEXT, size=10, weight=ft.FontWeight.BOLD),
            ft.Container(width=54, height=height, bgcolor=WORK_DRILLING, border_radius=6),
            ft.Text(label, color=DARK_MUTED, size=9),
        ],
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.END,
    )


def _distribution_line(label: str, value: Any, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=9,
        content=ft.Row(
            controls=[
                ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                ft.Text(label, color=DARK_MUTED, size=10, expand=True),
                ft.Text(str(value), color=DARK_TEXT, size=11, weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        ),
    )


def _issue_row(message: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=10,
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=color, size=18),
                ft.Text(message, color=DARK_TEXT, size=10, expand=True),
            ],
            spacing=8,
        ),
    )


def _timesheet_header(
    month_field: ft.TextField,
    site_field: ft.Dropdown,
    refresh: Any,
    validate: Any,
    export_excel: Any,
    outlook: Any,
    whatsapp: Any,
    email: Any,
    export_employee: Any,
    export_all: Any,
    export_selection: Any,
    export_audit: Any,
) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("TimeSheet 21 → 20", color=DARK_TEXT, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("Pilotage, controle et validation de la periode.", color=DARK_MUTED, size=10),
                    ],
                    spacing=2,
                    width=280,
                ),
                month_field,
                site_field,
                ft.IconButton(icon=ft.Icons.SYNC_OUTLINED, tooltip="Synchroniser", icon_color=PRIMARY, on_click=refresh),
                ft.PopupMenuButton(
                    icon=ft.Icons.DOWNLOAD_OUTLINED,
                    tooltip="Exports et partage",
                    items=[
                        ft.PopupMenuItem(content=ft.Text("TimeSheet complet Excel"), on_click=export_excel),
                        ft.PopupMenuItem(content=ft.Text("Envoyer par email"), on_click=email),
                        ft.PopupMenuItem(content=ft.Text("Preparer dans Outlook"), on_click=outlook),
                        ft.PopupMenuItem(content=ft.Text("Preparer dans WhatsApp"), on_click=whatsapp),
                        ft.PopupMenuItem(content=ft.Text("TimeSheet individuel Excel"), on_click=export_employee),
                        ft.PopupMenuItem(content=ft.Text("Tous les individuels Excel"), on_click=export_all),
                        ft.PopupMenuItem(content=ft.Text("Exporter la selection"), on_click=export_selection),
                        ft.PopupMenuItem(content=ft.Text("Exporter audit"), on_click=export_audit),
                    ],
                ),
                ft.ElevatedButton("Valider TimeSheet", icon=ft.Icons.VERIFIED_OUTLINED, on_click=validate),
            ],
            spacing=10,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
