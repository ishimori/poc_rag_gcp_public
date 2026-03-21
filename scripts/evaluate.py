"""評価パイプライン: eval_dataset.jsonl → RAG Flow → スコアレポート"""

import json
import os
import sys
from pathlib import Path

# Windows cp932 問題を回避
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluate.reporter import generate_report, print_report, save_report
from src.evaluate.runner import run_evaluation
from src.evaluate.scorer import EvalCase

EVAL_DATASET = "test-data/golden/eval_dataset.jsonl"


def main():
    print("=== RAG Evaluation ===")
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
            )
        )

    print(f"Loaded {len(cases)} evaluation cases.")
    print()

    results = run_evaluation(cases)
    report = generate_report(results)
    print_report(report)

    file_path = save_report(report)
    print(f"Report saved to: {file_path}")


if __name__ == "__main__":
    main()
