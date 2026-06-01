from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.employee_service import create_employee
from app.services.maintenance_action_service import (
    create_action,
    create_equipment_maintenance,
    export_action_tracker_xlsx,
    export_equipment_maintenance_xlsx,
    get_maintenance_action_summary,
    list_action_tracker,
    list_equipment_maintenance,
    update_action,
    update_equipment_maintenance,
)


class MaintenanceActionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()
        self.employee_id = self._create_employee()
        self.site_id = self._first_site()

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_maintenance_lifecycle_and_late_status(self) -> None:
        maintenance_id = create_equipment_maintenance(
            {
                "equipment_code": "RIG-01",
                "equipment_name": "Foreuse RC",
                "category": "Drilling",
                "site_id": self.site_id,
                "responsible_employee_id": self.employee_id,
                "maintenance_type": "preventive",
                "priority": "critique",
                "status": "planifiee",
                "planned_date": "2026-01-01",
                "cost": 1250,
            }
        )

        rows = list_equipment_maintenance()
        summary = get_maintenance_action_summary()

        self.assertEqual(rows[0]["id_maintenance"], maintenance_id)
        self.assertEqual(rows[0]["status"], "en_retard")
        self.assertEqual(summary["maintenance_open"], 1)
        self.assertEqual(summary["maintenance_late"], 1)
        self.assertEqual(summary["maintenance_critical"], 1)

        update_equipment_maintenance(
            maintenance_id,
            {
                **rows[0],
                "status": "terminee",
                "planned_date": "2026-01-01",
                "completed_date": "2026-01-03",
            },
        )
        self.assertEqual(list_equipment_maintenance()[0]["status"], "terminee")

    def test_action_tracker_lifecycle_and_export(self) -> None:
        action_id = create_action(
            {
                "source": "Inspection",
                "title": "Corriger garde-corps",
                "description": "Action terrain",
                "site_id": self.site_id,
                "owner_employee_id": self.employee_id,
                "priority": "haute",
                "status": "en_cours",
                "due_date": "2026-01-01",
                "progress": 40,
            }
        )

        rows = list_action_tracker()
        self.assertEqual(rows[0]["id_action"], action_id)
        self.assertEqual(rows[0]["status"], "en_retard")

        update_action(
            action_id,
            {
                **rows[0],
                "status": "terminee",
                "due_date": "2026-01-01",
                "closed_date": "2026-01-02",
            },
        )
        self.assertEqual(list_action_tracker()[0]["progress"], 100)

        maintenance_export = export_equipment_maintenance_xlsx()
        action_export = export_action_tracker_xlsx()
        self.assertTrue(maintenance_export.exists())
        self.assertTrue(action_export.exists())
        self.assertGreater(maintenance_export.stat().st_size, 0)
        self.assertGreater(action_export.stat().st_size, 0)

    def _first_site(self) -> int:
        with connection.db_session() as db:
            row = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            return int(row["id_site"])

    def _create_employee(self) -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        return create_employee(
            {
                "nom_complet": "Responsable Maintenance",
                "fonction_id": fonction["id_fonction"],
                "site_id": site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": "national",
                "statut_employe": "actif",
            }
        )


if __name__ == "__main__":
    unittest.main()
