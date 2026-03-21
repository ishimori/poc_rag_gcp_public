# DD-019-3-2: Tuning画面の実行状態表示

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 完了 |

## 目的

Tuning画面を開いた際に、バックグラウンドで実行中のタスク（Ingest、Evaluate等）があれば、自動的に実行状態を表示する。

## 背景・課題

DD-019-3の再Ingest実行中に、Tuning画面にはタスクの実行状態が表示されなかった。ユーザーが画面を開いたときに「何かが動いているのか」「終わったのか」が分からない。

### 現在の問題

- **Ingestに進捗表示がない**: ボタンを押した後「取り込み中...」のまま、完了するまで件数や経過時間のフィードバックがない
- Evaluateは既にリアルタイム進捗表示（プログレスバー、件数、経過/残り時間、中止ボタン）が実装済み
- 別タブで実行を開始した場合、Tuning画面ではIngestの状態が不明（Evaluateは`evalDetached`で検出可能）
- 長時間タスク（Ingest: 数分〜10分）で特に問題

## 検討内容

### 実行状態の管理方法

| 案 | 内容 | メリット | デメリット |
|----|------|---------|-----------|
| A: Firestoreにタスク状態を記録 | `task_status`コレクションに実行中/完了/エラーを保存 | 複数クライアント間で共有可能 | Firestore書き込みコスト |
| B: Cloud Functions のメモリ内管理 | グローバル変数で状態管理 | 実装が簡単 | CFインスタンスが変わるとリセット |
| C: Admin APIにポーリングエンドポイント | `/api/admin/task-status` で状態を返す | RESTful | ローカル実行時は未対応 |

### 表示すべき情報

- タスク種別（Ingest / Evaluate）
- 開始日時
- 進捗（処理済み件数 / 全件数）
- ステータス（実行中 / 完了 / エラー）
- 完了日時・結果サマリ

## 決定事項

- **案B採用（インメモリ管理）**: Evaluateで実績のある`_eval_progress`グローバル変数パターンをIngestにも適用
  - ローカル単一プロセス（PoC前提）なのでグローバル変数で十分
  - Firestoreへの書き込みコスト不要
  - 将来CLIからの実行検出が必要になった場合は案A（Firestore）に切替可能（フロントエンド変更なし）
- **スコープ**: IngestにEvaluateと同等の進捗表示を追加（Evaluateは既に実装済みのため対象外）
- **UI設計**: Ingestアクションカード内にプログレスバー表示（Evaluateと同じCSS・同じ配置パターン）
- **表示項目**: ファイル数進捗 / 経過時間 / 残り推定 / 処理中ファイル名 / 中止ボタン
- **対応範囲**: Tuning画面ボタン経由の実行のみ。CLI（`scripts/ingest.py`）は対象外

## タスク一覧

### Phase 0: 事前精査 ✅
- [x] 📋 **実行状態の管理方法を決定** → 案B（インメモリ管理）。Evaluateの実績パターン踏襲
- [x] 📋 **UI設計** → Evaluateと同じプログレスバー形式。Ingestアクションカード内に配置
- [ ] 😈 **Devil's Advocate調査**

### Phase 1: 実装
- [x] `main.py`: `_ingest_progress` グローバル dict + `GET /ingest/status` + `POST /ingest/cancel` エンドポイント追加
- [x] `main.py`: `_handle_ingest()` にファイルループ内の進捗更新・キャンセルチェック追加
- [x] `ui/src/admin/api.ts`: `IngestProgress` 型 + `getIngestStatus()` + `cancelIngest()` 追加
- [x] `ui/src/admin/Tuning.tsx`: Ingest進捗ポーリング（2秒間隔）+ detached検出 + プログレスバーUI + 中止ボタン
- [ ] 🔬 **機械検証**: ローカルサーバーでIngest実行 → プログレスバー表示確認
- [ ] 🔬 **機械検証**: 画面再オープン時のdetachedモード動作確認
- [ ] 😈 **DA批判レビュー**

## ログ

### 2026-03-21
- DD作成（DD-019-3からの派生）
- 背景: 再Ingest実行中にTuning画面で実行状態が見えない問題
- Phase 0完了: 案B（インメモリ管理）採用。Evaluateの実績パターン踏襲
- Phase 1 コード実装完了:
  - `main.py`: `_ingest_progress` dict、ステータス/キャンセルAPI、`_handle_ingest`内の進捗更新
  - `api.ts`: `IngestProgress`型、`getIngestStatus()`、`cancelIngest()`
  - `Tuning.tsx`: ポーリングuseEffect、detached検出、プログレスバーUI、中止ボタン

---

## DA批判レビュー記録
