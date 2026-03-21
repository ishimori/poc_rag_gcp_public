from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
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
    discrepancies: list[dict] = field(default_factory=list)


def generate_report(results: list[EvalResult]) -> Report:
    """評価結果からレポートを生成する"""
    # skippedケースを除外して集計
    active_results = [r for r in results if not r.skipped]
    skipped_results = [r for r in results if r.skipped]

    # タイプ別スコア（skipped除外）
    by_type: dict[str, dict[str, int]] = {}
    for r in active_results:
        if r.type not in by_type:
            by_type[r.type] = {"passed": 0, "total": 0}
        by_type[r.type]["total"] += 1
        if r.passed:
            by_type[r.type]["passed"] += 1

    # skippedタイプも表示用に記録
    for r in skipped_results:
        if r.type not in by_type:
            by_type[r.type] = {"passed": 0, "total": 0, "skipped": 0}
        by_type[r.type].setdefault("skipped", 0)
        by_type[r.type]["skipped"] = by_type[r.type].get("skipped", 0) + 1

    score_by_type = {
        t: {**counts, "rate": counts["passed"] / counts["total"] if counts["total"] > 0 else 0}
        for t, counts in by_type.items()
    }

    total_passed = sum(1 for r in active_results if r.passed)
    overall = {
        "passed": total_passed,
        "total": len(active_results),
        "total_with_skipped": len(results),
        "skipped": len(skipped_results),
        "rate": total_passed / len(active_results) if active_results else 0,
    }

    failed_cases = [asdict(r) for r in active_results if not r.passed]
    discrepancies = [asdict(r) for r in active_results if r.discrepancy]

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
        discrepancies=discrepancies,
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

    print("--- Score by Type (LLM-as-Judge) ---")
    for type_name, score in report.score_by_type.items():
        skipped = score.get("skipped", 0)
        if skipped and score["total"] == 0:
            print(f"  {type_name:<20} (skipped: {skipped} cases, feature not active)")
        else:
            pct = f"{score['rate'] * 100:.1f}"
            skip_note = f"  +{skipped} skipped" if skipped else ""
            print(f"  {type_name:<20} {score['passed']}/{score['total']}  ({pct}%){skip_note}")
    print()

    print("--- Overall ---")
    pct = f"{report.overall['rate'] * 100:.1f}"
    skipped = report.overall.get("skipped", 0)
    total_all = report.overall.get("total_with_skipped", report.overall["total"])
    print(f"  Active: {report.overall['passed']}/{report.overall['total']} ({pct}%)")
    if skipped:
        print(f"  Skipped: {skipped} cases (features not active)")
        print(f"  Total cases: {total_all}")
    print()

    if report.discrepancies:
        print("--- Discrepancies (keyword vs LLM) ---")
        for dc in report.discrepancies:
            disc_type = dc["discrepancy"]
            label = "keyword=PASS/LLM=FAIL" if disc_type == "keyword_lenient" else "keyword=FAIL/LLM=PASS"
            _safe_print(f"  [{dc['id']}] {label}")
            _safe_print(f"    Query: {dc['query']}")
            _safe_print(f"    LLM: {dc['llm_label']} - {dc['llm_reasoning']}")
            if dc.get("keyword_missed"):
                _safe_print(f"    Missed keywords: {', '.join(dc['keyword_missed'])}")
            print()

    if report.failed_cases:
        print("--- Failed Cases ---")
        for fc in report.failed_cases:
            _safe_print(f"  [{fc['id']}] {fc['query']}")
            _safe_print(f"    Expected: {fc['expected']}")
            _safe_print(f"    Got: {fc['actual'][:100]}...")
            _safe_print(f"    LLM: {fc.get('llm_label', 'N/A')} - {fc.get('llm_reasoning', '')}")
            if fc["keyword_missed"]:
                _safe_print(f"    Missed keywords: {', '.join(fc['keyword_missed'])}")
            print()


def save_report(report: Report) -> str:
    """レポートをFirestoreとJSONファイルに保存する"""
    # Firestore保存
    try:
        from google.cloud import firestore as _firestore

        db = _firestore.Client(project=config.project_id or None)
        db.collection("eval_results").add(
            {
                **asdict(report),
                "timestamp": _firestore.SERVER_TIMESTAMP,
            }
        )
    except Exception as e:
        print(f"  [Reporter] Firestore save failed: {e}")

    # ローカルファイル保存（フォールバック）
    try:
        os.makedirs(config.results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(config.results_dir, f"eval_{timestamp}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)
        return file_path
    except Exception:
        return "(saved to Firestore only)"
