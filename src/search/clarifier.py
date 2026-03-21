"""曖昧質問の判定モジュール — Pre-RAG で曖昧なクエリを検出し聞き返しを生成する"""

from __future__ import annotations

import json
from dataclasses import dataclass

import vertexai
from vertexai.generative_models import GenerativeModel, HarmBlockThreshold, HarmCategory

from src.config import config

_model: GenerativeModel | None = None
_vertexai_initialized = False

_CLARIFICATION_PROMPT = """\
あなたは社内ドキュメント検索システムの入力判定器です。
ユーザーの質問が曖昧で、検索しても適切な回答ができないかどうかを判定してください。

## 曖昧と判定する基準（非常に厳格に: 以下の全条件を満たす場合のみ曖昧）
- 指示語のみで対象が完全に不明（「あれ」「それ」「これ」だけで何を指すか分からない）
- 「エラーが出る」「接続できない」のように対象システムが一切不明
- 「申請したい」のように目的語が完全に欠落

## 曖昧ではないと判定する基準（重要: 少しでも対象が推測できるなら非曖昧）
- 対象が明確（「VPNの設定方法を教えて」「有給休暇は何日？」）
- 短い質問でも対象が特定できる（「PCが重い」「パスワードの条件は？」）
- 具体的なキーワードがある（「SUS316Lのボルトの部品番号」「経費精算の手順」）
- 問題の対象が特定できる（「メールが送れない」「印刷できない」「画面が固まった」）
- 動作や目的が具体的（「ログインできない」「USBメモリを使いたい」「新しいソフトを入れたい」）
- 社内ドキュメントに答えがない質問（「来月の株価は？」「競合他社の価格は？」）→ 回答不能であり曖昧ではない

## 出力形式
以下のJSON形式のみを出力してください。他のテキストは不要です。

曖昧な場合:
{{"is_ambiguous": true, "clarification_question": "具体的に何について知りたいですか？例えば○○、△△など..."}}

明確な場合:
{{"is_ambiguous": false, "clarification_question": ""}}

## ユーザーの質問
{query}"""


def _get_model() -> GenerativeModel:
    global _model, _vertexai_initialized
    if not _vertexai_initialized:
        vertexai.init(project=config.project_id or None, location=config.location)
        _vertexai_initialized = True
    if _model is None:
        _model = GenerativeModel(
            "gemini-2.5-flash",
            generation_config={"temperature": 0.0, "max_output_tokens": 2048},
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
    return _model


@dataclass
class ClarificationResult:
    is_ambiguous: bool
    clarification_question: str


def detect_ambiguity(query: str) -> ClarificationResult:
    """クエリが曖昧かどうかを判定し、曖昧な場合は聞き返し文を生成する"""
    try:
        model = _get_model()
        prompt = _CLARIFICATION_PROMPT.format(query=query)
        response = model.generate_content(prompt)

        if not (response.candidates and response.candidates[0].content.parts):
            return ClarificationResult(is_ambiguous=False, clarification_question="")

        raw = response.candidates[0].content.parts[0].text.strip()

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
