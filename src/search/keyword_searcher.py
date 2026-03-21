from __future__ import annotations

import re
from dataclasses import replace

from google.cloud import firestore

from src.config import config
from src.search.retriever import SearchResult

_db: firestore.Client | None = None
_chunk_cache: list[SearchResult] | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=config.project_id or None)
    return _db


def _fetch_all_chunks() -> list[SearchResult]:
    """Firestoreから全チャンクを取得しキャッシュする"""
    global _chunk_cache
    if _chunk_cache is not None:
        return _chunk_cache

    db = _get_db()
    collection = db.collection(config.collection_name)

    chunks: list[SearchResult] = []
    for doc in collection.stream():
        data = doc.to_dict()
        chunks.append(
            SearchResult(
                content=data["content"],
                score=0.0,
                source_file=data["source_file"],
                chunk_index=data["chunk_index"],
                category=data.get("category", "general"),
                security_level=data.get("security_level", "public"),
            )
        )

    _chunk_cache = chunks
    print(f"  [KeywordSearch] cached {len(chunks)} chunks from Firestore")
    return _chunk_cache


def invalidate_chunk_cache() -> None:
    """キャッシュを破棄する（Ingest後に呼び出す）"""
    global _chunk_cache
    _chunk_cache = None


def _extract_identifiers(query: str) -> list[str]:
    """クエリから型番・品番・英数コードを抽出する"""
    # 4桁以上の数字列（999999, 1000001 等）
    numbers = re.findall(r"\d{4,}", query)
    # 英字+数字のコード（SUS304, M8, M10 等）
    codes = re.findall(r"[A-Z][A-Za-z]*\d+", query)
    return numbers + codes


def _score_chunk(identifiers: list[str], content: str) -> float:
    """識別子のマッチ度合いでチャンクをスコアリングする"""
    score = 0.0
    for identifier in identifiers:
        if identifier in content:
            score += 2.0
    return score


def keyword_search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """識別子ベースのキーワード検索"""
    identifiers = _extract_identifiers(query)
    if not identifiers:
        return []

    k = top_k or config.top_k
    all_chunks = _fetch_all_chunks()

    scored: list[tuple[float, int, SearchResult]] = []
    for i, chunk in enumerate(all_chunks):
        s = _score_chunk(identifiers, chunk.content)
        if s > 0:
            scored.append((s, i, replace(chunk, score=s)))

    # スコア降順でソート
    scored.sort(key=lambda x: -x[0])

    results = [item[2] for item in scored[:k]]
    print(f"  [KeywordSearch] {len(identifiers)} identifiers {identifiers}, {len(results)} hits")
    return results
