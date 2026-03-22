# DD-025: Gemini 3 Flash モデル切替と再評価

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-22 | 2026-03-22 | 完了 |

## 目的

RAGの回答生成モデルを Gemini 2.5 Flash → Gemini 3 Flash に切り替え、自前RAG / Vertex AI Search の両方で再評価する。過去スコアとの比較により、モデル切替の効果を定量化する。

## 背景・課題

- Gemini 3 Flash が2026年3月にリリース。「Pro級の知能をFlash価格で」という位置づけ
- 現在のPoCは `gemini-2.5-flash` を使用中
- DD-024で Vertex AI Search 84.4% を計測済みだが、これも 2.5 Flash での回答生成
- モデル切替で回答品質が向上すれば、自前/Vertex 両方のスコアが改善する可能性

## 前提

- **DD-022（チャンク実験）の結果確定後に着手** — 変数を1つに絞るため
- **LLM-as-Judge は gemini-2.5-flash 据え置き** — 判定基準を統一し、過去スコアと比較可能にする

## 検討内容

### 変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `src/config.py` | `llm_model` → `gemini-3-flash-preview`、`llm_location` → `global` 追加 |
| `src/search/flow.py` | 旧SDK(`vertexai.GenerativeModel`) → 新SDK(`google.genai.Client`) に移行 |
| `src/search/clarifier.py` | 同上（新SDKに移行、`config.llm_model` を参照） |
| `src/evaluate/scorer.py` | **変更なし** — LLM-as-Judge は `gemini-2.5-flash` + `asia-northeast1`（旧SDK）のまま据え置き |

### リージョン整理

| location | 用途 |
|---|---|
| `asia-northeast1`（`config.location`） | Firestore、Embedding、LLM-as-Judge |
| `global`（`config.llm_location`） | Gemini 3 Flash（回答生成・曖昧判定）、Vertex AI Search、Reranking |

### 評価マトリクス

| # | 検索エンジン | 回答モデル | 比較対象 |
|---|------------|-----------|---------|
| 1 | 自前RAG（Firestore） | Gemini 3 Flash | DD-019-9 の 85.1%（2.5 Flash） |
| 2 | Vertex AI Search | Gemini 3 Flash | DD-024 の 84.4%（2.5 Flash） |

## 決定事項

- モデルID: `gemini-3-flash-preview`
- location: `global`（`asia-northeast1` では404）
- SDK: `google.genai`（旧`vertexai` SDKではGemini 3系が呼べない）
- LLM-as-Judge: `gemini-2.5-flash` 据え置き（旧SDK + `asia-northeast1`）

### 精度追求の中止判断（2026-03-22）

DD-025の評価結果と一連の計測から、以下の知見が得られた:

1. **検索エンジンを変えてもスコアは変わらない** — 自前RAG 85% ≈ Vertex 84%（DD-024）
2. **LLMモデルを上げてもスコアは変わらない** — 2.5 Flash ≈ 3 Flash、むしろ低下（DD-025）
3. **制御層を個別に調整しても数ケース改善するだけ** — Clarifier/Gate修正で最大+5pt程度（DD-024-3）
4. **計測コストが高額** — 74件×LLM呼び出し（回答生成+LLM-as-Judge）のAPI費用が蓄積

**結論: 現在の評価データ・文書セットでは85%前後が天井。これ以上の精度追求はROIが低い。DD-023（報告書作成）に舵を切る。**

以下のDDを「見送り」とする:
- **DD-024-2**（ログUI改善）→ 見送り。精度に寄与しない
- **DD-024-3**（Vertex検索精度改善）→ Phase 1完了で中断。残施策のROIが低い
- **DD-025**（本DD）→ 計測完了。精度追求は中止
- **DD-026**（SFT）→ 見送り。LLMモデル性能は既にボトルネックではないと判明

## タスク一覧

### Phase 0: 事前精査
- [x] 📋 **各Phaseのタスク精査・詳細化**
- [x] 😈 **Devil's Advocate調査**
  - モデルID → `gemini-3-flash-preview`（Web検索 + API一覧で確認）
  - リージョン → `asia-northeast1` で404。`global` で動作確認済み
  - max_output_tokens → 65,536（2.5 Flashと同等以上）
  - **追加DA**: 旧SDK(`vertexai`)ではGemini 3系が呼べない → 新SDK(`google.genai`)に移行が必要

### Phase 1: モデル切替
- [x] `src/config.py` — `llm_model` を `gemini-3-flash-preview` に変更、`llm_location = "global"` 追加
- [x] `src/search/flow.py` — 新SDK(`google.genai.Client`)に移行
- [x] `src/search/clarifier.py` — 同上
- [x] 🔬 **機械検証**: 自前RAG で `ネジ999999の材質は？` → `SUS304` 正答 ✅
- [x] 🔬 **機械検証**: Vertex AI Search で `VPN接続の手順` → 手順回答 ✅
- [x] 🔬 **機械検証**: clarifier で `エラーが出る` → 曖昧判定 ✅
- [x] 😈 **DA批判レビュー**

### Phase 2: 再評価（自前RAG × Gemini 3 Flash）
- [x] 3コレクション（chunks_600, chunks_800, chunks_1200）で並列評価実行
- [x] 🔬 **機械検証**: 結果JSON 3件が生成

**結果:**

| チャンクサイズ | 3 Flash Overall | 2.5 Flash 参考 | 差分 |
|:---:|:-:|:-:|:-:|
| 600 | **77.0%** (57/74) | — | — |
| 800 | **77.0%** (57/74) | 81.1% | -4.1pt |
| 1200 | **75.7%** (56/74) | 85.1% | -9.4pt |

**カテゴリ別（3 Flash）:**

| カテゴリ | 600 | 800 | 1200 |
|---------|:-:|:-:|:-:|
| exact_match (8) | 100% | 100% | 100% |
| similar_number (6) | 83.3% | 100% | 100% |
| semantic (12) | 50.0% | 33.3% | 33.3% |
| step_sequence (7) | 100% | 85.7% | 85.7% |
| multi_chunk (7) | 100% | 71.4% | 71.4% |
| unanswerable (5) | 60.0% | 60.0% | 60.0% |
| ambiguous (5) | 100% | 100% | 100% |
| cross_category (5) | 60.0% | 60.0% | 60.0% |
| security (5) | 60.0% | 100% | 80.0% |
| noise_resistance (6) | 33.3% | 83.3% | 100% |
| table_extract (5) | 100% | 100% | 80.0% |
| temporal (3) | 100% | 66.7% | 66.7% |

**所見:**
- 3 Flash は 2.5 Flash より全体スコアが低下（77% vs 85%）
- unanswerable が 100%→60% に悪化（Shadow Retrieval の誤発動で「権限なし」と回答するケースが増加）
- cross_category も 100%→60% に悪化（同様にShadow Retrieval誤発動）
- semantic は chunk_600 が最良（50%）だが、2.5 Flash 時代と同水準
- noise_resistance は chunk_1200 が100%で最良

- [x] 😈 **DA批判レビュー**: 3 Flashでスコアが下がった。clarifier誤判定とShadow Retrieval誤発動が主な悪化要因だが、原因がプロンプトの問題かモデルの特性変化かは未特定

### Phase 3: 再評価（Vertex AI Search × Gemini 3 Flash）
- [x] `config.use_vertex_ai_search = True` で評価実行
- [x] 🔬 **機械検証**: `results/eval_vertex_3flash_20260322_141719.json` 生成確認
- [x] 😈 **DA批判レビュー**

**結果: Vertex × 3 Flash = 79.7% (59/74)**

| カテゴリ | Vertex × 3 Flash | Vertex × 2.5 Flash (DD-024) |
|---------|:-:|:-:|
| exact_match (8) | **100%** | 100% |
| similar_number (6) | **100%** | 83.3% |
| semantic (12) | 58.3% | 66.7% |
| step_sequence (7) | 85.7% | 100% |
| multi_chunk (7) | 71.4% | 85.7% |
| unanswerable (5) | **100%** | 100% |
| ambiguous (5) | **100%** | 100% |
| cross_category (5) | 80.0% | 100% |
| security (5) | 40.0% | 40.0% |
| noise_resistance (6) | **83.3%** | 50.0% |
| table_extract (5) | 60.0% | 100% |
| temporal (3) | **100%** | 100% |

### Phase 4: 比較・記録
- [x] 比較表を作成

  **2×2 マトリクス（Overall）:**

  | 検索エンジン | 2.5 Flash | 3 Flash | 差分 |
  |---|:-:|:-:|:-:|
  | 自前RAG (chunk=800) | 81.1% | 77.0% | **-4.1pt** |
  | 自前RAG (chunk=1200) | 85.1% | 75.7% | **-9.4pt** |
  | Vertex AI Search | 84.4% | 79.7% | **-4.7pt** |

  **3 Flash × チャンクサイズ比較:**

  | チャンクサイズ | 自前RAG |
  |:-:|:-:|
  | 600 | 77.0% |
  | 800 | 77.0% |
  | 1200 | 75.7% |

- [x] `doc/record/rag_improvement_history.md` に結果追記（3F-600/800/1200, 3F-V の4行追加）
- [x] `doc/research/cross-cutting/vertex-ai-search-comparison.md` に「Gemini 3 Flash での再評価」セクション追記
- [x] 😈 **DA批判レビュー**: 全パターンで2.5 Flashより低下。原因未特定（プロンプト起因かモデル特性かの切り分けが必要）。Vertexのnoise_resistanceは83.3%に改善（DD-024-3のWikipediaペナルティ効果）

## ログ

### 2026-03-22
- DD作成
- 前提: DD-022（チャンク実験）完了後に着手
- Phase 0 完了: モデルID `gemini-3-flash-preview`、location `global` 確認
- Phase 1 完了: config.py / flow.py / clarifier.py を新SDK(`google.genai`)に移行。自前RAG・Vertex・clarifier全て動作確認済み
  - 失敗: `asia-northeast1` で404 → `config.llm_location = "global"` で解決
  - 失敗: 旧SDK(`vertexai.GenerativeModel`)ではGemini 3系が呼べない → `google.genai.Client` に移行
- Phase 2完了: 自前RAG × 3 Flash（chunks_600: 77.0%, chunks_800: 77.0%, chunks_1200: 75.7%）
- Phase 3完了: Vertex × 3 Flash = 79.7%
  - バグ修正: `vertex_ai_searcher.py` の `UnboundLocalError`（検索結果0件時に変数 `i` が未定義）
- Phase 4完了: 比較表作成、`rag_improvement_history.md` 追記
- **結論: Gemini 3 Flash は 2.5 Flash より全パターンで低下（-4〜9pt）。悪化原因の切り分け（プロンプト vs モデル特性）が今後の課題**

---

## DA批判レビュー記録

### Phase 0 DA批判レビュー

**DA観点:** モデル切替で予期しない副作用はないか？

| # | 発見した問題/改善点 | 重要度 | 再現手順（高/中は必須） | DA観点 | 対応 |
|---|-------------------|--------|----------------------|--------|------|
| 1 | 旧SDK(`vertexai`)ではGemini 3系が呼べない | 高 | `GenerativeModel('gemini-3-flash-preview')` → 404 | 技術的実現性 | ✅ 新SDK(`google.genai`)に移行 |
| 2 | `asia-northeast1` では Gemini 3 Flash が利用不可 | 高 | `vertexai.init(location='asia-northeast1')` → 404 | リージョン制約 | ✅ `config.llm_location = "global"` を分離 |
| 3 | LLM-as-Judge を 3 Flash に変えると過去スコアと比較不能 | 中 | — | 評価の公平性 | ✅ scorer.py は `gemini-2.5-flash` + 旧SDK のまま据え置き |
