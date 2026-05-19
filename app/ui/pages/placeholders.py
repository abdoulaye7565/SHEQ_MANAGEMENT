import flet as ft

from app.ui.components.module_header import module_header
from app.ui.theme import MUTED


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
                bgcolor="#FFFFFF",
                border=ft.border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=20,
                content=ft.Text(
                    "Module pret a developper dans la prochaine etape.",
                    size=14,
                    color=MUTED,
                ),
            ),
        ],
        spacing=22,
        expand=True,
    )
