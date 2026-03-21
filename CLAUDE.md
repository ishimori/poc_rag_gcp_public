# DD-Know-How プロジェクト設定

このファイルは DD-Know-How をベースにしたプロジェクトの Claude Code 設定テンプレートです。

## DD設定

- **フロー**: full（9ステップ）
- **DDフォルダ**: `doc/DD/`
- **DD索引**: `doc/DD/INDEX.md` — DD作成・ステータス変更・アーカイブ時に必ず更新すること
- **アーカイブ**: `doc/DD/archived/`
- **テンプレート**: `doc/templates/dd_template.md`

## 利用可能なスキル

> スキルは `.claude/skills/` に配置されています（skills形式）

### DD管理
- `/dd new タイトル` - 新規DD作成
- `/dd status` - 進捗確認
- `/dd list` - DD一覧
- `/dd log メモ` - ログ追記
- `/dd archive 番号` - アーカイブ
- DA メソッド: `doc/da-method.md`（DA品質フィルター・再チェック条件）
- `/setup パス` - 外部プロジェクトへDD導入

## 開発フロー

### Standard（5ステップ）
1. DD作成
2. 実装
3. テスト
4. レビュー
5. コミット・アーカイブ

### Full（9ステップ）
1. DD作成
2. 仕様確認
3. 実装前チェック
4. コーディング
5. テスト作成
6. コード検証
7. レビュー
8. 仕様書同期
9. コミット・アーカイブ

詳細は `doc/development-flow.md` または `doc/development-flow-full.md` を参照。

## プロジェクト概要

エンタープライズRAG（Retrieval-Augmented Generation）のPoCプロジェクト。社内ドキュメントに基づいてAIが質問に回答するチャットシステムと、精度チューニングのための管理画面を提供する。

## 技術スタック

- **フロントエンド**: React 19 + TypeScript + Vite（`ui/`）
- **バックエンド**: Python 3.12 + Cloud Functions Gen2（`main.py`, `src/`）
- **データベース**: Firestore（ベクトルDB兼ドキュメントストア）
- **AI/ML**: Vertex AI Gemini 2.5（LLM）+ text-embedding-005（768次元）+ Discovery Engine（リランキング）
- **インフラ**: Firebase Hosting + Cloud Functions / GCP asia-northeast1

## ディレクトリ構成

```
main.py              # Cloud Functions エントリポイント（chat + admin）
src/
├── config.py        # 設定クラス（環境変数 + チューニングパラメータ）
├── search/          # RAGパイプライン（retriever, reranker, flow）
├── ingest/          # インジェスト（chunker, embedder, store）
├── evaluate/        # 評価（scorer, runner, reporter）
└── browse/          # データエクスポート
ui/src/
├── App.tsx          # チャット画面
├── admin/           # 管理画面（Dashboard, Tuning, DataBrowser, History, Logs）
└── main.tsx         # React Router ルーティング
test-data/           # テストデータ（sources/ + golden/）
scripts/             # 開発スクリプト（dev.sh 等）
doc/spec/            # 仕様ドキュメント
├── app/             # アプリ仕様（database.md, api.md, screens.md）
└── infra/           # 環境構成（infrastructure.md, development.md）
```

## コーディング規約

- Python: 型ヒント使用、`from __future__ import annotations`
- TypeScript: strict モード、React 関数コンポーネント
- 環境変数は `src/config.py` で一元管理（`Config` クラス）

## テスト方針

- 自動評価パイプライン: `test-data/golden/eval_dataset.jsonl`（45件 × 10パターン）
- キーワードマッチによるスコアリング（DD-013 で改善検討中）
- 管理画面から Ingest → Evaluate → スコア比較のサイクルを実行可能

## セキュリティ要件

- PoCフェーズのため認証なし
- `security_level` / `allowed_groups` フィールドは chunks に存在するがフィルタ未実装（DD-013 調査対象）

## ドキュメント更新ルール

**DB / API / 画面を変更したら、対応する `doc/spec/` ファイルを同期すること。**

| 変更内容 | 更新先 |
|---------|--------|
| Firestore コレクション・フィールド追加/変更 | `doc/spec/app/database.md` |
| API エンドポイント追加/変更 | `doc/spec/app/api.md` |
| 画面・ルーティング追加/変更 | `doc/spec/app/screens.md` |
| GCPサービス・環境変数・ポート変更 | `doc/spec/infra/infrastructure.md` |
| 開発手順・デプロイ手順変更 | `doc/spec/infra/development.md` |
