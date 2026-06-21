from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

import flet as ft

from app.services.accident_service import get_accident_summary
from app.services.ai_service import (
    AIConfigurationError,
    assistant_answer_with_history,
    build_full_qhse_context,
    get_ai_settings,
    summarize_alerts_and_reports,
)
from app.services.alert_service import get_alert_summary
from app.services.maintenance_action_service import get_maintenance_action_summary
from app.services.ppe_service import get_ppe_summary
from app.ui.components.feedback import show_feedback
from app.ui.theme import DANGER, PRIMARY, SUCCESS, WARNING

_BG        = "#071321"
_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#7A9CC0"
_AI_ACCENT = "#10B981"   # teal — AI bubble left border
_USR_ACCENT= "#2563EB"   # blue — user bubble right border


def ai_assistant_page(page: ft.Page | None = None) -> ft.Control:
    conversation: list[dict[str, Any]] = []
    state: dict[str, Any] = {"loading": False, "cancelled": False}

    # ── Initial AI settings (for header rendering) ────────────────────────────
    try:
        ai_init = get_ai_settings()
    except Exception:
        ai_init = {"enabled": False, "model": "N/A", "api_key_configured": False,
                   "operational": False, "last_test_status": "not_tested", "ready": False}

    # ── Shared mutable controls ───────────────────────────────────────────────
    kpi_strip         = ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    chat_list         = ft.Column(spacing=20, tight=True)
    conv_label        = ft.Text("Nouvelle conversation", color=_DK_MUTED, size=11)
    # Two separate Text controls — same value, but each can have only one parent in Flet
    model_label_badge  = ft.Text(ai_init.get("model", "N/A"), color=_DK_MUTED, size=11)
    model_label_footer = ft.Text(ai_init.get("model", "N/A"), color=_DK_MUTED, size=11)

    question_tf = ft.TextField(
        hint_text="Posez votre question QHSE — l'IA voit vos données en temps réel…",
        multiline=True,
        min_lines=2,
        max_lines=6,
        expand=True,
        border=ft.InputBorder.OUTLINE,
        border_color=_DK_BORDER,
        focused_border_color=PRIMARY,
        focused_border_width=2,
        fill_color=_DK_CARD2,
        filled=True,
        hint_style=ft.TextStyle(color=_DK_MUTED, size=13),
        text_style=ft.TextStyle(color=_DK_TEXT, size=13),
        cursor_color=PRIMARY,
        border_radius=10,
        on_submit=lambda e: _ask(),
    )
    send_btn = ft.ElevatedButton(
        "Envoyer",
        icon=ft.Icons.SEND_ROUNDED,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT:  PRIMARY,
                ft.ControlState.DISABLED: _DK_HEAD,
            },
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
        ),
        tooltip="Envoyer (Entrée)",
        on_click=lambda e: _ask(),
    )
    cancel_btn = ft.IconButton(
        icon=ft.Icons.STOP_CIRCLE_OUTLINED,
        icon_color=DANGER,
        icon_size=24,
        tooltip="Annuler",
        visible=False,
        on_click=lambda e: _cancel(),
    )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _now() -> str:
        return datetime.now().strftime("%H:%M")

    def _page_update() -> None:
        try:
            if page:
                page.update()
        except Exception:
            pass

    def _update() -> None:
        try:
            root.update()
            root.scroll_to(offset=float("inf"), duration=250)
        except Exception:
            pass

    def _copy(content: str) -> None:
        if page:
            try:
                page.set_clipboard(content)
                show_feedback(page, "Réponse copiée dans le presse-papiers.", SUCCESS)
            except Exception:
                pass

    # ── Context builder ───────────────────────────────────────────────────────
    def _build_context() -> dict[str, Any]:
        return build_full_qhse_context()

    # ── KPI strip refresh ─────────────────────────────────────────────────────
    def render_summary() -> None:
        try:
            alerts = get_alert_summary()
        except Exception:
            alerts = {}
        try:
            maint = get_maintenance_action_summary()
        except Exception:
            maint = {}
        try:
            acc = get_accident_summary()
        except Exception:
            acc = {}
        try:
            ppe = get_ppe_summary()
        except Exception:
            ppe = {}
        try:
            ai = get_ai_settings()
        except Exception:
            ai = ai_init

        _m = ai.get("model", "N/A")
        model_label_badge.value  = _m
        model_label_footer.value = _m

        def _dot(label: str, value: Any, color: str) -> ft.Control:
            active = bool(value) and value != 0
            c = color if active else _DK_BORDER
            return ft.Row(
                controls=[
                    ft.Container(width=7, height=7, bgcolor=c, border_radius=4),
                    ft.Text(f"{value}  {label}", color=c if active else _DK_MUTED, size=11),
                ],
                spacing=5, tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        def _sep() -> ft.Control:
            return ft.Container(width=1, height=12, bgcolor=_DK_BORDER)

        kpi_strip.controls = [
            _dot("alertes", alerts.get("open", 0), DANGER),
            _sep(),
            _dot("risques hauts", maint.get("risks_high_residual", 0), WARNING),
            _sep(),
            _dot("accidents ouverts", acc.get("ouverts", 0), "#F97316"),
            _sep(),
            _dot("EPI expirés", ppe.get("expired", 0), DANGER),
            _sep(),
            _dot("Clé API", "OK" if ai.get("api_key_configured") else "—",
                 SUCCESS if ai.get("api_key_configured") else DANGER),
        ]

    # ── Chat rebuild ──────────────────────────────────────────────────────────
    def _rebuild_chat() -> None:
        controls: list[ft.Control] = []
        if not conversation and not state["loading"]:
            controls.append(_empty_state())
        else:
            for msg in conversation:
                if msg["role"] == "user":
                    controls.append(_user_bubble(msg["content"], msg.get("ts", "")))
                else:
                    controls.append(
                        _ai_bubble(msg["content"], msg.get("ts", ""), msg.get("error", False))
                    )
            if state["loading"]:
                controls.append(_loading_bubble())

        chat_list.controls = controls
        send_btn.disabled  = state["loading"]
        cancel_btn.visible = state["loading"]

        n = sum(1 for m in conversation if m["role"] == "user")
        conv_label.value = (
            f"{n} échange{'s' if n > 1 else ''}"
            if n else "Nouvelle conversation"
        )

    # ── Core actions ──────────────────────────────────────────────────────────
    def _ask(event: ft.ControlEvent | None = None) -> None:
        question = (question_tf.value or "").strip()
        if not question or state["loading"]:
            return

        ts = _now()
        conversation.append({"role": "user", "content": question, "ts": ts})
        question_tf.value  = ""
        state["loading"]   = True
        state["cancelled"] = False

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in conversation[:-1]
        ]
        context = _build_context()

        _rebuild_chat()
        _update()

        def _run() -> None:
            response: str | None  = None
            error_msg: str | None = None
            try:
                response = assistant_answer_with_history(question, history, context)
            except (ValueError, AIConfigurationError, Exception) as exc:
                error_msg = str(exc)
            finally:
                state["loading"] = False

            if not state["cancelled"]:
                if response:
                    conversation.append({"role": "assistant", "content": response, "ts": _now()})
                elif error_msg:
                    conversation.append({
                        "role": "assistant", "content": error_msg,
                        "ts": _now(), "error": True,
                    })

            _rebuild_chat()
            _page_update()

        threading.Thread(target=_run, daemon=True).start()

    def _cancel(event: ft.ControlEvent | None = None) -> None:
        state["cancelled"] = True
        state["loading"]   = False
        _rebuild_chat()
        _update()

    def _clear(event: ft.ControlEvent | None = None) -> None:
        conversation.clear()
        question_tf.value  = ""
        state["loading"]   = False
        state["cancelled"] = True
        _rebuild_chat()
        _update()

    def _preset(text: str) -> None:
        question_tf.value = text
        _update()

    def _ask_summary(event: ft.ControlEvent | None = None) -> None:
        if state["loading"]:
            return
        ts = _now()
        conversation.append({
            "role": "user",
            "content": "Génère une synthèse opérationnelle QHSE complète pour le briefing terrain.",
            "ts": ts,
        })
        state["loading"]   = True
        state["cancelled"] = False
        _rebuild_chat()
        _update()

        def _run() -> None:
            response: str | None  = None
            err: str | None       = None
            try:
                response = summarize_alerts_and_reports(_build_context())
            except Exception as exc:
                err = str(exc)
            finally:
                state["loading"] = False

            if not state["cancelled"]:
                if response:
                    conversation.append({"role": "assistant", "content": response, "ts": _now()})
                elif err:
                    conversation.append({
                        "role": "assistant", "content": err,
                        "ts": _now(), "error": True,
                    })
            _rebuild_chat()
            _page_update()

        threading.Thread(target=_run, daemon=True).start()

    # ── Dynamic presets ───────────────────────────────────────────────────────
    def _priorities_prompt() -> str:
        try:
            a  = get_alert_summary()
            m  = get_maintenance_action_summary()
            ac = get_accident_summary()
            pp = get_ppe_summary()
        except Exception:
            a = m = ac = pp = {}
        return (
            f"Situation : {a.get('open','?')} alertes ouvertes "
            f"({a.get('critical','?')} critiques), "
            f"{m.get('risks_high_residual','?')} risques hauts, "
            f"{m.get('actions_late','?')} actions en retard, "
            f"{ac.get('ouverts','?')} accidents/incidents ouverts, "
            f"{pp.get('expired','?')} EPI expirés. "
            "Établis les 5 priorités QHSE les plus urgentes pour aujourd'hui "
            "avec délais recommandés et responsables suggérés."
        )

    # ── Bubble components ─────────────────────────────────────────────────────
    def _user_bubble(content: str, ts: str) -> ft.Control:
        return ft.Row(
            controls=[
                ft.Container(expand=True),
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.only(
                        right=ft.BorderSide(3, _USR_ACCENT),
                        top=ft.BorderSide(1, _DK_BORDER),
                        left=ft.BorderSide(1, _DK_BORDER),
                        bottom=ft.BorderSide(1, _DK_BORDER),
                    ),
                    border_radius=ft.border_radius.only(
                        top_left=14, top_right=4,
                        bottom_left=14, bottom_right=14,
                    ),
                    padding=ft.padding.symmetric(horizontal=18, vertical=12),
                    content=ft.Column(
                        controls=[
                            ft.Text(content, color=_DK_TEXT, size=13, selectable=True),
                            ft.Row(
                                controls=[
                                    ft.Container(expand=True),
                                    ft.Text(ts, color=_DK_MUTED, size=9),
                                ],
                            ),
                        ],
                        spacing=6, tight=True,
                    ),
                ),
            ],
            spacing=8,
        )

    def _ai_bubble(content: str, ts: str, is_error: bool = False) -> ft.Control:
        accent = DANGER if is_error else _AI_ACCENT
        body: ft.Control = (
            ft.Text(content, color=DANGER, size=13, selectable=True)
            if is_error
            else ft.Markdown(
                value=content,
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            )
        )
        return ft.Row(
            controls=[
                ft.Container(
                    width=36, height=36,
                    bgcolor=_DK_HEAD,
                    border_radius=18,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.SMART_TOY_OUTLINED, color=accent, size=18),
                ),
                ft.Container(
                    bgcolor=_DK_CARD,
                    border=ft.border.only(
                        left=ft.BorderSide(3, accent),
                        top=ft.BorderSide(1, _DK_BORDER),
                        right=ft.BorderSide(1, _DK_BORDER),
                        bottom=ft.BorderSide(1, _DK_BORDER),
                    ),
                    border_radius=ft.border_radius.only(
                        top_left=4, top_right=14,
                        bottom_left=14, bottom_right=14,
                    ),
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                    expand=True,
                    content=ft.Column(
                        controls=[
                            body,
                            ft.Row(
                                controls=[
                                    ft.Text(ts, color=_DK_MUTED, size=9),
                                    ft.Container(expand=True),
                                    ft.IconButton(
                                        icon=ft.Icons.COPY_ALL_OUTLINED,
                                        icon_color=_DK_MUTED,
                                        icon_size=15,
                                        tooltip="Copier",
                                        on_click=lambda e, c=content: _copy(c),
                                    ),
                                ],
                                spacing=4,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=10, tight=True,
                    ),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _loading_bubble() -> ft.Control:
        return ft.Row(
            controls=[
                ft.Container(
                    width=36, height=36,
                    bgcolor=_DK_HEAD,
                    border_radius=18,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.SMART_TOY_OUTLINED, color=_AI_ACCENT, size=18),
                ),
                ft.Container(
                    bgcolor=_DK_CARD,
                    border=ft.border.only(
                        left=ft.BorderSide(3, _AI_ACCENT),
                        top=ft.BorderSide(1, _DK_BORDER),
                        right=ft.BorderSide(1, _DK_BORDER),
                        bottom=ft.BorderSide(1, _DK_BORDER),
                    ),
                    border_radius=ft.border_radius.only(
                        top_left=4, top_right=14,
                        bottom_left=14, bottom_right=14,
                    ),
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                    content=ft.Row(
                        controls=[
                            ft.ProgressRing(
                                width=18, height=18, stroke_width=2,
                                color=_AI_ACCENT,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Analyse en cours…",
                                            color=_DK_TEXT, size=13, italic=True),
                                    ft.Text(
                                        "Collecte du contexte QHSE · Appel API · Génération",
                                        color=_DK_MUTED, size=10,
                                    ),
                                ],
                                spacing=2, tight=True,
                            ),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _empty_state() -> ft.Control:
        suggestions = [
            (ft.Icons.PRIORITY_HIGH_OUTLINED, "Priorités du jour", _priorities_prompt),
            (ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "Risques ISO 45001",
             lambda: (
                 "Analyse les risques résiduels hauts et propose des mesures correctives "
                 "concrètes selon la hiérarchie des contrôles ISO 45001."
             )),
            (ft.Icons.SUMMARIZE_OUTLINED, "Briefing QHSE",
             lambda: (
                 "Prépare une synthèse professionnelle pour le briefing QHSE du jour : "
                 "points critiques, actions urgentes, rappels réglementaires."
             )),
        ]
        return ft.Column(
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(vertical=28),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                width=64, height=64,
                                bgcolor=_DK_HEAD,
                                border_radius=32,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(ft.Icons.SMART_TOY_OUTLINED,
                                                color=PRIMARY, size=30),
                            ),
                            ft.Text(
                                "Prêt à analyser",
                                color=_DK_TEXT, size=16, weight=ft.FontWeight.W_600,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Posez une question libre ou cliquez sur une suggestion",
                                color=_DK_MUTED, size=12,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10, tight=True,
                    ),
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            bgcolor=_DK_HEAD,
                            border=ft.border.all(1, _DK_BORDER),
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=14, vertical=16),
                            ink=True,
                            on_click=lambda e, fn=fn: (_preset(fn()), _update()),
                            col={"xs": 12, "sm": 4},
                            content=ft.Column(
                                controls=[
                                    ft.Icon(icon, color=PRIMARY, size=22),
                                    ft.Text(
                                        label, color=_DK_TEXT, size=12,
                                        weight=ft.FontWeight.W_500,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10, tight=True,
                            ),
                        )
                        for icon, label, fn in suggestions
                    ],
                    spacing=10, run_spacing=10,
                ),
                ft.Container(
                    bgcolor="#0B1F36",
                    border=ft.border.all(1, "#1A3A5C"),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    content=ft.Text(
                        "⚠  Les réponses IA ne remplacent pas l'inspection terrain "
                        "ni les exigences légales applicables.",
                        color=_DK_MUTED, size=10,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),
            ],
            spacing=12, tight=True,
        )

    # ── Context visibility panel ─────────────────────────────────────────────
    ctx_visible: list[bool] = [False]
    ctx_arrow   = ft.Icon(ft.Icons.EXPAND_MORE_OUTLINED, color=_DK_MUTED, size=14)
    ctx_details = ft.Container(visible=False)

    def _toggle_ctx(event: ft.ControlEvent | None = None) -> None:
        ctx_visible[0] = not ctx_visible[0]
        ctx_arrow.name = (
            ft.Icons.EXPAND_LESS_OUTLINED
            if ctx_visible[0]
            else ft.Icons.EXPAND_MORE_OUTLINED
        )
        ctx_details.visible = ctx_visible[0]
        if ctx_visible[0]:
            ctx_details.content = _ctx_panel_content()
        _update()

    def _ctx_panel_content() -> ft.Control:
        modules = [
            (ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, "Alertes & rapports"),
            (ft.Icons.HANDYMAN_OUTLINED,              "Maintenance & risques"),
            (ft.Icons.PERSONAL_INJURY_OUTLINED,       "Accidents & incidents"),
            (ft.Icons.SAFETY_CHECK_OUTLINED,          "EPI & expirations"),
            (ft.Icons.SCHOOL_OUTLINED,                "Formations & habilitations"),
            (ft.Icons.CALENDAR_TODAY_OUTLINED,        "Date/heure terrain"),
        ]
        return ft.Column(
            controls=[
                ft.Divider(height=12, color=_DK_BORDER),
                ft.Text(
                    "Contexte collecté au moment de chaque envoi — données en temps réel.",
                    color=_DK_MUTED, size=10, italic=True,
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            col={"xs": 12, "sm": 6, "md": 4},
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        width=6, height=6,
                                        bgcolor=_AI_ACCENT, border_radius=3,
                                    ),
                                    ft.Text(label, color=_DK_MUTED, size=11),
                                ],
                                spacing=7,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        )
                        for _, label in modules
                    ],
                    spacing=8, run_spacing=6,
                ),
            ],
            spacing=6, tight=True,
        )

    # ── Preset pill helper ────────────────────────────────────────────────────
    def _pill(label: str, color: str, on_click, filled: bool = False) -> ft.Control:
        if filled:
            return ft.ElevatedButton(
                label,
                style=ft.ButtonStyle(
                    bgcolor=color, color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=20),
                    padding=ft.padding.symmetric(horizontal=16, vertical=9),
                    text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_500),
                ),
                on_click=on_click,
            )
        return ft.OutlinedButton(
            label,
            style=ft.ButtonStyle(
                color=color,
                side=ft.BorderSide(1, color),
                shape=ft.RoundedRectangleBorder(radius=20),
                padding=ft.padding.symmetric(horizontal=14, vertical=9),
                text_style=ft.TextStyle(size=11),
            ),
            on_click=on_click,
        )

    # ── Header ────────────────────────────────────────────────────────────────
    _s_color = _ai_status_color(ai_init)
    _s_label = _ai_status_label(ai_init)

    header = ft.Container(
        bgcolor=_DK_CARD,
        border=ft.border.all(1, _DK_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=44, height=44,
                    bgcolor=_DK_HEAD,
                    border_radius=22,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.SMART_TOY_OUTLINED, color=PRIMARY, size=22),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Assistant IA QHSE",
                                color=_DK_TEXT, size=16, weight=ft.FontWeight.W_600),
                        ft.Text(
                            "Analyse terrain  ·  priorisation des risques  ·  synthèses opérationnelles",
                            color=_DK_MUTED, size=11,
                        ),
                    ],
                    spacing=2, tight=True,
                ),
                ft.Container(expand=True),
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.all(1, _s_color),
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                    content=ft.Row(
                        controls=[
                            ft.Container(width=7, height=7, bgcolor=_s_color, border_radius=4),
                            ft.Text(_s_label, color=_s_color, size=11,
                                    weight=ft.FontWeight.W_500),
                        ],
                        spacing=7,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    bgcolor=_DK_HEAD,
                    border=ft.border.all(1, _DK_BORDER),
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.MEMORY_OUTLINED, color=_DK_MUTED, size=12),
                            model_label_badge,
                        ],
                        spacing=5,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                    icon_color=_DK_MUTED,
                    icon_size=18,
                    tooltip="Vider la conversation",
                    on_click=_clear,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # ── Page layout ───────────────────────────────────────────────────────────
    root = ft.Column(
        controls=[
            header,

            # ── Compact KPI strip + context toggle ────────────────────────
            ft.Container(
                bgcolor=_DK_CARD2,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=16, vertical=9),
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                kpi_strip,
                                ft.Container(expand=True),
                                ft.TextButton(
                                    "Ce que voit l'IA",
                                    icon=ft.Icons.VISIBILITY_OUTLINED,
                                    style=ft.ButtonStyle(
                                        color=_DK_MUTED,
                                        shape=ft.RoundedRectangleBorder(radius=6),
                                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                        icon_size=13,
                                    ),
                                    on_click=_toggle_ctx,
                                ),
                                ctx_arrow,
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ctx_details,
                    ],
                    spacing=0, tight=True,
                ),
            ),

            # ── Chat area ─────────────────────────────────────────────────
            ft.Container(
                bgcolor=_DK_CARD2,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=18, vertical=18),
                content=chat_list,
            ),

            # ── Actions rapides (preset pills) ────────────────────────────
            ft.Container(
                bgcolor=_DK_CARD2,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "ACTIONS RAPIDES",
                            color=_DK_MUTED, size=9,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Row(
                            controls=[
                                _pill("🚨  Priorités du jour", WARNING,
                                      lambda e: (_preset(_priorities_prompt()), _update())),
                                _pill("⚠️  Risques ISO 45001", DANGER,
                                      lambda e: (_preset(
                                          "Analyse les risques résiduels hauts et propose des mesures "
                                          "correctives selon la hiérarchie des contrôles ISO 45001 : "
                                          "élimination → substitution → ingénierie → administratif → EPI."
                                      ), _update())),
                                _pill("💀  Accidents & Causes", "#F97316",
                                      lambda e: (_preset(
                                          "Analyse les accidents et incidents récents. "
                                          "Identifie les causes racines (méthode 5 Pourquoi) "
                                          "et propose un plan de prévention ciblé et mesurable."
                                      ), _update())),
                                _pill("🦺  EPI & Formations", "#7C3AED",
                                      lambda e: (_preset(
                                          "Identifie les lacunes EPI (expirations, non-conformités) "
                                          "et de formation (habilitations échues, postes non couverts). "
                                          "Propose un plan de mise en conformité priorisé."
                                      ), _update())),
                                _pill("🔧  Maintenance & Équipements", PRIMARY,
                                      lambda e: (_preset(
                                          "Analyse l'état du parc d'équipements : maintenances en retard, "
                                          "équipements critiques, coûts cumulés et risques associés. "
                                          "Donne les 3 interventions les plus urgentes à planifier cette semaine."
                                      ), _update())),
                                _pill("📊  Synthèse complète", SUCCESS,
                                      _ask_summary, filled=True),
                            ],
                            spacing=8,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ],
                    spacing=8, tight=True,
                ),
            ),

            # ── Input area ────────────────────────────────────────────────
            ft.Container(
                bgcolor=_DK_CARD,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=16, vertical=14),
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                question_tf,
                                ft.Column(
                                    controls=[send_btn, cancel_btn],
                                    spacing=6, tight=True,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE_OUTLINED,
                                        color=_DK_MUTED, size=11),
                                conv_label,
                                ft.Text("·", color=_DK_MUTED, size=11),
                                model_label_footer,
                                ft.Text("·", color=_DK_MUTED, size=11),
                                ft.Text("6 modules actifs", color="#3B82F6", size=11),
                            ],
                            spacing=5,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=8, tight=True,
                ),
            ),
        ],
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    render_summary()
    _rebuild_chat()
    return ft.Container(bgcolor=_BG, expand=True, content=root)


# ── Module-level status helpers ───────────────────────────────────────────────

def _ai_status_label(ai: dict[str, Any]) -> str:
    if ai.get("operational"):
        return "Opérationnelle"
    if ai.get("last_test_status") == "error":
        return "Erreur"
    if ai.get("ready"):
        return "À tester"
    if ai.get("enabled"):
        return "Clé requise"
    return "Désactivée"


def _ai_status_color(ai: dict[str, Any]) -> str:
    if ai.get("operational"):
        return SUCCESS
    if ai.get("last_test_status") == "error":
        return DANGER
    return WARNING
