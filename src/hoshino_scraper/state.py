import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import PROJECT_ROOT


STATE_VERSION = 1
DEFAULT_STATE_PATH = PROJECT_ROOT / "state" / "availability.json"


def normalize_dates(dates: list[dict]) -> list[dict[str, str]]:
    """比較と保存に使える決定的な順序へ空室情報を正規化する。"""
    normalized = [
        {"date": str(item["date"]), "status": str(item["status"])}
        for item in dates
    ]
    return sorted(normalized, key=lambda item: (item["date"], item["status"]))


class AvailabilityStateStore:
    """施設ごとの最終確認済み空室状態をJSONへ永続化する。"""

    def __init__(self, path: Path | str = DEFAULT_STATE_PATH):
        self.path = Path(path)

    def load(self) -> dict[str, list[dict[str, str]]]:
        if not self.path.exists():
            return {}

        with self.path.open(encoding="utf-8") as f:
            payload = json.load(f)

        if not isinstance(payload, dict):
            raise ValueError("State file must contain a JSON object")
        if payload.get("version") != STATE_VERSION:
            raise ValueError(f"Unsupported state version: {payload.get('version')}")

        facilities = payload.get("facilities")
        if not isinstance(facilities, dict):
            raise ValueError("State file must contain a facilities object")

        loaded = {}
        for name, dates in facilities.items():
            if not isinstance(name, str) or not isinstance(dates, list):
                raise ValueError("Invalid facility state")
            loaded[name] = normalize_dates(dates)
        return loaded

    def save(self, facilities: dict[str, list[dict[str, str]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STATE_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "facilities": {
                name: normalize_dates(dates)
                for name, dates in sorted(facilities.items())
            },
        }

        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temporary_path, self.path)
