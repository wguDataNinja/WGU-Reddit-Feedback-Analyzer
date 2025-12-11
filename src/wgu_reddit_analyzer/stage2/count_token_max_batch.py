#!/usr/bin/env python
"""
inspect_course_batch_token_budget.py

Simple Stage 2 helper:

Given painpoints_full_for_clustering.csv with columns:
    post_id,course_code,root_cause_summary,pain_point_snippet

For each course_code:
    - count tokens for each row (root_cause_summary + pain_point_snippet)
    - sum tokens across all rows for that course

Then print the course(s) with the highest total token count.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict

from wgu_reddit_analyzer.utils.token_utils import count_tokens


def project_root() -> Path:
    """
    Repository root.

    File is at:
        src/wgu_reddit_analyzer/stage2/inspect_course_batch_token_budget.py
    Root is three levels up.
    """
    return Path(__file__).resolve().parents[3]


def default_csv_path() -> Path:
    return project_root() / "artifacts" / "stage2" / "painpoints_full_for_clustering.csv"


def main() -> None:
    csv_path = default_csv_path()
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    # course_code -> total token count
    course_tokens: Dict[str, int] = defaultdict(int)

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = ["course_code", "root_cause_summary", "pain_point_snippet"]
        for col in required:
            if col not in reader.fieldnames:
                raise SystemExit(
                    f"Missing required column '{col}' in CSV. "
                    f"Found columns: {reader.fieldnames}"
                )

        for row in reader:
            course_code = (row.get("course_code") or "").strip()
            if not course_code:
                continue

            summary = (row.get("root_cause_summary") or "").strip()
            snippet = (row.get("pain_point_snippet") or "").strip()
            text = f"{summary}\n{snippet}".strip()

            if not text:
                continue

            tokens = count_tokens(text)
            course_tokens[course_code] += tokens

    if not course_tokens:
        raise SystemExit("No valid rows found with text and course_code.")

    # Find max total tokens
    max_tokens = max(course_tokens.values())
    max_courses = [c for c, t in course_tokens.items() if t == max_tokens]

    print(f"CSV: {csv_path}")
    print(f"Total courses: {len(course_tokens)}")
    print(f"Max total tokens in a single course batch: {max_tokens}")
    print("Course(s) with this max total token count:")
    for c in max_courses:
        print(f"  {c}: {course_tokens[c]} tokens")


if __name__ == "__main__":
    main()