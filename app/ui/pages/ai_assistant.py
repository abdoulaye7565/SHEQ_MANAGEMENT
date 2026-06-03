from __future__ import annotations

from typing import Any

import flet as ft

from app.services.ai_service import AIConfigurationError, assistant_answer, get_ai_settings
from app.services.alert_service import get_alert_summary
from app.services.maintenance_action_service import get_maintenance_action_summary
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.components.stats import stat_card
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


def ai_assistant_page(page: ft.Page | None = None) -> ft.Control:
    status = ft.Text("", size=12, color=MUTED)
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    question = ft.TextField(
        label="Question QHSE",
        hint_text="Ex: Analyse les risques critiques ouverts et propose les priorites de la semaine.",
        multiline=True,
        min_lines=4,
        max_lines=7,
        expand=True,
    )
    answer = ft.TextField(
        label="Reponse IA",
        multiline=True,
        min_lines=12,
        max_lines=18,
        read_only=True,
        expand=True,
        value="",
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

    def local_context() -> dict[str, Any]:
        return {
            "ai_settings": get_ai_settings(),
            "maintenance_actions": get_maintenance_action_summary(),
            "alerts": get_alert_summary(),
        }

    def render_summary() -> None:
        ai = get_ai_settings()
        maintenance = get_maintenance_action_summary()
        alerts = get_alert_summary()
        summary_row.controls = [
            _summary_chip("IA", "Active" if ai["enabled"] else "Off", SUCCESS if ai["enabled"] else WARNING, ft.Icons.AUTO_AWESOME_OUTLINED),
            _summary_chip("Cle API", "OK" if ai["api_key_configured"] else "A configurer", SUCCESS if ai["api_key_configured"] else DANGER, ft.Icons.KEY_OUTLINED),
            _summary_chip("Alertes ouvertes", alerts.get("open", 0), WARNING, ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
            _summary_chip("Risques hauts", maintenance.get("risks_high_residual", 0), DANGER if maintenance.get("risks_high_residual") else SUCCESS, ft.Icons.SHIELD_OUTLINED),
        ]

    def ask_ai(event: ft.ControlEvent | None = None) -> None:
        try:
            answer.value = "Analyse en cours..."
            notify("Assistant IA en cours de generation.", PRIMARY)
            _update()
            answer.value = assistant_answer(str(question.value or ""), local_context())
            notify("Reponse IA generee. A valider par un responsable QHSE.", SUCCESS)
        except (ValueError, AIConfigurationError) as exc:
            answer.value = ""
            notify(str(exc), DANGER)
        _update()

    def preset(text: str) -> None:
        question.value = text
        _update()

    root = ft.Column(
        controls=[
            module_header(
                "Assistant IA QHSE",
                "Aide a l'analyse terrain, aux priorites QHSE et aux syntheses operationnelles.",
            ),
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=16,
                content=ft.Column(
                    controls=[
                        summary_row,
                        ft.Row(
                            controls=[
                                ft.OutlinedButton(
                                    "Priorites QHSE",
                                    icon=ft.Icons.PRIORITY_HIGH_OUTLINED,
                                    on_click=lambda event: preset("Resume les priorites QHSE actuelles et propose un ordre d'action."),
                                ),
                                ft.OutlinedButton(
                                    "Risques ISO",
                                    icon=ft.Icons.HEALTH_AND_SAFETY_OUTLINED,
                                    on_click=lambda event: preset("Analyse les risques residuels hauts et propose des mesures selon la hierarchie des controles ISO."),
                                ),
                                ft.OutlinedButton(
                                    "Rapport jour",
                                    icon=ft.Icons.SUMMARIZE_OUTLINED,
                                    on_click=lambda event: preset("Prepare une synthese professionnelle pour le briefing QHSE du jour."),
                                ),
                                status,
                            ],
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
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
                        question,
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("Demander a l'IA", icon=ft.Icons.AUTO_AWESOME_OUTLINED, on_click=ask_ai),
                                ft.OutlinedButton("Effacer", icon=ft.Icons.CLEAR_OUTLINED, on_click=lambda event: preset("")),
                            ],
                            spacing=10,
                        ),
                        answer,
                        ft.Text(
                            "L'assistant ne remplace pas l'approbation HSE, les inspections terrain ou les exigences legales.",
                            color=MUTED,
                            size=12,
                        ),
                    ],
                    spacing=12,
                ),
            ),
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render_summary()
    return root


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        stat_card(label, value, color, icon, compact=True),
        col={"xs": 12, "sm": 6, "md": 3, "lg": 3, "xl": 3},
    )
