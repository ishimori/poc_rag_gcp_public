"""曖昧質問の判定モジュール — Pre-RAG で曖昧なクエリを検出し聞き返しを生成する"""

from __future__ import annotations

import json
from dataclasses import dataclass

from google import genai
from google.genai.types import GenerateContentConfig

from src.config import config

_genai_client: genai.Client | None = None


def _get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=config.project_id or None,
            location=config.llm_location,
        )
    return _genai_client


_CLARIFICATION_PROMPT = """\
あなたは社内ドキュメント検索システムの入力判定器です。
ユーザーの質問が曖昧で、検索しても適切な回答ができないかどうかを判定してください。

## 曖昧と判定する基準（以下のいずれかを満たす場合は曖昧）
- 指示語のみで対象が完全に不明（「あれ」「それ」「これ」だけで何を指すか分からない）
- 対象システムが一切不明（「エラーが出る」「接続できない」だけで何のシステムか不明）
- 目的語が完全に欠落（「申請したい」だけで何の申請か不明）
- 何の期限・条件かが不明（「期限はいつまで？」だけで対象が特定できない）

## 曖昧ではないと判定する基準（少しでも対象が推測できるなら非曖昧）
- 対象が明確（「VPNの設定方法を教えて」「有給休暇は何日？」）
- 具体的なキーワードがある（「SUS316Lのボルトの部品番号」「経費精算の手順」）
- 問題の対象が特定できる（「メールが送れない」「印刷できない」）
- 社内ドキュメントに答えがない質問 → 回答不能であり曖昧ではない

## 判定例

### 曖昧な例
- 「あれの設定方法を教えて」→ 曖昧（「あれ」が何を指すか不明）
- 「接続できない」→ 曖昧（何への接続か不明）
- 「エラーが出る」→ 曖昧（どのシステムのエラーか不明）
- 「申請したい」→ 曖昧（何の申請か不明）
- 「期限はいつまで？」→ 曖昧（何の期限か不明）

### 明確な例
- 「VPNに接続できない」→ 明確（VPNという対象が特定されている）
- 「有給休暇の申請方法」→ 明確（有給休暇の申請と特定されている）
- 「PCが重い」→ 明確（PCのパフォーマンス問題と特定できる）
- 「来月の株価は？」→ 明確（回答不能だが曖昧ではない）

## 出力形式
以下のJSON形式のみを出力してください。他のテキストは不要です。

曖昧な場合:
{{"is_ambiguous": true, "clarification_question": "具体的に何について知りたいですか？例えば○○、△△など..."}}

明確な場合:
{{"is_ambiguous": false, "clarification_question": ""}}

## ユーザーの質問
{query}"""


_GENAI_CONFIG = GenerateContentConfig(temperature=0.0, max_output_tokens=2048)


@dataclass
class ClarificationResult:
    is_ambiguous: bool
    clarification_question: str


def detect_ambiguity(query: str) -> ClarificationResult:
    """クエリが曖昧かどうかを判定し、曖昧な場合は聞き返し文を生成する"""
    try:
        client = _get_genai_client()
        prompt = _CLARIFICATION_PROMPT.format(query=query)
        response = client.models.generate_content(
            model=config.llm_model,
            contents=prompt,
            config=_GENAI_CONFIG,
        )

        if not response.text:
            return ClarificationResult(is_ambiguous=False, clarification_question="")

        raw = response.text.strip()

        # JSON部分を抽出
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return ClarificationResult(is_ambiguous=False, clarification_question="")

        result = json.loads(raw[start:end])
        is_ambiguous = result.get("is_ambiguous", False)
        clarification = result.get("clarification_question", "")

        if is_ambiguous and not clarification:
            clarification = "もう少し具体的に教えていただけますか？"

        return ClarificationResult(
            is_ambiguous=bool(is_ambiguous),
            clarification_question=clarification,
        )
    except (json.JSONDecodeError, Exception) as e:
        # パース失敗・API エラー時は安全側（非曖昧）に倒す
        print(f"  [Clarifier] Error: {e}")
        return ClarificationResult(is_ambiguous=False, clarification_question="")
