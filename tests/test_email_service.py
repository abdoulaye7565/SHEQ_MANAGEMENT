from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import email_service


class FakeSMTP:
    sent_messages = []

    def __init__(self, host: str, port: int, timeout: int = 25) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tls_started = False
        self.logged_in = False
        self.closed = False

    def starttls(self) -> None:
        self.tls_started = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = bool(username and password)

    def send_message(self, message) -> None:
        self.sent_messages.append(message)

    def quit(self) -> None:
        self.closed = True


class EmailServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = email_service.EMAIL_CONFIG_PATH
        email_service.EMAIL_CONFIG_PATH = Path(self.temp_dir.name) / "email_config.json"
        FakeSMTP.sent_messages = []

    def tearDown(self) -> None:
        email_service.EMAIL_CONFIG_PATH = self.original_path
        self.temp_dir.cleanup()

    def test_save_email_settings_marks_configuration_ready(self) -> None:
        settings = email_service.save_email_settings(
            {
                "enabled": True,
                "smtp_host": "smtp.office365.com",
                "smtp_port": "587",
                "use_tls": True,
                "sender_email": "qhse@example.com",
                "sender_name": "OREZONE QHSE",
                "password": "secret",
                "manager_email": "manager@example.com",
                "somisy_email": "somisy@example.com",
            }
        )

        self.assertTrue(settings["ready"])
        self.assertTrue(settings["password_configured"])
        self.assertEqual(settings["smtp_port"], 587)

    def test_send_timesheet_email_attaches_export(self) -> None:
        attachment = Path(self.temp_dir.name) / "timesheet.xlsx"
        attachment.write_bytes(b"xlsx")
        email_service.save_email_settings(
            {
                "enabled": True,
                "smtp_host": "smtp.office365.com",
                "smtp_port": "587",
                "use_tls": True,
                "sender_email": "qhse@example.com",
                "sender_name": "OREZONE QHSE",
                "password": "secret",
                "manager_email": "manager@example.com",
                "somisy_email": "somisy@example.com",
            }
        )

        with patch.object(email_service.smtplib, "SMTP", FakeSMTP):
            result = email_service.send_timesheet_email("TimeSheet 21-20", "2026-06", attachment)

        self.assertEqual(result["recipients"], ["manager@example.com", "somisy@example.com"])
        self.assertEqual(len(FakeSMTP.sent_messages), 1)
        message = FakeSMTP.sent_messages[0]
        self.assertIn("manager@example.com", message["To"])
        self.assertIn("timesheet.xlsx", str(message))

    def test_prepare_timesheet_outlook_draft_uses_configured_recipients(self) -> None:
        attachment = Path(self.temp_dir.name) / "timesheet.xlsx"
        attachment.write_bytes(b"xlsx")
        email_service.save_email_settings(
            {
                "enabled": False,
                "smtp_host": "",
                "smtp_port": "587",
                "sender_email": "",
                "password": "",
                "manager_email": "manager@example.com",
                "somisy_email": "somisy@example.com",
            }
        )

        with patch.object(email_service.subprocess, "Popen") as popen_mock:
            result = email_service.prepare_timesheet_outlook_draft("TimeSheet 1-25", "2026-06", attachment)

        self.assertEqual(result["recipients"], ["manager@example.com", "somisy@example.com"])
        command = popen_mock.call_args.args[0]
        self.assertIn("powershell.exe", command[0])
        self.assertIn(str(attachment.resolve()), command)

    def test_prepare_timesheet_whatsapp_share_opens_configured_targets(self) -> None:
        attachment = Path(self.temp_dir.name) / "timesheet.xlsx"
        attachment.write_bytes(b"xlsx")
        email_service.save_email_settings(
            {
                "enabled": False,
                "smtp_host": "",
                "smtp_port": "587",
                "sender_email": "",
                "password": "",
                "manager_whatsapp": "+225 07 00 00 00 00",
                "somisy_whatsapp": "2250100000000",
            }
        )

        with patch.object(email_service.webbrowser, "open") as open_mock:
            result = email_service.prepare_timesheet_whatsapp_share("TimeSheet 21-20", "2026-06", attachment)

        self.assertEqual(result["targets"], ["2250700000000", "2250100000000"])
        self.assertEqual(open_mock.call_count, 2)
        first_url = open_mock.call_args_list[0].args[0]
        self.assertIn("https://wa.me/2250700000000", first_url)
        self.assertIn("TimeSheet%2021-20", first_url)


if __name__ == "__main__":
    unittest.main()
