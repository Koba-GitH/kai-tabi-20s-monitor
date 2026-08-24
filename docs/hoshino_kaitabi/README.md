# 星野リゾート 界タビ20s 空き監視

## 概要

星野リゾート「界」の界タビ20sプランの空き状況を監視し、△（空きわずか）または○（空きあり）が検出された場合にDiscordへ通知するスクリプト。

## セットアップ

### 1. 依存パッケージのインストール

```bash
.venv\Scripts\pip install selenium requests pyyaml python-dotenv
```

### 2. 環境変数の設定 (.env)

```
DISCORD_WEBHOOK_URL_HOSHINO=https://discord.com/api/webhooks/...
```

### 3. 設定ファイル

| ファイル | 説明 |
|---------|------|
| `switch.yaml` | アプリのon/off設定 |
| `config/settings.yaml` | 対象施設・検索期間の設定 |
| `config/url.yaml` | 施設URL一覧 |

## 使用方法

### サーバー起動 (常時監視)

```bash
.venv\Scripts\python server.py
```

### 単発実行

```bash
.venv\Scripts\python -c "from src.hoshino_scraper.main import run; run()"
```

## 設定例

### config/settings.yaml

```yaml
hoshino:
  target_facilities:
    - アルプス
    - 箱根
    # - all  # 全施設を監視

  search_period:
    # 方式1: 個別日付
    # dates:
    #   - "2026-01-13"

    # 方式2: 区間指定
    # ranges:
    #   - start: "2026-01-01"
    #     end: "2026-01-31"

    # 方式3: 今日から○ヶ月
    months_from_today: 2
```

## 対象施設一覧 (20施設)

| 施設名 | URL |
|--------|-----|
| ポロト | https://hoshinoresorts.com/plans/JA/0000000129/0000000063 |
| 津軽 | https://hoshinoresorts.com/plans/JA/0000000114/0000000431 |
| 秋保 | https://hoshinoresorts.com/plans/JA/0000000133/0000000016 |
| 鬼怒川 | https://hoshinoresorts.com/plans/JA/0000000121/0000000173 |
| 箱根 | https://hoshinoresorts.com/plans/JA/0000000117/0000000338 |
| 仙石原 | https://hoshinoresorts.com/plans/JA/0000000124/0000000116 |
| アンジン | https://hoshinoresorts.com/plans/JA/0000000122/0000000092 |
| 伊東 | https://hoshinoresorts.com/plans/JA/0000000108/0000000523 |
| 遠州 | https://hoshinoresorts.com/plans/JA/0000000113/0000000566 |
| アルプス | https://hoshinoresorts.com/plans/JA/0000000123/0000000079 |
| 奥飛騨 | https://hoshinoresorts.com/plans/JA/0000000134/0000000022 |
| 加賀 | https://hoshinoresorts.com/plans/JA/0000000103/0000000506 |
| 玉造 | https://hoshinoresorts.com/plans/JA/0000000106/0000000512 |
| 出雲 | https://hoshinoresorts.com/plans/JA/0000000132/0000000028 |
| 長門 | https://hoshinoresorts.com/plans/JA/0000000126/0000000040 |
| 雲仙 | https://hoshinoresorts.com/plans/JA/0000000131/0000000083 |
| 別府 | https://hoshinoresorts.com/plans/JA/0000000128/0000000088 |
| 由布院 | https://hoshinoresorts.com/plans/JA/0000000130/0000000066 |
| 阿蘇 | https://hoshinoresorts.com/plans/JA/0000000115/0000000428 |
| 霧島 | https://hoshinoresorts.com/plans/JA/0000000127/0000000086 |

## 空き判定

| 記号 | HTMLクラス | 意味 |
|------|------------|------|
| ○ | `.circle` | 空きあり |
| △ | `.triangle` | 空きわずか |
| × | `.batu` + `full` | 満室 |
| − | `closed` | 休館/対象外 |

## 重複通知スキップ

施設ごとの前回状態を `state/availability.json` に永続化し、前回と同じ内容の通知は自動的にスキップされる。プロセス再起動後やGitHub Actionsの別実行でも有効。

| 状況 | 動作 |
|------|------|
| 空きあり（前回と異なる） | 通知送信 |
| 空きあり（前回と同じ） | スキップ |
| 空きなし | 通知なし、状態リセット |

**例:**
```
1回目: 空きあり(A) → 通知送信
2回目: 同じ空き(A) → スキップ
3回目: 空き増減(B) → 通知送信
4回目: 空きなし    → 通知なし（状態リセット）
5回目: 空きあり(B) → 通知送信（リセット後なので通知）
```
