# バックエンド (src/)

Cloud Functions で動作する RAG パイプライン。エントリポイントは `main.py`（ルート）。

## モジュール構成

### config.py

環境変数とチューニングパラメータの一元管理（`Config` クラス）。

### search/ — RAG検索パイプライン

| ファイル | 説明 |
|---------|------|
| retriever.py | Firestore ベクトル検索（COSINE, 768次元） |
| reranker.py | Discovery Engine リランキング |
| flow.py | 検索 → リランク → LLM回答のオーケストレーション |

### ingest/ — ドキュメント取り込み

| ファイル | 説明 |
|---------|------|
| chunker.py | Markdown 分割（RecursiveCharacterTextSplitter + ヘッダーインジェクション） |
| embedder.py | Vertex AI text-embedding-005 による埋め込み生成 |
| store.py | Firestore バッチ書き込み（重複検出付き） |

### evaluate/ — 評価パイプライン

| ファイル | 説明 |
|---------|------|
| runner.py | テストケース実行 |
| scorer.py | キーワードマッチスコアリング |
| reporter.py | 結果レポート生成（Firestore + ローカルファイル保存） |

### browse/ — データエクスポート

| ファイル | 説明 |
|---------|------|
| exporter.py | Firestore コレクションの CSV エクスポート |

## 関連ドキュメント

- [API仕様](../doc/spec/app/api.md)
- [DB設計](../doc/spec/app/database.md)
- [インフラ構成](../doc/spec/infra/infrastructure.md)
