from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.alert_service import (
    create_manual_alert,
    delete_manual_alert,
    get_alert_summary,
    list_alerts,
    update_manual_alert_status,
)
from app.services.employee_service import create_employee
from app.services.ppe_service import create_ppe_item
from app.services.training_service import create_training


class AlertServiceTest(unittest.TestCase):
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

    def test_manual_alert_lifecycle(self) -> None:
        alert_id = create_manual_alert("Incident terrain", "Zone a securiser", "haut")

        open_alerts = list_alerts(source="manual")
        self.assertTrue(any(row["id"] == f"manual:{alert_id}" for row in open_alerts))

        update_manual_alert_status(alert_id, "traitee")
        treated = list_alerts(source="manual", statut="traitee")
        self.assertTrue(any(row["id"] == f"manual:{alert_id}" for row in treated))

        delete_manual_alert(alert_id)
        all_manual = list_alerts(source="manual", statut="all")
        self.assertFalse(any(row["id"] == f"manual:{alert_id}" for row in all_manual))

    def test_generated_alerts_include_ppe_training_and_badge_signals(self) -> None:
        employee_id = self._create_employee_without_badge()
        training_type_id = self._first_id("training_types", "id_training_type")
        type_epi_id = self._first_id("types_epi", "id_type_epi")

        create_training(
            {
                "employe_id": employee_id,
                "type_training_id": training_type_id,
                "date_formation": "2020-01-01",
                "structure_responsable": "HSE",
            }
        )
        create_ppe_item(
            {
                "type_epi_id": type_epi_id,
                "nom": "Test low stock gloves",
                "etat": "neuf",
                "quantite_initiale": 0,
                "seuil_minimum": 2,
            }
        )

        alerts = list_alerts(statut="ouverte")
        messages = [row["message"] for row in alerts]
        summary = get_alert_summary()

        self.assertTrue(any("badge" in message.lower() for message in messages))
        self.assertTrue(any("expire" in message.lower() for message in messages))
        self.assertTrue(any("Stock" in message for message in messages))
        self.assertGreaterEqual(summary["open"], 3)

    def test_generated_alerts_include_expired_badges(self) -> None:
        self._create_employee_with_badge("BAD-EXP", "2018-01-01")

        alerts = list_alerts(statut="ouverte")
        messages = [row["message"] for row in alerts]

        self.assertTrue(any("BAD-EXP" in message and "expire" in message.lower() for message in messages))

    def _create_employee_without_badge(self) -> int:
        return create_employee(
            {
                "nom_complet": "Alert Test",
                "fonction_id": self._first_id("fonctions", "id_fonction"),
                "site_id": self._first_id("sites", "id_site"),
                "shift_id": self._first_shift_id(),
                "type_employe": "national",
                "statut_employe": "actif",
            }
        )

    def _create_employee_with_badge(self, badge: str, issue_date: str) -> int:
        return create_employee(
            {
                "nom_complet": "Badge Alert",
                "fonction_id": self._first_id("fonctions", "id_fonction"),
                "site_id": self._first_id("sites", "id_site"),
                "shift_id": self._first_shift_id(),
                "type_employe": "national",
                "statut_employe": "actif",
                "numero_badge": badge,
                "statut_badge": "valide",
                "date_remise": issue_date,
            }
        )

    def _first_id(self, table: str, column: str) -> int:
        with connection.db_session() as db:
            row = db.execute(f"SELECT {column} FROM {table} ORDER BY {column} LIMIT 1").fetchone()
            return int(row[column])

    def _first_shift_id(self) -> int:
        with connection.db_session() as db:
            row = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
            return int(row["id_shift"])


if __name__ == "__main__":
    unittest.main()
