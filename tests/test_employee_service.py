from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
from app.services.employee_service import (
    create_employee,
    list_employee_site_assignments,
    list_employees,
    list_former_employees,
    mark_employee_departure,
    restore_employee,
    update_employee,
)
from app.services.employee_import_service import import_employees_from_file
from app.services.xlsx_service import write_simple_xlsx


class EmployeeServiceTest(unittest.TestCase):
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

    def test_departure_moves_employee_out_of_active_list_and_can_restore(self) -> None:
        employee_id = self._create_employee()

        mark_employee_departure(
            employee_id,
            "demissionne",
            "2026-05-12",
            "Depart volontaire",
        )

        active_ids = {row["id_employe"] for row in list_employees()}
        former = list_former_employees()

        self.assertNotIn(employee_id, active_ids)
        self.assertEqual(len(former), 1)
        self.assertEqual(former[0]["departure_type"], "demissionne")
        self.assertEqual(former[0]["departure_date"], "2026-05-12")
        self.assertEqual(former[0]["departure_comment"], "Depart volontaire")

        restore_employee(employee_id)

        self.assertIn(employee_id, {row["id_employe"] for row in list_employees()})
        self.assertEqual(list_former_employees(), [])

    def test_import_employees_from_csv_creates_records_with_badges(self) -> None:
        source = Path(self.temp_dir.name) / "employees.csv"
        source.write_text(
            "\n".join(
                [
                    "Matricule;Nom;Prenom;Badge;Fonction;Site;Shift;Type employe",
                    "EMP-001;Diallo;Awa;B-001;Operateur;OREZONE;DAY;national",
                    "EMP-002;Smith;John;B-002;Officier HSE;OREZONE;Night Shift;expatriate",
                ]
            ),
            encoding="utf-8",
        )

        result = import_employees_from_file(source)
        employees = list_employees()

        self.assertEqual(result["created"], 2)
        self.assertEqual(result["errors"], [])
        self.assertEqual({row["matricule"] for row in employees}, {"EMP-001", "EMP-002"})
        self.assertEqual({row["numero_badge"] for row in employees}, {"B-001", "B-002"})

    def test_badge_expiration_is_saved_and_reported(self) -> None:
        employee_id = self._create_employee_with_badge("B-900", "2097-12-31")

        employee = next(row for row in list_employees() if row["id_employe"] == employee_id)

        self.assertEqual(employee["date_expiration_badge"], "2099-12-31")
        self.assertEqual(employee["badge_validity_state"], "valid")

    def test_site_update_creates_assignment_history(self) -> None:
        employee_id = self._create_employee()
        with connection.db_session() as db:
            department = db.execute("SELECT id_department FROM departments WHERE nom = 'Geologie'").fetchone()
            cursor = db.execute(
                """
                INSERT INTO sites(nom, localisation, department_id, actif)
                VALUES ('TEST_SITE', 'Site test', ?, 1)
                """,
                (department["id_department"],),
            )
            site_id = int(cursor.lastrowid)
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()

        update_employee(
            employee_id,
            {
                "nom_complet": "Ancien Employe",
                "fonction_id": fonction["id_fonction"],
                "site_id": site_id,
                "shift_id": shift["id_shift"],
                "type_employe": "national",
                "statut_employe": "actif",
            },
        )

        assignments = list_employee_site_assignments(employee_id)

        self.assertEqual(assignments[0]["site"], "TEST_SITE")
        self.assertIsNone(assignments[0]["date_fin"])
        self.assertEqual(len(assignments), 2)
        self.assertIsNotNone(assignments[1]["date_fin"])

    def test_expired_badge_is_reported_as_risk(self) -> None:
        employee_id = self._create_employee_with_badge("B-901", "2018-01-01")

        employee = next(row for row in list_employees() if row["id_employe"] == employee_id)

        self.assertEqual(employee["badge_validity_state"], "expired")
        self.assertIn("2020-01-01", employee["badge_validity_label"])

    def test_import_employees_rejects_unknown_reference_without_creating_records(self) -> None:
        source = Path(self.temp_dir.name) / "employees.csv"
        source.write_text(
            "\n".join(
                [
                    "Nom;Prenom;Fonction;Site;Shift",
                    "Invalid;Employee;Fonction inconnue;OREZONE;DAY",
                ]
            ),
            encoding="utf-8",
        )

        result = import_employees_from_file(source)

        self.assertEqual(result["created"], 0)
        self.assertEqual(list_employees(), [])
        self.assertIn("Fonction introuvable", result["errors"][0]["message"])

    def test_import_employees_from_xlsx(self) -> None:
        source = Path(self.temp_dir.name) / "employees.xlsx"
        write_simple_xlsx(
            source,
            "Employes",
            ["Matricule", "Nom complet", "Badge", "Fonction", "Site", "Shift"],
            [["EMP-003", "Xlsx Employe", "B-003", "Operateur", "OREZONE", "DAY"]],
        )

        result = import_employees_from_file(source)

        self.assertEqual(result["created"], 1)
        self.assertEqual(list_employees()[0]["nom_complet"], "Xlsx Employe")

    def _create_employee(self) -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        return create_employee(
            {
                "nom_complet": "Ancien Employe",
                "fonction_id": fonction["id_fonction"],
                "site_id": site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": "national",
                "statut_employe": "actif",
            }
        )

    def _create_employee_with_badge(self, badge: str, issue_date: str) -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
        return create_employee(
            {
                "nom_complet": f"Badge {badge}",
                "fonction_id": fonction["id_fonction"],
                "site_id": site["id_site"],
                "shift_id": shift["id_shift"],
                "type_employe": "national",
                "statut_employe": "actif",
                "numero_badge": badge,
                "statut_badge": "valide",
                "date_remise": issue_date,
            }
        )


if __name__ == "__main__":
    unittest.main()
