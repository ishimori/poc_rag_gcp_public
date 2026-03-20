# ADR-003: Embeddingモデル

- **ステータス**: 採用
- **日付**: 2026-03-20

## 選択肢

| # | 選択肢 | 気軽さ | コスト | 数値評価 |
|---|--------|--------|--------|---------|
| 1 | text-multilingual-embedding-002 | ◎ | $0.000025/1K chars | ○ |
| 2 | **gemini-embedding-001** | **◎ 同じAPI** | **$0.000025/1K chars** | **◎ 100+言語対応、最新モデル** |
| 3 | gemini-embedding-2-preview | ○ プレビュー版 | 未確定 | ◎ マルチモーダル対応 |

## 決定

**gemini-embedding-001** を採用。

## 理由

- Google推奨の最新安定版で、100以上の言語に対応
- 料金は text-multilingual-embedding-002 と同等で、性能が上
- `task_type` パラメータ（RETRIEVAL_QUERY / RETRIEVAL_DOCUMENT）を使い分けることで検索精度を最適化でき、その効果を Recall / Precision で測定可能

## 影響

- gemini-embedding-2-preview（マルチモーダル）は画像検索が必要になった段階で再検討
