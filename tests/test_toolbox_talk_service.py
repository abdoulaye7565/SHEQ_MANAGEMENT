from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from app.db import connection
from app.services import attendance_export_service
from app.services.toolbox_talk_service import (
    DEFAULT_TOOLBOX_FACILITATOR,
    apply_monthly_toolbox_facilitator,
    assign_monthly_topics,
    assign_topic_to_dates,
    clear_monthly_toolbox_topics,
    delete_theme_catalog,
    delete_toolbox_topic,
    generate_toolbox_theme_catalog,
    list_theme_catalog,
    list_toolbox_facilitators,
    list_toolbox_topics,
    save_theme_catalog,
    save_toolbox_topic,
)


class ToolboxTalkServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = connection.DATA_DIR
        self.original_database_path = connection.DATABASE_PATH
        self.original_exports_dir = attendance_export_service.EXPORTS_DIR
        connection.DATA_DIR = Path(self.temp_dir.name)
        connection.DATABASE_PATH = connection.DATA_DIR / "test.db"
        attendance_export_service.EXPORTS_DIR = Path(self.temp_dir.name) / "exports"
        connection.initialize_database()

    def tearDown(self) -> None:
        connection.DATA_DIR = self.original_data_dir
        connection.DATABASE_PATH = self.original_database_path
        attendance_export_service.EXPORTS_DIR = self.original_exports_dir
        self.temp_dir.cleanup()

    def test_month_contains_one_row_per_day(self) -> None:
        data = list_toolbox_topics("2026-05")

        self.assertEqual(data["summary"]["days"], 31)
        self.assertEqual(len(data["rows"]), 31)
        self.assertEqual(data["rows"][0]["date_theme"], "2026-05-01")
        self.assertEqual(data["summary"]["completed"], 0)

    def test_save_topic_upserts_one_topic_per_day(self) -> None:
        first_id = save_toolbox_topic(
            {
                "date_theme": "2026-05-14",
                "theme": "Port des EPI",
                "facilitateur": "HSE",
            }
        )
        second_id = save_toolbox_topic(
            {
                "date_theme": "2026-05-14",
                "theme": "Circulation sur site",
                "facilitateur": "Superviseur",
            }
        )

        data = list_toolbox_topics("2026-05")
        row = next(item for item in data["rows"] if item["date_theme"] == "2026-05-14")

        self.assertEqual(first_id, second_id)
        self.assertEqual(row["theme"], "Site traffic management / Circulation sur site")
        self.assertEqual(row["status"], "done")
        self.assertEqual(data["summary"]["completed"], 1)

    def test_default_facilitator_is_abou_diarra(self) -> None:
        save_toolbox_topic({"date_theme": "2026-05-14", "theme": "Fatigue management"})

        row = next(item for item in list_toolbox_topics("2026-05")["rows"] if item["date_theme"] == "2026-05-14")

        self.assertEqual(row["facilitateur"], DEFAULT_TOOLBOX_FACILITATOR)
        self.assertEqual(list_toolbox_facilitators()[0]["label"], DEFAULT_TOOLBOX_FACILITATOR)

    def test_apply_facilitator_to_full_month(self) -> None:
        count = apply_monthly_toolbox_facilitator("2026-05", "Superviseur HSE")

        data = list_toolbox_topics("2026-05")

        self.assertEqual(count, 31)
        self.assertEqual(data["summary"]["completed"], 0)
        self.assertTrue(all(row["facilitateur"] == "Superviseur HSE" for row in data["rows"]))

    def test_month_assignment_still_fills_days_after_facilitator_was_applied(self) -> None:
        generate_toolbox_theme_catalog(31)
        apply_monthly_toolbox_facilitator("2026-05", "Superviseur HSE")

        count = assign_monthly_topics("2026-05")
        data = list_toolbox_topics("2026-05")

        self.assertEqual(count, 31)
        self.assertEqual(data["summary"]["completed"], 31)
        self.assertTrue(all(row["facilitateur"] == "Superviseur HSE" for row in data["rows"]))
        self.assertTrue(all(str(row["theme"] or "").strip() for row in data["rows"]))

    def test_delete_topic_marks_day_missing(self) -> None:
        save_toolbox_topic({"date_theme": "2026-05-14", "theme": "Fatigue management"})

        delete_toolbox_topic("2026-05-14")

        row = next(item for item in list_toolbox_topics("2026-05")["rows"] if item["date_theme"] == "2026-05-14")
        self.assertEqual(row["status"], "missing")

    def test_assign_topic_to_selected_date(self) -> None:
        count = assign_topic_to_dates(
            {
                "dates": ["2026-05-01"],
                "theme": "Controle des EPI",
                "facilitateur": "QHSE",
            }
        )

        data = list_toolbox_topics("2026-05")
        by_date = {row["date_theme"]: row for row in data["rows"]}

        self.assertEqual(count, 1)
        self.assertEqual(by_date["2026-05-01"]["theme"], "PPE inspection and control / Controle des EPI")
        self.assertEqual(by_date["2026-05-01"]["facilitateur"], "QHSE")

    def test_generate_toolbox_theme_catalog_creates_reusable_topics(self) -> None:
        count = generate_toolbox_theme_catalog(5)

        themes = list_theme_catalog()

        self.assertEqual(count, 5)
        self.assertEqual(len(themes), 5)
        self.assertTrue(any("EPI" in row["theme"] for row in themes))

    def test_random_month_assignment_does_not_repeat_topics(self) -> None:
        generate_toolbox_theme_catalog(31)

        count = assign_monthly_topics("2026-05", facilitateur="QHSE")

        data = list_toolbox_topics("2026-05")
        counts: dict[str, int] = {}
        for row in data["rows"]:
            counts[row["theme"]] = counts.get(row["theme"], 0) + 1

        self.assertEqual(count, 31)
        self.assertEqual(data["summary"]["completed"], 31)
        self.assertTrue(counts)
        self.assertTrue(all(occurrences == 1 for occurrences in counts.values()))

    def test_assign_same_topic_twice_in_month_is_rejected(self) -> None:
        save_toolbox_topic({"date_theme": "2026-05-01", "theme": "Controle des EPI"})

        with self.assertRaises(ValueError):
            save_toolbox_topic({"date_theme": "2026-05-02", "theme": "PPE inspection and control / Controle des EPI"})

        with self.assertRaises(ValueError):
            assign_topic_to_dates(
                {
                    "dates": ["2026-06-01", "2026-06-02"],
                    "theme": "Controle des EPI",
                    "facilitateur": "QHSE",
                }
            )

    def test_existing_single_language_catalog_topics_are_completed_as_bilingual(self) -> None:
        save_theme_catalog({"theme": "Port des EPI", "obligatoire": True, "actif": True})

        themes = list_theme_catalog()

        self.assertIn("Mandatory PPE selection and use / Port des EPI", {row["theme"] for row in themes})

    def test_theme_catalog_can_be_updated_and_deleted(self) -> None:
        topic_id = save_theme_catalog({"theme": "Port des EPI", "obligatoire": True, "actif": True})

        save_theme_catalog(
            {
                "id_topic": topic_id,
                "theme": "Circulation sur site",
                "obligatoire": False,
                "actif": True,
            }
        )
        themes = list_theme_catalog()
        self.assertIn("Site traffic management / Circulation sur site", {row["theme"] for row in themes})

        delete_theme_catalog(topic_id)

        self.assertNotIn(topic_id, {int(row["id_topic"]) for row in list_theme_catalog(include_inactive=True)})

    def test_clear_monthly_topics_dissociates_all_days_without_deleting_catalog(self) -> None:
        generate_toolbox_theme_catalog(31)
        assign_monthly_topics("2026-05", facilitateur="QHSE")

        count = clear_monthly_toolbox_topics("2026-05")
        data = list_toolbox_topics("2026-05")

        self.assertEqual(count, 31)
        self.assertEqual(data["summary"]["completed"], 0)
        self.assertEqual(data["summary"]["missing"], 31)
        self.assertGreater(len(list_theme_catalog()), 0)

    def test_export_toolbox_talk_xlsx_contains_topics(self) -> None:
        save_toolbox_topic(
            {
                "date_theme": "2026-05-14",
                "theme": "Port des EPI",
                "facilitateur": "HSE",
            }
        )

        output = attendance_export_service.export_toolbox_talk_xlsx("2026-05")

        self.assertTrue(output.exists())
        with zipfile.ZipFile(output) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("Port des EPI", sheet)
        self.assertIn("OREZONE QHSE - TOOLBOX TALK MONTHLY MEETING", sheet)
        self.assertIn("Monthly meeting", sheet)
        self.assertIn("OREZONE", sheet)
        self.assertIn("Prepared by", sheet)
        self.assertIn("Checked by", sheet)
        self.assertIn("Approved by", sheet)
        self.assertNotIn("Description OREZONE", sheet)
        self.assertNotIn("Signature / Comments", sheet)

    def test_bilingual_topic_split_keeps_english_and_french_columns(self) -> None:
        split = attendance_export_service._split_bilingual_toolbox_topic

        self.assertEqual(
            split("Mandatory PPE selection and use / Port obligatoire des EPI"),
            ("Mandatory PPE selection and use", "Port obligatoire des EPI"),
        )
        self.assertEqual(
            split("Port obligatoire des EPI / Mandatory PPE selection and use"),
            ("Mandatory PPE selection and use", "Port obligatoire des EPI"),
        )
        self.assertEqual(
            split("FR: Gestion de la fatigue EN: Fatigue management before starting work"),
            ("Fatigue management before starting work", "Gestion de la fatigue"),
        )

    def test_export_toolbox_talk_xlsx_reorders_reversed_bilingual_topic(self) -> None:
        save_toolbox_topic(
            {
                "date_theme": "2026-05-14",
                "theme": "Port obligatoire des EPI / Mandatory PPE selection and use",
                "facilitateur": "HSE",
            }
        )

        output = attendance_export_service.export_toolbox_talk_xlsx("2026-05")

        with zipfile.ZipFile(output) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        english_position = sheet.index("Mandatory PPE selection and use")
        french_position = sheet.index("Port obligatoire des EPI")
        self.assertLess(english_position, french_position)


if __name__ == "__main__":
    unittest.main()
