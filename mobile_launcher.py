I"""
Wrapper de lancement diagnostique.
Importe mobile_app dans un try/except et affiche l'erreur a l'ecran
si le module plante (au lieu d'un ecran noir).
"""
from __future__ import annotations
import traceback
import flet as ft


def main(page: ft.Page) -> None:
    page.bgcolor = "#071321"
    page.padding = 0
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Spinner visible immediatement — API minimale, pas de Container/alignment
    page.add(
        ft.ProgressRing(color="#3B82F6", width=48, height=48, stroke_width=3),
        ft.Text("OREZONE QHSE", size=18, weight=ft.FontWeight.BOLD,
                color="#E2E8F0", text_align=ft.TextAlign.CENTER),
        ft.Text("Chargement en cours...", size=12, color="#7A9BB5",
                text_align=ft.TextAlign.CENTER),
    )
    page.update()

    try:
        import mobile_app as _app
        page.controls.clear()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        _app.build_mobile_page(page)
    except Exception:
        err = traceback.format_exc()
        page.controls.clear()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.add(
            ft.Icon(ft.Icons.BUG_REPORT_OUTLINED, color="#EF4444", size=48),
            ft.Text("Erreur au demarrage", size=15,
                    weight=ft.FontWeight.BOLD, color="#EF4444",
                    text_align=ft.TextAlign.CENTER),
            ft.Text(err[-600:], size=10, color="#94A3B8",
                    no_wrap=False, max_lines=20,
                    text_align=ft.TextAlign.LEFT),
        )
        page.update()


if __name__ == "__main__":
    ft.run(main)
