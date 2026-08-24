# 星野リゾート「界タビ20s」空室監視

「界タビ20s」の予約カレンダーを定期確認し、○または△の空室状況が変化したときだけDiscordへ通知します。全施設を対象とし、ローカル常時監視とGitHub Actionsの単発実行に対応しています。

## 通知状態の永続化

施設ごとの最終確認済み空室状態を `state/availability.json` に保存します。プロセスやGitHub Actionsの実行環境が毎回新しくなっても、同じ空室の重複通知を防げます。

- 新しい空室、日付・記号の変化: Discord通知後に状態を更新
- 同じ空室: 通知をスキップ
- 空室がなくなった施設: 状態だけを空に更新
- 取得に失敗した施設: 前回状態を保持し、他施設の確認を継続
- Discord送信失敗: 状態を更新せず、次回に再試行

GitHub Actionsでは状態ファイルに変化があった場合だけ、`github-actions[bot]` がリポジトリへコミットします。

## ローカルセットアップ

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
Copy-Item .env.example .env
```

`.env` の `DISCORD_WEBHOOK_URL_HOSHINO` を実際のDiscord Webhook URLへ変更します。`.env` はGit管理対象外です。

単発実行:

```powershell
.venv\Scripts\python.exe -m src.hoshino_scraper.main
```

ローカル常時監視:

```powershell
.venv\Scripts\python.exe server.py
```

テスト:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## GitHub Actions

`.github/workflows/monitor.yml` は毎時7分から10分間隔で実行します。毎時0分付近の混雑を避けるため、開始分をずらしています。手動実行にも対応しています。

GitHubへ公開する前に、リポジトリの `Settings > Secrets and variables > Actions` で以下のRepository secretを登録します。

```text
DISCORD_WEBHOOK_URL_HOSHINO
```

ワークフローには状態ファイルをコミットするため `contents: write` 権限を付与しています。同一ワークフローの重複実行は `concurrency` で直列化します。

## 設定

- `config/settings.yaml`: 対象施設と検索期間
- `config/url.yaml`: 施設名と予約プランURL
- `switch.yaml`: ローカル常時監視の有効化と間隔

現在の `target_facilities` は `all` で、`config/url.yaml` に登録された全20施設を確認します。
