from __future__ import annotations

import tempfile
import unittest
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

from app.db import connection
from app.services.admin_service import create_user, list_roles
from app.services.break_service import create_break
from app.services.employee_service import create_employee
from app.services import mobile_sync_service


class MobileSyncServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        self.original_config_path = mobile_sync_service.MOBILE_SYNC_CONFIG_PATH
        root = Path(self.temp_dir.name)
        connection.DATA_DIR = root / "data"
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        mobile_sync_service.MOBILE_SYNC_CONFIG_PATH = root / "mobile_sync_config.json"
        connection.initialize_database()
        self.employee_id = self._create_employee()
        role_id = next(row["id_role"] for row in list_roles() if row["nom"] == "Officier HSE")
        create_user(
            {
                "username": "mobile.user",
                "password": "Mobile2026",
                "role_id": role_id,
                "statut": "actif",
            }
        )

    def tearDown(self) -> None:
        mobile_sync_service.stop_mobile_sync_server()
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        mobile_sync_service.MOBILE_SYNC_CONFIG_PATH = self.original_config_path
        self.temp_dir.cleanup()

    def test_mobile_settings_store_token_without_plain_text(self) -> None:
        settings = mobile_sync_service.save_mobile_sync_settings(
            {
                "enabled": False,
                "host": "0.0.0.0",
                "port": "8765",
                "token": "mobile-secret-token",
            }
        )

        stored = mobile_sync_service.MOBILE_SYNC_CONFIG_PATH.read_text(encoding="utf-8")

        self.assertTrue(settings["token_configured"])
        self.assertNotIn("mobile-secret-token", stored)

    def test_pairing_package_exports_url_and_token(self) -> None:
        mobile_sync_service.save_mobile_sync_settings(
            {
                "enabled": True,
                "host": "127.0.0.1",
                "port": "8765",
                "token": "pairing-token",
            }
        )

        package = mobile_sync_service.create_mobile_pairing_package()

        self.assertTrue(Path(package["path"]).exists())
        self.assertEqual(package["server_url"], "http://127.0.0.1:8765")
        self.assertEqual(package["token"], "pairing-token")

    def test_bootstrap_returns_field_referentials(self) -> None:
        bootstrap = mobile_sync_service.get_mobile_bootstrap("2026-06-04")

        self.assertEqual(bootstrap["server"], "OREZONE QHSE")
        self.assertEqual(bootstrap["date_presence"], "2026-06-04")
        self.assertTrue(bootstrap["sites"])
        self.assertTrue(any(row["id_employe"] == self.employee_id for row in bootstrap["employees"]))
        self.assertTrue(bootstrap["shift_templates"])

    def test_apply_mobile_sync_payload_updates_attendance_and_records_event(self) -> None:
        result = mobile_sync_service.apply_mobile_sync_payload(
            {
                "device_id": "phone-001",
                "device_name": "Telephone HSE",
                "attendances": [
                    {
                        "employee_id": self.employee_id,
                        "date_presence": "2026-06-04",
                        "status": "present",
                        "heure_entree": "06:00",
                        "heure_sortie": "14:00",
                    }
                ],
            }
        )

        with connection.db_session() as db:
            row = db.execute(
                """
                SELECT statut_presence, heure_entree, heure_sortie, heures_travaillees
                FROM presences
                WHERE employe_id = ? AND date_presence = '2026-06-04'
                """,
                (self.employee_id,),
            ).fetchone()
        events = mobile_sync_service.list_mobile_sync_events()

        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["applied"], 1)
        self.assertEqual(row["statut_presence"], "present")
        self.assertEqual(row["heure_entree"], "06:00")
        self.assertEqual(row["heure_sortie"], "14:00")
        self.assertEqual(float(row["heures_travaillees"]), 8)
        self.assertEqual(events[0]["device_id"], "phone-001")
        self.assertEqual(events[0]["status"], "applied")

    def test_mobile_sync_applies_valid_attendance_when_another_employee_is_on_break(self) -> None:
        valid_employee_id = self._create_employee("Mobile Valid Employee")
        create_break(
            {
                "employe_id": self.employee_id,
                "type_break": "break",
                "date_debut": "2026-06-03",
                "date_fin": "2026-06-10",
                "statut": "en_cours",
            }
        )

        result = mobile_sync_service.apply_mobile_sync_payload(
            {
                "device_id": "phone-partial",
                "device_name": "Telephone Terrain",
                "attendances": [
                    {
                        "local_id": 10,
                        "employee_id": self.employee_id,
                        "employee_name": "Employe en break",
                        "date_presence": "2026-06-04",
                        "status": "present",
                        "heure_entree": "06:00",
                        "heure_sortie": "14:00",
                    },
                    {
                        "local_id": 11,
                        "employee_id": valid_employee_id,
                        "employee_name": "Employe valide",
                        "date_presence": "2026-06-04",
                        "status": "present",
                        "heure_entree": "06:00",
                        "heure_sortie": "14:00",
                    },
                ],
            }
        )

        with connection.db_session() as db:
            valid_presence = db.execute(
                """
                SELECT statut_presence
                FROM presences
                WHERE employe_id = ? AND date_presence = '2026-06-04'
                """,
                (valid_employee_id,),
            ).fetchone()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["attendance_applied"], 1)
        self.assertEqual(result["accepted"]["attendance"], [11])
        self.assertIn("Employe en break", result["errors"][0])
        self.assertEqual(valid_presence["statut_presence"], "present")

    def test_apply_mobile_sync_payload_records_toolbox_and_maintenance(self) -> None:
        result = mobile_sync_service.apply_mobile_sync_payload(
            {
                "device_id": "phone-002",
                "device_name": "Telephone Superviseur",
                "toolbox_confirmations": [
                    {
                        "date_theme": "2026-06-04",
                        "theme": "PPE use / Port des EPI",
                        "facilitator": "Chef equipe",
                        "attendees_count": 12,
                        "comments": "Meeting realise au demarrage.",
                    }
                ],
                "maintenance_observations": [
                    {
                        "observation_date": "2026-06-04",
                        "equipment_label": "RIG-01 - Foreuse",
                        "priority": "haute",
                        "observation": "Fuite hydraulique observee sur flexible.",
                    }
                ],
            }
        )

        with connection.db_session() as db:
            toolbox = db.execute("SELECT * FROM mobile_toolbox_confirmations").fetchone()
            observation = db.execute("SELECT * FROM mobile_maintenance_observations").fetchone()
            action = db.execute("SELECT * FROM action_tracker WHERE source = 'Mobile Maintenance'").fetchone()

        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["toolbox_applied"], 1)
        self.assertEqual(result["maintenance_applied"], 1)
        self.assertEqual(toolbox["attendees_count"], 12)
        self.assertEqual(observation["priority"], "haute")
        self.assertIsNotNone(action)
        self.assertIn("RIG-01", action["title"])

    def test_blocked_mobile_device_cannot_sync(self) -> None:
        mobile_sync_service.apply_mobile_sync_payload(
            {
                "device_id": "phone-blocked",
                "device_name": "Telephone bloque",
                "attendances": [],
            }
        )
        mobile_sync_service.update_mobile_device_status("phone-blocked", "blocked")

        with self.assertRaisesRegex(mobile_sync_service.MobileSyncConfigurationError, "bloque"):
            mobile_sync_service.apply_mobile_sync_payload(
                {
                    "device_id": "phone-blocked",
                    "device_name": "Telephone bloque",
                    "attendances": [
                        {
                            "employee_id": self.employee_id,
                            "date_presence": "2026-06-04",
                            "status": "present",
                            "heure_entree": "06:00",
                            "heure_sortie": "14:00",
                        }
                    ],
                }
            )

        devices = mobile_sync_service.list_mobile_devices()
        events = mobile_sync_service.list_mobile_sync_events()

        self.assertEqual(devices[0]["status"], "blocked")
        self.assertTrue(any(row["status"] == "rejected" for row in events))

    def test_mobile_role_controls_profile_and_sync_capabilities(self) -> None:
        mobile_sync_service.apply_mobile_sync_payload(
            {
                "device_id": "phone-maintenance",
                "device_name": "Telephone Maintenance",
                "attendances": [],
            }
        )
        mobile_sync_service.update_mobile_device_role("phone-maintenance", "maintenance")

        bootstrap = mobile_sync_service.get_mobile_bootstrap("2026-06-04", device_id="phone-maintenance")
        profile = bootstrap["profile"]

        self.assertEqual(profile["role"], "maintenance")
        self.assertEqual(profile["capabilities"], ["dashboard", "maintenance", "alerts"])
        self.assertEqual(bootstrap["employees"], [])
        self.assertEqual(bootstrap["shift_templates"], [])
        self.assertEqual(bootstrap["toolbox_topic"], {})
        with self.assertRaisesRegex(
            mobile_sync_service.MobileSyncConfigurationError,
            "ne peut pas enregistrer les presences",
        ):
            mobile_sync_service.apply_mobile_sync_payload(
                {
                    "device_id": "phone-maintenance",
                    "device_name": "Telephone Maintenance",
                    "attendances": [
                        {
                            "employee_id": self.employee_id,
                            "date_presence": "2026-06-04",
                            "status": "present",
                        }
                    ],
                }
            )

        result = mobile_sync_service.apply_mobile_sync_payload(
            {
                "device_id": "phone-maintenance",
                "device_name": "Telephone Maintenance",
                "maintenance_observations": [
                    {
                        "local_id": 5,
                        "observation_date": "2026-06-04",
                        "equipment_label": "RIG-02",
                        "priority": "haute",
                        "observation": "Flexible a inspecter.",
                    }
                ],
            }
        )
        self.assertEqual(result["maintenance_applied"], 1)
        self.assertEqual(result["accepted"]["maintenance"], [5])

    def test_administrator_mobile_bootstrap_includes_timesheet(self) -> None:
        bootstrap = mobile_sync_service.get_mobile_bootstrap(
            "2026-06-04",
            device_id="phone-admin",
            user_role="Administrateur",
        )

        self.assertEqual(bootstrap["profile"]["role"], "admin")
        self.assertIn("timesheet", bootstrap["profile"]["capabilities"])
        self.assertIn("summary", bootstrap["timesheet"])
        self.assertIn("dashboard", bootstrap)

    def test_invalid_mobile_role_is_rejected(self) -> None:
        mobile_sync_service.apply_mobile_sync_payload(
            {
                "device_id": "phone-role",
                "device_name": "Telephone Role",
                "attendances": [],
            }
        )

        with self.assertRaisesRegex(mobile_sync_service.MobileSyncConfigurationError, "Role mobile invalide"):
            mobile_sync_service.update_mobile_device_role("phone-role", "administrator")

    def test_bootstrap_http_requires_device_identity(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = int(probe.getsockname()[1])
        mobile_sync_service.save_mobile_sync_settings(
            {
                "enabled": True,
                "host": "127.0.0.1",
                "port": port,
                "token": "http-test-token",
            }
        )
        url = f"http://127.0.0.1:{port}/api/mobile/bootstrap?date=2026-06-04"
        missing_device = urllib.request.Request(
            url,
            headers={"X-OREZONE-Mobile-Token": "http-test-token"},
        )
        with self.assertRaises(urllib.error.HTTPError) as rejected:
            urllib.request.urlopen(missing_device, timeout=5)
        self.assertEqual(rejected.exception.code, 401)
        rejected.exception.close()

        login = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/mobile/login",
            data=json.dumps({"username": "mobile.user", "password": "Mobile2026"}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-OREZONE-Mobile-Token": "http-test-token",
                "X-OREZONE-Device-Id": "phone-http",
                "X-OREZONE-Device-Name": "Telephone HTTP",
            },
            method="POST",
        )
        with urllib.request.urlopen(login, timeout=5) as response:
            session = json.loads(response.read().decode("utf-8"))["session_token"]

        identified = urllib.request.Request(
            url,
            headers={
                "X-OREZONE-Mobile-Token": "http-test-token",
                "X-OREZONE-Device-Id": "phone-http",
                "X-OREZONE-Device-Name": "Telephone HTTP",
                "X-OREZONE-Mobile-Session": session,
            },
        )
        with urllib.request.urlopen(identified, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["server"], "OREZONE QHSE")
        self.assertTrue(any(row["device_id"] == "phone-http" for row in mobile_sync_service.list_mobile_devices()))

    def test_mobile_user_session_is_bound_to_device(self) -> None:
        mobile_sync_service.apply_mobile_sync_payload(
            {"device_id": "phone-auth", "device_name": "Telephone Auth", "attendances": []}
        )
        session = mobile_sync_service.authenticate_mobile_user("phone-auth", "mobile.user", "Mobile2026")

        identity = mobile_sync_service.get_mobile_session_identity("phone-auth", session["session_token"])
        self.assertEqual(identity["username"], "mobile.user")
        with self.assertRaisesRegex(mobile_sync_service.MobileSyncConfigurationError, "Session mobile expiree"):
            mobile_sync_service.get_mobile_session_identity("another-phone", session["session_token"])

    def test_rate_limit_blocks_after_max_attempts(self) -> None:
        device_id = "phone-ratelimit"
        # Réinitialise les compteurs pour isolation
        mobile_sync_service._LOGIN_FAILURES.pop(device_id, None)

        for _ in range(mobile_sync_service._MAX_LOGIN_ATTEMPTS):
            mobile_sync_service._record_login_failure(device_id)

        self.assertTrue(mobile_sync_service._is_login_rate_limited(device_id))

    def test_rate_limit_cleared_on_success(self) -> None:
        device_id = "phone-clear"
        mobile_sync_service._LOGIN_FAILURES.pop(device_id, None)

        for _ in range(mobile_sync_service._MAX_LOGIN_ATTEMPTS - 1):
            mobile_sync_service._record_login_failure(device_id)

        self.assertFalse(mobile_sync_service._is_login_rate_limited(device_id))

        mobile_sync_service._clear_login_failures(device_id)
        self.assertFalse(mobile_sync_service._is_login_rate_limited(device_id))

    def test_rate_limit_http_returns_429_after_max_attempts(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = int(probe.getsockname()[1])
        mobile_sync_service.save_mobile_sync_settings(
            {"enabled": True, "host": "127.0.0.1", "port": port, "token": "rl-test-token"}
        )
        device_id = "phone-rl-http"
        mobile_sync_service._LOGIN_FAILURES.pop(device_id, None)
        for _ in range(mobile_sync_service._MAX_LOGIN_ATTEMPTS):
            mobile_sync_service._record_login_failure(device_id)

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/mobile/login",
            data=json.dumps({"username": "mobile.user", "password": "Mobile2026"}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-OREZONE-Mobile-Token": "rl-test-token",
                "X-OREZONE-Device-Id": device_id,
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 429)
        ctx.exception.close()

    def _create_employee(self, name: str = "Mobile Sync Tester") -> int:
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
