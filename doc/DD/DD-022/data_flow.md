# DD-022: データフロー図・状態遷移図

> DD-022 本体: [DD-022_コレクション切替による並列チャンク実験.md](../DD-022_コレクション切替による並列チャンク実験.md)

## データフロー図

CLI → Firestore → UI の全体の流れ。

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI（実験トリガー）                        │
│                                                                 │
│  scripts/run_chunk_experiments.py                               │
│    for size in [1200, 1600, 2000]:                              │
│      config.collection_name = f"chunks_{size}"                  │
│      config.chunk_size = size                                   │
│      task_id = f"ingest:chunks_{size}"                          │
│      → ingest.py (task_status に進捗書込)                        │
│      task_id = f"evaluate:chunks_{size}"                        │
│      → evaluate.py (task_status に進捗書込)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ Firestore書込
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Firestore                                   │
│                                                                 │
│  task_status/                                                   │
│    ingest:chunks_1200   {running: true, current: 5, total: 12}  │
│    ingest:chunks_1600   {running: true, current: 2, total: 12}  │
│    evaluate:chunks_1200 {running: false}                        │
│                                                                 │
│  chunks/          ← デフォルト (800)                             │
│  chunks_1200/     ← chunk_size=1200                             │
│  chunks_1600/     ← chunk_size=1600                             │
│  chunks_2000/     ← chunk_size=2000                             │
│                                                                 │
│  eval_results/    ← 各コレクションの評価結果                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ API経由で読取
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│               Operations Monitor（UI）                          │
│                                                                 │
│  ┌─ Active Collection ────────────────────────────┐             │
│  │  [chunks_1200 ▼]  (292 chunks, 85.1%)          │             │
│  └────────────────────────────────────────────────┘             │
│                                                                 │
│  ┌─ Running Jobs ─────────────────────────────────┐             │
│  │  ingest:chunks_1200   [████████░░] 8/12  67%   │             │
│  │  ingest:chunks_1600   [██░░░░░░░░] 2/12  17%   │             │
│  └────────────────────────────────────────────────┘             │
│                                                                 │
│  ┌─ Score Comparison ─────────────────────────────┐             │
│  │  chunks (800)   79.7%  ████████░░              │             │
│  │  chunks_1200    85.1%  █████████░              │             │
│  │  chunks_1600    --     (未評価)                 │             │
│  └────────────────────────────────────────────────┘             │
│                                                                 │
│  ポーリング: GET /tasks (2秒間隔)                                │
│  切替:      PUT /collections/active                             │
│  スコア:    GET /collections                                    │
└─────────────────────────────────────────────────────────────────┘
```

## タスク状態遷移図

Ingest / Evaluate ジョブの状態遷移。CLI実行からUI上での進捗表示・キャンセルまでの流れ。

```
                CLI 実行
                   │
                   ▼
    ┌──────────────────────┐
    │  running: true       │
    │  cancel: false       │
    │  current: 0          │
    │  total: N            │
    └──────┬───────────────┘
           │
     ┌─────┴─────┐
     │  処理中    │◄─── update_task_status() per file
     │  current++ │         UI: GET /tasks でポーリング (2秒)
     └─────┬─────┘
           │
     ┌─────┴──────────────┐
     │                    │
     ▼                    ▼
  正常完了           キャンセル要求
     │            (UI → POST /ingest/cancel
     │             → cancel: true)
     │                    │
     │                    ▼
     │            check_cancel() = true
     │            次ファイルでループ脱出
     │                    │
     ▼                    ▼
    ┌──────────────────────┐
    │  clear_task_status() │
    │  running: false      │
    │  cancel: false       │
    └──────────────────────┘
```
