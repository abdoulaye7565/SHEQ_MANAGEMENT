from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.attendance_service import get_attendance_list, get_attendance_summary, save_attendance_day
from app.services.break_service import create_break
from app.services.employee_service import create_employee


class AttendanceServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_employee_on_break_cannot_be_marked_present(self) -> None:
        employee_id = self._create_employee("Break Attendance")
        create_break(
            {
                "employe_id": employee_id,
                "type_break": "break",
                "date_debut": "2026-05-10",
                "date_fin": "2026-05-20",
                "statut": "en_cours",
            }
        )

        with self.assertRaisesRegex(ValueError, "en break"):
            save_attendance_day(
                "2026-05-14",
                {
                    employee_id: {
                        "statut_presence": "present",
                        "heure_entree": "07:00",
                        "heure_sortie": "17:00",
                    }
                },
            )

        self.assertEqual(get_attendance_list("2026-05-14"), [])
        self.assertEqual(get_attendance_summary("2026-05-14")["present"], 0)

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
