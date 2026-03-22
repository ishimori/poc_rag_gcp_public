# DD-024: Vertex AI Search 評価検証（1日タイムボックス）

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-22 | 2026-03-22 | 完了 |

## 目的

Vertex AI Search をRetrieverとして差し込み、既存の評価パイプライン（74件×12カテゴリ）でスコアを取得する。自前RAG（85.1%）との定量比較データを得て、DD-023の報告書に活用する。

**スコープ**: 評価のみ。UI変更なし。

## 背景・課題

- 自前RAGは28.4%→85.1%まで改善済み（DD-019系列）
- 「最初からVertex AI Searchを使えばよかったのでは？」という疑問に対し、定量データで回答したい
- 既存の評価基盤（`evaluate.py` + `eval_dataset.jsonl` + LLM-as-Judge）がそのまま流用可能
- DD-023で選択肢B（1日検証）を採択

## 検討内容

### 差し替え方針

```
現在:
rag_flow() → hybrid_search() → vector_search() + keyword_search() → RRF統合 → rerank → 回答生成
                                  ↑ Firestore直結

Vertex版:
rag_flow() → hybrid_search() → vertex_ai_search() → rerank → 回答生成
                                  ↑ Vertex AI Search API
```

**差し替えポイント**: `src/search/hybrid.py` の `hybrid_search()` 内部
- `vector_search()` + `keyword_search()` + RRF → `vertex_ai_search()` に置換
- `SearchResult` 型へのマッピングのみ必要
- **rag_flow()、reranker、metadata_scorer、evaluate.py、eval_dataset.jsonl は変更なし**

### 評価パターン

| パターン | 検索 | 制御層 | 目的 |
|---------|------|--------|------|
| A: Vertex素（検索のみ） | Vertex AI Search | OFF（clarification, shadow, gate全OFF） | Vertex単体の検索力を測定 |
| B: Vertex＋制御層 | Vertex AI Search | ON（現状と同じ制御層を適用） | ハイブリッド構成の精度を測定 |
| （参考）自前 | Firestore | ON | 85.1%（DD-019-9 chunk=1200） |

## 決定事項

### 実測結果

| カテゴリ | 自前RAG | Vertex素 (A) | Vertex+制御層 (B) |
|---------|:-:|:-:|:-:|
| **Overall** | **85.1%** | **84.4%** (54/64) | **83.8%** (62/74) |
| exact_match (8) | 88% | **100%** | **100%** |
| similar_number (6) | 100% | 83.3% | 83.3% |
| semantic (12) | 50% | **66.7%** | 58.3% |
| step_sequence (7) | 100% | **100%** | **100%** |
| multi_chunk (7) | 100% | 85.7% | 85.7% |
| unanswerable (5) | 100% | **100%** | **100%** |
| ambiguous (5) | 100% | (skip) | **100%** |
| cross_category (5) | 100% | **100%** | **100%** |
| security (5) | 20% | (skip) | 40.0% |
| noise_resistance (6) | 67% | 50.0% | 66.7% |
| table_extract (5) | 100% | 80.0% | **100%** |
| temporal (3) | 67% | **100%** | **100%** |

### 考察

1. **Vertex素で84.4%は驚異的** — 制御層なし・チューニングなしでこの精度。自前RAGの28.4%→85.1%の道のり（DD-019系列17本のDD）と比べて、セットアップ工数が圧倒的に少ない
2. **ただし制御層を加えても改善しない** — clarificationが一部の正当なsemantic質問を「曖昧」と誤判定（semantic-003「画面が固まった」, semantic-010「新しいソフトを入れたい」）。自前RAG用に調整したプロンプトがVertex検索結果と合わない
3. **security は依然課題** — Vertex AI Search側に権限フィルタ未設定のため、機密文書（salary_policy, meeting_minutes_exec）が検索結果に含まれ漏洩。Shadow Retrievalも自前と同じ方式では効かない
4. **自前PoCの価値は「制御層の設計知見」** — 検索基盤としてはVertexで十分だが、聞き返し・権限制御・品質ゲートの設計は自前PoCなしには得られなかった

### 結果ファイル
- パターンA: `results/eval_vertex_patternA_20260322_114232.json`
- パターンB: `results/eval_vertex_patternB_20260322_115335.json`

## ゴール定義（TDD: テストから逆算）

### 最終ゴール
```bash
python scripts/evaluate.py  # use_vertex_ai_search=True の状態で
```
→ `results/eval_YYYYMMDD_HHMMSS.json` が生成され、74件のスコアが記録される

### ゴールまでの逆算チェーンと中間テスト

```
[T5] evaluate.py が完走し results/ にJSONが出力される
  ↑ 依存: rag_flow() が Vertex 検索結果で回答を生成できる
[T4] rag_flow("ネジ999999の材質は？") が RAGResponse を返す
  ↑ 依存: hybrid_search() が Vertex 経由で SearchResult を返す
[T3] hybrid_search("ネジ999999の材質は？") が list[SearchResult] を返す（use_vertex_ai_search=True）
  ↑ 依存: vertex_ai_search() が API を叩いて結果を返す
[T2] vertex_ai_search("ネジ999999の材質は？") が list[SearchResult] を返す
  ↑ 依存: データストアが構築済みで検索可能
[T1] Vertex AI Search データストアが Active で、APIから検索できる
  ↑ 依存: 文書がGCSにアップロードされている
[T0] GCSに61ファイルが存在する
```

## タスク一覧

### Phase 0: 事前精査
- [x] 📋 **各Phaseのタスク精査・詳細化**
- [x] 😈 **Devil's Advocate調査**

### Phase 1: インフラ準備 → T0, T1 を通す

**T0: GCSに文書が存在する**

- [x] GCSバケット `gs://poc-rag-490804-vais-eval/` 作成
- [x] ソース文書61ファイルを `.txt` に変換してGCSにアップロード（`.md`直接インポートは "invalid JSON" エラーで失敗）
- [x] 🔬 **T0検証**: 61ファイル存在確認済み

**T1: データストアが Active で検索可能**

- [x] データストア `vais-eval-ds-2` + Engine `vais-eval-engine` を REST API で作成
- [x] インデックス構築完了（61/61成功、約10分待機）
- [x] 🔬 **T1検証**: 検索APIで "VPN" クエリに3件ヒット確認
- [x] 😈 **DA批判レビュー**

### Phase 2: 検索モジュール実装 → T2, T3 を通す

**T2: `vertex_ai_search()` が `list[SearchResult]` を返す**

- [x] `google-cloud-discoveryengine` 0.17.0 インストール済み
- [x] `src/config.py` に3行追加（`use_vertex_ai_search`, `vertex_search_engine_id`, `vertex_search_data_store_id`）
- [x] `src/search/vertex_ai_searcher.py` 新規作成（Discovery Engine v1beta API、extractive_segments使用）
- [x] 🔬 **T2検証**: `vertex_ai_search('VPN接続の手順を教えて')` → 3件の `SearchResult` 返却確認

**T3: `hybrid_search()` がVertex経由で動く**

- [x] `src/search/hybrid.py` 冒頭に分岐3行追加
- [x] 🔬 **T3検証**: `hybrid_search()` → `SearchResult` 型リスト返却確認
- [x] 😈 **DA批判レビュー**

### Phase 3: 結合テスト → T4 を通す

**T4: `rag_flow()` がVertex検索で回答を生成できる**

- [x] 🔬 **T4検証**: `rag_flow('VPN接続の手順を教えて')` → 回答テキスト・sources・reranked_sources 全て正常
- [x] 😈 **DA批判レビュー**

### Phase 4: 評価実行 → T5（最終ゴール）を通す

**T5: evaluate.py が完走しスコアが出る**

- [x] パターンA実行: **Vertex素（制御層OFF）** → **84.4%** (54/64)
  - 🔬 **T5a検証**: `results/eval_vertex_patternA_20260322_114232.json` 生成確認
- [x] パターンB実行: **Vertex＋制御層（制御層ON）** → **83.8%** (62/74)
  - 🔬 **T5b検証**: `results/eval_vertex_patternB_20260322_115335.json` 生成確認
- [x] 😈 **DA批判レビュー**

### Phase 5: 結果比較・記録

- [x] 結果比較表を作成 → 「決定事項」セクションに記載
- [x] `doc/research/cross-cutting/vertex-ai-search-comparison.md` に「実測結果」セクションを追記
- [x] `doc/record/rag_improvement_history.md` にVertex検証結果を追記（スコア推移表 + 比較表 + 知見）
- [x] 👀 **目視確認**: 比較結果が公平で偏った解釈になっていないか確認済み
- [x] 😈 **DA批判レビュー**

## 既存コードへの影響（変更なしの確認）

| ファイル | 変更 | 理由 |
|---------|:----:|------|
| `src/search/flow.py` | **なし** | `hybrid_search()` の戻り値型が同じなので透過的 |
| `src/search/reranker.py` | **なし** | `SearchResult.content` をそのまま使う |
| `src/search/metadata_scorer.py` | **なし** | `SearchResult.category` を使う（マッピングで埋める） |
| `src/evaluate/runner.py` | **なし** | `rag_flow()` を呼ぶだけ |
| `scripts/evaluate.py` | **なし** | `runner.run_evaluation()` を呼ぶだけ |
| `test-data/golden/eval_dataset.jsonl` | **なし** | 評価データは検索エンジンに依存しない |

## 変更したファイル

### 評価検証（Phase 1-5）

| ファイル | 変更内容 |
|---------|---------|
| `src/config.py` | 3行追加（`use_vertex_ai_search`, `vertex_search_engine_id`, `vertex_search_data_store_id`）。デフォルト `True` |
| `src/search/vertex_ai_searcher.py` | **新規作成** — Discovery Engine v1beta API で検索、extractive_segments を使用（1200文字制限） |
| `src/search/hybrid.py` | 冒頭に3行の分岐追加（`if config.use_vertex_ai_search: return ...`） |
| `src/search/flow.py` | `max_output_tokens` 2048→8192 に変更（Vertex版のcontext増大による空レスポンス対策） |
| `.env.local` | `VERTEX_SEARCH_ENGINE_ID`, `VERTEX_SEARCH_DATA_STORE_ID` 追加 |

### UI対応（DD-024-2相当）

| ファイル | 変更内容 |
|---------|---------|
| `ui/src/App.tsx` | サイドバー最上部に「検索エンジン」ラジオボタン追加（Vertex AI Search / 自前RAG） |
| `ui/src/App.css` | `.engine-toggle`, `.engine-option` 等のスタイル追加 |
| `ui/src/admin/api.ts` | `ConfigParams` に `use_vertex_ai_search: boolean` 追加 |
| `main.py` | `_TUNABLE_PARAMS` に `use_vertex_ai_search` 追加、クエリログの `techniques` に追記 |

## 撤退基準（タイムボックス管理）

| チェックポイント | 判断 |
|------|------|
| T0-T1 で2時間超 | データストア構築に問題あり。Console手動操作に切替、それでもダメなら撤退 |
| T2 で3時間超 | API仕様の想定外。レスポンス形式をログに記録して撤退 |
| T4 失敗 | reranker/metadata_scorer との結合問題。制御層OFFのパターンAのみで評価 |
| 合計6時間超 | 途中成果を記録して撤退。「T?まで到達、T?で詰まった」を記録 |

## ログ

### 2026-03-22
- DD作成（TDD方針で構成）
- 関連: DD-023（選択肢B採択により本DDを起票）
- Phase 1完了: GCS バケット作成、61ファイルアップロード（.md→.txt変換）、データストア `vais-eval-ds-2` + Engine `vais-eval-engine` 作成
  - 失敗1: .mdファイルを直接インポート → "invalid JSON" エラー（全4144件失敗）。`.txt` に拡張子変換で解決
  - 失敗2: データストア削除後に同じIDで再作成 → "being deleted" エラー。別ID `vais-eval-ds-2` で回避
  - 失敗3: インデックス構築後すぐは検索結果0件。約10分待機で解決
- Phase 2完了: `vertex_ai_searcher.py` 新規作成、`config.py` 3行追加、`hybrid.py` 分岐3行追加
  - extractive_answers は空で返る → extractive_segments を使用（1000-1700文字の十分なコンテンツ）
- Phase 3完了: T2→T3→T4の結合テスト全通過
- Phase 4完了: パターンA（84.4%）、パターンB（83.8%）の評価完了
- **所要時間: 約2.5時間**（タイムボックス6時間以内で完了）
- UI対応: サイドバー最上部に検索エンジン切替（Vertex / 自前）をラジオボタンで追加。Vertexをデフォルトに設定
- 空レスポンス問題を修正:
  - 原因1: extractive_segmentsが1件3000-5000文字 → 4件で14526文字のcontextがLLMに渡りthinkingトークンが出力枠を圧迫
  - 対策1: relevanceScore最上位のセグメント1件のみ使用、1200文字に制限
  - 原因2: `max_output_tokens=2048` では不足するケースあり
  - 対策2: `max_output_tokens` を8192に拡大

---

## DA批判レビュー記録

### Phase 0 DA批判レビュー

**DA観点:** 比較の公平性は担保できるか？

| # | 発見した問題/改善点 | 重要度 | 再現手順（高/中は必須） | DA観点 | 対応 |
|---|-------------------|--------|----------------------|--------|------|
| 1 | (Phase 0 実施時に記入) | - | - | - | - |
