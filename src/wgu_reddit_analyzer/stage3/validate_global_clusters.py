from __future__ import annotations

"""
Stage 3 global cluster validation utilities.

Validates that:
    - global_clusters.json has the expected schema and ordering.
    - cluster_global_index.csv is consistent with global_clusters.json.
    - Every cluster_id from cluster_global_index is accounted for exactly once
      (either in a global cluster or in unassigned_clusters).
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Set

from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("stage3.validate_global_clusters")


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load_cluster_global_index(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"cluster_global_index.csv not found at {path}")

    meta: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("cluster_id")
            if not cid:
                continue
            meta[cid] = row

    if not meta:
        raise RuntimeError(f"No rows loaded from {path}")

    logger.info("Loaded %d cluster rows from %s", len(meta), path)
    return meta


def validate_global_clusters(run_dir: Path) -> None:
    """
    Validate global_clusters.json and cluster_global_index.csv in a Stage-3 run dir.
    """
    global_json_path = run_dir / "global_clusters.json"
    index_csv_path = run_dir / "cluster_global_index.csv"

    if not global_json_path.is_file():
        raise FileNotFoundError(f"global_clusters.json not found at {global_json_path}")
    if not index_csv_path.is_file():
        raise FileNotFoundError(
            f"cluster_global_index.csv not found at {index_csv_path}"
        )

    cluster_meta = _load_cluster_global_index(index_csv_path)
    all_cluster_ids: Set[str] = set(cluster_meta.keys())

    obj = json.loads(global_json_path.read_text(encoding="utf-8"))
    _ensure(isinstance(obj, dict), "Top-level global_clusters.json must be an object")

    global_clusters = obj.get("global_clusters")
    _ensure(
        isinstance(global_clusters, list),
        "Field 'global_clusters' must be a list",
    )

    unassigned_clusters = obj.get("unassigned_clusters")
    _ensure(
        isinstance(unassigned_clusters, list),
        "Field 'unassigned_clusters' must be a list",
    )

    assigned_ids: Set[str] = set()
    global_ids: Set[str] = set()
    last_total_posts: int | None = None

    for gc in global_clusters:
        _ensure(isinstance(gc, dict), "Each entry in global_clusters must be an object")

        gid = gc.get("global_cluster_id")
        _ensure(
            isinstance(gid, str) and gid.strip(),
            "global_cluster_id must be a non-empty string",
        )
        _ensure(gid not in global_ids, f"Duplicate global_cluster_id '{gid}'")
        global_ids.add(gid)

        provisional_label = gc.get("provisional_label")
        normalized_issue_label = gc.get("normalized_issue_label")
        short_description = gc.get("short_description")
        member_cluster_ids = gc.get("member_cluster_ids")
        total_num_posts = gc.get("total_num_posts")
        num_clusters = gc.get("num_clusters")
        num_courses = gc.get("num_courses")

        _ensure(
            isinstance(provisional_label, str) and provisional_label.strip(),
            f"{gid}: provisional_label must be a non-empty string",
        )
        _ensure(
            isinstance(normalized_issue_label, str)
            and normalized_issue_label.strip(),
            f"{gid}: normalized_issue_label must be a non-empty string",
        )
        _ensure(
            isinstance(short_description, str) and short_description.strip(),
            f"{gid}: short_description must be a non-empty string",
        )
        _ensure(
            isinstance(member_cluster_ids, list),
            f"{gid}: member_cluster_ids must be a list",
        )
        _ensure(
            isinstance(total_num_posts, int) and total_num_posts >= 0,
            f"{gid}: total_num_posts must be a non-negative integer",
        )
        _ensure(
            isinstance(num_clusters, int) and num_clusters >= 0,
            f"{gid}: num_clusters must be a non-negative integer",
        )
        _ensure(
            isinstance(num_courses, int) and num_courses >= 0,
            f"{gid}: num_courses must be a non-negative integer",
        )

        # Check sorted by total_num_posts descending.
        if last_total_posts is None:
            last_total_posts = total_num_posts
        else:
            _ensure(
                total_num_posts <= last_total_posts,
                "global_clusters must be sorted by total_num_posts descending",
            )
            last_total_posts = total_num_posts

        # Validate member_cluster_ids.
        calc_total_posts = 0
        courses_for_gc: Set[str] = set()
        seen_members: Set[str] = set()

        for cid in member_cluster_ids:
            _ensure(
                isinstance(cid, str) and cid.strip(),
                f"{gid}: member_cluster_ids must contain only non-empty strings",
            )
            _ensure(
                cid in all_cluster_ids,
                f"{gid}: member_cluster_ids references unknown cluster_id '{cid}'",
            )
            _ensure(
                cid not in assigned_ids,
                f"cluster_id '{cid}' appears in multiple global clusters",
            )
            assigned_ids.add(cid)
            seen_members.add(cid)

            row = cluster_meta[cid]
            try:
                n_posts = int(row.get("num_posts", 0))
            except (TypeError, ValueError):
                n_posts = 0
            calc_total_posts += n_posts
            courses_for_gc.add(row.get("course_code", "").strip())

        _ensure(
            len(seen_members) == num_clusters,
            f"{gid}: num_clusters={num_clusters} but found {len(seen_members)} "
            "member_cluster_ids",
        )
        _ensure(
            calc_total_posts == total_num_posts,
            f"{gid}: total_num_posts={total_num_posts} but sum(num_posts)={calc_total_posts}",
        )
        _ensure(
            len(courses_for_gc) == num_courses,
            f"{gid}: num_courses={num_courses} but unique course_codes={len(courses_for_gc)}",
        )

    # Validate unassigned_clusters.
    unassigned_ids: Set[str] = set()
    for cid in unassigned_clusters:
        _ensure(
            isinstance(cid, str) and cid.strip(),
            "unassigned_clusters must contain only non-empty strings",
        )
        _ensure(
            cid in all_cluster_ids,
            f"unassigned_clusters references unknown cluster_id '{cid}'",
        )
        _ensure(
            cid not in assigned_ids,
            f"cluster_id '{cid}' appears both in global_clusters and unassigned_clusters",
        )
        unassigned_ids.add(cid)

    accounted_ids = assigned_ids | unassigned_ids
    _ensure(
        accounted_ids == all_cluster_ids,
        "Not all cluster_ids from cluster_global_index.csv are accounted for. "
        f"Missing={sorted(all_cluster_ids - accounted_ids)}, "
        f"extra={sorted(accounted_ids - all_cluster_ids)}",
    )

    logger.info(
        "Stage-3 global clusters validated: %d global clusters, %d assigned clusters, "
        "%d unassigned clusters.",
        len(global_clusters),
        len(assigned_ids),
        len(unassigned_ids),
    )
    print(
        f"OK: {len(global_clusters)} global clusters; "
        f"{len(assigned_ids)} assigned clusters; {len(unassigned_ids)} unassigned."
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Stage-3 global cluster outputs."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Path to a Stage-3 run directory (containing global_clusters.json).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    validate_global_clusters(run_dir=Path(args.run_dir))


if __name__ == "__main__":
    main()