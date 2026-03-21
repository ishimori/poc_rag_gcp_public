"""インジェストパイプライン: test-data/sources/ → チャンク分割 → Embedding → Firestore"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.ingest.chunker import chunk_document
from src.ingest.contextualizer import contextualize_chunks
from src.ingest.embedder import embed_texts
from src.ingest.store import clear_collection, store_chunks

SOURCES_DIR = "test-data/sources"


def main():
    should_clear = "--clear" in sys.argv

    print("=== Ingest Pipeline ===")
    print(f"Project: {config.project_id}")
    print(f"Collection: {config.collection_name}")
    print(f"Chunk size: {config.chunk_size}, Overlap: {config.chunk_overlap}")
    print()

    if should_clear:
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

    for file_name, file_path in files:
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

    print()
    print("=== Summary ===")
    print(f"Total chunks: {total_chunks}")
    print(f"Stored: {total_stored}")
    print(f"Skipped (duplicate): {total_skipped}")


if __name__ == "__main__":
    main()
