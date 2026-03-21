# 状態遷移図

## タスクのライフサイクル

```mermaid
stateDiagram-v2
    [*] --> Idle: 初期状態<br/>(ドキュメント未存在 or running=false)

    Idle --> Running: タスク開始<br/>update_task_status(running=true)

    Running --> Running: 進捗更新<br/>update_task_status(current++)

    Running --> Completed: 正常完了<br/>clear_task_status()
    Running --> Cancelled: 中止要求検出<br/>cancel=true → ループ脱出
    Running --> Error: 例外発生

    Cancelled --> Idle: clear_task_status()
    Error --> Idle: clear_task_status()
    Completed --> Idle: clear_task_status()

    note right of Running
        Firestoreドキュメント:
        running=true
        current/total が更新される
        フロントエンドはここをポーリング
    end note

    note right of Idle
        running=false or
        ドキュメント未存在
        → フロントエンド: 何も表示しない
    end note
```

## 中止フローの詳細

```mermaid
sequenceDiagram
    participant User as ユーザー（ブラウザ）
    participant FE as Tuning.tsx
    participant API as main.py
    participant FS as Firestore<br/>task_status
    participant CLI as scripts/ingest.py

    Note over CLI: ファイルループ実行中

    CLI->>FS: update_task_status(current=15, total=61)

    FE->>API: GET /ingest/status (ポーリング)
    API->>FS: get_task_status("ingest")
    FS-->>API: {running:true, current:15, total:61}
    API-->>FE: JSON応答
    FE->>FE: プログレスバー表示 (15/61)

    User->>FE: 「中止」ボタンクリック
    FE->>API: POST /ingest/cancel
    API->>FS: update cancel=true
    FS-->>API: OK
    API-->>FE: {cancelled: true}

    Note over CLI: 次のループ反復で cancel を検出
    CLI->>FS: get_task_status("ingest")
    FS-->>CLI: {cancel: true}
    CLI->>CLI: ループ break
    CLI->>FS: clear_task_status("ingest")

    FE->>API: GET /ingest/status (ポーリング)
    API->>FS: get_task_status("ingest")
    FS-->>API: {running: false}
    API-->>FE: {running: false}
    FE->>FE: プログレスバー非表示
```

## 正常フロー（Ingest）

```mermaid
sequenceDiagram
    participant CLI as scripts/ingest.py
    participant TS as src/task_status.py
    participant FS as Firestore<br/>task_status
    participant API as main.py
    participant FE as Tuning.tsx

    CLI->>TS: update_task_status("ingest", running=true, total=61)
    TS->>FS: set doc "ingest"

    loop ファイルごと (i = 1..61)
        CLI->>CLI: chunk_document() → embed_texts() → store_chunks()
        CLI->>TS: update_task_status("ingest", current=i, current_file=name)
        TS->>FS: update doc "ingest"
    end

    par フロントエンドのポーリング（2秒間隔）
        FE->>API: GET /ingest/status
        API->>FS: get doc "ingest"
        FS-->>API: {running:true, current:i, total:61, ...}
        API-->>FE: JSON応答
        FE->>FE: プログレスバー更新
    end

    CLI->>TS: clear_task_status("ingest")
    TS->>FS: update running=false
    CLI->>CLI: サマリー表示して終了
```

## Firestore書き込み頻度の考慮

| タスク | ループ単位 | 想定回数 | 書き込み間隔 |
|--------|-----------|---------|-------------|
| Ingest | ファイル単位 | 61回 | 数秒〜数十秒/ファイル |
| Evaluate | テストケース単位 | 45回 | 約10秒/ケース |

> PoCの規模（61ファイル / 45ケース）ではFirestoreの書き込みコストは無視できる水準。
> 仮に1回の実行で100回書き込みが発生しても、無料枠（20,000回/日）の範囲内。
