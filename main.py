"""Cloud Functions for Firebase — RAG API エントリポイント"""

import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加（src/ のインポート用）
sys.path.insert(0, Path(__file__).parent.as_posix())

from dataclasses import asdict

from firebase_functions import https_fn, options

from src.search.flow import rag_flow


@https_fn.on_request(
    region="asia-northeast1",
    memory=options.MemoryOption.GB_1,
    timeout_sec=120,
    min_instances=0,
    cors=options.CorsOptions(
        cors_origins=["http://localhost:5180"],
        cors_methods=["GET", "POST"],
    ),
)
def chat(req: https_fn.Request) -> https_fn.Response:
    """RAG チャット API"""
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)

    body = req.get_json(force=True, silent=True)
    if not body or "query" not in body:
        return https_fn.Response('{"error": "query is required"}', status=400,
                                 content_type="application/json")

    query = body["query"]
    model = body.get("model")
    result = rag_flow(query, model_name=model)

    response_data = {
        "answer": result.answer,
        "query": result.query,
        "sources": [
            {
                "content": s.content,
                "score": s.score,
                "source_file": s.source_file,
                "chunk_index": s.chunk_index,
                "category": s.category,
                "security_level": s.security_level,
            }
            for s in result.reranked_sources
        ],
    }

    return https_fn.Response(
        response=__import__("json").dumps(response_data, ensure_ascii=False),
        status=200,
        content_type="application/json",
    )
