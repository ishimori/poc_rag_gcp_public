# DD-019-8: semanticテスト失敗の原因分析 — 詳細ドキュメント

親DD: [DD-019-8_semanticテスト失敗の原因分析.md](../DD-019-8_semanticテスト失敗の原因分析.md)

## ファイル一覧

| ファイル | 内容 | Phase |
|---|---|---|
| [test_cases.md](test_cases.md) | 成功/失敗ケース一覧、代表3件、初期仮説 | 0 |
| [da_review.md](da_review.md) | DA批判レビュー記録（全Phase分） | 0- |
| [phase1_diagnosis.md](phase1_diagnosis.md) | 検索段階の診断（サブタスク定義・コマンド・結果） | 1 |
| [phase2_experiments.md](phase2_experiments.md) | 対策実験の結果（top_k増・クエリ拡張・embedding検証） | 2 |
| [analysis_vector_search_failure.md](analysis_vector_search_failure.md) | ベクトル検索失敗の推理・仮説検討 | 2 |

## 現在の状況

- **Phase 0-1**: 完了。代表3件とも失敗段階A（検索で引けない）
- **Phase 2**: embedding検証中。仮説D（異常値）・B（次元不一致）は否定済み → 仮説A（similarity分散）が有力
