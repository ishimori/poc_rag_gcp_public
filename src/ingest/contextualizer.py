"""Contextual Retrieval: LLMで各チャンクに固有の文脈説明を自動生成する。

ヘッダーインジェクション（#02）の上位互換。文書全体を読んだ上で
各チャンクが「文書のどこにあり、何について述べているか」を説明するプレフィックスを生成する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import vertexai
from vertexai.generative_models import GenerativeModel

from src.config import config

if TYPE_CHECKING:
    from src.ingest.chunker import Chunk

_model: GenerativeModel | None = None
_vertexai_initialized = False

_CONTEXT_PROMPT = """\
以下の文書の一部（チャンク）に、簡潔な文脈説明を付けてください。
文脈説明は、このチャンクが文書のどの部分にあり、何について述べているかを1〜2文で説明するものです。

## 文書全体
{document_text}

## 対象チャンク
{chunk_text}

## 出力形式
文脈説明のみを出力してください。他のテキストは不要です。"""


def _get_model() -> GenerativeModel:
    global _model, _vertexai_initialized
    if not _vertexai_initialized:
        vertexai.init(project=config.project_id or None, location=config.location)
        _vertexai_initialized = True
    if _model is None:
        _model = GenerativeModel(
            config.llm_model,
            generation_config={"temperature": 0.0, "max_output_tokens": 256},
        )
    return _model


def _generate_context(document_text: str, chunk_text: str) -> str:
    """1チャンクの文脈説明を生成する。エラー時は空文字を返す。"""
    model = _get_model()
    prompt = _CONTEXT_PROMPT.format(
        document_text=document_text[:8000],  # トークン制限対策
        chunk_text=chunk_text,
    )
    try:
        response = model.generate_content(prompt)
        if response.candidates and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text.strip()
    except Exception as e:
        print(f"    [Context] Error: {e}")
    return ""


def contextualize_chunks(
    chunks: list[Chunk],
    document_text: str,
) -> list[Chunk]:
    """チャンクリストに文脈説明プレフィックスを付与する。

    各チャンクのcontentを `[文脈説明]\n{original_content}` に置換する。
    LLM生成に失敗した場合はチャンクをそのまま返す（フォールバック）。
    """
    from src.ingest.chunker import Chunk as ChunkClass

    contextualized = []
    for i, chunk in enumerate(chunks):
        context = _generate_context(document_text, chunk.content)
        if context:
            new_content = f"[{context}]\n{chunk.content}"
            print(f"    [Context] chunk {i}: {context[:60]}...")
        else:
            new_content = chunk.content
            print(f"    [Context] chunk {i}: fallback (no context generated)")

        contextualized.append(
            ChunkClass(
                content=new_content,
                source_file=chunk.source_file,
                chunk_index=chunk.chunk_index,
                category=chunk.category,
                security_level=chunk.security_level,
                allowed_groups=chunk.allowed_groups,
            )
        )

    return contextualized
