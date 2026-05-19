from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.employee_service import create_employee
from app.services.ppe_service import (
    assign_ppe,
    create_ppe_item,
    get_ppe_summary,
    list_ppe_compliance,
    list_ppe_inspections,
    list_ppe_requirements,
    list_ppe_alerts,
    list_ppe_assignments,
    list_ppe_items,
    record_ppe_inspection,
    record_stock_movement,
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
