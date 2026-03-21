from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import config


@dataclass
class Chunk:
    content: str
    source_file: str
    chunk_index: int
    category: str = "general"
    security_level: str = "public"
    allowed_groups: list[str] = field(default_factory=lambda: ["all"])


def _extract_frontmatter(text: str) -> tuple[str, dict[str, str | list[str]]]:
    """Markdownのフロントマターからメタデータを抽出する"""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        return text, {}

    meta: dict[str, str | list[str]] = {}
    for line in match.group(1).split("\n"):
        kv = re.match(r"^(\w+):\s*(.+)$", line)
        if kv:
            value = kv.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                meta[kv.group(1)] = [s.strip().strip('"') for s in value[1:-1].split(",")]
            else:
                meta[kv.group(1)] = value.strip('"')
    return match.group(2), meta


def chunk_document(text: str, file_name: str) -> list[Chunk]:
    """Markdownテキストをチャンクに分割する"""
    body, meta = _extract_frontmatter(text)

    # タイトル抽出（最初のH1、なければファイル名）
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1) if title_match else file_name

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    docs = splitter.create_documents([body])

    chunks = []
    for i, doc in enumerate(docs):
        # ヘッダーインジェクション（config で無効化可能）
        if config.header_injection:
            content = f"[{title}]\n{doc.page_content}"
        else:
            content = doc.page_content
        chunks.append(
            Chunk(
                content=content,
                source_file=file_name,
                chunk_index=i,
                category=str(meta.get("category", "general")),
                security_level=str(meta.get("security_level", "public")),
                allowed_groups=meta.get("allowed_groups", ["all"]),  # type: ignore
            )
        )

    return chunks
