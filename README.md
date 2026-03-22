# エンタープライズRAG PoC

社内ドキュメントに基づいてAIが質問に回答するRAG（Retrieval-Augmented Generation）チャットシステムと、精度チューニングのための管理画面を提供するPoCプロジェクト。

## PoCの成果

| 指標 | 値 |
|------|----|
| 最終スコア（自前RAG、Gemini 3 Flash） | **77.0%** (57/74) |
| 最終スコア（Vertex AI Search、チューニングなし） | **84.4%** (54/64) |
| ベースライン | 28.4% (21/74) |
| 実装技術数 | 13技術 |
| テストケース数 | 74件 × 12カテゴリ |

精度改善の詳細な記録は [doc/record/rag_improvement_history.md](doc/record/rag_improvement_history.md) を参照。

### 実装した主要技術

- **検索**: ハイブリッド検索（ベクトル + キーワード）、メタデータスコアリング、Vertex AI Ranker（リランキング）
- **前処理**: Contextual Retrieval、AIフィルタ自動生成、曖昧判定・聞き返し
- **権限**: 権限フィルタ（allowed_groups）、Shadow Retrieval（権限除外検出）

### 次フェーズに向けて

本 PoC はサンプルデータ（61ファイル / 74件の評価セット）を用いた技術検証フェーズとして完了。
**次フェーズでは本番相当データに切り替え、本 PoC の知見（技術スタック・チューニング手法・評価基盤）をそのまま活用して再度実施する予定。**

検索基盤の選定（自前RAG vs Vertex AI Search）については [doc/research/cross-cutting/vertex-ai-search-comparison.md](doc/research/cross-cutting/vertex-ai-search-comparison.md) を参照。

---

## 技術スタック

- **フロントエンド**: React 19 + TypeScript + Vite（`ui/`）
- **バックエンド**: Python 3.12 + Cloud Functions Gen2（`main.py`, `src/`）
- **データベース**: Firestore（ベクトルDB兼ドキュメントストア）
- **AI/ML**: Vertex AI Gemini 3 Flash（LLM）+ text-embedding-005（768次元）+ Discovery Engine（リランキング）
- **インフラ**: Firebase Hosting + Cloud Functions / GCP asia-northeast1

## ディレクトリ構成

```
main.py              # Cloud Functions エントリポイント（chat + admin）
src/                 # バックエンド（RAGパイプライン）
ui/                  # フロントエンド（チャット + 管理画面）
scripts/             # 開発・運用スクリプト
test-data/           # テストデータ（ソース文書 + 評価データセット）
doc/                 # ドキュメント（仕様書・リサーチ・DD・プレゼン）
```

各ディレクトリの詳細は配下の README.md を参照。全ドキュメントの所在は [DOCUMENT-MAP.md](DOCUMENT-MAP.md) を参照。

## セットアップ

### 前提条件

- Python >= 3.12 / Node.js >= 18 / uv / Firebase CLI
- GCP プロジェクト（Firestore, Vertex AI, Discovery Engine 有効化済み）
- `gcloud auth application-default login` 実行済み

### インストール

```bash
# 環境変数設定
cp .env.local.example .env.local
# .env.local を編集: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION

# Python 依存
uv sync

# フロントエンド依存
cd ui && npm install && cd ..
```

### 開発サーバー起動

```bash
bash scripts/dev.sh        # 起動（chat:8081 + admin:8082 + UI:5180）
bash scripts/dev.sh stop   # 停止
```

詳細は [doc/spec/infra/development.md](doc/spec/infra/development.md) を参照。

## テスト・評価

- 自動評価パイプライン: `test-data/golden/eval_dataset.jsonl`（74件 × 12パターン）
- ハイブリッドスコアリング: LLM-as-Judge（主判定）+ キーワードマッチ（参考値）
- Operations Monitor（`/admin/tuning`）から Ingest → Evaluate → スコア比較のサイクルを実行可能

## セキュリティ

- PoCフェーズのため認証なし
- `security_level` / `allowed_groups` による権限フィルタ実装済み（80%達成）

## ドキュメント

- [DOCUMENT-MAP.md](DOCUMENT-MAP.md) — 全ドキュメントの所在一覧
- [doc/spec/](doc/spec/) — 仕様書（DB・API・画面・インフラ・開発手順）
- [doc/research/](doc/research/) — 技術調査メモ・ADR
- [doc/DD/INDEX.md](doc/DD/INDEX.md) — DD（設計文書）の進捗管理
