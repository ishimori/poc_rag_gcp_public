from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai.types import GenerateContentConfig

from src.config import config
from src.search.clarifier import detect_ambiguity
from src.search.hybrid import hybrid_search
from src.search.metadata_scorer import apply_metadata_scores
from src.search.reranker import rerank
from src.search.retriever import SearchResult, vector_search

_genai_client: genai.Client | None = None


def _get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=config.project_id or None,
            location=config.llm_location,
        )
    return _genai_client


@dataclass
class RAGResponse:
    answer: str
    sources: list[SearchResult]
    reranked_sources: list[SearchResult]
    query: str
    is_clarification: bool = False


def rag_flow(
    query: str,
    model_name: str | None = None,
    user_groups: list[str] | None = None,
) -> RAGResponse:
    """RAG Flow: 曖昧判定 → 検索 → リランキング → 回答生成"""
    # Step 0: 曖昧判定（Pre-RAG）
    if config.clarification:
        clarification = detect_ambiguity(query)
        if clarification.is_ambiguous:
            print("  [Clarifier] Ambiguous query detected, returning clarification")
            return RAGResponse(
                answer=clarification.clarification_question,
                sources=[],
                reranked_sources=[],
                query=query,
                is_clarification=True,
            )
        print("  [Clarifier] Query is clear, proceeding to search")

    # Step 1: 検索（ハイブリッド or ベクトルのみ）
    if config.hybrid_search:
        search_results = hybrid_search(query, user_groups=user_groups)
        print(f"  [HybridSearch] {len(search_results)} results")
    else:
        search_results = vector_search(query, user_groups=user_groups)
        print(f"  [VectorSearch] {len(search_results)} results")

    # Step 1.5: 権限除外検出（Shadow Retrieval）
    # フィルタなし検索を実行し、フィルタあり検索との差分で権限除外を検出する
    # ※ メイン検索と同じ検索方式で比較する（hybrid同士 or vector同士）
    if config.shadow_retrieval and config.permission_filter and user_groups:
        if config.hybrid_search:
            shadow_results = hybrid_search(query, user_groups=None)
        else:
            shadow_results = vector_search(query, user_groups=None)
        # フィルタなし/ありで source_file の差分を比較
        filtered_sources = {r.source_file for r in search_results}
        shadow_sources = {r.source_file for r in shadow_results}
        permission_filtered = shadow_sources - filtered_sources
        if permission_filtered:
            print(f"  [PermissionCheck] FILTERED_BY_PERMISSION — {permission_filtered}")
            return RAGResponse(
                answer="この情報へのアクセス権限がありません。管理者にお問い合わせください。",
                sources=[],
                reranked_sources=[],
                query=query,
            )

    # Step 2: リランキング
    reranked_results = rerank(query, search_results)
    print(f"  [Rerank] {len(reranked_results)} results after filtering")

    # Step 2.5: メタデータスコアリング
    if config.metadata_scoring:
        reranked_results = apply_metadata_scores(query, reranked_results)
        print(f"  [MetadataScore] applied to {len(reranked_results)} results")

    # Step 2.8: Answerability Gate（スコア閾値チェック）
    if config.answerability_threshold > 0:
        top_score = reranked_results[0].score if reranked_results else 0.0
        if top_score < config.answerability_threshold:
            print(
                f"  [AnswerabilityGate] REJECTED — top_score={top_score:.4f}"
                f" < threshold={config.answerability_threshold}"
            )
            return RAGResponse(
                answer="提供された情報には記載がありません。",
                sources=search_results,
                reranked_sources=reranked_results,
                query=query,
            )

    # Step 3: コンテキスト構築
    context = "\n\n---\n\n".join(r.content for r in reranked_results)

    # Step 4: LLMで回答生成
    answer = _generate_answer(query, context, model_name)

    return RAGResponse(
        answer=answer,
        sources=search_results,
        reranked_sources=reranked_results,
        query=query,
    )


def _generate_answer(query: str, context: str, model_name: str | None = None) -> str:
    """Vertex AI Gemini で回答を生成する"""
    name = model_name or config.llm_model

    prompt = f"""あなたは社内ドキュメントに基づいて質問に回答するアシスタントです。

以下のコンテキストのみを使って質問に回答してください。
コンテキストに情報がない場合は「提供された情報には記載がありません」と回答してください。
推測や外部知識は使わないでください。
同じ文書の複数バージョン（例: 2024年版と2026年版）がある場合は、最新版の情報を優先して回答してください。

## コンテキスト
{context}

## 質問
{query}"""

    try:
        client = _get_genai_client()
        response = client.models.generate_content(
            model=name,
            contents=prompt,
            config=GenerateContentConfig(temperature=0.1, max_output_tokens=8192),
        )
        if response.text:
            return response.text
        print("  LLM returned empty response")
        return "回答を生成できませんでした。"
    except Exception as e:
        print(f"  LLM error: {e}")
        return "回答の生成中にエラーが発生しました。"
