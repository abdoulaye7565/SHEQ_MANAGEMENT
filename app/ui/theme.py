import flet as ft


PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
SIDEBAR = "#111827"
SIDEBAR_ACTIVE = "#1D4ED8"
SIDEBAR_MUTED = "#9CA3AF"
TEXT = "#172033"
MUTED = "#64748B"
SURFACE = "#F6F8FC"
PANEL = "#FFFFFF"
BORDER = "#CBD5E1"
WARNING = "#F59E0B"
DANGER = "#DC2626"
SUCCESS = "#16A34A"
INFO = "#0891B2"
PANEL_ALT = "#F8FAFC"
HEADER_SOFT = "#EFF6FF"


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
