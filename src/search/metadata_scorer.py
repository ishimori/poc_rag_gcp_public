from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from src.config import config

if TYPE_CHECKING:
    from src.search.retriever import SearchResult


def apply_metadata_scores(
    query: str,
    results: list[SearchResult],
) -> list[SearchResult]:
    """リランキング後の検索結果にメタデータボーナスを加算して再ソートする。

    2軸で評価:
    - カテゴリ一致: 検索結果の多数決で推定したカテゴリと一致する文書にボーナス
    - ファイル名一致: クエリ内のキーワードがファイル名に含まれる文書にボーナス
    """
    if not results:
        return results

    query_category = _infer_query_category(results)

    scored = []
    for r in results:
        bonus = 0.0
        bonus += config.metadata_category_bonus * _category_bonus(r.category, query_category)
        bonus += config.metadata_filename_bonus * _filename_bonus(query, r.source_file)
        scored.append(replace(r, score=r.score + bonus))

    # スコア降順で再ソート
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored


def _infer_query_category(results: list[SearchResult]) -> str:
    """検索結果の多数決でクエリのカテゴリを推定する。

    "general" は推定対象から除外する（ノイズ文書のカテゴリであることが多いため）。
    有効なカテゴリがない場合は空文字を返し、カテゴリボーナスは適用されない。
    """
    categories = [r.category for r in results if r.category != "general"]
    if not categories:
        return ""
    counter = Counter(categories)
    return counter.most_common(1)[0][0]


def _category_bonus(result_category: str, query_category: str) -> float:
    """カテゴリ一致ボーナス。一致なら1.0、不一致なら0.0。"""
    if not query_category:
        return 0.0
    return 1.0 if result_category == query_category else 0.0


def _filename_bonus(query: str, source_file: str) -> float:
    """ファイル名一致ボーナス。クエリ内のキーワードがファイル名に含まれるなら1.0。

    ファイル名からパス・拡張子・アンダースコアを除去してキーワード化し、
    クエリに2文字以上のキーワードが含まれるかを判定する。
    """
    # ファイル名からキーワードを抽出: "parts_spec_999999.md" → ["parts", "spec", "999999"]
    basename = source_file.rsplit("/", 1)[-1]  # パス除去
    basename = re.sub(r"\.\w+$", "", basename)  # 拡張子除去
    file_keywords = [k for k in basename.split("_") if len(k) >= 2]

    # クエリにファイル名のキーワードが含まれるか（大文字小文字を無視）
    query_lower = query.lower()
    for keyword in file_keywords:
        if keyword.lower() in query_lower:
            return 1.0
    return 0.0
