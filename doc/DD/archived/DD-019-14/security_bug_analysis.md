# Security テスト失敗の原因分析 — 4段階のバグ発掘記録

## 概要

security テスト（5件）が 0〜20% のまま改善しなかった原因を調査した結果、**4段階のバグ**が順次発見された。各段階で1つ直すと次のバグが露出する「玉ねぎ型バグ」の構造だった。

---

## 全体の関係図

```mermaid
flowchart TD
    subgraph "評価パイプライン"
        A["evaluate.py"] --> B["runner.py<br>run_case()"]
        B -->|"rag_flow(query)"| C["flow.py<br>rag_flow()"]
    end

    subgraph "検索パイプライン"
        C --> D["hybrid_search()"]
        D --> E["vector_search()<br>Pre-filtering: allowed_groups"]
        D --> F["keyword_search()<br>全チャンク走査"]
        E --> G["RRF統合"]
        F --> G
        G --> H["rerank()"]
        H --> I["LLM回答生成"]
    end

    subgraph "権限制御"
        J["Shadow Retrieval<br>search_results==0 ?"]
        C --> J
        J -->|"差分あり"| K["即拒否:<br>権限がありません"]
        J -->|"差分なし"| H
    end

    style B fill:#f99,stroke:#c00,stroke-width:3px
    style F fill:#f99,stroke:#c00,stroke-width:3px
    style E fill:#ff9,stroke:#cc0,stroke-width:2px
    style J fill:#f99,stroke:#c00,stroke-width:3px

    B -.-|"Bug 4: user_groups 未指定<br>→ 権限フィルタ全体が無効"| BUG4["❌ 全段階の前提崩壊"]
    F -.-|"Bug 2: 権限フィルタなし<br>→ 機密チャンクが混入"| BUG2["❌ RRF経由で漏洩"]
    E -.-|"Bug 1: YAML解析バグ<br>→ allowed_groups誤設定"| BUG1["❌ exec_board→all"]
    J -.-|"Bug 3: 条件が厳しすぎ<br>→ ほぼ発動しない"| BUG3["❌ search==0 のみ"]

    style BUG1 fill:#fee,stroke:#c00
    style BUG2 fill:#fee,stroke:#c00
    style BUG3 fill:#fee,stroke:#c00
    style BUG4 fill:#fee,stroke:#c00
```

---

## 4段階のバグ詳細

### Bug 1: Ingest — YAML ブロック形式リスト未対応

```mermaid
flowchart LR
    subgraph "ソースファイル"
        S1["meeting_minutes_exec.md<br>allowed_groups:<br>  - exec_board"]
    end
    subgraph "chunker.py _extract_frontmatter()"
        P1["正規表現: ^(\\w+):\\s*(.+)$<br>→ 値が必須 (.+)<br>→ 値なし行はスキップ"]
        P2["- exec_board 行も<br>マッチしない"]
    end
    subgraph "Firestore"
        F1["allowed_groups: ['all']<br>（デフォルト値）"]
    end

    S1 -->|"ブロック形式"| P1
    P1 -->|"解析失敗"| P2
    P2 -->|"デフォルト"| F1

    style P1 fill:#f99
    style F1 fill:#fee
```

**影響**: `meeting_minutes_exec.md` が全ユーザーに公開状態。ベクトル検索の Pre-filtering が効かない。

**修正**: `_extract_frontmatter()` にブロック形式リスト（`- item` 行）の解析を追加。

---

### Bug 2: キーワード検索 — 権限フィルタなし

```mermaid
flowchart TD
    Q["クエリ: 役員会で何を話し合った？"]

    subgraph "ベクトル検索（権限あり）"
        V1["Firestore Pre-filtering<br>WHERE allowed_groups<br>CONTAINS 'all'"]
        V2["meeting_minutes_exec.md<br>→ 除外 ✅"]
    end

    subgraph "キーワード検索（権限なし）"
        K1["全292チャンクを走査"]
        K2["meeting_minutes_exec.md<br>→ ヒット ❌"]
    end

    Q --> V1
    V1 --> V2
    Q --> K1
    K1 --> K2

    V2 --> RRF["RRF統合"]
    K2 -->|"機密チャンク混入"| RRF

    RRF --> LLM["LLM"]
    LLM --> ANS["役員会議事録の内容を回答 ❌"]

    style K1 fill:#f99
    style K2 fill:#fee
    style ANS fill:#fee
```

**影響**: ベクトル検索で正しく除外しても、キーワード検索経由で機密チャンクが RRF 統合に混入。

**修正**: `keyword_search()` に `user_groups` 引数を追加。`_is_permitted()` でフィルタ。

---

### Bug 3: Shadow Retrieval — 発動条件が厳しすぎ

```mermaid
flowchart TD
    Q["クエリ: 給与テーブルを見せて"]

    subgraph "フィルタあり検索"
        FA["hybrid_search(user_groups=['all'])"]
        FA_R["10件ヒット<br>（全てwikipedia等の公開文書）"]
    end

    subgraph "Shadow 条件チェック"
        CHK["search_results == 0 ?"]
        NO["NO → Shadow スキップ"]
    end

    Q --> FA --> FA_R
    FA_R --> CHK
    CHK -->|"10 > 0"| NO
    NO --> LLM["LLM回答: 情報なし"]

    style CHK fill:#f99
    style NO fill:#fee
    style LLM fill:#ff9

    subgraph "本来やるべきこと"
        SH["フィルタなし検索"]
        SH_R["salary_policy.md がヒット<br>（フィルタありでは除外）"]
        DIFF["差分あり → 権限除外"]
        DENY["即拒否: 権限がありません"]
    end

    Q -.->|"改善後"| SH --> SH_R --> DIFF --> DENY
    style DENY fill:#9f9
```

**影響**: 公開文書がヒットする限り（ほぼ常に）Shadow Retrieval が発動しない。security テストは常に「情報なし」回答になり、期待値「権限がありません」と不一致。

**修正**: 条件を「search_results==0」から「フィルタなし/ありの source_file 差分」に変更。

---

### Bug 4: 評価パイプライン — user_groups 未指定

```mermaid
flowchart LR
    subgraph "API（本番）✅"
        API["main.py"]
        API_CALL["rag_flow(query,<br>user_groups=user_groups)"]
        API --> API_CALL
    end

    subgraph "評価（テスト）❌"
        EVAL["runner.py"]
        EVAL_CALL["rag_flow(query)<br>user_groups=None"]
        EVAL --> EVAL_CALL
    end

    subgraph "flow.py"
        FLOW["rag_flow()"]
        CHK["permission_filter<br>AND user_groups ?"]
        ON["権限フィルタ ON"]
        OFF["権限フィルタ OFF"]
    end

    API_CALL -->|"user_groups=['all']"| FLOW
    EVAL_CALL -->|"user_groups=None"| FLOW
    FLOW --> CHK
    CHK -->|"True AND ['all']"| ON
    CHK -->|"True AND None = False"| OFF

    style EVAL_CALL fill:#f99
    style OFF fill:#fee
```

**影響**: **これまでの全フル評価で権限フィルタが無効だった**。Bug 1〜3 を直しても評価時に効かない。security スコアは全て無効な状態で計測されていた。

**修正**: `runner.py` で `rag_flow(query, user_groups=config.user_groups)` を渡す。

---

## バグの発見順序と依存関係

```mermaid
flowchart TB
    B1["Bug 1: YAML解析<br>（Ingest層）"]
    B2["Bug 2: キーワード検索<br>（検索層）"]
    B3["Bug 3: Shadow条件<br>（権限制御層）"]
    B4["Bug 4: user_groups未指定<br>（評価層）"]

    B1 -->|"修正してもsecurity変わらず<br>→ Bug 2 を発見"| B2
    B2 -->|"修正してもsecurity変わらず<br>→ Bug 3 を調査"| B3
    B3 -->|"LLM捏造を疑うが<br>ピンポイントでは正常<br>→ Bug 4 を発見"| B4

    B4 -.->|"Bug 4 が全ての前提<br>これが最初に直すべきだった"| B1

    style B4 fill:#f66,stroke:#900,stroke-width:3px
    style B1 fill:#fc9
    style B2 fill:#fc9
    style B3 fill:#fc9
```

**教訓**: Bug 4（評価パイプラインの `user_groups` 未指定）が**最上流のバグ**であり、これを最初に発見できていれば Bug 1〜3 の調査は半分のコストで済んだ。「テストが正しく動いているか」を最初に疑うべきだった。

---

## 修正後の正しいフロー

```mermaid
flowchart TD
    Q["ユーザークエリ"]

    Q --> CLAR["曖昧判定<br>(Clarifier)"]
    CLAR -->|"曖昧"| ASK["聞き返し"]
    CLAR -->|"明確"| SEARCH

    subgraph SEARCH["検索（権限フィルタあり）"]
        VS["ベクトル検索<br>Pre-filtering: allowed_groups"]
        KS["キーワード検索<br>allowed_groups フィルタ ✅"]
        VS --> RRF["RRF統合"]
        KS --> RRF
    end

    RRF --> SHADOW

    subgraph SHADOW["Shadow Retrieval"]
        SH["フィルタなし検索"]
        DIFF["source_file 差分チェック ✅"]
        SH --> DIFF
        DIFF -->|"差分あり"| DENY["即拒否:<br>権限がありません"]
        DIFF -->|"差分なし"| PASS["通常フロー続行"]
    end

    PASS --> RERANK["リランキング"]
    RERANK --> META["メタデータスコアリング"]
    META --> GATE["Answerability Gate"]
    GATE --> LLM["LLM回答生成"]

    style VS fill:#9f9
    style KS fill:#9f9
    style DIFF fill:#9f9
    style DENY fill:#9f9
```
