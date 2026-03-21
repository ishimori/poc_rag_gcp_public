# DD-019-8 分析記録: ベクトル検索で社内文書が引けない原因の推理

## 1. 観察された事実

### 1.1 Phase 1 の診断結果
- 代表3件（semantic-001, 006, 011）でhybrid_searchを実行
- **3件とも期待ソースが top_k=10 に含まれない**（失敗段階A）
- 上位10件は**全て wikipedia 系ドキュメント**
- keyword検索は全件0件ヒット（口語クエリに対しては無力 — 設計通り）

### 1.2 Phase 2 のテスト結果
- **top_k=50 でも社内文書がほぼ現れない**
  - 「PCが重い」: 社内文書1件のみ（40位、しかも期待ソースではない）
  - 「パスワードの条件は？」: 社内文書 0/50件
  - 「タクシー代を会社に請求したい」: 社内文書 0/50件
- **クエリ拡張しても全結果が wikipedia**
  - 口語→具体キーワード展開でも変化なし

### 1.3 チャンク規模
- Firestore `chunks` コレクション: **wikipedia 403件 vs 社内文書 51件（89%がwikipedia）**
- 社内文書は19ファイルから51チャンク

### 1.4 成功している2件
- semantic-005「Zoomは使える？」→ HIT（it_helpdesk_faq.md）
- semantic-007「USBメモリを使いたい」→ HIT（it_helpdesk_faq.md）

## 2. 異常性の認識

### 2.1 cosine距離でこの結果は不自然

ベクトル検索は cosine distance を使っている（`retriever.py:54`、`DistanceMeasure.COSINE`）。

cosine距離は**ベクトルの方向のみ**を比較し、大きさは無関係。つまり:
- チャンク数の多寡はcosine距離に影響しない
- 403件 vs 51件 の量比は、直接的にはランキングに影響しないはず

にもかかわらず、「パスワードの条件は？」で50件取得しても it_helpdesk_faq.md のチャンクが**1件も**入らないのは、以下のいずれかを意味する:

**(a) 社内文書の embedding が本当にクエリから遠い**
- 社内文書チャンクの embedding が、どんなクエリに対しても wikipedia チャンクより遠い位置にある
- つまり embedding の品質 or 生成過程に問題がある

**(b) Firestore ベクトルインデックスの異常**
- インデックスが一部のチャンクしかカバーしていない
- 社内文書のチャンクがインデックスに含まれていない可能性

**(c) embedding フィールドが欠損 or 異常値**
- 社内文書チャンクの `embedding` フィールドがゼロベクトルや null になっている
- または embedding の次元数が不一致

### 2.2 成功ケースとの矛盾

semantic-005「Zoomは使える？」と semantic-007「USBメモリを使いたい」は成功している。
この2件は it_helpdesk_faq.md から引けている。

**ということは、it_helpdesk_faq.md の少なくとも一部のチャンクは正常に検索できる。**

- 「パスワードの条件は？」で it_helpdesk_faq.md が50件中0件なのに
- 「Zoomは使える？」では引ける

この差は何か？ → **チャンク単位での embedding 品質のばらつき**の可能性が高い。

## 3. 仮説の絞り込み

### 仮説A: contextual_retrieval の前置テキストが embedding を歪めている

`config.py:22` で `contextual_retrieval: bool = True`。

contextual_retrieval はチャンクの先頭に文脈説明テキスト（例: `[このチャンクは、ITヘルプデスクFAQ文書の冒頭部分であり...]`）を付与してから embedding する。

**Phase 1 のチャンク内容確認で確認済み**: チャンクにはcontextual_retrievalテキストが付与されている（例: `[このチャンクは、経費精算マニュアルの「費目別ルール」セクションです。...]`）。

**問題の可能性**:
- 前置テキストが長すぎて、本文（FAQ回答やマニュアル内容）の意味が embedding に反映されにくくなっている
- 前置テキストはどのチャンクも似た構造（`[このチャンクは、{文書名}の{セクション名}であり...]`）なので、embedding が前置テキストに引きずられて**全チャンクが似た方向**に偏っている可能性
- 一方、wikipedia チャンクにも contextual_retrieval が付与されているはずだが、wikipedia の方が本文の情報量が多く、前置テキストの影響が相対的に小さい可能性

**検証方法**:
- 社内文書チャンクの embedding を直接取得し、クエリ embedding との cosine similarity を計算
- contextual_retrieval テキストを除いた本文のみで embedding を再計算し、cosine similarity を比較

### 仮説B: embedding 次元・モデルの不一致

`config.py:25-26`:
```python
embedding_model: str = "text-embedding-005"
embedding_dimension: int = 768
```

**問題の可能性**:
- Ingest 時と検索時で異なる embedding モデルが使われた（設定変更後に再Ingestしていない）
- embedding の次元数が変わった後にインデックスを再構築していない

**検証方法**:
- Firestore のチャンクの embedding フィールドの次元数を確認
- embed_text() で生成したベクトルの次元数と一致するか確認

### 仮説C: Firestore ベクトルインデックスの部分的な不整合

**問題の可能性**:
- ベクトルインデックスが最後の Ingest 時に完全に構築されていない
- 一部のドキュメントがインデックスに含まれていない（非同期インデックス構築の遅延）

**検証方法**:
- Firestore のインデックスステータスを確認
- 社内文書チャンクに対して `doc_id` 指定で直接取得し、embedding フィールドの存在と値を確認

### 仮説D: 社内文書の embedding がゼロベクトルまたは異常値

**問題の可能性**:
- Ingest 時に embedding API がエラーを返し、フォールバック値（ゼロベクトル等）が保存された
- 特定のチャンクだけ embedding が正常に生成されなかった

**検証方法**:
- 社内文書チャンクの embedding ベクトルの L2 ノルムを確認（ゼロベクトルなら 0.0）
- 各チャンクの embedding の先頭5要素を出力して値の分布を確認

## 4. 検証の優先順位

| 優先度 | 仮説 | 理由 | コスト |
|---|---|---|---|
| **1** | D: embedding がゼロ/異常値 | 最も致命的で、最も簡単に検証可能 | 低（Firestore読み取りのみ） |
| **2** | B: 次元・モデル不一致 | 次に検証が容易 | 低（次元数比較のみ） |
| **3** | A: contextual_retrieval の歪み | 成功/失敗ケースの比較で検証可能 | 中（embedding再計算が必要） |
| **4** | C: インデックス不整合 | GCPコンソールでの確認が必要 | 中 |

## 5. 次のアクション

1. 社内文書チャンク（失敗: pc_troubleshoot.md#0、成功: it_helpdesk_faq.md の Zoom 該当チャンク）の embedding を直接取得し、以下を確認:
   - embedding フィールドが存在するか
   - ベクトルの次元数は 768 か
   - L2 ノルムが 0 でないか（ゼロベクトルチェック）
   - クエリ embedding との cosine similarity を手計算

2. 成功ケース（semantic-005「Zoomは使える？」）と失敗ケース（semantic-006「パスワードの条件は？」）で、同じ it_helpdesk_faq.md の異なるチャンクが対象になるため、チャンク間の embedding 品質差を直接比較できる
