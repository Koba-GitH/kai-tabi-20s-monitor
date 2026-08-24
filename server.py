import time
import importlib
from datetime import datetime
from pathlib import Path
import yaml


def load_switch() -> dict:
    """switch.yaml を読み込む"""
    with open("switch.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    print("=" * 60)
    print("Monitor Server")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    switch = load_switch()
    apps = switch.get("apps", {})

    # 有効なアプリを表示
    enabled_apps = {name: cfg for name, cfg in apps.items() if cfg.get("enabled", False)}
    if not enabled_apps:
        print("No apps enabled. Check switch.yaml")
        return

    print("Enabled apps:")
    for name, cfg in enabled_apps.items():
        print(f"  - {name} (interval: {cfg.get('interval_minutes', 5)} min)")
    print()
    print("Press Ctrl+C to stop.\n")

    # 各アプリの最終実行時刻を追跡
    last_run = {name: datetime.min for name in enabled_apps}

    while True:
        try:
            now = datetime.now()

            for app_name, cfg in enabled_apps.items():
                interval = cfg.get("interval_minutes", 5)
                elapsed = (now - last_run[app_name]).total_seconds() / 60

                if elapsed >= interval:
                    try:
                        # 動的にモジュールを読み込んで実行
                        module = importlib.import_module(f"src.{app_name}.main")
                        module.run()
                        last_run[app_name] = now
                    except Exception as e:
                        print(f"[Error] {app_name} failed: {e}")

            # 1分ごとにチェック
            time.sleep(60)

        except KeyboardInterrupt:
            print("\n\nShutting down...")
            break


if __name__ == "__main__":
    main()
