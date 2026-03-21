# DD-016: 評価基盤のFirebase完全対応

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 完了 |

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

1. **A案を修正採用**: 評価結果のFirestore保存のみ実施。test-dataのデプロイは不要（Evaluate/IngestはCF上ではタイムアウトするためローカル専用）
2. 既存の `results/` ディレクトリへのファイル保存は**ローカル互換として残す**（try-except でFirestore書き込み失敗時のフォールバック）
3. UIのAPI呼び出しは変更不要（レスポンス形式は同じ）
4. **運用方針**: ローカルでEvaluate/Ingest/Tuning → Firestore保存 → Firebase HostingのHistory/Chat/Logsで閲覧

## タスク一覧

### Phase 0: 事前精査
- [x] 📋 **タスク精査・詳細化** — 変更対象4ファイルの具体的な変更内容を確定
- [x] 😈 **Devil's Advocate調査** — 下記DA記録参照

### ~~Phase 1: test-dataのデプロイ対応~~ （取り消し）
- ~~`firebase.json` — ignoreリストから `test-data` を削除~~
- **取り消し理由**: CF上でEvaluate/Ingestが74件×RAGでタイムアウト（540s超）。ローカル専用と割り切り、firebase.jsonのignoreに `test-data` を戻した

### Phase 2: 評価結果のFirestore保存
- [x] `src/evaluate/reporter.py` — `save_report()` にFirestore書き込みを追加（ファイル保存も残す）
- [x] `main.py` (`_handle_evaluate_results`) — Firestore `eval_results` 優先読み込み + ローカルファイルフォールバック
- [x] 🔬 **機械検証**: Evaluate実行後、Firestoreに `eval_results` ドキュメント作成確認 ✅
- [ ] 🔬 **機械検証**: History画面でFirestoreから結果が表示されること（PH3で実施）
- [x] 😈 **DA批判レビュー** — 重大な問題なし

### Phase 3: デプロイ・E2E検証
- [x] Firebase再デプロイ（functions + hosting + firestore）
- [x] 🔬 **機械検証**: History APIがFirestoreから結果を取得できること ✅
- [x] 🔬 **機械検証**: ローカルで Evaluate → Firestoreに結果保存 → Hosting上のHistoryで閲覧 ✅
- ⚠️ **制約事項**: Evaluate実行はCloud Functions上では74件×RAGでタイムアウト（540s超）。ローカル実行 → Firestore保存 → Hosting閲覧の運用
- [x] 😈 **DA批判レビュー** — ベクトルインデックス削除問題を発見・記録

### Phase 4: デプロイ手順書の作成
- [x] `doc/spec/infra/development.md` のデプロイセクションを全面更新
  - `.env` リネーム手順を明記
  - `--force` 禁止の理由（ベクトルインデックス削除）を表で説明
  - デプロイ後のベクトルインデックス確認手順と再作成コマンド
  - ローカルとFirebaseの役割分担表を追加
- [x] `doc/spec/infra/infrastructure.md` のDD-016関連記述を修正

## ログ

### 2026-03-21
- DD作成。A案（test-dataデプロイ + Firestore保存）に決定
- PH1完了: firebase.jsonからtest-data除外
- PH2完了: reporter.pyにFirestore書き込み追加、main.pyのevaluate_resultsをFirestore優先に変更
- PH3: デプロイ成功。ただし `firebase deploy --force` がベクトルインデックスを削除する問題を発見
  - 原因: firestore.indexes.jsonにベクトルインデックスは宣言型で管理できない（gcloud CLIのみ）
  - 対応: `--force` なしでデプロイするか、デプロイ後にベクトルインデックスを再作成する
  - Evaluate実行はCloud Functions上では74件×RAGでタイムアウト（540s超）
  - 運用: ローカルでEvaluate → Firestore保存 → Hosting上のHistoryで閲覧
- 方針転換: test-dataのデプロイは取り消し（firebase.jsonのignoreにtest-dataを戻す）
  - Evaluate/IngestはCF上ではタイムアウトするためローカル専用と割り切る
  - 中途半端にCFで実行できても開発スピードが落ちるだけと判断
  - 有効な変更: 評価結果のFirestore保存 + History APIのFirestore読み込みのみ残す

---

## DA批判レビュー記録

### Phase 0 DA批判レビュー

**DA観点:** アーキテクチャ変更の妥当性・リスク

| # | 発見した問題/改善点 | 重要度 | 再現手順（高/中は必須） | DA観点 | 対応 |
|---|-------------------|--------|----------------------|--------|------|
| 1 | test-dataをデプロイに含めるとデプロイサイズが増加 | 低 | `firebase deploy` 実行時のサイズ確認 | コスト | 現状のtest-dataは数十KB。Wikipediaデータ含めても数MB以内。PoCでは問題なし |
| 2 | Firestore書き込みとファイル保存の二重管理 | 低 | — | 保守性 | ファイル保存はローカル開発時の利便性のため残す。Firestore書き込み失敗時のフォールバックとしても機能 |
| 3 | eval_resultsコレクションにfailed_cases全件を保存するとドキュメントサイズが大きくなる | 中 | 100件超のテストケースで全件失敗時に確認 | スケーラビリティ | Firestoreの1ドキュメント上限は1MB。failed_casesは回答全文を含むが、100件×2KBでも200KB程度。PoCでは十分余裕 |
