# DD-Know-How プロジェクト設定

- プロジェクト概要・セットアップ → [README.md](README.md)
- ローカル操作ガイド → [doc/guide/local-operations.md](doc/guide/local-operations.md)
- 全ドキュメント一覧 → [DOCUMENT-MAP.md](DOCUMENT-MAP.md)

## DD設定

- **フロー**: full（9ステップ）→ 詳細は `doc/development-flow-full.md`
- **DDフォルダ**: `doc/DD/`
- **DD索引**: `doc/DD/INDEX.md` — DD作成・ステータス変更・アーカイブ時に必ず更新すること
- **アーカイブ**: `doc/DD/archived/`
- **テンプレート**: `doc/templates/dd_template.md`

## 利用可能なスキル

> スキルは `.claude/skills/` に配置されています（skills形式）

- `/dd new タイトル` - 新規DD作成
- `/dd status` - 進捗確認
- `/dd list` - DD一覧
- `/dd log メモ` - ログ追記
- `/dd archive 番号` - アーカイブ
- DA メソッド: `doc/da-method.md`
- `/setup パス` - 外部プロジェクトへDD導入

## コーディング規約

- Python: 型ヒント使用、`from __future__ import annotations`
- TypeScript: strict モード、React 関数コンポーネント
- 環境変数は `src/config.py` で一元管理（`Config` クラス）

## ドキュメント更新ルール

コード変更時は対応ドキュメントを同期すること。
対象ファイルと同期タイミングは [DOCUMENT-MAP.md](DOCUMENT-MAP.md) を参照。
