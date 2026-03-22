"""評価パイプライン: eval_dataset.jsonl → RAG Flow → スコアレポート"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Windows cp932 問題を回避
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.evaluate.reporter import generate_report, print_report, save_report
from src.evaluate.runner import run_evaluation
from src.evaluate.scorer import EvalCase
from src.task_status import check_cancel, clear_task_status, update_task_status

EVAL_DATASET = "test-data/golden/eval_dataset.jsonl"


def main():
    parser = argparse.ArgumentParser(description="RAG評価パイプライン")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="先頭N件だけ実行する（検証用。0=全件）",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="Override collection_name (default: config value)",
    )
    args = parser.parse_args()

    # CLI引数でconfigを上書き
    if args.collection is not None:
        config.collection_name = args.collection

    # task_id をコレクション別にする
    task_id = f"evaluate:{config.collection_name}"

    print("=== RAG Evaluation ===")
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

    start_time = time.time()
    active_count = 0

    update_task_status(
        task_id,
        running=True,
        cancel=False,
        current=0,
        total=len(cases),
        current_id="",
        elapsed=0.0,
        estimated_remaining=0.0,
        results=[],
        collection=config.collection_name,
    )

    def _on_progress(current: int, total: int, result) -> None:
        nonlocal active_count
        elapsed = time.time() - start_time
        if not result.skipped:
            active_count += 1

        est_remaining = 0.0
        if active_count >= 2:
            avg_per_active = elapsed / active_count
            est_remaining = avg_per_active * (total - current)

        update_task_status(
            task_id,
            current=current,
            total=total,
            current_id=result.id,
            elapsed=round(elapsed, 1),
            estimated_remaining=round(est_remaining, 1),
        )

    def _should_cancel() -> bool:
        return check_cancel(task_id)

    try:
        results = run_evaluation(cases, on_progress=_on_progress, should_cancel=_should_cancel)
    finally:
        clear_task_status(task_id)

    report = generate_report(results)
    print_report(report)

    file_path = save_report(report)
    print(f"Report saved to: {file_path}")

    if args.limit > 0:
        print(f"\n  ⚠ Limited run ({args.limit}/{total_loaded} cases). Results are partial.")


if __name__ == "__main__":
    main()
