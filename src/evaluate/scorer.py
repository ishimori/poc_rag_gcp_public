from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    id: str
    query: str
    expected_answer: str
    expected_keywords: list[str]
    type: str
    category: str


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
