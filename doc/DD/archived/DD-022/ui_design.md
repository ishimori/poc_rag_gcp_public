# DD-022: UI改修設計（Tuning → Operations Monitor）

> DD-022 本体: [DD-022_コレクション切替による並列チャンク実験.md](../DD-022_コレクション切替による並列チャンク実験.md)

## 方針

> コレクション選択はチャット画面ではなくOperations Monitorに配置。チャット画面はシンプルに保ち、設定変更は管理画面に集約する。DD-021（検索プリセット）破棄と同じ方針 — チャット画面にユーザーが判断しづらい切替UIを置かない。

## 廃止する機能

| 機能 | 移行先 |
|------|--------|
| パラメータ編集（chunk_size, top_k 等） | `config.py` / CLI引数 |
| Technique Toggles | `config.py` |
| Re-tune（一括実行） | `scripts/run_chunk_experiments.py` |

## 新設する機能

- コレクション選択ドロップダウン（チャンク数・評価スコア付き）
- Ingest / Evaluate 複数ジョブの進捗一覧（コレクションごとのプログレスバー）
- スコア比較テーブル（完了済みコレクション横断）

**HTMLモック:** `mock_operations_monitor.html`（同フォルダ内）

## UI → API マッピング

| UI操作 | API呼び出し | タイミング |
|--------|-----------|-----------|
| 画面オープン | `GET /collections` | マウント時 |
| 画面オープン | `GET /tasks` | マウント時 + 2秒ポーリング |
| コレクション切替 | `PUT /collections/active` | ドロップダウン変更時 |
| ジョブキャンセル | `POST /ingest/cancel` or `POST /evaluate/cancel` | キャンセルボタン |

## 既存UIからの削除対象（`Tuning.tsx`）

| 対象 | 行番号（現時点） |
|------|----------------|
| `PARAM_FIELDS` 定義と Parameters セクション | L210-311 |
| Technique Toggles セクション | L243-284 |
| `handleRetune()` と Re-tune ボタン | L181-203, L413-420 |
| `handleSaveConfig()` と Save Parameters ボタン | L125-135, L304-311 |
| 関連state | `config`, `draft`, `configStatus`, `retuneStatus` |

## 既存UIから保持する要素

- Ingest / Evaluate の実行ボタン・進捗バー・キャンセル（→ 複数ジョブ対応に改修）
- Evaluation Result 表示（→ スコア比較テーブルに発展）
