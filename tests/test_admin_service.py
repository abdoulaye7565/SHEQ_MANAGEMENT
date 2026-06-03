from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import connection
import app.services.admin_service as admin_service
from app.services.admin_service import (
    authenticate_user,
    create_database_backup,
    create_user,
    get_admin_summary,
    list_admin_audit,
    list_backups,
    list_role_permissions,
    list_roles,
    list_users,
    get_role_modules,
    reset_user_password,
    restore_database_backup,
    update_role_modules,
    update_user,
    update_user_status,
    verify_password,
)


class AdminServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        self.original_backups_dir = admin_service.BACKUPS_DIR
        root = Path(self.temp_dir.name)
        connection.DATA_DIR = root / "data"
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        admin_service.BACKUPS_DIR = root / "backups"
        connection.initialize_database()

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        admin_service.BACKUPS_DIR = self.original_backups_dir
        self.temp_dir.cleanup()

    def test_user_lifecycle_and_authentication(self) -> None:
        role_id = self._admin_role_id()
        user_id = create_user(
            {
                "username": "admin_test",
                "password": "Password123",
                "role_id": role_id,
                "statut": "actif",
            }
        )

        authenticated = authenticate_user("admin_test", "Password123")
        self.assertEqual(authenticated["id_user"], user_id)
        self.assertEqual(authenticated["role"], "Administrateur")

        create_user(
            {
                "username": "backup_admin",
                "password": "Password123",
                "role_id": role_id,
                "statut": "actif",
            }
        )
        update_user(user_id, {"username": "admin_ops", "role_id": role_id, "statut": "actif"})
        reset_user_password(user_id, "NewPassword123")
        update_user_status(user_id, "inactif")

        self.assertEqual(list_users("admin_ops")[0]["statut"], "inactif")
        with self.assertRaisesRegex(ValueError, "inactif"):
            authenticate_user("admin_ops", "NewPassword123")

    def test_password_hash_is_not_plain_text(self) -> None:
        user_id = create_user(
            {
                "username": "hash_test",
                "password": "Password123",
                "role_id": self._admin_role_id(),
            }
        )
        with connection.db_session() as db:
            row = db.execute("SELECT password_hash FROM utilisateurs WHERE id_user = ?", (user_id,)).fetchone()
        self.assertNotEqual(row["password_hash"], "Password123")
        self.assertTrue(verify_password("Password123", row["password_hash"]))

    def test_backup_creation_and_summary(self) -> None:
        output = create_database_backup("manual")
        summary = get_admin_summary()

        self.assertTrue(output.exists())
        self.assertIn("manual", output.name)
        self.assertEqual(len(list_backups()), 1)
        self.assertEqual(summary["backups"], 1)
        self.assertGreaterEqual(summary["roles"], 1)

    def test_restore_backup_creates_safety_copy(self) -> None:
        output = create_database_backup("restore_source")

        safety = restore_database_backup(output.name, changed_by="tester")

        self.assertTrue(safety.exists())
        self.assertIn("avant_restauration", safety.name)
        self.assertTrue(any(row["action"] == "restore_backup" for row in list_admin_audit()))

    def test_role_modules_limit_navigation_scope(self) -> None:
        admin_modules = get_role_modules("Administrateur")
        stock_modules = get_role_modules("Responsable stock")
        unknown_modules = get_role_modules("Role inconnu")

        self.assertIn("Admin", admin_modules)
        self.assertIn("ToolboxTalk", admin_modules)
        self.assertIn("Ppe", stock_modules)
        self.assertNotIn("Admin", stock_modules)
        self.assertEqual(unknown_modules, ["Dashboard"])

    def test_partial_admin_permissions_are_completed_by_migration(self) -> None:
        with connection.db_session() as db:
            admin_role = db.execute("SELECT id_role FROM roles WHERE nom = 'Administrateur'").fetchone()
            db.execute("DELETE FROM role_module_permissions WHERE role_id = ?", (admin_role["id_role"],))
            for module in ("ToolboxTalk", "TimeSheet", "Admin"):
                db.execute(
                    """
                    INSERT INTO role_module_permissions(role_id, module_key)
                    VALUES (?, ?)
                    """,
                    (admin_role["id_role"], module),
                )

        connection.initialize_database()

        admin_modules = get_role_modules("Administrateur")
        self.assertEqual(admin_modules, admin_service.ROLE_MODULES["Administrateur"])

    def test_role_permissions_can_be_updated_and_audited(self) -> None:
        stock_role_id = self._role_id("Responsable stock")

        update_role_modules(stock_role_id, ["Dashboard", "Alerts"], changed_by="tester")

        self.assertEqual(get_role_modules("Responsable stock"), ["Dashboard", "Alerts"])
        stock = next(row for row in list_role_permissions() if row["nom"] == "Responsable stock")
        self.assertEqual(stock["modules"], ["Dashboard", "Alerts"])
        self.assertTrue(
            any(row["action"] == "role_modules" and row["changed_by"] == "tester" for row in list_admin_audit())
        )

    def test_legacy_reports_permission_maps_to_alerts_reports(self) -> None:
        stock_role_id = self._role_id("Responsable stock")
        with connection.db_session() as db:
            db.execute("DELETE FROM role_module_permissions WHERE role_id = ?", (stock_role_id,))
            db.execute(
                """
                INSERT INTO role_module_permissions(role_id, module_key)
                VALUES (?, ?)
                """,
                (stock_role_id, "Reports"),
            )

        self.assertEqual(get_role_modules("Responsable stock"), ["Alerts"])

    def test_admin_role_keeps_admin_module(self) -> None:
        admin_role_id = self._role_id("Administrateur")

        with self.assertRaisesRegex(ValueError, "Administration"):
            update_role_modules(admin_role_id, ["Dashboard", "Alerts"])

    def test_last_active_admin_cannot_be_disabled_or_demoted(self) -> None:
        admin_role_id = self._role_id("Administrateur")
        stock_role_id = self._role_id("Responsable stock")
        user_id = create_user(
            {
                "username": "only_admin",
                "password": "Password123",
                "role_id": admin_role_id,
                "statut": "actif",
            }
        )

        with self.assertRaisesRegex(ValueError, "administrateur actif"):
            update_user_status(user_id, "inactif")

        with self.assertRaisesRegex(ValueError, "administrateur actif"):
            update_user(
                user_id,
                {"username": "only_admin", "role_id": stock_role_id, "statut": "actif"},
            )

    def test_admin_can_be_disabled_when_another_active_admin_exists(self) -> None:
        admin_role_id = self._role_id("Administrateur")
        first_id = create_user(
            {
                "username": "admin_one",
                "password": "Password123",
                "role_id": admin_role_id,
                "statut": "actif",
            }
        )
        create_user(
            {
                "username": "admin_two",
                "password": "Password123",
                "role_id": admin_role_id,
                "statut": "actif",
            }
        )

        update_user_status(first_id, "inactif")

        self.assertEqual(list_users("admin_one")[0]["statut"], "inactif")

    def _admin_role_id(self) -> int:
        return self._role_id("Administrateur")

    def _role_id(self, name: str) -> int:
        roles = list_roles()
        for role in roles:
            if role["nom"] == name:
                return int(role["id_role"])
        raise AssertionError(f"Role {name} introuvable")


if __name__ == "__main__":
    unittest.main()
