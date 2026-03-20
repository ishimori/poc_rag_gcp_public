"""Firestoreコレクションをローカルにエクスポートする"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime

from google.cloud import firestore

from src.config import config

_db: firestore.Client | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=config.project_id or None)
    return _db


def export_collection(cache_dir: str) -> int:
    """Firestoreのchunksコレクションを全件取得しCSVに保存する

    embeddingカラムは除外（サイズが大きすぎる）
    """
    db = _get_db()
    collection = db.collection(config.collection_name)
    docs = collection.get()

    os.makedirs(cache_dir, exist_ok=True)
    csv_path = os.path.join(cache_dir, "chunks.csv")
    meta_path = os.path.join(cache_dir, "meta.json")

    fields = [
        "source_file",
        "chunk_index",
        "category",
        "security_level",
        "allowed_groups",
        "content_hash",
        "content",
    ]

    rows = []
    for doc in docs:
        data = doc.to_dict()
        row = {}
        for field in fields:
            val = data.get(field, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            row[field] = val
        rows.append(row)

    # chunk_index でソート
    rows.sort(key=lambda r: (r["source_file"], int(r.get("chunk_index", 0))))

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # メタ情報
    meta = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(rows),
        "collection": config.collection_name,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return len(rows)
