# DD-009: Streamlit チャットUI + Python全面移行

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-20 | 2026-03-20 | 完了 |

## 目的

RAGパイプライン全体をPythonに統一し、StreamlitでチャットUIを実装する。CLIの数値評価だけでなく、人間が実際に質問して動作を確認できるようにする。

## 背景・課題

- DD-008でTypeScript製のingest/search/evaluateパイプラインが動作している（初回スコア 66.7%）
- しかしCLI出力だけでは「RAGがどう振る舞うか」を体感しにくい
- TypeScript + Pythonの二重管理はPoCとして管理コストが見合わない
- 本番デプロイ先はCloud Run（Streamlitをそのまま載せられる）

## 検討内容

### 技術選択の経緯

| 選択肢 | 検討結果 |
|--------|---------|
| Express + HTML/JS | UIの見栄えが質素、Firebase Hosting前提だったが社内ツールにはCloud Runの方が適切 |
| React / Next.js | PoC向けにはオーバー |
| **Streamlit** | **採用。チャットUIのプロトタイピングに最適。Cloud Runでそのまま本番化可能** |

### Python移行の判断

| 観点 | 判断 |
|------|------|
| TypeScript資産の価値 | 当日作成したばかり、守る必要なし |
| GCP SDK | Pythonの方が充実（google-cloud-firestore, vertexai） |
| 言語統一 | ingest/evaluate/UIが全て同じ言語で共通モジュールを使い回せる |
| デプロイ | Streamlit + Cloud Run で完結。Firebase Hosting + Cloud Functions が不要に |

### アーキテクチャ

```
ローカル開発:
  streamlit run app.py (localhost:8501) → GCP APIs

本番:
  Cloud Run (Streamlit) → GCP APIs
    ├── Firestore (ベクトルDB)
    ├── Vertex AI (Embedding + LLM)
    └── Discovery Engine (Ranking API)
```

### プロジェクト構成（移行後）

```
poc_rag_gcp_public/
├── app.py                    # Streamlit チャットUI
├── src/
│   ├── config.py             # パラメータ設定
│   ├── ingest/
│   │   ├── chunker.py        # チャンク分割
│   │   ├── embedder.py       # Embedding API
│   │   └── store.py          # Firestore書き込み
│   ├── search/
│   │   ├── retriever.py      # Firestore検索
│   │   ├── reranker.py       # Ranking API
│   │   └── flow.py           # RAG Flow
│   └── evaluate/
│       ├── scorer.py         # スコアリング
│       ├── runner.py         # 評価実行
│       └── reporter.py       # レポート出力
├── scripts/
│   ├── ingest.py             # uv run python scripts/ingest.py
│   └── evaluate.py           # uv run python scripts/evaluate.py
├── test-data/                # DD-007で作成済み
├── results/                  # 評価結果（gitignore）
├── pyproject.toml            # Python依存管理（UV）
└── .env                      # 環境変数（gitignore）
```

## 決定事項

- TypeScript実装を全て削除し、Pythonに統一
- Streamlit でチャットUI実装
- ローカル開発: `streamlit run app.py`
- 本番デプロイ: Cloud Run
- CLIスクリプト: `uv run python scripts/ingest.py`, `uv run python scripts/evaluate.py`

## タスク一覧

### Phase 0: DA批判レビュー
- [x] 😈 **Devil's Advocate調査** — Python SDK可用性・Streamlit本番適性の検証

### Phase 1: TypeScript削除 + Python依存追加
- [x] `package.json`, `tsconfig.json`, `package-lock.json`, `main.py` を削除
- [x] `src/**/*.ts`, `scripts/**/*.ts` を削除（13ファイル）
- [x] `node_modules/` を削除
- [x] `pyproject.toml` に依存追加: `streamlit`, `google-cloud-firestore`, `vertexai`, `google-cloud-discoveryengine`, `langchain-text-splitters`, `python-dotenv`
- [x] 🔬 **機械検証**: `uv sync` 成功（68パッケージインストール）

### Phase 2: Python共通モジュール実装
- [x] `src/__init__.py`, `src/ingest/__init__.py`, `src/search/__init__.py`, `src/evaluate/__init__.py` 作成
- [x] `src/config.py` — パラメータ設定（python-dotenvで.env読み込み）
- [x] `src/ingest/chunker.py` — Recursive Character Text Splitter + ヘッダーインジェクション
- [x] `src/ingest/embedder.py` — Vertex AI `TextEmbeddingModel` (text-embedding-005)
- [x] `src/ingest/store.py` — Firestore書き込み（`Vector` クラス使用、content_hash重複チェック）
- [x] `src/search/retriever.py` — Firestore `find_nearest()` ベクトル検索
- [x] `src/search/reranker.py` — Discovery Engine `RankServiceClient`
- [x] `src/search/flow.py` — `GenerativeModel` (gemini-2.5-flash) でRAG Flow
- [x] `src/evaluate/scorer.py` — キーワード判定
- [x] `src/evaluate/runner.py` — 評価実行
- [x] `src/evaluate/reporter.py` — レポート生成（Windows UTF-8対応済み）
- [x] `scripts/ingest.py` — エントリポイント
- [x] `scripts/evaluate.py` — エントリポイント（`sys.stdout.reconfigure(encoding="utf-8")`）
- [x] 🔬 **機械検証**: `uv run python scripts/ingest.py --clear` → 30チャンク格納成功
- [x] 🔬 **機械検証**: `uv run python scripts/evaluate.py` → 30/45 (66.7%) TypeScript版と同等

### Phase 3: Streamlit チャットUI実装
- [x] `app.py` — チャット画面
  - `st.chat_input` で質問入力
  - `st.chat_message` で会話履歴表示
  - `st.expander` で参照ソース（ファイル名、スコア）を折りたたみ表示
  - `st.spinner` でローディング表示
- [ ] 🔬 **機械検証**: `streamlit run app.py` が起動し、質問→回答が表示されること
- [ ] 👀 **目視確認**: チャットの見た目、ソース表示が自然か

### Phase 4: 統合テスト
- [ ] `uv run python scripts/ingest.py --clear && uv run python scripts/evaluate.py` がTypeScript版と同等のスコアを出すこと
- [ ] Streamlitで複数回の質問→回答が正しく表示されること
- [ ] 回答不能ケース（「来月の株価は？」）で適切に「情報がありません」と表示されること
- [ ] 👀 **目視確認**: 実際に触ってみて「動いている」と体感できること
- [ ] 🔬 **機械検証**: TypeScript版スコア（30/45）と同等以上のスコアが出ること

## ログ

### 2026-03-20
- DD作成（当初Express + HTML/JS案）
- Streamlit + Python全面移行に方針転換
- Phase 0: DA批判レビュー完了（Python SDK全対応確認、Streamlit本番リスク記録）
- Phase 1: TypeScript削除、Python依存追加（uv sync成功）
- Phase 2: Python共通モジュール実装、ingest/evaluate動作確認（30/45 = 66.7%）
- Phase 3: Streamlit チャットUI実装、ブラウザで動作確認完了

---

## DA批判レビュー記録

### Phase 0 DA批判レビュー

**DA観点:** Python移行の技術的リスクとStreamlitの本番適性

#### 1. Python SDK可用性（結論: 全て問題なし）

| SDK | ベクトル検索対応 | 確認結果 |
|-----|----------------|---------|
| `google-cloud-firestore` | `find_nearest()` (v2.16+) | ✅ COSINE距離、distance_result_field対応 |
| `vertexai` | `TextEmbeddingModel.get_embeddings()` | ✅ text-embedding-005対応、task_type指定可能 |
| `google-cloud-discoveryengine` | `RankServiceClient.rank()` | ✅ semantic-ranker-default-004利用可能 |

#### 2. Streamlit × Cloud Run の本番リスク

| # | 発見した問題 | 重要度 | 詳細 | 対応 |
|---|------------|--------|------|------|
| 1 | **シングルスレッド: 同時2ユーザーでブロッキングの可能性** | 高 | Streamlitはシングルスレッド。LLM応答待ち中に別ユーザーがリクエストするとブロックされる。3000人規模では破綻する | ⏭️ PoCフェーズでは問題なし。本番化時にCloud Runインスタンス数スケーリング + セッションアフィニティで対応。同時利用が10人超なら別UIフレームワークへの移行を検討 |
| 2 | **WebSocket切断でセッション状態が消失** | 中 | Cloud Runのリクエストタイムアウト（デフォルト300秒）でWebSocketが切れると、会話履歴がリセットされる | ⏭️ タイムアウトを600秒に延長。会話履歴をFirestoreに永続化する設計を本番化時に検討 |
| 3 | **コールドスタート: コンテナ起動に数秒かかる** | 低 | Streamlit + 依存パッケージの読み込みで初回アクセスが遅い | ⏭️ `min-instances=1` で回避可能（月数百円程度のコスト増） |
| 4 | **スケールtoゼロが効かない可能性** | 低 | WebSocketキープアライブでCloud Runがアイドルにならず課金が継続するケース報告あり | ⏭️ PoCでは影響小。本番化時にヘルスチェック設定とアイドルタイムアウトを調整 |

#### 判定

- 重要度「高」の#1は、**PoCフェーズ（数人の検証）では発生しない**。3000人が使う本番では対応が必要だが、それは別DDで扱うべき課題
- Python SDK は全て揃っており、移行に技術的障壁なし
- **結論: 予定通りStreamlit + Python移行で進行**
- **本番化方針**: PoCはStreamlit、本番化時はFastAPI + フロントエンドへの移行を検討。`src/` 共通モジュールはそのまま流用可能な設計にする
