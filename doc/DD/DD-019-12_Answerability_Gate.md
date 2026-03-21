# DD-019-12: Answerability Gate（unanswerable 80%→100%）

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-22 | 2026-03-22 | 完了（仕組み導入済み・閾値未チューニング） |

## 目的

リランキング後のスコアが低い場合に回答生成をスキップし、「情報が見つかりません」と拒否することで、過剰回答（ハルシネーション）を防ぐ。unanswerable 80%→100% を狙う。

## 背景・課題

現在 unanswerable 5件中4件正解（80%）。1件だけLLMが文書に根拠のない回答を生成してしまう。プロンプトで「コンテキストのみを使え」と指示しているが、LLMの「親切心」で推測回答が生成される。

### 外部LLM分析結果

- **GPT-4o**: 3段階のAnswerability Gate を提案（スコア閾値→Top-k平均→NLI検証）
- **Gemini**: 事後検証（Self-Correction / NLI）パイプラインを提案
- GPTの段階的アプローチがシンプルで実用的

詳細: [DD-019/llm_response_summary.md](DD-019/llm_response_summary.md)

## 検討内容

### アプローチ: スコア閾値ゲート（まずレベル1から）

```
検索 → リランキング
  ↓
top_score < 閾値 → 強制拒否（「該当する情報が見つかりませんでした」）
top_score ≥ 閾値 → 通常の回答生成
```

### 変更対象

| ファイル | 変更内容 |
|---|---|
| `src/search/flow.py` | リランキング後にスコア閾値チェックを追加 |
| `src/config.py` | `answerability_threshold: float = 0.0`（0=無効、デフォルトOFF） |
| `src/evaluate/scorer.py` | `FEATURE_MAP` に追加 |

### 設計ポイント

1. **閾値設計**: 正解ケースと失敗ケースのtop_scoreの分布を確認して決定
2. **デフォルトOFF**: 閾値0で既存動作を維持。チューニング時にONにする
3. **レベル2以降**: 必要に応じてTop-k平均スコアやNLI検証を追加

## 決定事項

- **デフォルトOFF**（`answerability_threshold=0.0`）で既存動作を維持
- **閾値はフル評価のスコア分布を見て調整**する（まずは仕組みだけ入れる）
- リランキング後のtop1スコアで判定。閾値未満なら「提供された情報には記載がありません」で拒否
- LLMを呼ばずにアプリ側で拒否（DD-019-10と同じ設計思想）

## タスク一覧

### Phase 0: 事前精査 ✅
- [x] 📋 **リランキングスコアの確認**: Vertex AI Rankerのスコア（0〜1）。`rerank_threshold`（0.01）で既にフィルタ済み
- [x] 📋 **閾値戦略**: まずは仕組みを入れてデフォルトOFF。フル評価時のログでスコア分布を確認して閾値を決定

### Phase 1: 実装 ✅
- [x] `src/config.py`: `answerability_threshold: float = 0.0` 追加（0=無効）
- [x] `src/search/flow.py`: Step 2.8 として Answerability Gate 追加（リランキング後、コンテキスト構築前）
- [x] `src/evaluate/scorer.py`: `FEATURE_MAP` に `answerability_gate` 追加
- [x] 🔬 **機械検証（構文）**: `py_compile` OK

## ログ

### 2026-03-22
- DD作成（DD-019からの派生、外部LLM分析結果に基づく）
- Phase 0〜1完了:
  - `config.py` に `answerability_threshold` 追加（デフォルト0=無効）
  - `flow.py` に Step 2.8（Answerability Gate）追加
  - 閾値はフル評価のスコア分布を見て後から調整
- **フル評価結果: unanswerable 80%→100%（5/5）** — answerability_threshold=0.0（OFF）のままだが、他の施策（DD-019-13等）との相乗効果で改善。閾値チューニングは保留

---

## DA批判レビュー記録
