from __future__ import annotations

from dataclasses import dataclass

from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from src.config import config
from src.ingest.embedder import embed_text

_db: firestore.Client | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=config.project_id or None)
    return _db


@dataclass
class SearchResult:
    content: str
    score: float
    source_file: str
    chunk_index: int
    category: str
    security_level: str


def vector_search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """Firestoreのベクトル検索でチャンクを取得する"""
    db = _get_db()
    collection = db.collection(config.collection_name)
    k = top_k or config.top_k

    # クエリをベクトル化
    query_embedding = embed_text(query)

    # Firestoreベクトル検索
    vector_query = collection.find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=k,
        distance_result_field="distance",
    )

    docs = vector_query.get()

    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append(
            SearchResult(
                content=data["content"],
                score=data.get("distance", 0),
                source_file=data["source_file"],
                chunk_index=data["chunk_index"],
                category=data.get("category", "general"),
                security_level=data.get("security_level", "public"),
            )
        )

    return results
