"""Multi-Query Expansion — クエリをLLMで複数の意味的バリエーションに展開する"""

from __future__ import annotations

import json

import vertexai
from vertexai.generative_models import GenerativeModel

from src.config import config

_model: GenerativeModel | None = None
_vertexai_initialized = False

_EXPAND_PROMPT = """\
あなたは検索クエリの書き換えアシスタントです。

ユーザーの質問に対して、意味は同じだが異なる表現・語彙の検索クエリを{count}個生成してください。

## ルール
- 元の質問の意図を変えない
- 異なる言い回し、同義語、関連する専門用語を使う
- 簡潔に（各クエリは1文）
- JSON配列で出力（他のテキスト不要）

## ユーザーの質問
{query}

## 出力形式
["{count}個のクエリをここに"]"""


def _get_model() -> GenerativeModel:
    global _model, _vertexai_initialized
    if not _vertexai_initialized:
        vertexai.init(project=config.project_id or None, location=config.location)
        _vertexai_initialized = True
    if _model is None:
        _model = GenerativeModel(
            "gemini-2.5-flash",
            generation_config={"temperature": 0.0, "max_output_tokens": 1024},
        )
    return _model


def expand_query(query: str) -> list[str]:
    """クエリを複数のバリエーションに展開する。元のクエリは含まない。"""
    try:
        model = _get_model()
        prompt = _EXPAND_PROMPT.format(query=query, count=config.multi_query_count)
        response = model.generate_content(prompt)

        if not (response.candidates and response.candidates[0].content.parts):
            return []

        raw = response.candidates[0].content.parts[0].text.strip()

        # JSON配列を抽出
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start < 0 or end <= start:
            return []

        queries = json.loads(raw[start:end])
        if not isinstance(queries, list):
            return []

        return [q for q in queries if isinstance(q, str) and q.strip()]
    except Exception as e:
        print(f"  [QueryExpander] Error: {e}")
        return []
