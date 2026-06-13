from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import ai_service


class AIServiceTestCase(unittest.TestCase):
    def test_ai_settings_are_saved_without_exposing_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = ai_service.AI_CONFIG_PATH
            ai_service.AI_CONFIG_PATH = Path(tmpdir) / "ai_config.json"
            try:
                with patch.dict(os.environ, {}, clear=True):
                    settings = ai_service.save_ai_settings(
                        {
                            "enabled": True,
                            "model": "test-model",
                            "api_key": "sk-local-test",
                        }
                    )
                    self.assertTrue(settings["enabled"])
                    self.assertEqual(settings["model"], "test-model")
                    self.assertTrue(settings["api_key_configured"])
                    self.assertTrue(settings["ready"])
                    self.assertFalse(settings["operational"])
                    self.assertNotIn("sk-local-test", str(settings))
                    self.assertIn("sk-local-test", ai_service.AI_CONFIG_PATH.read_text(encoding="utf-8"))
            finally:
                ai_service.AI_CONFIG_PATH = original_path

    def test_ai_test_status_controls_operational_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = ai_service.AI_CONFIG_PATH
            ai_service.AI_CONFIG_PATH = Path(tmpdir) / "ai_config.json"
            try:
                with patch.dict(os.environ, {}, clear=True):
                    ai_service.save_ai_settings({"enabled": True, "model": "test-model", "api_key": "sk-local-test"})
                    errored = ai_service.record_ai_test_status("error", "Quota OpenAI depasse")
                    self.assertFalse(errored["operational"])
                    ok = ai_service.record_ai_test_status("ok", "Connexion IA confirmee")
                    self.assertTrue(ok["operational"])
            finally:
                ai_service.AI_CONFIG_PATH = original_path

    def test_disabled_ai_rejects_generation_before_network_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = ai_service.AI_CONFIG_PATH
            ai_service.AI_CONFIG_PATH = Path(tmpdir) / "ai_config.json"
            try:
                with patch.dict(os.environ, {}, clear=True):
                    ai_service.save_ai_settings({"enabled": False, "model": "test-model", "api_key": "sk-local-test"})
                    with self.assertRaises(ai_service.AIConfigurationError):
                        ai_service.generate_ai_text("system", "user")
            finally:
                ai_service.AI_CONFIG_PATH = original_path

    def test_default_model_is_current_operational_default(self) -> None:
        self.assertEqual(ai_service.DEFAULT_MODEL, "gpt-4o-mini")


if __name__ == "__main__":
    unittest.main()
