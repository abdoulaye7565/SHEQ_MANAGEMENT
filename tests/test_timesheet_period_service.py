from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.db import connection
from app.services.attendance_service import lock_attendance_day, save_attendance_day
from app.services.employee_service import create_employee
from app.services.timesheet_period_service import (
    TIMESHEET_1_25,
    TIMESHEET_21_20,
    get_active_timesheet_period,
    get_timesheet_sync_status,
    validate_timesheet_export_payload,
)


class TimeSheetPeriodServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()
        self.employee_id = self._create_employee()

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_active_21_20_period_switches_on_twenty_first(self) -> None:
        before_switch = get_active_timesheet_period(TIMESHEET_21_20, date(2026, 6, 20))
        after_switch = get_active_timesheet_period(TIMESHEET_21_20, date(2026, 6, 21))

        self.assertEqual(before_switch["start"], "2026-05-21")
        self.assertEqual(before_switch["end"], "2026-06-20")
        self.assertEqual(after_switch["start"], "2026-06-21")
        self.assertEqual(after_switch["end"], "2026-07-20")

    def test_active_1_25_period_prepares_next_month_after_twenty_fifth(self) -> None:
        current = get_active_timesheet_period(TIMESHEET_1_25, date(2026, 6, 25))
        prepared = get_active_timesheet_period(TIMESHEET_1_25, date(2026, 6, 26))

        self.assertEqual(current["start"], "2026-06-01")
        self.assertEqual(current["end"], "2026-06-25")
        self.assertEqual(prepared["start"], "2026-07-01")
        self.assertEqual(prepared["end"], "2026-07-25")

    def test_sync_status_reports_presence_and_validation(self) -> None:
        save_attendance_day(
            "2026-06-04",
            {self.employee_id: {"statut_presence": "present", "heure_entree": "06:00", "heure_sortie": "14:00"}},
        )
        lock_attendance_day("2026-06-04")

        status = get_timesheet_sync_status(TIMESHEET_1_25, "2026-06")

        self.assertEqual(status["source"], "presences")
        self.assertEqual(status["presence_records"], 1)
        self.assertEqual(status["days_with_data"], 1)
        self.assertEqual(status["validated_days"], 1)
        self.assertTrue(status["synchronized"])

    def test_export_validation_rejects_cell_outside_period(self) -> None:
        payload = {
            "period": {"month": "2026-06", "start": "2026-06-01", "end": "2026-06-25"},
            "rows": [{"cells": [{"date": "2026-06-26"}]}],
        }

        with self.assertRaisesRegex(ValueError, "hors de la periode"):
            validate_timesheet_export_payload(payload, TIMESHEET_1_25)

    def _create_employee(self) -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites WHERE nom = 'SYAMA'").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        return create_employee(
            {
                "nom_complet": "Period Employee",
                "fonction_id": fonction["id_fonction"],
                "site_id": site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": "national",
                "statut_employe": "actif",
            }
        )


if __name__ == "__main__":
    unittest.main()
