# DD-018: README・DOCUMENT-MAP整備

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 完了 |

## 目的

各ディレクトリにREADMEを配置し、CLAUDE.mdをリンク集に軽量化し、DOCUMENT-MAP.mdで全ドキュメントの所在を一覧管理する。

## 背景・課題

- CLAUDE.mdにプロジェクト情報が集中（4.5KB）。Claude Codeは毎会話で読み込むため小さく保つべき
- root にREADME.mdがない。src/, scripts/, doc/ にもない
- ドキュメントが doc/spec/, doc/research/, doc/DD/ 等に分散しており、全体像の把握が困難

## 決定事項

- CLAUDE.md はDD設定・スキル・規約・リンクのみ（~1.5KB目標）
- README.md（root）にプロジェクト概要を移動
- DOCUMENT-MAP.md で全ドキュメントのパス・説明を一覧管理
- サブディレクトリREADMEは src/, ui/, scripts/, doc/ の4箇所（個別モジュールREADMEは不要）

## タスク一覧

### Phase 1: root README.md + DOCUMENT-MAP.md 作成
- [x] `README.md`（root）作成 — CLAUDE.mdからプロジェクト概要・技術スタック・ディレクトリ構成・セットアップ・テスト方針・セキュリティ要件を移動
- [x] `DOCUMENT-MAP.md`（root）作成 — spec/5ファイル、research/12ファイル、ADR/9+index、cross-cutting/4ファイル、presentation/13スライド、DD/INDEX.md、各READMEを網羅
- [x] 🔬 **機械検証**: DOCUMENT-MAP.md に記載された全34パスが実在確認済み

### Phase 2: CLAUDE.md 軽量化
- [x] `CLAUDE.md` — プロジェクト概要・技術スタック・ディレクトリ構成・テスト方針・セキュリティ要件を削除
- [x] `CLAUDE.md` — 冒頭にREADME.md / DOCUMENT-MAP.md へのリンク追加
- [x] `CLAUDE.md` — ドキュメント更新ルールにDOCUMENT-MAP.md更新を追加
- [x] 🔬 **機械検証**: CLAUDE.md 43行（109行 → 43行、60%削減）

### Phase 3: サブディレクトリ README 作成
- [x] `src/README.md` 作成 — search/ingest/evaluate/browse の説明 + 主要ファイル一覧
- [x] `ui/README.md` 書き換え — Viteテンプレート → 画面構成・コンポーネント一覧
- [x] `scripts/README.md` 作成 — 5スクリプトの一覧と説明
- [x] `doc/README.md` 作成 — spec/research/DD/presentation/templates へのポインタ
- [x] 🔬 **機械検証**: 各READMEのリンク先存在確認済み

## ログ

### 2026-03-21
- DD作成
- Phase 1-3 完了
  - README.md（root）: プロジェクト概要・セットアップ
  - DOCUMENT-MAP.md: 全ドキュメント一覧（34パス）
  - CLAUDE.md: 109行 → 43行に軽量化
  - サブディレクトリ README: src/, ui/, scripts/, doc/ の4箇所

---

## DA批判レビュー記録

### Phase N DA批判レビュー

**DA観点:** （各Phase完了時に記入）

| # | 発見した問題/改善点 | 重要度 | 再現手順（高/中は必須） | DA観点 | 対応 |
|---|-------------------|--------|----------------------|--------|------|
| | | | | | |
