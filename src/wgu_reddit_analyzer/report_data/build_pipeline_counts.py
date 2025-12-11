from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple

import pandas as pd


def _load_post_master(report_data_dir: Path) -> pd.DataFrame:
    path = report_data_dir / "post_master.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing post_master.csv at {path}")
    df = pd.read_csv(path)
    required = {"post_id", "course_code", "is_pain_point", "course_title_final", "college_list"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"post_master.csv is missing required columns: {sorted(missing)}")
    return df


def _load_course_cluster_detail(report_data_dir: Path) -> pd.DataFrame:
    path = report_data_dir / "course_cluster_detail.jsonl"
    if not path.exists():
        # Valid case for partial runs; just return empty
        return pd.DataFrame(columns=["course_code", "cluster_id", "example_post_ids"])

    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            records.append(obj)

    if not records:
        return pd.DataFrame(columns=["course_code", "cluster_id", "example_post_ids"])

    df = pd.DataFrame.from_records(records)
    # Keep only the bits we need
    needed = ["course_code", "cluster_id", "example_post_ids"]
    for col in needed:
        if col not in df.columns:
            df[col] = None
    return df[needed]


def _load_issue_course_matrix(report_data_dir: Path) -> pd.DataFrame:
    path = report_data_dir / "issue_course_matrix.csv"
    if not path.exists():
        return pd.DataFrame(columns=["normalized_issue_label", "course_code", "num_posts", "num_clusters"])
    df = pd.read_csv(path)
    # Ensure expected columns exist; fill if missing
    for col in ["normalized_issue_label", "course_code", "num_posts", "num_clusters"]:
        if col not in df.columns:
            if col in ("num_posts", "num_clusters"):
                df[col] = 0
            else:
                df[col] = None
    return df[["normalized_issue_label", "course_code", "num_posts", "num_clusters"]]


def _load_global_issues(report_data_dir: Path) -> pd.DataFrame:
    path = report_data_dir / "global_issues.csv"
    if not path.exists():
        return pd.DataFrame(columns=["global_cluster_id", "normalized_issue_label"])
    df = pd.read_csv(path)
    for col in ["global_cluster_id", "normalized_issue_label"]:
        if col not in df.columns:
            df[col] = None
    return df[["global_cluster_id", "normalized_issue_label"]]


def compute_pipeline_counts(report_data_dir: str | Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute per-course and per-college pipeline counts.

    Returns:
        (pipeline_counts_by_course, pipeline_counts_by_college)
    """
    report_data_dir = Path(report_data_dir)

    pm = _load_post_master(report_data_dir)
    course_clusters = _load_course_cluster_detail(report_data_dir)
    icm = _load_issue_course_matrix(report_data_dir)

    # ---- Course-level metadata ----
    pm["course_code"] = pm["course_code"].astype(str)
    meta = (
        pm.groupby("course_code", dropna=False)
        .agg(
            course_title=("course_title_final", "first"),
            college=("college_list", "first"),
        )
    )

    # ---- Stage 0 + Stage 1 counts ----
    # Stage 0 posts = all rows per course
    stage0_posts = (
        pm.groupby("course_code", dropna=False)["post_id"]
        .size()
        .rename("stage0_posts")
    )

    # Normalize pain flag to int 0/1
    is_pain = pm["is_pain_point"].fillna(0).astype(int)
    pm = pm.assign(is_pain_point=is_pain)

    stage1_painpoints = (
        pm.groupby("course_code", dropna=False)["is_pain_point"]
        .sum()
        .rename("stage1_painpoints")
    )
    stage1_non_painpoints = (
        stage0_posts - stage1_painpoints
    ).rename("stage1_non_painpoints")

    # No explicit Stage-1 error flags are present in post_master.csv
    stage1_error_rows = pd.Series(
        0, index=stage0_posts.index, name="stage1_error_rows"
    )

    # ---- Stage 2 counts from course_cluster_detail.jsonl ----
    if course_clusters.empty:
        stage2_clusters = pd.Series(
            0, index=stage0_posts.index, name="stage2_clusters"
        )
        stage2_clustered_posts = pd.Series(
            0, index=stage0_posts.index, name="stage2_clustered_posts"
        )
    else:
        course_clusters["course_code"] = course_clusters["course_code"].astype(str)

        stage2_clusters = (
            course_clusters.groupby("course_code", dropna=False)["cluster_id"]
            .nunique()
            .rename("stage2_clusters")
        )

        # example_post_ids is a list of post_ids per cluster; we want unique posts per course
        exploded = course_clusters[["course_code", "example_post_ids"]].explode(
            "example_post_ids"
        )
        exploded = exploded.dropna(subset=["example_post_ids"])
        stage2_clustered_posts = (
            exploded.groupby("course_code", dropna=False)["example_post_ids"]
            .nunique()
            .rename("stage2_clustered_posts")
        )

    # ---- Stage 3 counts from issue_course_matrix.csv ----
    if icm.empty:
        stage3_global_issues_in_course = pd.Series(
            0, index=stage0_posts.index, name="stage3_global_issues_in_course"
        )
        stage3_posts_with_global_issue = pd.Series(
            0, index=stage0_posts.index, name="stage3_posts_with_global_issue"
        )
    else:
        icm["course_code"] = icm["course_code"].astype(str)

        stage3_global_issues_in_course = (
            icm.groupby("course_code", dropna=False)["normalized_issue_label"]
            .nunique()
            .rename("stage3_global_issues_in_course")
        )
        stage3_posts_with_global_issue = (
            icm.groupby("course_code", dropna=False)["num_posts"]
            .sum()
            .rename("stage3_posts_with_global_issue")
        )

    # ---- Combine per-course counts ----
    course_index = meta.index

    def _align(series: pd.Series, name: str) -> pd.Series:
        s = series.copy()
        s.name = name
        # align to all known courses, filling missing with 0
        s = s.reindex(course_index, fill_value=0)
        return s

    course_counts = meta.copy()
    course_counts = course_counts.join(_align(stage0_posts, "stage0_posts"))
    course_counts = course_counts.join(_align(stage1_painpoints, "stage1_painpoints"))
    course_counts = course_counts.join(
        _align(stage1_non_painpoints, "stage1_non_painpoints")
    )
    course_counts = course_counts.join(_align(stage1_error_rows, "stage1_error_rows"))
    course_counts = course_counts.join(_align(stage2_clusters, "stage2_clusters"))
    course_counts = course_counts.join(
        _align(stage2_clustered_posts, "stage2_clustered_posts")
    )
    course_counts = course_counts.join(
        _align(stage3_global_issues_in_course, "stage3_global_issues_in_course")
    )
    course_counts = course_counts.join(
        _align(stage3_posts_with_global_issue, "stage3_posts_with_global_issue")
    )

    # Derived metric: unclustered painpoints
    course_counts["stage2_unclustered_painpoints"] = (
        course_counts["stage1_painpoints"]
        - course_counts["stage2_clustered_posts"]
    ).clip(lower=0)

    # Normalize dtypes for numeric columns
    numeric_cols = [
        "stage0_posts",
        "stage1_painpoints",
        "stage1_non_painpoints",
        "stage1_error_rows",
        "stage2_clusters",
        "stage2_clustered_posts",
        "stage2_unclustered_painpoints",
        "stage3_global_issues_in_course",
        "stage3_posts_with_global_issue",
    ]
    for col in numeric_cols:
        course_counts[col] = course_counts[col].astype(int)

    course_counts = course_counts.reset_index().rename(columns={"course_code": "course_code"})

    # Rename for final outward-facing schema
    course_counts = course_counts.rename(
        columns={
            "course_title": "course_title",
            "college": "college",
        }
    )

    # ---- College-level aggregation ----
    # Explode courses across multiple colleges
    exploded = course_counts.copy()
    exploded["college"] = exploded["college"].fillna("Unknown")
    exploded["college"] = exploded["college"].astype(str)
    exploded["college"] = exploded["college"].str.split(";")
    exploded = exploded.explode("college")
    exploded["college"] = exploded["college"].str.strip()
    exploded = exploded[exploded["college"] != ""]

    college_counts = (
        exploded.groupby("college", dropna=False)[numeric_cols]
        .sum()
        .reset_index()
    )

    return course_counts, college_counts


def _write_overview(
    report_data_dir: Path,
    course_counts: pd.DataFrame,
    college_counts: pd.DataFrame,
) -> None:
    gi_df = _load_global_issues(report_data_dir)

    total_stage0_posts = int(course_counts["stage0_posts"].sum())
    total_stage1_pain = int(course_counts["stage1_painpoints"].sum())
    total_stage2_clusters = int(course_counts["stage2_clusters"].sum())

    if not gi_df.empty:
        if "normalized_issue_label" in gi_df.columns and gi_df["normalized_issue_label"].notna().any():
            total_global_issues = int(gi_df["normalized_issue_label"].nunique())
        elif "global_cluster_id" in gi_df.columns and gi_df["global_cluster_id"].notna().any():
            total_global_issues = int(gi_df["global_cluster_id"].nunique())
        else:
            total_global_issues = int(
                course_counts["stage3_global_issues_in_course"].sum()
            )
    else:
        total_global_issues = int(
            course_counts["stage3_global_issues_in_course"].sum()
        )

    num_courses_with_pain = int((course_counts["stage1_painpoints"] > 0).sum())

    # For college count, explode as in compute_pipeline_counts
    exploded_colleges = course_counts.copy()
    exploded_colleges["college"] = exploded_colleges["college"].fillna("Unknown")
    exploded_colleges["college"] = exploded_colleges["college"].astype(str)
    exploded_colleges["college"] = exploded_colleges["college"].str.split(";")
    exploded_colleges = exploded_colleges.explode("college")
    exploded_colleges["college"] = exploded_colleges["college"].str.strip()
    exploded_colleges = exploded_colleges[exploded_colleges["college"] != ""]
    num_colleges = int(exploded_colleges["college"].nunique())

    overview_path = report_data_dir / "pipeline_counts_overview.md"
    overview_text = (
        "# Pipeline Counts Overview\n\n"
        f"**Total Stage 0 posts:** {total_stage0_posts}\n\n"
        f"**Total Stage 1 pain points:** {total_stage1_pain}\n\n"
        f"**Total Stage 2 clusters:** {total_stage2_clusters}\n\n"
        f"**Total Stage 3 global issues:** {total_global_issues}\n\n"
        f"**Courses with at least one pain point:** {num_courses_with_pain}\n\n"
        f"**Colleges represented:** {num_colleges}\n\n"
        "These counts describe how many strongly negative Reddit posts flow through "
        "each stage of the pipeline for every course and college. They are useful "
        "for understanding data coverage and the kinds of issues that appear in the "
        "corpus, but they should not be used to rank courses by difficulty or "
        "overall quality.\n"
        "The underlying dataset is a filtered, complaint-heavy subset of Reddit, "
        "and does not represent all student experiences.\n"
    )

    overview_path.write_text(overview_text, encoding="utf-8")

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build pipeline-wide Stage 0–3 counts by course and by college."
    )
    parser.add_argument(
        "--report-data-dir",
        type=str,
        default="artifacts/report_data",
        help="Directory containing Stage 4 report data (default: artifacts/report_data)",
    )
    args = parser.parse_args(argv)

    report_data_dir = Path(args.report_data_dir)
    report_data_dir.mkdir(parents=True, exist_ok=True)

    course_counts, college_counts = compute_pipeline_counts(report_data_dir)

    # Sort outputs before saving
    course_counts = course_counts.sort_values(
        ["stage1_painpoints", "stage2_clusters", "course_code"],
        ascending=[False, False, True],
    )

    college_counts = college_counts.sort_values(
        ["stage1_painpoints", "stage2_clusters", "college"],
        ascending=[False, False, True],
    )

    # Save outputs
    course_path = report_data_dir / "pipeline_counts_by_course.csv"
    college_path = report_data_dir / "pipeline_counts_by_college.csv"

    course_counts.to_csv(course_path, index=False)
    college_counts.to_csv(college_path, index=False)

    _write_overview(report_data_dir, course_counts, college_counts)


if __name__ == "__main__":
    main()