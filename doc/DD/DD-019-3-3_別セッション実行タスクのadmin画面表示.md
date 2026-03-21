# DD-019-3-3: 別セッション実行タスクのadmin画面表示

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 進行中 |

## 目的

CLI（`python scripts/ingest.py`、`python scripts/evaluate.py`）で実行中のIngest/Evaluateタスクを、Tuning画面で検出・表示できるようにする。

## 背景・課題

DD-019-3-2でTuning画面ボタン経由のIngest進捗表示を実装したが、インメモリ管理（案B）のため**同一プロセス内**でしか状態を共有できない。

### 現在の制約

| 起動方法 | 進捗表示 | 理由 |
|---|---|---|
| Tuning画面のIngestボタン | 対応済（DD-019-3-2） | 同一プロセスのグローバル変数 |
| `python scripts/ingest.py`（CLI） | **非対応** | 別プロセス |
| `python scripts/evaluate.py`（CLI） | **非対応** | 別プロセス |

### 前提

- PoCであり、ローカルPCでのみ実行（Firebase上では実行不可）
- CLI実行が主な運用パターン（VSCodeターミナルから実行）
- DD-019-3-2で作成したフロントエンド（ポーリング・プログレスバー・中止ボタン）はそのまま再利用可能

## 検討内容

### アプローチ: Firestoreにタスク状態を記録（案A）

DD-019-3-2の検討時に「将来CLIからの実行検出が必要になった場合は案Aに切替可能」と設計済み。

**方針**: `task_status` Firestoreコレクションに実行状態を書き込み、`/ingest/status` `/evaluate/status` APIがそこから読み取る。

```
CLI (scripts/ingest.py)  ──書き込み──→  Firestore (task_status)
                                              ↑
バックエンド (main.py)    ──読み取り──→  Firestore (task_status)
                                              ↑
フロントエンド (Tuning.tsx) ──ポーリング→ /ingest/status API
```

### Firestoreドキュメント設計

コレクション: `task_status`
ドキュメントID: `ingest` / `evaluate`（固定、1タスク種別につき1ドキュメント）

```json
{
  "running": true,
  "current": 3,
  "total": 61,
  "current_file": "vpn_manual.md",
  "elapsed": 45.2,
  "estimated_remaining": 120.5,
  "updated_at": "2026-03-21T10:00:00Z"
}
```

### 変更対象

| 層 | ファイル | 変更内容 |
|---|---|---|
| 共通モジュール（新規） | `src/task_status.py` | Firestoreへのタスク状態読み書きユーティリティ |
| CLI | `scripts/ingest.py` | タスク状態をFirestoreに書き込み |
| CLI | `scripts/evaluate.py` | タスク状態をFirestoreに書き込み |
| バックエンド | `main.py` | `_handle_ingest_status` / `_handle_evaluate_status` をFirestore読み取りに変更 |
| バックエンド | `main.py` | `_handle_ingest` / `_handle_evaluate` もFirestore経由に統一 |
| フロントエンド | 変更なし | ポーリング先APIは同じ |

### 既存Evaluate進捗との統合

現在のEvaluateは `_eval_progress` グローバル変数 + `/evaluate/status` で動作中。これもFirestore経由に統一することで、CLI実行のEvaluateも検出可能になる。

## 決定事項

- **Firestore `task_status` コレクション**で状態共有（固定ドキュメントID方式）
- **新規モジュール `src/task_status.py`** に読み書きユーティリティを集約
- **フロントエンド変更なし**（DD-019-3-2のUI・ポーリングをそのまま再利用）
- **main.pyのインメモリ管理（`_ingest_progress` / `_eval_progress`）をFirestore経由に置換**
- 設計資料: [DD-019-3-3/](DD-019-3-3/) 参照

## タスク一覧

### Phase 0: 事前精査 ✅
- [x] 📋 **各Phaseのタスク精査・詳細化**
- [ ] 😈 **Devil's Advocate調査**

### Phase 1: タスク状態ユーティリティ ✅
- [x] `src/task_status.py`（新規作成）: Firestoreへのタスク状態読み書きユーティリティ
  - `update_task_status(task_id, **fields)` — ドキュメントを `set(..., merge=True)` で更新
  - `get_task_status(task_id) -> dict` — ドキュメントを読み取り、未存在なら `{"running": False}` を返す
  - `clear_task_status(task_id)` — `running=False, cancel=False` に更新
  - `check_cancel(task_id) -> bool` — `cancel` フィールドを読み取り
  - Firestoreクライアントは `src/ingest/store.py` と同じシングルトンパターン（`config.project_id`）
- [x] 🔬 **機械検証**: 構文チェック → OK

### Phase 2: CLI統合（Ingest） ✅
- [x] `scripts/ingest.py`: ファイルループの前後と各反復でタスク状態を更新
  - 開始時: `update_task_status("ingest", running=True, total=len(files), current=0, ...)`
  - 各ファイル処理後: `update_task_status("ingest", current=i, current_file=name, elapsed=..., estimated_remaining=...)`
  - 完了/エラー時: `clear_task_status("ingest")`（try/finally）
  - 中止: `check_cancel("ingest")` でループ脱出
- [ ] 🔬 **機械検証**: `python scripts/ingest.py --clear` 実行中にFirestoreの `task_status/ingest` が更新されることを確認
- [ ] 😈 **DA批判レビュー**

### Phase 3: CLI統合（Evaluate） ✅
- [x] `scripts/evaluate.py`: `run_evaluation()` に `on_progress` / `should_cancel` コールバックを渡してタスク状態を更新
  - 開始時: `update_task_status("evaluate", running=True, total=len(cases), current=0, ...)`
  - `on_progress` コールバック内: `update_task_status("evaluate", current=i, current_id=result.id, ...)`
  - `should_cancel` コールバック: `check_cancel("evaluate")` を返す
  - 完了/エラー時: `clear_task_status("evaluate")`（try/finally）
- [ ] 🔬 **機械検証**: `python scripts/evaluate.py --limit 3` 実行中にFirestoreの `task_status/evaluate` が更新されることを確認
- [ ] 😈 **DA批判レビュー**

### Phase 4: バックエンド統合 ✅
- [x] `main.py` `_handle_ingest_status()`: `get_task_status("ingest")` に変更
- [x] `main.py` `_handle_ingest_cancel()`: `update_task_status("ingest", cancel=True)` に変更
- [x] `main.py` `_handle_ingest()`: `update_task_status()` / `clear_task_status()` + try/finally に変更
- [x] `main.py` `_handle_evaluate_status()`: `get_task_status("evaluate")` に変更
- [x] `main.py` `_handle_evaluate_cancel()`: `update_task_status("evaluate", cancel=True)` に変更
- [x] `main.py` `_handle_evaluate()`: `update_task_status()` / `clear_task_status()` + try/finally に変更
- [x] `main.py`: `_ingest_progress` / `_eval_progress` グローバル変数を削除
- [x] 🔬 **機械検証（構文）**: `py_compile` 全ファイルOK + `npx tsc --noEmit` OK
- [ ] 🔬 **機械検証（実行）**: Tuning画面のIngestボタン実行 → プログレスバー表示確認（Playwright）
- [ ] 🔬 **機械検証（クロスプロセス）**: CLI Ingest実行中にTuning画面を開く → detachedモードで進捗表示されることを確認
- [ ] 😈 **DA批判レビュー**

## ログ

### 2026-03-21
- DD作成（DD-019-3-2からの派生）
- 背景: DD-019-3-2のインメモリ管理では別プロセス（CLI）の実行状態を検出できない
- 方針: Firestoreにタスク状態を記録し、CLI/バックエンド両方から読み書きする
- フロントエンドは変更不要（DD-019-3-2のUI・ポーリングをそのまま再利用）
- 設計資料作成: [DD-019-3-3/](DD-019-3-3/)（アーキテクチャ図、ER図、状態遷移図）
- Phase 0完了: タスク精査・詳細化（Phase 1〜4に分解）
- Phase 1〜4 コード実装完了:
  - `src/task_status.py` 新規作成（Firestore読み書きユーティリティ）
  - `scripts/ingest.py` タスク状態更新 + 中止チェック + try/finally
  - `scripts/evaluate.py` on_progress/should_cancel コールバック + try/finally
  - `main.py` インメモリ管理（`_ingest_progress` / `_eval_progress`）を全てFirestore経由に置換
  - 構文チェック + TypeScript型チェック 全パス

---

## DA批判レビュー記録
