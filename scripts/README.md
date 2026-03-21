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

### evaluate.py — 評価パイプライン実行

`test-data/golden/eval_dataset.jsonl` を使ってRAGの精度を評価し、スコアレポートを出力する。

```bash
uv run python scripts/evaluate.py
```

結果は `results/` ディレクトリと Firestore（`eval_results` コレクション）に保存される。

### fetch_wikipedia.py — Wikipedia 記事取得

ノイズチャンク用のテストデータとして、Wikipedia 日本語版から記事を取得し `test-data/sources/wikipedia/` に保存する。

```bash
uv run python scripts/fetch_wikipedia.py
```

既存ファイルはスキップされる。取得対象の記事リストはスクリプト内の `ARTICLES` 辞書で定義。

## 関連ドキュメント

- [開発手順](../doc/spec/infra/development.md)
- [環境構成](../doc/spec/infra/infrastructure.md)
