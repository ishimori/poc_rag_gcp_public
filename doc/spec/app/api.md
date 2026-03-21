# API仕様書

> 最終更新: 2026-03-21 | 対応DD: DD-012

## Cloud Functions 構成

| 関数名 | リージョン | メモリ | タイムアウト | 用途 |
|--------|-----------|--------|------------|------|
| `chat` | asia-northeast1 | 1 GB | 120秒 | RAGチャット |
| `admin` | asia-northeast1 | 1 GB | 540秒 | 管理系API（パスベースルーティング） |

**ランタイム**: Python 3.12 / `firebase-functions`

## CORS

```python
cors_origins=["http://localhost:5180"]
cors_methods=["GET", "POST", "PUT"]
```

本番環境では Firebase Hosting 経由のアクセスのため CORS は不要（same-origin）。

## 共通レスポンス形式

**成功時**: `200 OK`（Content-Type: `application/json`）

**エラー時**:

```json
{"error": "エラーメッセージ"}
```

| ステータス | 条件 |
|-----------|------|
| 400 | リクエスト不正（必須パラメータ不足、不正なJSON等） |
| 404 | 存在しないパス |
| 405 | 許可されていないHTTPメソッド |

## Firebase Hosting リライト

```
/api/admin/** → admin 関数
**            → /index.html（SPA fallback）
```

`chat` 関数へのルーティングは Firebase Functions の直接呼び出し（`/api` パス）。

---

## エンドポイント一覧

| # | メソッド | パス | 関数 | 概要 |
|---|---------|------|------|------|
| 1 | POST | `/api` | chat | RAGチャット |
| 2 | POST | `/api/admin/ingest` | admin | ドキュメントインジェスト |
| 3 | POST | `/api/admin/evaluate` | admin | 評価実行 |
| 4 | GET | `/api/admin/evaluate/results` | admin | 評価結果一覧 |
| 5 | GET | `/api/admin/config` | admin | パラメータ取得 |
| 6 | PUT | `/api/admin/config` | admin | パラメータ更新 |
| 7 | GET | `/api/admin/chunks` | admin | チャンク一覧 |
| 8 | GET | `/api/admin/logs` | admin | クエリログ一覧 |

---

## 1. POST /api — RAGチャット

ユーザーの質問に対してRAGパイプラインで回答を生成する。

### リクエスト

```json
{
  "query": "VPNの接続方法を教えてください",
  "model": "gemini-2.5-flash"
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|---|------|-----------|------|
| `query` | string | Yes | — | ユーザーの質問 |
| `model` | string | No | `"gemini-2.5-flash"` | LLMモデル名（`gemini-2.5-flash` / `gemini-2.5-pro`） |

### レスポンス

```json
{
  "answer": "VPNに接続するには...",
  "query": "VPNの接続方法を教えてください",
  "sources": [
    {
      "content": "[VPN接続マニュアル]\nGlobalProtect...",
      "score": 0.123,
      "source_file": "VPN_Manual.md",
      "chunk_index": 2,
      "category": "it_helpdesk",
      "security_level": "public"
    }
  ]
}
```

| フィールド | 型 | 説明 |
|-----------|---|------|
| `answer` | string | LLMの回答テキスト |
| `query` | string | 元の質問（エコーバック） |
| `sources` | array | リランキング後の参照ソース一覧 |
| `sources[].content` | string | チャンクのテキスト内容 |
| `sources[].score` | number | リランキングスコア |
| `sources[].source_file` | string | 元ファイル名 |
| `sources[].chunk_index` | integer | ファイル内チャンク番号 |
| `sources[].category` | string | 文書カテゴリ |
| `sources[].security_level` | string | セキュリティレベル |

### 副作用

- `query_logs` コレクションにクエリログを保存（失敗してもレスポンスには影響しない）

---

## 2. POST /api/admin/ingest — インジェスト実行

`test-data/sources/` 内の Markdown ファイルをチャンク分割・埋め込み・Firestore 保存する。

### リクエスト

```json
{
  "clear": true
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|---|------|-----------|------|
| `clear` | boolean | No | `false` | `true` の場合、インジェスト前に既存チャンクを全削除 |

### レスポンス

```json
{
  "cleared": 30,
  "files": 12,
  "total_chunks": 35,
  "stored": 35,
  "skipped": 0,
  "details": [
    {
      "file": "FAQ_IT-Helpdesk.md",
      "chunks": 8,
      "stored": 8,
      "skipped": 0
    }
  ]
}
```

| フィールド | 型 | 説明 |
|-----------|---|------|
| `cleared` | integer | 削除されたチャンク数（`clear: false` なら 0） |
| `files` | integer | 処理したファイル数 |
| `total_chunks` | integer | 生成されたチャンク総数 |
| `stored` | integer | 保存されたチャンク数 |
| `skipped` | integer | 重複でスキップされたチャンク数 |
| `details` | array | ファイルごとの処理結果 |

### 注意

- `test-data/sources/` はデプロイ対象外。本エンドポイントはローカル開発専用。

---

## 3. POST /api/admin/evaluate — 評価実行

`test-data/golden/eval_dataset.jsonl` のテストケースに対してRAGパイプラインを実行し、スコアリングする。

### リクエスト

ボディ不要。

### レスポンス

```json
{
  "report": {
    "date": "2026-03-21T10:30:00",
    "config_params": {
      "chunk_size": 800,
      "chunk_overlap": 150,
      "top_k": 10,
      "rerank_top_n": 5,
      "rerank_threshold": 0.01
    },
    "overall": {
      "total": 45,
      "passed": 30,
      "failed": 15,
      "score": 0.667
    },
    "score_by_type": {
      "exact_match": {"total": 5, "passed": 5, "failed": 0, "score": 1.0},
      "semantic": {"total": 10, "passed": 8, "failed": 2, "score": 0.8}
    },
    "failed_cases": []
  },
  "saved_to": "results/eval_20260321_103000.json"
}
```

| フィールド | 型 | 説明 |
|-----------|---|------|
| `report.date` | string | 評価実行日時 |
| `report.config_params` | object | 評価時のパラメータ |
| `report.overall` | object | 全体スコア（total, passed, failed, score） |
| `report.score_by_type` | object | テストタイプ別スコア |
| `report.failed_cases` | array | 失敗ケースの詳細 |
| `saved_to` | string | 保存先ファイルパス |

### 注意

- 実行に数分かかる。タイムアウト 540秒。
- `test-data/` および `results/` はデプロイ対象外。ローカル開発専用。

---

## 4. GET /api/admin/evaluate/results — 評価結果一覧

Firestore `eval_results` コレクションから評価レポートを新しい順に返す。Firestore読み取り失敗時は `results/` ディレクトリのローカルファイルにフォールバック。

### リクエスト

パラメータなし。

### レスポンス

```json
[
  {
    "file": "eval_20260321_103000.json",
    "date": "2026-03-21T10:30:00",
    "config_params": {"chunk_size": 800, "...": "..."},
    "overall": {"total": 45, "passed": 30, "failed": 15, "score": 0.667},
    "score_by_type": {"...": "..."}
  }
]
```

---

## 5. GET /api/admin/config — パラメータ取得

現在のチューニングパラメータを返す。

### リクエスト

パラメータなし。

### レスポンス

```json
{
  "chunk_size": 800,
  "chunk_overlap": 150,
  "header_injection": true,
  "top_k": 10,
  "rerank_top_n": 5,
  "rerank_threshold": 0.01
}
```

### チューニングパラメータ一覧

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `chunk_size` | int | 800 | チャンク分割の最大文字数 |
| `chunk_overlap` | int | 150 | チャンク間のオーバーラップ文字数 |
| `header_injection` | bool | true | チャンク先頭にドキュメントタイトルを付与するか |
| `top_k` | int | 10 | ベクトル検索の取得件数 |
| `rerank_top_n` | int | 5 | リランキング後の最終件数 |
| `rerank_threshold` | float | 0.01 | リランキングスコアの最低閾値 |

---

## 6. PUT /api/admin/config — パラメータ更新

チューニングパラメータをランタイムで変更する。再デプロイで初期値に戻る。

### リクエスト

```json
{
  "chunk_size": 600,
  "top_k": 8
}
```

更新したいパラメータのみ指定すればよい（部分更新）。

### レスポンス

```json
{
  "updated": {"chunk_size": 600, "top_k": 8},
  "errors": ["Unknown parameter: foo"]
}
```

| フィールド | 型 | 説明 |
|-----------|---|------|
| `updated` | object | 更新に成功したパラメータ |
| `errors` | array\<string\> | エラーメッセージ（存在しないキー、型不正等）。エラーがなければ省略 |

---

## 7. GET /api/admin/chunks — チャンク一覧

Firestore の chunks コレクションからチャンク一覧を取得する。`embedding` フィールドは除外される。

### クエリパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `category` | string | — | カテゴリでフィルタ |
| `security_level` | string | — | セキュリティレベルでフィルタ |
| `limit` | int | 200 | 取得件数（最大 500） |
| `offset` | int | 0 | オフセット（簡易ページネーション） |

### レスポンス

```json
{
  "chunks": [
    {
      "id": "abc123",
      "content": "[FAQ] VPNに接続できない場合は...",
      "content_preview": "[FAQ] VPNに接続できない場合は...",
      "content_hash": "a1b2c3...",
      "source_file": "FAQ_IT-Helpdesk.md",
      "chunk_index": 0,
      "category": "it_helpdesk",
      "security_level": "public",
      "allowed_groups": ["all"]
    }
  ],
  "count": 1
}
```

### ソート順

`source_file` ASC → `chunk_index` ASC

---

## 8. GET /api/admin/logs — クエリログ一覧

Firestore の query_logs コレクションからクエリログを取得する。

### クエリパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `no_answer` | string | — | `"true"` で無回答ログのみ取得 |
| `limit` | int | 50 | 取得件数（最大 200） |

### レスポンス

```json
{
  "logs": [
    {
      "id": "xyz789",
      "query": "VPNの接続方法は？",
      "answer": "VPNに接続するには...",
      "model": "gemini-2.5-flash",
      "elapsed_ms": 3200,
      "sources": [
        {"file": "VPN_Manual.md", "score": 0.85}
      ],
      "source_count": 1,
      "no_answer": false,
      "timestamp": "2026-03-21T10:30:00+00:00"
    }
  ],
  "count": 1
}
```

### ソート順

`timestamp` DESC
