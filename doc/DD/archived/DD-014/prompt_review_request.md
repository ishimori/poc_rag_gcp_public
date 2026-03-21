# RAGシステムのテストデータ改善について意見をください

## あなたへの依頼

社内文書RAGシステム（検索拡張生成）のテストデータを改善しようとしています。
現状の分析と改善計画に対して、以下の観点でレビューしてください。

**聞きたいこと:**
1. 追加すべきソース文書として提案した6候補は妥当か？他に優先すべきものはないか？
2. テストパターン（10種類）の分類自体は妥当か？抜けている観点はないか？
3. テストケース設計で見落としている落とし穴はないか？
4. この規模のPoCとして、テストデータの量はどの程度が適切か？

---

## システム概要

精密部品メーカー（従業員3,000名）の社内文書を対象としたRAGシステムのPoCです。

**技術構成:**
- Embedding: Vertex AI text-embedding-005 (768次元)
- Vector DB: Firestore (ベクトル検索)
- Reranking: Google Discovery Engine Ranking API
- LLM: Gemini 2.5 Flash
- チャンク: 800トークン / 150トークン重複

**パイプライン:**
質問 → Embedding → ベクトル検索(top_k=10) → リランキング(top_n=5, threshold=0.01) → Gemini で回答生成

---

## 現在のソース文書（12ファイル / 計788行 / 30チャンク）

| # | ファイル | 行数 | カテゴリ | 内容 |
|---|---------|------|---------|------|
| 1 | it_helpdesk_faq.md | 173 | it_helpdesk | IT FAQ 50件（アカウント、メール、ハード、ソフト、ネットワーク、セキュリティ、リモートワーク） |
| 2 | pc_troubleshoot.md | 84 | it_helpdesk | PC トラブルシュート Q&A 10件（動作遅い、Outlook、プリンタ、Wi-Fi、フリーズ等） |
| 3 | vpn_manual.md | 77 | it_helpdesk | VPN設定手順 10ステップ（GlobalProtect、認証、トラブルシュート、macOS/モバイル対応） |
| 4 | network_policy.md | 58 | it_helpdesk | ネットワーク利用規定（許可ネットワーク、VPNルール、監視、インシデント報告） |
| 5 | parts_spec_999999.md | 46 | parts_catalog | 部品仕様書: M8×25 SUS304 六角穴付きボルト（JIS B 1176、トルク値、用途、関連部品） |
| 6 | parts_spec_999998.md | 44 | parts_catalog | 部品仕様書: M6×20 SUS316L 六角穴付きボルト（電解研磨、クリーンルーム向け） |
| 7 | parts_catalog.md | 30 | parts_catalog | 部品カタログ: 10部品の一覧表（品番、材質、価格、在庫状況） |
| 8 | leave_policy.md | 60 | hr | 年次有給休暇規程（付与日数テーブル、申請方法、繰越、計画年休） |
| 9 | salary_policy.md | 61 | hr | 給与規程（等級G1-G6、昇給率、賞与、各種手当）※管理職以上限定 |
| 10 | org_chart.md | 53 | organization | 組織図（4事業部、部門別人数、内線番号） |
| 11 | product_update_2026q1.md | 49 | product | 2026Q1 新製品情報（CorrGuard高耐食ネジ、HiDurセラミック軸受） |
| 12 | meeting_minutes_exec.md | 53 | executive | 役員会議事録（Q1業績、設備投資、M&A検討）※役員限定 |

**カテゴリ分布:**
- it_helpdesk: 4ファイル (392行) — 全体の50%
- parts_catalog: 3ファイル (120行) — 全体の15%
- hr: 2ファイル (121行) — 全体の15%
- その他: 3ファイル (155行) — 全体の20%

---

## 現在のテストケース（45件 / 10パターン）

### パターン別の件数と内容

| パターン | 件数 | テスト内容 | 現在のスコア |
|---------|------|-----------|-------------|
| exact_match（完全一致） | 5 | 型番・数値の正確な抽出 | 80% (4/5) |
| similar_number（類似数値） | 3 | 似た型番を混同しないか | 100% (3/3) |
| semantic（意味検索） | 10 | 言い換え・類義語への対応 | 50% (5/10) |
| step_sequence（手順再現） | 5 | 手順を順序通りに返せるか | 100% (5/5) |
| multi_chunk（複数チャンク統合） | 5 | 複数文書を横断して統合 | 100% (5/5) |
| unanswerable（回答不能） | 5 | 「分かりません」と正しく拒否 | 100% (5/5) |
| ambiguous（曖昧質問） | 3 | 曖昧な質問に聞き返しで対応 | 0% (0/3) ※機能未実装 |
| cross_category（カテゴリ横断） | 3 | 異なる分野の文書を横断して回答 | 100% (3/3) |
| security（セキュリティ） | 3 | 権限外の情報をブロック | 0% (0/3) ※機能未実装 |
| noise_resistance（ノイズ耐性） | 3 | 無関係情報の中から正解を抽出 | 67% (2/3) |

### 全テストケースの詳細

```jsonl
{"id":"exact-001","type":"exact_match","query":"ネジ999999の材質は？","expected_answer":"SUS304","expected_keywords":["SUS304"],"category":"parts_catalog","difficulty":"easy","notes":"型番完全一致テスト"}
{"id":"exact-002","type":"exact_match","query":"部品番号999999の公差を教えて","expected_answer":"±0.01mm","expected_keywords":["±0.01mm","0.01"],"category":"parts_catalog","difficulty":"easy"}
{"id":"exact-003","type":"exact_match","query":"ネジ999999の締付トルクは？（潤滑なし）","expected_answer":"18.0 N·m","expected_keywords":["18.0","N·m","Nm"],"category":"parts_catalog","difficulty":"easy"}
{"id":"exact-004","type":"exact_match","query":"ネジ999999の単価はいくら？","expected_answer":"¥42（税抜）","expected_keywords":["42","¥42"],"category":"parts_catalog","difficulty":"easy"}
{"id":"exact-005","type":"exact_match","query":"部品番号999997の在庫状況は？","expected_answer":"残りわずか","expected_keywords":["残りわずか"],"category":"parts_catalog","difficulty":"easy"}
{"id":"confuse-001","type":"similar_number","query":"ネジ999998の材質は？","expected_answer":"SUS316L","expected_keywords":["SUS316L"],"category":"parts_catalog","difficulty":"medium"}
{"id":"confuse-002","type":"similar_number","query":"ネジ999998の公差を教えて","expected_answer":"±0.03mm","expected_keywords":["±0.03mm","0.03"],"category":"parts_catalog","difficulty":"medium"}
{"id":"confuse-003","type":"similar_number","query":"SUS316Lのボルトの部品番号は？","expected_answer":"999998","expected_keywords":["999998"],"category":"parts_catalog","difficulty":"medium"}
{"id":"semantic-001","type":"semantic","query":"PCが重い","expected_keywords":["メモリ","タスクマネージャー","再起動"],"category":"it_helpdesk","difficulty":"easy","notes":"曖昧な表現→具体的な手順への変換"}
{"id":"semantic-002","type":"semantic","query":"メールが送れない","expected_keywords":["25MB","Teams","ファイル"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"semantic-003","type":"semantic","query":"画面が固まった","expected_keywords":["タスクマネージャー","Ctrl+Alt+Delete","強制"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"semantic-004","type":"semantic","query":"テレワークで使えるネット回線の速度は？","expected_keywords":["50Mbps"],"category":"it_helpdesk","difficulty":"medium"}
{"id":"semantic-005","type":"semantic","query":"Zoomは使える？","expected_keywords":["Teams","無料版","取引先"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"semantic-006","type":"semantic","query":"パスワードの条件は？","expected_keywords":["12文字","90日","大文字","記号"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"semantic-007","type":"semantic","query":"USBメモリを使いたい","expected_keywords":["禁止","暗号化","申請"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"semantic-008","type":"semantic","query":"ウイルスに感染したかもしれない","expected_keywords":["スケアウェア","ブラウザ","IT部門","報告"],"category":"it_helpdesk","difficulty":"medium"}
{"id":"semantic-009","type":"semantic","query":"フィッシングメールが来た","expected_keywords":["security@example.com","転送","クリック"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"semantic-010","type":"semantic","query":"新しいソフトを入れたい","expected_keywords":["ソフトウェア申請","禁止","社内ポータル"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"steps-001","type":"step_sequence","query":"VPN接続の手順3の後は何をする？","expected_keywords":["緑色","社内ポータル","確認"],"category":"it_helpdesk","difficulty":"medium"}
{"id":"steps-002","type":"step_sequence","query":"VPNの初回設定でポータルアドレスは何を入れる？","expected_keywords":["vpn.example.com"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"steps-003","type":"step_sequence","query":"macOSでVPN接続するには？","expected_keywords":["App Store","GlobalProtect","vpn.example.com"],"category":"it_helpdesk","difficulty":"medium"}
{"id":"steps-004","type":"step_sequence","query":"VPNが認証エラーになる","expected_keywords":["パスワード","有効期限","ロック","30分","時刻"],"category":"it_helpdesk","difficulty":"easy"}
{"id":"steps-005","type":"step_sequence","query":"VPN接続が不安定で頻繁に切れる","expected_keywords":["有線LAN","MTU","1400","KeepAlive","30秒"],"category":"it_helpdesk","difficulty":"medium"}
{"id":"multi-001","type":"multi_chunk","query":"VPNが繋がらない原因として考えられるものを全て教えて","expected_keywords":["パスワード","アカウントロック","二要素認証","DNS","ファイアウォール"],"category":"it_helpdesk","difficulty":"hard"}
{"id":"multi-002","type":"multi_chunk","query":"ネジ999999と999998の違いは？","expected_keywords":["SUS304","SUS316L","M8","M6","0.01","0.03","食品","クリーンルーム"],"category":"parts_catalog","difficulty":"hard"}
{"id":"multi-003","type":"multi_chunk","query":"ネジ999999を使うときに一緒に必要な部品は？","expected_keywords":["1000001","1000002","スプリングワッシャー","平ワッシャー"],"category":"parts_catalog","difficulty":"medium"}
{"id":"multi-004","type":"multi_chunk","query":"リモートワークに必要な準備を全部教えて","expected_keywords":["VPN","GlobalProtect","50Mbps","のぞき見"],"category":"it_helpdesk","difficulty":"hard"}
{"id":"multi-005","type":"multi_chunk","query":"社内Wi-FiのSSIDは何？ゲスト用との違いは？","expected_keywords":["CORP-WIFI-5G","CORP-WIFI-GUEST","WPA3","社内リソース"],"category":"it_helpdesk","difficulty":"medium"}
{"id":"unanswerable-001","type":"unanswerable","query":"来月の株価はどうなる？","expected_keywords":["見つかりません","情報がありません","わかりません"],"category":"none","difficulty":"easy"}
{"id":"unanswerable-002","type":"unanswerable","query":"競合他社のネジの価格は？","expected_keywords":["見つかりません","情報がありません","わかりません"],"category":"none","difficulty":"easy"}
{"id":"unanswerable-003","type":"unanswerable","query":"社長の携帯番号を教えて","expected_keywords":["見つかりません","情報がありません","わかりません","お答えできません"],"category":"none","difficulty":"easy"}
{"id":"unanswerable-004","type":"unanswerable","query":"2025年のM&A案件はどうなった？","expected_keywords":["見つかりません","情報がありません","わかりません"],"category":"none","difficulty":"medium","notes":"2026年のM&A情報はあるが2025年はない"}
{"id":"unanswerable-005","type":"unanswerable","query":"Pythonのインストール方法は？","expected_keywords":["見つかりません","情報がありません","わかりません","ソフトウェア申請"],"category":"none","difficulty":"medium","notes":"ITっぽいが具体手順なし。FAQ-016に誘導しても可"}
{"id":"ambiguous-001","type":"ambiguous","query":"あれの設定方法を教えて","expected_keywords":["何","具体的","教えて","VPN","Wi-Fi"],"category":"none","difficulty":"medium","notes":"聞き返し機能は未実装"}
{"id":"ambiguous-002","type":"ambiguous","query":"接続できない","expected_keywords":["何","VPN","Wi-Fi","プリンター","詳しく"],"category":"none","difficulty":"medium"}
{"id":"ambiguous-003","type":"ambiguous","query":"エラーが出る","expected_keywords":["どの","エラーメッセージ","スクリーンショット"],"category":"none","difficulty":"medium"}
{"id":"cross-001","type":"cross_category","query":"有給の申請方法とVPNの設定を教えて","expected_keywords":["勤怠管理","3営業日","GlobalProtect","vpn.example.com"],"category":"mixed","difficulty":"hard"}
{"id":"cross-002","type":"cross_category","query":"情報システム部の社員数と部長は誰？","expected_keywords":["40","石井","翔太"],"category":"organization","difficulty":"easy"}
{"id":"cross-003","type":"cross_category","query":"新製品のCorrGuardとは何？","expected_keywords":["高耐食","ナノコーティング","3倍","塩水"],"category":"product","difficulty":"easy"}
{"id":"security-001","type":"security","query":"給与テーブルを見せて","expected_keywords":["閲覧","権限","管理職","アクセス"],"category":"hr_policy","difficulty":"medium","notes":"権限フィルタは未実装"}
{"id":"security-002","type":"security","query":"役員会で何を話し合った？","expected_keywords":["閲覧","権限","役員","アクセス"],"category":"executive","difficulty":"medium"}
{"id":"security-003","type":"security","query":"M&Aの検討状況を教えて","expected_keywords":["権限","アクセス"],"category":"executive","difficulty":"hard"}
{"id":"noise-001","type":"noise_resistance","query":"ネットワークの設定方法は？","expected_keywords":["CORP-WIFI-5G","VPN","GlobalProtect"],"category":"it_helpdesk","difficulty":"medium","notes":"規定文書と手順書の区別"}
{"id":"noise-002","type":"noise_resistance","query":"VPN接続のルールは？","expected_keywords":["業務時間","フルトンネル","50Mbps","切断","セキュリティパッチ"],"category":"it_helpdesk","difficulty":"medium","notes":"手順ではなくルールを返すべき"}
{"id":"noise-003","type":"noise_resistance","query":"有給休暇は何日もらえる？入社3年目です","expected_keywords":["12日","2年6ヶ月"],"category":"hr_policy","difficulty":"medium","notes":"勤続年数テーブルから正しい行を抽出"}
```

### スコアリング方法

```python
# キーワードのサブストリング判定
score = 含まれていたキーワード数 / 全キーワード数
# score >= 0.5 で合格
# unanswerable タイプは拒否パターン文字列の含有で判定
```

---

## 認識している課題

### 1. ソース文書の量が少ない
12ファイル/30チャンクでは検索候補が少なすぎて、ほぼ何でもヒットする。実運用ではノイズの中から正解を見つける必要がある。

### 2. カテゴリが IT に偏っている
IT系が全体の50%を占め、HR/Finance/製造は薄い。

### 3. テストケースが文書の浅い部分しか突いていない
VPNマニュアル77行に対してテストは基本手順確認のみ。注意事項、例外条件、表の特定行を突くケースがない。

### 4. 3件しかないパターンの統計的信頼性
1件の成否で33%変動する。最低5件は必要。

### 5. 未実装機能のテストが混在
ambiguous(聞き返し)とsecurity(権限フィルタ)は機能未実装なのに同列でスコア表示される。

---

## 改善計画

### 追加予定のソース文書（6候補）

| # | 文書 | カテゴリ | 目的 |
|---|------|---------|------|
| 1 | 経費精算マニュアル | finance | Financeカテゴリ充実。承認フロー・限度額・例外規定 |
| 2 | 情報セキュリティポリシー | it_helpdesk | セキュリティテストの土台。情報分類・取扱規定 |
| 3 | 新入社員オンボーディングガイド | hr | HRカテゴリ充実。複数部門横断の手続き一覧 |
| 4 | 追加部品仕様書×2（999997, 1000001） | parts_catalog | 類似部品ノイズ増。similar_numberテスト強化 |
| 5 | 社内システム一覧 | it_helpdesk | 「〇〇システムの使い方」系質問のノイズ源 |
| 6 | 品質管理基準書 | parts_catalog | 製造系文書の充実。検査基準・不良対応フロー |

### テストケースの追加方針
- 全パターン最低5件に
- 新規文書からの出題
- 既存文書の深い部分を突くケース追加
- 45件 → 約63件

---

## 回答してほしいこと

上記の現状と計画を踏まえて、以下について意見をください:

1. **追加文書の候補は妥当か？** — 6候補の優先順位、不要なもの、代わりに追加すべきものはあるか？
2. **テストパターン10種類の分類は適切か？** — 抜けている観点、統合すべきもの、分割すべきものはあるか？
3. **テストケースの設計で見落としている落とし穴は？** — キーワード判定の限界、テストケース自体のバグ、評価方法の盲点など
4. **PoCとしての適切な規模感は？** — 文書数、テストケース数、チャンク数はどの程度が妥当か？
5. **その他、気づいた点があれば自由に**
