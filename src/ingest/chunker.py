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
    """Markdownのフロントマターからメタデータを抽出する

    インライン形式とブロック形式の両方をサポート:
      allowed_groups: ["all"]           # インライン形式
      allowed_groups:                    # ブロック形式
        - exec_board
    """
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        return text, {}

    meta: dict[str, str | list[str]] = {}
    lines = match.group(1).split("\n")
    i = 0
    while i < len(lines):
        # key: value（インライン）or key:（ブロックリストの開始）
        kv = re.match(r"^(\w+):\s*(.*)$", lines[i])
        if kv:
            key = kv.group(1)
            value = kv.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                # インライン形式リスト: ["all", "hr_admin"]
                meta[key] = [s.strip().strip('"') for s in value[1:-1].split(",")]
            elif value:
                # スカラー値: public
                meta[key] = value.strip('"')
            else:
                # 値なし → 次行以降のブロック形式リストを収集
                items: list[str] = []
                while i + 1 < len(lines) and re.match(r"^\s+-\s+", lines[i + 1]):
                    i += 1
                    item = re.sub(r"^\s+-\s+", "", lines[i]).strip().strip('"')
                    items.append(item)
                if items:
                    meta[key] = items
        i += 1
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
        # contextual_retrieval ONの場合、header_injectionは付けない（contextualizer.pyが上位互換として処理）
        if config.contextual_retrieval:
            content = doc.page_content
        elif config.header_injection:
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
