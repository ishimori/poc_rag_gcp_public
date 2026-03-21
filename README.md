# エンタープライズRAG PoC

社内ドキュメントに基づいてAIが質問に回答するRAG（Retrieval-Augmented Generation）チャットシステムと、精度チューニングのための管理画面を提供するPoCプロジェクト。

## 技術スタック

- **フロントエンド**: React 19 + TypeScript + Vite（`ui/`）
- **バックエンド**: Python 3.12 + Cloud Functions Gen2（`main.py`, `src/`）
- **データベース**: Firestore（ベクトルDB兼ドキュメントストア）
- **AI/ML**: Vertex AI Gemini 2.5（LLM）+ text-embedding-005（768次元）+ Discovery Engine（リランキング）
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
- 未実装機能テスト（ambiguous/security）は `requires` フィールドで自動除外
- 現在のベースライン: 21/64 (32.8%)
- 管理画面（`/admin/tuning`）から Ingest → Evaluate → スコア比較のサイクルを実行可能

## セキュリティ

- PoCフェーズのため認証なし
- `security_level` / `allowed_groups` フィールドは chunks に存在するがフィルタ未実装

## ドキュメント

- [DOCUMENT-MAP.md](DOCUMENT-MAP.md) — 全ドキュメントの所在一覧
- [doc/spec/](doc/spec/) — 仕様書（DB・API・画面・インフラ・開発手順）
- [doc/research/](doc/research/) — 技術調査メモ・ADR
- [doc/DD/INDEX.md](doc/DD/INDEX.md) — DD（設計文書）の進捗管理
