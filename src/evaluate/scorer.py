from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import vertexai
from vertexai.generative_models import GenerativeModel, HarmBlockThreshold, HarmCategory

from src.config import config

_judge_model: GenerativeModel | None = None
_vertexai_initialized = False


@dataclass
class EvalCase:
    id: str
    query: str
    expected_answer: str
    expected_keywords: list[str]
    type: str
    category: str
    requires: str = ""  # 必要な機能名（空=常に評価対象）


@dataclass
class EvalResult:
    id: str
    query: str
    type: str
    category: str
    expected: str
    actual: str
    keyword_score: float
    keyword_matched: list[str] = field(default_factory=list)
    keyword_missed: list[str] = field(default_factory=list)
    passed: bool = False
    skipped: bool = False  # requires機能がOFF/未実装の場合True
    skipped_reason: str = ""
    # LLM-as-Judge fields
    llm_score: float = 0.0
    llm_label: str = ""  # "correct" / "partial" / "incorrect"
    llm_reasoning: str = ""
    discrepancy: str = ""  # "" = no discrepancy, otherwise description


# 機能名 → config属性名。Noneは未実装を意味する
FEATURE_MAP: dict[str, str | None] = {
    "permission_filter": None,  # 権限フィルタ: 未実装
    "clarification": None,  # 聞き返し機能: 未実装
    "header_injection": "header_injection",  # config.header_injection
}


def is_feature_active(feature_name: str) -> bool:
    """機能がONかどうかを判定する"""
    if feature_name not in FEATURE_MAP:
        return True  # 未知の機能名は常にON扱い
    config_attr = FEATURE_MAP[feature_name]
    if config_attr is None:
        return False  # 未実装
    return bool(getattr(config, config_attr, False))


def score_by_keywords(answer: str, expected_keywords: list[str]) -> dict[str, float | list[str]]:
    """キーワードベースのスコアリング"""
    if not expected_keywords:
        return {"score": 1.0, "matched": [], "missed": []}

    matched = [k for k in expected_keywords if k in answer]
    missed = [k for k in expected_keywords if k not in answer]

    return {
        "score": len(matched) / len(expected_keywords),
        "matched": matched,
        "missed": missed,
    }


def is_refusal(answer: str) -> bool:
    """回答不能ケースの判定"""
    refusal_patterns = [
        "記載がありません",
        "情報がありません",
        "情報は含まれていません",
        "見つかりません",
        "お答えできません",
        "該当する情報",
        "含まれていません",
    ]
    return any(p in answer for p in refusal_patterns)


def _get_judge_model() -> GenerativeModel:
    """LLM-as-Judge用モデルを取得する"""
    global _judge_model, _vertexai_initialized
    if not _vertexai_initialized:
        vertexai.init(project=config.project_id or None, location=config.location)
        _vertexai_initialized = True
    if _judge_model is None:
        _judge_model = GenerativeModel(
            "gemini-2.5-flash",
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 2048,
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
    return _judge_model


_JUDGE_PROMPT = """\
あなたはRAGシステムの回答品質を評価する審査員です。

## 評価対象
- 質問: {query}
- 期待回答: {expected}
- 実際の回答: {actual}

## 評価基準
以下の3段階で評価してください:
- **correct**: 実際の回答が期待回答の情報を正確に含んでおり、質問に適切に答えている
- **partial**: 期待回答の一部の情報は含んでいるが、不完全または不正確な部分がある
- **incorrect**: 期待回答の情報をほとんど含んでいない、または明らかに間違っている

意味的に同等であれば表現の違いは問いません（例: 「権限がない」と「アクセス拒否」は同等）。

## 出力形式
以下のJSON形式のみを出力してください。他のテキストは不要です。
{{"label": "correct|partial|incorrect", "reasoning": "判定理由（1文）"}}"""


def score_by_llm(query: str, expected: str, actual: str) -> dict[str, float | str]:
    """LLM-as-Judgeによるスコアリング（3段階）"""
    label_to_score = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}

    try:
        model = _get_judge_model()
        # 回答が長すぎるとMAX_TOKENSエラーになるため制限
        actual_trimmed = actual[:500] if len(actual) > 500 else actual
        prompt = _JUDGE_PROMPT.format(query=query, expected=expected, actual=actual_trimmed)
        response = model.generate_content(prompt)

        if not (response.candidates and response.candidates[0].content.parts):
            # ブロック理由を確認
            block_reason = ""
            if response.candidates:
                block_reason = str(getattr(response.candidates[0], "finish_reason", ""))
            elif hasattr(response, "prompt_feedback"):
                block_reason = str(response.prompt_feedback)
            return {
                "score": 0.0,
                "label": "incorrect",
                "reasoning": f"LLM returned empty response (block: {block_reason})",
            }

        raw = response.candidates[0].content.parts[0].text.strip()
        # JSON部分を抽出（前後にテキストやmarkdownがある場合に対応）
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # JSONパース失敗時: テキストからlabelを推定
            label = _extract_label_from_text(raw + response.candidates[0].content.parts[0].text)
            return {"score": label_to_score.get(label, 0.0), "label": label, "reasoning": "JSON parse fallback"}

        label = result.get("label", "incorrect")
        if label not in label_to_score:
            label = "incorrect"

        return {
            "score": label_to_score[label],
            "label": label,
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        return {"score": 0.0, "label": "incorrect", "reasoning": f"LLM judge error: {e}"}


def _extract_label_from_text(text: str) -> str:
    """テキストからlabelを推定するフォールバック"""
    text_lower = text.lower()
    # "correct" が "incorrect" より前に単独で現れるか確認
    match = re.search(r'"label"\s*:\s*"(correct|partial|incorrect)"', text_lower)
    if match:
        return match.group(1)
    if "partial" in text_lower:
        return "partial"
    if "incorrect" in text_lower:
        return "incorrect"
    if "correct" in text_lower:
        return "correct"
    return "incorrect"


def detect_discrepancy(keyword_passed: bool, llm_label: str) -> str:
    """キーワード判定とLLM判定の乖離を検出する"""
    llm_passed = llm_label in ("correct", "partial")

    if keyword_passed and not llm_passed:
        return "keyword_lenient"  # キーワードが甘い（偽陽性）
    if not keyword_passed and llm_passed:
        return "keyword_strict"  # キーワードが厳しい（偽陰性）
    return ""
