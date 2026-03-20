from __future__ import annotations

from src.search.flow import rag_flow
from src.evaluate.scorer import EvalCase, EvalResult, score_by_keywords, is_refusal


def run_case(eval_case: EvalCase) -> EvalResult:
    """1件の評価ケースを実行する"""
    print(f"  [{eval_case.id}] {eval_case.query}")

    rag_result = rag_flow(eval_case.query)
    answer = rag_result.answer

    if eval_case.type == "unanswerable":
        passed = is_refusal(answer)
        keyword_result = {"score": 1.0 if passed else 0.0, "matched": [], "missed": []}
    else:
        keyword_result = score_by_keywords(answer, eval_case.expected_keywords)
        passed = keyword_result["score"] >= 0.5  # type: ignore

    return EvalResult(
        id=eval_case.id,
        query=eval_case.query,
        type=eval_case.type,
        category=eval_case.category,
        expected=eval_case.expected_answer,
        actual=answer,
        keyword_score=keyword_result["score"],  # type: ignore
        keyword_matched=keyword_result["matched"],  # type: ignore
        keyword_missed=keyword_result["missed"],  # type: ignore
        passed=passed,
    )


def run_evaluation(cases: list[EvalCase]) -> list[EvalResult]:
    """全評価ケースを実行する"""
    results: list[EvalResult] = []

    for eval_case in cases:
        result = run_case(eval_case)
        status = "PASS" if result.passed else "FAIL"
        print(f"    → {status} (keyword: {result.keyword_score * 100:.0f}%)")
        results.append(result)

    return results
