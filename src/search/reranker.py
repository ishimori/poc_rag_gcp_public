from __future__ import annotations

from google.cloud import discoveryengine_v1 as discoveryengine

from src.config import config
from src.search.retriever import SearchResult


def rerank(
    query: str,
    results: list[SearchResult],
    top_n: int | None = None,
    threshold: float | None = None,
) -> list[SearchResult]:
    """Vertex AI Ranking API でリランキングする"""
    n = top_n or config.rerank_top_n
    thresh = threshold if threshold is not None else config.rerank_threshold

    client = discoveryengine.RankServiceClient()

    project_id = config.project_id
    if not project_id:
        import google.auth

        _, project_id = google.auth.default()

    ranking_config = client.ranking_config_path(
        project=project_id,
        location="global",
        ranking_config="default_ranking_config",
    )

    records = [discoveryengine.RankingRecord(id=str(i), content=r.content) for i, r in enumerate(results)]

    request = discoveryengine.RankRequest(
        ranking_config=ranking_config,
        query=query,
        records=records,
        top_n=n,
    )

    try:
        response = client.rank(request=request)
    except Exception as e:
        print(f"  Ranking API error: {e}")
        print("  Falling back to original order.")
        return results[:n]

    reranked = []
    for record in response.records:
        print(f"    [Rerank] id={record.id} score={record.score:.4f}")
        if record.score >= thresh:
            original = results[int(record.id)]
            reranked.append(
                SearchResult(
                    content=original.content,
                    score=record.score,
                    source_file=original.source_file,
                    chunk_index=original.chunk_index,
                    category=original.category,
                    security_level=original.security_level,
                )
            )

    return reranked
