import flet as ft


PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
SIDEBAR = "#111827"
SIDEBAR_MUTED = "#9CA3AF"
TEXT = "#172033"
MUTED = "#64748B"
SURFACE = "#F3F6FB"
PANEL = "#FFFFFF"
BORDER = "#D8E0EC"
WARNING = "#F59E0B"
DANGER = "#DC2626"
SUCCESS = "#16A34A"
INFO = "#0891B2"


def page_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        visual_density=ft.VisualDensity.COMFORTABLE,
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=PRIMARY,
            thumb_visibility=True,
            track_color="#1F2937",
            track_visibility=True,
            thickness=8,
            radius=4,
        ),
        use_material3=True,
    )
