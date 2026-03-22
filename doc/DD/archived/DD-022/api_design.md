# DD-022: API エンドポイント設計

> DD-022 本体: [DD-022_コレクション切替による並列チャンク実験.md](../DD-022_コレクション切替による並列チャンク実験.md)

既存の admin API パスベースルーティング（`main.py` `admin()`）に以下を追加する。

## 新規エンドポイント

### GET /collections — コレクション一覧

**取得方法:** Firestore の `chunks*` コレクションをリストアップする。
Firestore Admin SDK の `db.collections()` で全トップレベルコレクションを取得し、`chunks` プレフィクスでフィルタ。
各コレクションのチャンク数は `collection.count().get()` で取得（集計クエリ、読み取り課金なし）。

**評価スコアの取得:** 既存の `eval_results` コレクション（Firestore）にはコレクション名が記録されていない。
→ 評価結果の `config_params.collection_name`（本DDで追加）から逆引きする。
→ 未評価のコレクションは `score: null` を返す。

```
GET /api/admin/collections

Response 200:
{
  "collections": [
    {
      "name": "chunks",
      "chunk_count": 403,
      "score": { "overall": 0.797, "date": "2026-03-20" }   // eval_results から
    },
    {
      "name": "chunks_1200",
      "chunk_count": 292,
      "score": { "overall": 0.851, "date": "2026-03-21" }
    },
    {
      "name": "chunks_1600",
      "chunk_count": 0,
      "score": null                                          // 未評価
    }
  ],
  "active": "chunks"       // 現在の config.collection_name
}
```

### PUT /collections/active — アクティブコレクション切替

既存の `PUT /config` を拡張する案もあるが、**意味が異なる**ため別エンドポイントにする:
- `PUT /config` = チューニングパラメータの変更（検索閾値等）
- `PUT /collections/active` = どのデータセットを使うかの切替

```
PUT /api/admin/collections/active
Body: { "name": "chunks_1200" }

Response 200:
{ "active": "chunks_1200", "previous": "chunks" }

Response 400:  （存在しないコレクション名の場合）
{ "error": "Collection 'chunks_9999' not found" }
```

**実装:** `config.collection_name` を書き換える。ランタイムのみ（再デプロイでリセット）。
既存の `PUT /config` と同じパターン。バリデーションとして `db.collections()` でコレクション存在確認を行う。

### GET /tasks — タスク一覧

```
GET /api/admin/tasks
GET /api/admin/tasks?prefix=ingest:

Response 200:
{
  "tasks": [
    {
      "task_id": "ingest:chunks_1200",
      "running": true,
      "current": 5,
      "total": 12,
      "current_file": "guide/setup.md",
      "elapsed": 45.2,
      "estimated_remaining": 63.0
    },
    {
      "task_id": "ingest:chunks_1600",
      "running": false
    }
  ]
}
```

## 既存 API の変更

| 既存エンドポイント | 変更内容 |
|-------------------|---------|
| `GET /ingest/status` | **後方互換維持**。内部で `get_task_status("ingest")` → `get_task_status(f"ingest:{config.collection_name}")` に変更。既存UIが壊れないようにする |
| `POST /ingest` | task_id を `f"ingest:{config.collection_name}"` に変更 |
| `POST /ingest/cancel` | 同上 |
| `GET /evaluate/status` | task_id を `f"evaluate:{config.collection_name}"` に変更 |
| `POST /evaluate` | 同上 |
| `POST /evaluate/cancel` | 同上 |
