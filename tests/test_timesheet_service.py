from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.db import connection
from app.services.attendance_service import save_attendance_day
from app.services.break_service import create_break
from app.services.employee_service import create_employee
from app.services.timesheet_service import (
    get_timesheet,
    get_timesheet_period,
    get_timesheet_lock,
    list_timesheet_audit,
    list_timesheet_days,
    lock_timesheet_month,
    set_day_activity,
    set_day_activity_range,
    unlock_timesheet_month,
    update_timesheet_day_status,
)


class TimeSheetServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()
        self.employee_id = self._create_employee("Time Sheet Employe")

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_period_runs_from_21_to_20_next_month(self) -> None:
        period = get_timesheet_period("2026-04")
        days = list_timesheet_days("2026-04")

        self.assertEqual(period["start"], "2026-04-21")
        self.assertEqual(period["end"], "2026-05-20")
        self.assertEqual(days[0], "2026-04-21")
        self.assertEqual(days[-1], "2026-05-20")

    def test_timesheet_marks_weeks_from_period_start(self) -> None:
        timesheet = get_timesheet("2026-04")
        days = timesheet["days"]

        self.assertEqual(days[0]["week_index"], 1)
        self.assertTrue(days[0]["week_start"])
        self.assertEqual(days[6]["week_index"], 1)
        self.assertFalse(days[6]["week_start"])
        self.assertEqual(days[7]["week_index"], 2)
        self.assertTrue(days[7]["week_start"])

    def test_timesheet_calculates_drilling_standard_rest_and_break_days(self) -> None:
        set_day_activity("2026-04-21", True)
        set_day_activity("2026-04-22", False)
        save_attendance_day(
            "2026-04-21",
            {
                self.employee_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "19:00",
                }
            },
        )
        save_attendance_day(
            "2026-04-22",
            {
                self.employee_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "15:00",
                }
            },
        )
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-04-23",
                "date_fin": "2026-04-23",
                "statut": "planifie",
            }
        )

        timesheet = get_timesheet("2026-04")
        row = timesheet["rows"][0]
        cells = {cell["date"]: cell for cell in row["cells"]}

        self.assertEqual(cells["2026-04-21"]["status"], "worked_drilling")
        self.assertEqual(cells["2026-04-21"]["hours"], 12)
        self.assertEqual(cells["2026-04-22"]["status"], "worked_standard")
        self.assertEqual(cells["2026-04-22"]["hours"], 8)
        self.assertEqual(cells["2026-04-23"]["status"], "break")
        self.assertEqual(cells["2026-04-23"]["hours"], 8)
        self.assertEqual(cells["2026-04-24"]["status"], "unfilled")
        self.assertEqual(row["worked_days"], 2)
        self.assertEqual(row["break_days"], 1)
        self.assertEqual(row["hours"], 28)
        self.assertEqual(row["drilling_hours"], 12)
        self.assertEqual(row["standard_hours"], 16)
        self.assertEqual(row["weekly_hours"]["S1"], 28)

    def test_drilling_day_counts_twelve_hours_for_each_present_employee(self) -> None:
        set_day_activity("2026-04-21", True)
        save_attendance_day(
            "2026-04-21",
            {
                self.employee_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "15:00",
                }
            },
        )

        timesheet = get_timesheet("2026-04")
        cell = timesheet["rows"][0]["cells"][0]

        self.assertEqual(cell["status"], "worked_drilling")
        self.assertEqual(cell["hours"], 12)
        self.assertEqual(timesheet["rows"][0]["hours"], 12)

    def test_expatriate_employee_is_excluded_from_timesheet(self) -> None:
        expatriate_id = self._create_employee("Expat Employee", employee_type="expatriate")
        set_day_activity("2026-04-21", True)
        save_attendance_day(
            "2026-04-21",
            {
                self.employee_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "19:00",
                },
                expatriate_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "19:00",
                },
            },
        )

        timesheet = get_timesheet("2026-04")
        employee_ids = [row["employee"]["id_employe"] for row in timesheet["rows"]]

        self.assertIn(self.employee_id, employee_ids)
        self.assertNotIn(expatriate_id, employee_ids)
        with self.assertRaisesRegex(ValueError, "expatries"):
            update_timesheet_day_status(expatriate_id, "2026-04-21", "present")

    def test_timesheet_can_be_scoped_to_one_site(self) -> None:
        with connection.db_session() as db:
            department = db.execute("SELECT id_department FROM departments WHERE nom = 'Geologie'").fetchone()
            cursor = db.execute(
                """
                INSERT INTO sites(nom, localisation, department_id, actif)
                VALUES ('SECOND_SITE', 'Second site', ?, 1)
                """,
                (department["id_department"],),
            )
            second_site_id = int(cursor.lastrowid)
        second_employee_id = self._create_employee("Second Site Employee", site_id=second_site_id)
        set_day_activity("2026-04-21", True)
        update_timesheet_day_status(self.employee_id, "2026-04-21", "present")
        update_timesheet_day_status(second_employee_id, "2026-04-21", "present")

        site_timesheet = get_timesheet("2026-04", site_id=second_site_id)
        employee_ids = [row["employee"]["id_employe"] for row in site_timesheet["rows"]]

        self.assertEqual(site_timesheet["site"]["nom"], "SECOND_SITE")
        self.assertEqual(employee_ids, [second_employee_id])

    def test_site_timesheet_only_counts_days_assigned_to_that_site(self) -> None:
        employee_id = self._create_employee("Transfer Employee")
        with connection.db_session() as db:
            department = db.execute("SELECT id_department FROM departments WHERE nom = 'Geologie'").fetchone()
            cursor = db.execute(
                """
                INSERT INTO sites(nom, localisation, department_id, actif)
                VALUES ('TRANSFER_SITE', 'Transfer site', ?, 1)
                """,
                (department["id_department"],),
            )
            transfer_site_id = int(cursor.lastrowid)
            db.execute(
                """
                UPDATE employee_site_assignments
                SET date_debut = '2026-04-21', date_fin = '2026-04-21'
                WHERE employe_id = ?
                """,
                (employee_id,),
            )
            db.execute(
                """
                INSERT INTO employee_site_assignments(employe_id, site_id, date_debut, motif)
                VALUES (?, ?, '2026-04-22', 'Transfert test')
                """,
                (employee_id, transfer_site_id),
            )
        set_day_activity("2026-04-21", True)
        set_day_activity("2026-04-22", True)
        update_timesheet_day_status(employee_id, "2026-04-21", "present")
        update_timesheet_day_status(employee_id, "2026-04-22", "present")

        timesheet = get_timesheet("2026-04", site_id=transfer_site_id)
        cells = {cell["date"]: cell for cell in timesheet["rows"][0]["cells"]}

        self.assertEqual(cells["2026-04-21"]["status"], "not_assigned")
        self.assertEqual(cells["2026-04-22"]["status"], "worked_drilling")
        self.assertEqual(timesheet["rows"][0]["hours"], 12)

    def test_update_timesheet_day_status_updates_source_data(self) -> None:
        set_day_activity("2026-04-21", True)

        update_timesheet_day_status(self.employee_id, "2026-04-21", "present")
        timesheet = get_timesheet("2026-04")
        cell = timesheet["rows"][0]["cells"][0]
        self.assertEqual(cell["status"], "worked_drilling")
        self.assertEqual(cell["hours"], 12)

        update_timesheet_day_status(self.employee_id, "2026-04-21", "rest")
        timesheet = get_timesheet("2026-04")
        cell = timesheet["rows"][0]["cells"][0]
        self.assertEqual(cell["status"], "rest")
        self.assertEqual(cell["hours"], 0)

        update_timesheet_day_status(self.employee_id, "2026-04-21", "permission")
        timesheet = get_timesheet("2026-04")
        cell = timesheet["rows"][0]["cells"][0]
        self.assertEqual(cell["status"], "break")
        self.assertEqual(cell["label"], "P")

    def test_cannot_fill_future_timesheet_day(self) -> None:
        with self.assertRaisesRegex(ValueError, "pas encore arrive"):
            update_timesheet_day_status(self.employee_id, "2026-05-21", "present")

        with self.assertRaisesRegex(ValueError, "pas encore arrive"):
            set_day_activity("2026-05-21", True)

    def test_bulk_activity_lock_and_audit(self) -> None:
        updated = set_day_activity_range("2026-04-21", "2026-04-23", True)
        self.assertEqual(updated, 3)
        timesheet = get_timesheet("2026-04")
        self.assertEqual(timesheet["summary"]["drilling_days"], 3)

        today = date.today().isoformat()
        set_day_activity_range("2026-04-24", min(today, "2026-05-20"), True)
        for day in list_timesheet_days("2026-04"):
            if day > today:
                continue
            update_timesheet_day_status(self.employee_id, day, "rest")
        lock_timesheet_month("2026-04", commentaire="Validation superviseur")
        self.assertIsNotNone(get_timesheet_lock("2026-04"))
        with self.assertRaisesRegex(ValueError, "verrouille"):
            update_timesheet_day_status(self.employee_id, "2026-04-21", "present")

        unlock_timesheet_month("2026-04")
        update_timesheet_day_status(self.employee_id, "2026-04-21", "present")
        audit_rows = list_timesheet_audit("2026-04")
        self.assertTrue(any(row["action"] == "lock" for row in audit_rows))
        self.assertTrue(any(row["action"] == "unlock" for row in audit_rows))
        self.assertTrue(any(row["action"] == "status" for row in audit_rows))

    def _create_employee(self, name: str, employee_type: str = "national", site_id: int | None = None) -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        return create_employee(
            {
                "nom_complet": name,
                "fonction_id": fonction["id_fonction"],
                "site_id": site_id or site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": employee_type,
                "statut_employe": "actif",
            }
        )


if __name__ == "__main__":
    unittest.main()
