# DD-019-8: テストケースデータ

## 成功ケース（8件 — 対策後）

| ID | クエリ | 期待ソース | 備考 |
|---|---|---|---|
| semantic-001 | PCが重い | pc_troubleshoot.md | 対策後に改善 |
| semantic-003 | 画面が固まった | pc_troubleshoot.md | 対策後に改善 |
| semantic-004 | テレワークで使えるネット回線の速度は？ | it_helpdesk_faq.md | 対策後に改善 |
| semantic-005 | Zoomは使える？ | it_helpdesk_faq.md | 対策前から成功 |
| semantic-006 | パスワードの条件は？ | it_helpdesk_faq.md | 対策後に改善 |
| semantic-007 | USBメモリを使いたい | it_helpdesk_faq.md | 対策前から成功 |
| semantic-008 | ウイルスに感染したかもしれない | it_helpdesk_faq.md | 対策後に改善 |
| semantic-009 | フィッシングメールが来た | it_helpdesk_faq.md | 対策後に改善 |

## 失敗ケース一覧（4件 — 対策後も未解決）

| ID | クエリ | 期待ソース | 回答 |
|---|---|---|---|
| semantic-002 | メールが送れない | it_helpdesk_faq.md | 情報なし |
| semantic-010 | 新しいソフトを入れたい | it_helpdesk_faq.md | 情報なし |
| semantic-011 | タクシー代を会社に請求したい | expense_manual.md | 情報なし |
| semantic-012 | 社外秘の書類を捨てたい | security_policy.md | 情報なし |

## 代表3件（詳細分析対象 — 対策前の選定）

- **semantic-001**「PCが重い」— 最も曖昧な口語クエリ（期待: pc_troubleshoot.md）→ **対策後に成功**
- **semantic-006**「パスワードの条件は？」— 比較的明確なクエリ（期待: it_helpdesk_faq.md）→ **対策後に成功**
- **semantic-011**「タクシー代を会社に請求したい」— カテゴリ違い（期待: expense_manual.md）→ 未解決

## 初期仮説

1. **検索段階の問題（最有力）**: ベクトル検索で関連文書が top_k=10 に入らない。短い口語クエリ（「PCが重い」）と文書内容（「メモリ使用率を確認し...」）の意味的距離が大きい
2. **チャンキングの問題**: 関連情報がチャンク境界で分断され、検索時に必要な文脈が失われている
3. **リランキングの問題**: ベクトル検索では引けているがリランキングで除外されている
