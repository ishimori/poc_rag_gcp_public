from __future__ import annotations

from dataclasses import dataclass

import vertexai
from vertexai.generative_models import GenerativeModel

from src.config import config
from src.search.metadata_scorer import apply_metadata_scores
from src.search.reranker import rerank
from src.search.retriever import SearchResult, vector_search

_models: dict[str, GenerativeModel] = {}
_vertexai_initialized = False


def _get_model(model_name: str | None = None) -> GenerativeModel:
    global _vertexai_initialized
    if not _vertexai_initialized:
        vertexai.init(project=config.project_id or None, location=config.location)
        _vertexai_initialized = True

    name = model_name or config.llm_model
    if name not in _models:
        _models[name] = GenerativeModel(
            name,
            generation_config={"temperature": 0.1, "max_output_tokens": 2048},
        )
    return _models[name]


@dataclass
class RAGResponse:
    answer: str
    sources: list[SearchResult]
    reranked_sources: list[SearchResult]
    query: str


def rag_flow(query: str, model_name: str | None = None) -> RAGResponse:
    """RAG Flow: 検索 → リランキング → 回答生成"""
    # Step 1: ベクトル検索
    search_results = vector_search(query)
    print(f"  [Search] {len(search_results)} results")

    # Step 2: リランキング
    reranked_results = rerank(query, search_results)
    print(f"  [Rerank] {len(reranked_results)} results after filtering")

    # Step 2.5: メタデータスコアリング
    if config.metadata_scoring:
        reranked_results = apply_metadata_scores(query, reranked_results)
        print(f"  [MetadataScore] applied to {len(reranked_results)} results")

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
    model = _get_model(model_name)

    prompt = f"""あなたは社内ドキュメントに基づいて質問に回答するアシスタントです。

以下のコンテキストのみを使って質問に回答してください。
コンテキストに情報がない場合は「提供された情報には記載がありません」と回答してください。
推測や外部知識は使わないでください。

## コンテキスト
{context}

## 質問
{query}"""

    try:
        response = model.generate_content(prompt)
        if response.candidates and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text
        print("  LLM returned empty response")
        return "回答を生成できませんでした。"
    except Exception as e:
        print(f"  LLM error: {e}")
        return "回答の生成中にエラーが発生しました。"
