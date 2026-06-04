from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.automation_service import run_startup_automations


class AutomationServiceTest(unittest.TestCase):
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

    def test_startup_automations_return_operational_summary(self) -> None:
        result = run_startup_automations()

        self.assertIn("attendance_ready", result)
        self.assertIn("maintenance", result)
        self.assertIn("toolbox_assigned", result)
        self.assertIn("warnings", result)


if __name__ == "__main__":
    unittest.main()
