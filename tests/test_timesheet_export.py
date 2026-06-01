from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from app.config import EXPORTS_DIR
from app.db import connection
from app.services.attendance_export_service import (
    export_timesheet_all_employees_xls,
    export_timesheet_employee_xls,
    export_timesheet_xls,
)
from app.services.attendance_service import save_attendance_day
from app.services.employee_service import create_employee
from app.services.timesheet_service import set_day_activity


class TimeSheetExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        self.original_exports_dir = EXPORTS_DIR
        connection.DATA_DIR = Path(self.temp_dir.name) / "data"
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()
        self.employee_id = self._create_employee()
        self.second_employee_id = self._create_employee("Second Export Employe")

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_export_timesheet_xls_contains_colors_and_legend(self) -> None:
        set_day_activity("2026-04-21", True)
        set_day_activity("2026-05-01", False, "Jour chome", day_type="holiday")
        save_attendance_day(
            "2026-04-21",
            {
                self.employee_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "15:00",
                },
                self.second_employee_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "15:00",
                }
            },
        )

        output = export_timesheet_xls("2026-04")
        self.assertEqual(output.suffix, ".xlsx")
        with zipfile.ZipFile(output) as workbook:
            content = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            styles = workbook.read("xl/styles.xml").decode("utf-8")

        self.assertTrue(output.name.startswith("timesheet_orezone_2026-04"))
        self.assertIn("Legende", content)
        self.assertIn("MLE", content)
        self.assertIn("NOM", content)
        self.assertIn("PRENOMS", content)
        self.assertIn("R = OFF DAYS", content)
        self.assertIn("8 = JOURS FERIES &amp; CHOMES PAYES", content)
        self.assertIn("Jour ferie ou chome paye = 8H", content)
        self.assertIn("ANNUAL LEAVE", content)
        self.assertIn("FF00A6D6", styles)
        self.assertIn("Prepared by", content)
        self.assertIn("Checked by", content)
        self.assertIn("Approved by", content)
        self.assertIn("Export Employe", content)
        self.assertIn("Second Export Employe", content)

    def test_export_timesheet_all_employees_creates_one_file_per_employee(self) -> None:
        output_dir = export_timesheet_all_employees_xls("2026-04")
        files = sorted(output_dir.glob("*.xlsx"))

        self.assertTrue(output_dir.name.startswith("timesheets_individuels_orezone_2026-04"))
        self.assertEqual(len(files), 2)
        contents = []
        for path in files:
            with zipfile.ZipFile(path) as workbook:
                contents.append(workbook.read("xl/worksheets/sheet1.xml").decode("utf-8"))
        self.assertTrue(any("Export Employe" in content for content in contents))
        self.assertTrue(any("Second Export Employe" in content for content in contents))

    def test_export_timesheet_employee_uses_print_layout(self) -> None:
        output = export_timesheet_employee_xls("2026-04", self.employee_id)
        self.assertEqual(output.suffix, ".xlsx")
        with zipfile.ZipFile(output) as workbook:
            content = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

        self.assertIn("Prepared by", content)
        self.assertIn("Export Employe", content)
        self.assertIn("Legende", content)

    def _create_employee(self, name: str = "Export Employe") -> int:
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
