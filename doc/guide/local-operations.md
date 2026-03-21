# ローカル操作ガイド

> セットアップ手順は [doc/spec/infra/development.md](../spec/infra/development.md) を参照。
> 本ガイドはセットアップ済みの環境での日常操作をまとめたもの。

## 前提条件

| 項目 | 状態 | 確認方法 |
|------|------|---------|
| GCP認証 | `gcloud auth application-default login` 実行済み | `gcloud auth list` で有効なアカウントが表示される |
| 環境変数 | `.env.local` に `GOOGLE_CLOUD_PROJECT` 設定済み | `cat .env.local` |
| Python仮想環境 | `uv sync` 実行済み | `.venv/` が存在する |
| Node.js依存 | `cd ui && npm install` 実行済み | `ui/node_modules/` が存在する |

## 操作一覧: ローカル vs デプロイ

| 操作 | ローカル実行 | CFデプロイ必要 | 備考 |
|------|:-----------:|:------------:|------|
| **evaluate**（評価パイプライン） | **可** | 不要 | ローカルから直接GCP APIを呼ぶ |
| **ingest**（データ投入） | **可** | 不要 | Firestoreに直接書き込む |
| **チャット（dev server）** | **可** | 不要 | `bash scripts/dev.sh` |
| **チャット（本番URL）** | — | **必要** | `bash scripts/deploy.sh` |
| **パラメータ変更** | **可** | 不要 | `src/config.py` 直接編集 or Admin API |
| **UI変更の反映（ローカル）** | **可** | 不要 | Vite HMRで自動反映 |
| **UI変更の反映（本番）** | — | **必要** | `bash scripts/deploy.sh hosting` |

**原則: バックエンドのPythonコード変更はデプロイ不要でevaluateに反映される。**

## よく使うコマンド

### 評価パイプライン

```bash
# 全件実行（74件、約5分）
python scripts/evaluate.py

# 件数制限（動作確認用）
python scripts/evaluate.py --limit 5

# 結果は results/ に JSON 保存 + Firestore に自動保存
```

evaluate.py はローカルで `rag_flow()` を直接呼び出す。CFを経由しないため、`src/` 配下のコード変更は即座に反映される。

### データ投入（Ingest）

```bash
# 通常実行（既存データに追加、重複はスキップ）
python scripts/ingest.py

# 全削除してから投入（テストデータ変更時）
python scripts/ingest.py --clear
```

### 開発サーバー

```bash
bash scripts/dev.sh        # 起動（chat:8081 + admin:8082 + UI:5180）
bash scripts/dev.sh stop   # 停止
bash scripts/dev-kill.sh   # 強制停止（ポート占有時）
```

### デプロイ

```bash
bash scripts/deploy.sh              # 全体デプロイ
bash scripts/deploy.sh hosting      # UI のみ
bash scripts/deploy.sh functions    # CF のみ
```

## よくあるハマりポイント

### `vertexai` の import エラー

```
ModuleNotFoundError: No module named 'vertexai'
```

仮想環境が有効になっていない。`uv run python ...` で実行するか、`.venv` を activate する。

### `firebase deploy --force` でベクトルインデックスが消える

`--force` は `firestore.indexes.json` に未定義のインデックスを削除する。ベクトルインデックスは gcloud CLI でしか作れないため、`--force` で消える。

再作成コマンド（5〜10分かかる）:
```bash
gcloud firestore indexes composite create \
  --project=poc-rag-490804 \
  --collection-group=chunks \
  --query-scope=COLLECTION \
  --field-config='vector-config={"dimension":"768","flat": "{}"},field-path=embedding'
```

### evaluate.py のコンソール出力が文字化け（Windows）

cp932 エンコーディングの問題。evaluate.py 内で `PYTHONUTF8=1` を設定済みだが、ターミナルによっては発生する。JSONレポート（`results/`）は正常に保存される。

### Ingest 後に検索結果が変わらない

Firestore のベクトルインデックスは即時反映だが、ブラウザキャッシュやCF側のインメモリキャッシュが古い場合がある。ローカル dev server を再起動するか、evaluate.py（ローカル直接実行）で確認する。
