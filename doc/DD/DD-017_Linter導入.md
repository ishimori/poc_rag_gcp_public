# DD-017: Linter導入（Ruff + pre-commit hook）

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 完了 |

## 目的

Python側にRuff Linterを導入し、pre-commitフックで自動実行されるようにする。既存のESLint（TypeScript）もフックに組み込み、コミット時に両言語の構文チェックが走る体制を構築する。

## 背景・課題

- TypeScript側はESLint導入済みだが、Python側にLinterがない
- LLMによるコード生成だけでなく、機械的な構文チェック・未使用変数検出が必要
- 手動でlintを実行するのは忘れがちなので、pre-commitフックで自動化したい

## 決定事項

- Python Linter: **Ruff**（高速・設定が簡潔・pyproject.toml統合）
- フック管理: **pre-commit** フレームワーク
- ESLintもpre-commitフックに組み込む

## タスク一覧

### Phase 0: 事前精査
- [x] 📋 各Phaseのタスク精査・詳細化
- [x] 😈 Devil's Advocate調査
  - リスク: Ruff のルール有効化で既存コードに大量の警告が出る可能性 → `--fix` で自動修正 + 必要に応じてignore
  - 代替: flake8+isort → Ruffの方が高速・設定統合で優位

### Phase 1: Ruff設定
- [x] `pyproject.toml` に `[tool.ruff]` セクション追加（E/W/F/I/UP/Bルール、line-length=120）
- [x] 🔬 **機械検証**: `ruff check src/ main.py` → All checks passed!

### Phase 2: pre-commit設定
- [x] `.pre-commit-config.yaml` 作成（ruff + ruff-format + eslint）
- [x] `pre-commit install` でフック有効化
- [x] 🔬 **機械検証**: `pre-commit run --all-files` → 全フックPassed

### Phase 3: 既存コード修正
- [x] `ruff check --fix` で自動修正（Python 13件: 未使用import, import順序, f-string, open mode等）
- [x] `ruff format` でフォーマット適用（6ファイル）
- [x] ESLint修正: Dashboard.tsx（useEffect内setState）、Logs.tsx（依存配列不足）
- [x] 🔬 **機械検証**: `pre-commit run --all-files` → ruff Passed, ruff-format Passed, eslint Passed

## ログ

### 2026-03-21
- DD作成
- 全Phase完了。Ruff + pre-commit + ESLintフック導入完了
