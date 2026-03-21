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

- **デフォルトOFF**（`config.multi_query = False`）で既存動作を維持
- 展開数: `config.multi_query_count = 3`（original + 3 = 計4クエリ）
- `hybrid.py` のRRFに統合（各クエリのベクトル検索 + キーワード検索結果を全て投入）
- 温度0で再現性確保
- 新規モジュール: `src/search/query_expander.py`

## タスク一覧

### Phase 1: 実装 ✅
- [x] `src/config.py`: `multi_query: bool = False` + `multi_query_count: int = 3` 追加
- [x] `src/search/query_expander.py`（新規）: LLMでクエリを複数展開するモジュール
- [x] `src/search/hybrid.py`: `config.multi_query` ON時に展開クエリでも検索し、全結果をRRF統合
- [x] `src/evaluate/scorer.py`: `FEATURE_MAP` に `multi_query` 追加
- [x] 🔬 **機械検証（構文）**: `py_compile` 全ファイルOK

## ログ

### 2026-03-22
- DD作成（DD-019からの派生、外部LLM分析結果に基づく）
- Phase 1完了:
  - `query_expander.py` 新規作成（Gemini 2.5 Flash, 温度0, JSON配列出力）
  - `hybrid.py` にMulti-Query統合（全クエリの検索結果をRRFに投入）
  - デフォルトOFF。`config.multi_query = True` で有効化

---

## DA批判レビュー記録
