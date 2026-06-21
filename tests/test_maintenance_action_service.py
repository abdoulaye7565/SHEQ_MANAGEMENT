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
    get_maintenance_cost_analysis,
    get_maintenance_management_snapshot,
    list_action_tracker,
    list_equipment_maintenance,
    list_maintenance_equipment_catalog,
    list_maintenance_action_alerts,
    list_maintenance_inspections,
    list_maintenance_parts,
    list_maintenance_plans,
    list_risk_assessments,
    record_maintenance_inspection,
    save_maintenance_part,
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

    def test_synchronized_management_views_share_equipment_plan_alerts_and_costs(self) -> None:
        create_equipment_maintenance(
            {
                "equipment_code": "SYNC-01",
                "equipment_name": "Synchronous loader",
                "category": "Heavy equipment",
                "site_id": self.site_id,
                "responsible_employee_id": self.employee_id,
                "maintenance_type": "preventive",
                "priority": "haute",
                "status": "planifiee",
                "planned_date": "2026-12-01",
                "current_odometer": 4900,
                "last_service_odometer": 4000,
                "service_interval_km": 1000,
                "cost": 75000,
            }
        )

        equipment = list_maintenance_equipment_catalog()
        plans = list_maintenance_plans()
        costs = get_maintenance_cost_analysis()
        snapshot = get_maintenance_management_snapshot()

        self.assertTrue(any(row["equipment_code"] == "SYNC-01" for row in equipment))
        self.assertTrue(any(row["equipment_code"] == "SYNC-01" and row["next_due_odometer"] == 5000 for row in plans))
        self.assertEqual(costs["total"], 75000)
        self.assertIn("summary", snapshot)
        self.assertIn("alerts", snapshot)
        self.assertIn("costs", snapshot)

    def test_parts_and_inspections_feed_synchronized_alerts(self) -> None:
        part_id = save_maintenance_part(
            {
                "reference": "FLT-01",
                "name": "Filtre huile",
                "category": "Filtration",
                "quantity_available": 2,
                "minimum_threshold": 5,
                "unit_cost": 15000,
            }
        )
        inspection_id = record_maintenance_inspection(
            {
                "equipment_code": "RIG-ALERT",
                "equipment_name": "Foreuse alerte",
                "inspection_date": "2026-01-01",
                "status": "critique",
                "next_inspection_date": "2026-01-02",
                "inspector": "Maintenance",
                "observations": "Fuite hydraulique",
            }
        )

        parts = list_maintenance_parts()
        inspections = list_maintenance_inspections()
        alerts = list_maintenance_action_alerts()

        self.assertTrue(any(row["id_part"] == part_id and row["low_stock"] == 1 for row in parts))
        self.assertTrue(
            any(row["id_inspection"] == inspection_id and row["computed_status"] == "critique" for row in inspections)
        )
        self.assertTrue(any(row["id_part"] == part_id for row in alerts["parts"]))
        self.assertTrue(any(row["id_inspection"] == inspection_id for row in alerts["inspections"]))
        self.assertTrue(
            any(
                row["source"] == "Maintenance Inspection"
                and f"#{inspection_id}" in row["title"]
                and row["priority"] == "critique"
                for row in list_action_tracker()
            )
        )

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
        with zipfile.ZipFile(maintenance_export) as workbook:
            dashboard = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            sheet = workbook.read("xl/worksheets/sheet2.xml").decode("utf-8")
            styles = workbook.read("xl/styles.xml").decode("utf-8")
            workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
            chart = workbook.read("xl/charts/chart1.xml").decode("utf-8")
        self.assertIn("TABLEAU DE BORD EXECUTIF", dashboard)
        self.assertIn("EQUIPMENT MAINTENANCE REGISTER", sheet)
        self.assertIn("Next maintenance km", sheet)
        self.assertIn("Prepared by", sheet)
        self.assertIn("<f>IF(AND(L", sheet)
        self.assertIn("DUE KM", sheet)
        self.assertNotIn("DATEVALUE", sheet)
        self.assertIn("FF1E3A8A", styles)
        self.assertIn("Dashboard Executif", workbook_xml)
        self.assertIn("Registre Maintenance", workbook_xml)
        self.assertIn("Analyse Couts Alertes", workbook_xml)
        self.assertIn("Controle Signatures", workbook_xml)
        self.assertIn("EVOLUTION DES COUTS ET RETARDS", chart)

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

    def test_high_residual_risk_creates_action_tracker_item(self) -> None:
        risk_id = create_risk_assessment(
            {
                "activity": "Fuel transfer",
                "task": "Refuelling mobile equipment",
                "hazard": "Hydrocarbon spill",
                "risk_event": "Fire or environmental release",
                "consequences": "Major damage",
                "existing_controls": "Extinguisher and spill kit",
                "site_id": self.site_id,
                "owner_employee_id": self.employee_id,
                "probability_initial": 4,
                "severity_initial": 5,
                "hierarchy_control": "engineering",
                "additional_controls": "Install drip tray and dedicated exclusion zone",
                "probability_residual": 5,
                "severity_residual": 5,
                "status": "in_progress",
                "due_date": "2026-06-10",
            }
        )

        actions = list_action_tracker()

        self.assertTrue(
            any(
                row["source"] == "Risk Assessment"
                and f"#{risk_id}" in row["title"]
                and row["priority"] == "critique"
                for row in actions
            )
        )

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
