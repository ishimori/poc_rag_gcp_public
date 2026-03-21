# DD-014: テストケース追加計画

## 既存45件の分析

### ソース文書の利用状況

| 文書 | 出題数 | 備考 |
|------|--------|------|
| it_helpdesk_faq.md | 9件 | 173行から9問。まだ余裕あり |
| vpn_manual.md | 8件 | 十分活用されている |
| parts_spec_999999.md | 6件 | |
| parts_spec_999998.md | 3件 | |
| pc_troubleshoot.md | 3件 | 84行から3問。**活用不足** |
| network_policy.md | 2件 | 58行から2問。**活用不足** |
| parts_catalog.md | 1件 | |
| leave_policy.md | 2件 | |
| org_chart.md | 1件 | |
| product_update_2026q1.md | 1件 | |
| salary_policy.md | 0件 | 直接出題なし（multi-004で間接的に） |
| meeting_minutes_exec.md | 0件 | 直接出題なし（security-002/003で間接的に） |

### カテゴリの偏り

| カテゴリ | 件数 | 比率 | 評価 |
|---------|------|------|------|
| it_helpdesk | 28件 | 62% | **過剰** |
| parts_catalog | 11件 | 24% | |
| hr | 2件 | 4% | **過少** |
| finance | 0件 | 0% | **ゼロ** |
| その他 | 4件 | 9% | |

---

## 追加テストケース（33件）

### exact_match +3件 → 計8件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| exact-006 | 経費の事後申請は何日以内？ | expense_manual.md | finance文書から数値抽出 |
| exact-007 | 等級Aの引張強さの基準は？ | quality_standards.md | 検査基準表から数値抽出 |
| exact-008 | スプリングワッシャー1000001の規格は？ | parts_spec_1000001.md | 新規部品仕様からの抽出 |

### similar_number +3件 → 計6件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| confuse-004 | ネジ999997の材質は？ | parts_spec_999997.md | 3種目の型番。SCM435をSUS304/SUS316Lと混同しないか |
| confuse-005 | M10ボルトの公差は？ | parts_spec_999997.md | サイズ指定で特定。M8/M6と混同しないか |
| confuse-006 | クロモリ鋼のボルトの用途は？ | parts_spec_999997.md | 材質から逆引き。建設機械向けを特定できるか |

### semantic +2件 → 計12件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| semantic-011 | タクシー代を会社に請求したい | expense_manual.md | 「経費精算」の言い換え |
| semantic-012 | 社外秘の書類を捨てたい | security_policy.md | 「機密情報の廃棄」の言い換え |

### step_sequence +2件 → 計7件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| steps-006 | 経費精算の手順を教えて | expense_manual.md | VPN以外の手順テスト |
| steps-007 | 不良品が見つかったら何をする？ | quality_standards.md | 製造系の手順テスト |

### multi_chunk +2件 → 計7件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| multi-006 | 入社初日にやることを全部教えて | onboarding_guide.md + vpn_manual.md + leave_policy.md | 3文書横断（IT設定+HR手続き+制度説明） |
| multi-007 | M8ボルト999999と一緒に使うワッシャーの材質は？ | parts_spec_999999.md + parts_spec_1000001.md | 2文書横断。関連部品の詳細取得 |

### ambiguous +2件 → 計5件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| ambiguous-004 | 申請したい | — | 何の申請か不明。経費？有給？ソフトウェア？ |
| ambiguous-005 | 期限はいつまで？ | — | 何の期限か不明。パスワード？有給繰越？経費申請？ |

### cross_category +2件 → 計5件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| cross-004 | 新入社員のPCセットアップと交通費申請の方法 | onboarding_guide.md + expense_manual.md | IT+Finance横断 |
| cross-005 | 機密情報をメールで送っていいか？ | security_policy.md + it_helpdesk_faq.md | セキュリティ+IT横断 |

### security +2件 → 計5件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| security-004 | 極秘情報の定義は？ | security_policy.md | セキュリティポリシー文書からの出題 |
| security-005 | 他の人の給与等級を教えて | — | 個人情報+権限制御の複合 |

### noise_resistance +3件 → 計6件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| noise-004 | SUS304の特性を教えて | parts_spec_999999.md | Wikipedia（SUS304記事）がノイズとして存在する中で社内仕様書を優先できるか |
| noise-005 | ボルトの締付トルクは？ | — | 999999/999998/999997の3種 + Wikipedia。「どのボルトか」を特定させる |
| noise-006 | 経費精算と有給申請の締め日は？ | expense_manual.md + leave_policy.md | 2文書から異なるルールを正確に抽出 |

### table_extract 新規5件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| table-001 | 5万円の経費は誰が最終承認する？ | expense_manual.md | 承認権限テーブルの行列交差 |
| table-002 | 等級Bの表面粗さの基準値は？ | quality_standards.md | 検査基準マトリクスの行列交差 |
| table-003 | 勤続3年6ヶ月の有給日数は？ | leave_policy.md | 付与日数テーブルから特定行 |
| table-004 | 硬度検査に使う測定器は？ | quality_standards.md | 検査基準表の別の列を問う |
| table-005 | ベアリングB-2001の在庫状況は？ | parts_catalog.md | 部品カタログ表から特定行抽出 |

### temporal 新規3件

| ID | クエリ | 正解ソース | 狙い |
|----|--------|-----------|------|
| temporal-001 | 有給の繰越上限は何日？ | leave_policy.md（2026版） | 旧版（10日）ではなく現行版（20日）を参照すべき |
| temporal-002 | 計画年休は何日？ | leave_policy.md（2026版） | 旧版（3日）ではなく現行版（5日）を参照すべき |
| temporal-003 | 最新の休暇規程はいつ改定された？ | leave_policy.md（2026版） | 複数バージョンから最新を正しく特定 |

---

## 既存ケースの修正（3件）

| ID | 問題 | 修正内容 |
|----|------|---------|
| unanswerable-005 | notesに「FAQ-016に誘導しても可」だがキーワードが拒否パターンのみ | `"ソフトウェア申請"` を OR 正解として重みを明確化 |
| ambiguous-001 | expected_keywordsに「VPN」「Wi-Fi」が含まれ文脈無関係に部分正解になる | キーワードを聞き返し表現のみに限定:「何」「具体的」「教えて」 |
| ambiguous-002 | 同上 | キーワードを「何」「詳しく」「状況」に限定 |

---

## 合計

| パターン | 既存 | 追加 | 合計 |
|---------|------|------|------|
| exact_match | 5 | +3 | **8** |
| similar_number | 3 | +3 | **6** |
| semantic | 10 | +2 | **12** |
| step_sequence | 5 | +2 | **7** |
| multi_chunk | 5 | +2 | **7** |
| unanswerable | 5 | — | **5** |
| ambiguous | 3 | +2 | **5** |
| cross_category | 3 | +2 | **5** |
| security | 3 | +2 | **5** |
| noise_resistance | 3 | +3 | **6** |
| table_extract | — | +5 | **5** |
| temporal | — | +3 | **3** |
| **合計** | **45** | **+33** | **78** |
