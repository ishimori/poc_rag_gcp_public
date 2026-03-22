from __future__ import annotations

import time
from collections.abc import Callable

from src.config import config
from src.evaluate.scorer import (
    EvalCase,
    EvalResult,
    detect_discrepancy,
    is_feature_active,
    is_refusal,
    score_by_keywords,
    score_by_llm,
)
from src.search.flow import rag_flow

ProgressCallback = Callable[[int, int, EvalResult], None]
CancelCheck = Callable[[], bool]


def _format_time(seconds: float) -> str:
    """秒数を M:SS 形式に変換する"""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def run_case(eval_case: EvalCase) -> EvalResult:
    """1件の評価ケースを実行する"""

    # requires判定: 機能がOFF/未実装ならスキップ
    if eval_case.requires and not is_feature_active(eval_case.requires):
        return EvalResult(
            id=eval_case.id,
            query=eval_case.query,
            type=eval_case.type,
            category=eval_case.category,
            expected=eval_case.expected_answer,
            actual="(skipped)",
            keyword_score=0.0,
            skipped=True,
            skipped_reason=f"requires: {eval_case.requires}",
        )

    rag_result = rag_flow(eval_case.query, user_groups=config.user_groups)
    answer = rag_result.answer

    # キーワード判定（参考値として常に実行）
    if eval_case.type == "unanswerable":
        keyword_passed = is_refusal(answer)
        keyword_result = {"score": 1.0 if keyword_passed else 0.0, "matched": [], "missed": []}
    else:
        keyword_result = score_by_keywords(answer, eval_case.expected_keywords)
        keyword_passed = keyword_result["score"] >= 0.5  # type: ignore

    # LLM-as-Judge判定（主判定）
    llm_result = score_by_llm(
        query=eval_case.query,
        expected=eval_case.expected_answer,
        actual=answer,
    )

    # passed判定はLLMベース（correct or partial = PASS）
    passed = llm_result["label"] in ("correct", "partial")

    # 乖離検出
    discrepancy = detect_discrepancy(keyword_passed, llm_result["label"])  # type: ignore

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
        llm_score=llm_result["score"],  # type: ignore
        llm_label=llm_result["label"],  # type: ignore
        llm_reasoning=llm_result["reasoning"],  # type: ignore
        discrepancy=discrepancy,
    )


def run_evaluation(
    cases: list[EvalCase],
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> list[EvalResult]:
    """全評価ケースを実行する"""
    results: list[EvalResult] = []
    total = len(cases)
    start_time = time.time()
    active_count = 0

    for i, eval_case in enumerate(cases, 1):
        if should_cancel and should_cancel():
            print(f"\n  Cancelled at {i - 1}/{total} cases.")
            break

        result = run_case(eval_case)
        elapsed = time.time() - start_time
        elapsed_str = _format_time(elapsed)

        if result.skipped:
            print(f"  [{i}/{total}] SKIP {result.id} ({result.skipped_reason}) [{elapsed_str} elapsed]")
        else:
            active_count += 1
            status = "PASS" if result.passed else "FAIL"
            disc = f" ⚠ {result.discrepancy}" if result.discrepancy else ""

            # 残り時間推定: activeケースの平均実行時間 × 残りケース数
            remaining_str = ""
            if active_count >= 2:
                avg_per_active = elapsed / active_count
                est_remaining = avg_per_active * (total - i)
                remaining_str = f", ~{_format_time(est_remaining)} remaining"

            print(
                f"  [{i}/{total}] {status} {result.id}"
                f" (llm: {result.llm_label}, keyword: {result.keyword_score * 100:.0f}%)"
                f"{disc} [{elapsed_str} elapsed{remaining_str}]"
            )

        if on_progress:
            on_progress(i, total, result)

        results.append(result)

    skipped = sum(1 for r in results if r.skipped)
    if skipped:
        print(f"\n  Skipped: {skipped} cases (requires unimplemented features)")

    return results
