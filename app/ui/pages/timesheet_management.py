from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import flet as ft

from app.config import EXPORTS_DIR
from app.services.attendance_export_service import (
    export_monthly_10h_timesheet_pdf,
    export_monthly_10h_timesheet_xlsx,
)
from app.services.employee_service import list_employees
from app.services.monthly_timesheet_service import current_monthly_timesheet_month
from app.ui.pages.monthly_timesheet import monthly_timesheet_page
from app.ui.pages.timesheet import timesheet_page
from app.ui.theme import DANGER, PRIMARY, SUCCESS, WARNING, INFO, MUTED

from app.ui.components.dark_styles import BG, BORDER, CARD

DARK_TEXT  = "#FFFFFF"
DARK_MUTED = "#9DB0C5"
DARK_BRD   = "#1E3A56"

MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
             "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
MONTHS_SH = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]


def timesheet_management_page(page: ft.Page) -> ft.Control:
    content = ft.Container(expand=True, bgcolor="#071321")
    state = {"active": "21-20"}
    _tab_cache: dict = {}

    def _get_tab(name: str) -> ft.Control:
        if name not in _tab_cache:
            if name == "21-20":
                _tab_cache[name] = timesheet_page(page)
            elif name == "1-25":
                _tab_cache[name] = monthly_timesheet_page(page)
            else:
                _tab_cache[name] = _download_center(page)
        return _tab_cache[name]

    def render() -> None:
        content.content = _get_tab(state["active"])
        button_21.style  = _tab_style(state["active"] == "21-20")
        button_125.style = _tab_style(state["active"] == "1-25")
        button_dl.style  = _tab_style(state["active"] == "downloads")

    def switch(target: str) -> None:
        state["active"] = target
        render()
        try:
            root.update()
        except (RuntimeError, IndexError):
            pass

    button_21 = ft.TextButton(
        content=ft.Row(controls=[
            ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=18),
            ft.Text("TimeSheet 21-20", weight=ft.FontWeight.BOLD),
        ], spacing=8, tight=True),
        on_click=lambda e: switch("21-20"),
    )
    button_125 = ft.TextButton(
        content=ft.Row(controls=[
            ft.Icon(ft.Icons.EVENT_NOTE_OUTLINED, size=18),
            ft.Text("TimeSheet 1-25", weight=ft.FontWeight.BOLD),
        ], spacing=8, tight=True),
        on_click=lambda e: switch("1-25"),
    )
    button_dl = ft.TextButton(
        content=ft.Row(controls=[
            ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, size=18),
            ft.Text("Téléchargements", weight=ft.FontWeight.BOLD),
        ], spacing=8, tight=True),
        on_click=lambda e: switch("downloads"),
    )

    root = ft.Column(
        controls=[
            ft.Container(
                bgcolor=CARD,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=8,
                content=ft.Row(controls=[button_21, button_125, button_dl], wrap=True, spacing=8),
            ),
            content,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


# ─────────────────────────────────────────────────────────────────────────────
# Download center panel
# ─────────────────────────────────────────────────────────────────────────────

def _download_center(page: ft.Page) -> ft.Control:
    today = date.today()
    ds: dict[str, Any] = {"month": today.month, "year": today.year, "ts_type": "1_25"}

    status_txt = ft.Text("", size=12, color=MUTED)
    files_col   = ft.Column(spacing=6)
    spinner     = ft.ProgressRing(color=PRIMARY, width=18, height=18, stroke_width=2, visible=False)

    def _month_str() -> str:
        return f"{ds['year']}-{ds['month']:02d}"

    def _period_label() -> str:
        y, m, tp = ds["year"], ds["month"], ds["ts_type"]
        if tp == "1_25":
            return f"01 au 25 {MONTHS_SH[m-1]} {y}"
        nm = m + 1 if m < 12 else 1
        ny = y if m < 12 else y + 1
        return f"21 {MONTHS_SH[m-1]} {y} → 20 {MONTHS_SH[nm-1]} {ny}"

    def _notify(msg: str, color: str = MUTED) -> None:
        status_txt.value = msg
        status_txt.color = color
        spinner.visible = False
        try:
            status_txt.update(); spinner.update()
        except Exception:
            pass

    def _open(path: Path) -> None:
        try:
            os.startfile(str(path))
        except Exception as exc:
            _notify(f"Impossible d'ouvrir : {exc}", DANGER)

    def _busy(on: bool) -> None:
        spinner.visible = on
        try: spinner.update()
        except Exception: pass

    # ── Month navigation ─────────────────────────────────────────────────────
    month_lbl = ft.Text(
        "", size=17, weight=ft.FontWeight.BOLD, color=DARK_TEXT,
        text_align=ft.TextAlign.CENTER,
    )

    def prev_month(_: Any = None) -> None:
        m = ds["month"] - 1
        if m < 1: m = 12; ds["year"] -= 1
        ds["month"] = m; _rebuild()

    def next_month(_: Any = None) -> None:
        m = ds["month"] + 1
        if m > 12: m = 1; ds["year"] += 1
        ds["month"] = m; _rebuild()

    month_nav = ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BRD),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row([
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
                icon_color=DARK_MUTED, icon_size=22,
                on_click=lambda e: prev_month(),
            ),
            ft.Column([
                month_lbl,
                ft.Text("Sélection du mois", size=9, color=DARK_MUTED,
                        text_align=ft.TextAlign.CENTER),
            ], spacing=2, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
                icon_color=DARK_MUTED, icon_size=22,
                on_click=lambda e: next_month(),
            ),
        ], spacing=4),
    )

    # ── Period selector ───────────────────────────────────────────────────────
    period_row = ft.Row(spacing=8)

    def _period_btn(key: str, label: str) -> ft.Container:
        active = ds["ts_type"] == key
        def click(_: Any, k: str = key) -> None:
            ds["ts_type"] = k; _rebuild()
        return ft.Container(
            expand=True, border_radius=10,
            bgcolor=PRIMARY if active else f"#10{PRIMARY[1:]}",
            border=ft.border.all(1, PRIMARY if active else DARK_BRD),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            ink=True, on_click=click,
            content=ft.Text(
                label, size=13,
                color=DARK_TEXT if active else DARK_MUTED,
                weight=ft.FontWeight.W_600,
                text_align=ft.TextAlign.CENTER,
            ),
        )

    # ── Download helpers ──────────────────────────────────────────────────────
    def _do_export(fmt: str, emp_id: int | None = None, silent: bool = False) -> Path | None:
        try:
            m = _month_str()
            tp = ds["ts_type"]
            emp_lbl = f" — Employé #{emp_id}" if emp_id else ""
            if not silent:
                _notify(f"Génération {fmt.upper()} {_period_label()}{emp_lbl}…", MUTED)
                _busy(True)
            if fmt == "xlsx":
                path = export_monthly_10h_timesheet_xlsx(m, ts_type=tp, employee_id=emp_id)
            else:
                path = export_monthly_10h_timesheet_pdf(m, ts_type=tp, employee_id=emp_id)
            if not silent:
                _notify(f"Généré : {path.name}  ({path.stat().st_size // 1024} Ko)", SUCCESS)
                _rebuild_files()
            return path
        except Exception as exc:
            if not silent:
                _notify(f"Erreur : {exc}", DANGER)
            return None

    def export_xlsx(_: Any = None) -> None:
        path = _do_export("xlsx")
        if path: _open(path)

    def export_pdf(_: Any = None) -> None:
        path = _do_export("pdf")
        if path: _open(path)

    def export_all_employees_xlsx(_: Any = None) -> None:
        emps = list_employees()
        if not emps:
            _notify("Aucun employé en base.", WARNING); return
        _notify(f"Génération {len(emps)} feuilles individuelles Excel…", MUTED); _busy(True)
        ok = fail = 0
        for emp in emps:
            emp = dict(emp)
            eid = emp.get("id_employe")
            try:
                export_monthly_10h_timesheet_xlsx(_month_str(), ts_type=ds["ts_type"], employee_id=int(eid))
                ok += 1
            except Exception:
                fail += 1
        _notify(f"Feuilles individuelles Excel : {ok} OK, {fail} erreur(s)",
                SUCCESS if fail == 0 else WARNING)
        _rebuild_files()

    def export_all_employees_pdf(_: Any = None) -> None:
        emps = list_employees()
        if not emps:
            _notify("Aucun employé en base.", WARNING); return
        _notify(f"Génération {len(emps)} feuilles individuelles PDF…", MUTED); _busy(True)
        ok = fail = 0
        for emp in emps:
            emp = dict(emp)
            eid = emp.get("id_employe")
            try:
                export_monthly_10h_timesheet_pdf(_month_str(), ts_type=ds["ts_type"], employee_id=int(eid))
                ok += 1
            except Exception:
                fail += 1
        _notify(f"Feuilles individuelles PDF : {ok} OK, {fail} erreur(s)",
                SUCCESS if fail == 0 else WARNING)
        _rebuild_files()

    def batch_download(_: Any = None) -> None:
        _notify("Génération lot : 6 mois × 2 périodes × 2 formats…", MUTED); _busy(True)
        months: list[str] = []
        d = date.today().replace(day=1)
        for _ in range(6):
            months.append(d.strftime("%Y-%m"))
            d = (d - timedelta(days=1)).replace(day=1)
        ok = fail = 0
        for m in months:
            for tp in ("1_25", "21_20"):
                for fmt in ("xlsx", "pdf"):
                    try:
                        if fmt == "xlsx":
                            export_monthly_10h_timesheet_xlsx(m, ts_type=tp)
                        else:
                            export_monthly_10h_timesheet_pdf(m, ts_type=tp)
                        ok += 1
                    except Exception:
                        fail += 1
        _notify(f"Lot terminé : {ok} fichiers générés, {fail} erreur(s)",
                SUCCESS if fail == 0 else WARNING)
        _rebuild_files()

    # ── File list ─────────────────────────────────────────────────────────────
    def _list_ts_files() -> list[Path]:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        files = [p for p in EXPORTS_DIR.iterdir()
                 if p.is_file() and p.stem.startswith("timesheet_")]
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:50]

    def _file_row(path: Path) -> ft.Control:
        exists = path.exists()
        sz  = (path.stat().st_size // 1024) if exists else 0
        ext = path.suffix.lower().lstrip(".")
        c_fmt = SUCCESS if ext == "xlsx" else DANGER
        ico_fmt = (ft.Icons.TABLE_VIEW_ROUNDED if ext == "xlsx"
                   else ft.Icons.PICTURE_AS_PDF_ROUNDED)

        def do_open(_: Any) -> None:
            if exists: _open(path)
            else: _notify("Fichier introuvable.", WARNING)

        def do_delete(_: Any) -> None:
            try:
                if path.exists(): path.unlink()
                _notify(f"Supprimé : {path.name}", MUTED)
                _rebuild_files()
            except Exception as exc:
                _notify(f"Erreur suppression : {exc}", DANGER)

        return ft.Container(
            bgcolor=CARD,
            border=ft.border.all(1, DARK_BRD if exists else f"#30{DANGER[1:]}"),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row([
                ft.Container(
                    width=32, height=32, border_radius=8,
                    bgcolor=f"#15{c_fmt[1:]}",
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ico_fmt, color=c_fmt, size=16),
                ),
                ft.Column([
                    ft.Text(
                        path.name, size=12, weight=ft.FontWeight.W_600,
                        color=DARK_TEXT if exists else DARK_MUTED,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        f"{sz} Ko  ·  {path.parent.name}",
                        size=10, color=DARK_MUTED,
                    ),
                ], spacing=2, expand=True, tight=True),
                ft.Container(
                    bgcolor=f"#12{c_fmt[1:]}" if exists else f"#12{DANGER[1:]}",
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    content=ft.Text(
                        "Disponible" if exists else "Manquant",
                        size=10,
                        color=c_fmt if exists else DANGER,
                        weight=ft.FontWeight.W_600,
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                    icon_color=PRIMARY if exists else DARK_MUTED,
                    icon_size=18,
                    tooltip="Ouvrir",
                    on_click=do_open,
                    disabled=not exists,
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_color=DANGER, icon_size=18,
                    tooltip="Supprimer",
                    on_click=do_delete,
                ),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _rebuild_files() -> None:
        ts_files = _list_ts_files()
        files_col.controls = (
            [_file_row(p) for p in ts_files]
            if ts_files else [
                ft.Container(
                    bgcolor=CARD,
                    border=ft.border.all(1, DARK_BRD),
                    border_radius=12,
                    padding=ft.padding.symmetric(vertical=32),
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX_OUTLINED, color=DARK_MUTED, size=44),
                        ft.Text("Aucun fichier généré", size=14, color=DARK_MUTED,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("Utilisez les boutons ci-dessus pour générer des exports.",
                                size=11, color=DARK_MUTED, text_align=ft.TextAlign.CENTER),
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                )
            ]
        )
        try: files_col.update()
        except Exception: pass

    period_info_lbl = ft.Text("", size=11, color=PRIMARY)

    def _rebuild() -> None:
        month_lbl.value = f"{MONTHS_FR[ds['month']-1]} {ds['year']}"
        period_row.controls = [
            _period_btn("1_25", "Période  01 – 25"),
            _period_btn("21_20", "Période  21 – 20"),
        ]
        period_info_lbl.value = _period_label()
        status_txt.value = ""
        _rebuild_files()
        try:
            month_lbl.update(); period_row.update()
            period_info_lbl.update(); status_txt.update()
        except Exception:
            pass

    _rebuild()

    # ── Download action buttons ────────────────────────────────────────────────
    def _dl_btn(label: str, sub: str, icon: str, color: str, cb: Any) -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor=f"#10{color[1:]}",
            border=ft.border.all(1, f"#30{color[1:]}"),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            ink=True, on_click=lambda e: cb(),
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=color, size=22),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_700, color=color),
                ], spacing=8, tight=True),
                ft.Text(sub, size=10, color=DARK_MUTED),
            ], spacing=4, tight=True),
        )

    panel = ft.Container(
        bgcolor="#071321",
        expand=True,
        padding=ft.padding.all(20),
        content=ft.Column(
            controls=[
                # ── Header ───────────────────────────────────────────────────
                ft.Container(
                    bgcolor=CARD,
                    border=ft.border.all(1, DARK_BRD),
                    border_radius=14,
                    padding=ft.padding.all(16),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                width=44, height=44,
                                bgcolor=f"#15{PRIMARY[1:]}",
                                border_radius=12,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(ft.Icons.DOWNLOAD_ROUNDED,
                                               color=PRIMARY, size=24),
                            ),
                            ft.Column([
                                ft.Text("Centre de téléchargements",
                                        size=16, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                                ft.Text("Générez et téléchargez les timesheets Excel & PDF — les deux périodes",
                                        size=11, color=DARK_MUTED),
                            ], spacing=3, expand=True, tight=True),
                            spinner,
                        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Container(height=12),
                        # Month nav
                        month_nav,
                        ft.Container(height=8),
                        # Period toggle
                        period_row,
                        ft.Container(height=4),
                        ft.Row([
                            ft.Icon(ft.Icons.DATE_RANGE_OUTLINED, color=PRIMARY, size=13),
                            period_info_lbl,
                        ], spacing=6, tight=True),
                    ], spacing=0, tight=True),
                ),
                # ── Download buttons ─────────────────────────────────────────
                ft.Container(
                    bgcolor=CARD,
                    border=ft.border.all(1, DARK_BRD),
                    border_radius=14,
                    padding=ft.padding.all(16),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE_ROUNDED,
                                    color=DARK_MUTED, size=14),
                            ft.Text("Télécharger — mois & période sélectionnés",
                                    size=12, weight=ft.FontWeight.W_700, color=DARK_TEXT),
                        ], spacing=6),
                        ft.Container(height=8),
                        ft.Row([
                            _dl_btn("Excel complet", "Tableau 10H officiel",
                                    ft.Icons.TABLE_VIEW_ROUNDED, SUCCESS, export_xlsx),
                            _dl_btn("PDF complet", "Version imprimable",
                                    ft.Icons.PICTURE_AS_PDF_ROUNDED, DANGER, export_pdf),
                        ], spacing=10),
                        ft.Container(height=8),
                        ft.Row([
                            _dl_btn("Excel — par employé", "Une feuille par agent",
                                    ft.Icons.PERSON_OUTLINED, PRIMARY, export_all_employees_xlsx),
                            _dl_btn("PDF — par employé", "PDF individuel par agent",
                                    ft.Icons.PERSON_OUTLINED, "#7C3AED", export_all_employees_pdf),
                        ], spacing=10),
                        ft.Container(height=8),
                        # Batch button
                        ft.Container(
                            bgcolor=f"#0A{WARNING[1:]}",
                            border=ft.border.all(1, f"#25{WARNING[1:]}"),
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=14, vertical=12),
                            ink=True, on_click=lambda e: batch_download(),
                            content=ft.Row([
                                ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED,
                                        color=WARNING, size=22),
                                ft.Column([
                                    ft.Text("Télécharger tout — 6 mois × 2 périodes",
                                            size=13, weight=ft.FontWeight.W_700, color=WARNING),
                                    ft.Text("Génère XLSX + PDF pour les 6 derniers mois",
                                            size=10, color=DARK_MUTED),
                                ], spacing=4, expand=True, tight=True),
                            ], spacing=10),
                        ),
                        ft.Container(height=8),
                        status_txt,
                    ], spacing=0, tight=True),
                ),
                # ── Files list ───────────────────────────────────────────────
                ft.Container(
                    bgcolor=CARD,
                    border=ft.border.all(1, DARK_BRD),
                    border_radius=14,
                    padding=ft.padding.all(16),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED,
                                    color=PRIMARY, size=16),
                            ft.Text("Fichiers générés",
                                    size=13, weight=ft.FontWeight.W_700, color=DARK_TEXT,
                                    expand=True),
                            ft.TextButton(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.REFRESH_ROUNDED,
                                            color=DARK_MUTED, size=15),
                                    ft.Text("Actualiser", size=11, color=DARK_MUTED),
                                ], spacing=4, tight=True),
                                on_click=lambda e: _rebuild_files(),
                            ),
                            ft.TextButton(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED,
                                            color=PRIMARY, size=15),
                                    ft.Text("Ouvrir dossier", size=11, color=PRIMARY),
                                ], spacing=4, tight=True),
                                on_click=lambda e: _open_exports_dir(),
                            ),
                        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Container(height=8),
                        files_col,
                    ], spacing=0, tight=True),
                ),
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
    )

    def _open_exports_dir() -> None:
        try:
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(EXPORTS_DIR))
        except Exception as exc:
            _notify(f"Impossible d'ouvrir le dossier : {exc}", DANGER)

    return panel


def _tab_style(selected: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color=DARK_TEXT if selected else DARK_MUTED,
        bgcolor=PRIMARY if selected else BG,
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )
