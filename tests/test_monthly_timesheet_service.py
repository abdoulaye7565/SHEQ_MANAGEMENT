from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from app.db import connection
from app.services import attendance_export_service
from app.services.break_service import create_break
from app.services.employee_service import create_employee
from app.services.monthly_timesheet_service import get_monthly_10h_timesheet, list_monthly_timesheet_days
from app.services.attendance_service import save_attendance_day
from app.services.timesheet_service import set_day_activity


class MonthlyTimeSheetServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        self.original_exports_dir = attendance_export_service.EXPORTS_DIR
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        attendance_export_service.EXPORTS_DIR = Path(self.temp_dir.name) / "exports"
        connection.initialize_database()
        self.employee_id = self._create_employee("Monthly Employee")

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        attendance_export_service.EXPORTS_DIR = self.original_exports_dir
        self.temp_dir.cleanup()

    def test_period_runs_from_first_to_twenty_fifth(self) -> None:
        days = list_monthly_timesheet_days("2026-05")

        self.assertEqual(days[0], "2026-05-01")
        self.assertEqual(days[-1], "2026-05-25")
        self.assertEqual(len(days), 25)

    def test_monthly_timesheet_counts_ten_hours_and_sunday_rest(self) -> None:
        save_attendance_day(
            "2026-05-01",
            {self.employee_id: {"statut_presence": "present", "heure_entree": "07:00", "heure_sortie": "17:00"}},
        )
        timesheet = get_monthly_10h_timesheet("2026-05")
        row = timesheet["rows"][0]
        cells = {cell["date"]: cell for cell in row["cells"]}

        self.assertEqual(cells["2026-05-01"]["status"], "worked")
        self.assertEqual(cells["2026-05-01"]["hours"], 10)
        self.assertEqual(cells["2026-05-02"]["status"], "unfilled")
        self.assertEqual(cells["2026-05-03"]["status"], "rest")
        self.assertEqual(cells["2026-05-03"]["label"], "R")
        self.assertEqual(row["hours"], 10)

    def test_monthly_timesheet_marks_holidays_as_eight_hours(self) -> None:
        set_day_activity("2026-05-04", has_drilling=False, day_type="holiday")

        timesheet = get_monthly_10h_timesheet("2026-05")
        row = timesheet["rows"][0]
        cells = {cell["date"]: cell for cell in row["cells"]}

        self.assertEqual(cells["2026-05-04"]["status"], "holiday")
        self.assertEqual(cells["2026-05-04"]["label"], "8H")
        self.assertEqual(cells["2026-05-04"]["hours"], 8)

    def test_break_normal_and_annual_have_separate_statuses(self) -> None:
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-05-04",
                "date_fin": "2026-05-04",
                "statut": "planifie",
            }
        )
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "annual",
                "date_debut": "2026-05-05",
                "date_fin": "2026-05-05",
                "statut": "planifie",
            }
        )

        timesheet = get_monthly_10h_timesheet("2026-05")
        cells = {cell["date"]: cell for cell in timesheet["rows"][0]["cells"]}

        self.assertEqual(cells["2026-05-04"]["status"], "normal_break")
        self.assertEqual(cells["2026-05-04"]["label"], "B")
        self.assertEqual(cells["2026-05-05"]["status"], "annual_break")
        self.assertEqual(cells["2026-05-05"]["label"], "BA")
        self.assertEqual(timesheet["summary"]["normal_break_days"], 1)
        self.assertEqual(timesheet["summary"]["annual_break_days"], 1)

    def test_break_spanning_period_colors_every_break_day(self) -> None:
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-04-28",
                "date_fin": "2026-05-10",
                "statut": "en_cours",
            }
        )

        timesheet = get_monthly_10h_timesheet("2026-05")
        row = timesheet["rows"][0]
        cells = {cell["date"]: cell for cell in row["cells"]}

        for day in range(1, 11):
            cell = cells[f"2026-05-{day:02d}"]
            self.assertEqual(cell["status"], "normal_break")
            self.assertEqual(cell["label"], "B")
            self.assertEqual(cell["break_start"], "2026-04-28")
            self.assertEqual(cell["break_end"], "2026-05-10")
        self.assertEqual(cells["2026-05-11"]["status"], "unfilled")
        self.assertEqual(row["normal_break_days"], 10)

    def test_permission_after_three_days_becomes_absence_in_monthly_timesheet(self) -> None:
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "permission",
                "date_debut": "2026-05-01",
                "date_fin": "2026-05-04",
                "statut": "planifie",
            }
        )

        timesheet = get_monthly_10h_timesheet("2026-05")
        row = timesheet["rows"][0]
        cells = {cell["date"]: cell for cell in row["cells"]}

        self.assertEqual(cells["2026-05-01"]["status"], "normal_break")
        self.assertEqual(cells["2026-05-02"]["status"], "normal_break")
        self.assertEqual(cells["2026-05-03"]["status"], "normal_break")
        self.assertEqual(cells["2026-05-04"]["status"], "absent")
        self.assertEqual(cells["2026-05-04"]["label"], "A")
        self.assertEqual(row["normal_break_days"], 3)
        self.assertEqual(row["hours"], 0)

    def test_export_monthly_timesheet_xlsx_contains_status_labels(self) -> None:
        self._create_employee("Expat Employee", employee_type="expatriate")
        save_attendance_day(
            "2026-05-01",
            {self.employee_id: {"statut_presence": "present", "heure_entree": "07:00", "heure_sortie": "17:00"}},
        )
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "annual",
                "date_debut": "2026-05-05",
                "date_fin": "2026-05-05",
                "statut": "planifie",
            }
        )

        output = attendance_export_service.export_monthly_10h_timesheet_xlsx("2026-05")

        self.assertTrue(output.exists())
        with zipfile.ZipFile(output) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            styles = workbook.read("xl/styles.xml").decode("utf-8")
        self.assertIn("10h", sheet)
        self.assertIn("MONTHLY TIMESHEET", sheet)
        self.assertIn(">R<", sheet)
        self.assertIn(">BA<", sheet)
        self.assertIn("EXPATRIES - RESERVE", sheet)
        self.assertIn("Expat Employee", sheet)
        self.assertIn('width="6.5"', sheet)
        self.assertIn('horizontal="center" vertical="center"', styles)
        self.assertIn('textRotation="45"', styles)
        self.assertIn('left style="thin"', styles)

    def _create_employee(self, name: str, employee_type: str = "national") -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites WHERE nom = 'SYAMA'").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        return create_employee(
            {
                "nom_complet": name,
                "fonction_id": fonction["id_fonction"],
                "site_id": site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": employee_type,
                "statut_employe": "actif",
            }
        )


if __name__ == "__main__":
    unittest.main()
