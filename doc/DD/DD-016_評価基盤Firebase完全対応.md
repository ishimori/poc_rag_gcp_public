# DD-016: 評価基盤のFirebase完全対応

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 進行中 |

## 目的

Evaluate / Ingest / History の全機能をFirebase Hosting + Cloud Functions上で動作させる。現状ローカルでしか実行できない評価・インジェスト機能をクラウド上で完結できるようにする。

## 背景・課題

- Ingest: `test-data/sources/` がCloud Functionsにデプロイされないため、Firebase上では実行不可
- Evaluate: `test-data/golden/eval_dataset.jsonl` が同上の理由で実行不可
- History: 評価結果が `results/` ディレクトリ（ローカルファイル）に保存されるため、Firebase上ではデータが存在しない
- 結果として、Tuning画面のRe-tune機能やHistory画面がFirebase Hosting上では使えない

## 検討内容

### 案の比較

| 案 | 内容 | メリット | デメリット |
|---|------|---------|----------|
| **A（採用）** | test-dataをデプロイ + 結果をFirestoreに保存 | シンプル。コード変更少ない | デプロイサイズ微増（数十KB） |
| B | test-data自体もFirestoreに格納 | 完全DB駆動 | 過剰。テストデータの管理がやりにくい |
| C | Cloud Storageに配置 | 本番向き | GCSセットアップが追加で必要 |

### 変更対象

| 変更 | ファイル | 内容 |
|------|---------|------|
| 1 | `firebase.json` | ignoreから `test-data` を除外 |
| 2 | `src/evaluate/reporter.py` | `save_report()` をFirestore `eval_results` コレクションへの書き込みに変更 |
| 3 | `main.py` (`_handle_evaluate_results`) | `results/` ディレクトリ読み込み → Firestore `eval_results` コレクション読み込みに変更 |
| 4 | `main.py` (`_handle_evaluate`) | `save_report()` の戻り値変更に対応 |

### Firestoreコレクション設計: `eval_results`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| date | string | 評価実行日時（ISO 8601） |
| config_params | map | 評価時のパラメータ |
| score_by_type | map | タイプ別スコア |
| overall | map | 全体スコア（passed, total, rate） |
| failed_cases | array | 失敗ケース一覧 |
| timestamp | timestamp | 記録日時（SERVER_TIMESTAMP） |

## 決定事項

1. **A案を採用**: test-dataをデプロイ対象に含め、評価結果をFirestoreに保存
2. 既存の `results/` ディレクトリへのファイル保存は**ローカル互換として残す**（try-except でFirestore書き込み失敗時のフォールバック）
3. UIのAPI呼び出しは変更不要（レスポンス形式は同じ）

## タスク一覧

### Phase 0: 事前精査
- [x] 📋 **タスク精査・詳細化** — 変更対象4ファイルの具体的な変更内容を確定
- [x] 😈 **Devil's Advocate調査** — 下記DA記録参照

### Phase 1: test-dataのデプロイ対応
- [ ] `firebase.json` — ignoreリストから `test-data` を削除
- [ ] 🔬 **機械検証**: `firebase deploy --only functions` でデプロイ成功すること
- [ ] 😈 **DA批判レビュー**

### Phase 2: 評価結果のFirestore保存
- [ ] `src/evaluate/reporter.py` — `save_report()` にFirestore書き込みを追加（ファイル保存も残す）
- [ ] `main.py` (`_handle_evaluate`) — `save_report()` の変更に対応
- [ ] `main.py` (`_handle_evaluate_results`) — Firestore `eval_results` コレクションから読み込みに変更
- [ ] 🔬 **機械検証**: ローカルで Evaluate 実行後、Firestoreに `eval_results` ドキュメントが作成されること
- [ ] 🔬 **機械検証**: History画面でFirestoreから結果が表示されること
- [ ] 😈 **DA批判レビュー**

### Phase 3: デプロイ・E2E検証
- [ ] Firebase再デプロイ（functions + hosting）
- [ ] 🔬 **機械検証**: Firebase Hosting上で Tuning → Re-tune → History比較 の一連のフローが動作すること
- [ ] 😈 **DA批判レビュー**

## ログ

### 2026-03-21
- DD作成。A案（test-dataデプロイ + Firestore保存）に決定

---

## DA批判レビュー記録

### Phase 0 DA批判レビュー

**DA観点:** アーキテクチャ変更の妥当性・リスク

| # | 発見した問題/改善点 | 重要度 | 再現手順（高/中は必須） | DA観点 | 対応 |
|---|-------------------|--------|----------------------|--------|------|
| 1 | test-dataをデプロイに含めるとデプロイサイズが増加 | 低 | `firebase deploy` 実行時のサイズ確認 | コスト | 現状のtest-dataは数十KB。Wikipediaデータ含めても数MB以内。PoCでは問題なし |
| 2 | Firestore書き込みとファイル保存の二重管理 | 低 | — | 保守性 | ファイル保存はローカル開発時の利便性のため残す。Firestore書き込み失敗時のフォールバックとしても機能 |
| 3 | eval_resultsコレクションにfailed_cases全件を保存するとドキュメントサイズが大きくなる | 中 | 100件超のテストケースで全件失敗時に確認 | スケーラビリティ | Firestoreの1ドキュメント上限は1MB。failed_casesは回答全文を含むが、100件×2KBでも200KB程度。PoCでは十分余裕 |
