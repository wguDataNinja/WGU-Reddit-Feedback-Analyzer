from __future__ import annotations

"""
Pipeline Counts Builder

Computes deterministic Stage 0–3 summary counts from frozen artifacts and writes:
- pipeline_counts_by_course.csv
- pipeline_counts_by_college.csv
- pipeline_counts_overview.md

Notes:
- Some Stage 3 counts are issue-course memberships (not unique post counts).
- College totals may exceed corpus totals when courses map to multiple colleges.

Run from repo root:
python src/wgu_reddit_analyzer/report_data/build_pipeline_counts.py --report-data-dir artifacts/report_data
"""

import argparse
import json
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

# Logger fallback: prefer project logger; fallback to stdlib logging.
try:
    from wgu_reddit_analyzer.utils.logging_utils import get_logger  # type: ignore

    logger = get_logger(__name__)
except Exception:  # noqa: BLE001
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger(__name__)


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
        return pd.DataFrame()

    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    if not records:
        return pd.DataFrame()

    return pd.DataFrame.from_records(records)


def _load_issue_course_matrix(report_data_dir: Path) -> pd.DataFrame:
    path = report_data_dir / "issue_course_matrix.csv"
    if not path.exists():
        return pd.DataFrame(columns=["normalized_issue_label", "course_code", "num_posts", "num_clusters"])
    df = pd.read_csv(path)
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


def _infer_repo_root(report_data_dir: Path) -> Path:
    """
    Prefer repo_root/artifacts/report_data layout.
    If not found, fall back to CWD.
    """
    rd = report_data_dir.resolve()
    if rd.name == "report_data" and rd.parent.name == "artifacts":
        return rd.parent.parent
    return Path.cwd().resolve()


def _load_stage2_painpoints_table(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "artifacts" / "stage2" / "painpoints_llm_friendly.csv"
    if not path.exists():
        return pd.DataFrame(columns=["post_id", "course_code"])
    df = pd.read_csv(path, dtype=str).fillna("")
    for col in ["post_id", "course_code"]:
        if col not in df.columns:
            df[col] = ""
    df["post_id"] = df["post_id"].astype(str)
    df["course_code"] = df["course_code"].astype(str)
    df = df[(df["post_id"].str.strip() != "") & (df["course_code"].str.strip() != "")]
    return df[["post_id", "course_code"]]


def _detect_membership_column(df: pd.DataFrame) -> Optional[str]:
    """
    If course_cluster_detail has a true membership list per cluster, use it.
    Otherwise return None.
    """
    candidates = [
        "post_ids",
        "member_post_ids",
        "cluster_post_ids",
        "all_post_ids",
        "post_id_list",
        "members",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def compute_pipeline_counts(report_data_dir: str | Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute per-course and per-college pipeline counts.

    Returns:
        (pipeline_counts_by_course, pipeline_counts_by_college)
    """
    report_data_dir = Path(report_data_dir)
    repo_root = _infer_repo_root(report_data_dir)

    pm = _load_post_master(report_data_dir)
    course_clusters = _load_course_cluster_detail(report_data_dir)
    icm = _load_issue_course_matrix(report_data_dir)

    # ---- Course-level metadata (deterministic) ----
    pm["course_code"] = pm["course_code"].astype(str)
    pm["post_id"] = pm["post_id"].astype(str)
    pm = pm.sort_values(["course_code", "post_id"], kind="mergesort")

    meta = pm.groupby("course_code", dropna=False).agg(
        course_title=("course_title_final", "first"),
        college=("college_list", "first"),
    )

    # ---- Stage 0 + Stage 1 counts ----
    stage0_posts = pm.groupby("course_code", dropna=False)["post_id"].size().rename("stage0_posts")

    is_pain = pm["is_pain_point"].fillna(0).astype(int)
    pm = pm.assign(is_pain_point=is_pain)

    stage1_painpoints = pm.groupby("course_code", dropna=False)["is_pain_point"].sum().rename("stage1_painpoints")
    stage1_non_painpoints = (stage0_posts - stage1_painpoints).rename("stage1_non_painpoints")

    # post_master.csv does not carry parse/schema/LLM failure flags; keep a stable placeholder column.
    stage1_error_rows = pd.Series(0, index=stage0_posts.index, name="stage1_error_rows")

    # ---- Stage 2 counts (true counts; no example-based proxies) ----
    stage2_table = _load_stage2_painpoints_table(repo_root)

    stage2_posts_included_for_clustering = (
        stage2_table.groupby("course_code", dropna=False)["post_id"]
        .nunique()
        .rename("stage2_posts_included_for_clustering")
    )

    if course_clusters.empty:
        stage2_clusters = pd.Series(0, index=stage0_posts.index, name="stage2_clusters")
    else:
        course_clusters = course_clusters.copy()
        if "course_code" not in course_clusters.columns:
            course_clusters["course_code"] = None
        if "cluster_id" not in course_clusters.columns:
            course_clusters["cluster_id"] = None

        course_clusters["course_code"] = course_clusters["course_code"].astype(str)

        # Counting clusters is valid if each record corresponds to a real cluster id.
        stage2_clusters = course_clusters.groupby("course_code", dropna=False)["cluster_id"].nunique().rename("stage2_clusters")

        # If a true membership column exists, we can cross-check counts, but we do not
        # use example_post_ids for published metrics.
        membership_col = _detect_membership_column(course_clusters)
        if membership_col is not None:
            exploded = course_clusters[["course_code", membership_col]].explode(membership_col)
            exploded = exploded.dropna(subset=[membership_col])
            exploded[membership_col] = exploded[membership_col].astype(str)
            _stage2_posts_from_membership = (
                exploded.groupby("course_code", dropna=False)[membership_col]
                .nunique()
                .rename("stage2_posts_from_membership_debug")
            )
            _ = _stage2_posts_from_membership  # intentionally unused (debug-only)

    # ---- Stage 3 counts from issue_course_matrix.csv ----
    if icm.empty:
        stage3_global_issues_in_course = pd.Series(0, index=stage0_posts.index, name="stage3_global_issues_in_course")
        stage3_issue_course_post_memberships = pd.Series(
            0, index=stage0_posts.index, name="stage3_issue_course_post_memberships"
        )
    else:
        icm = icm.copy()
        icm["course_code"] = icm["course_code"].astype(str)

        stage3_global_issues_in_course = (
            icm.groupby("course_code", dropna=False)["normalized_issue_label"]
            .nunique()
            .rename("stage3_global_issues_in_course")
        )

        # This is a membership total across issue-course rows, not a unique-post count.
        stage3_issue_course_post_memberships = (
            icm.groupby("course_code", dropna=False)["num_posts"]
            .sum()
            .rename("stage3_issue_course_post_memberships")
        )

    # ---- Combine per-course counts ----
    course_index = meta.index

    def _align(series: pd.Series, name: str) -> pd.Series:
        s = series.copy()
        s.name = name
        return s.reindex(course_index, fill_value=0)

    course_counts = meta.copy()
    course_counts = course_counts.join(_align(stage0_posts, "stage0_posts"))
    course_counts = course_counts.join(_align(stage1_painpoints, "stage1_painpoints"))
    course_counts = course_counts.join(_align(stage1_non_painpoints, "stage1_non_painpoints"))
    course_counts = course_counts.join(_align(stage1_error_rows, "stage1_error_rows"))
    course_counts = course_counts.join(_align(stage2_clusters, "stage2_clusters"))
    course_counts = course_counts.join(
        _align(stage2_posts_included_for_clustering, "stage2_posts_included_for_clustering")
    )
    course_counts = course_counts.join(_align(stage3_global_issues_in_course, "stage3_global_issues_in_course"))
    course_counts = course_counts.join(
        _align(stage3_issue_course_post_memberships, "stage3_issue_course_post_memberships")
    )

    course_counts["stage2_unclustered_painpoints"] = (
        course_counts["stage1_painpoints"] - course_counts["stage2_posts_included_for_clustering"]
    ).clip(lower=0)

    numeric_cols = [
        "stage0_posts",
        "stage1_painpoints",
        "stage1_non_painpoints",
        "stage1_error_rows",
        "stage2_clusters",
        "stage2_posts_included_for_clustering",
        "stage2_unclustered_painpoints",
        "stage3_global_issues_in_course",
        "stage3_issue_course_post_memberships",
    ]
    for col in numeric_cols:
        course_counts[col] = course_counts[col].astype(int)

    course_counts = course_counts.reset_index().rename(columns={"course_code": "course_code"})

    output_cols = ["course_code", "course_title", "college"] + numeric_cols
    course_counts = course_counts[output_cols]

    # ---- College-level aggregation ----
    exploded = course_counts.copy()
    exploded["college"] = exploded["college"].fillna("Unknown").astype(str)
    exploded["college"] = exploded["college"].str.split(";")
    exploded = exploded.explode("college")
    exploded["college"] = exploded["college"].astype(str).str.strip()
    exploded = exploded[exploded["college"] != ""]

    college_counts = exploded.groupby("college", dropna=False)[numeric_cols].sum().reset_index()
    college_counts = college_counts[["college"] + numeric_cols]

    return course_counts, college_counts


def _write_overview(
    report_data_dir: Path,
    course_counts: pd.DataFrame,
) -> None:
    gi_df = _load_global_issues(report_data_dir)
    icm = _load_issue_course_matrix(report_data_dir)

    total_stage0_posts = int(course_counts["stage0_posts"].sum())
    total_stage1_pain = int(course_counts["stage1_painpoints"].sum())
    total_stage2_clusters = int(course_counts["stage2_clusters"].sum())

    # Prefer a true corpus-wide unique count of global issues.
    if not gi_df.empty:
        if "normalized_issue_label" in gi_df.columns and gi_df["normalized_issue_label"].notna().any():
            total_global_issues = int(gi_df["normalized_issue_label"].nunique())
        elif "global_cluster_id" in gi_df.columns and gi_df["global_cluster_id"].notna().any():
            total_global_issues = int(gi_df["global_cluster_id"].nunique())
        else:
            total_global_issues = int(icm["normalized_issue_label"].nunique()) if not icm.empty else 0
    else:
        total_global_issues = int(icm["normalized_issue_label"].nunique()) if not icm.empty else 0

    num_courses_with_pain = int((course_counts["stage1_painpoints"] > 0).sum())

    exploded_colleges = course_counts.copy()
    exploded_colleges["college"] = exploded_colleges["college"].fillna("Unknown").astype(str)
    exploded_colleges["college"] = exploded_colleges["college"].str.split(";")
    exploded_colleges = exploded_colleges.explode("college")
    exploded_colleges["college"] = exploded_colleges["college"].astype(str).str.strip()
    exploded_colleges = exploded_colleges[exploded_colleges["college"] != ""]
    num_colleges = int(exploded_colleges["college"].nunique())

    overview_path = report_data_dir / "pipeline_counts_overview.md"
    overview_text = (
        "# Pipeline Counts Overview\n\n"
        f"Total Stage 0 posts: {total_stage0_posts}\n\n"
        f"Total Stage 1 pain points: {total_stage1_pain}\n\n"
        f"Total Stage 2 clusters: {total_stage2_clusters}\n\n"
        f"Total Stage 3 global issues: {total_global_issues}\n\n"
        f"Courses with at least one pain point: {num_courses_with_pain}\n\n"
        f"Colleges represented: {num_colleges}\n\n"
        "These counts describe how many posts flow through each stage of the pipeline for every "
        "course and college. They are useful for understanding data coverage and the kinds of "
        "issues that appear in the corpus, but they should not be used to rank courses by "
        "difficulty or overall quality.\n"
        "The underlying dataset is a filtered, complaint-heavy subset of Reddit and does not "
        "represent all student experiences.\n"
    )
    overview_path.write_text(overview_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build pipeline-wide Stage 0–3 counts by course and by college.")
    parser.add_argument(
        "--report-data-dir",
        type=str,
        default="artifacts/report_data",
        help="Directory containing report data inputs and outputs (default: artifacts/report_data)",
    )
    args = parser.parse_args(argv)

    report_data_dir = Path(args.report_data_dir)
    report_data_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Building pipeline counts in %s", str(report_data_dir))

    course_counts, college_counts = compute_pipeline_counts(report_data_dir)

    course_counts = course_counts.sort_values(
        ["stage1_painpoints", "stage2_clusters", "course_code"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    college_counts = college_counts.sort_values(
        ["stage1_painpoints", "stage2_clusters", "college"],
        ascending=[False, False, True],
        kind="mergesort",
    )

    course_path = report_data_dir / "pipeline_counts_by_course.csv"
    college_path = report_data_dir / "pipeline_counts_by_college.csv"

    course_counts.to_csv(course_path, index=False)
    college_counts.to_csv(college_path, index=False)

    _write_overview(report_data_dir, course_counts)

    logger.info("Wrote %s", str(course_path))
    logger.info("Wrote %s", str(college_path))
    logger.info("Wrote %s", str(report_data_dir / "pipeline_counts_overview.md"))


if __name__ == "__main__":
    main()