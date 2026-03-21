非常に整理されたPoCです。
81.1%は「設計はほぼ正しい」状態で、残課題は**検索精度よりも「制御・判定ロジック」寄り**です。

以下、**スコアを90%以上に引き上げるための具体策**を、指定フォーマットで提示します。

---

# 1️⃣ security 0% 改善策（最優先）

## 対策①: アクセス拒否検知フラグ注入（Access Denied Signal Injection）

* **概要**
  検索前に「本来ヒットするはずの文書が、権限フィルタで除外されたか」を判定し、
  その結果を `retrieval_status` としてLLMに明示的に渡す。
  例:

  ```json
  {
    "retrieval_status": "FILTERED_BY_PERMISSION",
    "matched_doc_count_without_filter": 3,
    "matched_doc_count_with_filter": 0
  }
  ```

* **期待効果**
  security: **0% → 100%**（5/5）
  overall: +6〜7pt

* **実装難易度**: 中

* **再Ingestの要否**: 不要

* **トレードオフ・リスク**:
  フィルタなし検索を内部的に走らせる必要あり（コスト増）

✅ これが最も本質的解決策です。

---

## 対策②: 二段階検索（Shadow Retrieval）

* **概要**
  1回目: 権限ありで検索
  2回目: 権限なしで検索（スコアのみ取得、本文は渡さない）
  → 差分があるなら「権限不足」と判断

* **期待効果**
  security: 100%到達可能

* **実装難易度**: 中

* **再Ingest**: 不要

* **リスク**:
  レイテンシ増（+100〜200ms程度）

---

## 対策③: 権限付きメタ情報をLLMに明示

* **概要**
  「あなたは以下のグループに属しています: A, B」
  「この質問に該当する文書はグループC専用です」
  というメタ説明をプロンプトに含める。

* **期待効果**
  security: 0% → 60〜80%（単独では不安定）

* **実装難易度**: 低

* **再Ingest**: 不要

* **リスク**:
  LLM依存になるため再現性が弱い

👉 推奨は **① + ②の併用**

---

# 2️⃣ semantic 67% → 90%改善

残り4件は「検索の最適化」より「意味拡張不足」の可能性が高い。

---

## 対策④: クエリ拡張（Multi-Query Expansion）

* **概要**
  クエリをLLMで3〜5個に言い換えて検索
  （例：「接続できない」→「ログイン不可」「VPNエラー」「通信障害」）

* **期待効果**
  semantic: 67% → 90%前後
  cross_categoryも改善

* **実装難易度**: 中

* **再Ingest**: 不要

* **リスク**:
  ノイズ増 → RRFで制御必要

---

## 対策⑤: BM25重み強化（ハイブリッド比率最適化）

* **概要**
  semantic失敗ケースを分析し、
  ベクトル:キーワードのRRF重みをチューニング

* **期待効果**
  semantic +5〜10pt

* **難易度**: 低

* **再Ingest**: 不要

---

## 対策⑥: Answer-Aware Retrieval（生成前再検索）

* **概要**
  一度ドラフト回答を生成し、その回答を再度検索クエリにして再取得

* **期待効果**
  semantic +5〜10pt
  multi_chunk安定化

* **難易度**: 中

* **再Ingest**: 不要

* **リスク**: レイテンシ増

---

# 3️⃣ ambiguous 60% → 100%

これは「生成品質」ではなく「評価安定性」の問題。

---

## 対策⑦: ルールベース曖昧判定の併用

* **概要**
  LLM判定に加えて、

  * 主語欠落
  * 指示語（それ・あれ）
  * 文書カテゴリ未特定
    などをルール判定

* **期待効果**
  ambiguous: 60% → 90〜100%

* **難易度**: 低

* **再Ingest**: 不要

* **リスク**: 過検知

---

## 対策⑧: 温度0固定 + JSON出力強制

* **概要**
  曖昧判定は deterministic にする

  ```
  { "is_ambiguous": true/false, "reason": "" }
  ```

* **期待効果**
  評価ブレ解消

* **難易度**: 低

---

# 4️⃣ unanswerable 80% → 100%

---

## 対策⑨: 回答信頼度スコアリング（Answerability Gate）

* **概要**
  生成前に
  「検索スコアが閾値未満なら強制拒否」
  例:

  * top1_score < 0.25 → 回答禁止

* **期待効果**
  unanswerable: 100%到達可能

* **難易度**: 低

* **再Ingest**: 不要

* **リスク**: false negative増加

---

## 対策⑩: NLIベースの回答検証

* **概要**
  「回答はコンテキストに含まれているか？」をLLMで判定
  entailmentチェック

* **期待効果**
  unanswerable + semantic改善

* **難易度**: 中

* **リスク**: コスト増

---

# 5️⃣ 90%を超えるための追加施策

---

## 対策⑪: Top-kの動的調整

* **概要**
  クエリタイプ別にkを変える

  * exact: k=5
  * semantic: k=15

* **期待効果**
  semantic + cross_category改善

* **難易度**: 低

---

## 対策⑫: チャンク再設計（構造単位分割）

* **概要**
  800文字固定ではなく
  見出し単位 + セクション単位で再分割

* **期待効果**
  semantic + table_extract向上

* **難易度**: 中

* **再Ingest**: 要

---

## 対策⑬: Rerankerにクエリ意図を渡す

* **概要**
  Rankerに
  「これはトラブルシューティング系質問」などの意図情報を付与

* **期待効果**
  semantic + cross_category改善

* **難易度**: 中

---

# 6️⃣ 構造的改善ポイント

---

## 🔥 最大の構造問題

現在の構成は：

```
検索 → 統合 → リランキング → 生成
```

だが本来は：

```
① クエリ理解
   ├─ 意図分類
   ├─ 曖昧判定
   ├─ セキュリティ判定
   └─ フィルタ生成
② 動的検索戦略決定
③ 検索
④ 回答可能性判定
⑤ 生成
⑥ 回答検証
```

つまり今は「検索中心型」、
90%超えには「制御中心型RAG」に進化させる必要があります。

---

# 📈 改善後の到達予測

| カテゴリ         | 改善後予測      |
| ------------ | ---------- |
| security     | 100%       |
| semantic     | 90〜92%     |
| ambiguous    | 100%       |
| unanswerable | 100%       |
| overall      | **90〜93%** |

---

# 🎯 優先順位（ROI順）

1. ✅ Access Denied Signal Injection（最重要）
2. ✅ 回答信頼度ゲート
3. ✅ Multi-Query Expansion
4. ✅ 曖昧判定のdeterministic化
5. ⭕ 構造分割チャンク再設計

---

# 最終結論

あなたのPoCは既に「検索精度の問題」ではありません。

残課題は：

> **検索後に、正しい制御シグナルをLLMに渡していないこと**

です。

特に security は
「RAGの失敗」ではなく「状態伝達の失敗」です。

ここを直せば90%は現実的です。

---

必要なら：

* security改善の具体的プロンプト設計
* multi-queryの実装テンプレ
* answerability gateの閾値設計方法

まで踏み込みますか？
------------------

了解です。
では最重要の **① Access Denied Signal Injection（security 0%対策）** から具体設計に入ります。

---

# ✅ 対策①: Access Denied Signal Injection（設計レベル詳細）

---

## 🎯 目的

LLMが

* 「検索でヒットしなかった」のか
* 「権限で除外された」のか

を **明確に区別できる状態を作る**。

---

# 🧠 基本思想

Pre-filtering は正しい設計ですが、

> フィルタは検索前に透過的に適用される
> → LLMは「世界に存在しない情報」と誤認する

これを解決するには：

> 🔥 **フィルタ前後の検索差分をシステム側で検出し、明示的にLLMへ伝える**

---

# 🏗 実装アーキテクチャ

## 🔁 追加する処理フロー

現在：

```
Query
  ↓
Pre-filter付き検索
  ↓
LLM生成
```

改善後：

```
Query
  ↓
① フィルタなし検索（shadow）
② フィルタあり検索（通常）
  ↓
③ 差分判定
  ↓
④ retrieval_status生成
  ↓
LLMへ明示的に注入
```

---

# 🔎 ステップ詳細

---

## Step 1: フィルタなし検索（Shadow Retrieval）

```python
results_without_filter = vector_search(query, filter=None, top_k=5)
```

※本文はLLMに渡さない
※スコアとdoc_idのみ保持

---

## Step 2: フィルタあり検索（通常）

```python
results_with_filter = vector_search(
    query,
    filter={"allowed_groups": {"$in": user_groups}},
    top_k=5
)
```

---

## Step 3: 差分判定ロジック

```python
if len(results_without_filter) > 0 and len(results_with_filter) == 0:
    retrieval_status = "FILTERED_BY_PERMISSION"
elif len(results_with_filter) == 0:
    retrieval_status = "NO_MATCH"
else:
    retrieval_status = "OK"
```

さらに精密化するなら：

```python
top_score_without = results_without_filter[0].score if results_without_filter else 0
top_score_with = results_with_filter[0].score if results_with_filter else 0

if top_score_without > 0.3 and top_score_with < 0.1:
    retrieval_status = "LIKELY_FILTERED"
```

---

# 🧾 LLMへのプロンプト注入

生成プロンプトの system 部に明示的に追加：

---

### 🔐 例

```
[Retrieval Status]
- status: FILTERED_BY_PERMISSION
- explanation:
  The query matches documents that exist in the system,
  but the current user does not have permission to access them.

Instructions:
If status is FILTERED_BY_PERMISSION,
you must respond that the user does not have permission to access the requested information.
Do NOT say "information not found".
```

---

# 🎯 LLM出力制御（重要）

さらに安全にするなら：

### 出力フォーマットを固定

```json
{
  "decision": "answer" | "permission_denied" | "not_found",
  "message": "..."
}
```

そしてアプリ側で：

```python
if decision == "permission_denied":
    return "この情報にアクセスする権限がありません。"
```

→ LLMの文言ぶれも防止可能

---

# 📈 期待される改善

| Before        | After  |
| ------------- | ------ |
| security 0%   | 100%   |
| overall 81.1% | 87〜88% |

securityは5件なので一気に伸びます。

---

# ⚠️ 実装時の注意点

### 1️⃣ コスト増

検索が2回になる
→ ただし61文書規模なら問題なし

---

### 2️⃣ レイテンシ増

+100〜200ms程度

---

### 3️⃣ 閾値設計

0件差分だけでなく
「スコア差」で見るのが安定

---

# 🔥 ベストプラクティス（推奨構成）

```
if FILTERED_BY_PERMISSION:
    LLMを呼ばない
    → アプリ側で即拒否
```

これが最も堅牢。

LLMに判断させる必要すらありません。

---

# 🎯 結論

security 0% の本質は：

> 検索は成功している
> だが「状態」がLLMに伝わっていない

です。

RAGは検索精度だけではなく
**状態制御設計が8割**です。

---

次に進みますか？

👉 次は **② Answerability Gate（unanswerable 80%対策）** に行きますか？
それとも security について深掘りしますか？
------------
了解です。
次は **② Answerability Gate（unanswerable 80% → 100%）** を具体設計まで落とします。

---

# ✅ 対策②: Answerability Gate（回答可能性ゲート）

---

## 🎯 目的

> 文書に答えが存在しないのに、LLMが「それっぽく回答してしまう」問題を止める

今の失敗1件は典型的な：

* retrieval弱ヒット
* LLMが補完推論
* LLM-as-Judgeで incorrect

というパターンの可能性が高いです。

---

# 🧠 基本思想

生成前に：

> 「そもそも回答可能か？」を判定するレイヤーを追加する

RAGではこれが **90%超えの分水嶺** です。

---

# 🏗 改善アーキテクチャ

現在：

```id="4xk2p9"
検索 → リランキング → 生成
```

改善後：

```id="n8r2k1"
検索 → リランキング
        ↓
   Answerability判定
        ↓
   OKなら生成
   NGなら拒否
```

---

# 🧪 実装パターン（3段階強化）

---

# 🥇 レベル1（まずはこれ）

## スコア閾値ベース・ゲート

---

### 🔎 ロジック

```python
top_score = reranked_results[0].score if reranked_results else 0

if top_score < 0.25:
    return "該当する情報が見つかりませんでした。"
```

### 🔧 閾値設計方法

1. 正解ケースのtop_score分布を可視化
2. unanswerable失敗ケースのtop_scoreを見る
3. 境界を決める（例: 0.22〜0.30）

---

### 🎯 期待効果

| before           | after   |
| ---------------- | ------- |
| unanswerable 80% | 90〜100% |

---

### ⚠️ リスク

* 閾値が高すぎると false negative
* semantic質問が削られる可能性

→ まずログで分布確認が重要

---

# 🥈 レベル2（推奨）

## Top-k平均スコア利用

単一チャンクではなく：

```python
mean_score = np.mean([r.score for r in reranked_results[:3]])

if mean_score < 0.23:
    reject
```

これで偶然ヒットの誤検知を減らせます。

---

# 🥉 レベル3（高精度版）

## NLI（Entailment）ベース回答検証

---

### ステップ

1. LLMでドラフト回答生成
2. 以下を別プロンプトで判定

```text
Question:
{query}

Context:
{retrieved_chunks}

Answer:
{draft_answer}

Does the context explicitly support the answer?
Answer only YES or NO.
```

3. NOなら拒否

---

### 🎯 効果

* hallucination激減
* unanswerable 100%安定

---

### ⚠️ デメリット

* LLM呼び出し +1回
* レイテンシ増

PoCなら許容範囲

---

# 🔥 ベスト実装（実務推奨）

実は最も安定するのは：

```id="6j8l1q"
① スコア閾値ゲート
② 低信頼時のみNLI検証
```

つまり：

```python
if top_score < 0.20:
    reject
elif top_score < 0.30:
    run_nli_check()
else:
    generate_answer()
```

これがコスト効率と精度のバランス最適。

---

# 📊 実際の改善予測

| カテゴリ         | 期待改善   |
| ------------ | ------ |
| unanswerable | 100%   |
| semantic     | +3〜5pt |
| overall      | +2〜4pt |

---

# 🎯 なぜこれで90%超えに近づくか

現在81.1%
security対策で +6〜7pt
unanswerableで +2〜4pt

→ 89〜92%射程圏

---

# 🚨 重要な設計思想

LLMに：

> 「答えてよいかどうか」を判断させてはいけない

これは **アプリケーション層で制御する** のが正解です。

---

次はどれに行きますか？

1. semantic 67% → 90%（Multi-query + 再検索）
2. ambiguous 60% → 100%（判定安定化）
3. 全体構造を90%超え仕様に再設計

どれから攻めますか？
-------------
結論から言います。

> 🎯 **次にやるべきは semantic 67% → 90% 改善です。**

理由をロジカルに説明します。

---

# ✅ なぜ semantic を次にやるべきか

## ① 伸び代が一番大きい

| カテゴリ         | 現在  | 最大伸び幅       |
| ------------ | --- | ----------- |
| security     | 0%  | +5件（確定改善可能） |
| unanswerable | 80% | +1件         |
| ambiguous    | 60% | +2件         |
| semantic     | 67% | **+4件（最大）** |

semanticは **12件中4件失敗**。

ここを取ると：

```
+4 / 74 = 約 +5.4pt
```

一気にOverall 86〜88%に到達します。

---

## ② 構造的に「検索の完成度」を上げる工程だから

security / unanswerable は「制御レイヤー改善」。

semanticは：

> 🔥 RAGの本丸（retrieval精度そのもの）

ここが90%になると、全体の安定度が一段上がります。

---

## ③ 90%を超えるには semantic がほぼ必須

仮に：

* security → 100%
* unanswerable → 100%
* ambiguous → 100%

でも semanticが67%のままだと：

```
最大でも 88〜89%付近で止まる可能性高い
```

つまり：

> semanticを上げないと天井がある

---

# 🧠 戦略的優先順位

1️⃣ security（すぐ直せる、ROI高）
2️⃣ semantic（最大伸び代、本質改善）
3️⃣ unanswerable
4️⃣ ambiguous（最後でOK）

---

# 🎯 なのでおすすめ順は：

👉 **次は semantic 改善**

---

# 🔥 さらに踏み込むと

semantic 67%という数字は、

> 「Embeddingは正しくなったが、クエリ理解が弱い」

可能性が高いです。

なのでやるべきは：

* Multi-query expansion
* Query rewriting
* 意図分類付き検索戦略

この3つ。

---

# 🧭 提案

次にやるなら：

> 🚀 Multi-Query Expansion（最も効果が出やすい）

から行きましょう。

実装方法・プロンプト・RRF統合まで具体化します。

進みますか？

--------------------
よし、いきましょう。
**semantic 67% → 90% を狙う本命施策：Multi-Query Expansion（MQE）** を具体設計します。

---

# ✅ 対策③: Multi-Query Expansion（意味拡張検索）

---

## 🎯 目的

ユーザーの自然言語は抽象的・曖昧です。

例：

* 「接続できない」
* 「エラーが出る」
* 「申請方法がわからない」

文書側は具体語で書かれている：

* 「VPNログイン失敗時の対処」
* 「エラーコード E203 の対応」
* 「経費精算申請フロー」

👉 1クエリでは意味空間を十分にカバーできない。

---

# 🧠 基本思想

> 🔥 LLMでクエリを“複数の意味的バリエーション”に展開して検索する

Embeddingの弱点（単一点意味表現）を補う。

---

# 🏗 改善アーキテクチャ

現在：

```text
Query
  ↓
ベクトル検索 + BM25
```

改善後：

```text
Query
  ↓
LLMで3〜5個に拡張
  ↓
各クエリで検索
  ↓
RRF統合
  ↓
リランキング
```

---

# 🛠 実装詳細

---

## Step 1️⃣ クエリ拡張プロンプト

### 🔹 推奨プロンプト（temperature=0）

```text
You are a search query rewriting assistant.

Given the user question, generate 4 alternative search queries
that capture different phrasings, synonyms, and possible related terms.

Rules:
- Keep them concise
- Do not change the intent
- Include possible technical terms if relevant
- Output as a JSON list

User Question:
{query}
```

### 🔹 出力例

```json
[
  "VPN connection failure troubleshooting",
  "Cannot log in to VPN",
  "VPN authentication error",
  "How to fix VPN connection issues"
]
```

---

## Step 2️⃣ 検索実行

```python
expanded_queries = [original_query] + generated_queries

all_results = []
for q in expanded_queries:
    results = hybrid_search(q, top_k=10)
    all_results.extend(results)
```

---

## Step 3️⃣ RRF統合（重要）

すでにRRF使っているので、
各クエリの結果を同じRRFに投入するだけ。

```python
def rrf_score(rank, k=60):
    return 1 / (k + rank)
```

重複doc_idはスコア加算。

---

# 📈 期待効果

| カテゴリ             | 改善予測        |
| ---------------- | ----------- |
| semantic         | 67% → 90%前後 |
| cross_category   | +5pt        |
| noise_resistance | 微増          |
| overall          | +4〜6pt      |

---

# ⚠️ 重要なチューニングポイント

---

## ① クエリ数は4〜5が最適

多すぎると：

* ノイズ増加
* レイテンシ増加
* RRFが均される

推奨：**original + 3 = 計4本**

---

## ② 全部同じtop_kにしない

例：

```python
original_query: top_k=8
expanded_query: top_k=5
```

元クエリを重視。

---

## ③ semanticタイプだけに適用（最適）

クエリ分類して：

* exact_match → 不要
* similar_number → 不要
* semantic系のみ実行

これでコスト抑制。

---

# 🔥 精度をさらに上げる応用

---

## 🧩 応用①: 観点拡張型プロンプト

単なる言い換えではなく：

```text
Generate:
1. A troubleshooting-focused query
2. A procedural query
3. A definition-style query
4. A keyword-heavy short query
```

これが意外と効きます。

---

## 🧩 応用②: 失敗ケースのみ拡張

もしtop1スコアが低ければ：

```python
if top_score < 0.28:
    run_multi_query()
```

普段は単一検索で高速化。

---

# 💰 コスト影響

* LLM呼び出し +1回
* 検索回数 ×4

61文書規模なら問題なし。

---

# 🧪 導入後の検証方法（重要）

semantic失敗4件だけ再評価し、

* retrievalヒット率
* top1スコア上昇
* 正解チャンク順位

を確認する。

---

# 🎯 ここまでやると

security + unanswerable + semantic改善で

> 🔥 90%は現実的ライン

---

# 🚀 次の一手は？

1. MQEの「より高度版（意図分類付き検索戦略）」
2. semantic失敗パターンのタイプ別分析方法
3. ambiguous安定化
4. 90%超えの最終構造設計

どこまで攻めますか？
------------------
いい質問です。
結論をはっきり言います。

> 🎯 **PoCとしては十分戦えるレベル。**
> でも「90%を安定して超えたい」なら、もう“一声”いくべきです。

理由を冷静に整理します。

---

# 📊 現在の到達予測

あなたが今入れようとしている施策：

* ✅ Security: Access Denied Signal
* ✅ Unanswerable: Answerability Gate
* ✅ Semantic: Multi-Query Expansion

これがうまくハマると…

| 項目           | 予測         |
| ------------ | ---------- |
| security     | 100%       |
| unanswerable | 100%       |
| semantic     | 85〜92%     |
| overall      | **88〜92%** |

問題はここです。

> 90%は「到達する可能性がある」状態
> でも「安定して超える保証」はまだない

---

# 🧠 なぜまだ揺れるのか？

残っている不安定要素は2つ：

---

## ① Retrieval Qualityのばらつき

Multi-queryは強力ですが、

* 失敗4件が「語彙不足型」なら効く
* 失敗4件が「チャンク構造問題型」なら効かない

もし後者なら、まだ取りこぼします。

---

## ② 評価揺れ（LLM-as-Judge問題）

ambiguousのブレがある時点で、

> 評価基盤自体がノイジー

という可能性があります。

90%を目指すなら、
評価の安定性も重要。

---

# 🔥 私のプロ視点での答え

PoCフェーズなら：

> ✅ 今回の3施策で一旦フル評価を回す
> → 実測を見る

これが合理的。

---

# ただし

もしあなたのゴールが：

* 本番導入前の精度保証
* 社内レビューで「文句なし」と言わせる
* 95%を射程に入れる

なら、

> 🚀 もう一声いくべき

---

# 🎯 その「もう一声」とは何か？

答えはこれです：

## 🔥 Retrieval後の“回答妥当性検証”レイヤー

つまり：

> 生成後に「本当に根拠があるか」を検証する

これは多くのRAGがやっていない最終兵器。

---

# 🏗 90%安定ラインの構造

理想は：

```text
Query
  ↓
Query理解
  ↓
Multi-Query Retrieval
  ↓
Answerability Gate
  ↓
Draft Answer生成
  ↓
Entailment検証（根拠確認）
  ↓
最終回答
```

ここまで入れると：

> 90%はほぼ再現可能
> 95%も現実的

---

# 🎯 私の推奨戦略

## フェーズ分けで考える

### Phase 1

今の3施策で再評価
→ スコアを見る

### Phase 2（必要なら）

Entailment検証を追加

---

# 📌 現実的な判断基準

もし再評価で：

* 88%未満 → 追加施策必須
* 88〜91% → 安定化施策を検討
* 92%以上 → PoCとして十分成功

---

# 💬 私からの率直な感想

あなたの設計はかなり高度です。
ここまで来ているRAGは少ない。

だからこそ、

> 「なんとなく90%」ではなく
> 「構造的に90%を出せる設計」に行くかどうか

が分かれ目です。

---

# 🎯 私ならどうするか？

私は一度回します。

理由：

> データを見ない改善は博打になる

---

ここで聞きたいです。

あなたのゴールはどれですか？

1️⃣ PoC成功ライン（90%前後でOK）
2️⃣ 本番投入前提（95%狙い）
3️⃣ 研究的に限界まで攻めたい

方向性で、次の一手が変わります。
