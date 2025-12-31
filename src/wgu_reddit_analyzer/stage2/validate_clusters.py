from __future__ import annotations

"""
Stage 2 cluster validation utilities.

Validates that LLM-produced cluster JSON matches the canonical schema and
is internally consistent (cluster IDs, post IDs, totals, etc.).

Supports multi-cluster membership: a post_id may appear in multiple clusters.
In that case:
    - total_posts = number of UNIQUE post_ids across all clusters
    - sum(num_posts) may be > total_posts
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from wgu_reddit_analyzer.utils.logging_utils import get_logger

import logging

try:
    from wgu_reddit_analyzer.utils.logging_utils import get_logger
    logger = get_logger("stage2.validate_clusters")
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("stage2.validate_clusters")

def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_clusters_dict(
    obj: Dict[str, Any],
    course_code: str,
    valid_post_ids: Iterable[str],
    expected_total_posts: int | None = None,
) -> None:
    """
    Validate a Stage-2 cluster JSON object in-memory.

    Hard failures:
        - bad JSON shape
        - wrong course_code
        - bad cluster_id / issue_summary
        - num_posts != len(post_ids)
        - post_ids not in valid_post_ids

    Soft failures (warn only, do NOT raise):
        - expected_total_posts != unique post_ids
        - total_posts != unique post_ids  → we normalize total_posts
    """
    valid_ids: Set[str] = set(valid_post_ids)

    _ensure(isinstance(obj, dict), "Top-level JSON must be an object")

    courses = obj.get("courses")
    _ensure(
        isinstance(courses, list) and courses,
        "Field 'courses' must be a non-empty list",
    )

    course = courses[0]
    _ensure(isinstance(course, dict), "First element of 'courses' must be an object")

    cc = course.get("course_code")
    _ensure(cc == course_code, f"course_code mismatch: expected {course_code}, got {cc}")

    clusters = course.get("clusters")
    _ensure(isinstance(clusters, list), "Field 'clusters' must be a list")

    total_posts = course.get("total_posts")
    _ensure(isinstance(total_posts, int), "'total_posts' must be an integer")

    seen_post_ids: Set[str] = set()

    for cluster in clusters:
        _ensure(isinstance(cluster, dict), "Cluster entry must be an object")

        cluster_id = cluster.get("cluster_id")
        _ensure(isinstance(cluster_id, str), "cluster_id must be a string")
        prefix = f"{course_code}_"
        _ensure(
            cluster_id.startswith(prefix),
            f"cluster_id '{cluster_id}' must start with '{prefix}'",
        )

        issue_summary = cluster.get("issue_summary")
        _ensure(
            isinstance(issue_summary, str) and issue_summary.strip(),
            "issue_summary must be a non-empty string",
        )

        num_posts = cluster.get("num_posts")
        _ensure(
            isinstance(num_posts, int) and num_posts >= 0,
            "num_posts must be a non-negative integer",
        )

        post_ids = cluster.get("post_ids")
        _ensure(isinstance(post_ids, list), "post_ids must be a list")

        _ensure(
            len(post_ids) == num_posts,
            f"Cluster {cluster_id} num_posts={num_posts} but len(post_ids)={len(post_ids)}",
        )

        for pid in post_ids:
            _ensure(isinstance(pid, str), "post_ids entries must be strings")
            _ensure(
                pid in valid_ids,
                f"Cluster {cluster_id} references unknown post_id '{pid}'",
            )
            seen_post_ids.add(pid)

    # Unique post count across all clusters
    unique_post_count = len(seen_post_ids)

    # Soft check vs expected_total_posts (from painpoints CSV)
    if expected_total_posts is not None and expected_total_posts != unique_post_count:
        logger.warning(
            "Course %s: expected_total_posts=%d but unique post_ids=%d "
            "(some painpoints may be unused in clusters)",
            course_code,
            expected_total_posts,
            unique_post_count,
        )

    # Soft check vs LLM-reported total_posts; normalize instead of failing
    if total_posts != unique_post_count:
        logger.warning(
            "Course %s: total_posts=%d but unique post_ids=%d; "
            "normalizing total_posts to %d",
            course_code,
            total_posts,
            unique_post_count,
            unique_post_count,
        )
        course["total_posts"] = unique_post_count

    logger.info(
        "Cluster JSON for %s passed validation: total_posts=%d, clusters=%d",
        course_code,
        course.get("total_posts", unique_post_count),
        len(clusters),
    )


def validate_clusters_dir(
    clusters_dir: Path,
    painpoints_csv: Path,
) -> None:
    """
    Validate all cluster JSON files in a directory against the painpoints CSV.
    """
    if not clusters_dir.is_dir():
        raise FileNotFoundError(f"Clusters directory not found at {clusters_dir}")
    if not painpoints_csv.is_file():
        raise FileNotFoundError(f"Painpoints CSV not found at {painpoints_csv}")

    course_to_ids: Dict[str, Set[str]] = {}

    with painpoints_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["course_code"]
            pid = row["post_id"]
            course_to_ids.setdefault(code, set()).add(pid)

    for json_path in clusters_dir.glob("*.json"):
        course_code = json_path.stem
        valid_ids = course_to_ids.get(course_code, set())
        if not valid_ids:
            logger.warning(
                "No painpoints found for %s; skipping validation for %s",
                course_code,
                json_path,
            )
            continue

        obj = json.loads(json_path.read_text(encoding="utf-8"))
        validate_clusters_dict(
            obj,
            course_code=course_code,
            valid_post_ids=valid_ids,
            expected_total_posts=len(valid_ids),
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Stage-2 cluster JSON files."
    )
    default_clusters_dir = Path("artifacts/stage2/runs")
    if default_clusters_dir.exists():
        # pick the latest run by modified time
        latest_run_dir = max(default_clusters_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        default_clusters_dir = latest_run_dir / "clusters"
    parser.add_argument(
        "--clusters-dir",
        default=str(default_clusters_dir),
        help="Directory containing <course_code>.json cluster files.",
    )
    parser.add_argument(
        "--painpoints-csv",
        default="artifacts/stage2/painpoints_llm_friendly.csv",
        help="Path to Stage-2 painpoints CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    validate_clusters_dir(
        clusters_dir=Path(args.clusters_dir),
        painpoints_csv=Path(args.painpoints_csv),
    )


if __name__ == "__main__":
    main()