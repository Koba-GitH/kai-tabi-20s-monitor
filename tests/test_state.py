import json
import tempfile
import unittest
from pathlib import Path

from src.hoshino_scraper.state import AvailabilityStateStore, normalize_dates


class AvailabilityStateStoreTests(unittest.TestCase):
    def test_missing_file_loads_empty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AvailabilityStateStore(Path(directory) / "state.json")
            self.assertEqual({}, store.load())

    def test_state_round_trip_is_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store = AvailabilityStateStore(path)
            store.save(
                {
                    "箱根": [
                        {"date": "2026/09/02", "status": "△"},
                        {"date": "2026/09/01", "status": "○"},
                    ]
                }
            )

            self.assertEqual(
                {
                    "箱根": [
                        {"date": "2026/09/01", "status": "○"},
                        {"date": "2026/09/02", "status": "△"},
                    ]
                },
                store.load(),
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(1, payload["version"])
            self.assertIn("updated_at", payload)

    def test_normalize_dates_does_not_depend_on_scrape_order(self):
        dates = [
            {"date": "2026/09/02", "status": "△"},
            {"date": "2026/09/01", "status": "○"},
        ]
        self.assertEqual(
            [
                {"date": "2026/09/01", "status": "○"},
                {"date": "2026/09/02", "status": "△"},
            ],
            normalize_dates(dates),
        )

    def test_invalid_top_level_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("[]", encoding="utf-8")

            with self.assertRaises(ValueError):
                AvailabilityStateStore(path).load()


if __name__ == "__main__":
    unittest.main()
