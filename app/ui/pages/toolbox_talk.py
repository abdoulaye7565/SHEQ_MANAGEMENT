from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table

from app.services import (
    DEFAULT_TOOLBOX_FACILITATOR,
    apply_monthly_toolbox_facilitator,
    assign_topic_to_dates,
    assign_monthly_topics,
    clear_monthly_toolbox_topics,
    current_toolbox_month,
    delete_toolbox_topic,
    export_toolbox_talk_xlsx,
    generate_toolbox_theme_catalog,
    get_toolbox_options,
    list_theme_catalog,
    list_toolbox_topics,
    save_theme_catalog,
    save_toolbox_topic,
)
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def toolbox_talk_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, Any] = {"data": None, "editing_date": None, "themes": [], "selected_dates": set()}
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.Row(spacing=8, wrap=True)
    table_area = ft.Column(spacing=10)
    theme_area = ft.Column(spacing=10)
    options = get_toolbox_options()

    def facilitator_options(current: str | None = None) -> list[ft.dropdown.Option]:
        names = [str(row["label"]) for row in options.get("facilitators", [])]
        selected = str(current or "").strip()
        if selected and selected not in names:
            names.append(selected)
        if DEFAULT_TOOLBOX_FACILITATOR not in names:
            names.insert(0, DEFAULT_TOOLBOX_FACILITATOR)
        return [ft.dropdown.Option(name, name) for name in names]

    month_field = ft.TextField(label="Mois", value=current_toolbox_month(), hint_text="AAAA-MM", width=150)
    status_filter = ft.Dropdown(
        label="Etat",
        value="all",
        width=170,
        options=[
            ft.dropdown.Option("all", "Tous"),
            ft.dropdown.Option("done", "Renseigne"),
            ft.dropdown.Option("missing", "A completer"),
        ],
    )
    date_field = ft.TextField(label="Date", hint_text="AAAA-MM-JJ", width=160)
    topic_field = ft.Dropdown(label="Topic EN / Theme FR journalier", width=520)
    facilitator_field = ft.Dropdown(
        label="Facilitateur",
        value=DEFAULT_TOOLBOX_FACILITATOR,
        width=260,
        options=facilitator_options(),
    )
    catalog_theme_field = ft.TextField(
        label="Nouveau theme bilingue",
        hint_text="English topic / Theme francais",
        width=520,
    )
    mandatory_field = ft.Checkbox(label="Theme obligatoire")
    monthly_facilitator_field = ft.Dropdown(
        label="Facilitateur du mois",
        value=DEFAULT_TOOLBOX_FACILITATOR,
        width=260,
        options=facilitator_options(),
    )
    generated_count_field = ft.TextField(label="Nombre de themes", value="31", width=150)
    site_field = ft.Dropdown(
        label="Site",
        width=220,
        options=[ft.dropdown.Option("", "-")]
        + [ft.dropdown.Option(str(row["value"]), str(row["label"])) for row in options["sites"]],
    )

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
            load_theme_options()
            state["data"] = list_toolbox_topics(month_field.value)
            render()
            notify("Planning Toolbox Talk actualise.", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def load_theme_options() -> None:
        nonlocal options
        options = get_toolbox_options()
        state["themes"] = list_theme_catalog()
        topic_field.options = [
            ft.dropdown.Option(str(row["theme"]), str(row["theme"]))
            for row in state["themes"]
        ]
        facilitator_field.options = facilitator_options(str(facilitator_field.value or DEFAULT_TOOLBOX_FACILITATOR))
        monthly_facilitator_field.options = facilitator_options(str(monthly_facilitator_field.value or DEFAULT_TOOLBOX_FACILITATOR))
        facilitator_field.value = str(facilitator_field.value or DEFAULT_TOOLBOX_FACILITATOR)
        monthly_facilitator_field.value = str(monthly_facilitator_field.value or DEFAULT_TOOLBOX_FACILITATOR)

    def filtered_rows() -> list[dict[str, Any]]:
        data = state.get("data") or {"rows": []}
        selected = str(status_filter.value or "all")
        rows = []
        for row in data["rows"]:
            if selected != "all" and row["status"] != selected:
                continue
            rows.append(row)
        return rows

    def start_edit(row: dict[str, Any]) -> None:
        state["editing_date"] = row["date_theme"]
        date_field.value = row["date_theme"]
        topic_field.value = str(row.get("theme") or "")
        facilitator_field.options = facilitator_options(str(row.get("facilitateur") or DEFAULT_TOOLBOX_FACILITATOR))
        facilitator_field.value = str(row.get("facilitateur") or DEFAULT_TOOLBOX_FACILITATOR)
        site_field.value = str(row.get("site_id") or "")
        notify(f"Edition du topic du {row['date_theme']}.", PRIMARY)
        _update()

    def clear_form(event: ft.ControlEvent | None = None) -> None:
        state["editing_date"] = None
        state["selected_dates"] = set()
        date_field.value = ""
        topic_field.value = ""
        facilitator_field.value = DEFAULT_TOOLBOX_FACILITATOR
        site_field.value = ""
        notify("Formulaire vide.", MUTED)
        _update()

    def add_catalog_theme(event: ft.ControlEvent | None = None) -> None:
        try:
            save_theme_catalog(
                {
                    "theme": catalog_theme_field.value,
                    "obligatoire": bool(mandatory_field.value),
                    "actif": True,
                }
            )
            catalog_theme_field.value = ""
            mandatory_field.value = False
            notify("Theme ajoute a la banque Toolbox Talk.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def generate_catalog(event: ft.ControlEvent | None = None) -> None:
        try:
            count = generate_toolbox_theme_catalog(int(generated_count_field.value or 12))
            notify(f"{count} theme(s) OREZONE ajoutes a la banque.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def assign_month(event: ft.ControlEvent | None = None) -> None:
        try:
            count = assign_monthly_topics(month_field.value, monthly_facilitator_field.value)
            notify(f"{count} topic(s) affecte(s) automatiquement sur le mois.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def apply_facilitator_to_month(event: ft.ControlEvent | None = None) -> None:
        try:
            count = apply_monthly_toolbox_facilitator(month_field.value, monthly_facilitator_field.value)
            notify(f"Facilitateur applique sur {count} jour(s) du mois.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def clear_month_topics(event: ft.ControlEvent | None = None) -> None:
        try:
            count = clear_monthly_toolbox_topics(str(month_field.value or ""))
            state["selected_dates"] = set()
            notify(f"{count} theme(s) dissocie(s) des jours du mois.", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def assign_selected_dates(event: ft.ControlEvent | None = None) -> None:
        try:
            dates = sorted(state.get("selected_dates") or [])
            count = assign_topic_to_dates(
                {
                    "dates": dates,
                    "theme": topic_field.value,
                    "facilitateur": facilitator_field.value,
                    "site_id": site_field.value,
                }
            )
            notify(f"{count} date(s) mises a jour avec le theme selectionne.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def save_topic(event: ft.ControlEvent | None = None) -> None:
        try:
            save_toolbox_topic(
                {
                    "date_theme": date_field.value,
                    "theme": topic_field.value,
                    "facilitateur": facilitator_field.value,
                    "site_id": site_field.value,
                }
            )
            notify("Theme Toolbox Talk enregistre.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def delete_topic(row: dict[str, Any]) -> None:
        try:
            delete_toolbox_topic(str(row["date_theme"]))
            notify("Theme supprime pour cette date.", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _update()

    def export_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            output = export_toolbox_talk_xlsx(str(month_field.value or ""))
            notify(f"Export Excel Toolbox Talk Meeting cree: {output}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _update()

    def toggle_date(row: dict[str, Any], selected: bool | None) -> None:
        dates: set[str] = set(state.get("selected_dates") or set())
        current = str(row["date_theme"])
        if selected:
            dates.add(current)
        else:
            dates.discard(current)
        state["selected_dates"] = dates
        date_field.value = ", ".join(sorted(dates)) if dates else str(state.get("editing_date") or "")
        notify(f"{len(dates)} date(s) selectionnee(s).", PRIMARY if dates else MUTED)
        render()
        _update()

    def render() -> None:
        data = state.get("data") or {"summary": {}, "rows": [], "label": ""}
        summary = data["summary"]
        rows = filtered_rows()
        selected_dates: set[str] = set(state.get("selected_dates") or set())
        summary_row.controls = [
            _summary_chip("Mois", data.get("label") or "-", PRIMARY, ft.Icons.CALENDAR_MONTH_OUTLINED),
            _summary_chip("Jours", summary.get("days", 0), PRIMARY, ft.Icons.DATE_RANGE_OUTLINED),
            _summary_chip("Renseignes", summary.get("completed", 0), SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _summary_chip("A completer", summary.get("missing", 0), DANGER, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _summary_chip("Avancement", f"{summary.get('completion', 0)}%", WARNING, ft.Icons.INSIGHTS_OUTLINED),
        ]
        table_area.controls = [
            ft.Row(
                controls=[
                    ft.OutlinedButton("Actualiser", icon=ft.Icons.REFRESH_OUTLINED, on_click=refresh),
                    ft.OutlinedButton("Exporter Excel", icon=ft.Icons.DOWNLOAD_OUTLINED, on_click=export_excel),
                    ft.OutlinedButton("Effacer formulaire", icon=ft.Icons.CLEAR_OUTLINED, on_click=clear_form),
                    status,
                ],
                wrap=True,
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Sel.")),
                            ft.DataColumn(ft.Text("Date")),
                            ft.DataColumn(ft.Text("Jour")),
                        ft.DataColumn(ft.Text("Topic EN / Theme FR")),
                            ft.DataColumn(ft.Text("Facilitateur")),
                            ft.DataColumn(ft.Text("Site")),
                            ft.DataColumn(ft.Text("Etat")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(
                                        ft.Checkbox(
                                            value=str(row["date_theme"]) in selected_dates,
                                            on_change=lambda event, current=row: toggle_date(current, event.control.value),
                                        )
                                    ),
                                    ft.DataCell(ft.Text(str(row["date_theme"]))),
                                    ft.DataCell(ft.Text(str(row["weekday"]))),
                                    ft.DataCell(ft.Text(str(row.get("theme") or "-"), width=320)),
                                    ft.DataCell(ft.Text(str(row.get("facilitateur") or "-"))),
                                    ft.DataCell(ft.Text(str(row.get("site") or "-"))),
                                    ft.DataCell(_state_badge(str(row["status"]))),
                                    ft.DataCell(
                                        ft.Row(
                                            controls=[
                                                ft.IconButton(
                                                    icon=ft.Icons.EDIT_OUTLINED,
                                                    tooltip="Modifier le topic",
                                                    icon_color=PRIMARY,
                                                    on_click=lambda event, current=row: start_edit(current),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.DELETE_OUTLINE,
                                                    tooltip="Supprimer le topic",
                                                    icon_color=DANGER,
                                                    on_click=lambda event, current=row: delete_topic(current),
                                                    disabled=not row.get("id_theme"),
                                                ),
                                            ],
                                            spacing=0,
                                        )
                                    ),
                                ]
                            )
                            for row in rows
                        ],
                        border=ft.border.all(1, "#BFDBFE"),
                        border_radius=8,
                        heading_row_color="#DBEAFE",
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]
        render_theme_catalog()

    def render_theme_catalog() -> None:
        themes = list(state.get("themes") or [])
        theme_area.controls = [
            ft.Row(
                controls=[
                    catalog_theme_field,
                    mandatory_field,
                    ft.ElevatedButton("Ajouter theme", icon=ft.Icons.ADD_OUTLINED, on_click=add_catalog_theme),
                    generated_count_field,
                    ft.OutlinedButton("Generer themes", icon=ft.Icons.AUTO_AWESOME_OUTLINED, on_click=generate_catalog),
                    monthly_facilitator_field,
                    ft.OutlinedButton("Appliquer facilitateur au mois", icon=ft.Icons.PERSON_PIN_OUTLINED, on_click=apply_facilitator_to_month),
                    ft.OutlinedButton("Affecter le mois aleatoire", icon=ft.Icons.AUTO_AWESOME_OUTLINED, on_click=assign_month),
                    ft.OutlinedButton("Dissocier le mois", icon=ft.Icons.LINK_OFF_OUTLINED, on_click=clear_month_topics),
                ],
                wrap=True,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    _theme_chip(row)
                    for row in themes
                ],
                wrap=True,
                spacing=8,
            )
            if themes
            else ft.Text("Aucun theme cree. Ajoute des themes avant l'affectation mensuelle.", color=MUTED, size=12),
        ]

    for control in (status_filter,):
        control.on_change = lambda event: (render(), _update())

    root = ft.Column(
        controls=[
            module_header(
                "Gestion des Meeting Toolbox Talk",
                "Planification bilingue anglais / francais des topics journaliers.",
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
                                month_field,
                                status_filter,
                                ft.ElevatedButton("Charger le mois", icon=ft.Icons.CALENDAR_MONTH_OUTLINED, on_click=refresh),
                            ],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        summary_row,
                    ],
                    spacing=12,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Banque de themes bilingues", color=TEXT, weight=ft.FontWeight.BOLD),
                        theme_area,
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Theme journalier bilingue", color=TEXT, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                date_field,
                                topic_field,
                                facilitator_field,
                                site_field,
                                ft.ElevatedButton("Enregistrer", icon=ft.Icons.SAVE_OUTLINED, on_click=save_topic),
                                ft.OutlinedButton("Affecter aux dates selectionnees", icon=ft.Icons.CHECKLIST_OUTLINED, on_click=assign_selected_dates),
                            ],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=10,
                ),
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
    refresh()
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


def _state_badge(state: str) -> ft.Control:
    done = state == "done"
    color = SUCCESS if done else DANGER
    label = "Renseigne" if done else "A completer"
    return ft.Container(
        bgcolor=color,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color="#FFFFFF"),
    )


def _theme_chip(row: dict[str, Any]) -> ft.Control:
    mandatory = bool(row.get("obligatoire"))
    color = WARNING if mandatory else PRIMARY
    label = f"{row.get('theme') or '-'}" + (" | obligatoire" if mandatory else "")
    return ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=12, color=color),
    )

