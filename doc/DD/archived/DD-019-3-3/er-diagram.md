# Firestore データモデル

## task_status コレクション（新規）

```mermaid
erDiagram
    task_status {
        string _document_id PK "固定ID: 'ingest' or 'evaluate'"
        boolean running "実行中かどうか"
        boolean cancel "中止リクエストフラグ"
        int current "処理済み件数"
        int total "全体件数"
        float elapsed "経過時間（秒）"
        float estimated_remaining "残り推定時間（秒）"
        timestamp updated_at "最終更新日時（SERVER_TIMESTAMP）"
    }

    task_status_ingest {
        string current_file "処理中のファイル名"
    }

    task_status_evaluate {
        string current_id "処理中のテストケースID"
        array results "各ケースの結果リスト"
    }

    task_status ||--o| task_status_ingest : "doc_id = 'ingest'"
    task_status ||--o| task_status_evaluate : "doc_id = 'evaluate'"
```

## ドキュメント例

### `task_status/ingest`

```json
{
  "running": true,
  "cancel": false,
  "current": 15,
  "total": 61,
  "current_file": "社内規程/vpn_manual.md",
  "elapsed": 45.2,
  "estimated_remaining": 138.6,
  "updated_at": "2026-03-21T10:00:45Z"
}
```

### `task_status/evaluate`

```json
{
  "running": true,
  "cancel": false,
  "current": 12,
  "total": 45,
  "current_id": "exact_match_003",
  "elapsed": 120.5,
  "estimated_remaining": 330.0,
  "results": [
    { "id": "exact_match_001", "status": "PASS", "llm_label": "CORRECT" },
    { "id": "exact_match_002", "status": "FAIL", "llm_label": "INCORRECT" }
  ],
  "updated_at": "2026-03-21T10:02:00Z"
}
```

## 既存コレクションとの関係

```mermaid
erDiagram
    task_status ||--o{ chunks : "Ingestが書き込む対象"
    task_status ||--o{ eval_results : "Evaluateが書き込む対象"

    task_status {
        string _id PK "ingest / evaluate"
        boolean running
        int current
        int total
    }

    chunks {
        string _id PK
        string content
        string content_hash
        vector embedding
        string source_file
        int chunk_index
    }

    eval_results {
        string _id PK
        string date
        object config_params
        object overall
        object score_by_type
        timestamp timestamp
    }
```

> `task_status` は実行中の進捗を一時的に保持するだけで、
> 処理の結果は従来通り `chunks` / `eval_results` に保存される。
> タスク完了時に `running: false` に更新される。
