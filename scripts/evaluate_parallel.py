"""並列評価パイプライン: eval_dataset.jsonl → RAG Flow（並列実行） → スコアレポート

通常の evaluate.py と同じ結果を出力するが、複数ケースを同時に実行して高速化する。

Usage:
    # デフォルト5並列
    python scripts/evaluate_parallel.py --collection chunks_800

    # 並列数を指定
    python scripts/evaluate_parallel.py --collection chunks_800 --workers 3

    # 先頭10件だけ
    python scripts/evaluate_parallel.py --collection chunks_800 --limit 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

# Windows cp932 問題を回避
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.evaluate.reporter import generate_report, print_report, save_report
from src.evaluate.runner import run_case
from src.evaluate.scorer import EvalCase, EvalResult
from src.task_status import check_cancel, clear_task_status, update_task_status

EVAL_DATASET = "test-data/golden/eval_dataset.jsonl"


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="並列RAG評価パイプライン")
    parser.add_argument("--limit", type=int, default=0, help="先頭N件だけ実行する（0=全件）")
    parser.add_argument("--collection", type=str, default=None, help="コレクション名")
    parser.add_argument("--workers", type=int, default=5, help="並列数（デフォルト: 5）")
    args = parser.parse_args()

    if args.collection is not None:
        config.collection_name = args.collection

    task_id = f"evaluate:{config.collection_name}"

    print(f"=== RAG Evaluation (Parallel, workers={args.workers}) ===")
    print(f"Collection: {config.collection_name}")
    print(f"Task ID: {task_id}")
    print()

    with open(EVAL_DATASET, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    cases = []
    for line in lines:
        data = json.loads(line)
        cases.append(
            EvalCase(
                id=data["id"],
                query=data["query"],
                expected_answer=data["expected_answer"],
                expected_keywords=data["expected_keywords"],
                type=data["type"],
                category=data["category"],
                requires=data.get("requires", ""),
            )
        )

    total_loaded = len(cases)
    if args.limit > 0:
        cases = cases[: args.limit]
        print(f"Loaded {total_loaded} evaluation cases (limit: {args.limit}).")
    else:
        print(f"Loaded {total_loaded} evaluation cases.")
    print()

    total = len(cases)
    start_time = time.time()
    completed = 0
    active_count = 0
    print_lock = Lock()
    results_map: dict[str, EvalResult] = {}

    update_task_status(
        task_id,
        running=True,
        cancel=False,
        current=0,
        total=total,
        current_id="",
        elapsed=0.0,
        estimated_remaining=0.0,
        results=[],
        collection=config.collection_name,
    )

    cancelled = False

    def _run_one(case: EvalCase) -> EvalResult:
        return run_case(case)

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_case = {executor.submit(_run_one, case): case for case in cases}

            for future in as_completed(future_to_case):
                if check_cancel(task_id):
                    cancelled = True
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                case = future_to_case[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = EvalResult(
                        id=case.id,
                        query=case.query,
                        type=case.type,
                        category=case.category,
                        expected=case.expected_answer,
                        actual=f"ERROR: {e}",
                        keyword_score=0.0,
                        passed=False,
                    )

                with print_lock:
                    completed += 1
                    if not result.skipped:
                        active_count += 1

                    results_map[case.id] = result

                    elapsed = time.time() - start_time
                    elapsed_str = _fmt(elapsed)

                    if result.skipped:
                        print(f"  [{completed}/{total}] SKIP {result.id} ({result.skipped_reason}) [{elapsed_str}]")
                    else:
                        status = "PASS" if result.passed else "FAIL"
                        disc = f" ⚠ {result.discrepancy}" if result.discrepancy else ""

                        remaining_str = ""
                        if active_count >= 2:
                            avg = elapsed / active_count
                            est = avg * (total - completed)
                            remaining_str = f", ~{_fmt(est)} remaining"

                        print(
                            f"  [{completed}/{total}] {status} {result.id}"
                            f" (llm: {result.llm_label}, keyword: {result.keyword_score * 100:.0f}%)"
                            f"{disc} [{elapsed_str}{remaining_str}]"
                        )

                    update_task_status(
                        task_id,
                        current=completed,
                        total=total,
                        current_id=result.id,
                        elapsed=round(elapsed, 1),
                        estimated_remaining=round(
                            (elapsed / active_count) * (total - completed) if active_count >= 2 else 0.0, 1
                        ),
                    )
    finally:
        clear_task_status(task_id)

    if cancelled:
        print(f"\n  Cancelled at {completed}/{total} cases.")

    # 元の順序で結果を並べる
    results = [results_map[case.id] for case in cases if case.id in results_map]

    report = generate_report(results)
    print_report(report)

    file_path = save_report(report)
    print(f"Report saved to: {file_path}")

    total_elapsed = time.time() - start_time
    print(f"Total time: {_fmt(total_elapsed)} ({args.workers} workers)")

    if args.limit > 0:
        print(f"\n  ⚠ Limited run ({args.limit}/{total_loaded} cases). Results are partial.")


if __name__ == "__main__":
    main()
