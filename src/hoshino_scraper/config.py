import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 環境変数
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL_HOSHINO", "")


def load_urls() -> dict:
    """config/url.yaml を読み込む"""
    with open(PROJECT_ROOT / "config" / "url.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_settings() -> dict:
    """config/settings.yaml の hoshino セクションを読み込む"""
    with open(PROJECT_ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["hoshino"]


def get_facility_url(name: str) -> str | None:
    """施設名からURLを取得"""
    urls = load_urls()
    for facility in urls["facilities"]:
        if facility["name"] == name:
            return facility["url"]
    return None


def get_all_facility_names() -> list[str]:
    """全施設名を取得"""
    urls = load_urls()
    return [f["name"] for f in urls["facilities"]]
