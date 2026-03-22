"""インジェストパイプライン: test-data/sources/ → チャンク分割 → Embedding → Firestore"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.ingest.chunker import chunk_document
from src.ingest.contextualizer import contextualize_chunks
from src.ingest.embedder import embed_texts
from src.ingest.store import clear_collection, store_chunks
from src.task_status import check_cancel, clear_task_status, update_task_status

SOURCES_DIR = "test-data/sources"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest pipeline")
    parser.add_argument("--clear", action="store_true", help="Clear collection before ingesting")
    parser.add_argument("--chunk-size", type=int, default=None, help="Override chunk_size (default: config value)")
    parser.add_argument(
        "--chunk-overlap", type=int, default=None, help="Override chunk_overlap (default: config value)"
    )
    parser.add_argument("--collection", type=str, default=None, help="Override collection_name (default: config value)")
    return parser.parse_args()


def main():
    args = _parse_args()

    # CLI引数でconfigを上書き
    if args.chunk_size is not None:
        config.chunk_size = args.chunk_size
    if args.chunk_overlap is not None:
        config.chunk_overlap = args.chunk_overlap
    if args.collection is not None:
        config.collection_name = args.collection

    # task_id をコレクション別にする（UI から複数ジョブを区別可能にする）
    task_id = f"ingest:{config.collection_name}"

    print("=== Ingest Pipeline ===")
    print(f"Project: {config.project_id}")
    print(f"Collection: {config.collection_name}")
    print(f"Chunk size: {config.chunk_size}, Overlap: {config.chunk_overlap}")
    print(f"Task ID: {task_id}")
    print()

    if args.clear:
        print("Clearing existing collection...")
        deleted = clear_collection()
        print(f"Deleted {deleted} documents.")
        print()

    # ソースファイルの読み込み（サブディレクトリも再帰的に走査）
    files: list[tuple[str, str]] = []  # (relative_name, full_path)
    for root, _dirs, fnames in os.walk(SOURCES_DIR):
        for fname in sorted(fnames):
            if fname.endswith(".md"):
                full_path = os.path.join(root, fname)
                rel = os.path.relpath(full_path, SOURCES_DIR).replace("\\", "/")
                files.append((rel, full_path))
    files.sort()
    print(f"Found {len(files)} source files.")

    total_chunks = 0
    total_stored = 0
    total_skipped = 0
    start_time = time.time()
    cancelled = False

    update_task_status(
        task_id,
        running=True,
        cancel=False,
        current=0,
        total=len(files),
        current_file="",
        elapsed=0.0,
        estimated_remaining=0.0,
        collection=config.collection_name,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )

    try:
        for i, (file_name, file_path) in enumerate(files):
            if check_cancel(task_id):
                print(f"\n  Cancelled at {i}/{len(files)} files.")
                cancelled = True
                break

            update_task_status(task_id, current_file=file_name)

            with open(file_path, encoding="utf-8") as f:
                text = f.read()

            # チャンク分割
            chunks = chunk_document(text, file_name)
            print(f"  {file_name}: {len(chunks)} chunks")

            # 文脈説明の自動付与（Contextual Retrieval）
            if config.contextual_retrieval:
                chunks = contextualize_chunks(chunks, text)

            # Embedding生成
            texts = [c.content for c in chunks]
            embeddings = embed_texts(texts)

            # Firestoreに保存
            result = store_chunks(chunks, embeddings)
            total_chunks += len(chunks)
            total_stored += result["stored"]
            total_skipped += result["skipped"]

            # 進捗更新
            done = i + 1
            elapsed = time.time() - start_time
            avg = elapsed / done
            update_task_status(
                task_id,
                current=done,
                elapsed=round(elapsed, 1),
                estimated_remaining=round(avg * (len(files) - done), 1),
            )
    finally:
        clear_task_status(task_id)

    print()
    if cancelled:
        print("=== Cancelled ===")
    print("=== Summary ===")
    print(f"Total chunks: {total_chunks}")
    print(f"Stored: {total_stored}")
    print(f"Skipped (duplicate): {total_skipped}")


if __name__ == "__main__":
    main()
