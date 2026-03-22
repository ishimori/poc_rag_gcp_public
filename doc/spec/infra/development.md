# 開発手順

> 最終更新: 2026-03-21 | 対応DD: DD-012
>
> 環境変数・ポート・サービス構成は [infrastructure.md](infrastructure.md) を参照。

## 前提条件

| ツール | バージョン | 確認コマンド |
|--------|-----------|------------|
| Python | >= 3.12 | `python --version` |
| Node.js | >= 18 | `node --version` |
| uv | latest | `uv --version` |
| Firebase CLI | latest | `firebase --version` |
| GCP認証 | — | `gcloud auth application-default login` |

## セットアップ

```bash
# 1. リポジトリクローン
git clone <repo-url> && cd poc_rag_gcp_public

# 2. 環境変数設定
cp .env.local.example .env.local
# .env.local を編集: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION を設定

# 3. Python依存インストール
uv sync

# 4. フロントエンド依存インストール
cd ui && npm install && cd ..

# 5. GCP認証（初回のみ）
gcloud auth application-default login
```

## 開発サーバー起動・停止

```bash
# 起動（chat API + admin API + Vite を同時起動）
bash scripts/dev.sh

# 停止
bash scripts/dev.sh stop

# 強制停止（ポートを占有するプロセスを kill）
bash scripts/dev-kill.sh
```

起動後のアクセス先:

| サービス | URL |
|---------|-----|
| フロントエンド | http://localhost:5180 |
| Chat API | http://localhost:8081 |
| Admin API | http://localhost:8082 |

## フロントエンドビルド

```bash
cd ui
npm run build    # ui/dist/ に出力
npx tsc -b       # 型チェックのみ
```

## デプロイ

### 手順

```bash
# デプロイスクリプトを使用（UIビルド → firebase deploy → インデックス確認）
bash scripts/deploy.sh

# 個別デプロイ
bash scripts/deploy.sh hosting      # Hosting のみ
bash scripts/deploy.sh functions    # Functions のみ
bash scripts/deploy.sh firestore    # Firestore インデックスのみ
bash scripts/deploy.sh --skip-build # UIビルドをスキップ
```

手動で実行する場合:

```bash
# 1. フロントエンドビルド
cd ui && npm run build && cd ..

# 2. デプロイ（--force は使わない！理由は下記）
firebase deploy

# 3. ベクトルインデックスの存在確認
gcloud firestore indexes composite list --project=poc-rag-490804 --database="(default)" --format="table(name.basename(),collectionGroup,state)"
# → chunks のベクトルインデックスが READY であること
```

### デプロイ時の注意

| 注意事項 | 理由 |
|---------|------|
| **`firebase deploy --force` は使わない** | `--force` は `firestore.indexes.json` に定義されていないインデックスを削除する。ベクトルインデックスは `firestore.indexes.json` で宣言できない（gcloud CLIのみ）ため、削除されてしまう |
| **デプロイ後にベクトルインデックスを確認** | 万が一削除された場合は再作成（5〜10分かかる）: `gcloud firestore indexes composite create --project=poc-rag-490804 --collection-group=chunks --query-scope=COLLECTION --field-config='vector-config={"dimension":"768","flat": "{}"},field-path=embedding'` |
| `test-data/`、`results/` はデプロイ対象外 | `firebase.json` の ignore で除外。Evaluate/Ingest はローカル専用 |
| パラメータ変更（`PUT /config`）はランタイムのみ | 再デプロイで初期値に戻る |
| **`use_vertex_ai_search` はデフォルト `False` にすること** | `True` のままデプロイすると、本番に `.env.local` がないため `VERTEX_SEARCH_ENGINE_ID` が空 → 500エラー。Vertex AI Search を本番有効化する場合は Cloud Functions の環境変数に `VERTEX_SEARCH_ENGINE_ID` と `VERTEX_SEARCH_DATA_STORE_ID` を設定する必要がある |

### ローカルとFirebaseの役割分担

| 機能 | ローカル | Firebase Hosting |
|------|:---:|:---:|
| チャット（質問・回答） | ○ | ○ |
| クエリログ閲覧（Logs） | ○ | ○ |
| Ingest（データ投入） | ○ | × |
| Evaluate（評価実行） | ○ | × |
| Tuning（パラメータ変更+Re-tune） | ○ | × |
| History（評価結果の閲覧・比較） | ○ | ○ |

ローカルで実行した評価結果はFirestoreに自動保存され、Firebase Hosting上のHistoryで閲覧・比較できる。
