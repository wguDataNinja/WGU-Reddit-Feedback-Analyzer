# src/wgu_reddit_analyzer/stage3/preprocess_clusters.py

import argparse
import csv
import json
from pathlib import Path


def preprocess_clusters(stage2_run_dir: Path, out_path: Path) -> None:
    clusters_dir = stage2_run_dir / "clusters"
    rows = []

    for json_path in sorted(clusters_dir.glob("*.json")):
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for course_obj in data.get("courses", []):
            course_code = course_obj.get("course_code")
            course_title = course_obj.get("course_title")
            for cluster in course_obj.get("clusters", []):
                rows.append({
                    "cluster_id": cluster.get("cluster_id"),
                    "issue_summary": cluster.get("issue_summary"),
                    "course_code": course_code,
                    "course_title": course_title,
                    "num_posts": cluster.get("num_posts"),
                })

    # optional stable ordering
    rows.sort(key=lambda r: (r["course_code"] or "", r["cluster_id"] or ""))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["cluster_id", "issue_summary", "course_code", "course_title", "num_posts"]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage2-run-dir",
        required=True,
        help="Path to the Stage 2 run directory (contains clusters/)",
    )
    parser.add_argument(
        "--out-path",
        required=True,
        help="Output CSV path for LLM-friendly clusters",
    )
    args = parser.parse_args()

    stage2_run_dir = Path(args.stage2_run_dir)
    out_path = Path(args.out_path)

    preprocess_clusters(stage2_run_dir, out_path)


if __name__ == "__main__":
    main()