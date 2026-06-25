from __future__ import annotations

from datetime import date
from typing import Any

import flet as ft

from app.services.drilling_service import (
    add_equipment,
    count_drilling_reports,
    create_drilling_report,
    delete_drilling_report,
    delete_equipment,
    get_drilling_kpis,
    get_drilling_report,
    list_drilling_reports,
    list_equipment,
    update_drilling_report,
    validate_drilling_report,
    reject_drilling_report,
    update_equipment,
)
from app.ui.theme import DANGER, PRIMARY, SUCCESS, WARNING

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#071321"
CARD    = "#0F2336"
CARD2   = "#10243A"
BORDER  = "#1E3A56"
TEXT    = "#FFFFFF"
MUTED   = "#9DB0C5"
HEAD    = "#112240"

PAGE_SIZE = 10

_STATUS_COLOR = {
    "draft":     MUTED,
    "submitted": WARNING,
    "validated": SUCCESS,
    "synced":    PRIMARY,
}
_STATUS_LABEL = {
    "draft":     "Brouillon",
    "submitted": "Soumis",
    "validated": "Validé",
    "synced":    "Synchronisé",
}
_SHIFT_OPTS = ["DAY", "NIGHT"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chip(label: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, size=10, color=color, weight=ft.FontWeight.BOLD),
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        border_radius=12,
        border=ft.border.all(1, color),
    )


def _kpi_card(icon: str, label: str, value: str, color: str = PRIMARY) -> ft.Container:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=10,
        padding=14,
        expand=True,
        content=ft.Column(
            controls=[
                ft.Row(controls=[
                    ft.Icon(icon, color=color, size=20),
                    ft.Text(label, size=11, color=MUTED),
                ], spacing=6),
                ft.Text(value, size=26, weight=ft.FontWeight.BOLD, color=TEXT),
            ],
            spacing=4,
        ),
    )


def _section_title(text: str) -> ft.Text:
    return ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color=MUTED)


def _field(label: str, ctrl: ft.Control) -> ft.Column:
    return ft.Column(
        controls=[ft.Text(label, size=11, color=MUTED), ctrl],
        spacing=4,
        expand=True,
    )


def _txt(hint: str = "", value: str = "", expand: bool = True) -> ft.TextField:
    return ft.TextField(
        value=value,
        hint_text=hint,
        border_color=BORDER,
        focused_border_color=PRIMARY,
        color=TEXT,
        hint_style=ft.TextStyle(color=MUTED),
        bgcolor=CARD2,
        border_radius=6,
        height=40,
        text_size=13,
        expand=expand,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
    )


def _dropdown(options: list[str], value: str | None = None) -> ft.Dropdown:
    return ft.Dropdown(
        value=value or options[0],
        options=[ft.dropdown.Option(o) for o in options],
        border_color=BORDER,
        focused_border_color=PRIMARY,
        color=TEXT,
        bgcolor=CARD2,
        border_radius=6,
        height=40,
        text_size=13,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
        expand=True,
    )


# ── Log entry row widget ──────────────────────────────────────────────────────

class _LogRow:
    def __init__(self, data: dict[str, Any] | None = None, on_delete=None):
        d = data or {}
        self.f_bh   = _txt("BGC 000000", str(d.get("bh_number") or ""), expand=False)
        self.f_from = _txt("0", str(d.get("depth_from") or ""), expand=False)
        self.f_to   = _txt("0", str(d.get("depth_to") or ""), expand=False)
        self.f_run  = ft.TextField(
            value=str(d.get("run") or ""),
            hint_text="auto",
            border_color=BORDER,
            color=MUTED,
            bgcolor="#071321",
            border_radius=6,
            height=36,
            text_size=12,
            expand=False,
            read_only=True,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            width=60,
        )
        self.f_adv  = _txt("0", str(d.get("advance") or ""), expand=False)
        self.f_time = _txt("0", str(d.get("time_hours") or ""), expand=False)
        self.f_comm = _txt("", str(d.get("comments") or ""), expand=False)

        for f in (self.f_from, self.f_to):
            f.on_change = lambda _: self._update_run()

        def _w(ctrl, w: int) -> ft.Container:
            ctrl.width = w
            return ctrl

        self.row = ft.Row(
            controls=[
                _w(self.f_bh,   110),
                _w(self.f_from, 65),
                _w(self.f_to,   65),
                self.f_run,
                _w(self.f_adv,  65),
                _w(self.f_time, 55),
                _w(self.f_comm, 200),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=DANGER,
                    icon_size=18,
                    on_click=lambda _: on_delete(self) if on_delete else None,
                    tooltip="Supprimer",
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _update_run(self) -> None:
        try:
            df = float(self.f_from.value or 0)
            dt = float(self.f_to.value or 0)
            self.f_run.value = str(round(dt - df, 2))
        except ValueError:
            self.f_run.value = ""
        if self.f_run.page:
            self.f_run.update()

    def to_dict(self) -> dict[str, Any]:
        def _f(v: str) -> float | None:
            try:
                return float(v) if v.strip() else None
            except ValueError:
                return None
        return {
            "bh_number":   self.f_bh.value or None,
            "depth_from":  _f(self.f_from.value or ""),
            "depth_to":    _f(self.f_to.value or ""),
            "run":         _f(self.f_run.value or ""),
            "advance":     _f(self.f_adv.value or ""),
            "time_hours":  _f(self.f_time.value or ""),
            "comments":    self.f_comm.value or None,
        }


# ── Report form dialog ────────────────────────────────────────────────────────

def _report_form_dialog(
    page: ft.Page,
    on_save,
    report: dict[str, Any] | None = None,
) -> ft.AlertDialog:
    r = report or {}
    equipment = list_equipment(active_only=True)
    is_edit = bool(r.get("id"))
    title_str = "Modifier rapport" if is_edit else "Nouveau rapport"

    # Header fields
    f_shift    = _dropdown(_SHIFT_OPTS, r.get("shift", "DAY"))
    f_date     = _txt("YYYY-MM-DD", r.get("report_date") or date.today().isoformat())
    f_rig_type = _txt("AC/RC", r.get("rig_type") or "")
    f_rig_num  = _txt("001", r.get("rig_number") or "")
    f_location = _txt("Folona", r.get("contract_location") or "")
    f_hole     = _txt("", r.get("hole_number") or "")
    f_angle    = _txt("60", str(r.get("angle") or ""))
    f_client   = _txt("SOMISY", r.get("client") or "")
    f_operator = _txt("", r.get("operator_name") or "")
    f_refueler = _txt("", r.get("refueler_name") or "")

    # Diesel fields
    diesel_data = r.get("diesel") or {}
    diesel_fields: dict[str, ft.TextField] = {}
    diesel_rows = []
    for eq in equipment:
        code = eq["code"]
        tf = _txt("0", str(diesel_data.get(code) or ""), expand=False)
        tf.width = 120
        diesel_fields[code] = tf
        diesel_rows.append(
            ft.Row(controls=[
                ft.Text(eq["name"], size=12, color=TEXT, expand=True),
                tf,
                ft.Text(eq["unit"], size=11, color=MUTED),
            ], spacing=8)
        )

    # Log rows
    log_rows: list[_LogRow] = []
    rows_col = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)

    def _delete_log_row(lr: _LogRow) -> None:
        log_rows.remove(lr)
        rows_col.controls.remove(lr.row)
        rows_col.update()

    def _add_log_row(data: dict[str, Any] | None = None) -> None:
        lr = _LogRow(data, on_delete=_delete_log_row)
        log_rows.append(lr)
        rows_col.controls.append(lr.row)
        if rows_col.page:
            rows_col.update()

    for entry in r.get("entries") or [{}]:
        _add_log_row(entry)
    if not log_rows:
        _add_log_row()

    err_txt = ft.Text("", color=DANGER, size=12)

    def _save(_) -> None:
        try:
            adv = sum(
                float(lr.f_adv.value or 0)
                for lr in log_rows
                if lr.f_adv.value
            )
            diesel = {}
            for code, tf in diesel_fields.items():
                try:
                    v = float(tf.value or 0)
                    if v:
                        diesel[code] = v
                except ValueError:
                    pass
            data = {
                "shift":             f_shift.value,
                "report_date":       f_date.value,
                "rig_type":          f_rig_type.value or None,
                "rig_number":        f_rig_num.value or None,
                "contract_location": f_location.value or None,
                "hole_number":       f_hole.value or None,
                "angle":             float(f_angle.value) if f_angle.value else None,
                "client":            f_client.value or None,
                "total_advance":     round(adv, 2),
                "diesel":            diesel,
                "refueler_name":     f_refueler.value or None,
                "operator_name":     f_operator.value or None,
                "entries":           [lr.to_dict() for lr in log_rows],
                "status":            r.get("status") or "draft",
            }
            on_save(data, r.get("id"))
            dlg.open = False
            page.update()
        except Exception as exc:
            err_txt.value = str(exc)
            err_txt.update()

    # Column headers for log table
    def _hdr(t: str, w: int) -> ft.Container:
        return ft.Container(
            ft.Text(t, size=10, color=MUTED, weight=ft.FontWeight.BOLD),
            width=w,
        )

    log_header = ft.Row(controls=[
        _hdr("B/H NUMBER", 110),
        _hdr("FROM (m)", 65),
        _hdr("TO (m)", 65),
        _hdr("RUN", 60),
        _hdr("ADVANCE", 65),
        _hdr("TIME (h)", 55),
        _hdr("COMMENTS / SPECIAL CONDITIONS", 200),
        ft.Container(width=40),
    ], spacing=6)

    content = ft.Column(
        controls=[
            _section_title("INFORMATIONS GÉNÉRALES"),
            ft.Row(controls=[
                _field("Shift", f_shift),
                _field("Date", f_date),
                _field("Type Rig", f_rig_type),
                _field("N° Rig", f_rig_num),
            ], spacing=12),
            ft.Row(controls=[
                _field("Localisation", f_location),
                _field("N° Trou", f_hole),
                _field("Angle (°)", f_angle),
                _field("Client", f_client),
            ], spacing=12),
            ft.Row(controls=[
                _field("Opérateur", f_operator),
                _field("Ravitailleur", f_refueler),
            ], spacing=12),
            ft.Divider(color=BORDER),
            _section_title("TABLEAU DE FORAGE"),
            log_header,
            rows_col,
            ft.TextButton(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.ADD, size=16, color=PRIMARY),
                    ft.Text("Ajouter ligne", color=PRIMARY, size=12),
                ], tight=True, spacing=4),
                on_click=lambda _: _add_log_row(),
            ),
            ft.Divider(color=BORDER),
            _section_title("DIESEL RE-FUELING"),
            *diesel_rows,
            err_txt,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        width=820,
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title_str, color=TEXT, size=16, weight=ft.FontWeight.BOLD),
        bgcolor=CARD,
        content=ft.Container(content=content, height=560),
        actions=[
            ft.TextButton("Annuler", on_click=lambda _: (setattr(dlg, "open", False), page.update())),
            ft.ElevatedButton(
                "Enregistrer",
                bgcolor=PRIMARY,
                color=TEXT,
                on_click=_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


# ── Detail view (read-only) ───────────────────────────────────────────────────

def _detail_dialog(page: ft.Page, report: dict[str, Any], on_validate, on_reject, on_delete, on_export_pdf) -> ft.AlertDialog:
    r = report
    equipment = list_equipment(active_only=False)
    diesel = r.get("diesel") or {}

    def _row2(label: str, value: str) -> ft.Row:
        return ft.Row(controls=[
            ft.Text(label + ":", size=12, color=MUTED, width=160),
            ft.Text(str(value or "—"), size=12, color=TEXT),
        ], spacing=8)

    status = r.get("status", "draft")
    sc = _STATUS_COLOR.get(status, MUTED)

    # Entries table
    entry_rows: list[ft.DataRow] = []
    for e in r.get("entries") or []:
        entry_rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(str(e.get("bh_number") or "—"), size=11, color=TEXT)),
            ft.DataCell(ft.Text(str(e.get("depth_from") or ""), size=11, color=TEXT)),
            ft.DataCell(ft.Text(str(e.get("depth_to") or ""), size=11, color=TEXT)),
            ft.DataCell(ft.Text(str(e.get("run") or ""), size=11, color=TEXT)),
            ft.DataCell(ft.Text(str(e.get("advance") or ""), size=11, color=TEXT)),
            ft.DataCell(ft.Text(str(e.get("time_hours") or ""), size=11, color=TEXT)),
            ft.DataCell(ft.Text(str(e.get("comments") or ""), size=11, color=MUTED)),
        ]))

    dt_cols = [ft.DataColumn(ft.Text(h, size=10, color=MUTED, weight=ft.FontWeight.BOLD)) for h in
               ["B/H NUMBER", "FROM", "TO", "RUN", "ADVANCE", "TIME", "COMMENTS"]]

    diesel_items = []
    for eq in equipment:
        v = diesel.get(eq["code"])
        if v:
            diesel_items.append(ft.Row(controls=[
                ft.Text(eq["name"], size=12, color=TEXT, expand=True),
                ft.Text(f"{v} {eq['unit']}", size=12, color=TEXT, weight=ft.FontWeight.BOLD),
            ]))

    actions = [
        ft.TextButton("Fermer", on_click=lambda _: (setattr(dlg, "open", False), page.update())),
        ft.ElevatedButton(
            "Exporter PDF",
            icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
            bgcolor="#1E3A56",
            color=TEXT,
            on_click=lambda _: on_export_pdf(r),
        ),
    ]
    if status == "submitted":
        actions.insert(1, ft.ElevatedButton(
            "Valider", bgcolor=SUCCESS, color=TEXT,
            on_click=lambda _: (on_validate(r["id"]), setattr(dlg, "open", False), page.update()),
        ))
    if status == "validated":
        actions.insert(1, ft.TextButton(
            "Rejeter", style=ft.ButtonStyle(color=DANGER),
            on_click=lambda _: (on_reject(r["id"]), setattr(dlg, "open", False), page.update()),
        ))
    if status in ("draft", "submitted"):
        actions.insert(1, ft.TextButton(
            "Supprimer", style=ft.ButtonStyle(color=DANGER),
            on_click=lambda _: (on_delete(r["id"]), setattr(dlg, "open", False), page.update()),
        ))

    content = ft.Column(
        controls=[
            ft.Row(controls=[
                _chip(_STATUS_LABEL.get(status, status), sc),
                ft.Text(f"Rapport du {r.get('report_date', '')} — Shift {r.get('shift', '')}", size=13, color=MUTED),
            ], spacing=10),
            ft.Divider(color=BORDER),
            ft.Row(controls=[
                ft.Column(controls=[
                    _row2("Rig", f"{r.get('rig_type','')} {r.get('rig_number','')}".strip()),
                    _row2("Localisation", r.get("contract_location")),
                    _row2("N° Trou", r.get("hole_number")),
                    _row2("Angle", f"{r.get('angle','')}°" if r.get("angle") else "—"),
                ], spacing=6, expand=True),
                ft.Column(controls=[
                    _row2("Client", r.get("client")),
                    _row2("Opérateur", r.get("operator_name")),
                    _row2("Superviseur", r.get("supervisor_name")),
                    _row2("Avance totale", f"{r.get('total_advance', 0)} m"),
                ], spacing=6, expand=True),
            ], spacing=20),
            ft.Divider(color=BORDER),
            ft.Text("TABLEAU DE FORAGE", size=11, color=MUTED, weight=ft.FontWeight.BOLD),
            ft.DataTable(
                columns=dt_cols,
                rows=entry_rows,
                border=ft.border.all(1, BORDER),
                heading_row_color=HEAD,
                data_row_color={ft.ControlState.DEFAULT: CARD2},
                column_spacing=12,
                horizontal_margin=8,
            ) if entry_rows else ft.Text("Aucune entrée", size=12, color=MUTED),
            ft.Divider(color=BORDER),
            ft.Text("DIESEL RE-FUELING", size=11, color=MUTED, weight=ft.FontWeight.BOLD),
            *(diesel_items or [ft.Text("Aucun carburant enregistré", size=12, color=MUTED)]),
            ft.Divider(color=BORDER),
            ft.Row(controls=[
                ft.Text(f"Ravitailleur: {r.get('refueler_name') or '—'}", size=12, color=MUTED, expand=True),
                ft.Text(f"Validé le: {r.get('validated_at','')[:10] if r.get('validated_at') else '—'}", size=12, color=MUTED),
            ]),
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        width=780,
    )

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=CARD,
        title=ft.Text("Détail du rapport", color=TEXT, size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(content=content, height=520),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


# ── Equipment management panel ────────────────────────────────────────────────

def _equipment_panel(page: ft.Page) -> ft.Control:
    eq_list = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    msg_txt = ft.Text("", size=12)
    f_name  = _txt("RIG – SDMA 01")
    f_code  = _txt("SDMA01")
    f_unit  = _txt("Litre")

    def _refresh_list() -> None:
        eq_list.controls.clear()
        for eq in list_equipment(active_only=False):
            active = bool(eq.get("active", 1))
            eq_list.controls.append(ft.Container(
                bgcolor=CARD2,
                border=ft.border.all(1, BORDER),
                border_radius=6,
                padding=8,
                content=ft.Row(controls=[
                    ft.Icon(
                        ft.Icons.LOCAL_GAS_STATION_OUTLINED,
                        color=PRIMARY if active else MUTED,
                        size=18,
                    ),
                    ft.Column(controls=[
                        ft.Text(eq["name"], size=12, color=TEXT if active else MUTED),
                        ft.Text(f"Code: {eq['code']} | Unité: {eq['unit']}", size=10, color=MUTED),
                    ], spacing=2, expand=True),
                    ft.IconButton(
                        icon=ft.Icons.TOGGLE_ON if active else ft.Icons.TOGGLE_OFF,
                        icon_color=SUCCESS if active else MUTED,
                        icon_size=22,
                        tooltip="Activer/Désactiver",
                        on_click=lambda _, e=eq: _toggle(e),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=DANGER,
                        icon_size=18,
                        tooltip="Supprimer",
                        on_click=lambda _, e=eq: _delete(e["id"]),
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        if eq_list.page:
            eq_list.update()

    def _toggle(eq: dict) -> None:
        update_equipment(eq["id"], eq["name"], eq["code"], eq["unit"], not eq.get("active", 1))
        _refresh_list()

    def _delete(eq_id: int) -> None:
        delete_equipment(eq_id)
        _refresh_list()

    def _add(_) -> None:
        name = f_name.value.strip()
        code = f_code.value.strip()
        if not name or not code:
            msg_txt.value = "Nom et code requis."
            msg_txt.color = DANGER
            msg_txt.update()
            return
        try:
            add_equipment(name, code, f_unit.value.strip() or "Litre")
            f_name.value = f_code.value = f_unit.value = ""
            msg_txt.value = "Équipement ajouté."
            msg_txt.color = SUCCESS
            page.update()
            _refresh_list()
        except Exception as exc:
            msg_txt.value = str(exc)
            msg_txt.color = DANGER
            msg_txt.update()

    _refresh_list()

    return ft.Column(
        controls=[
            _section_title("ÉQUIPEMENTS DIESEL"),
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=12,
                content=ft.Column(controls=[
                    ft.Text("Ajouter un équipement", size=13, color=TEXT, weight=ft.FontWeight.BOLD),
                    ft.Row(controls=[
                        _field("Nom", f_name),
                        _field("Code", f_code),
                        _field("Unité", f_unit),
                        ft.Container(
                            ft.ElevatedButton("Ajouter", bgcolor=PRIMARY, color=TEXT, on_click=_add),
                            padding=ft.padding.only(top=16),
                        ),
                    ], spacing=12),
                    msg_txt,
                ], spacing=8),
            ),
            ft.Container(height=8),
            eq_list,
        ],
        spacing=10,
        expand=True,
    )


# ── Main page ─────────────────────────────────────────────────────────────────

def drilling_page(page: ft.Page) -> ft.Control:
    state: dict[str, Any] = {
        "tab": "list",
        "page": 0,
        "status": "all",
        "location": "",
        "active": True,
    }

    kpi_row   = ft.Row(spacing=12)
    list_col  = ft.Column(spacing=0, expand=True)
    pager_row = ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER)
    msg_bar   = ft.Text("", size=12)

    f_filter_loc = _txt("Localisation…")
    f_filter_loc.width = 180
    f_filter_loc.on_submit = lambda _: _refresh()

    status_dd = ft.Dropdown(
        value="all",
        options=[ft.dropdown.Option("all", "Tous")] + [
            ft.dropdown.Option(k, v) for k, v in _STATUS_LABEL.items()
        ],
        border_color=BORDER,
        focused_border_color=PRIMARY,
        color=TEXT,
        bgcolor=CARD2,
        border_radius=6,
        height=40,
        text_size=12,
        width=140,
        on_change=lambda e: (state.update({"status": e.control.value, "page": 0}), _refresh()),
    )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    def _tab_style(active: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            color=TEXT if active else MUTED,
            bgcolor=CARD2 if active else "transparent",
            side={ft.ControlState.DEFAULT: ft.BorderSide(1, BORDER if active else "transparent")},
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
        )

    btn_list = ft.TextButton(
        content=ft.Row(controls=[ft.Icon(ft.Icons.LIST_ALT_OUTLINED, size=16), ft.Text("Rapports")], spacing=6, tight=True),
        on_click=lambda _: _switch_tab("list"),
    )
    btn_equip = ft.TextButton(
        content=ft.Row(controls=[ft.Icon(ft.Icons.LOCAL_GAS_STATION_OUTLINED, size=16), ft.Text("Équipements")], spacing=6, tight=True),
        on_click=lambda _: _switch_tab("equipment"),
    )
    tab_bar = ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=8,
        content=ft.Row(controls=[btn_list, btn_equip], spacing=8),
    )

    content_area = ft.Container(expand=True)
    equip_panel  = _equipment_panel(page)

    def _switch_tab(tab: str) -> None:
        state["tab"] = tab
        btn_list.style  = _tab_style(tab == "list")
        btn_equip.style = _tab_style(tab == "equipment")
        content_area.content = _list_view() if tab == "list" else equip_panel
        if content_area.page:
            content_area.update()
        if tab_bar.page:
            tab_bar.update()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    def _refresh_kpis() -> None:
        kpis = get_drilling_kpis()
        kpi_row.controls = [
            _kpi_card(ft.Icons.DESCRIPTION_OUTLINED,   "Total rapports",  str(kpis["total"])),
            _kpi_card(ft.Icons.PENDING_OUTLINED,        "En attente",      str(kpis["pending"]),   WARNING),
            _kpi_card(ft.Icons.CHECK_CIRCLE_OUTLINED,   "Validés",         str(kpis["validated"]), SUCCESS),
            _kpi_card(ft.Icons.STRAIGHTEN_OUTLINED,     "Avance totale",   f"{kpis['total_advance_m']:.1f} m", PRIMARY),
            _kpi_card(ft.Icons.TODAY_OUTLINED,          "Aujourd'hui",     str(kpis["today"]),     "#60A5FA"),
        ]
        if kpi_row.page:
            kpi_row.update()

    # ── List view ─────────────────────────────────────────────────────────────
    def _list_view() -> ft.Control:
        return ft.Column(
            controls=[
                ft.Row(controls=[
                    ft.Text("Filtre :", size=12, color=MUTED),
                    f_filter_loc,
                    status_dd,
                    ft.IconButton(ft.Icons.SEARCH, icon_color=PRIMARY, on_click=lambda _: _refresh(), tooltip="Rechercher"),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "Nouveau rapport",
                        icon=ft.Icons.ADD,
                        bgcolor=PRIMARY,
                        color=TEXT,
                        on_click=_open_create,
                    ),
                ], spacing=8),
                msg_bar,
                list_col,
                pager_row,
            ],
            spacing=10,
            expand=True,
        )

    # ── Table rows ────────────────────────────────────────────────────────────
    def _refresh(_=None) -> None:
        if not state["active"]:
            return
        loc    = f_filter_loc.value.strip()
        status = state["status"]
        pg     = state["page"]
        total  = count_drilling_reports(
            status=status if status != "all" else None,
            location=loc or None,
        )
        reports = list_drilling_reports(
            status=status if status != "all" else None,
            location=loc or None,
            limit=PAGE_SIZE,
            offset=pg * PAGE_SIZE,
        )
        max_page = max((total - 1) // PAGE_SIZE, 0)

        list_col.controls = [
            ft.Container(
                bgcolor=HEAD,
                border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                content=ft.Row(controls=[
                    ft.Text("Date",          size=11, color=MUTED, width=90),
                    ft.Text("Shift",         size=11, color=MUTED, width=55),
                    ft.Text("Rig",           size=11, color=MUTED, width=80),
                    ft.Text("Localisation",  size=11, color=MUTED, width=110),
                    ft.Text("Client",        size=11, color=MUTED, width=90),
                    ft.Text("Avance",        size=11, color=MUTED, width=70),
                    ft.Text("Statut",        size=11, color=MUTED, width=90),
                    ft.Container(expand=True),
                ], spacing=0),
            )
        ]

        for rep in reports:
            status_c = _STATUS_COLOR.get(rep["status"], MUTED)
            status_l = _STATUS_LABEL.get(rep["status"], rep["status"])
            list_col.controls.append(ft.Container(
                bgcolor=CARD2,
                border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                ink=True,
                on_click=lambda _, r=rep: _open_detail(r["id"]),
                content=ft.Row(controls=[
                    ft.Text(rep.get("report_date", "")[:10], size=12, color=TEXT, width=90),
                    ft.Text(rep.get("shift", ""), size=12, color=TEXT, width=55),
                    ft.Text(f"{rep.get('rig_type','')} {rep.get('rig_number','')}".strip() or "—", size=12, color=TEXT, width=80),
                    ft.Text(rep.get("contract_location") or "—", size=12, color=TEXT, width=110),
                    ft.Text(rep.get("client") or "—", size=12, color=TEXT, width=90),
                    ft.Text(f"{rep.get('total_advance', 0)} m", size=12, color=TEXT, width=70),
                    _chip(status_l, status_c),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED,
                        icon_color=PRIMARY,
                        icon_size=16,
                        tooltip="Modifier",
                        on_click=lambda _, r=rep: _open_edit(r["id"]),
                    ),
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))

        # Pagination
        pager_row.controls = []
        if max_page > 0:
            pager_row.controls.append(ft.IconButton(
                ft.Icons.CHEVRON_LEFT,
                icon_color=PRIMARY if pg > 0 else MUTED,
                disabled=pg == 0,
                on_click=lambda _: _go_page(pg - 1),
            ))
            for p in range(max_page + 1):
                pager_row.controls.append(ft.TextButton(
                    str(p + 1),
                    style=ft.ButtonStyle(
                        color=TEXT if p == pg else MUTED,
                        bgcolor=PRIMARY if p == pg else "transparent",
                    ),
                    on_click=lambda _, pp=p: _go_page(pp),
                ))
            pager_row.controls.append(ft.IconButton(
                ft.Icons.CHEVRON_RIGHT,
                icon_color=PRIMARY if pg < max_page else MUTED,
                disabled=pg >= max_page,
                on_click=lambda _: _go_page(pg + 1),
            ))

        _refresh_kpis()
        if list_col.page:
            list_col.update()
        if pager_row.page:
            pager_row.update()

    def _go_page(p: int) -> None:
        state["page"] = p
        _refresh()

    # ── Actions ───────────────────────────────────────────────────────────────
    def _open_create(_=None) -> None:
        def _save(data: dict, _id: int | None) -> None:
            create_drilling_report(data)
            msg_bar.value = "Rapport créé."
            msg_bar.color = SUCCESS
            _refresh()
            if msg_bar.page:
                msg_bar.update()

        dlg = _report_form_dialog(page, _save)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _open_edit(report_id: int) -> None:
        rep = get_drilling_report(report_id)
        if not rep:
            return

        def _save(data: dict, rid: int) -> None:
            update_drilling_report(rid, data)
            msg_bar.value = "Rapport mis à jour."
            msg_bar.color = SUCCESS
            _refresh()
            if msg_bar.page:
                msg_bar.update()

        dlg = _report_form_dialog(page, _save, rep)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _open_detail(report_id: int) -> None:
        rep = get_drilling_report(report_id)
        if not rep:
            return

        def _do_validate(rid: int) -> None:
            validate_drilling_report(rid, "Superviseur")
            msg_bar.value = "Rapport validé."
            msg_bar.color = SUCCESS
            _refresh()
            if msg_bar.page:
                msg_bar.update()

        def _do_reject(rid: int) -> None:
            reject_drilling_report(rid)
            msg_bar.value = "Validation annulée."
            msg_bar.color = WARNING
            _refresh()
            if msg_bar.page:
                msg_bar.update()

        def _do_delete(rid: int) -> None:
            delete_drilling_report(rid)
            msg_bar.value = "Rapport supprimé."
            msg_bar.color = DANGER
            _refresh()
            if msg_bar.page:
                msg_bar.update()

        def _do_export(r: dict) -> None:
            _export_pdf(page, r, msg_bar)

        dlg = _detail_dialog(page, rep, _do_validate, _do_reject, _do_delete, _do_export)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Init ──────────────────────────────────────────────────────────────────
    _switch_tab("list")
    _refresh()

    root = ft.Column(
        controls=[
            tab_bar,
            kpi_row,
            content_area,
        ],
        spacing=12,
        expand=True,
    )
    return ft.Container(bgcolor=BG, expand=True, padding=12, content=root)


# ── PDF Export ────────────────────────────────────────────────────────────────

def _export_pdf(page: ft.Page, report: dict[str, Any], msg_ctrl: ft.Text) -> None:
    try:
        from app.services.drilling_pdf_service import build_drilling_pdf
        from app.config import EXPORTS_DIR
        import os

        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = (report.get("report_date") or "")[:10].replace("-", "")
        rig_str  = (report.get("rig_number") or "").replace(" ", "_")
        fname    = f"drilling_report_{date_str}_{rig_str}.pdf"
        out_path = EXPORTS_DIR / fname
        counter  = 1
        while out_path.exists():
            out_path = EXPORTS_DIR / f"drilling_report_{date_str}_{rig_str}_{counter}.pdf"
            counter += 1

        pdf_bytes = build_drilling_pdf(report)
        out_path.write_bytes(pdf_bytes)

        msg_ctrl.value = f"PDF exporté : {out_path.name}"
        msg_ctrl.color = SUCCESS
        if msg_ctrl.page:
            msg_ctrl.update()
        os.startfile(str(out_path))
    except Exception as exc:
        msg_ctrl.value = f"Erreur PDF : {exc}"
        msg_ctrl.color = DANGER
        if msg_ctrl.page:
            msg_ctrl.update()
