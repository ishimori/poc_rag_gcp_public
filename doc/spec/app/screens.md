# 画面設計書

> 最終更新: 2026-03-21 | 対応DD: DD-012

## ルーティング構成

```
BrowserRouter
├── /                    → App（チャット画面）
└── /admin               → AdminLayout（管理画面レイアウト）
    ├── index            → Dashboard
    ├── /admin/tuning    → Tuning
    ├── /admin/data      → DataBrowser
    ├── /admin/history   → History
    └── /admin/logs      → Logs
```

**実装**: `ui/src/main.tsx` — React Router v7（`react-router-dom`）

### ナビゲーション

- チャット → 管理画面: ヘッダーの「Admin →」リンク
- 管理画面 → チャット: サイドナビの「← Chat」リンク
- 管理画面内: サイドナビの `NavLink`（アクティブ状態のハイライトあり）

---

## 1. チャット画面（`/`）

**コンポーネント**: `ui/src/App.tsx`

**使用API**: `POST /api`

### 構成

| 領域 | 内容 |
|------|------|
| ヘッダー | タイトル「エンタープライズRAG PoC」+ Admin リンク |
| サイドバー | モデル選択（ラジオボタン）+ サンプル質問（4件） |
| チャットエリア | メッセージ一覧 + 入力欄 |

### モデル選択

| モデル | 表示名 | 価格（per 1M tokens） | ラベル |
|--------|--------|---------------------|-------|
| `gemini-2.5-flash` | Gemini 2.5 Flash | $0.15 / $0.60 | 低コスト |
| `gemini-2.5-pro` | Gemini 2.5 Pro | $1.25 / $10.00 | 高性能 |

### サンプル質問

1. 「ネジ999999の材質は？」
2. 「VPN接続の手順を教えて」
3. 「PCが重い」
4. 「有給休暇は何日もらえる？」

### メッセージ表示

- **ユーザー**: テキストのみ
- **アシスタント**: Markdown レンダリング（`react-markdown`）+ メタ情報（モデル名、応答時間）
- **参照ソース**: 折りたたみ式リスト（ファイル名#チャンク番号、スコア、内容先頭120文字）
- **ローディング**: 「検索・回答生成中...」表示
- **自動スクロール**: 新メッセージ追加時に最下部へスクロール

---

## 2. Dashboard（`/admin`）

**コンポーネント**: `ui/src/admin/Dashboard.tsx`

**使用API**: `GET /api/admin/config`, `GET /api/admin/evaluate/results`, `GET /api/admin/chunks`

### 構成

| セクション | 内容 |
|-----------|------|
| スコアカード | 全体スコア（%）、チャンク数、現在のパラメータ |
| テストタイプ別スコア | 10パターンのスコア表（スコア、件数、評価バッジ） |
| 技術マップ | 13の対策技術一覧（実装済み / 調査済み、改善対象テストタイプとの対応） |

### スコア評価基準

| スコア | ラベル | バッジ |
|--------|-------|-------|
| ≥ 90% | 優秀 | ◎ |
| ≥ 70% | 良好 | ○ |
| ≥ 50% | 改善余地あり | △ |
| < 50% | 要対策 | ✕ |

### テストタイプ（10パターン）

| キー | 表示名 | 説明 |
|------|--------|------|
| exact_match | 完全一致 | 型番・固有名詞を正確に特定できるか |
| similar_number | 類似数値の区別 | 似た番号を混同しないか |
| semantic | 意味検索 | 言い換え・類義語に対応できるか |
| step_sequence | 手順再現 | 操作手順を正しい順序で返せるか |
| multi_chunk | 複数チャンク統合 | 複数の文書断片を横断して統合できるか |
| unanswerable | 回答不能判定 | 文書にない質問に「分かりません」と言えるか |
| ambiguous | 曖昧質問対応 | 曖昧な質問に適切に対応できるか |
| cross_category | カテゴリ横断 | 異なる分野の文書を横断して回答できるか |
| security | セキュリティ | 権限外の情報を適切にブロックできるか |
| noise_resistance | ノイズ耐性 | 無関係な情報の中から正しい情報を抽出できるか |

---

## 3. Tuning（`/admin/tuning`）

**コンポーネント**: `ui/src/admin/Tuning.tsx`

**使用API**: `GET /api/admin/config`, `PUT /api/admin/config`, `POST /api/admin/ingest`, `POST /api/admin/evaluate`

### 構成

| セクション | 内容 |
|-----------|------|
| パラメータ編集 | 5パラメータの入力フォーム + Save ボタン |
| インジェスト | Clear チェックボックス + Run Ingest ボタン + 結果表示 |
| 評価 | Run Evaluate ボタン + スコア結果表示（タイプ別） |
| Re-tune | ワンクリックで Save → Ingest(clear) → Evaluate を順次実行 |

### パラメータ編集

| パラメータ | 入力タイプ | 説明 |
|-----------|-----------|------|
| chunk_size | number | チャンク分割の最大文字数 |
| chunk_overlap | number | チャンク間のオーバーラップ文字数 |
| top_k | number | ベクトル検索の取得件数 |
| rerank_top_n | number | リランキング後の最終件数 |
| rerank_threshold | number (step=0.01) | リランキングスコアの最低閾値 |

### ステータス管理

各操作（config保存、ingest、evaluate、re-tune）は `idle` / `loading` / `success` / `error` の4状態で管理。

---

## 4. Data Browser（`/admin/data`）

**コンポーネント**: `ui/src/admin/DataBrowser.tsx`

**使用API**: `GET /api/admin/chunks`

### 構成

| セクション | 内容 |
|-----------|------|
| フィルタ | Category（select）、Security Level（select）、Limit（number）+ Fetch Data ボタン |
| チャンク一覧 | テーブル（source_file, chunk_index, category, security_level, content先頭50文字） |
| 詳細表示 | 行クリックで全文表示（id, content全文, category, security_level, allowed_groups） |

### フィルタ選択肢

**Category**: All / parts_catalog / it_helpdesk / hr_policy / finance / network

**Security Level**: All / public / internal / confidential

### カラータグ

カテゴリとセキュリティレベルにはCSSクラスによるカラータグを表示。

---

## 5. History（`/admin/history`）

**コンポーネント**: `ui/src/admin/History.tsx`

**使用API**: `GET /api/admin/evaluate/results`

### 構成

| セクション | 内容 |
|-----------|------|
| 評価結果一覧 | テーブル（日時、スコア%、passed/total、5パラメータ値） |
| タイプ別詳細 | 行クリックで展開（テストタイプ別スコア表 + トレンドバー） |

### テーブルカラム

| カラム | 内容 |
|--------|------|
| Date | 評価日時（秒まで） |
| Score | 全体スコア%（50%以上: 緑、未満: 赤） |
| Passed | 合格数/全体数 |
| chunk_size | パラメータ値 |
| overlap | パラメータ値 |
| top_k | パラメータ値 |
| rerank_top_n | パラメータ値 |
| threshold | パラメータ値 |

---

## 6. Logs（`/admin/logs`）

**コンポーネント**: `ui/src/admin/Logs.tsx`

**使用API**: `GET /api/admin/logs`

### 構成

| セクション | 内容 |
|-----------|------|
| フィルタ | No-answer only（チェックボックス）、Limit（number）+ Fetch ボタン |
| ログ一覧 | テーブル（日時、クエリ先頭40文字、モデル、応答時間、ソース数、no_answer） |
| 詳細表示 | 行クリックで展開（クエリ全文、回答全文、ソース一覧） |

### 初期動作

- ページ表示時に自動で `handleFetch()` を呼び出し（`useEffect`）
- デフォルト: no_answer フィルタなし、limit=50

### タイムスタンプ表示

- `ja-JP` ロケール、`Asia/Tokyo` タイムゾーンで表示
