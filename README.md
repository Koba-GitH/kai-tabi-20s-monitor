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

`.github/workflows/monitor.yml` を5分間隔で実行します。手動実行にも対応しています。

GitHubへ公開する前に、リポジトリの `Settings > Secrets and variables > Actions` で以下のRepository secretを登録します。

```text
DISCORD_WEBHOOK_URL_HOSHINO
```

ワークフローには状態ファイルをコミットするため `contents: write` 権限を付与しています。同一ワークフローの重複実行は `concurrency` で直列化します。実行中に次の起動が来た場合はPendingで待機し、順番に実行されます。

### 起動方式: cron-job.orgからのworkflow_dispatch（2026-09-02設定）

GitHubの `schedule` イベントはベストエフォートで、Freeプランでは大幅に間引かれます（本リポジトリの実測: 想定144回/日に対し2〜7回/日）。このため定期起動は外部のcron-job.orgから `workflow_dispatch` APIを叩く方式を採用しています。ワークフロー内の `schedule`（毎時2分から5分間隔）はフォールバックとして残しています。

cron-job.org側のジョブ設定:

- Title: `kai-tabi-20s-monitor dispatch`（Job ID: 8366636）
- Schedule: Every 5 minutes（Asia/Tokyo）
- Request: `POST https://api.github.com/repos/Koba-GitH/kai-tabi-20s-monitor/actions/workflows/monitor.yml/dispatches`
- Headers: `Authorization: Bearer <PAT>`、`Accept: application/vnd.github+json`、`Content-Type: application/json`
- Body: `{"ref":"main"}`（成功時はHTTP 204）

認証に使うGitHub fine-grained PAT:

- Token name: `cron-job-org-dispatch`（有効期限: 2027-09-02）
- 対象: このリポジトリのみ、権限: Actions = Read and write のみ
- PAT値はcron-job.orgのジョブ設定にのみ保存（他の場所には保管しない）

運用メモ:

- PAT失効時は再発行し、cron-job.orgのジョブのAuthorizationヘッダーを更新する
- cron-job.orgは15回連続失敗でジョブを無効化し、メール通知する（GitHub側で401が続く場合はPAT失効を疑う）
- Actionsの実行分数は公開リポジトリのため無料。GitHub APIのレート制限（5,000回/時）にも12回/時で十分収まる

## 設定

- `config/settings.yaml`: 対象施設と検索期間
- `config/url.yaml`: 施設名と予約プランURL
- `switch.yaml`: ローカル常時監視の有効化と間隔

現在の `target_facilities` は `all` で、`config/url.yaml` に登録された全20施設を確認します。
