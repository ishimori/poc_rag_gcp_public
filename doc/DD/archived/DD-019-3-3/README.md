# DD-019-3-3 添付資料

DD本体: [DD-019-3-3_別セッション実行タスクのadmin画面表示.md](../DD-019-3-3_別セッション実行タスクのadmin画面表示.md)

## 資料一覧

| ファイル | 内容 |
|---|---|
| [architecture.md](architecture.md) | アーキテクチャ図（現状 vs 改善後、コンポーネント責務） |
| [er-diagram.md](er-diagram.md) | Firestoreデータモデル（task_statusコレクション設計） |
| [state-transition.md](state-transition.md) | 状態遷移図・シーケンス図（正常/中止フロー） |

## 設計の要点

- **Firestore `task_status` コレクション**で CLI/バックエンド間の状態共有を実現
- 固定ドキュメントID（`"ingest"` / `"evaluate"`）で常に1パスで読み書き
- フロントエンドは**変更なし**（DD-019-3-2のポーリング・UIをそのまま再利用）
