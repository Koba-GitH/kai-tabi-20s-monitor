# プロジェクト構成

```
D:\monitor\
├── server.py                 # エントリーポイント (常時起動)
├── switch.yaml               # アプリon/off設定
├── .env                      # 環境変数 (DISCORD_WEBHOOK_URL等)
│
├── config\
│   ├── url.yaml              # 施設URL一覧 (20施設)
│   └── settings.yaml         # 監視設定 (施設・期間指定)
│
├── src\
│   ├── __init__.py
│   │
│   ├── notifier\             # 汎用通知モジュール
│   │   ├── __init__.py
│   │   └── discord.py        # Discord Webhook送信
│   │
│   └── hoshino_scraper\      # 星野リゾート監視モジュール
│       ├── __init__.py
│       ├── main.py           # 監視ロジック (run関数)
│       ├── scraper.py        # Seleniumスクレイパー
│       └── config.py         # 設定読み込み
│
├── docs\
│   ├── tree.md               # 本ファイル
│   └── hoshino_kaitabi\
│       └── README.md         # 星野リゾート監視の説明書
│
└── .venv\                    # Python仮想環境
```

## ファイル説明

| ファイル | 説明 |
|---------|------|
| `server.py` | switch.yaml を読み込み、有効なアプリを定期実行 |
| `switch.yaml` | 各監視アプリのon/off・実行間隔を設定 |
| `config/url.yaml` | 監視対象の施設URLリスト |
| `config/settings.yaml` | 監視の詳細設定 (対象施設、検索期間等) |
| `src/notifier/discord.py` | `send_discord(message, webhook_url)` 汎用関数 |
| `src/hoshino_scraper/main.py` | `run()` - server.pyから呼ばれるエントリーポイント (重複通知スキップ機能付き) |
| `src/hoshino_scraper/scraper.py` | `HoshinoScraper` クラス |

## 共通機能

### 重複通知スキップ

各監視アプリは、前回と同じ内容の通知をスキップする機能を持つ。

- 機能ごとに独立して管理（hoshino_scraperと他アプリは別々に記録）
- 空きなし時は状態をリセット（次回空きが出たら必ず通知）

## 拡張方法

新しい監視アプリを追加する場合:

1. `src/新アプリ名/` フォルダを作成
2. `main.py` に `run()` 関数を実装
3. `switch.yaml` にアプリ設定を追加

```yaml
apps:
  hoshino_scraper:
    enabled: true
    interval_minutes: 5
  新アプリ名:
    enabled: true
    interval_minutes: 10
```
