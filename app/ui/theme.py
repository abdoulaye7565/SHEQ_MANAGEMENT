import flet as ft


PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
SIDEBAR = "#111827"
SIDEBAR_ACTIVE = "#1D4ED8"
SIDEBAR_MUTED = "#9CA3AF"
TEXT = "#172033"
MUTED = "#64748B"
SURFACE = "#071321"
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
            thumb_color="#2563EB",
            thumb_visibility=True,
            track_color="#0D2040",
            track_visibility=True,
            thickness=7,
            radius=4,
        ),
        use_material3=True,
    )


def dark_page_theme() -> ft.Theme:
    """Dark cockpit theme — controls dropdown popup colors, input chrome, etc."""
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=PRIMARY,
            on_primary="#FFFFFF",
            surface="#0D2040",
            on_surface="#E2E8F0",
            on_surface_variant="#9DB0C5",
            outline="#1E3A5F",
            surface_container="#0A1929",
            surface_container_high="#112240",
            surface_container_highest="#0D2040",
        ),
        visual_density=ft.VisualDensity.COMFORTABLE,
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color="#2563EB",
            thumb_visibility=True,
            track_color="#0D2040",
            track_visibility=True,
            thickness=7,
            radius=4,
        ),
        use_material3=True,
    )
