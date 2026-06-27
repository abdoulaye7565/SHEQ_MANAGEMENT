from __future__ import annotations

from typing import Any

import flet as ft

from app.services.permit_service import (
    create_permit,
    update_permit,
    delete_permit,
    get_permit,
    list_permits,
    get_permit_summary,
    list_validations,
    validate_permit,
    set_permit_status,
    get_expiring_permits,
    PERMIT_TYPES,
    STATUTS,
    VALIDATION_ROLES,
)
from app.ui.components.module_header import module_header
from app.ui.components.pagination import PAGE_SIZE, pagination_row
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING

# ── Dark palette ──────────────────────────────────────────────────────────────
_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"

# ── Type badge colours ────────────────────────────────────────────────────────
_TYPE_COLORS: dict[str, str] = {
    "hauteur":        WARNING,
    "feu":            DANGER,
    "espace_confine": "#7C3AED",
    "electrique":     "#F97316",
    "levage":         PRIMARY,
    "excavation":     "#8B5CF6",
    "general":        SUCCESS,
}

# ── Status overlay colours ────────────────────────────────────────────────────
_STAT_OV: dict[str, str] = {
    "#64748B": "#1A1F2B",
    "#F59E0B": "#2D1F00",
    "#3B82F6": "#0F2D5E",
    "#10B981": "#052E16",
    "#F97316": "#2D1600",
    "#94A3B8": "#1A1F2B",
}

_TYPE_OV: dict[str, str] = {
    WARNING:   "#2D1F00",
    DANGER:    "#3B0F0F",
    "#7C3AED": "#1A0A3B",
    "#F97316": "#2D1600",
    PRIMARY:   "#0F2D5E",
    "#8B5CF6": "#1A0A3B",
    SUCCESS:   "#052E16",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _statut_badge(statut: str) -> ft.Control:
    label, color = STATUTS.get(statut, (statut, "#64748B"))
    ov = _STAT_OV.get(color, "#0A1929")
    return ft.Container(
        bgcolor=ov,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(label, color=color, size=10, weight=ft.FontWeight.BOLD),
    )


def _type_badge(type_permis: str) -> ft.Control:
    label = PERMIT_TYPES.get(type_permis, type_permis.upper())
    color = _TYPE_COLORS.get(type_permis, _DK_MUTED)
    ov = _TYPE_OV.get(color, "#0A1929")
    return ft.Container(
        bgcolor=ov,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(label, color=color, size=10, weight=ft.FontWeight.BOLD),
    )


def _empty_state(icon: str, title: str, subtitle: str = "") -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=24, vertical=40),
        content=ft.Column(
            controls=[
                ft.Container(
                    width=64,
                    height=64,
                    bgcolor=_DK_HEAD,
                    border_radius=32,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color=_DK_MUTED, size=28),
                ),
                ft.Text(title, color=_DK_TEXT, size=15, weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(subtitle, color=_DK_MUTED, size=12, text_align=ft.TextAlign.CENTER)
                if subtitle else ft.Container(height=0),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
    )


def _panel_dk(title: str, icon: str, accent: str, body: ft.Control) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            controls=[
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=3, height=14, bgcolor=accent, border_radius=2),
                            ft.Icon(icon, color=accent, size=16),
                            ft.Text(title, color=_DK_TEXT, size=14, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=14),
                    content=body,
                ),
            ],
            spacing=0,
        ),
    )


def _tf(label: str, value: str = "", multiline: bool = False, hint: str = "",
         width: int | None = None) -> ft.TextField:
    kwargs: dict[str, Any] = dict(
        label=label,
        value=value,
        border_color=_DK_BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=_DK_MUTED),
        text_style=ft.TextStyle(color=_DK_TEXT),
        bgcolor=_DK_CARD2,
        color=_DK_TEXT,
    )
    if multiline:
        kwargs["multiline"] = True
        kwargs["max_lines"] = 4
        kwargs["min_lines"] = 2
    if hint:
        kwargs["hint_text"] = hint
        kwargs["hint_style"] = ft.TextStyle(color=_DK_MUTED)
    if width is not None:
        kwargs["width"] = width
    return ft.TextField(**kwargs)


def _dd(label: str, value: str, options: list[ft.dropdown.Option],
        width: int | None = None) -> ft.Dropdown:
    kwargs: dict[str, Any] = dict(
        label=label,
        value=value,
        options=options,
        fill_color=_DK_CARD2,
        border_color=_DK_BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=_DK_MUTED),
        text_style=ft.TextStyle(color=_DK_TEXT),
    )
    if width is not None:
        kwargs["width"] = width
    return ft.Dropdown(fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F", focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"), text_style=ft.TextStyle(color="#E2E8F0"), **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Main page
# ─────────────────────────────────────────────────────────────────────────────

def permits_page(page: Any = None) -> ft.Control:  # noqa: C901
    state: dict[str, Any] = {
        "tab":         "dashboard",
        "editing_id":  None,
        "filter_type": "tous",
        "filter_stat": "tous",
        "page":        0,
    }

    content_area = ft.Container()
    tab_buttons: dict[str, ft.ElevatedButton] = {}

    _TABS = [
        ("dashboard", "Tableau de bord",  ft.Icons.DASHBOARD_OUTLINED),
        ("registre",  "Registre",          ft.Icons.TABLE_ROWS_OUTLINED),
        ("formulaire","Formulaire",         ft.Icons.EDIT_NOTE_OUTLINED),
    ]

    # ── Tab switching ─────────────────────────────────────────────────────────

    def _switch_tab(tab_key: str) -> None:
        state["tab"] = tab_key
        _refresh_tab_styles()
        _render_content()

    def _refresh_tab_styles() -> None:
        for key, btn in tab_buttons.items():
            if key == state["tab"]:
                btn.style = ft.ButtonStyle(
                    bgcolor={ft.ControlState.DEFAULT: PRIMARY},
                    color={ft.ControlState.DEFAULT: "#FFFFFF"},
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                )
            else:
                btn.style = ft.ButtonStyle(
                    bgcolor={ft.ControlState.DEFAULT: _DK_CARD},
                    color={ft.ControlState.DEFAULT: _DK_MUTED},
                    shape=ft.RoundedRectangleBorder(radius=8),
                    side=ft.BorderSide(1, _DK_BORDER),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                )
            try:
                btn.update()
            except RuntimeError:
                pass

    def _render_content() -> None:
        try:
            if state["tab"] == "dashboard":
                controls = _render_dashboard()
            elif state["tab"] == "registre":
                controls = _render_registre()
            elif state["tab"] == "formulaire":
                controls = _render_formulaire()
            else:
                controls = []
            content_area.content = ft.Column(controls=controls, spacing=14, tight=True)
        except Exception as exc:
            content_area.content = ft.Container(
                bgcolor=_DK_CARD,
                border=ft.border.all(1, DANGER),
                border_radius=10,
                padding=16,
                content=ft.Text(f"Erreur de rendu: {exc}", color=DANGER, size=12),
            )
        try:
            content_area.update()
        except RuntimeError:
            pass

    # ── TAB 1: Tableau de bord ────────────────────────────────────────────────

    def _render_dashboard() -> list[ft.Control]:
        try:
            summary = get_permit_summary()
        except Exception:
            summary = {"total": 0, "actifs": 0, "en_attente": 0, "brouillons": 0, "suspendus": 0, "clos": 0}

        kpi_defs = [
            ("Total permis",    summary.get("total", 0),      PRIMARY,   ft.Icons.ASSIGNMENT_OUTLINED),
            ("Actifs",          summary.get("actifs", 0),      "#10B981", ft.Icons.CHECK_CIRCLE_OUTLINED),
            ("En validation",   summary.get("en_attente", 0),  "#F59E0B", ft.Icons.PENDING_OUTLINED),
            ("Brouillons",      summary.get("brouillons", 0),  "#64748B", ft.Icons.DRAFTS_OUTLINED),
            ("Suspendus",       summary.get("suspendus", 0),   "#F97316", ft.Icons.PAUSE_CIRCLE_OUTLINED),
        ]

        kpi_cards = []
        for label, value, color, icon in kpi_defs:
            ov = _STAT_OV.get(color, _TYPE_OV.get(color, "#0A1929"))
            kpi_cards.append(
                ft.Container(
                    col={"xs": 12, "sm": 6, "md": 4, "lg": 2},
                    content=ft.Container(
                        bgcolor=_DK_CARD,
                        border=ft.border.only(
                            left=ft.BorderSide(4, color),
                            top=ft.BorderSide(1, _DK_BORDER),
                            right=ft.BorderSide(1, _DK_BORDER),
                            bottom=ft.BorderSide(1, _DK_BORDER),
                        ),
                        border_radius=12,
                        padding=ft.padding.only(left=14, right=14, top=12, bottom=12),
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            width=32, height=32,
                                            bgcolor=ov,
                                            border_radius=8,
                                            alignment=ft.Alignment(0, 0),
                                            content=ft.Icon(icon, color=color, size=16),
                                        ),
                                        ft.Text(label, color=_DK_MUTED, size=10,
                                                weight=ft.FontWeight.W_500, expand=True, max_lines=2),
                                    ],
                                    spacing=7,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                            ],
                            spacing=4,
                        ),
                    ),
                )
            )

        kpi_row = ft.ResponsiveRow(controls=kpi_cards, spacing=12, run_spacing=12)

        # ── Permis expirant dans 48h ──────────────────────────────────────────
        try:
            expiring = get_expiring_permits(2)
        except Exception:
            expiring = []

        expiring_panel: ft.Control | None = None
        if expiring:
            exp_rows: list[ft.Control] = []
            for p in expiring:
                exp_rows.append(
                    ft.Container(
                        bgcolor=_DK_CARD2,
                        border=ft.border.all(1, DANGER),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.ALARM_OUTLINED, color=DANGER, size=16),
                                ft.Text(
                                    str(p.get("numero") or ""),
                                    color=DANGER,
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    width=120,
                                ),
                                ft.Text(
                                    str(p.get("titre") or ""),
                                    color=_DK_TEXT,
                                    size=12,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                _type_badge(str(p.get("type_permis") or "general")),
                                ft.Text(
                                    f"Fin: {str(p.get('date_fin') or '')}",
                                    color=DANGER,
                                    size=11,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            expiring_panel = _panel_dk(
                f"Permis expirant dans 48h ({len(expiring)})",
                ft.Icons.ALARM_OUTLINED,
                DANGER,
                ft.Column(controls=exp_rows, spacing=6, tight=True),
            )

        # ── 5 permis récents ──────────────────────────────────────────────────
        try:
            recent = list_permits()[:5]
        except Exception:
            recent = []

        if recent:
            rec_rows: list[ft.Control] = []
            for p in recent:
                rec_rows.append(
                    ft.Container(
                        bgcolor=_DK_CARD2,
                        border=ft.border.all(1, _DK_BORDER),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    str(p.get("numero") or ""),
                                    color=PRIMARY,
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    width=130,
                                ),
                                ft.Text(
                                    str(p.get("titre") or ""),
                                    color=_DK_TEXT,
                                    size=12,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                _type_badge(str(p.get("type_permis") or "general")),
                                _statut_badge(str(p.get("statut") or "brouillon")),
                                ft.Text(
                                    str(p.get("date_debut") or ""),
                                    color=_DK_MUTED,
                                    size=11,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            recent_body: ft.Control = ft.Column(controls=rec_rows, spacing=6, tight=True)
        else:
            recent_body = ft.Text("Aucun permis enregistré.", color=_DK_MUTED, size=12)

        recent_panel = _panel_dk(
            "Permis récents",
            ft.Icons.ASSIGNMENT_OUTLINED,
            PRIMARY,
            recent_body,
        )

        controls: list[ft.Control] = [kpi_row]
        if expiring_panel is not None:
            controls.append(expiring_panel)
        controls.append(recent_panel)
        return controls

    # ── TAB 2: Registre ───────────────────────────────────────────────────────

    def _render_registre() -> list[ft.Control]:
        type_options = [ft.dropdown.Option("tous", "Tous les types")]
        for k, v in PERMIT_TYPES.items():
            type_options.append(ft.dropdown.Option(k, v))

        stat_options = [ft.dropdown.Option("tous", "Tous les statuts")]
        for k, (label, _) in STATUTS.items():
            stat_options.append(ft.dropdown.Option(k, label))

        dd_type = _dd("Type", state["filter_type"], type_options, width=180)
        dd_stat = _dd("Statut", state["filter_stat"], stat_options, width=160)

        table_area = ft.Column(spacing=8, tight=True)

        def _load_table() -> None:
            try:
                permits = list_permits(
                    type_permis=state["filter_type"] if state["filter_type"] != "tous" else None,
                    statut=state["filter_stat"] if state["filter_stat"] != "tous" else None,
                )
            except Exception:
                permits = []

            if not permits:
                table_area.controls = [
                    _empty_state(
                        ft.Icons.ASSIGNMENT_OUTLINED,
                        "Aucun permis trouvé",
                        "Modifiez les filtres ou créez un nouveau permis.",
                    )
                ]
                try:
                    table_area.update()
                except RuntimeError:
                    pass
                return

            total = len(permits)
            max_page = max(0, (total - 1) // PAGE_SIZE)
            state["page"] = max(0, min(max_page, state["page"]))
            start = state["page"] * PAGE_SIZE
            page_permits = permits[start : start + PAGE_SIZE]

            cols = [
                ft.DataColumn(ft.Text("N°", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Type", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Titre", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Lieu", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Date début", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Date fin", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Statut", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Actions", color=PRIMARY, size=12, weight=ft.FontWeight.BOLD)),
            ]

            rows: list[ft.DataRow] = []
            for p in page_permits:
                pid = p.get("id")
                statut = str(p.get("statut") or "brouillon")

                def _edit(r: dict[str, Any] = p) -> None:
                    state["editing_id"] = r.get("id")
                    _switch_tab("formulaire")

                def _del(r: dict[str, Any] = p) -> None:
                    try:
                        delete_permit(int(r["id"]))
                    except Exception:
                        pass
                    _load_table()

                def _activer(r: dict[str, Any] = p) -> None:
                    try:
                        set_permit_status(int(r["id"]), "actif")
                    except Exception:
                        pass
                    _load_table()

                def _cloturer(r: dict[str, Any] = p) -> None:
                    try:
                        set_permit_status(int(r["id"]), "clos")
                    except Exception:
                        pass
                    _load_table()

                can_activate = statut == "valide"
                can_close = statut in ("actif", "valide", "suspendu", "en_validation")

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(p.get("numero") or ""), color=PRIMARY, size=11,
                                                weight=ft.FontWeight.BOLD)),
                            ft.DataCell(_type_badge(str(p.get("type_permis") or "general"))),
                            ft.DataCell(
                                ft.Text(str(p.get("titre") or ""), color=_DK_TEXT, size=12,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                            ),
                            ft.DataCell(
                                ft.Text(str(p.get("lieu") or "—"), color=_DK_MUTED, size=11)
                            ),
                            ft.DataCell(
                                ft.Text(str(p.get("date_debut") or ""), color=_DK_MUTED, size=11)
                            ),
                            ft.DataCell(
                                ft.Text(str(p.get("date_fin") or ""), color=_DK_MUTED, size=11)
                            ),
                            ft.DataCell(_statut_badge(statut)),
                            ft.DataCell(
                                ft.Row(
                                    controls=[
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT_OUTLINED,
                                            icon_color=PRIMARY,
                                            icon_size=16,
                                            tooltip="Modifier",
                                            on_click=lambda e, r=p: _edit(r),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                                            icon_color="#10B981",
                                            icon_size=16,
                                            tooltip="Activer",
                                            on_click=lambda e, r=p: _activer(r),
                                            visible=can_activate,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.LOCK_OUTLINED,
                                            icon_color=_DK_MUTED,
                                            icon_size=16,
                                            tooltip="Clôturer",
                                            on_click=lambda e, r=p: _cloturer(r),
                                            visible=can_close,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            icon_color=DANGER,
                                            icon_size=16,
                                            tooltip="Supprimer",
                                            on_click=lambda e, r=p: _del(r),
                                        ),
                                    ],
                                    spacing=0,
                                )
                            ),
                        ]
                    )
                )

            table = ft.DataTable(
                columns=cols,
                rows=rows,
                heading_row_color={ft.ControlState.DEFAULT: _DK_HEAD},
                data_row_color={ft.ControlState.DEFAULT: _DK_CARD},
                border=ft.border.all(1, _DK_BORDER),
                border_radius=10,
                column_spacing=16,
                data_row_min_height=44,
            )

            table_area.controls = [
                ft.Container(
                    bgcolor=_DK_CARD,
                    border_radius=10,
                    content=ft.Row(
                        controls=[table],
                        scroll=ft.ScrollMode.AUTO,
                        tight=True,
                    ),
                ),
                pagination_row(
                    current_page=state["page"],
                    max_page=max_page,
                    total=total,
                    shown_start=start + 1 if page_permits else 0,
                    shown_end=start + len(page_permits),
                    item_label="permis",
                    on_prev=lambda: (state.__setitem__("page", state["page"] - 1), _load_table()),
                    on_next=lambda: (state.__setitem__("page", state["page"] + 1), _load_table()),
                    on_page=lambda p: (state.__setitem__("page", p), _load_table()),
                ),
            ]
            try:
                table_area.update()
            except RuntimeError:
                pass

        def _apply_filters(e: Any = None) -> None:
            state["filter_type"] = dd_type.value or "tous"
            state["filter_stat"] = dd_stat.value or "tous"
            state["page"] = 0
            _load_table()

        def _reset_filters(e: Any = None) -> None:
            state["filter_type"] = "tous"
            state["filter_stat"] = "tous"
            state["page"] = 0
            dd_type.value = "tous"
            dd_stat.value = "tous"
            for dd in (dd_type, dd_stat):
                try:
                    dd.update()
                except RuntimeError:
                    pass
            _load_table()

        def _new_permit(e: Any = None) -> None:
            state["editing_id"] = None
            _switch_tab("formulaire")

        filter_bar = ft.Container(
            bgcolor=_DK_CARD2,
            border=ft.border.all(1, _DK_BORDER),
            border_radius=10,
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            dd_type,
                            dd_stat,
                            ft.ElevatedButton(
                                "Filtrer",
                                icon=ft.Icons.FILTER_LIST,
                                bgcolor=PRIMARY,
                                color="#FFFFFF",
                                on_click=_apply_filters,
                            ),
                            ft.OutlinedButton(
                                "Réinitialiser",
                                icon=ft.Icons.REFRESH,
                                style=ft.ButtonStyle(
                                    color={ft.ControlState.DEFAULT: _DK_MUTED},
                                    side=ft.BorderSide(1, _DK_BORDER),
                                ),
                                on_click=_reset_filters,
                            ),
                            ft.ElevatedButton(
                                "+ Nouveau permis",
                                icon=ft.Icons.ADD,
                                bgcolor=SUCCESS,
                                color="#FFFFFF",
                                on_click=_new_permit,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
        )

        _load_table()
        return [filter_bar, table_area]

    # ── TAB 3: Formulaire ─────────────────────────────────────────────────────

    def _render_formulaire() -> list[ft.Control]:  # noqa: C901
        editing_id = state.get("editing_id")
        existing: dict[str, Any] = {}
        if editing_id is not None:
            try:
                existing = get_permit(int(editing_id)) or {}
            except Exception:
                existing = {}

        today_iso = __import__("datetime").date.today().isoformat()

        # ── Fields ────────────────────────────────────────────────────────────
        dd_type = _dd(
            "Type de permis *",
            str(existing.get("type_permis") or "general"),
            [ft.dropdown.Option(k, v) for k, v in PERMIT_TYPES.items()],
            width=220,
        )
        tf_titre = _tf("Titre *", str(existing.get("titre") or ""))
        tf_lieu = _tf("Lieu", str(existing.get("lieu") or ""), width=200)
        tf_zone = _tf("Zone", str(existing.get("zone") or ""), width=180)
        tf_date_emission = _tf("Date émission *", str(existing.get("date_emission") or today_iso),
                                hint="YYYY-MM-DD", width=150)
        tf_date_debut = _tf("Date début *", str(existing.get("date_debut") or today_iso),
                             hint="YYYY-MM-DD", width=150)
        tf_date_fin = _tf("Date fin *", str(existing.get("date_fin") or today_iso),
                           hint="YYYY-MM-DD", width=150)
        tf_heure_debut = _tf("Heure début", str(existing.get("heure_debut") or ""),
                              hint="HH:MM", width=120)
        tf_heure_fin = _tf("Heure fin", str(existing.get("heure_fin") or ""),
                            hint="HH:MM", width=120)
        tf_effectif = _tf("Effectif", str(existing.get("effectif") or "1"), width=100)
        tf_entreprise = _tf("Entreprise", str(existing.get("entreprise") or ""), width=220)
        tf_responsable = _tf("Responsable travaux", str(existing.get("responsable_travaux") or ""))
        tf_description = _tf("Description des travaux", str(existing.get("description_travaux") or ""),
                              multiline=True)
        tf_risques = _tf("Risques identifiés", str(existing.get("risques") or ""), multiline=True)
        tf_precautions = _tf("Précautions / Mesures", str(existing.get("precautions") or ""),
                              multiline=True)
        tf_equipements = _tf("Équipements requis", str(existing.get("equipements_requis") or ""),
                              multiline=True)

        dd_statut = _dd(
            "Statut",
            str(existing.get("statut") or "brouillon"),
            [ft.dropdown.Option(k, v) for k, (v, _) in STATUTS.items()],
            width=180,
        )

        feedback = ft.Text("", color=SUCCESS, size=12)

        def _save(e: Any = None) -> None:
            if not tf_titre.value or not tf_titre.value.strip():
                feedback.value = "Le titre est obligatoire."
                feedback.color = DANGER
                try:
                    feedback.update()
                except RuntimeError:
                    pass
                return
            data = {
                "type_permis":         dd_type.value or "general",
                "titre":               tf_titre.value.strip(),
                "lieu":                tf_lieu.value,
                "zone":                tf_zone.value,
                "date_emission":       tf_date_emission.value or today_iso,
                "date_debut":          tf_date_debut.value or today_iso,
                "date_fin":            tf_date_fin.value or today_iso,
                "heure_debut":         tf_heure_debut.value,
                "heure_fin":           tf_heure_fin.value,
                "effectif":            tf_effectif.value or "1",
                "entreprise":          tf_entreprise.value,
                "responsable_travaux": tf_responsable.value,
                "description_travaux": tf_description.value,
                "risques":             tf_risques.value,
                "precautions":         tf_precautions.value,
                "equipements_requis":  tf_equipements.value,
                "statut":              dd_statut.value or "brouillon",
            }
            try:
                if editing_id is not None:
                    update_permit(int(editing_id), data)
                    msg = "Permis mis à jour."
                else:
                    create_permit(data)
                    msg = "Permis créé avec succès."
                feedback.value = msg
                feedback.color = SUCCESS
                try:
                    feedback.update()
                except RuntimeError:
                    pass
                if page:
                    try:
                        page.show_dialog(ft.SnackBar(
                            content=ft.Text(msg, color="#FFFFFF"),
                            bgcolor=SUCCESS,
                        ))
                    except RuntimeError:
                        pass
                state["editing_id"] = None
                _switch_tab("registre")
            except Exception as exc:
                feedback.value = f"Erreur: {exc}"
                feedback.color = DANGER
                try:
                    feedback.update()
                except RuntimeError:
                    pass

        def _cancel(e: Any = None) -> None:
            state["editing_id"] = None
            _switch_tab("registre")

        # ── Layout ────────────────────────────────────────────────────────────
        left_col = ft.Column(
            controls=[
                dd_type,
                tf_titre,
                ft.Row(controls=[tf_lieu, tf_zone], spacing=10, wrap=True),
                ft.Row(controls=[tf_date_emission, tf_date_debut, tf_date_fin], spacing=10, wrap=True),
                ft.Row(controls=[tf_heure_debut, tf_heure_fin, tf_effectif], spacing=10, wrap=True),
                tf_entreprise,
                tf_responsable,
            ],
            spacing=12,
            expand=True,
        )

        right_col = ft.Column(
            controls=[
                tf_description,
                tf_risques,
                tf_precautions,
                tf_equipements,
            ],
            spacing=12,
            expand=True,
        )

        form_row = ft.Row(
            controls=[
                left_col,
                ft.VerticalDivider(color=_DK_BORDER, width=1),
                right_col,
            ],
            spacing=20,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        action_row = ft.Row(
            controls=[
                dd_statut,
                ft.ElevatedButton(
                    "Enregistrer",
                    icon=ft.Icons.SAVE_OUTLINED,
                    bgcolor=PRIMARY,
                    color="#FFFFFF",
                    on_click=_save,
                ),
                ft.OutlinedButton(
                    "Annuler",
                    icon=ft.Icons.CLOSE,
                    style=ft.ButtonStyle(
                        color={ft.ControlState.DEFAULT: _DK_MUTED},
                        side=ft.BorderSide(1, _DK_BORDER),
                    ),
                    on_click=_cancel,
                ),
                feedback,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        title_text = "Modifier le permis" if editing_id is not None else "Nouveau permis de travail"
        form_panel = _panel_dk(
            title_text,
            ft.Icons.EDIT_NOTE_OUTLINED,
            PRIMARY,
            ft.Column(
                controls=[form_row, ft.Divider(color=_DK_BORDER), action_row],
                spacing=16,
            ),
        )

        panels: list[ft.Control] = [form_panel]

        # ── Workflow de validation + boutons de statut (édition uniquement) ───
        if editing_id is not None:
            current_statut = str(existing.get("statut") or "brouillon")

            # Status action buttons
            status_btns: list[ft.Control] = []

            def _do_set_status(new_st: str) -> None:
                try:
                    set_permit_status(int(editing_id), new_st)
                    state["editing_id"] = int(editing_id)
                    _switch_tab("formulaire")
                except Exception as exc:
                    if page:
                        try:
                            page.show_dialog(ft.SnackBar(
                                content=ft.Text(f"Erreur: {exc}", color="#FFFFFF"),
                                bgcolor=DANGER,
                            ))
                        except RuntimeError:
                            pass

            if current_statut == "brouillon":
                status_btns.append(
                    ft.ElevatedButton(
                        "Soumettre pour validation",
                        icon=ft.Icons.SEND_OUTLINED,
                        bgcolor="#F59E0B",
                        color="#FFFFFF",
                        on_click=lambda e: _do_set_status("en_validation"),
                    )
                )
            if current_statut == "valide":
                status_btns.append(
                    ft.ElevatedButton(
                        "Activer le permis",
                        icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                        bgcolor="#10B981",
                        color="#FFFFFF",
                        on_click=lambda e: _do_set_status("actif"),
                    )
                )
            if current_statut == "actif":
                status_btns.append(
                    ft.ElevatedButton(
                        "Suspendre",
                        icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
                        bgcolor="#F97316",
                        color="#FFFFFF",
                        on_click=lambda e: _do_set_status("suspendu"),
                    )
                )
            if current_statut not in ("clos", "brouillon"):
                status_btns.append(
                    ft.ElevatedButton(
                        "Clôturer",
                        icon=ft.Icons.LOCK_OUTLINED,
                        bgcolor="#64748B",
                        color="#FFFFFF",
                        on_click=lambda e: _do_set_status("clos"),
                    )
                )

            if status_btns:
                status_panel = _panel_dk(
                    "Contrôle du statut",
                    ft.Icons.SETTINGS_OUTLINED,
                    WARNING,
                    ft.Row(controls=status_btns, spacing=10, wrap=True),
                )
                panels.append(status_panel)

            # ── Validations ───────────────────────────────────────────────────
            try:
                validations = list_validations(int(editing_id))
            except Exception:
                validations = []

            val_cards: list[ft.Control] = []
            for v in validations:
                vid = v.get("id")
                v_statut = str(v.get("statut") or "en_attente")
                v_role = str(v.get("role_validateur") or "")
                v_nom = str(v.get("nom_validateur") or "")
                v_date = str(v.get("date_validation") or "")
                v_comment = str(v.get("commentaire") or "")

                vcolor_map = {
                    "en_attente": _DK_MUTED,
                    "valide":     "#10B981",
                    "refuse":     DANGER,
                }
                v_color = vcolor_map.get(v_statut, _DK_MUTED)

                nom_field = ft.TextField(
                    label="Validateur *",
                    value=v_nom,
                    width=180,
                    border_color=_DK_BORDER,
                    focused_border_color=PRIMARY,
                    label_style=ft.TextStyle(color=_DK_MUTED),
                    text_style=ft.TextStyle(color=_DK_TEXT),
                    bgcolor=_DK_CARD2,
                )
                comment_field = ft.TextField(
                    label="Commentaire",
                    value=v_comment,
                    expand=True,
                    border_color=_DK_BORDER,
                    focused_border_color=PRIMARY,
                    label_style=ft.TextStyle(color=_DK_MUTED),
                    text_style=ft.TextStyle(color=_DK_TEXT),
                    bgcolor=_DK_CARD2,
                )

                def _do_validate(vid_: int = vid, nom_f: ft.TextField = nom_field,
                                  com_f: ft.TextField = comment_field, st: str = "valide") -> None:
                    try:
                        validate_permit(vid_, nom_f.value or "", st, com_f.value or "")
                        state["editing_id"] = int(editing_id)
                        _switch_tab("formulaire")
                    except Exception as exc:
                        if page:
                            try:
                                page.show_dialog(ft.SnackBar(
                                    content=ft.Text(f"Erreur: {exc}", color="#FFFFFF"),
                                    bgcolor=DANGER,
                                ))
                            except RuntimeError:
                                pass

                val_cards.append(
                    ft.Container(
                        bgcolor=_DK_CARD2,
                        border=ft.border.all(1, v_color),
                        border_radius=10,
                        padding=12,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(width=3, height=20, bgcolor=v_color, border_radius=2),
                                        ft.Text(v_role, color=_DK_TEXT, size=13,
                                                weight=ft.FontWeight.W_600, expand=True),
                                        ft.Container(
                                            bgcolor=_STAT_OV.get(v_color, "#0A1929"),
                                            border=ft.border.all(1, v_color),
                                            border_radius=8,
                                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                            content=ft.Text(
                                                v_statut.replace("_", " ").capitalize(),
                                                color=v_color,
                                                size=10,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ),
                                        ft.Text(v_date[:16] if v_date else "", color=_DK_MUTED, size=10),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    controls=[
                                        nom_field,
                                        comment_field,
                                    ],
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                ),
                                ft.Row(
                                    controls=[
                                        ft.ElevatedButton(
                                            "Valider",
                                            icon=ft.Icons.CHECK_CIRCLE_OUTLINED,
                                            bgcolor="#10B981",
                                            color="#FFFFFF",
                                            on_click=lambda e, vid_=vid, nf=nom_field, cf=comment_field:
                                                _do_validate(vid_, nf, cf, "valide"),
                                        ),
                                        ft.OutlinedButton(
                                            "Refuser",
                                            icon=ft.Icons.CANCEL_OUTLINED,
                                            style=ft.ButtonStyle(
                                                color={ft.ControlState.DEFAULT: DANGER},
                                                side=ft.BorderSide(1, DANGER),
                                            ),
                                            on_click=lambda e, vid_=vid, nf=nom_field, cf=comment_field:
                                                _do_validate(vid_, nf, cf, "refuse"),
                                        ),
                                    ],
                                    spacing=8,
                                ),
                            ],
                            spacing=10,
                            tight=True,
                        ),
                    )
                )

            if val_cards:
                val_panel = _panel_dk(
                    "Workflow de validation",
                    ft.Icons.VERIFIED_OUTLINED,
                    "#3B82F6",
                    ft.Column(controls=val_cards, spacing=10, tight=True),
                )
                panels.append(val_panel)

        return panels

    # ── Build tab bar ─────────────────────────────────────────────────────────
    tab_btn_controls: list[ft.Control] = []
    for key, label, icon in _TABS:
        btn = ft.ElevatedButton(
            label,
            icon=icon,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: _DK_CARD},
                color={ft.ControlState.DEFAULT: _DK_MUTED},
                shape=ft.RoundedRectangleBorder(radius=8),
                side=ft.BorderSide(1, _DK_BORDER),
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
            ),
            on_click=lambda e, k=key: _switch_tab(k),
        )
        tab_buttons[key] = btn
        tab_btn_controls.append(btn)

    tab_bar = ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            controls=tab_btn_controls,
            spacing=8,
            wrap=True,
        ),
    )

    root = ft.Column(
        controls=[
            module_header(
                "Permis de Travail",
                "Émission · Validation multi-niveaux · Archivage",
            ),
            tab_bar,
            content_area,
        ],
        spacing=14,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    _switch_tab("dashboard")
    return ft.Container(bgcolor="#071321", expand=True, content=root)
