from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.equipment_check_service import (
    confirm_monthly_equipment_check,
    current_equipment_check_month,
    get_monthly_equipment_check_status,
    monthly_equipment_check_alert,
)


class EquipmentCheckServiceTest(unittest.TestCase):
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

    def test_monthly_equipment_check_alert_persists_until_confirmation(self) -> None:
        month = current_equipment_check_month()

        status = get_monthly_equipment_check_status(month)
        alert = monthly_equipment_check_alert()

        self.assertFalse(status["confirmed"])
        self.assertIsNotNone(alert)
        self.assertEqual(alert["type_alerte"], "Verification mensuelle des engins")

        confirm_monthly_equipment_check(month, confirmed_by="admin")
        confirmed = get_monthly_equipment_check_status(month)

        self.assertTrue(confirmed["confirmed"])
        self.assertEqual(confirmed["confirmed_by"], "admin")
        self.assertIsNone(monthly_equipment_check_alert())


if __name__ == "__main__":
    unittest.main()
