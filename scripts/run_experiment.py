"""DD-022: 単一コレクションの Ingest → Evaluate 一括実行スクリプト

1つのチャンクサイズ設定に対して Ingest → Evaluate を順次実行する。
複数コレクションを並列実行したい場合は、このスクリプトを複数起動する。

Usage:
    # Ingest + Evaluate
    python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200

    # Evaluate のみ（Ingest 済みコレクション）
    python scripts/run_experiment.py --collection chunks_1200 --evaluate-only

    # Ingest のみ
    python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200 --ingest-only

    # 3並列実行
    python scripts/run_experiment.py --chunk-size 1200 --collection chunks_1200 &
    python scripts/run_experiment.py --chunk-size 1600 --collection chunks_1600 &
    python scripts/run_experiment.py --chunk-size 2000 --collection chunks_2000 &
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ["PYTHONUTF8"] = "1"

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def run_ingest(collection: str, chunk_size: int, chunk_overlap: int) -> int:
    """Ingest を実行し、リターンコードを返す"""
    cmd = [
        PYTHON,
        str(SCRIPTS_DIR / "ingest.py"),
        "--clear",
        "--chunk-size",
        str(chunk_size),
        "--chunk-overlap",
        str(chunk_overlap),
        "--collection",
        collection,
    ]
    _log(f"[INGEST] {' '.join(cmd)}")
    result = subprocess.run(cmd, env={**os.environ, "PYTHONUTF8": "1"})
    return result.returncode


def run_evaluate(collection: str) -> int:
    """Evaluate を実行し、リターンコードを返す"""
    cmd = [
        PYTHON,
        str(SCRIPTS_DIR / "evaluate.py"),
        "--collection",
        collection,
    ]
    _log(f"[EVALUATE] {' '.join(cmd)}")
    result = subprocess.run(cmd, env={**os.environ, "PYTHONUTF8": "1"})
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="1コレクションの Ingest → Evaluate を一括実行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--collection", required=True, help="コレクション名 (例: chunks_1200)")
    parser.add_argument("--chunk-size", type=int, default=None, help="チャンクサイズ (Ingest時に必要)")
    parser.add_argument(
        "--chunk-overlap", type=int, default=None, help="チャンクオーバーラップ (省略時: chunk_size の 1/6)"
    )
    parser.add_argument("--ingest-only", action="store_true", help="Ingest のみ実行")
    parser.add_argument("--evaluate-only", action="store_true", help="Evaluate のみ実行")
    args = parser.parse_args()

    if args.ingest_only and args.evaluate_only:
        print("Error: --ingest-only と --evaluate-only は同時に指定できません")
        sys.exit(1)

    do_ingest = not args.evaluate_only
    do_evaluate = not args.ingest_only

    if do_ingest and args.chunk_size is None:
        print("Error: Ingest 実行時は --chunk-size が必要です")
        sys.exit(1)

    chunk_overlap = args.chunk_overlap or (args.chunk_size // 6 if args.chunk_size else 0)

    _log(f"=== Experiment: {args.collection} ===")
    if do_ingest:
        _log(f"  chunk_size={args.chunk_size}, chunk_overlap={chunk_overlap}")
    _log(f"  ingest={'YES' if do_ingest else 'SKIP'}, evaluate={'YES' if do_evaluate else 'SKIP'}")
    _log("")

    overall_start = time.time()

    # Ingest
    if do_ingest:
        _log("[INGEST] Starting...")
        start = time.time()
        rc = run_ingest(args.collection, args.chunk_size, chunk_overlap)
        elapsed = time.time() - start
        if rc != 0:
            _log(f"[INGEST] FAILED (exit code {rc}) in {_fmt(elapsed)}")
            sys.exit(rc)
        _log(f"[INGEST] Done in {_fmt(elapsed)}")
        _log("")

    # Evaluate
    if do_evaluate:
        _log("[EVALUATE] Starting...")
        start = time.time()
        rc = run_evaluate(args.collection)
        elapsed = time.time() - start
        if rc != 0:
            _log(f"[EVALUATE] FAILED (exit code {rc}) in {_fmt(elapsed)}")
            sys.exit(rc)
        _log(f"[EVALUATE] Done in {_fmt(elapsed)}")
        _log("")

    total = time.time() - overall_start
    _log(f"=== Experiment Complete: {args.collection} — Total {_fmt(total)} ===")


if __name__ == "__main__":
    main()
