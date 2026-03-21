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


# 一般語マッチで除外するストップワード
_STOP_WORDS = frozenset(
    "の は が を に で と も か な い う た て へ から まで より ない です ます って たい"
    " する した して ある いる どう 方法 場合 教え 知り やり 方 ため とき 時".split()
)


def _split_kanji_compound(token: str) -> list[str]:
    """4文字以上の漢字のみトークンを2文字ずつに分割する。

    例: '繰越上限' → ['繰越', '上限']
        '情報' → [] (4文字未満)
        'セキュリティ' → [] (漢字のみではない)
    """
    if len(token) < 4:
        return []
    # 漢字のみで構成されているか判定
    if not all("\u4e00" <= c <= "\u9fff" for c in token):
        return []
    return [token[i : i + 2] for i in range(0, len(token) - 1, 2)]


def _extract_keywords(query: str) -> list[str]:
    """クエリから一般語キーワードを抽出する（2文字以上、ストップワード除外）"""
    # ひらがな連続・句読点・記号で分割して、2文字以上のトークンを抽出
    tokens = re.findall(r"[\u4e00-\u9fff\u30a0-\u30ffA-Za-z]+", query)
    result: list[str] = []
    for t in tokens:
        if len(t) < 2 or t in _STOP_WORDS:
            continue
        result.append(t)
        # 漢語複合語を2文字ずつに分割して追加（元トークンも保持）
        for sub in _split_kanji_compound(t):
            if sub not in result and sub not in _STOP_WORDS:
                result.append(sub)
    return result


def _score_chunk(identifiers: list[str], keywords: list[str], content: str) -> float:
    """識別子マッチ + 一般語マッチでチャンクをスコアリングする"""
    score = 0.0
    # 識別子マッチ（高配点）
    for identifier in identifiers:
        if identifier in content:
            score += 2.0
    # 一般語マッチ（低配点 — RRFブースト用）
    for kw in keywords:
        if kw in content:
            score += 1.0
    return score


def keyword_search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """識別子 + 一般語キーワード検索"""
    identifiers = _extract_identifiers(query)
    keywords = _extract_keywords(query)
    if not identifiers and not keywords:
        return []

    k = top_k or config.top_k
    all_chunks = _fetch_all_chunks()

    scored: list[tuple[float, int, SearchResult]] = []
    for i, chunk in enumerate(all_chunks):
        s = _score_chunk(identifiers, keywords, chunk.content)
        if s > 0:
            scored.append((s, i, replace(chunk, score=s)))

    # スコア降順でソート
    scored.sort(key=lambda x: -x[0])

    results = [item[2] for item in scored[:k]]
    print(f"  [KeywordSearch] identifiers={identifiers}, keywords={keywords}, {len(results)} hits")
    return results
