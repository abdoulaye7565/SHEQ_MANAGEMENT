from __future__ import annotations

import tempfile
import unittest
import sqlite3
from pathlib import Path

from app.db import connection
from app.services.training_service import (
    create_training,
    create_training_type,
    create_trainings_for_employees,
    get_training_options,
    get_training_matrix,
    list_trainings,
    update_training,
    update_trainings_bulk,
)


class TrainingServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        connection.initialize_database()
        self.employee_id = self._create_employee()
        self.training_type_id = self._create_training_type(validity_months=12)

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_create_training_uses_two_year_validity_and_facilitator(self) -> None:
        training_id = create_training(
            {
                "employe_id": self.employee_id,
                "type_training_id": self.training_type_id,
                "date_formation": "2024-01-31",
                "facilitateur": "Awa Traore",
                "structure_responsable": "HSE",
            }
        )

        with connection.db_session() as db:
            row = db.execute(
                """
                SELECT date_expiration, facilitateur, structure_responsable
                FROM formations
                WHERE id_formation = ?
                """,
                (training_id,),
            ).fetchone()

        self.assertEqual(row["date_expiration"], "2026-01-31")
        self.assertEqual(row["facilitateur"], "Awa Traore")
        self.assertEqual(row["structure_responsable"], "HSE")

    def test_create_training_renews_existing_employee_training(self) -> None:
        first_id = create_training(
            {
                "employe_id": self.employee_id,
                "type_training_id": self.training_type_id,
                "date_formation": "2024-01-31",
                "facilitateur": "Initial",
                "structure_responsable": "HSE",
            }
        )
        renewed_id = create_training(
            {
                "employe_id": self.employee_id,
                "type_training_id": self.training_type_id,
                "date_formation": "2024-06-15",
                "facilitateur": "Renouvellement",
                "structure_responsable": "Operations",
            }
        )

        with connection.db_session() as db:
            rows = db.execute(
                """
                SELECT id_formation, date_debut, date_expiration, facilitateur, structure_responsable
                FROM formations
                WHERE employe_id = ? AND type_training_id = ?
                """,
                (self.employee_id, self.training_type_id),
            ).fetchall()

        self.assertEqual(renewed_id, first_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date_debut"], "2024-06-15")
        self.assertEqual(rows[0]["date_expiration"], "2026-06-15")
        self.assertEqual(rows[0]["facilitateur"], "Renouvellement")
        self.assertEqual(rows[0]["structure_responsable"], "Operations")

    def test_update_training_keeps_two_year_validity(self) -> None:
        training_id = create_training(
            {
                "employe_id": self.employee_id,
                "type_training_id": self.training_type_id,
                "date_formation": "2024-01-31",
                "facilitateur": "Initial",
                "structure_responsable": "HSE",
            }
        )
        longer_type_id = self._create_training_type(name="Validite ignoree", validity_months=36)

        update_training(
            training_id,
            {
                "employe_id": self.employee_id,
                "type_training_id": longer_type_id,
                "date_formation": "2024-02-29",
                "facilitateur": "Moussa Diallo",
                "structure_responsable": "Operations",
            },
        )

        with connection.db_session() as db:
            row = db.execute(
                """
                SELECT date_expiration, facilitateur, structure_responsable
                FROM formations
                WHERE id_formation = ?
                """,
                (training_id,),
            ).fetchone()

        self.assertEqual(row["date_expiration"], "2026-02-28")
        self.assertEqual(row["facilitateur"], "Moussa Diallo")
        self.assertEqual(row["structure_responsable"], "Operations")

    def test_bulk_update_keeps_employee_history_and_updates_selected_trainings(self) -> None:
        first_id = create_training(
            {
                "employe_id": self.employee_id,
                "type_training_id": self.training_type_id,
                "date_formation": "2024-01-31",
                "facilitateur": "Initial",
                "structure_responsable": "HSE",
            }
        )
        second_employee_id = self._create_employee("Second Employe")
        second_id = create_training(
            {
                "employe_id": second_employee_id,
                "type_training_id": self.training_type_id,
                "date_formation": "2024-02-15",
                "facilitateur": "Initial",
                "structure_responsable": "HSE",
            }
        )

        updated = update_trainings_bulk(
            [first_id, second_id],
            {
                "type_training_id": self.training_type_id,
                "date_formation": "2024-03-01",
                "facilitateur": "Formateur Groupe",
                "structure_responsable": "Operations",
            },
        )

        with connection.db_session() as db:
            rows = db.execute(
                """
                SELECT employe_id, date_debut, date_expiration, facilitateur, structure_responsable
                FROM formations
                WHERE id_formation IN (?, ?)
                ORDER BY id_formation
                """,
                (first_id, second_id),
            ).fetchall()

        self.assertEqual(updated, 2)
        self.assertEqual([row["employe_id"] for row in rows], [self.employee_id, second_employee_id])
        self.assertEqual({row["date_debut"] for row in rows}, {"2024-03-01"})
        self.assertEqual({row["date_expiration"] for row in rows}, {"2026-03-01"})
        self.assertEqual({row["facilitateur"] for row in rows}, {"Formateur Groupe"})
        self.assertEqual({row["structure_responsable"] for row in rows}, {"Operations"})

    def test_bulk_validate_multiple_trainings_for_multiple_employees(self) -> None:
        second_employee_id = self._create_employee("Second Employe")
        height_type_id = self._create_training_type(name="Travail en hauteur groupe test")
        underground_type_id = self._create_training_type(name="Underground groupe test")
        medical_type_id = self._create_training_type(name="Visite medicale groupe test")

        total = create_trainings_for_employees(
            {
                "employee_ids": [self.employee_id, second_employee_id],
                "training_type_ids": [height_type_id, underground_type_id, medical_type_id],
                "date_formation": "2024-05-10",
                "facilitateur": "Equipe HSE",
                "structure_responsable": "HSE",
            }
        )

        with connection.db_session() as db:
            rows = db.execute(
                """
                SELECT employe_id, type_training_id, date_debut, date_expiration, facilitateur, structure_responsable
                FROM formations
                WHERE employe_id IN (?, ?)
                  AND type_training_id IN (?, ?, ?)
                """,
                (self.employee_id, second_employee_id, height_type_id, underground_type_id, medical_type_id),
            ).fetchall()

        self.assertEqual(total, 6)
        self.assertEqual(len(rows), 6)
        self.assertEqual({row["date_debut"] for row in rows}, {"2024-05-10"})
        self.assertEqual({row["date_expiration"] for row in rows}, {"2026-05-10"})
        self.assertEqual({row["facilitateur"] for row in rows}, {"Equipe HSE"})

    def test_training_type_is_linked_to_department_and_available_for_bulk_selection(self) -> None:
        underground_id = create_training_type("Underground department test", "Operations")

        options = get_training_options()
        underground_option = next(item for item in options["training_types"] if item["value"] == underground_id)

        self.assertEqual(underground_option["department"], "Operations")

        create_training(
            {
                "employe_id": self.employee_id,
                "type_training_id": underground_id,
                "date_formation": "2024-05-10",
                "facilitateur": "Equipe HSE",
                "structure_responsable": "Operations",
            }
        )
        row = next(item for item in list_trainings("Underground department test") if item["type_training_id"] == underground_id)

        self.assertEqual(row["training_department"], "Operations")
        self.assertEqual(row["training_department_id"], underground_option["department_id"])

    def test_database_migration_adds_department_to_existing_training_types(self) -> None:
        legacy_path = connection.DATABASE_PATH
        connection.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if legacy_path.exists():
            legacy_path.unlink()
        legacy = sqlite3.connect(legacy_path)
        try:
            legacy.executescript(
                """
                CREATE TABLE training_types (
                    id_training_type INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL UNIQUE,
                    categorie TEXT,
                    validite_mois INTEGER NOT NULL DEFAULT 24,
                    actif INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                );
                INSERT INTO training_types(nom, categorie, validite_mois, actif)
                VALUES ('Legacy HSE', 'obligatoire', 24, 1);
                """
            )
            legacy.commit()
        finally:
            legacy.close()

        connection.initialize_database()

        with connection.db_session() as db:
            row = db.execute(
                """
                SELECT tt.department_id, td.nom AS department
                FROM training_types tt
                LEFT JOIN training_departments td ON td.id_department = tt.department_id
                WHERE tt.nom = 'Legacy HSE'
                """
            ).fetchone()

        self.assertEqual(row["department"], "HSE")

    def test_training_matrix_exposes_expiration_statistics(self) -> None:
        create_training(
            {
                "employe_id": self.employee_id,
                "type_training_id": self.training_type_id,
                "date_formation": "2024-01-31",
                "facilitateur": "Initial",
                "structure_responsable": "HSE",
            }
        )

        matrix = get_training_matrix()
        cell = next(
            cell
            for row in matrix["rows"]
            if row["employee"]["id_employe"] == self.employee_id
            for cell in row["cells"]
            if cell["type_training_id"] == self.training_type_id
        )

        self.assertEqual(cell["date_expiration"], "2026-01-31")
        self.assertIn("summary", matrix)
        self.assertIn("training_stats", matrix)
        self.assertGreaterEqual(matrix["summary"]["expired"], 1)

    def _create_employee(self, name: str = "Test Employe") -> int:
        with connection.db_session() as db:
            fonction = db.execute("SELECT id_fonction FROM fonctions ORDER BY id_fonction LIMIT 1").fetchone()
            site = db.execute("SELECT id_site FROM sites ORDER BY id_site LIMIT 1").fetchone()
            shift = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
            cursor = db.execute(
                """
                INSERT INTO employes (
                    nom_complet, fonction_id, site_id, shift_id, type_employe, statut
                ) VALUES (?, ?, ?, ?, 'national', 'actif')
                """,
                (name, fonction["id_fonction"], site["id_site"], shift["id_shift"]),
            )
            return int(cursor.lastrowid)

    def _create_training_type(self, name: str = "Validite 12 mois", validity_months: int = 12) -> int:
        with connection.db_session() as db:
            cursor = db.execute(
                """
                INSERT INTO training_types (nom, categorie, validite_mois, actif)
                VALUES (?, 'test', ?, 1)
                """,
                (name, validity_months),
            )
            return int(cursor.lastrowid)


if __name__ == "__main__":
    unittest.main()
