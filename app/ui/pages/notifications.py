from __future__ import annotations
from typing import Any

import flet as ft

from app.services.notification_service import (
    list_notifications,
    acknowledge_notification,
    dismiss_notification,
    clear_handled,
    count_new_notifications,
    sync_module_alerts,
    PRIORITES,
    SOURCE_LABELS,
)

_BG     = "#071321"
_CARD   = "#0D2040"
_CARD2  = "#0A1929"
_HEAD   = "#112240"
_BORDER = "#1E3A5F"
_FIELD  = "#0C1C2E"
_TEXT   = "#E2E8F0"
_MUTED  = "#9DB0C5"
PRIMARY = "#3B82F6"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER  = "#EF4444"

_SOURCE_ICONS: dict[str, str] = {
    "risques":   ft.Icons.SHIELD_OUTLINED,
    "accidents": ft.Icons.PERSONAL_INJURY_OUTLINED,
    "permis":    ft.Icons.ASSIGNMENT_OUTLINED,
    "epi":       ft.Icons.HEALTH_AND_SAFETY_OUTLINED,
    "formation": ft.Icons.SCHOOL_OUTLINED,
    "general":   ft.Icons.NOTIFICATIONS_OUTLINED,
}


def notifications_page(page: Any = None) -> ft.Control:
    filter_state: dict[str, Any] = {"statut": "nouveau", "priorite": None, "source": None}
    notif_area = ft.Column(spacing=8, tight=True)
    badge_text = ft.Text("0", color="#FFFFFF", size=10, weight=ft.FontWeight.BOLD)
    badge_container = ft.Container(
        bgcolor=DANGER,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=7, vertical=2),
        content=badge_text,
        visible=False,
    )
    status_text = ft.Text("", color=_MUTED, size=11)

    filter_buttons: dict[str, ft.ElevatedButton] = {}

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def _notif_card(n: dict[str, Any]) -> ft.Control:
        prio  = str(n.get("priorite") or "info")
        src   = str(n.get("source") or "general")
        clr   = PRIORITES.get(prio, PRIMARY)
        icon  = _SOURCE_ICONS.get(src, ft.Icons.NOTIFICATIONS_OUTLINED)
        src_l = SOURCE_LABELS.get(src, src.title())
        nid   = int(n["id"])
        is_new = n.get("statut") == "nouveau"
        ack_txt = n.get("acknowledged_at")

        btns: list[ft.Control] = []
        if is_new:
            btns += [
                ft.ElevatedButton(
                    "Marquer traité",
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    bgcolor=SUCCESS, color="#FFFFFF",
                    on_click=lambda ev, i=nid: _ack(i),
                ),
                ft.OutlinedButton(
                    "Ignorer",
                    icon=ft.Icons.CLOSE,
                    style=ft.ButtonStyle(
                        color={ft.ControlState.DEFAULT: _MUTED},
                        side=ft.BorderSide(1, _BORDER),
                    ),
                    on_click=lambda ev, i=nid: _dismiss(i),
                ),
            ]
        else:
            status_label = "Traité" if n.get("statut") == "traite" else "Ignoré"
            by = n.get("acknowledged_by") or ""
            note = f"{status_label}{' par ' + by if by else ''}"
            if ack_txt:
                note += f" le {ack_txt[:10]}"
            btns.append(ft.Text(note, color=SUCCESS if status_label == "Traité" else _MUTED, size=9, italic=True))

        return ft.Container(
            bgcolor=_CARD2,
            border=ft.border.all(1, _BORDER),
            border_radius=8,
            padding=10,
            margin=ft.margin.only(bottom=2),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(width=4, height=40, bgcolor=clr, border_radius=2),
                            ft.Icon(icon, color=clr, size=20),
                            ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                bgcolor=clr, border_radius=4,
                                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                                content=ft.Text(prio.upper(), color="#FFFFFF", size=8, weight=ft.FontWeight.BOLD),
                                            ),
                                            ft.Container(
                                                bgcolor=_FIELD, border_radius=4,
                                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                                content=ft.Text(src_l, color=_MUTED, size=8),
                                            ),
                                            ft.Text(str(n.get("created_at", ""))[:16], color=_MUTED, size=8),
                                        ],
                                        spacing=5,
                                    ),
                                    ft.Text(
                                        str(n.get("titre") or "—"),
                                        color=_TEXT, size=11, weight=ft.FontWeight.W_600,
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        str(n.get("message") or ""),
                                        color=_MUTED, size=10,
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                                spacing=3,
                                tight=True,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Row(controls=btns, spacing=8) if btns else ft.Container(height=0),
                ],
                spacing=6,
                tight=True,
            ),
        )

    def _ack(notif_id: int) -> None:
        try:
            acknowledge_notification(notif_id)
            status_text.value = "Notification marquée comme traitée."
        except Exception as exc:
            status_text.value = f"Erreur : {exc}"
        refresh()

    def _dismiss(notif_id: int) -> None:
        try:
            dismiss_notification(notif_id)
        except Exception:
            pass
        refresh()

    def _set_filter(statut: str | None, priorite: str | None = None, source: str | None = None) -> None:
        filter_state["statut"] = statut
        filter_state["priorite"] = priorite
        filter_state["source"] = source
        _update_filter_btns()
        refresh()

    def _update_filter_btns() -> None:
        current = filter_state.get("statut")
        current_p = filter_state.get("priorite")
        for key, btn in filter_buttons.items():
            selected = (key == current) or (key == current_p)
            btn.style = ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: "#FFFFFF" if selected else _MUTED},
                bgcolor={ft.ControlState.DEFAULT: PRIMARY if selected else _FIELD},
                shape=ft.RoundedRectangleBorder(radius=6),
            )
        try:
            for btn in filter_buttons.values():
                btn.update()
        except RuntimeError:
            pass

    def do_sync(e: Any = None) -> None:
        try:
            n = sync_module_alerts()
            status_text.value = f"Synchronisation : {n} nouvelle(s) notification(s) ajoutée(s)."
        except Exception as exc:
            status_text.value = f"Erreur sync : {exc}"
        refresh()

    def do_clear(e: Any = None) -> None:
        try:
            n = clear_handled()
            status_text.value = f"{n} notification(s) traitée(s)/ignorée(s) supprimée(s)."
        except Exception as exc:
            status_text.value = f"Erreur : {exc}"
        refresh()

    source_dd = ft.Dropdown(
        label="Source",
        value="",
        width=200,
        bgcolor=_FIELD,
        color=_TEXT,
        border_color=_BORDER,
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=_MUTED),
        options=[ft.dropdown.Option("", "Toutes sources")] + [
            ft.dropdown.Option(k, v) for k, v in SOURCE_LABELS.items()
        ],
    )
    source_dd.on_change = lambda ev: _set_filter(
        filter_state.get("statut"),
        filter_state.get("priorite"),
        ev.control.value or None,
    )

    def refresh(e: Any = None) -> None:
        try:
            notifs = list_notifications(
                statut=filter_state.get("statut"),
                priorite=filter_state.get("priorite"),
                source=filter_state.get("source"),
            )
        except Exception:
            notifs = []

        new_count = 0
        try:
            new_count = count_new_notifications()
        except Exception:
            pass

        badge_text.value = str(new_count)
        badge_container.visible = new_count > 0

        if notifs:
            notif_area.controls = [_notif_card(n) for n in notifs]
        else:
            notif_area.controls = [
                ft.Container(
                    bgcolor="#052E16",
                    border=ft.border.all(1, SUCCESS),
                    border_radius=8,
                    padding=16,
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=24),
                            ft.Text(
                                "Aucune notification — Tout est sous contrôle.",
                                color=SUCCESS, size=12,
                            ),
                        ],
                        spacing=10,
                    ),
                )
            ]
        _update()

    # ── Build filter tab buttons ──────────────────────────────────────────
    filter_defs = [
        ("nouveau",   "Nouvelles"),
        ("traite",    "Traitées"),
        ("ignore",    "Ignorées"),
        (None,        "Toutes"),
    ]
    for key, lbl in filter_defs:
        btn = ft.ElevatedButton(
            lbl,
            style=ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: _MUTED},
                bgcolor={ft.ControlState.DEFAULT: _FIELD},
                shape=ft.RoundedRectangleBorder(radius=6),
            ),
            on_click=lambda ev, k=key: _set_filter(k),
        )
        filter_buttons[key if key is not None else "None"] = btn

    prio_btns: list[ft.Control] = []
    for prio, clr in PRIORITES.items():
        prio_btns.append(ft.ElevatedButton(
            prio.title(),
            style=ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: clr},
                bgcolor={ft.ControlState.DEFAULT: _FIELD},
                side=ft.BorderSide(1, clr),
                shape=ft.RoundedRectangleBorder(radius=6),
            ),
            on_click=lambda ev, p=prio: _set_filter(None, p),
        ))

    header = ft.Container(
        bgcolor=_CARD,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=44, height=44, bgcolor=WARNING, border_radius=8,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, color="#FFFFFF", size=24),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Centre de Notifications QHSE", color=_TEXT, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("Alertes centralisées — Risques · Accidents · Permis · EPI", color=_MUTED, size=11),
                    ],
                    spacing=2, tight=True,
                ),
                ft.Container(expand=True),
                badge_container,
                ft.ElevatedButton(
                    "Synchroniser",
                    icon=ft.Icons.SYNC_OUTLINED,
                    bgcolor=PRIMARY, color="#FFFFFF",
                    on_click=do_sync,
                ),
                ft.OutlinedButton(
                    "Nettoyer traitées",
                    icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                    style=ft.ButtonStyle(
                        color={ft.ControlState.DEFAULT: _MUTED},
                        side=ft.BorderSide(1, _BORDER),
                    ),
                    on_click=do_clear,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    filter_bar = ft.Container(
        bgcolor=_CARD,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Statut :", color=_MUTED, size=10),
                        *list(filter_buttons.values()),
                        ft.Container(width=12),
                        ft.Text("Priorité :", color=_MUTED, size=10),
                        *prio_btns,
                    ],
                    spacing=6,
                    wrap=False,
                    scroll=ft.ScrollMode.AUTO,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[source_dd],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                status_text,
            ],
            spacing=6,
            tight=True,
        ),
    )

    root = ft.Container(
        bgcolor=_BG,
        expand=True,
        content=ft.Column(
            controls=[header, filter_bar, notif_area],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    # Auto-sync on load then refresh
    try:
        sync_module_alerts()
    except Exception:
        pass
    _update_filter_btns()
    refresh()
    return root
