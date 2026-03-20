# DD-009-3: チャットUI TypeScript移行

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-20 | 2026-03-20 | 進行中 |

## 目的

DD-009で実装したStreamlitチャットUIを、TypeScript（React/Next.js）ベースに移行する。PoCの画面量が少ないため、Streamlitの生産性メリットよりTypeScriptの表現力を優先する。

## 背景・課題

- DD-009でStreamlitを選定した理由は「PoCの高速プロトタイピングに最適」
- しかし実際のチャットUI画面は1画面のみで、実装量が少ない
- 実装量が少ないなら、Streamlitの生産性メリットは薄く、TypeScriptの表現力・カスタマイズ性の方が価値が高い
- 本番化時にFastAPI + フロントエンドへの移行を見据えていた（DD-009のDA批判レビュー）が、最初からTypeScriptで作れば移行コスト不要
- DD-009-4（管理者向けUI）も含めると、UIの表現力がより重要になる

## 検討内容

### 技術選択

| 選択肢 | メリット | デメリット |
|--------|---------|----------|
| **React + Vite** | 軽量、高速起動、学習コスト低 | SSR不要ならこれで十分 |
| **Next.js** | SSR/SSG、APIルート、ファイルベースルーティング | PoCには若干オーバースペック |
| **Streamlit（現状維持）** | 実装済み、変更コストゼロ | 表現力に限界、シングルスレッド |

### バックエンドとの関係

- 現在のPython共通モジュール（`src/`）はそのまま維持
- TypeScript UIからPythonバックエンドをAPI経由で呼ぶ構成
- バックエンドAPI: FastAPI or Cloud Functions
- `src/search/flow.py` の `rag_flow()` をAPIエンドポイントとして公開

### DD-009-4との関係

- DD-009-4（管理者向けUI）も同じTypeScriptプロジェクトで構築できる
- チャットUI（利用者向け）と管理画面（管理者向け）を同一フロントエンドに統合

## アーキテクチャ

### 全体構成図

```
┌─────────────────────────────────────────────────────────┐
│                      Firebase                           │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────────────┐ │
│  │  Firebase Hosting │      │  Cloud Functions (Python) │ │
│  │                  │      │                          │ │
│  │  React + Vite    │ HTTP │  POST /chat              │ │
│  │  (TypeScript)    │─────▶│    → rag_flow()          │ │
│  │                  │◀─────│    → RAGResponse         │ │
│  │  ┌────────────┐  │ JSON │                          │ │
│  │  │ チャットUI  │  │      │  GET /sources            │ │
│  │  │ (DD-009-3) │  │      │    → データ一覧           │ │
│  │  ├────────────┤  │      │                          │ │
│  │  │ 管理者UI   │  │      └──────────┬───────────────┘ │
│  │  │ (DD-009-4) │  │               │                  │
│  │  └────────────┘  │               │                  │
│  └──────────────────┘               │                  │
└─────────────────────────────────────┼──────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │           GCP Services             │
                    │                 │                   │
                    │    ┌────────────▼──────────┐       │
                    │    │    Firestore           │       │
                    │    │  (ベクトルDB + メタ)    │       │
                    │    └────────────┬──────────┘       │
                    │                 │                   │
                    │    ┌────────────▼──────────┐       │
                    │    │    Vertex AI           │       │
                    │    │  ・Gemini 2.5 Flash    │       │
                    │    │  ・Embedding API       │       │
                    │    │  ・Ranking API         │       │
                    │    └──────────────────────-┘       │
                    └───────────────────────────────────┘
```

### データフロー

```
ユーザー質問
  │
  ▼
[React UI] ──POST /chat──▶ [Cloud Function]
                               │
                               ├─ 1. Embedding生成 (Vertex AI)
                               ├─ 2. ベクトル検索 (Firestore, top-10)
                               ├─ 3. リランキング (Ranking API, top-5)
                               ├─ 4. LLM回答生成 (Gemini 2.5 Flash)
                               │
                               ▼
[React UI] ◀──JSON────────── RAGResponse
  │                          { answer, sources, reranked_sources }
  ▼
回答 + ソース表示
```

### ディレクトリ構成（予定）

```
poc_rag_gcp_public/
├── ui/                        # フロントエンド（新規）
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Chat.tsx       # チャットUI (DD-009-3)
│   │   │   └── Admin.tsx      # 管理者UI (DD-009-4)
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── functions/                 # Cloud Functions（新規）
│   ├── main.py               # エントリポイント
│   └── requirements.txt
├── src/                       # 既存Pythonモジュール（変更なし）
│   ├── search/flow.py
│   ├── ingest/
│   └── ...
├── firebase.json              # Firebase設定
└── .firebaserc
```

## 決定事項

- **フロントエンド**: React + Vite（PoCに十分、SSR不要、軽量）
- **バックエンドAPI**: Cloud Functions for Firebase（Python、既存src/モジュール活用）
- **構成**: Firebase Hosting（静的フロント） + Cloud Functions（APIバックエンド）
- **DD-009-4統合**: 同一Viteプロジェクト内でReact Routerにより分離
- **デプロイ**: Firebase のみ（Hosting + Functions）

## タスク一覧

### Phase 0: 事前精査
- [x] 📋 **技術選定の確定**
  - React + Vite を選定（SSR不要、PoCに軽量で最適）
  - FastAPI を選定（既存Pythonモジュール活用、Cloud Runと相性良好）
- [x] 😈 **Devil's Advocate調査**
  - Streamlit継続案 → DD-009-4の複雑UIを考慮すると移行が妥当
  - API通信オーバーヘッド → rag_flow()が数秒のためHTTP往復(数ms)は無視可能
  - 同一プロジェクトリスク → 認証はバックエンドAPI側で制御、フロント構成に影響なし

### Phase 1: バックエンドAPI化（Cloud Functions for Firebase）
- [ ] Firebase Functions（Python）プロジェクト初期化
- [ ] `rag_flow()` を Cloud Function として公開（`POST /chat`）
- [ ] APIエンドポイント設計（`POST /chat`, `GET /sources` 等）
- [ ] 🔬 **機械検証**: Functions エミュレータでAPIを叩いて回答が返ること

### Phase 2: TypeScript UIの実装
- [ ] フロントエンドプロジェクト初期化
- [ ] チャット画面の実装（質問入力、会話履歴表示、ソース表示）
- [ ] 🔬 **機械検証**: ブラウザで質問→回答が表示されること
- [ ] 😈 **DA批判レビュー**

### Phase 3: Streamlit削除・統合テスト
- [ ] `app.py`（Streamlit）を削除
- [ ] `pyproject.toml` から `streamlit` 依存を削除
- [ ] 🔬 **機械検証**: TypeScript UIで質問→回答→ソース表示が動作すること

## ログ

### 2026-03-20
- DD作成
- Phase 0完了: React + Vite + FastAPI に決定
  - Next.jsはSSR不要のPoCにはオーバースペック
  - Cloud Functions for Firebase で既存src/モジュールをAPI化（Firebase統一構成）
  - DD-009-4と同一Viteプロジェクトで統合予定

---

## DA批判レビュー記録

### Phase 0 DA批判レビュー

**DA観点:** 技術選定の妥当性を検証

| # | 発見した問題/改善点 | 重要度 | 再現手順（高/中は必須） | DA観点 | 対応 |
|---|-------------------|--------|----------------------|--------|------|
| 1 | Streamlitは動作中のUIを捨てるコスト | 中 | 現状2画面が動作している | 沈没コストの誤謬に注意。DD-009-4で複雑UIが必要になるため、早期移行の方が総コスト低い | 移行実施 |
| 2 | FastAPI追加でデプロイ構成が複雑化 | 低 | 現在はStreamlit単体でCloud Run 1サービス | PoCフェーズではローカル開発が主。本番化時にはAPI分離が必須なので先行投資 | 許容 |
| 3 | CORS設定が必要（フロント・バックエンド分離） | 低 | フロントとAPIが別オリジンで動作 | 開発時はViteのproxy設定で回避可能 | Phase 1で対応 |
