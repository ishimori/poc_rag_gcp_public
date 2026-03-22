"""DD-022: チャンクサイズ調整実験 — コレクション別自動一括実行スクリプト

各実験を独立したコレクション（chunks_1200, chunks_1600 等）に格納し、
結果を doc/DD/DD-022/ に保存する。

Usage:
    python scripts/run_chunk_experiments.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.evaluate.reporter import generate_report, print_report
from src.evaluate.runner import run_evaluation
from src.evaluate.scorer import EvalCase
from src.ingest.chunker import chunk_document
from src.ingest.contextualizer import contextualize_chunks
from src.ingest.embedder import embed_texts
from src.ingest.store import clear_collection, store_chunks
from src.task_status import check_cancel, clear_task_status, update_task_status

# ── 設定 ──────────────────────────────────────────

SOURCES_DIR = "test-data/sources"
EVAL_DATASET = "test-data/golden/eval_dataset.jsonl"
OUTPUT_DIR = "doc/DD/DD-022"

EXPERIMENTS = [
    {"label": "chunk1200", "chunk_size": 1200, "chunk_overlap": 200},
    {"label": "chunk1600", "chunk_size": 1600, "chunk_overlap": 300},
    {"label": "chunk2000", "chunk_size": 2000, "chunk_overlap": 400},
]

# ── ヘルパー ──────────────────────────────────────


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# ── Ingest ────────────────────────────────────────


def run_ingest(task_id: str) -> dict:
    """Clear + Ingest を実行し、サマリーを返す"""
    _log("Clearing collection...")
    deleted = clear_collection()
    _log(f"  Deleted {deleted} documents")

    files: list[tuple[str, str]] = []
    for root, _dirs, fnames in os.walk(SOURCES_DIR):
        for fname in sorted(fnames):
            if fname.endswith(".md"):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, SOURCES_DIR).replace("\\", "/")
                files.append((rel, full))
    files.sort()
    _log(f"  Found {len(files)} source files")

    total_chunks = 0
    total_stored = 0
    start = time.time()

    update_task_status(
        task_id,
        running=True,
        cancel=False,
        current=0,
        total=len(files),
        current_file="",
        elapsed=0.0,
        estimated_remaining=0.0,
        collection=config.collection_name,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )

    try:
        for i, (file_name, file_path) in enumerate(files, 1):
            if check_cancel(task_id):
                _log(f"  Cancelled at {i}/{len(files)} files.")
                break

            update_task_status(task_id, current_file=file_name)

            with open(file_path, encoding="utf-8") as f:
                text = f.read()

            chunks = chunk_document(text, file_name)

            if config.contextual_retrieval:
                chunks = contextualize_chunks(chunks, text)

            texts = [c.content for c in chunks]
            embeddings = embed_texts(texts)
            result = store_chunks(chunks, embeddings)

            total_chunks += len(chunks)
            total_stored += result["stored"]
            elapsed = time.time() - start

            done = i
            avg = elapsed / done
            update_task_status(
                task_id,
                current=done,
                elapsed=round(elapsed, 1),
                estimated_remaining=round(avg * (len(files) - done), 1),
            )

            _log(f"  [{i}/{len(files)}] {file_name}: {len(chunks)} chunks [{_fmt(elapsed)}]")
    finally:
        clear_task_status(task_id)

    return {
        "files": len(files),
        "total_chunks": total_chunks,
        "stored": total_stored,
        "elapsed": round(time.time() - start, 1),
    }


# ── Evaluate ──────────────────────────────────────


def run_evaluate(task_id: str) -> dict:
    """全件評価を実行し、レポートdictを返す"""
    with open(EVAL_DATASET, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    cases = [
        EvalCase(
            id=(d := json.loads(line))["id"],
            query=d["query"],
            expected_answer=d["expected_answer"],
            expected_keywords=d["expected_keywords"],
            type=d["type"],
            category=d["category"],
            requires=d.get("requires", ""),
        )
        for line in lines
    ]
    _log(f"  Loaded {len(cases)} evaluation cases")

    update_task_status(
        task_id,
        running=True,
        cancel=False,
        current=0,
        total=len(cases),
        collection=config.collection_name,
        chunk_size=config.chunk_size,
    )

    try:
        results = run_evaluation(cases)
    finally:
        clear_task_status(task_id)

    report = generate_report(results)
    print_report(report)
    return asdict(report)


# ── メイン ────────────────────────────────────────


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_summaries: list[dict] = []

    _log(f"=== DD-022: チャンクサイズ調整実験 ({len(EXPERIMENTS)} experiments) ===")
    _log(f"Output: {OUTPUT_DIR}/")
    _log("")

    overall_start = time.time()

    for idx, exp in enumerate(EXPERIMENTS, 1):
        label = exp["label"]
        collection_name = f"chunks_{exp['chunk_size']}"
        ingest_task_id = f"ingest:{collection_name}"
        evaluate_task_id = f"evaluate:{collection_name}"

        _log(f"{'=' * 60}")
        _log(f"Experiment {idx}/{len(EXPERIMENTS)}: {label}")
        _log(f"  chunk_size={exp['chunk_size']}, chunk_overlap={exp['chunk_overlap']}")
        _log(f"  collection={collection_name}")
        _log(f"{'=' * 60}")

        # Config を書き換え
        config.chunk_size = exp["chunk_size"]
        config.chunk_overlap = exp["chunk_overlap"]
        config.collection_name = collection_name

        # Ingest
        _log("[INGEST] Starting...")
        ingest_summary = run_ingest(ingest_task_id)
        _log(f"[INGEST] Done — {ingest_summary['total_chunks']} chunks in {_fmt(ingest_summary['elapsed'])}")
        _log("")

        # Evaluate
        _log("[EVALUATE] Starting...")
        eval_start = time.time()
        report = run_evaluate(evaluate_task_id)
        eval_elapsed = time.time() - eval_start
        _log(f"[EVALUATE] Done in {_fmt(eval_elapsed)}")

        overall = report["overall"]
        rate_pct = f"{overall['rate'] * 100:.1f}"
        _log(f"[RESULT] {overall['passed']}/{overall['total']} ({rate_pct}%)")
        _log("")

        # 結果を保存
        result_file = os.path.join(OUTPUT_DIR, f"result_{label}.json")
        combined = {
            "experiment": {**exp, "collection": collection_name},
            "ingest": ingest_summary,
            "report": report,
        }
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        _log(f"Saved: {result_file}")
        _log("")

        all_summaries.append(
            {
                "label": label,
                "collection": collection_name,
                "chunk_size": exp["chunk_size"],
                "chunk_overlap": exp["chunk_overlap"],
                "passed": overall["passed"],
                "total": overall["total"],
                "rate": overall["rate"],
                "chunks": ingest_summary["total_chunks"],
            }
        )

    # ── サマリー ──
    total_elapsed = time.time() - overall_start
    _log(f"{'=' * 60}")
    _log(f"ALL EXPERIMENTS DONE — Total time: {_fmt(total_elapsed)}")
    _log(f"{'=' * 60}")
    _log("")
    _log(f"{'Label':<20} {'Collection':<20} {'Chunks':>6} {'Score':>12} {'Rate':>6}")
    _log(f"{'-' * 20} {'-' * 20} {'-' * 6} {'-' * 12} {'-' * 6}")
    for s in all_summaries:
        score_str = f"{s['passed']}/{s['total']}"
        rate_str = f"{s['rate'] * 100:.1f}%"
        _log(f"{s['label']:<20} {s['collection']:<20} {s['chunks']:>6} {score_str:>12} {rate_str:>6}")

    # サマリーも保存
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "experiments": all_summaries,
                "total_elapsed": round(total_elapsed, 1),
                "baseline": {"chunk_size": 800, "chunk_overlap": 150, "rate": 0.797},
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    _log(f"\nSummary saved: {summary_file}")


if __name__ == "__main__":
    main()
