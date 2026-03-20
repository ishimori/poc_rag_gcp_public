# テストデータセット

RAGパイプラインの評価用テストデータ。

## 構成

```
test-data/
├── sources/           # 層1: ソースドキュメント（検索対象）
│   ├── parts_catalog.md         # 部品マスタ表
│   ├── parts_spec_999999.md     # ネジ999999仕様書
│   ├── parts_spec_999998.md     # ネジ999998仕様書
│   ├── vpn_manual.md            # VPN接続手順書（10手順）
│   ├── pc_troubleshoot.md       # PCトラブルFAQ（10問）
│   ├── network_policy.md        # ネットワーク利用規定
│   ├── it_helpdesk_faq.md       # ITヘルプデスクFAQ（50問）
│   ├── leave_policy.md          # 有給休暇規定（全社公開）
│   ├── salary_policy.md         # 給与規定（管理職以上限定）
│   ├── org_chart.md             # 組織図
│   ├── product_update_2026q1.md # プロダクトアップデート
│   └── meeting_minutes_exec.md  # 役員会議事録（役員限定）
├── golden/
│   └── eval_dataset.jsonl       # 層2: Q&Aペア（45件）
└── README.md
```

## Q&Aペアのフォーマット

```json
{
  "id": "exact-001",
  "type": "exact_match",
  "query": "ネジ999999の材質は？",
  "expected_answer": "SUS304",
  "expected_keywords": ["SUS304"],
  "expected_source": "parts_spec_999999.md",
  "category": "parts_catalog",
  "difficulty": "easy",
  "notes": "型番完全一致テスト"
}
```

## 質問タイプ

| type | 件数 | 評価観点 | 正解判定 |
|------|------|---------|---------|
| `exact_match` | 5 | 型番・数値の正確な抽出 | `expected_keywords` が全て含まれること |
| `similar_number` | 3 | 近い番号の区別 | `expected_keywords` + 誤った番号が含まれないこと |
| `semantic` | 10 | 曖昧な質問への対応 | `expected_keywords` が1つ以上含まれること |
| `step_sequence` | 5 | 手順の連続性 | `expected_keywords` + 手順の順序が正しいこと |
| `multi_chunk` | 5 | 複数チャンクの統合 | `expected_keywords` の80%以上が含まれること |
| `unanswerable` | 5 | ハルシネーション抑制 | 「わからない」旨の回答であること |
| `ambiguous` | 3 | 逆質問の適切さ | 質問返しをしていること（LLM判定） |
| `cross_category` | 3 | カテゴリ横断の対応 | `expected_keywords` が含まれること |
| `security` | 3 | 権限チェック | アクセス拒否の旨の回答であること |
| `noise_resistance` | 3 | 似た文書からの正しい選択 | `expected_source` の内容が優先されていること |

## 権限テスト用の設定

| ドキュメント | security_level | allowed_groups |
|-------------|---------------|----------------|
| leave_policy.md | general | ["all"] |
| salary_policy.md | admin_only | ["hr_admin", "exec_board"] |
| meeting_minutes_exec.md | exec_only | ["exec_board"] |
| その他 | general | ["all"] |
