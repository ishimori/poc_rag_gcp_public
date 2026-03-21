"""DD-019-8 の記載内容と eval_dataset.jsonl の整合性を検証する。

チェック項目:
1. DD記載の失敗ケースID・クエリ・期待ソースが eval_dataset.jsonl と一致するか
2. DD記載の成功ケースが最新評価結果で実際に合格しているか
3. DD記載の代表3件が失敗ケースに含まれているか
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DD_PATH = ROOT / "doc" / "DD" / "DD-019-8_semanticテスト失敗の原因分析.md"
DD_TEST_CASES_PATH = ROOT / "doc" / "DD" / "DD-019-8" / "test_cases.md"
EVAL_DATASET = ROOT / "test-data" / "golden" / "eval_dataset.jsonl"
RESULTS_DIR = ROOT / "results"


def load_eval_cases() -> dict[str, dict]:
    """eval_dataset.jsonl から semantic ケースを読み込む。"""
    cases = {}
    with EVAL_DATASET.open(encoding="utf-8") as f:
        for line in f:
            case = json.loads(line)
            if case["type"] == "semantic":
                cases[case["id"]] = case
    return cases


def load_latest_results() -> dict[str, bool]:
    """最新の評価結果から semantic ケースの合否を取得する。

    結果ファイルには failed_cases のみ記録される。
    score_by_type.semantic.passed/total から成功IDを推定する。
    """
    result_files = sorted(RESULTS_DIR.glob("eval_*.json"))
    if not result_files:
        print("WARNING: 評価結果ファイルが見つかりません")
        return {}
    latest = result_files[-1]
    print(f"最新評価結果: {latest.name}")
    with latest.open(encoding="utf-8") as f:
        data = json.load(f)

    # failed_cases から不合格IDを収集
    failed_ids = {c["id"] for c in data.get("failed_cases", []) if c.get("type") == "semantic"}

    # eval_dataset.jsonl の全semantic IDと突き合わせて合否を判定
    eval_cases = load_eval_cases()
    results = {}
    for cid in eval_cases:
        results[cid] = cid not in failed_ids
    return results


def parse_dd_table(section_name: str, dd_text: str) -> list[dict]:
    """DD内のMarkdownテーブルからケース情報を抽出する。"""
    pattern = rf"##+ {re.escape(section_name)}.*?\n\n\|.*?\|\n\|[-| ]+\|\n((?:\|.*?\|\n)*)"
    match = re.search(pattern, dd_text, re.DOTALL)
    if not match:
        return []
    rows = []
    for line in match.group(1).strip().split("\n"):
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 3:
            rows.append(
                {
                    "id": cells[0],
                    "query": cells[1],
                    "source": cells[2],
                }
            )
    return rows


def parse_representative_cases(dd_text: str) -> list[dict]:
    """DD内の代表3件を抽出する。"""
    pattern = r"\*\*(\w+-\d+)\*\*「(.+?)」"
    return [{"id": m[0], "query": m[1]} for m in re.findall(pattern, dd_text)]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    dd_text = DD_PATH.read_text(encoding="utf-8")
    # テーブルが別ファイルに分離されている場合はそちらも読み込む
    if DD_TEST_CASES_PATH.exists():
        dd_text += "\n" + DD_TEST_CASES_PATH.read_text(encoding="utf-8")
    eval_cases = load_eval_cases()
    eval_results = load_latest_results()

    print(f"eval_dataset.jsonl: semantic {len(eval_cases)} 件")
    print(f"評価結果: semantic {len(eval_results)} 件")
    print()

    # --- Check 1: 失敗ケーステーブルの検証 ---
    print("=== Check 1: 失敗ケーステーブル ===")
    fail_rows = parse_dd_table("失敗ケース一覧", dd_text)
    if not fail_rows:
        errors.append("失敗ケーステーブルが見つかりません")
    for row in fail_rows:
        cid = row["id"]
        if cid not in eval_cases:
            errors.append(f"[失敗] {cid}: eval_dataset.jsonl に存在しません")
            continue
        ec = eval_cases[cid]
        if row["query"] != ec["query"]:
            errors.append(f'[失敗] {cid}: クエリ不一致 DD="{row["query"]}" actual="{ec["query"]}"')
        if row["source"] != ec["expected_source"]:
            errors.append(f'[失敗] {cid}: ソース不一致 DD="{row["source"]}" actual="{ec["expected_source"]}"')
        if eval_results.get(cid, False):
            errors.append(f"[失敗] {cid}: 評価結果では合格しているのに失敗一覧に含まれています")
        else:
            print(f"  OK {cid}: {row['query']}")

    # --- Check 2: 成功ケーステーブルの検証 ---
    print("\n=== Check 2: 成功ケーステーブル ===")
    pass_rows = parse_dd_table("成功ケース", dd_text)
    if not pass_rows:
        warnings.append("成功ケーステーブルが見つかりません")
    for row in pass_rows:
        cid = row["id"]
        if cid not in eval_cases:
            errors.append(f"[成功] {cid}: eval_dataset.jsonl に存在しません")
            continue
        ec = eval_cases[cid]
        if row["query"] != ec["query"]:
            errors.append(f'[成功] {cid}: クエリ不一致 DD="{row["query"]}" actual="{ec["query"]}"')
        if row["source"] != ec["expected_source"]:
            errors.append(f'[成功] {cid}: ソース不一致 DD="{row["source"]}" actual="{ec["expected_source"]}"')
        if not eval_results.get(cid, False):
            errors.append(f"[成功] {cid}: 評価結果では不合格なのに成功一覧に含まれています")
        else:
            print(f"  OK {cid}: {row['query']}")

    # --- Check 3: 網羅性（全semantic caseが成功or失敗に含まれるか） ---
    print("\n=== Check 3: 網羅性 ===")
    dd_ids = {r["id"] for r in fail_rows} | {r["id"] for r in pass_rows}
    for cid in sorted(eval_cases.keys()):
        if cid not in dd_ids:
            errors.append(f"[網羅] {cid}: DDのどちらのテーブルにも含まれていません")
    for cid in sorted(dd_ids):
        if cid not in eval_cases:
            errors.append(f"[網羅] {cid}: DDに記載があるが eval_dataset.jsonl に存在しません")
    if not errors:
        print(f"  OK 全 {len(eval_cases)} 件がDDに記載されています")

    # --- Check 4: 代表3件の検証 ---
    print("\n=== Check 4: 代表3件 ===")
    reps = parse_representative_cases(dd_text)
    fail_ids = {r["id"] for r in fail_rows}
    for rep in reps:
        if rep["id"] not in fail_ids:
            errors.append(f"[代表] {rep['id']}: 失敗ケース一覧に含まれていません")
        elif rep["id"] in eval_cases and rep["query"] != eval_cases[rep["id"]]["query"]:
            errors.append(
                f'[代表] {rep["id"]}: クエリ不一致 DD="{rep["query"]}" actual="{eval_cases[rep["id"]]["query"]}"'
            )
        else:
            print(f"  OK {rep['id']}: {rep['query']}")

    # --- Summary ---
    print("\n" + "=" * 50)
    if errors:
        print(f"FAIL: {len(errors)} 件のエラー")
        for e in errors:
            print(f"  x {e}")
        return 1
    else:
        print("PASS: DD-019-8 の記載は eval_dataset.jsonl と整合しています")
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
