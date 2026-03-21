from __future__ import annotations

from dataclasses import replace

from src.config import config
from src.search.keyword_searcher import keyword_search
from src.search.retriever import SearchResult, vector_search


def _rrf_score(rank: int, k: int) -> float:
    """RRFスコアを計算する（rank は 1-indexed）"""
    return 1.0 / (k + rank)


def _merge_by_rrf(
    vector_results: list[SearchResult],
    keyword_results: list[SearchResult],
    k: int,
) -> list[SearchResult]:
    """ベクトル検索とキーワード検索の結果をRRFで統合する"""

    # チャンクを一意に識別するキー（source_file + chunk_index）
    def chunk_key(r: SearchResult) -> str:
        return f"{r.source_file}:{r.chunk_index}"

    # 各チャンクのRRFスコアを計算
    rrf_scores: dict[str, float] = {}
    chunk_map: dict[str, SearchResult] = {}

    for rank, result in enumerate(vector_results, start=1):
        key = chunk_key(result)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + _rrf_score(rank, k)
        chunk_map[key] = result

    for rank, result in enumerate(keyword_results, start=1):
        key = chunk_key(result)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + _rrf_score(rank, k)
        if key not in chunk_map:
            chunk_map[key] = result

    # RRFスコア降順でソート
    sorted_keys = sorted(rrf_scores, key=lambda k_: -rrf_scores[k_])

    return [replace(chunk_map[key], score=rrf_scores[key]) for key in sorted_keys]


def hybrid_search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """ベクトル検索 + キーワード検索 → RRF統合"""
    k = top_k or config.top_k

    # 両方の検索を実行
    vector_results = vector_search(query, top_k=k)
    keyword_results = keyword_search(query, top_k=k)

    # RRF統合
    merged = _merge_by_rrf(vector_results, keyword_results, config.rrf_k)

    results = merged[:k]
    print(f"  [HybridSearch] vector={len(vector_results)}, keyword={len(keyword_results)}, merged={len(results)}")
    return results
