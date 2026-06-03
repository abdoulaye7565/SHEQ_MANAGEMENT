from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from app.db import connection
from app.services.employee_service import create_employee
from app.services.maintenance_action_service import (
    create_action,
    create_equipment_maintenance,
    create_risk_assessment,
    export_action_tracker_xlsx,
    export_equipment_maintenance_xlsx,
    export_risk_assessments_xlsx,
    get_maintenance_action_summary,
    list_action_tracker,
    list_equipment_maintenance,
    list_maintenance_action_alerts,
    list_risk_assessments,
    update_action,
    update_equipment_maintenance,
    update_risk_assessment,
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

    def test_oil_change_maintenance_is_due_by_odometer(self) -> None:
        maintenance_id = create_equipment_maintenance(
            {
                "equipment_code": "TRUCK-01",
                "equipment_name": "Service truck",
                "category": "Vehicle",
                "site_id": self.site_id,
                "responsible_employee_id": self.employee_id,
                "maintenance_type": "oil_change",
                "priority": "haute",
                "status": "planifiee",
                "planned_date": "2026-12-01",
                "current_odometer": 12500,
                "last_service_odometer": 10000,
                "service_interval_km": 2500,
            }
        )

        row = list_equipment_maintenance()[0]
        summary = get_maintenance_action_summary()
        alerts = list_maintenance_action_alerts()["maintenance"]

        self.assertEqual(row["id_maintenance"], maintenance_id)
        self.assertEqual(row["maintenance_type"], "oil_change")
        self.assertEqual(row["next_due_odometer"], 12500)
        self.assertEqual(row["remaining_km"], 0)
        self.assertEqual(row["status"], "en_retard")
        self.assertEqual(summary["maintenance_odometer_due"], 1)
        self.assertTrue(any(item["id_maintenance"] == maintenance_id for item in alerts))

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

    def test_risk_assessment_calculates_levels_and_exports(self) -> None:
        risk_id = create_risk_assessment(
            {
                "activity": "Drilling operations",
                "task": "Rod handling",
                "hazard": "Rotating equipment",
                "risk_event": "Hand caught in rotation zone",
                "consequences": "Serious injury",
                "existing_controls": "Toolbox talk, guarding, supervision",
                "site_id": self.site_id,
                "owner_employee_id": self.employee_id,
                "probability_initial": 4,
                "severity_initial": 5,
                "hierarchy_control": "engineering",
                "additional_controls": "Improve guarding and exclusion zone",
                "probability_residual": 2,
                "severity_residual": 4,
                "status": "in_progress",
                "due_date": "2026-06-10",
                "review_date": "2026-06-20",
            }
        )

        row = list_risk_assessments()[0]
        summary = get_maintenance_action_summary()

        self.assertEqual(row["id_risk"], risk_id)
        self.assertEqual(row["risk_initial"], 20)
        self.assertEqual(row["level_initial"], "critical")
        self.assertEqual(row["risk_residual"], 8)
        self.assertEqual(row["level_residual"], "medium")
        self.assertEqual(summary["risks_open"], 1)
        self.assertEqual(summary["risks_high_initial"], 1)

        update_risk_assessment(risk_id, {**row, "status": "controlled", "review_date": "2026-06-25"})
        self.assertEqual(list_risk_assessments()[0]["status"], "controlled")

        output = export_risk_assessments_xlsx()
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 0)
        with zipfile.ZipFile(output) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            styles = workbook.read("xl/styles.xml").decode("utf-8")
        self.assertIn("Risk assessment summary", sheet)
        self.assertIn("ISO hierarchy", sheet)
        self.assertIn("Prepared by", sheet)
        self.assertIn("Approved by", sheet)
        self.assertIn("Critical", sheet)
        self.assertIn("FFDC2626", styles)
        self.assertIn("FFFBBF24", styles)

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
