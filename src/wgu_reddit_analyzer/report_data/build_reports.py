"""
Lightweight report overviews for WGU Reddit Analyzer.

This script reads the full report_data tables and produces two sorted
overview CSVs to help with report design and manual inspection:

- artifacts/report_data/courses_overview.csv
    All courses, sorted by pain-point volume (no cutoffs).

- artifacts/report_data/issues_overview.csv
    All normalized issues, sorted by total posts and number of courses.

No rows are filtered out; this stage never decides thresholds.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def project_root() -> Path:
    """Return the repo root (one level above src/)."""
    return Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_course_summary(report_data_dir: Path) -> pd.DataFrame:
    """Load per-course summary metrics."""
    path = report_data_dir / "course_summary.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing report_data file: {path}")
    df = pd.read_csv(path)
    return df


def load_global_issues(report_data_dir: Path) -> pd.DataFrame:
    """Load normalized cross-course issue summaries."""
    path = report_data_dir / "global_issues.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing report_data file: {path}")
    df = pd.read_csv(path)
    return df


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_courses_overview(course_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Create an ordered overview of all courses.

    No filtering; just rank by:
    - total_pain_point_posts (desc)
    - total_negative_posts (desc)
    """
    df = course_summary.copy()

    df = df.sort_values(
        ["total_pain_point_posts", "total_negative_posts"],
        ascending=[False, False],
    ).reset_index(drop=True)

    df["rank_by_pain_points"] = df.index + 1

    # Keep useful columns up front
    cols = [
        "rank_by_pain_points",
        "course_code",
        "course_title_final",
        "college_list",
        "total_pain_point_posts",
        "total_negative_posts",
        "num_clusters",
        "top_issue_labels",
    ]
    # only keep columns that exist in df
    cols = [c for c in cols if c in df.columns]
    return df[cols]


def build_issues_overview(global_issues: pd.DataFrame) -> pd.DataFrame:
    """
    Create an ordered overview of all normalized issues.

    No filtering; just rank by:
    - total_num_posts (desc)
    - num_courses (desc)
    """
    df = global_issues.copy()

    df = df.sort_values(
        ["total_num_posts", "num_courses"],
        ascending=[False, False],
    ).reset_index(drop=True)

    df["rank_by_posts"] = df.index + 1

    cols = [
        "rank_by_posts",
        "normalized_issue_label",
        "provisional_label",
        "short_description",
        "total_num_posts",
        "num_courses",
        "num_clusters",
        "global_cluster_id",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols]


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build non-filtered report overviews for WGU Reddit Analyzer."
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Path to artifacts/ root (default: <repo_root>/artifacts)",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point: build overview CSVs for reports."""
    args = parse_args()
    root = project_root()
    artifacts_dir = args.artifacts_dir or (root / "artifacts")
    report_data_dir = artifacts_dir / "report_data"

    if not report_data_dir.exists():
        raise FileNotFoundError(f"report_data directory not found: {report_data_dir}")

    course_summary = load_course_summary(report_data_dir)
    global_issues = load_global_issues(report_data_dir)

    courses_overview = build_courses_overview(course_summary)
    issues_overview = build_issues_overview(global_issues)

    courses_overview_path = report_data_dir / "courses_overview.csv"
    issues_overview_path = report_data_dir / "issues_overview.csv"

    courses_overview.to_csv(courses_overview_path, index=False)
    issues_overview.to_csv(issues_overview_path, index=False)

    print("Report overviews written to:")
    print(f"- {courses_overview_path}")
    print(f"- {issues_overview_path}")


if __name__ == "__main__":
    main()