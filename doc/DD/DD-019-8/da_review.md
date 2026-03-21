# DD-019-8: DA批判レビュー記録

<!-- DA批判レビューの手順・品質フィルター・再チェック条件は doc/da-method.md を参照 -->

## Phase 0 DA（2026-03-21）

### 指摘1: DD記載データの不正確さ【Critical → 修正済み】
- **事実**: DD作成時の失敗ケース一覧で ID・クエリ・期待ソースが eval_dataset.jsonl と6件不一致
- **原因**: LLMによるDD生成時にテストデータを正確に参照しなかった
- **対策**: eval_dataset.jsonl から正確に転記し、`scripts/verify_dd_019_8.py` で整合性を機械検証
- **再発防止**: DDにテストケースを記載する際は必ず検証スクリプトを通す

### 指摘2: テストデータ側の問題はないか？【検証済み → 問題なし】
- **検証結果**: 期待ソース文書を全件確認。全ての期待回答に対応する情報がソース文書に存在する
  - semantic-001「PCが重い」→ pc_troubleshoot.md Q1「PCの動作が遅い（重い）」に完全対応
  - semantic-006「パスワードの条件は？」→ it_helpdesk_faq.md FAQ-001 に12文字以上等の条件記載
  - semantic-011「タクシー代を会社に請求したい」→ expense_manual.md 4.1交通費にタクシー規定あり

### 指摘3: contextual_retrieval が有効なのに17%は想定外か？【要注意】
- **事実**: `config.py:22` で `contextual_retrieval: bool = True` が有効
- **懸念**: contextual_retrieval はチャンクに文脈情報を付与して検索精度を上げる手法。それが有効でも17%というのは、チャンキング自体か embedding の問題の可能性が高い
- **Phase 1 で確認**: Firestoreのチャンクに contextual_retrieval テキストが実際に付与されているか検証する

### 指摘4: 成功2件との比較分析が必要【Medium】
- **事実**: semantic-005「Zoomは使える？」と semantic-007「USBメモリを使いたい」は成功している
- **懸念**: 「Zoomは使える？」は FAQ-019 に直接「Zoom」というキーワードがある。成功ケースは**キーワードが一致**しているだけで、真の意味理解ではない可能性
- **提案**: Phase 1 で成功ケースも1件分析し、なぜ通るのかを比較する

### 指摘5: hybrid_search のキーワード検索は semantic ケースに効かない【Low】
- **事実**: `keyword_searcher.py` は型番・品番のパターンマッチ。「PCが重い」のような口語クエリにはキーワードヒットしない
- **影響**: semantic ケースでは事実上ベクトル検索のみに依存している。hybrid_search の恩恵がない
- **確認**: Phase 1 で keyword_search の結果件数も記録する
