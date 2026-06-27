"""lock_indicator.py — Composant Flet pour afficher l'état de verrouillage d'une fiche."""
from __future__ import annotations

import flet as ft

from app.services.lock_service import get_lock_info


def LockIndicator(
    table_name: str,
    record_id: str,
    current_user: str,
) -> ft.Container:
    """Retourne un badge visuel indiquant l'état de verrouillage de la fiche.

    - Verrou tenu par un autre utilisateur → badge rouge.
    - Verrou tenu par l'utilisateur courant → badge vert.
    - Pas de verrou → conteneur vide invisible.
    """
    try:
        info = get_lock_info(table_name, record_id)
    except Exception:
        info = None

    if info is None:
        return ft.Container(visible=False)

    owner = info.get("utilisateur", "")
    pc = info.get("pc_nom", "")
    since_raw = info.get("verrouille_depuis", "")

    # Formatage de l'heure (HH:MM)
    heure = since_raw[11:16] if len(since_raw) >= 16 else since_raw

    if owner == current_user:
        # Verrou appartenant à l'utilisateur courant
        badge_color = "#16A34A"   # vert
        icon = ft.Icons.EDIT_OUTLINED
        label = "En cours de modification"
        detail = ""
    else:
        # Verrou appartenant à quelqu'un d'autre
        badge_color = "#DC2626"   # rouge
        icon = ft.Icons.LOCK_OUTLINED
        who = f"{owner} ({pc})" if pc and pc != owner else owner
        label = f"En cours d'utilisation par {who}"
        detail = f" depuis {heure}" if heure else ""

    return ft.Container(
        bgcolor=badge_color,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color="#FFFFFF", size=14),
                ft.Text(
                    f"{label}{detail}",
                    color="#FFFFFF",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    no_wrap=True,
                ),
            ],
            spacing=6,
            tight=True,
        ),
    )
