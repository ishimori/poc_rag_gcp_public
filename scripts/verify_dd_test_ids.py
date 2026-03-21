"""全DDファイルに記載されたテストケースIDが eval_dataset.jsonl と整合しているか検証する。

チェック項目:
1. DD内のテストケースIDが eval_dataset.jsonl に存在するか
2. IDと同じ行にクエリが記載されている場合、クエリが一致するか
3. IDと同じ行にソースが記載されている場合、ソースが一致するか
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_DATASET = ROOT / "test-data" / "golden" / "eval_dataset.jsonl"
DD_DIRS = [ROOT / "doc" / "DD", ROOT / "doc" / "DD" / "archived"]

# テストケースIDのパターン
ID_PATTERN = re.compile(
    r"\b(semantic|exact|confuse|steps|multi|unanswerable|ambiguous|cross|security|noise|table|temporal)-(\d+)\b"
)


def load_eval_cases() -> dict[str, dict]:
    """eval_dataset.jsonl から全ケースを読み込む。"""
    cases = {}
    with EVAL_DATASET.open(encoding="utf-8") as f:
        for line in f:
            case = json.loads(line)
            cases[case["id"]] = case
    return cases


def find_dd_files() -> list[Path]:
    """DDファイルを再帰的に検索する。"""
    files = []
    for dd_dir in DD_DIRS:
        if dd_dir.exists():
            files.extend(dd_dir.rglob("*.md"))
    return sorted(files)


def extract_ids_with_context(text: str, file_path: Path) -> list[dict]:
    """テキストからテストケースIDとその行の文脈を抽出する。"""
    findings = []
    for line_no, line in enumerate(text.split("\n"), start=1):
        for match in ID_PATTERN.finditer(line):
            case_id = f"{match.group(1)}-{match.group(2)}"
            # IDが含まれる行からクエリやソースを推定（Markdownテーブル行の場合）
            cells = [c.strip() for c in line.split("|")] if "|" in line else []
            findings.append(
                {
                    "id": case_id,
                    "line_no": line_no,
                    "line": line.strip(),
                    "cells": cells,
                    "file": file_path,
                }
            )
    return findings


def check_table_row(finding: dict, eval_cases: dict[str, dict]) -> list[str]:
    """テーブル行のIDに対応するクエリ・ソースの整合性をチェック。"""
    errors = []
    case_id = finding["id"]
    cells = finding["cells"]

    if case_id not in eval_cases:
        errors.append(
            f"  {finding['file'].relative_to(ROOT)}:{finding['line_no']}: "
            f"{case_id} は eval_dataset.jsonl に存在しません"
        )
        return errors

    ec = eval_cases[case_id]

    # テーブル行でクエリを探す（IDの次のセルにクエリがある場合が多い）
    for cell in cells:
        # クエリとの一致チェック（完全一致 or 部分一致）
        if cell and cell == ec.get("query"):
            break  # 一致 → OK
        # クエリに似ているが不一致のケースを検出
        query = ec.get("query", "")
        if cell and len(cell) > 3 and cell != query:
            # セルがクエリと文字列として類似しているか（部分一致で判定）
            if _is_query_like(cell, query):
                errors.append(
                    f"  {finding['file'].relative_to(ROOT)}:{finding['line_no']}: "
                    f'{case_id} クエリ不一致: DD="{cell}" actual="{query}"'
                )

    # ソースファイルの一致チェック
    expected_source = ec.get("expected_source", "")
    for cell in cells:
        if cell and cell.endswith(".md") and cell != expected_source:
            # .md で終わるセルがあり、期待ソースと異なる
            errors.append(
                f"  {finding['file'].relative_to(ROOT)}:{finding['line_no']}: "
                f'{case_id} ソース不一致: DD="{cell}" actual="{expected_source}"'
            )

    return errors


def _is_query_like(cell: str, query: str) -> bool:
    """セルがクエリと類似しているかを簡易判定する。

    - Markdownヘッダや表の区切り、数値のみのセルを除外
    - 日本語を含む3文字以上のテキストで、eval_datasetのクエリとは異なるものを検出
    """
    # 明らかに非クエリのパターンを除外
    if cell.startswith("#") or cell.startswith("-"):
        return False
    if re.match(r"^[\d./%]+$", cell):
        return False
    if cell in ("情報なし", "—", ""):
        return False
    # ファイル名は除外
    if cell.endswith(".md"):
        return False
    # 英数字のみのセル（カテゴリ名等）を除外
    if re.match(r"^[a-zA-Z0-9_\- ]+$", cell):
        return False
    # 数字+日本語（「2/12」等のスコア表記）を除外
    if re.match(r"^\d+/\d+", cell):
        return False
    # 括弧で始まるコメント的なセルを除外
    if cell.startswith("(") or cell.startswith("（"):
        return False
    # 長すぎるセル（説明文）を除外
    if len(cell) > 60:
        return False
    # 短すぎるセル（1-2文字）を除外
    if len(cell) <= 2:
        return False
    # ここまで来たら、日本語テキストとしてクエリ候補
    return True


def main() -> int:
    eval_cases = load_eval_cases()
    dd_files = find_dd_files()
    all_errors: list[str] = []
    files_checked = 0
    ids_checked = 0

    print(f"eval_dataset.jsonl: {len(eval_cases)} 件")
    print(f"DDファイル: {len(dd_files)} 件")
    print()

    for dd_file in dd_files:
        text = dd_file.read_text(encoding="utf-8")
        findings = extract_ids_with_context(text, dd_file)
        if not findings:
            continue

        files_checked += 1
        file_errors: list[str] = []

        for finding in findings:
            ids_checked += 1
            case_id = finding["id"]

            # IDの存在チェック
            if case_id not in eval_cases:
                file_errors.append(
                    f"  {dd_file.relative_to(ROOT)}:{finding['line_no']}: "
                    f"{case_id} は eval_dataset.jsonl に存在しません"
                )
                continue

            # テーブル行の場合はクエリ・ソースもチェック
            if finding["cells"]:
                file_errors.extend(check_table_row(finding, eval_cases))

        if file_errors:
            rel = dd_file.relative_to(ROOT)
            print(f"FAIL {rel} ({len(file_errors)} errors)")
            for e in file_errors:
                print(f"  x {e}")
            all_errors.extend(file_errors)
        else:
            rel = dd_file.relative_to(ROOT)
            print(f"  OK {rel} ({len(findings)} refs)")

    print()
    print("=" * 60)
    print(f"checked: {files_checked} files, {ids_checked} ID references")
    if all_errors:
        print(f"FAIL: {len(all_errors)} errors found")
        return 1
    else:
        print("PASS: All DD test case references match eval_dataset.jsonl")
        return 0


if __name__ == "__main__":
    sys.exit(main())
