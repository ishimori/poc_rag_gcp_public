from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime

from src.config import config
from src.evaluate.scorer import EvalResult


@dataclass
class Report:
    date: str
    config_params: dict
    score_by_type: dict[str, dict[str, int | float]]
    overall: dict[str, int | float]
    failed_cases: list[dict]


def generate_report(results: list[EvalResult]) -> Report:
    """評価結果からレポートを生成する"""
    # タイプ別スコア
    by_type: dict[str, dict[str, int]] = {}
    for r in results:
        if r.type not in by_type:
            by_type[r.type] = {"passed": 0, "total": 0}
        by_type[r.type]["total"] += 1
        if r.passed:
            by_type[r.type]["passed"] += 1

    score_by_type = {
        t: {**counts, "rate": counts["passed"] / counts["total"] if counts["total"] > 0 else 0}
        for t, counts in by_type.items()
    }

    total_passed = sum(1 for r in results if r.passed)
    overall = {
        "passed": total_passed,
        "total": len(results),
        "rate": total_passed / len(results) if results else 0,
    }

    failed_cases = [asdict(r) for r in results if not r.passed]

    return Report(
        date=datetime.now().isoformat(),
        config_params={
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
            "top_k": config.top_k,
            "rerank_top_n": config.rerank_top_n,
            "rerank_threshold": config.rerank_threshold,
            "embedding_model": config.embedding_model,
            "llm_model": config.llm_model,
        },
        score_by_type=score_by_type,
        overall=overall,
        failed_cases=failed_cases,
    )


def _safe_print(text: str) -> None:
    """Windows cp932で出力できない文字を置換して出力する"""
    print(text)


def print_report(report: Report) -> None:
    """レポートをコンソールに出力する"""
    print()
    print("=== RAG Evaluation Report ===")
    print(f"Date: {report.date}")
    cp = report.config_params
    print(
        f"Config: chunk_size={cp['chunk_size']}, overlap={cp['chunk_overlap']}, "
        f"top_k={cp['top_k']}, rerank_threshold={cp['rerank_threshold']}"
    )
    print()

    print("--- Score by Type ---")
    for type_name, score in report.score_by_type.items():
        pct = f"{score['rate'] * 100:.1f}"
        print(f"  {type_name:<20} {score['passed']}/{score['total']}  ({pct}%)")
    print()

    print("--- Overall ---")
    pct = f"{report.overall['rate'] * 100:.1f}"
    print(f"  Total: {report.overall['passed']}/{report.overall['total']} ({pct}%)")
    print()

    if report.failed_cases:
        print("--- Failed Cases ---")
        for fc in report.failed_cases:
            _safe_print(f"  [{fc['id']}] {fc['query']}")
            _safe_print(f"    Expected: {fc['expected']}")
            _safe_print(f"    Got: {fc['actual'][:100]}...")
            if fc["keyword_missed"]:
                _safe_print(f"    Missed keywords: {', '.join(fc['keyword_missed'])}")
            print()


def save_report(report: Report) -> str:
    """レポートをJSONファイルに保存する"""
    os.makedirs(config.results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(config.results_dir, f"eval_{timestamp}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    return file_path
