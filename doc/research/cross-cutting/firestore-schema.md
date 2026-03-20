# Firestoreスキーマ設計

> 本プロジェクトで使用するFirestoreのコレクション設計。ベクトル格納・セッション管理・フィードバック・評価まで一元管理。

---

## コレクション一覧

```mermaid
erDiagram
    chunks {
        string doc_id PK
        string content
        vector embedding
        string category
        string security_level
        string[] allowed_groups
        string source_url
        number page_number
        string parent_doc_id
        string content_hash
        timestamp updated_at
    }

    sessions {
        string session_id PK
        string user_id
        object[] history
        string summary
        timestamp created_at
        timestamp updated_at
    }

    feedback {
        string feedback_id PK
        string session_id FK
        string query
        string response
        string[] source_doc_ids
        string rating
        timestamp created_at
    }

    eval_datasets {
        string eval_id PK
        string query
        string expected_answer
        string category
    }

    chunks ||--o{ feedback : "source_doc_ids"
    sessions ||--o{ feedback : "session_id"
```

## 各コレクションの詳細

### `chunks` — ベクトル + メタデータ格納

| 用途 | 参照先 |
|------|--------|
| ベクトル検索の対象データ | [第1回](../01_データ前処理.md)、[第3回](../03_セマンティック検索.md) |
| メタデータフィルタリング | [メタデータ設計](metadata-design.md) |
| 権限ベースの Pre-filtering | [第6回](../06_セキュリティ.md) |

**インデックス**:

- ベクトルインデックス: `embedding` フィールド（COSINE距離）
- 複合インデックス: `category` + `embedding`（フィルタ付き検索用）
- 複合インデックス: `allowed_groups` + `embedding`（権限付き検索用）

### `sessions` — チャット履歴・セッション管理

| 用途 | 参照先 |
|------|--------|
| 対話継続時のコンテキスト保持 | [第5回](../05_Genkit.md) |
| 履歴の要約（コンテキスト圧縮） | [第5回](../05_Genkit.md) |

### `feedback` — ユーザーフィードバック

| 用途 | 参照先 |
|------|--------|
| 👍/👎 の記録 | [第7回](../07_評価.md) |
| 「再学習・評価待ち」キューとして利用 | [第7回](../07_評価.md) |

### `eval_datasets` — ゴールデンデータセット

| 用途 | 参照先 |
|------|--------|
| Genkit Evaluator の入力データ | [第7回](../07_評価.md) |
| CI/CDでの自動回帰テスト | [第7回](../07_評価.md) |
