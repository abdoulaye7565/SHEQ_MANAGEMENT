from __future__ import annotations

import flet as ft

from app.ui.components.module_header import module_header
from app.ui.pages.training import training_page
from app.ui.pages.training_matrix import training_matrix_page
from app.ui.theme import PRIMARY, TEXT


def training_management_page(page: ft.Page | None = None) -> ft.Control:
    state: dict[str, object] = {"view": "training", "cache": {}}
    content = ft.Container()
    training_button = ft.TextButton()
    matrix_button = ft.TextButton()

    def render() -> None:
        view = str(state["view"])
        training_button.style = _button_style(view == "training")
        matrix_button.style = _button_style(view == "matrix")
        cache = state["cache"]
        if isinstance(cache, dict):
            if view not in cache:
                cache[view] = training_page(page) if view == "training" else training_matrix_page()
            content.content = cache[view]
        try:
            root.update()
        except RuntimeError:
            pass

    def set_view(view: str) -> None:
        state["view"] = view
        render()

    training_button.content = "Formations"
    training_button.icon = ft.Icons.SCHOOL_OUTLINED
    training_button.on_click = lambda event: set_view("training")

    matrix_button.content = "Matrice"
    matrix_button.icon = ft.Icons.GRID_ON_OUTLINED
    matrix_button.on_click = lambda event: set_view("matrix")

    root = ft.Column(
        controls=[
            module_header(
                "Gestion de la formation",
                "Enregistrement, suivi des expirations et matrice de conformite.",
            ),
            ft.Container(
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#BFDBFE"),
                border_radius=8,
                padding=10,
                content=ft.Row(
                    controls=[training_button, matrix_button],
                    spacing=8,
                    wrap=True,
                ),
            ),
            content,
        ],
        spacing=18,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    render()
    return root


def _button_style(selected: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color=PRIMARY if selected else TEXT,
        bgcolor="#EFF6FF" if selected else "#FFFFFF",
        shape=ft.RoundedRectangleBorder(radius=8),
    )
