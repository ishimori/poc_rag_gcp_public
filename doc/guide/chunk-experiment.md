# チャンクサイズ実験ガイド

> 複数のチャンクサイズで Ingest → Evaluate を実行し、最適なパラメータを決定する手順。
> 関連DD: DD-022

## 概要

異なるチャンクサイズのコレクション（`chunks_1200`, `chunks_1600` 等）を Firestore 上に並存させ、スコアを比較する。Operations Monitor（`/admin/tuning`）で進捗を監視し、コレクションを切り替えてチャットで体感比較できる。

## 前提条件

- ローカル環境がセットアップ済み（[local-operations.md](local-operations.md) 参照）
- `gcloud auth application-default login` 実行済み

## 手順

### 1. コレクション設計

チャンクサイズと overlap を決める。overlap の目安は chunk_size の 1/6。

```
chunks_1200  → chunk_size=1200, overlap=200
chunks_1600  → chunk_size=1600, overlap=300
chunks_2000  → chunk_size=2000, overlap=400
```

### 2. Ingest（並列実行可）

```bash
# 1コレクションずつ
python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200

# 3並列実行
python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200 &
python scripts/run_experiment.py --chunk-size 1600 --collection chunks_1600 &
python scripts/run_experiment.py --chunk-size 2000 --collection chunks_2000 &

# Ingest のみ（Evaluate は後で）
python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200 --ingest-only
```

処理時間の目安（61ファイル、contextual_retrieval ON）:
- 1コレクションあたり約 7〜10 分
- 3並列でも合計時間はほぼ同じ（LLM API がボトルネック）

### 3. Firestore インデックス作成（初回のみ）

**新しいコレクションを初めて作った場合**、Firestore のベクトルインデックスが必要。Evaluate 実行時に `Missing vector index configuration` エラーが出たら以下を実行する。

```bash
# コレクションごとに2種類のインデックスが必要

# 1. ベクトル検索用（権限フィルタ付き）
gcloud firestore indexes composite create \
  --project=poc-rag-490804 \
  --collection-group=chunks_1200 \
  --query-scope=COLLECTION \
  --field-config='array-config=contains,field-path=allowed_groups' \
  --field-config='vector-config={"dimension":"768","flat": "{}"},field-path=embedding'

# 2. ベクトル検索用（フィルタなし — Shadow Retrieval 用）
gcloud firestore indexes composite create \
  --project=poc-rag-490804 \
  --collection-group=chunks_1200 \
  --query-scope=COLLECTION \
  --field-config='vector-config={"dimension":"768","flat": "{}"},field-path=embedding'
```

**chunks_1600, chunks_2000 も同様に `--collection-group` を変えて実行する。**

インデックス作成には 3〜10 分かかる。完了確認:

```bash
gcloud firestore indexes composite list --project=poc-rag-490804 --format="table(name,state)" | grep CREATING
# 出力が空なら完了
```

### 4. Evaluate

**並列版（推奨）**: `evaluate_parallel.py` はテストケースを複数同時実行して高速化する。

```bash
# 並列版（デフォルト5並列、1コレクション約2〜3分）
python scripts/evaluate_parallel.py --collection chunks_1200

# 並列数を指定
python scripts/evaluate_parallel.py --collection chunks_1200 --workers 3

# 先頭10件で動作確認
python scripts/evaluate_parallel.py --collection chunks_1200 --limit 10
```

**複数コレクションを同時に評価する場合**:

```bash
python scripts/evaluate_parallel.py --collection chunks_1200 &
python scripts/evaluate_parallel.py --collection chunks_1600 &
python scripts/evaluate_parallel.py --collection chunks_2000 &
```

**順次版**: 従来通り1件ずつ実行する場合（デバッグ用）。

```bash
python scripts/run_experiment.py --collection chunks_1200 --evaluate-only
```

### 5. 進捗監視

Operations Monitor（`http://localhost:5180/admin/tuning`）で:
- Ingest / Evaluate の進捗バーをリアルタイム表示
- コレクション一覧でチャンク数を確認

### 6. コレクション切替 & 体感比較

Operations Monitor のドロップダウンでコレクションを切り替えると、チャット画面（`/`）の検索対象が変わる。同じ質問を投げて回答品質を比較する。

### 7. 結果の確認

評価結果は `results/` フォルダに JSON で保存される。History 画面（`/admin/history`）でスコアを比較できる。

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `Missing vector index configuration` | 新コレクションにインデックスがない | 手順3を実行 |
| Ingest が遅い（1ファイル1分以上） | `contextual_retrieval` ON で LLM 呼び出し | 正常。OFF にすれば速いがスコアは下がる |
| 3並列 Ingest で一部が止まる | LLM API レートリミット | 2並列に減らすか待つ |
| Operations Monitor に進捗が出ない | バックエンドが古いコード | `dev-kill.sh` → `dev.sh` で再起動 |

## 関連ファイル

| ファイル | 説明 |
|---------|------|
| `scripts/run_experiment.py` | Ingest → Evaluate 一括実行ラッパー |
| `scripts/ingest.py` | Ingest 単体（`--chunk-size`, `--collection` 対応） |
| `scripts/evaluate.py` | Evaluate 単体・順次実行（`--collection` 対応） |
| `scripts/evaluate_parallel.py` | **Evaluate 並列版（推奨）**。`--workers` で並列数指定、デフォルト5並列 |
| `src/config.py` | デフォルトパラメータ（`collection_name`, `chunk_size` 等） |
