import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.hoshino_scraper import main
from src.hoshino_scraper.state import AvailabilityStateStore


NOW = datetime(2026, 8, 25, 12, 0, 0)
SETTINGS = {
    "target_facilities": ["all"],
    "search_period": {"dates": ["2026-09-01"]},
}


class FakeScraper:
    def __init__(self, results=None, failures=None):
        self.results = results or {}
        self.failures = set(failures or [])
        self.closed = False

    def get_available_dates(self, url, months):
        facility = url.rsplit("/", 1)[-1]
        if facility in self.failures:
            raise RuntimeError("temporary scrape failure")
        return self.results.get(facility, [])

    def close(self):
        self.closed = True


class MonitorRunTests(unittest.TestCase):
    def test_all_facilities_december_24_and_tsugaru_all_december(self):
        settings = main.load_settings()
        facilities = main.get_all_facility_names()
        self.assertEqual(["all"], settings["target_facilities"])
        candidates = [
            {
                "date": (datetime(2026, 11, 30) + timedelta(days=offset)).strftime(
                    "%Y/%m/%d"
                ),
                "status": "○" if offset % 2 else "△",
            }
            for offset in range(33)
        ]
        candidates += [
            {"date": "2025/12/24", "status": "○"},
            {"date": "2027/12/24", "status": "○"},
        ]
        expected = {
            facility: [
                date for date in candidates
                if (
                    date["date"].startswith("2026/12/")
                    if facility == "津軽"
                    else date["date"] == "2026/12/24"
                )
            ]
            for facility in facilities
        }
        store = Mock(spec=AvailabilityStateStore, path=Path("mock-state.json"))
        store.load.return_value = {}
        scraper = FakeScraper({facility: candidates for facility in facilities})
        notifier = Mock(return_value=True)

        with patch.object(
            main,
            "get_facility_url",
            side_effect=lambda name: f"https://example.test/{name}",
        ):
            success = main.run(
                state_store=store,
                scraper_factory=lambda: scraper,
                notifier=notifier,
                webhook_url="https://discord.test/webhook",
                settings=settings,
                now=datetime(2026, 11, 10, 12),
            )

        self.assertTrue(success)
        self.assertTrue(scraper.closed)
        store.save.assert_called_once_with(expected)
        notifier.assert_called_once_with(
            main.format_results([
                (facility, expected[facility], f"https://example.test/{facility}")
                for facility in facilities
            ]),
            "https://discord.test/webhook",
        )

    def run_monitor(self, store, scraper, notifier):
        with (
            patch.object(main, "get_all_facility_names", return_value=["箱根"]),
            patch.object(
                main,
                "get_facility_url",
                side_effect=lambda name: f"https://example.test/{name}",
            ),
        ):
            return main.run(
                state_store=store,
                scraper_factory=lambda: scraper,
                notifier=notifier,
                webhook_url="https://discord.test/webhook",
                settings=SETTINGS,
                now=NOW,
            )

    def test_duplicate_notification_is_skipped_across_new_process_state(self):
        availability = {
            "箱根": [{"date": "2026/09/01", "status": "○"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "availability.json"
            notifier = Mock(return_value=True)

            first = self.run_monitor(
                AvailabilityStateStore(state_path),
                FakeScraper(availability),
                notifier,
            )
            second = self.run_monitor(
                AvailabilityStateStore(state_path),
                FakeScraper(availability),
                notifier,
            )

            self.assertTrue(first)
            self.assertTrue(second)
            self.assertEqual(1, notifier.call_count)

    def test_cleared_availability_resets_state_and_return_notifies_again(self):
        availability = {
            "箱根": [{"date": "2026/09/01", "status": "○"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "availability.json"
            notifier = Mock(return_value=True)

            self.run_monitor(
                AvailabilityStateStore(state_path),
                FakeScraper(availability),
                notifier,
            )
            self.run_monitor(
                AvailabilityStateStore(state_path),
                FakeScraper({}),
                notifier,
            )
            self.run_monitor(
                AvailabilityStateStore(state_path),
                FakeScraper(availability),
                notifier,
            )

            self.assertEqual(2, notifier.call_count)

    def test_failed_notification_does_not_advance_state(self):
        availability = {
            "箱根": [{"date": "2026/09/01", "status": "○"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "availability.json"
            success = self.run_monitor(
                AvailabilityStateStore(state_path),
                FakeScraper(availability),
                Mock(return_value=False),
            )

            self.assertFalse(success)
            self.assertFalse(state_path.exists())

    def test_failed_facility_keeps_previous_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "availability.json"
            store = AvailabilityStateStore(state_path)
            old_dates = [{"date": "2026/09/01", "status": "○"}]
            store.save({"箱根": old_dates, "鬼怒川": old_dates})

            settings = {
                "target_facilities": ["箱根", "鬼怒川"],
                "search_period": {"dates": ["2026-09-01"]},
            }
            scraper = FakeScraper(results={"箱根": []}, failures={"鬼怒川"})
            with patch.object(
                main,
                "get_facility_url",
                side_effect=lambda name: f"https://example.test/{name}",
            ):
                success = main.run(
                    state_store=store,
                    scraper_factory=lambda: scraper,
                    notifier=Mock(return_value=True),
                    webhook_url="https://discord.test/webhook",
                    settings=settings,
                    now=NOW,
                )

            self.assertTrue(success)
            self.assertEqual([], store.load()["箱根"])
            self.assertEqual(old_dates, store.load()["鬼怒川"])

    def test_all_failed_does_not_change_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "availability.json"
            notifier = Mock(return_value=True)
            success = self.run_monitor(
                AvailabilityStateStore(state_path),
                FakeScraper(failures={"箱根"}),
                notifier,
            )

            self.assertFalse(success)
            self.assertFalse(state_path.exists())
            notifier.assert_not_called()


if __name__ == "__main__":
    unittest.main()
