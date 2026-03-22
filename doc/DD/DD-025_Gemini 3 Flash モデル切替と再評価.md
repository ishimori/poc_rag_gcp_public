# DD-025: Gemini 3 Flash モデル切替と再評価

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-22 | 2026-03-22 | 進行中 |

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
| `src/config.py` | `llm_model` を `gemini-3-flash` に変更 |
| `src/search/flow.py` | 変更なし（`config.llm_model` を参照しているため自動反映） |
| `src/evaluate/scorer.py` | **変更なし** — LLM-as-Judge は `gemini-2.5-flash` ハードコードのまま |

### 評価マトリクス

| # | 検索エンジン | 回答モデル | 比較対象 |
|---|------------|-----------|---------|
| 1 | 自前RAG（Firestore） | Gemini 3 Flash | DD-019-9 の 85.1%（2.5 Flash） |
| 2 | Vertex AI Search | Gemini 3 Flash | DD-024 の 84.4%（2.5 Flash） |

## 決定事項

（DD-022 完了後に記入）

## タスク一覧

### Phase 0: 事前精査
- [ ] 📋 **各Phaseのタスク精査・詳細化**
- [ ] 😈 **Devil's Advocate調査**
  - Gemini 3 Flash のモデルIDは何か？（`gemini-3-flash` or `gemini-3.0-flash` 等）
  - Vertex AI API で利用可能か？ リージョン制約はないか？
  - 3 Flash の max_output_tokens 制限は 2.5 Flash と同じか？

### Phase 1: モデル切替
- [ ] Gemini 3 Flash のモデルIDを確認（`gcloud` or API で利用可能なモデル一覧を取得）
- [ ] `src/config.py` の `llm_model` を変更
- [ ] 🔬 **機械検証**: テストクエリ1件で回答が返ることを確認
- [ ] 😈 **DA批判レビュー**

### Phase 2: 再評価（自前RAG）
- [ ] DD-022 で確定したチャンクサイズ設定を適用
- [ ] `python scripts/evaluate.py` でフル評価（74件）
- [ ] 🔬 **機械検証**: 結果JSONが生成されること
- [ ] 😈 **DA批判レビュー**

### Phase 3: 再評価（Vertex AI Search）
- [ ] `config.use_vertex_ai_search = True` に設定
- [ ] `python scripts/evaluate.py` でフル評価（74件）
- [ ] 🔬 **機械検証**: 結果JSONが生成されること
- [ ] 😈 **DA批判レビュー**

### Phase 4: 比較・記録
- [ ] 比較表を作成（2.5 Flash vs 3 Flash × 自前/Vertex の 2×2 マトリクス）
- [ ] `doc/record/rag_improvement_history.md` に結果追記
- [ ] `doc/research/cross-cutting/vertex-ai-search-comparison.md` に追記
- [ ] 😈 **DA批判レビュー**

## ログ

### 2026-03-22
- DD作成
- 前提: DD-022（チャンク実験）完了後に着手

---

## DA批判レビュー記録

### Phase 0 DA批判レビュー

**DA観点:** モデル切替で予期しない副作用はないか？

| # | 発見した問題/改善点 | 重要度 | 再現手順（高/中は必須） | DA観点 | 対応 |
|---|-------------------|--------|----------------------|--------|------|
| 1 | (Phase 0 実施時に記入) | - | - | - | - |
