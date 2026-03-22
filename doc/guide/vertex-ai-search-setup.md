# Vertex AI Search 環境構築ガイド

> 最終更新: 2026-03-22 | 関連DD: DD-024

本プロジェクトのソース文書を Vertex AI Search にインポートし、検索可能にするまでの手順。

## 前提条件

- `gcloud auth login` 済み
- プロジェクト: `poc-rag-490804`
- Discovery Engine API 有効化済み（`gcloud services enable discoveryengine.googleapis.com`）

## 1. GCSバケット作成 & 文書アップロード

Vertex AI Search は `.md` を直接インポートできない（"invalid JSON" エラー）。`.txt` に変換してアップロードする。

```bash
# バケット作成
gcloud storage buckets create gs://poc-rag-490804-vais-eval --location=asia-northeast1

# .md → .txt 変換（一時フォルダ）
mkdir -p /tmp/vais-txt/sources/wikipedia

for f in test-data/sources/*.md; do
  base=$(basename "$f" .md)
  cp "$f" "/tmp/vais-txt/sources/${base}.txt"
done

for f in test-data/sources/wikipedia/*.md; do
  base=$(basename "$f" .md)
  cp "$f" "/tmp/vais-txt/sources/wikipedia/${base}.txt"
done

# アップロード（Windows環境ではフルパスを使用）
gcloud storage cp "/tmp/vais-txt/sources/*.txt" gs://poc-rag-490804-vais-eval/txt/
gcloud storage cp "/tmp/vais-txt/sources/wikipedia/*.txt" gs://poc-rag-490804-vais-eval/txt/wikipedia/
```

**確認**: 61ファイルがアップロードされていること。

## 2. データストア作成

```bash
PROJECT_ID="poc-rag-490804"
DATA_STORE_ID="vais-eval-ds-2"  # 任意のID

curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores?dataStoreId=${DATA_STORE_ID}" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "'"${DATA_STORE_ID}"'",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "CONTENT_REQUIRED"
  }'
```

## 3. ドキュメントインポート

```bash
curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/default_branch/documents:import" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://poc-rag-490804-vais-eval/txt/**"],
      "dataSchema": "content"
    },
    "reconciliationMode": "FULL"
  }'
```

**重要**: `"dataSchema": "content"` を必ず指定する。省略するとJSONとして解析されエラーになる。

### インポート完了の確認

レスポンスの `name` フィールド（オペレーションID）で進捗を確認:

```bash
OPERATION="projects/636243402764/locations/global/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/operations/{operation-id}"

curl -s "https://discoveryengine.googleapis.com/v1/${OPERATION}" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}"
```

`"done": true` かつ `"successCount": "61"` になれば完了。所要時間: 約5-10分。

## 4. Search Engine（App）作成

データストア単体では検索できない。Engine を作成してデータストアを紐付ける。

```bash
ENGINE_ID="vais-eval-engine"  # 任意のID

curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines?engineId=${ENGINE_ID}" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "'"${ENGINE_ID}"'",
    "solutionType": "SOLUTION_TYPE_SEARCH",
    "dataStoreIds": ["'"${DATA_STORE_ID}"'"],
    "searchEngineConfig": {
      "searchTier": "SEARCH_TIER_ENTERPRISE",
      "searchAddOns": ["SEARCH_ADD_ON_LLM"]
    }
  }'
```

## 5. 検索テスト

Engine 作成後、インデックス構築完了まで**約10分待機**する。

```bash
curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1beta/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${ENGINE_ID}/servingConfigs/default_search:search" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "VPN接続の手順",
    "pageSize": 3,
    "contentSearchSpec": {
      "extractiveContentSpec": {
        "maxExtractiveSegmentCount": 3
      },
      "snippetSpec": {
        "returnSnippet": true
      }
    }
  }'
```

`results` が1件以上返れば成功。0件の場合はインデックス構築中のため、数分待って再試行。

## 6. アプリケーション設定

`.env.local` に以下を追加:

```
VERTEX_SEARCH_ENGINE_ID=vais-eval-engine
VERTEX_SEARCH_DATA_STORE_ID=vais-eval-ds-2
```

`src/config.py` の `use_vertex_ai_search` がデフォルト `True` のため、サーバー再起動で Vertex AI Search が有効になる。

チャットUIの「検索エンジン」トグルで自前RAGとの切替も可能。

## ハマりポイント

| 問題 | 原因 | 対処 |
|------|------|------|
| インポートで "invalid JSON" エラー | `.md` ファイルをそのままインポートした | `.txt` に拡張子変換 |
| インポートで `dataSchema` 未指定エラー | `auto_generate_ids` が content スキーマで使えない | `"dataSchema": "content"` を明示指定 |
| データストア削除後に同じIDで再作成できない | 削除処理に数時間かかる | 別のIDで作成 |
| 検索結果が0件 | インデックス構築未完了 | 10分程度待機 |
| `403 SERVICE_DISABLED` | quota project 未指定 | `-H "x-goog-user-project: ${PROJECT_ID}"` を追加 |
| LLM が空レスポンスを返す | extractive_segments が大きすぎて thinking token が出力枠を圧迫 | セグメントを1200文字に制限 + `max_output_tokens` を8192に拡大 |

## 現在の環境情報

| 項目 | 値 |
|------|-----|
| プロジェクト | `poc-rag-490804` |
| プロジェクト番号 | `636243402764` |
| GCSバケット | `gs://poc-rag-490804-vais-eval` |
| データストアID | `vais-eval-ds-2` |
| Engine ID | `vais-eval-engine` |
| ドキュメント数 | 61（社内19 + Wikipedia42） |
| リージョン | `global`（Vertex AI Search の制約） |
