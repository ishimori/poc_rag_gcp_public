# 意思決定記録（ADR）

本プロジェクトの技術選定における意思決定を記録する。

## 選定基準

すべての意思決定は以下の3つの観点で判断する。

1. **気軽に試せること** — セットアップが軽く、すぐに動かせる
2. **コストを抑えられること** — 無料枠 or 最安の選択肢を優先
3. **チューニング効果が数値評価できること** — ブラックボックスにしない

## ADR一覧

| # | テーマ | 採用 |
|---|--------|------|
| [ADR-001](ADR-001_ドキュメント解析.md) | ドキュメント解析手法 | Gemini 2.5 Flash（マルチモーダル） |
| [ADR-002](ADR-002_チャンキング.md) | チャンキング方式 | Recursive Character Text Splitter |
| [ADR-003](ADR-003_Embedding.md) | Embeddingモデル | gemini-embedding-001 |
| [ADR-004](ADR-004_検索方式.md) | 検索方式 | ベクトル検索（Firestoreのみ） |
| [ADR-005](ADR-005_リランキング.md) | リランキング | Vertex AI Ranking API |
| [ADR-006](ADR-006_LLM.md) | LLMモデル | Gemini 2.5 Flash |
| [ADR-007](ADR-007_認証.md) | 認証方式 | Firebase Auth |
| [ADR-008](ADR-008_フレームワーク.md) | フレームワーク | Genkit |
| [ADR-009](ADR-009_フロントエンド.md) | フロントエンド | Firebase Hosting |
