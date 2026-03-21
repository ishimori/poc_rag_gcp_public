# DD-019-8: semanticテスト失敗の原因分析

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 完了 |

## 目的

semantic テストタイプ（2/12 = 17%）の失敗原因を特定し、対策を実施してスコアを改善する。

## 詳細ドキュメント

| ファイル | 内容 |
|---|---|
| [test_cases.md](DD-019-8/test_cases.md) | 成功/失敗ケース一覧、代表3件、初期仮説 |
| [phase1_diagnosis.md](DD-019-8/phase1_diagnosis.md) | Phase 1 サブタスク定義・コマンド・結果 |
| [phase2_experiments.md](DD-019-8/phase2_experiments.md) | Phase 2 対策実験（top_k増・クエリ拡張）の結果 |
| [analysis_vector_search_failure.md](DD-019-8/analysis_vector_search_failure.md) | ベクトル検索失敗の推理・仮説検討 |
| [da_review.md](DD-019-8/da_review.md) | DA批判レビュー記録 |

## 決定事項

- **根本原因**: embedding の task_type 未指定 + 一般語キーワード検索の欠如（similarity 突出度不足 × wikipedia ノイズ89%の構造的問題）
- **対策1**: `embedder.py` に task_type 指定（RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY）を追加。再Ingest 必要
- **対策2**: `keyword_searcher.py` に一般語テキストマッチを追加。RRF統合で正解チャンクをブースト
- **結果**: Overall 50.0% → 75.7%（+25.7pt）、semantic 2/12(17%) → 8/12(67%)

## タスク一覧

### Phase 0: 事前精査
- [x] 📋 **各Phaseのタスク精査・詳細化**
- [x] 😈 **Devil's Advocate調査** → [da_review.md](DD-019-8/da_review.md)
- [x] 🔬 `scripts/verify_dd_019_8.py` で DD と eval_dataset.jsonl の整合性確認 → PASS

### Phase 1: 検索段階の診断 → [詳細](DD-019-8/phase1_diagnosis.md)
- [x] 代表3件を並行サブエージェントで診断 → **全件 失敗段階A（検索で引けない）**
- [x] 🔬 結果集約 → 上位10件が全て wikipedia 系。社内文書が1件も返らない
- [x] 😈 DA批判レビュー → [da_review.md](DD-019-8/da_review.md)

### Phase 2: 原因特定・対策検討 → [実験結果](DD-019-8/phase2_experiments.md) / [推理](DD-019-8/analysis_vector_search_failure.md)
- [x] 規模把握: wikipedia 403件(89%) vs 社内文書 51件(11%)
- [x] top_k=50 テスト → **解決不可能**（50件取得しても社内文書がほぼ0件）
- [x] クエリ拡張テスト → **解決不可能**（全結果がwikipedia系のまま）
- [x] **embedding 健全性チェック** → 仮説D（異常値）・B（次元不一致）を**否定**。embedding自体は正常
- [x] **cosine similarity 直接計算** → **根本原因特定**: similarity突出度不足 × wikipedia量的圧倒
- [x] 対策方針の策定 → [詳細](DD-019-8/phase2_experiments.md#対策方針)
  - **対策1**: `embed_text()` に task_type 指定（RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY）→ 再Ingest必要
  - **対策2**: keyword_searcher に一般語テキストマッチ追加 → RRFブーストで正解浮上
- [x] 対策1 実装 + 再Ingest（454チャンク）
- [x] 対策2 実装
- [x] 🔬 フル評価 → **Overall 50.0% → 75.7%（+25.7pt）、semantic 2/12 → 8/12（+50pt）**
- [x] 😈 DA批判レビュー → [da_review.md](DD-019-8/da_review.md)

### Phase 3: 評価・記録
- [x] DD-019-8 ログに結果を記録
- [x] DD-019 の子DD一覧のステータスを更新
- [x] 🔬 `scripts/verify_dd_019_8.py` で最終整合性チェック

## ログ

### 2026-03-21
- DD作成
- グループBフル評価で semantic 2/12 (17%) が最大ボトルネックと判明
- 失敗10件は全て「情報なし」回答 → 検索段階の問題が確定的
- 代表3件（semantic-001, 006, 011）で詳細分析する方針
- **Phase 0 DA発見**: DD記載の失敗ケース一覧が eval_dataset.jsonl と不一致
  - ID・クエリ・期待ソースにずれ（semantic-005〜012の範囲で6件に誤り）
  - 代表3件のIDも修正: 005→006、009→011
  - 検証スクリプト `scripts/verify_dd_019_8.py` で整合性を確認
  - 全DD横断調査: `scripts/verify_dd_test_ids.py` で14ファイルを検査。現行DDに実際のズレなし、アーカイブ済みDD-014に計画時と最終版の差異23件あり（履歴として残置）
  - **再発防止**: DDテンプレート Phase 0チェックリストにテストケースID検証ルールを追加
- **Phase 1 完了**: 3件とも失敗段階A。上位10件が全てwikipedia系、社内文書0件
- **Phase 2 中間**: top_k=50もクエリ拡張も無効。embedding異常の可能性 → 追加調査へ
- **Phase 2 根本原因特定**:
  - 仮説D（ゼロ/異常値）・B（次元不一致）は否定。embedding自体は正常（dim=768, norm=1.0）
  - **真の原因**: 成功ケース「Zoom」はsim=0.67で突出するが、失敗ケース「パスワード」はsim=0.58で突出しない
  - wikipedia(403件)のsimが0.44-0.52でわずかな差しかなく、量的に正解チャンクを圧倒
  - → similarity突出度不足 × ノイズ比率89%の構造的問題
- **対策実施・フル評価**:
  - 対策1: `embed_text()` に task_type 指定（RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY）→ 再Ingest(454チャンク)
  - 対策2: `keyword_searcher.py` に一般語テキストマッチ追加 → RRFブースト
  - **結果: Overall 50.0% → 75.7%（+25.7pt）、semantic 2/12(17%) → 8/12(67%)（+50pt）**
  - 評価結果: `results/eval_20260321_215058.json`
