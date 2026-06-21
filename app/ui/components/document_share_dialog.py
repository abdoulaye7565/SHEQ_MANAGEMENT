from __future__ import annotations

from pathlib import Path
from typing import Any

import flet as ft

from app.services.email_service import EmailConfigurationError
from app.ui.components.feedback import show_feedback

# Dark cockpit palette
_BG = "#071321"
_CARD = "#0D2040"
_CARD2 = "#0A1929"
_BORDER = "#1E3A5F"
_TEXT = "#E2E8F0"
_MUTED = "#64748B"
_PRIMARY = "#1A6FC4"
_SUCCESS = "#10B981"
_VIOLET = "#7C3AED"
_WARNING = "#F59E0B"
_DANGER = "#EF4444"
_ORANGE = "#F97316"

_EXT_COLORS: dict[str, str] = {
    "XLSX": "#21A366", "XLS": "#21A366",
    "PDF": "#DC2626",
    "DOCX": "#2B579A", "DOC": "#2B579A",
    "PNG": _ORANGE, "JPG": _ORANGE, "JPEG": _ORANGE,
    "CSV": _MUTED,
}

_CHANNELS: list[tuple[str, str, Any, str, str]] = [
    ("email",    "Email SMTP", ft.Icons.EMAIL_OUTLINED,   _PRIMARY, "Envoi direct\nSMTP"),
    ("outlook",  "Outlook",    ft.Icons.INBOX_OUTLINED,   _VIOLET,  "Brouillon\nà relire"),
    ("whatsapp", "WhatsApp",   ft.Icons.CHAT_OUTLINED,    _SUCCESS, "WhatsApp Web\nbrowser"),
]


def show_document_share_dialog(
    page: ft.Page,
    file_path: Path,
    document_title: str = "",
    default_subject: str = "",
    default_body: str = "",
) -> None:
    """Open the document-sharing dialog (Email / Outlook / WhatsApp)."""
    from app.services.document_share_service import (
        get_share_channels,
        share_document_email,
        share_document_outlook,
        share_document_whatsapp,
    )

    title = document_title or file_path.name
    ch_cfg = get_share_channels()

    try:
        raw = file_path.stat().st_size
        size_label = f"{raw // 1024} Ko" if raw < 1_048_576 else f"{raw / 1_048_576:.1f} Mo"
    except OSError:
        size_label = "—"

    state: dict[str, Any] = {"channel": None}

    # ── Shared fields ──────────────────────────────────────────────────────
    _tf_kwargs: dict[str, Any] = dict(
        bgcolor=_CARD2,
        border_color=_BORDER,
        focused_border_color=_PRIMARY,
        color=_TEXT,
        label_style=ft.TextStyle(color=_MUTED, size=11),
        text_size=12,
        dense=True,
    )

    subject_field = ft.TextField(
        value=default_subject or f"OREZONE QHSE — {title}",
        label="Objet",
        **_tf_kwargs,
    )
    body_field = ft.TextField(
        value=default_body or (
            f"Bonjour,\n\nVeuillez trouver ci-joint : {title}.\n\n"
            "Ce document a été généré depuis l'application OREZONE QHSE.\n\n"
            "Cordialement,\nOREZONE QHSE"
        ),
        label="Corps du message",
        multiline=True, min_lines=3, max_lines=6,
        **_tf_kwargs,
    )
    recipients_field = ft.TextField(
        value=", ".join(ch_cfg["email"]["recipients"] or ch_cfg["outlook"]["recipients"]),
        label="Destinataires (séparés par virgule)",
        **_tf_kwargs,
    )
    wa_message_field = ft.TextField(
        value=(
            f"Bonjour, le document *{title}* est disponible.\n\n"
            f"Fichier : {file_path.name}\n\n"
            "📎 Merci de joindre le fichier manuellement depuis le dossier exports.\n\n"
            "Cordialement, OREZONE QHSE"
        ),
        label="Message WhatsApp",
        multiline=True, min_lines=3, max_lines=6,
        **_tf_kwargs,
    )
    wa_targets_field = ft.TextField(
        value=", ".join(ch_cfg["whatsapp"]["targets"]),
        label="Numéros / liens WhatsApp (séparés par virgule)",
        **_tf_kwargs,
    )

    # ── Channel cards ──────────────────────────────────────────────────────
    channel_cards: dict[str, ft.Container] = {}

    def _make_card(ch_id: str, ch_label: str, ch_icon: Any, ch_color: str, ch_desc: str) -> ft.Container:
        available = ch_cfg.get(ch_id, {}).get("available", False)
        hint = ch_cfg.get(ch_id, {}).get("hint", "")
        return ft.Container(
            bgcolor=_CARD,
            border=ft.border.all(2, _BORDER),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=10, vertical=12),
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Container(
                        width=38, height=38,
                        bgcolor=ch_color + ("28" if available else "14"),
                        border_radius=8,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ch_icon, color=ch_color if available else _MUTED, size=20),
                    ),
                    ft.Text(ch_label, color=_TEXT if available else _MUTED, size=11,
                            weight=ft.FontWeight.W_600),
                    ft.Text(ch_desc, color=_MUTED, size=8, text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        "✓ Prêt" if available else (hint[:28] + "…" if len(hint) > 28 else hint),
                        color=_SUCCESS if available else _WARNING,
                        size=8, italic=not available,
                    ),
                ],
                spacing=4, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    cards_row: list[ft.Control] = []
    for ch_id, ch_label, ch_icon, ch_color, ch_desc in _CHANNELS:
        card = _make_card(ch_id, ch_label, ch_icon, ch_color, ch_desc)
        channel_cards[ch_id] = card
        available = ch_cfg.get(ch_id, {}).get("available", False)
        if available:
            cards_row.append(ft.GestureDetector(
                content=card,
                on_tap=lambda _e, cid=ch_id: _select(cid),
                mouse_cursor=ft.MouseCursor.CLICK,
            ))
        else:
            cards_row.append(card)

    # ── Detail area ────────────────────────────────────────────────────────
    detail_column = ft.Column(controls=[], spacing=8, tight=True)
    detail_area = ft.Container(content=detail_column, visible=False, padding=ft.padding.only(top=4))

    send_btn = ft.ElevatedButton(
        "Envoyer", icon=ft.Icons.SEND_OUTLINED,
        bgcolor=_PRIMARY, color="#FFFFFF",
        visible=False,
    )

    def _info_banner(text: str, color: str) -> ft.Container:
        return ft.Container(
            bgcolor=_CARD2,
            border=ft.border.all(1, color + "44"),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=color, size=14),
                ft.Text(text, color=_MUTED, size=10),
            ], spacing=6),
        )

    _form_builders: dict[str, Any] = {
        "email": lambda: (
            _set_detail([
                ft.Text("Destinataires et contenu", color=_MUTED, size=10, weight=ft.FontWeight.W_600),
                recipients_field, subject_field, body_field,
            ]),
            _set_send("Envoyer par Email", ft.Icons.EMAIL_OUTLINED, _PRIMARY),
        ),
        "outlook": lambda: (
            _set_detail([
                ft.Text("Destinataires et contenu", color=_MUTED, size=10, weight=ft.FontWeight.W_600),
                recipients_field, subject_field, body_field,
                _info_banner("Outlook s'ouvre avec le brouillon. Vérifiez avant d'envoyer.", _VIOLET),
            ]),
            _set_send("Ouvrir Outlook", ft.Icons.INBOX_OUTLINED, _VIOLET),
        ),
        "whatsapp": lambda: (
            _set_detail([
                wa_message_field, wa_targets_field,
                _info_banner(
                    "WhatsApp s'ouvre dans le navigateur. Joindre le fichier manuellement.",
                    _SUCCESS,
                ),
            ]),
            _set_send("Ouvrir WhatsApp", ft.Icons.CHAT_OUTLINED, _SUCCESS),
        ),
    }

    def _set_detail(controls: list[ft.Control]) -> None:
        detail_column.controls = controls
        detail_area.visible = True

    def _set_send(text: str, icon: Any, color: str) -> None:
        send_btn.text = text
        send_btn.icon = icon
        send_btn.bgcolor = color
        send_btn.visible = True

    def _select(channel: str) -> None:
        state["channel"] = channel
        for ch_id, card in channel_cards.items():
            _, _, _, ch_color, _ = next(c for c in _CHANNELS if c[0] == ch_id)
            if ch_id == channel:
                card.border = ft.border.all(2, ch_color)
                card.bgcolor = ch_color + "18"
            else:
                card.border = ft.border.all(2, _BORDER)
                card.bgcolor = _CARD
        _form_builders[channel]()
        page.update()

    def _do_send(_: ft.ControlEvent) -> None:
        channel = state.get("channel")
        if not channel:
            return
        try:
            if channel in ("email", "outlook"):
                recips = [r.strip() for r in recipients_field.value.split(",") if r.strip()]
                if not recips:
                    show_feedback(page, "Ajoutez au moins un destinataire.", _WARNING)
                    return
                subj = (subject_field.value or "").strip()
                body = (body_field.value or "").strip()
                if channel == "email":
                    share_document_email(file_path, subj, body, recips)
                    show_feedback(page, f"Document envoyé à {len(recips)} destinataire(s).", _SUCCESS)
                else:
                    share_document_outlook(file_path, subj, body, recips)
                    show_feedback(page, "Brouillon Outlook ouvert.", _VIOLET)
            else:
                tgts = [t.strip() for t in wa_targets_field.value.split(",") if t.strip()]
                if not tgts:
                    show_feedback(page, "Ajoutez au moins un numéro ou lien WhatsApp.", _WARNING)
                    return
                msg = (wa_message_field.value or "").strip()
                share_document_whatsapp(file_path, msg, tgts)
                show_feedback(page, "WhatsApp ouvert dans le navigateur.", _SUCCESS)
            _close()
        except EmailConfigurationError as exc:
            show_feedback(page, str(exc), _DANGER)

    send_btn.on_click = _do_send

    def _close(_: ft.ControlEvent | None = None) -> None:
        page.pop_dialog()
        page.update()

    # ── File info bar ──────────────────────────────────────────────────────
    ext = file_path.suffix.upper().lstrip(".")
    ext_color = _EXT_COLORS.get(ext, _MUTED)
    file_bar = ft.Container(
        bgcolor=_CARD2,
        border=ft.border.all(1, _BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row([
            ft.Container(
                bgcolor=ext_color + "28", border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                content=ft.Text(ext or "DOC", color=ext_color, size=10, weight=ft.FontWeight.BOLD),
            ),
            ft.Column([
                ft.Text(
                    file_path.name, color=_TEXT, size=12, weight=ft.FontWeight.W_500,
                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1,
                    expand=True,
                ),
                ft.Text(size_label, color=_MUTED, size=10),
            ], spacing=1, tight=True, expand=True),
            ft.Icon(ft.Icons.ATTACH_FILE_OUTLINED, color=_MUTED, size=16),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    # ── Dialog ────────────────────────────────────────────────────────────
    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=_BG,
        title=ft.Row([
            ft.Container(
                width=36, height=36,
                bgcolor=_PRIMARY + "28", border_radius=8,
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.SHARE_OUTLINED, color=_PRIMARY, size=20),
            ),
            ft.Column([
                ft.Text("Partager le document", color=_TEXT, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Choisissez un canal d'envoi", color=_MUTED, size=10),
            ], spacing=1, tight=True, expand=True),
            ft.IconButton(
                ft.Icons.CLOSE, icon_color=_MUTED, icon_size=18,
                on_click=_close,
            ),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        content=ft.Container(
            width=520,
            content=ft.Column(
                controls=[
                    file_bar,
                    ft.Divider(color=_BORDER, height=1),
                    ft.Text("Canal d'envoi :", color=_MUTED, size=10, weight=ft.FontWeight.W_600),
                    ft.Row(controls=cards_row, spacing=10),
                    detail_area,
                ],
                spacing=10, tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
        actions=[
            ft.TextButton(
                "Annuler",
                style=ft.ButtonStyle(color=_MUTED),
                on_click=_close,
            ),
            send_btn,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dialog)
