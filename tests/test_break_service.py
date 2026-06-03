from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.break_service import create_break, list_breaks, postpone_break, update_break_status
from app.services.employee_service import create_employee


class BreakServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()
        self.employee_id = self._create_employee("Break Planned")

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_confirm_cancel_and_postpone_planned_break(self) -> None:
        break_id = create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-06-10",
                "date_fin": "2026-06-16",
                "statut": "planifie",
            }
        )

        update_break_status(break_id, "en_cours")
        record = self._record(break_id)
        self.assertEqual(record["statut"], "en_cours")

        postpone_break(break_id, "2026-06-20")
        record = self._record(break_id)
        self.assertEqual(record["statut"], "planifie")
        self.assertEqual(record["date_debut"], "2026-06-20")
        self.assertEqual(record["date_fin"], "2026-06-26")

        update_break_status(break_id, "annule")
        self.assertEqual(self._record(break_id)["statut"], "annule")

    def test_employee_cannot_have_two_breaks_on_same_period(self) -> None:
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-06-10",
                "date_fin": "2026-06-16",
                "statut": "planifie",
            }
        )

        with self.assertRaisesRegex(ValueError, "deja un break"):
            create_break(
                {
                    "employe_id": self.employee_id,
                    "type_break": "annual",
                    "date_debut": "2026-06-14",
                    "date_fin": "2026-06-20",
                    "statut": "planifie",
                }
            )

    def test_postpone_break_cannot_overlap_another_break(self) -> None:
        first_id = create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-06-10",
                "date_fin": "2026-06-16",
                "statut": "planifie",
            }
        )
        second_id = create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-06-25",
                "date_fin": "2026-06-30",
                "statut": "planifie",
            }
        )

        with self.assertRaisesRegex(ValueError, "deja un break"):
            postpone_break(second_id, "2026-06-12")

        self.assertEqual(self._record(first_id)["date_debut"], "2026-06-10")
        self.assertEqual(self._record(second_id)["date_debut"], "2026-06-25")

    def _record(self, break_id: int) -> dict[str, object]:
        return next(record for record in list_breaks() if int(record["id_break"]) == break_id)

    def _create_employee(self, name: str) -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        return create_employee(
            {
                "nom_complet": name,
                "fonction_id": fonction["id_fonction"],
                "site_id": site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": "national",
                "statut_employe": "actif",
            }
        )


if __name__ == "__main__":
    unittest.main()
