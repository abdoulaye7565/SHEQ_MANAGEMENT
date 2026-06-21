from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.employee_service import create_employee
from app.services.ppe_service import (
    assign_multiple_ppe,
    assign_ppe,
    assign_required_ppe,
    create_ppe_item,
    get_ppe_summary,
    list_ppe_compliance,
    list_ppe_inspections,
    list_ppe_requirements,
    list_ppe_alerts,
    list_ppe_assignments,
    list_ppe_items,
    prepare_required_ppe_assignment,
    record_ppe_inspection,
    record_stock_movement,
    refresh_ppe_alerts,
    return_ppe_assignment,
    save_ppe_requirement,
)


class PpeServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()
        self.employee_id = self._create_employee()
        self.type_id = self._first_type()

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_create_item_records_initial_stock_and_low_stock_alert(self) -> None:
        initial_summary = get_ppe_summary()
        item_id = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Casque test",
                "taille": "M",
                "etat": "neuf",
                "quantite_initiale": 2,
                "seuil_minimum": 3,
            }
        )

        item = next(row for row in list_ppe_items() if row["id_epi"] == item_id)
        summary = get_ppe_summary()

        self.assertEqual(item["quantite_disponible"], 2)
        self.assertEqual(item["seuil_minimum"], 3)
        self.assertEqual(summary["stock_total"], initial_summary["stock_total"] + 2)
        self.assertTrue(any(row["id_epi"] == item_id for row in list_ppe_alerts()))

    def test_stock_movement_assignment_and_return(self) -> None:
        item_id = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Gants test",
                "etat": "neuf",
                "quantite_initiale": 5,
                "seuil_minimum": 1,
            }
        )

        record_stock_movement(
            {
                "epi_id": item_id,
                "type_mouvement": "entree",
                "quantite": 2,
                "motif": "Reception",
            }
        )
        assignment_id = assign_ppe(
            {
                "employe_id": self.employee_id,
                "epi_id": item_id,
                "quantite": 3,
                "date_remise": "2026-05-12",
            }
        )

        item = next(row for row in list_ppe_items() if row["id_epi"] == item_id)
        self.assertEqual(item["quantite_disponible"], 4)
        self.assertEqual(len(list_ppe_assignments(active_only=True)), 1)

        return_ppe_assignment(assignment_id, "2026-05-12", "retourne")
        item = next(row for row in list_ppe_items() if row["id_epi"] == item_id)
        self.assertEqual(item["quantite_disponible"], 7)
        self.assertEqual(list_ppe_assignments(active_only=True), [])

    def test_assignment_rejects_insufficient_stock(self) -> None:
        item_id = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Lunettes test",
                "etat": "neuf",
                "quantite_initiale": 1,
                "seuil_minimum": 0,
            }
        )

        with self.assertRaisesRegex(ValueError, "Stock insuffisant"):
            assign_ppe(
                {
                    "employe_id": self.employee_id,
                    "epi_id": item_id,
                    "quantite": 2,
                    "date_remise": "2026-05-12",
                }
            )

    def test_requirement_creates_compliance_gap_until_ppe_is_assigned(self) -> None:
        save_ppe_requirement(
            {
                "fonction_id": self.function_id,
                "type_epi_id": self.type_id,
                "quantite": 1,
                "obligatoire": True,
            }
        )

        self.assertEqual(len(list_ppe_requirements()), 1)
        self.assertTrue(any(row["statut"] == "manquant" for row in list_ppe_compliance()))

    def test_required_assignment_preparation_and_atomic_block(self) -> None:
        self._clear_type_stock()
        save_ppe_requirement(
            {
                "fonction_id": self.function_id,
                "type_epi_id": self.type_id,
                "quantite": 2,
                "obligatoire": True,
            }
        )
        item_id = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Stock obligatoire insuffisant",
                "quantite_initiale": 1,
                "seuil_minimum": 0,
            }
        )

        prepared = prepare_required_ppe_assignment(self.employee_id)
        self.assertEqual(prepared[0]["statut"], "stock_insuffisant")
        with self.assertRaisesRegex(ValueError, "Dotation bloquee"):
            assign_required_ppe(self.employee_id, "2026-05-12")

        item = next(row for row in list_ppe_items() if row["id_epi"] == item_id)
        self.assertEqual(item["quantite_disponible"], 1)
        self.assertEqual(list_ppe_assignments(active_only=True), [])

    def test_required_assignment_assigns_all_available_items(self) -> None:
        self._clear_type_stock()
        save_ppe_requirement(
            {
                "fonction_id": self.function_id,
                "type_epi_id": self.type_id,
                "quantite": 2,
                "obligatoire": True,
            }
        )
        item_id = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Stock obligatoire disponible",
                "quantite_initiale": 3,
                "seuil_minimum": 0,
            }
        )

        assignment_ids = assign_required_ppe(self.employee_id, "2026-05-12")
        self.assertEqual(len(assignment_ids), 1)
        item = next(row for row in list_ppe_items() if row["id_epi"] == item_id)
        self.assertEqual(item["quantite_disponible"], 1)
        self.assertEqual(prepare_required_ppe_assignment(self.employee_id)[0]["statut"], "deja_attribue")

    def test_refresh_alerts_deduplicates_open_alerts(self) -> None:
        item_id = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Stock nul alerte unique",
                "quantite_initiale": 0,
                "seuil_minimum": 1,
            }
        )

        first = refresh_ppe_alerts()
        second = refresh_ppe_alerts()
        self.assertEqual(len(first), len(second))
        with connection.db_session() as db:
            row = db.execute(
                """
                SELECT COUNT(*) AS total
                FROM alertes
                WHERE type_alerte = ? AND statut = 'ouverte'
                """,
                (f"ppe_auto:stock_nul:{item_id}",),
            ).fetchone()
        self.assertEqual(int(row["total"]), 1)

    def test_multiple_ppe_assignment_is_atomic(self) -> None:
        first = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Multiple first",
                "quantite_initiale": 3,
                "seuil_minimum": 0,
            }
        )
        second = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Multiple second",
                "quantite_initiale": 2,
                "seuil_minimum": 0,
            }
        )
        ids = assign_multiple_ppe(
            self.employee_id,
            [{"epi_id": first, "quantite": 1}, {"epi_id": second, "quantite": 2}],
            "2026-05-10",
            "Dotation complete",
        )
        self.assertEqual(len(ids), 2)
        active = list_ppe_assignments(active_only=True)
        self.assertEqual(sum(row["quantite"] for row in active), 3)

    def test_record_inspection_tracks_next_control(self) -> None:
        item_id = create_ppe_item(
            {
                "type_epi_id": self.type_id,
                "nom": "Inspection item",
                "etat": "neuf",
                "quantite_initiale": 1,
                "seuil_minimum": 0,
            }
        )

        record_ppe_inspection(
            {
                "epi_id": item_id,
                "date_inspection": "2026-05-12",
                "statut": "a_surveiller",
                "prochaine_inspection": "2026-06-12",
                "inspecteur": "HSE",
            }
        )

        inspections = list_ppe_inspections()
        self.assertEqual(inspections[0]["epi"], "Inspection item")
        self.assertEqual(inspections[0]["prochaine_inspection"], "2026-06-12")

    def _first_type(self) -> int:
        with connection.db_session() as db:
            row = db.execute("SELECT id_type_epi FROM types_epi ORDER BY id_type_epi LIMIT 1").fetchone()
            return int(row["id_type_epi"])

    def _clear_type_stock(self) -> None:
        with connection.db_session() as db:
            db.execute(
                """
                UPDATE stock_epi
                SET quantite_disponible = 0
                WHERE epi_id IN (SELECT id_epi FROM epi WHERE type_epi_id = ?)
                """,
                (self.type_id,),
            )

    def _create_employee(self) -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        self.function_id = int(fonction["id_fonction"])
        return create_employee(
            {
                "nom_complet": "Employe EPI",
                "fonction_id": fonction["id_fonction"],
                "site_id": site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": "national",
                "statut_employe": "actif",
            }
        )


if __name__ == "__main__":
    unittest.main()
