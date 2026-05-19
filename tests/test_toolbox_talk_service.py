from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from app.db import connection
from app.services import attendance_export_service
from app.services.toolbox_talk_service import (
    assign_monthly_topics,
    assign_topic_to_dates,
    clear_monthly_toolbox_topics,
    delete_toolbox_topic,
    generate_toolbox_theme_catalog,
    list_theme_catalog,
    list_toolbox_topics,
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
        self.assertEqual(row["theme"], "Circulation sur site")
        self.assertEqual(row["status"], "done")
        self.assertEqual(data["summary"]["completed"], 1)

    def test_delete_topic_marks_day_missing(self) -> None:
        save_toolbox_topic({"date_theme": "2026-05-14", "theme": "Fatigue management"})

        delete_toolbox_topic("2026-05-14")

        row = next(item for item in list_toolbox_topics("2026-05")["rows"] if item["date_theme"] == "2026-05-14")
        self.assertEqual(row["status"], "missing")

    def test_assign_topic_to_multiple_dates(self) -> None:
        count = assign_topic_to_dates(
            {
                "dates": ["2026-05-01", "2026-05-03", "2026-05-03"],
                "theme": "Controle des EPI",
                "facilitateur": "QHSE",
            }
        )

        data = list_toolbox_topics("2026-05")
        by_date = {row["date_theme"]: row for row in data["rows"]}

        self.assertEqual(count, 2)
        self.assertEqual(by_date["2026-05-01"]["theme"], "Controle des EPI")
        self.assertEqual(by_date["2026-05-03"]["theme"], "Controle des EPI")
        self.assertEqual(by_date["2026-05-03"]["facilitateur"], "QHSE")

    def test_generate_toolbox_theme_catalog_creates_reusable_topics(self) -> None:
        count = generate_toolbox_theme_catalog(5)

        themes = list_theme_catalog()

        self.assertEqual(count, 5)
        self.assertEqual(len(themes), 5)
        self.assertTrue(any("EPI" in row["theme"] for row in themes))

    def test_random_month_assignment_repeats_only_mandatory_topics_twice(self) -> None:
        generate_toolbox_theme_catalog(31)

        count = assign_monthly_topics("2026-05", facilitateur="QHSE")

        data = list_toolbox_topics("2026-05")
        counts: dict[str, int] = {}
        mandatory = {
            row["theme"]
            for row in list_theme_catalog()
            if int(row.get("obligatoire") or 0)
        }
        for row in data["rows"]:
            counts[row["theme"]] = counts.get(row["theme"], 0) + 1

        self.assertEqual(count, 31)
        self.assertEqual(data["summary"]["completed"], 31)
        self.assertTrue(any(value == 2 for value in counts.values()))
        for theme, occurrences in counts.items():
            if occurrences > 1:
                self.assertIn(theme, mandatory)
                self.assertLessEqual(occurrences, 2)

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
        self.assertIn("Renseigne", sheet)
        self.assertIn("OREZONE QHSE - TOOLBOX TALK MEETING", sheet)
        self.assertIn("Description OREZONE", sheet)


if __name__ == "__main__":
    unittest.main()
