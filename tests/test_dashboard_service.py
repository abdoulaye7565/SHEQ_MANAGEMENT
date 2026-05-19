from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.db import connection
from app.services.attendance_service import save_attendance_day
from app.services.dashboard_service import get_dashboard_summary
from app.services.employee_service import create_employee, mark_employee_departure


class DashboardServiceTest(unittest.TestCase):
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

    def test_presence_today_counts_only_active_tracked_employees(self) -> None:
        date_presence = date.today().isoformat()
        active_id = self._create_employee("Actif Present")
        inactive_id = self._create_employee("Ancien Present")

        save_attendance_day(
            date_presence,
            {
                active_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "17:00",
                },
                inactive_id: {
                    "statut_presence": "present",
                    "heure_entree": "07:00",
                    "heure_sortie": "17:00",
                },
            },
        )
        mark_employee_departure(inactive_id, "demissionne", date_presence)

        summary = get_dashboard_summary()

        self.assertEqual(summary["employes"], 1)
        self.assertEqual(summary["presence_today"]["total"], 1)
        self.assertEqual(summary["presence_today"]["present"], 1)
        self.assertEqual(summary["presence_today"]["hours"], 10.0)
        self.assertEqual(len(summary["presence_trend"]), 14)
        self.assertIn("ppe", summary)
        self.assertIn("training", summary)
        self.assertIn("workforce_by_state", summary)
        self.assertIn("workforce_by_team", summary)
        self.assertIn("performance_indicators", summary)
        self.assertEqual(summary["workforce_at_work"], 1)
        self.assertEqual(summary["workforce_on_break"], 0)

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
