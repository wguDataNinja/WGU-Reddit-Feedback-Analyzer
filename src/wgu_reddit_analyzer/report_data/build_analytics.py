"""
Build the report_data layer for WGU Reddit Analyzer.

This script merges Stage 0, Stage 2, and Stage 3 artifacts plus course metadata
into a small set of clean tables under artifacts/report_data/, which power
human-facing reports and any future site/GUI.

Outputs (all unfiltered, full data):

- artifacts/report_data/post_master.csv
- artifacts/report_data/course_summary.csv
- artifacts/report_data/course_cluster_detail.jsonl
- artifacts/report_data/global_issues.csv
- artifacts/report_data/issue_course_matrix.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def project_root() -> Path:
    """Return the repo root (one level above src/)."""
    return Path(__file__).resolve().parents[3]


def ensure_dir(path: Path) -> None:
    """Create directory if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_stage0_filtered(artifacts_dir: Path) -> pd.DataFrame:
    """Load the locked Stage 0 filtered posts."""
    path = artifacts_dir / "stage0_filtered_posts.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Missing Stage 0 file: {path}")
    df = pd.read_json(path, lines=True)
    if "post_id" not in df.columns:
        raise ValueError("stage0_filtered_posts.jsonl missing 'post_id'")
    return df


def load_painpoints_stage2(artifacts_dir: Path) -> pd.DataFrame:
    """Load Stage 2 pain point classifier outputs."""
    path = artifacts_dir / "stage2" / "painpoints_llm_friendly.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing Stage 2 painpoint file: {path}")
    df = pd.read_csv(path)
    required_cols = {"post_id", "course_code", "root_cause_summary", "pain_point_snippet"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Stage 2 painpoint file missing columns: {missing}")
    return df


def load_stage3_preprocessed(preprocessed_dir: Path) -> pd.DataFrame:
    """Load Stage 2/3 preprocessed clusters (clusters_llm.csv)."""
    path = preprocessed_dir / "clusters_llm.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing clusters_llm.csv in {preprocessed_dir}")
    df = pd.read_csv(path)
    required_cols = {"cluster_id", "issue_summary", "course_code", "course_title", "num_posts"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"clusters_llm.csv missing columns: {missing}")
    return df


def load_stage3_runs(run_dir: Path) -> Dict[str, Any]:
    """
    Load Stage 3 global clustering outputs:
    - cluster_global_index.csv
    - post_global_index.csv
    - global_clusters.json
    """
    cluster_global_path = run_dir / "cluster_global_index.csv"
    post_global_path = run_dir / "post_global_index.csv"
    global_clusters_path = run_dir / "global_clusters.json"

    for p in [cluster_global_path, post_global_path, global_clusters_path]:
        if not p.exists():
            raise FileNotFoundError(f"Missing Stage 3 file: {p}")

    df_cluster_global = pd.read_csv(cluster_global_path)
    df_post_global = pd.read_csv(post_global_path)
    with global_clusters_path.open("r", encoding="utf-8") as f:
        global_clusters = json.load(f)

    return {
        "cluster_global": df_cluster_global,
        "post_global": df_post_global,
        "global_clusters_raw": global_clusters,
    }


def load_course_metadata(data_dir: Path) -> pd.DataFrame:
    """Load course metadata (code, title, college)."""
    path = data_dir / "course_list_with_college.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing course metadata file: {path}")
    df = pd.read_csv(path)
    required_cols = {"CourseCode", "Title", "Colleges"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"course_list_with_college.csv missing columns: {missing}")
    return df


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_post_master(
    df_stage0: pd.DataFrame,
    df_pp: pd.DataFrame,
    df_post_global: pd.DataFrame,
    df_cluster_global: pd.DataFrame,
    df_courses: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the joined post×cluster table.

    One row per (post_id, cluster_id) when a post is assigned to multiple clusters.
    This is the raw intermediate used for course/global aggregations.

    A separate collapse step will derive the true post-level post_master.csv.
    """
    df_pp = df_pp.copy()
    df_pp["is_pain_point"] = 1

    # Merge Stage 0 with pain point outputs (left join: keep all negative posts)
    df = df_stage0.merge(
        df_pp[["post_id", "root_cause_summary", "pain_point_snippet", "is_pain_point"]],
        on="post_id",
        how="left",
    )
    df["is_pain_point"] = df["is_pain_point"].fillna(0).astype(int)

    # Merge in post_global_index to attach cluster_id + global_cluster_id + course_title
    df = df.merge(
        df_post_global[["post_id", "cluster_id", "global_cluster_id", "course_code", "course_title"]],
        on="post_id",
        how="left",
        suffixes=("", "_from_post_index"),
    )

    # Merge cluster_global_index to attach normalized_issue_label and provisional_label
    df = df.merge(
        df_cluster_global[
            [
                "cluster_id",
                "global_cluster_id",
                "provisional_label",
                "normalized_issue_label",
            ]
        ],
        on=["cluster_id", "global_cluster_id"],
        how="left",
    )

    # Attach course metadata (college, canonical catalog title)
    df = df.merge(
        df_courses.rename(
            columns={
                "CourseCode": "course_code",
                "Title": "course_title_catalog",
                "Colleges": "college_list",
            }
        ),
        on="course_code",
        how="left",
    )

    # Choose a single course title field
    def choose_title(row):
        if pd.notna(row.get("course_title")):
            return row["course_title"]
        if pd.notna(row.get("course_title_catalog")):
            return row["course_title_catalog"]
        return None

    df["course_title_final"] = df.apply(choose_title, axis=1)

    return df


def collapse_to_post_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse a post×cluster table to one row per post_id.

    - Non-cluster fields: take first (identical across clusters for a post).
    - Cluster / issue fields: aggregate unique values into semicolon-joined strings.
    """
    df = df.copy()

    cluster_cols = [
        "cluster_id",
        "global_cluster_id",
        "normalized_issue_label",
        "provisional_label",
    ]

    def uniq_join(series: pd.Series) -> str:
        vals = [str(v) for v in series.dropna().unique() if str(v) != ""]
        if not vals:
            return ""
        return ";".join(sorted(vals))

    agg: Dict[str, Any] = {}
    for col in df.columns:
        if col == "post_id":
            continue
        if col in cluster_cols:
            agg[col] = uniq_join
        else:
            agg[col] = "first"

    collapsed = df.groupby("post_id", as_index=False).agg(agg)
    return collapsed


def build_course_summary(df_post_cluster: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the post×cluster table into per-course summary metrics."""
    df = df_post_cluster.copy()

    # Base summary: course title, colleges, total negative posts (distinct posts)
    base = (
        df.groupby("course_code", dropna=True)
        .agg(
            course_title_final=("course_title_final", "first"),
            college_list=("college_list", "first"),
            total_negative_posts=("post_id", pd.Series.nunique),
        )
        .reset_index()
    )

    # Pain-point counts and distinct clusters
    pain = df[df["is_pain_point"] == 1].copy()

    pain_counts = (
        pain.groupby("course_code", dropna=True)
        .agg(
            total_pain_point_posts=("post_id", pd.Series.nunique),
            num_clusters=("cluster_id", pd.Series.nunique),
        )
        .reset_index()
    )

    summary = base.merge(pain_counts, on="course_code", how="left")
    summary["total_pain_point_posts"] = summary["total_pain_point_posts"].fillna(0).astype(int)
    summary["num_clusters"] = summary["num_clusters"].fillna(0).astype(int)

    # Top 3 normalized_issue_labels per course (based on distinct posts)
    if "normalized_issue_label" in pain.columns:
        top_issues = (
            pain.dropna(subset=["normalized_issue_label"])
            .groupby(["course_code", "normalized_issue_label"])["post_id"]
            .nunique()
            .reset_index(name="count")
        )

        top_agg = (
            top_issues
            .sort_values(["course_code", "count"], ascending=[True, False])
            .groupby("course_code")["normalized_issue_label"]
            .apply(lambda s: ", ".join(s.astype(str).head(3)))
            .reset_index(name="top_issue_labels")
        )
        summary = summary.merge(top_agg, on="course_code", how="left")
    else:
        summary["top_issue_labels"] = ""

    return summary


def build_course_cluster_detail(
    df_post_cluster: pd.DataFrame,
    df_clusters_llm: pd.DataFrame,
    course_summary: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Build per-(course, cluster) detail records from the post×cluster table.

    One record per (course_code, cluster_id) with:
    - cluster summaries
    - normalized issue label
    - post counts and share of course pain points
    - example post_ids and snippets
    """
    df = df_post_cluster[
        (df_post_cluster["is_pain_point"] == 1) & df_post_cluster["cluster_id"].notna()
    ].copy()

    # Attach issue_summary from clusters_llm.csv
    df_clusters_llm = df_clusters_llm.rename(columns={"issue_summary": "cluster_issue_summary"})
    df = df.merge(
        df_clusters_llm[["cluster_id", "cluster_issue_summary"]],
        on="cluster_id",
        how="left",
    )

    # Attach per-course total pain points to compute shares
    course_pain_counts = course_summary.set_index("course_code")["total_pain_point_posts"].to_dict()

    cluster_groups = df.groupby(["course_code", "cluster_id"], dropna=True)
    records: List[Dict[str, Any]] = []

    for (course_code, cluster_id), sub in cluster_groups:
        total_pp_course = course_pain_counts.get(course_code, 0) or 1  # avoid division by zero
        num_posts = len(sub)

        example_rows = sub.head(3)
        example_post_ids = example_rows["post_id"].tolist()
        snippet_col = "pain_point_snippet" if "pain_point_snippet" in sub.columns else "selftext"
        example_snippets = example_rows[snippet_col].fillna("").tolist()

        records.append(
            {
                "course_code": course_code,
                "course_title": sub["course_title_final"].iloc[0],
                "cluster_id": cluster_id,
                "cluster_issue_summary": sub["cluster_issue_summary"].iloc[0],
                "normalized_issue_label": sub["normalized_issue_label"].iloc[0],
                "provisional_label": sub["provisional_label"].iloc[0],
                "num_posts": num_posts,
                "share_of_course_pain_points": num_posts / float(total_pp_course),
                "example_post_ids": example_post_ids,
                "example_snippets": example_snippets,
            }
        )

    return records


def build_global_issues(global_clusters_raw: Dict[str, Any]) -> pd.DataFrame:
    """Flatten global_clusters.json into a table of normalized issues."""
    rows = []
    for gc in global_clusters_raw.get("global_clusters", []):
        rows.append(
            {
                "global_cluster_id": gc.get("global_cluster_id"),
                "normalized_issue_label": gc.get("normalized_issue_label"),
                "provisional_label": gc.get("provisional_label"),
                "short_description": gc.get("short_description"),
                "total_num_posts": gc.get("total_num_posts"),
                "num_clusters": gc.get("num_clusters"),
                "num_courses": gc.get("num_courses"),
            }
        )
    return pd.DataFrame(rows)


def build_issue_course_matrix(df_post_cluster: pd.DataFrame) -> pd.DataFrame:
    """
    Build normalized issue x course matrix from the post×cluster table.

    One row per (normalized_issue_label, course_code) with:
    - num_posts (distinct posts)
    - num_clusters (distinct clusters)
    """
    df = df_post_cluster[
        (df_post_cluster["is_pain_point"] == 1) & df_post_cluster["normalized_issue_label"].notna()
    ].copy()

    agg = (
        df.groupby(["normalized_issue_label", "course_code"], dropna=True)
        .agg(
            num_posts=("post_id", pd.Series.nunique),
            num_clusters=("cluster_id", pd.Series.nunique),
        )
        .reset_index()
    )

    return agg


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    """Write a list of dicts as JSON Lines."""
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build report_data tables for WGU Reddit Analyzer."
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Path to artifacts/ root (default: <repo_root>/artifacts)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to data/ root (default: <repo_root>/data)",
    )
    parser.add_argument(
        "--stage3-preprocessed-dir",
        type=Path,
        required=True,
        help="Path to Stage 2/3 preprocessed directory containing clusters_llm.csv",
    )
    parser.add_argument(
        "--stage3-run-dir",
        type=Path,
        required=True,
        help=(
            "Path to Stage 3 run directory containing "
            "cluster_global_index.csv, post_global_index.csv, and global_clusters.json"
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Entry point: build all report_data tables."""
    args = parse_args()
    root = project_root()

    artifacts_dir = args.artifacts_dir or (root / "artifacts")
    data_dir = args.data_dir or (root / "data")
    preprocessed_dir = args.stage3_preprocessed_dir
    run_dir = args.stage3_run_dir

    report_data_dir = artifacts_dir / "report_data"
    ensure_dir(report_data_dir)

    # Load inputs
    df_stage0 = load_stage0_filtered(artifacts_dir)
    df_pp = load_painpoints_stage2(artifacts_dir)
    df_clusters_llm = load_stage3_preprocessed(preprocessed_dir)
    stage3_runs = load_stage3_runs(run_dir)
    df_cluster_global = stage3_runs["cluster_global"]
    df_post_global = stage3_runs["post_global"]
    global_clusters_raw = stage3_runs["global_clusters_raw"]
    df_courses = load_course_metadata(data_dir)

    # Build post×cluster intermediate
    df_post_cluster = build_post_master(
        df_stage0=df_stage0,
        df_pp=df_pp,
        df_post_global=df_post_global,
        df_cluster_global=df_cluster_global,
        df_courses=df_courses,
    )

    # Collapse to true post-level master for reporting
    df_master = collapse_to_post_level(df_post_cluster)
    df_master["schema_version"] = SCHEMA_VERSION
    df_master.to_csv(report_data_dir / "post_master.csv", index=False)

    # Build course_summary (uses post×cluster for clusters, distinct posts for counts)
    course_summary = build_course_summary(df_post_cluster)
    course_summary["schema_version"] = SCHEMA_VERSION
    course_summary.to_csv(report_data_dir / "course_summary.csv", index=False)

    # Build course_cluster_detail from post×cluster table
    cluster_detail_records = build_course_cluster_detail(
        df_post_cluster=df_post_cluster,
        df_clusters_llm=df_clusters_llm,
        course_summary=course_summary,
    )
    write_jsonl(report_data_dir / "course_cluster_detail.jsonl", cluster_detail_records)

    # Build global_issues
    df_global_issues = build_global_issues(global_clusters_raw)
    df_global_issues["schema_version"] = SCHEMA_VERSION
    df_global_issues.to_csv(report_data_dir / "global_issues.csv", index=False)

    # Build issue_course_matrix from post×cluster table
    df_issue_course = build_issue_course_matrix(df_post_cluster)
    df_issue_course["schema_version"] = SCHEMA_VERSION
    df_issue_course.to_csv(report_data_dir / "issue_course_matrix.csv", index=False)

    print("Report data build complete. Outputs written to:", report_data_dir)


if __name__ == "__main__":
    main()