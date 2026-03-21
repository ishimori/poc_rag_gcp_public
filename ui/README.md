# フロントエンド (ui/)

React 19 + TypeScript + Vite によるチャット画面・管理画面。

## 画面構成

### チャット画面 (`/`)

| ファイル | 説明 |
|---------|------|
| src/App.tsx | RAGチャットインターフェース（モデル選択、ソース表示） |

### 管理画面 (`/admin/*`)

| ファイル | 説明 |
|---------|------|
| src/admin/AdminLayout.tsx | 管理画面レイアウト（サイドナビ） |
| src/admin/Dashboard.tsx | ダッシュボード（スコア、技術マップ） |
| src/admin/Tuning.tsx | パラメータ調整・Ingest・Evaluate 実行 |
| src/admin/DataBrowser.tsx | Firestore チャンク閲覧・フィルタ |
| src/admin/History.tsx | 評価履歴・比較 |
| src/admin/Logs.tsx | クエリログ分析 |

### 共通

| ファイル | 説明 |
|---------|------|
| src/main.tsx | React Router ルーティング定義 |
| src/admin/api.ts | バックエンド API 呼び出し |

## 開発

```bash
npm install
npm run dev          # 開発サーバー（port 5180）
npm run build        # ui/dist/ に出力
npx tsc -b           # 型チェック
```

## 関連ドキュメント

- [画面仕様](../doc/spec/app/screens.md)
- [API仕様](../doc/spec/app/api.md)
