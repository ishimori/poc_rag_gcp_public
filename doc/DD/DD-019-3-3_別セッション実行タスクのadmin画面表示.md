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

（Phase 0で検討）

## タスク一覧

### Phase 0: 事前精査
- [ ] 📋 **各Phaseのタスク精査・詳細化**
- [ ] 😈 **Devil's Advocate調査**

### Phase 1: 実装
（Phase 0の決定後に詳細化）

## ログ

### 2026-03-21
- DD作成（DD-019-3-2からの派生）
- 背景: DD-019-3-2のインメモリ管理では別プロセス（CLI）の実行状態を検出できない
- 方針: Firestoreにタスク状態を記録し、CLI/バックエンド両方から読み書きする
- フロントエンドは変更不要（DD-019-3-2のUI・ポーリングをそのまま再利用）

---

## DA批判レビュー記録
