import flet as ft

from app.ui.components.module_header import module_header
from app.ui.theme import MUTED

_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"
_DK_TRACK  = "#1A3050"


MODULE_DESCRIPTIONS = {
    "Employes et badges": "CRUD employes, matricules, badges uniques, filtres et fiche detaillee.",
    "Formations": "Saisie des formations, expiration automatique a 24 mois et statuts couleur.",
    "Matrice formation": "Vue globale employes x formations avec filtres par site, groupe et fonction.",
    "Presence": "Shifts, breaks, pointage journalier, total mensuel et controle des 12 heures.",
    "TimeSheet": "Calendrier mensuel des heures travaillees du 21 au 20.",
    "EPI et stock": "Catalogue EPI, stock, mouvements, seuils, remises et retours.",
    "Alertes": "Centralisation des alertes formation, presence, badge, stock et EPI requis.",
    "Rapports": "Exports PDF pour employes, formations, presence et stock.",
    "Administration": "Utilisateurs, roles, sauvegarde, restauration et historique.",
}


def placeholder_page(title: str) -> ft.Control:
    return ft.Column(
        controls=[
            module_header(title, MODULE_DESCRIPTIONS[title]),
            ft.Container(
                bgcolor=_DK_CARD,
                border=ft.border.all(1, _DK_BORDER),
                border_radius=8,
                padding=20,
                content=ft.Text(
                    "Module pret a developper dans la prochaine etape.",
                    size=14,
                    color=_DK_MUTED,
                ),
            ),
        ],
        spacing=22,
        expand=True,
    )
