# DD-019-8 Phase 1: 検索段階の診断

## 方式

代表3件を各1サブエージェントに割り当て、並行で診断を実行。

## サブタスク定義

### 入力

| サブタスク | ID | クエリ | 期待ソース |
|---|---|---|---|
| Agent A | semantic-001 | PCが重い | pc_troubleshoot.md |
| Agent B | semantic-006 | パスワードの条件は？ | it_helpdesk_faq.md |
| Agent C | semantic-011 | タクシー代を会社に請求したい | expense_manual.md |

### 手順（各エージェント共通）

1. `hybrid_search(クエリ)` を実行し、top_k=10 の結果を取得
   - 期待ソースが含まれるか（HIT/MISS）を判定
   - 全結果の `source_file#chunk_index score=X.XXXX` を記録
2. `rerank(クエリ, 検索結果)` を実行し、top_n=5 の結果を取得
   - 期待ソースが含まれるか（HIT/MISS）を判定
   - 全結果の `source_file#chunk_index score=X.XXXX` を記録
3. MISS の場合、Firestore から期待ソースのチャンク内容を取得
   - `chunks` コレクションで `source_file == 期待ソース` のチャンクを全件取得
   - 各チャンクの先頭200文字を記録（contextual_retrieval テキストの有無を確認）
4. 失敗段階を判定: A（検索で引けない）/ B（リランキングで除外）/ C（両方HIT）

### コマンドテンプレート

```python
# Step 1-2: 検索 → リランキング
.venv/Scripts/python.exe -c "
from src.search.hybrid import hybrid_search
from src.search.reranker import rerank
q = '{クエリ}'
src = '{期待ソース}'
results = hybrid_search(q)
print('=== hybrid_search ===')
found_search = False
for r in results:
    hit = '<<HIT>>' if r.source_file == src else ''
    if r.source_file == src: found_search = True
    print(f'  {r.source_file}#{r.chunk_index} score={r.score:.4f} {hit}')
print(f'期待ソース: {\"HIT\" if found_search else \"MISS\"}')
print()
reranked = rerank(q, results)
print('=== rerank ===')
found_rerank = False
for r in reranked:
    hit = '<<HIT>>' if r.source_file == src else ''
    if r.source_file == src: found_rerank = True
    print(f'  {r.source_file}#{r.chunk_index} score={r.score:.4f} {hit}')
print(f'期待ソース: {\"HIT\" if found_rerank else \"MISS\"}')
"

# Step 3: チャンク内容確認（MISSの場合のみ）
.venv/Scripts/python.exe -c "
from google.cloud import firestore
db = firestore.Client()
docs = db.collection('chunks').where('source_file','==','{期待ソース}').stream()
for d in docs:
    data = d.to_dict()
    print(f'chunk_{data[\"chunk_index\"]}:')
    print(f'  {data[\"content\"][:200]}')
    print()
"
```

### 出力フォーマット

```
## {ID}: {クエリ}
- 期待ソース: {期待ソース}
- hybrid_search: HIT/MISS（{何位}/{全件数}件中）
- rerank: HIT/MISS（{何位}/{全件数}件中）
- 失敗段階: A/B/C
- hybrid_search 結果:
  1. {source_file}#{chunk_index} score={score}
  2. ...
- rerank 結果:
  1. {source_file}#{chunk_index} score={score}
  2. ...
- チャンク内容（MISSの場合）:
  - chunk_0: {先頭200文字}
  - chunk_1: ...
- 所見: {なぜHIT/MISSなのかの考察}
```

## 結果

| ケース | hybrid_search | rerank後 | 失敗段階 | 所見 |
|---|---|---|---|---|
| semantic-001「PCが重い」 | MISS（0/10件） | MISS（0/5件） | **A** | 全結果がwikipedia系。pc_troubleshoot.mdはFirestoreに存在するがベクトル距離が遠い |
| semantic-006「パスワードの条件は？」 | MISS（0/10件） | MISS（0/5件） | **A** | chunk_0にFAQ-001（パスワードポリシー）が明記されているがベクトル検索で引けない |
| semantic-011「タクシー代を会社に請求したい」 | MISS（0/10件） | MISS（0/4件） | **A** | chunk_2に「タクシー利用」記述あり。wikipedia/経費.md#2が10位にかろうじて存在 |

### 共通パターン

- 3件とも **keyword=0件**（キーワード検索が効かない — DA指摘5の通り）
- 3件とも上位10件が **全てwikipedia系ドキュメント**。社内文書が1件も返らない
- 期待ソースのチャンクはFirestoreに存在し、contextual_retrievalテキストも付与済み
- **根本原因**: wikipedia系チャンク（数百件）が社内文書チャンク（数十件）をベクトル空間で圧倒しており、社内文書が上位に入れない
