#!/usr/bin/env python3
"""
Prepare a token-conscious painpoint table from full-corpus Stage-1 predictions.

Adds:
    - Sorting by number of posts per course (descending)
    - Stable tie-break on course_code, then post_id

Input:
    /Users/buddy/Desktop/WGU-Reddit/artifacts/stage1/full_corpus/.../predictions_FULL.csv

Output (example):
    /Users/buddy/Desktop/WGU-Reddit/artifacts/stage2/painpoints_full_for_clustering.csv

Keeps only:
    - pred_contains_painpoint == "y"
    - no parse/schema/fallback/llm failures
    - confidence_pred >= MIN_CONFIDENCE

Output columns:
    - post_id
    - course_code
    - root_cause_summary
    - pain_point_snippet
"""

import csv
from collections import defaultdict
from pathlib import Path

# --- CONFIG ---------------------------------------------------------

DEFAULT_INPUT = Path(
    "/Users/buddy/Desktop/WGU-Reddit/artifacts/stage1/full_corpus/"
    "gpt-5-mini_s1_optimal_fullcorpus_20251126_023336/"
    "predictions_FULL.csv"
)

DEFAULT_OUTPUT = Path(
    "/Users/buddy/Desktop/WGU-Reddit/artifacts/stage2/painpoints_llm_friendly.csv"
)

MIN_CONFIDENCE = 0.50


# --- SCRIPT ---------------------------------------------------------

def prepare_painpoints(
    input_csv: Path = DEFAULT_INPUT,
    output_csv: Path = DEFAULT_OUTPUT,
    min_conf: float = MIN_CONFIDENCE,
) -> None:

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    painpoints = []
    total = 0

    with input_csv.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)

        for row in reader:
            total += 1

            if row.get("pred_contains_painpoint") != "y":
                continue

            if any(
                row.get(flag, "False") == "True"
                for flag in ("parse_error", "schema_error", "used_fallback", "llm_failure")
            ):
                continue

            try:
                conf = float(row.get("confidence_pred", "0") or 0.0)
            except ValueError:
                conf = 0.0

            if conf < min_conf:
                continue

            post_id = row["post_id"]
            course_code = row["course_code"]
            root_cause = (row.get("root_cause_summary_pred") or "").strip()
            snippet = (row.get("pain_point_snippet_pred") or "").strip()

            painpoints.append(
                {
                    "post_id": post_id,
                    "course_code": course_code,
                    "root_cause_summary": root_cause,
                    "pain_point_snippet": snippet,
                }
            )

    # --- SORT: by number of posts per course (desc), then course_code, then post_id --

    course_post_ids = defaultdict(set)
    for p in painpoints:
        course_post_ids[p["course_code"]].add(p["post_id"])

    painpoints.sort(
        key=lambda r: (
            -len(course_post_ids[r["course_code"]]),  # more posts first
            r["course_code"],
            r["post_id"],
        )
    )

    # --- WRITE OUTPUT ----------------------------------------------
    with output_csv.open("w", newline="", encoding="utf-8") as f_out:
        fieldnames = [
            "post_id",
            "course_code",
            "root_cause_summary",
            "pain_point_snippet",
        ]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(painpoints)

    print(f"Done. Kept {len(painpoints)} painpoints out of {total} posts.")
    print(f"Written to: {output_csv}")


if __name__ == "__main__":
    prepare_painpoints()