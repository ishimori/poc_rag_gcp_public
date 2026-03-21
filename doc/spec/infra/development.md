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
cp .env.example .env
# .env を編集: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION を設定

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

```bash
# フロントエンドビルド + Firebase デプロイ（Hosting + Functions）
cd ui && npm run build && cd ..
firebase deploy

# Hosting のみ
firebase deploy --only hosting

# Functions のみ
firebase deploy --only functions

# Firestore インデックスのみ
firebase deploy --only firestore:indexes
```

### デプロイ時の注意

- `test-data/`、`results/`、`scripts/` はデプロイ対象外（`firebase.json` の ignore で除外）
- インジェスト・評価 API はローカル開発専用。デプロイ先では `test-data/` が存在しないため動作しない
- パラメータ変更（`PUT /config`）はランタイムのみ。再デプロイで初期値に戻る
