# DD-020: venv構成の一本化（.venv→venv）

| 作成日 | 更新日 | ステータス |
|--------|--------|------------|
| 2026-03-21 | 2026-03-21 | 完了 |

## 目的

Python仮想環境のディレクトリ構成を `.venv`（本体）+ `venv`（ジャンクション）から `venv` 一本に統一し、事故リスクを削減する。

## 背景・課題

### 現状の構成

```
.venv/          ← 本体（実ディレクトリ）
venv → .venv    ← ジャンクション（Windowsシンボリックリンク）
```

- `.venv`: `uv` 等のツールがデフォルトで作成する名前
- `venv`: Firebase CLIがコード解析時に `venv/Scripts/activate.bat` を探すため必要

### 過去の問題（DD未起票だが `1b094e8` で対応済み）

- `venv` ジャンクションがデプロイパッケージに含まれ、172MBがCloud Buildに送信されていた
- `firebase.json` に `"venv"`, `"venv/**"` をignoreに追加して解決（172MB→30KB、ビルド時間 2分49秒→35秒）

### 今回の事故

- DD-019-3-3の実装中、ジャンクションが消失していた（原因不明）
- Firebase CLIがデプロイ時に `venv/Scripts/activate.bat` を見つけられずエラー
- Claudeが `python -m venv venv` で実体venvを再作成 → 過去の最適化を無にする行為
- ジャンクション構成を知らないと正しく復旧できない = **事故が起きやすい構成**

## 検討内容

### `.venv` → `venv` 一本化

| 観点 | 現状（`.venv` + ジャンクション） | 提案（`venv` 一本） |
|---|---|---|
| 事故リスク | ジャンクション消失で事故 | 単純なので事故しにくい |
| Firebase CLI | ジャンクション経由で参照 | 直接参照 |
| デプロイ | `firebase.json` ignore で除外 ✓ | 同じ ✓ |
| git | `.gitignore` で除外済み ✓ | 同じ ✓ |
| `uv` 等のツール | デフォルトで `.venv` を作る | `uv venv venv` と指定が必要 |

### 懸念事項

- `uv` のデフォルトが `.venv` なので、`uv sync` 時に注意が必要
  - → `UV_PROJECT_ENVIRONMENT=venv` 環境変数 or `.python-version` の隣に設定で対応可能

## 決定事項

- **`venv` 一本化を採用**: `.venv` + ジャンクション構成を廃止
- `.gitignore` に `venv/` 登録済み → git管理外
- `firebase.json` に `"venv"`, `"venv/**"` 登録済み → デプロイパッケージから除外

## タスク一覧

### Phase 1: 実装 ✅
- [x] 既存のジャンクション `venv → .venv` を削除
- [x] `.venv`（実体）を削除
- [x] `python -m venv venv` で `venv` を実体ディレクトリとして作成
- [x] `pip install -r requirements.txt` で依存関係インストール
- [x] `.gitignore` に `venv/` が含まれていることを確認 ✓
- [x] `firebase.json` の ignore に `venv`, `venv/**` が含まれていることを確認 ✓
- [x] 🔬 **機械検証**: `bash scripts/deploy.sh functions --skip-build` → デプロイ成功、パッケージサイズ **34.51 KB**

## ログ

### 2026-03-21
- DD作成
- 背景: DD-019-3-3の実装中にジャンクション消失 → venv実体を誤作成する事故が発生
- 方針: `.venv`（本体）+ `venv`（ジャンクション）→ `venv` 一本化で構成を単純化
- 実装完了: `.venv` 削除、`venv` 実体作成、デプロイ検証OK（34.51 KB）

---

## DA批判レビュー記録
