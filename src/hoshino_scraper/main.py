from copy import deepcopy
from datetime import datetime, timedelta
from typing import Callable

from .config import (
    DISCORD_WEBHOOK_URL,
    get_all_facility_names,
    get_facility_url,
    load_settings,
)
from .scraper import HoshinoScraper
from .state import AvailabilityStateStore, normalize_dates
from ..notifier.discord import send_discord


def is_date_in_period(
    date_str: str,
    period: dict,
    now: datetime | None = None,
) -> bool:
    """日付が設定された検索期間のいずれかに含まれるか判定する。"""
    date = datetime.strptime(date_str, "%Y/%m/%d")

    for configured_date in period.get("dates") or []:
        if datetime.strptime(configured_date, "%Y-%m-%d") == date:
            return True

    for configured_range in period.get("ranges") or []:
        start = datetime.strptime(configured_range["start"], "%Y-%m-%d")
        end = datetime.strptime(configured_range["end"], "%Y-%m-%d")
        if start <= date <= end:
            return True

    months = period.get("months_from_today")
    if months:
        reference = now or datetime.now()
        today = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        max_date = today + timedelta(days=months * 31)
        if today <= date <= max_date:
            return True

    return False


def format_results(results: list[tuple[str, list[dict], str]]) -> str:
    """状態が変化した施設の空室情報を1つのDiscordメッセージへまとめる。"""
    lines = ["**【星野リゾート 界タビ20s】空き状況更新**", ""]

    for facility_name, dates, url in results:
        lines.append(f"**界 {facility_name}**")
        for date in dates:
            lines.append(f"  {date['status']} {date['date']}")
        lines.append(f"  {url}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _resolve_target_facilities(settings: dict) -> list[str]:
    target_facilities = settings.get("target_facilities", [])
    if "all" in target_facilities:
        return get_all_facility_names()
    return list(dict.fromkeys(target_facilities))


def run(
    *,
    state_store: AvailabilityStateStore | None = None,
    scraper_factory: Callable[[], HoshinoScraper] = HoshinoScraper,
    notifier: Callable[[str, str], bool] = send_discord,
    webhook_url: str | None = None,
    settings: dict | None = None,
    now: datetime | None = None,
) -> bool:
    """空室を1回確認し、変化があれば通知して状態を永続化する。"""
    started_at = now or datetime.now()
    print(
        f"[{started_at.strftime('%Y-%m-%d %H:%M:%S')}] "
        "[hoshino_scraper] Starting check..."
    )

    settings = settings or load_settings()
    search_period = settings.get("search_period", {})
    target_facilities = _resolve_target_facilities(settings)
    if not target_facilities:
        print("  [Error] No target facilities configured.")
        return False

    months = search_period.get("months_from_today", 2)
    state_store = state_store or AvailabilityStateStore()
    try:
        previous_state = state_store.load()
    except (OSError, ValueError) as error:
        print(f"  [Error] Failed to load persistent state: {error}")
        return False

    next_state = deepcopy(previous_state)
    target_set = set(target_facilities)
    for stale_facility in set(next_state) - target_set:
        del next_state[stale_facility]

    changed_results: list[tuple[str, list[dict], str]] = []
    failed_facilities: list[str] = []
    succeeded = 0

    try:
        scraper = scraper_factory()
    except Exception as error:
        print(f"  [Error] Failed to start browser: {error}")
        return False

    try:
        for facility_name in target_facilities:
            url = get_facility_url(facility_name)
            if not url:
                print(f"  [Error] URL not found for facility: {facility_name}")
                failed_facilities.append(facility_name)
                continue

            print(f"  Checking: {facility_name}...")
            try:
                all_dates = scraper.get_available_dates(url, months)
            except Exception as error:
                print(f"    [Error] {error}")
                failed_facilities.append(facility_name)
                continue

            succeeded += 1
            filtered_dates = normalize_dates(
                [
                    date
                    for date in all_dates
                    if is_date_in_period(date["date"], search_period, now=started_at)
                ]
            )

            if filtered_dates:
                print(f"    Found {len(filtered_dates)} available date(s)!")
                for date in filtered_dates:
                    print(f"      {date['date']}: {date['status']}")
            else:
                print("    No availability found.")

            if previous_state.get(facility_name) != filtered_dates:
                next_state[facility_name] = filtered_dates
                if filtered_dates:
                    changed_results.append((facility_name, filtered_dates, url))
    finally:
        try:
            scraper.close()
        except Exception as error:
            print(f"  [Warning] Failed to close browser cleanly: {error}")

    if succeeded == 0:
        print("  [Error] All facility checks failed; persistent state was not changed.")
        return False

    if changed_results:
        effective_webhook_url = (
            DISCORD_WEBHOOK_URL if webhook_url is None else webhook_url
        )
        if not effective_webhook_url:
            print("  [Error] Discord Webhook URL is not set; state was not changed.")
            return False

        message = format_results(changed_results)
        if not notifier(message, effective_webhook_url):
            print("  [Error] Discord notification failed; state was not changed.")
            return False
        print(f"  Discord notification sent for {len(changed_results)} facility(s).")
    elif next_state == previous_state:
        print("  No availability changes; notification skipped.")
    else:
        print("  Availability was cleared; notification skipped.")

    if next_state != previous_state:
        try:
            state_store.save(next_state)
            print(f"  Persistent state updated: {state_store.path}")
        except OSError as error:
            print(f"  [Error] Failed to save persistent state: {error}")
            return False

    if failed_facilities:
        print(
            "  [Warning] Failed facilities (previous state retained): "
            + ", ".join(failed_facilities)
        )

    completed_at = datetime.now()
    print(
        f"[{completed_at.strftime('%Y-%m-%d %H:%M:%S')}] "
        "[hoshino_scraper] Check completed."
    )
    return True


def main() -> None:
    raise SystemExit(0 if run() else 1)


if __name__ == "__main__":
    main()
