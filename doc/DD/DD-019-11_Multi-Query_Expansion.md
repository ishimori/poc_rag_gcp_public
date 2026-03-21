# DD-019-11: Multi-Query Expansion（semantic 67%→90%）

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-22 | 2026-03-22 | 進行中 |

## 目的

ユーザークエリをLLMで複数の意味的バリエーションに展開して検索し、semantic カテゴリの残り4件の失敗を改善する。Overall +4〜6pt を狙う。

## 背景・課題

DD-019-8でEmbedding task_type指定 + キーワード検索追加により semantic 17%→67% まで改善したが、4件が依然失敗。ユーザーの短い曖昧な語彙と、文書側の具体的な専門用語との間にEmbeddingだけでは埋めきれないギャップがある。

### 外部LLM分析結果

- **GPT-4o**: Multi-Query Expansion を推奨（クエリを3〜5個に言い換え→全て検索→RRF統合）
- **Gemini**: HyDE（仮説文書Embedding）を推奨
- いずれも「検索前にクエリを意味拡張する」アプローチ。Multi-Queryの方が既存RRFに統合しやすい

詳細: [DD-019/llm_response_summary.md](DD-019/llm_response_summary.md)

## 検討内容

### アプローチ: Multi-Query Expansion

```
Query
  ↓
LLMで3〜4個の代替クエリを生成
  ↓
各クエリで検索（ベクトル + キーワード）
  ↓
RRF統合（重複doc_idはスコア加算）
  ↓
リランキング → 生成
```

### 変更対象

| ファイル | 変更内容 |
|---|---|
| `src/search/query_expander.py`（新規） | LLMでクエリを複数展開するモジュール |
| `src/search/flow.py` | 検索前にクエリ展開を挟む分岐追加 |
| `src/config.py` | `multi_query: bool = False` 追加 |
| `src/evaluate/scorer.py` | `FEATURE_MAP` に追加 |

### 設計ポイント

1. **展開数**: original + 3 = 計4本が最適（GPT推奨）
2. **RRF統合**: 既存の `hybrid.py` のRRFに展開クエリの結果も投入
3. **コスト**: LLM呼び出し+1回、検索×4。61文書規模なら許容
4. **プロンプト**: temperature=0で再現性確保。日本語クエリに対して日本語で展開

## 決定事項

（Phase 0で検討）

## タスク一覧

### Phase 0: 事前精査
- [ ] 📋 **各Phaseのタスク精査・詳細化**
  - semantic 失敗4件のクエリと失敗原因を確認
  - 展開プロンプトの設計
- [ ] 😈 **Devil's Advocate調査**

### Phase 1: 実装
（Phase 0の決定後に詳細化）

## ログ

### 2026-03-22
- DD作成（DD-019からの派生、外部LLM分析結果に基づく）

---

## DA批判レビュー記録
