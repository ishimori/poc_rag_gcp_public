from __future__ import annotations

import hashlib

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector

from src.config import config
from src.ingest.chunker import Chunk
from src.search.keyword_searcher import invalidate_chunk_cache

_db: firestore.Client | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=config.project_id or None)
    return _db


def _content_hash(content: str) -> str:
    """コンテンツのハッシュ値を生成（重複チェック用）"""
    return hashlib.sha256(content.encode()).hexdigest()


def store_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> dict[str, int]:
    """チャンクとEmbeddingをFirestoreに保存する"""
    db = _get_db()
    collection = db.collection(config.collection_name)

    stored = 0
    skipped = 0

    # バッチ書き込み（500件ずつ）
    batch_size = 500
    for i in range(0, len(chunks), batch_size):
        batch = db.batch()
        batch_chunks = chunks[i : i + batch_size]
        batch_embeddings = embeddings[i : i + batch_size]

        for chunk, embedding in zip(batch_chunks, batch_embeddings, strict=False):
            content_hash = _content_hash(chunk.content)

            # 重複チェック
            existing = collection.where("content_hash", "==", content_hash).limit(1).get()
            if len(list(existing)) > 0:
                skipped += 1
                continue

            doc_ref = collection.document()
            batch.set(
                doc_ref,
                {
                    "content": chunk.content,
                    "content_hash": content_hash,
                    "embedding": Vector(embedding),
                    "source_file": chunk.source_file,
                    "chunk_index": chunk.chunk_index,
                    "category": chunk.category,
                    "security_level": chunk.security_level,
                    "allowed_groups": chunk.allowed_groups,
                },
            )
            stored += 1

        batch.commit()

    invalidate_chunk_cache()
    return {"stored": stored, "skipped": skipped}


def clear_collection() -> int:
    """コレクション内の全ドキュメントを削除する"""
    db = _get_db()
    collection = db.collection(config.collection_name)
    docs = collection.get()

    deleted = 0
    batch_size = 500

    doc_list = list(docs)
    for i in range(0, len(doc_list), batch_size):
        batch = db.batch()
        for doc in doc_list[i : i + batch_size]:
            batch.delete(doc.reference)
        batch.commit()
        deleted += len(doc_list[i : i + batch_size])

    invalidate_chunk_cache()
    return deleted
