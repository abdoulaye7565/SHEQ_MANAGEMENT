from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.employee_service import create_employee
from app.services.report_service import generate_report, get_report_summary, list_report_definitions


class ReportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name) / "data"
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_report_catalog_contains_operational_reports(self) -> None:
        keys = {row["key"] for row in list_report_definitions()}
        summary = get_report_summary()

        self.assertIn("attendance_excel", keys)
        self.assertIn("training_matrix", keys)
        self.assertIn("timesheet", keys)
        self.assertIn("timesheet_employee", keys)
        self.assertIn("monthly_10h_timesheet", keys)
        self.assertIn("toolbox_talk", keys)
        self.assertIn("ppe_inventory", keys)
        self.assertIn("alerts", keys)
        self.assertGreaterEqual(summary["reports"], 13)

    def test_generate_employee_report_creates_file(self) -> None:
        self._create_employee()

        output = generate_report("employees")

        self.assertTrue(output.exists())
        self.assertIn("list_of_orezone_employee", output.name)

    def test_generate_timesheet_reports_create_monthly_files(self) -> None:
        employee_id = self._create_employee()
        second_employee_id = self._create_employee("Second Report Employe")

        global_output = generate_report("timesheet", {"month": "2026-04"})
        employee_output = generate_report(
            "timesheet_employee",
            {"month": "2026-04", "employee_id": employee_id},
        )
        selected_output = generate_report(
            "timesheet_employee",
            {"month": "2026-04", "employee_ids": [employee_id, second_employee_id]},
        )

        self.assertTrue(global_output.exists())
        self.assertTrue(employee_output.exists())
        self.assertTrue(selected_output.exists())
        self.assertIn("timesheet_orezone_2026-04", global_output.name)
        self.assertIn("timesheet_orezone_2026-04", employee_output.name)
        self.assertTrue(selected_output.name.startswith("timesheets_selection_orezone_2026-04"))
        self.assertEqual(len(list(selected_output.glob("*.xls"))), 2)

    def test_generate_new_exportable_reports_create_files(self) -> None:
        self._create_employee()

        monthly_output = generate_report("monthly_10h_timesheet", {"month": "2026-05"})
        toolbox_output = generate_report("toolbox_talk", {"month": "2026-05"})

        self.assertTrue(monthly_output.exists())
        self.assertTrue(toolbox_output.exists())
        self.assertIn("timesheet_10h_1_25", monthly_output.name)
        self.assertIn("toolbox_talk_meeting_2026-05", toolbox_output.name)

    def test_unknown_report_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Rapport inconnu"):
            generate_report("unknown")

    def _create_employee(self, name: str = "Report Employe") -> int:
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
