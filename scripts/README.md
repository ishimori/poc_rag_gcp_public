# スクリプト (scripts/)

## 開発

### dev.sh — 開発サーバー起動

バックエンド（Cloud Functions）とフロントエンド（Vite）を同時起動する。

```bash
bash scripts/dev.sh        # 起動（chat:8081 + admin:8082 + UI:5180）
bash scripts/dev.sh stop   # 停止
bash scripts/dev.sh restart # 再起動
```

ポートは環境変数で変更可能: `API_PORT`（8081）, `ADMIN_PORT`（8082）, `UI_PORT`（5180）

### dev-kill.sh — 開発サーバー強制停止

ポートを占有しているプロセスを強制終了する。`dev.sh stop` で停止できない場合に使用。

```bash
bash scripts/dev-kill.sh
```

## デプロイ

### deploy.sh — Firebase デプロイ

UIビルド → `firebase deploy` → ベクトルインデックス確認 を自動化する。

```bash
bash scripts/deploy.sh              # 全体デプロイ
bash scripts/deploy.sh hosting      # Hosting のみ
bash scripts/deploy.sh functions    # Functions のみ
bash scripts/deploy.sh firestore    # Firestore インデックスのみ
bash scripts/deploy.sh --skip-build # UIビルドをスキップ
```

**注意**: `firebase deploy --force` は絶対に使わないこと（ベクトルインデックスが削除される）。

## データ管理

### ingest.py — ドキュメント一括取り込み

`test-data/sources/` 内の Markdown ファイルをチャンク分割 → Embedding生成 → Firestore に保存する。

```bash
uv run python scripts/ingest.py          # 差分投入（既存チャンクはスキップ）
uv run python scripts/ingest.py --clear  # 全削除してから再投入
```

前提: `.env.local` に `GOOGLE_CLOUD_PROJECT` を設定済みであること。

### evaluate.py — 評価パイプライン実行（順次版）

`test-data/golden/eval_dataset.jsonl` を使ってRAGの精度を評価し、スコアレポートを出力する。

```bash
uv run python scripts/evaluate.py
uv run python scripts/evaluate.py --collection chunks_1200    # コレクション指定
uv run python scripts/evaluate.py --limit 10                  # 先頭10件だけ
```

結果は `results/` ディレクトリと Firestore（`eval_results` コレクション）に保存される。

### evaluate_parallel.py — 評価パイプライン実行（並列版・推奨）

`evaluate.py` と同じ結果を出力するが、テストケースを複数同時実行して高速化する。**通常はこちらを使用する。**

```bash
uv run python scripts/evaluate_parallel.py                              # デフォルト5並列
uv run python scripts/evaluate_parallel.py --collection chunks_1200     # コレクション指定
uv run python scripts/evaluate_parallel.py --workers 3                  # 並列数指定
uv run python scripts/evaluate_parallel.py --limit 10                   # 先頭10件だけ
```

### run_experiment.py — Ingest → Evaluate 一括実行

1つのコレクションに対して Ingest → Evaluate を順次実行するラッパー。複数コレクションを `&` で並列起動できる。

```bash
uv run python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200
uv run python scripts/run_experiment.py --collection chunks_1200 --evaluate-only   # Evaluateのみ
uv run python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200 --ingest-only  # Ingestのみ
```

### fetch_wikipedia.py — Wikipedia 記事取得

ノイズチャンク用のテストデータとして、Wikipedia 日本語版から記事を取得し `test-data/sources/wikipedia/` に保存する。

```bash
uv run python scripts/fetch_wikipedia.py
```

既存ファイルはスキップされる。取得対象の記事リストはスクリプト内の `ARTICLES` 辞書で定義。

## 関連ドキュメント

- [開発手順](../doc/spec/infra/development.md)
- [環境構成](../doc/spec/infra/infrastructure.md)
