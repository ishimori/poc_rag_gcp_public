"""Vertex AI Search (Discovery Engine) を使った検索モジュール"""

from __future__ import annotations

from google.cloud import discoveryengine_v1beta as discoveryengine

from src.config import config
from src.search.retriever import SearchResult

_client: discoveryengine.SearchServiceClient | None = None

# ソースファイル名 → メタデータのマッピング（Firestoreのメタデータと同等）
_SOURCE_METADATA: dict[str, dict[str, str]] = {
    "it_helpdesk_faq.md": {"category": "it_support", "security_level": "public"},
    "pc_troubleshoot.md": {"category": "it_support", "security_level": "public"},
    "vpn_manual.md": {"category": "it_support", "security_level": "public"},
    "network_policy.md": {"category": "it_support", "security_level": "public"},
    "parts_spec_999999.md": {"category": "parts_catalog", "security_level": "public"},
    "parts_spec_999998.md": {"category": "parts_catalog", "security_level": "public"},
    "parts_spec_999997.md": {"category": "parts_catalog", "security_level": "public"},
    "parts_spec_1000001.md": {"category": "parts_catalog", "security_level": "public"},
    "parts_catalog.md": {"category": "parts_catalog", "security_level": "public"},
    "quality_standards.md": {"category": "quality", "security_level": "public"},
    "expense_manual.md": {"category": "hr_finance", "security_level": "public"},
    "leave_policy.md": {"category": "hr_finance", "security_level": "public"},
    "leave_policy_2024.md": {"category": "hr_finance", "security_level": "public"},
    "onboarding_guide.md": {"category": "hr_finance", "security_level": "public"},
    "org_chart.md": {"category": "hr_finance", "security_level": "public"},
    "salary_policy.md": {"category": "hr_finance", "security_level": "confidential"},
    "security_policy.md": {"category": "it_support", "security_level": "public"},
    "meeting_minutes_exec.md": {"category": "management", "security_level": "confidential"},
    "product_update_2026q1.md": {"category": "product", "security_level": "public"},
}


def _get_client() -> discoveryengine.SearchServiceClient:
    global _client
    if _client is None:
        _client = discoveryengine.SearchServiceClient(client_options={"api_endpoint": "discoveryengine.googleapis.com"})
    return _client


def _extract_source_file(doc_data: dict) -> str:
    """Vertex AI Search のレスポンスからソースファイル名を抽出する"""
    link = str(doc_data.get("link", ""))
    # GCS URI: gs://bucket/txt/filename.txt or gs://bucket/txt/wikipedia/filename.txt
    if "/" in link:
        filename = link.split("/")[-1]
        # .txt → .md に変換（元のファイル名に合わせる）
        if filename.endswith(".txt"):
            filename = filename[:-4] + ".md"
        return filename
    title = str(doc_data.get("title", ""))
    if title:
        # title にも .txt → .md 変換
        if title.endswith(".txt"):
            title = title[:-4] + ".md"
        elif not title.endswith(".md"):
            title = title + ".md"
        return title
    return "unknown"


def _get_metadata(source_file: str) -> dict[str, str]:
    """ソースファイル名からメタデータを取得する"""
    return _SOURCE_METADATA.get(source_file, {"category": "general", "security_level": "public"})


def _extract_content(doc_data: dict) -> str:
    """Vertex AI Search のレスポンスからコンテンツを抽出する"""
    # extractive_answers を優先
    answers = doc_data.get("extractive_answers", [])
    if answers:
        parts = []
        for a in answers:
            content = a.get("content", "")
            if content:
                parts.append(content)
        if parts:
            return "\n\n".join(parts)

    # extractive_segments にフォールバック（自前RAGのチャンクサイズに合わせて制限）
    segments = doc_data.get("extractive_segments", [])
    if segments:
        # relevanceScore が高い順にソートし、最も関連性の高いセグメントを使用
        scored = sorted(segments, key=lambda s: s.get("relevanceScore", 0), reverse=True)
        content = scored[0].get("content", "")
        if content:
            return content[:1200]

    # snippets にフォールバック
    snippets = doc_data.get("snippets", [])
    if snippets:
        parts = []
        for s in snippets:
            text = s.get("snippet", "")
            if text:
                parts.append(text)
        if parts:
            return "\n\n".join(parts)

    return ""


def vertex_ai_search(
    query: str,
    top_k: int | None = None,
    user_groups: list[str] | None = None,
) -> list[SearchResult]:
    """Vertex AI Search で検索し、SearchResult のリストを返す"""
    client = _get_client()
    k = top_k or config.top_k

    # Engine ベースの serving_config を優先（engine_id があれば）
    if config.vertex_search_engine_id:
        serving_config = (
            f"projects/{config.project_id}/locations/global"
            f"/collections/default_collection"
            f"/engines/{config.vertex_search_engine_id}"
            f"/servingConfigs/default_search"
        )
    else:
        serving_config = (
            f"projects/{config.project_id}/locations/global"
            f"/collections/default_collection"
            f"/dataStores/{config.vertex_search_data_store_id}"
            f"/servingConfigs/default_search"
        )

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_segment_count=5,
            num_previous_segments=1,
            num_next_segments=1,
            return_extractive_segment_score=True,
        ),
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True,
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=k,
        content_search_spec=content_search_spec,
    )

    response = client.search(request=request)

    results: list[SearchResult] = []
    for i, result in enumerate(response.results):
        doc_data = dict(result.document.derived_struct_data)
        source_file = _extract_source_file(doc_data)
        metadata = _get_metadata(source_file)
        content = _extract_content(doc_data)

        if not content:
            print(f"  [VertexAISearch] WARNING: empty content for {source_file}")
            continue

        results.append(
            SearchResult(
                content=content,
                score=1.0 / (i + 1),  # 順位ベースのスコア（1/rank）
                source_file=source_file,
                chunk_index=i,
                category=metadata["category"],
                security_level=metadata["security_level"],
            )
        )

    print(f"  [VertexAISearch] {len(results)} results for query: {query[:50]}...")
    return results
