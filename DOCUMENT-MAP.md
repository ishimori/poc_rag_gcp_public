# ドキュメントマップ

プロジェクト内の全ドキュメントの所在一覧。新規ドキュメント追加時は本ファイルも更新すること。

## ルート

| ファイル | 説明 |
|---------|------|
| [README.md](README.md) | プロジェクト概要・セットアップ |
| [CLAUDE.md](CLAUDE.md) | Claude Code 設定（DD/スキル/規約） |
| [DOCUMENT-MAP.md](DOCUMENT-MAP.md) | 本ファイル |

## 仕様書 (doc/spec/)

コード変更時に同期が必要なドキュメント群。

| ファイル | 説明 | 同期タイミング |
|---------|------|---------------|
| [app/database.md](doc/spec/app/database.md) | Firestoreスキーマ定義（3コレクション + ER図） | コレクション・フィールド変更時 |
| [app/api.md](doc/spec/app/api.md) | APIエンドポイント仕様（8エンドポイント） | エンドポイント変更時 |
| [app/screens.md](doc/spec/app/screens.md) | 画面・ルーティング仕様（6画面） | 画面変更時 |
| [infra/infrastructure.md](doc/spec/infra/infrastructure.md) | GCPインフラ構成・環境変数・依存パッケージ | サービス・環境変数変更時 |
| [infra/development.md](doc/spec/infra/development.md) | 開発・デプロイ手順 | 手順変更時 |

## リサーチ (doc/research/)

技術調査・検討メモ。

| ファイル | 説明 |
|---------|------|
| [00_全体構想.md](doc/research/00_全体構想.md) | プロジェクト全体構想 |
| [01_データ前処理.md](doc/research/01_データ前処理.md) | データ前処理の調査 |
| [01-2_コスト.md](doc/research/01-2_コスト.md) | コスト分析 |
| [02_チャンキング戦略.md](doc/research/02_チャンキング戦略.md) | チャンキング戦略 |
| [02-2_チャンク調整.md](doc/research/02-2_チャンク調整.md) | チャンクサイズ調整 |
| [03_セマンティック検索.md](doc/research/03_セマンティック検索.md) | セマンティック検索 |
| [03-2_深堀.md](doc/research/03-2_深堀.md) | 検索精度の深堀り |
| [04_リランキング.md](doc/research/04_リランキング.md) | リランキング技術 |
| [05_Genkit.md](doc/research/05_Genkit.md) | Genkit フレームワーク検討 |
| [06_セキュリティ.md](doc/research/06_セキュリティ.md) | セキュリティ設計 |
| [07_評価.md](doc/research/07_評価.md) | 評価パイプライン設計 |
| [08_UIUX.md](doc/research/08_UIUX.md) | UI/UX 設計 |

## ADR (doc/research/adr/)

アーキテクチャ意思決定記録。

| ファイル | 説明 |
|---------|------|
| [index.md](doc/research/adr/index.md) | ADR 一覧 |
| [ADR-001](doc/research/adr/ADR-001_ドキュメント解析.md) | ドキュメント解析 |
| [ADR-002](doc/research/adr/ADR-002_チャンキング.md) | チャンキング |
| [ADR-003](doc/research/adr/ADR-003_Embedding.md) | Embedding |
| [ADR-004](doc/research/adr/ADR-004_検索方式.md) | 検索方式 |
| [ADR-005](doc/research/adr/ADR-005_リランキング.md) | リランキング |
| [ADR-006](doc/research/adr/ADR-006_LLM.md) | LLM |
| [ADR-007](doc/research/adr/ADR-007_認証.md) | 認証 |
| [ADR-008](doc/research/adr/ADR-008_フレームワーク.md) | フレームワーク |
| [ADR-009](doc/research/adr/ADR-009_フロントエンド.md) | フロントエンド |

## 横断トピック (doc/research/cross-cutting/)

| ファイル | 説明 |
|---------|------|
| [cost-management.md](doc/research/cross-cutting/cost-management.md) | コスト管理 |
| [firestore-schema.md](doc/research/cross-cutting/firestore-schema.md) | Firestoreスキーマ設計 |
| [metadata-design.md](doc/research/cross-cutting/metadata-design.md) | メタデータ設計 |
| [prompt-design.md](doc/research/cross-cutting/prompt-design.md) | プロンプト設計 |

## プレゼン資料 (doc/presentation/)

| フォルダ | 説明 |
|---------|------|
| [20260320/](doc/presentation/20260320/) | RAG技術13選プレゼン（00〜13 + images/） |

## DD (doc/DD/)

設計文書の進捗管理。→ [doc/DD/INDEX.md](doc/DD/INDEX.md)

## サブディレクトリ README

| パス | 説明 |
|------|------|
| [src/README.md](src/README.md) | バックエンドモジュール構成 |
| [ui/README.md](ui/README.md) | フロントエンド構成 |
| [scripts/README.md](scripts/README.md) | ユーティリティスクリプト |
| [doc/README.md](doc/README.md) | ドキュメントフォルダ構成 |
| [test-data/README.md](test-data/README.md) | テストデータセット |
