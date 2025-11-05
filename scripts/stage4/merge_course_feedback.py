# filename: scripts/merge_course_feedback.py

import argparse
import json
import csv
import logging
from pathlib import Path
from typing import Dict, List

from utils.logger import setup_logger, get_timestamp_str


def load_courses(csv_path: Path) -> Dict:
    courses = {}
    with csv_path.open(newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses[row["CourseCode"]] = {
                "CourseCode": row["CourseCode"],
                "Title": row["Title"],
                "Colleges": row.get("Colleges", "")
            }
    return courses


def load_pain_points(jsonl_path: Path) -> Dict:
    pain_points = {}
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            pp = json.loads(line)
            pain_points[pp["pain_point_id"]] = pp
    return pain_points


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", required=True, help="Path to outputs/runs/YYYY-MM-DD/")
    parser.add_argument("--course_csv", required=True, help="Path to CSV with CourseCode, Title, Colleges")
    args = parser.parse_args()

    base = Path(args.output_dir)
    logs_dir = base / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Detailed logger for this script only
    merge_logger = setup_logger("merge", filename=str(logs_dir / "merge.log"))
    # Pipeline summary logger (must be initialized by the root pipeline)
    pipeline_logger = logging.getLogger("pipeline")

    clusters_dir = base / "stage2_output"
    pain_points_path = base / "stage1" / "pain_points_stage1.jsonl"
    output_path = base / "merged" / "merged_course_feedback.json"

    pipeline_logger.info("Merge: starting...")

    courses = load_courses(Path(args.course_csv))
    pain_points = load_pain_points(pain_points_path)

    merged: List[Dict] = []
    total_files = 0
    failed_files = 0
    skipped_no_course = 0

    for path in clusters_dir.glob("*_clusters.json"):
        total_files += 1
        course_code = path.stem.replace("_clusters", "")
        if course_code not in courses:
            skipped_no_course += 1
            merge_logger.warning(json.dumps({
                "event": "course_not_in_catalog",
                "course": course_code,
                "file": str(path),
                "timestamp": get_timestamp_str()
            }))
            continue

        try:
            with path.open(encoding='utf-8') as f:
                clusters = json.load(f)
        except Exception as e:
            failed_files += 1
            merge_logger.error(json.dumps({
                "event": "load_failed",
                "course": course_code,
                "file": str(path),
                "error": f"{type(e).__name__}: {e}",
                "timestamp": get_timestamp_str()
            }))
            continue

        for cluster in clusters.get("clusters", []):
            cluster["pain_points"] = [
                pain_points[pid] for pid in cluster.get("pain_point_ids", []) if pid in pain_points
            ]

        merged.append({
            "CourseCode": course_code,
            "Title": courses[course_code]["Title"],
            "Colleges": courses[course_code]["Colleges"],
            "clusters": clusters.get("clusters", [])
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    # Detailed completion event in merge.log
    merge_logger.info(json.dumps({
        "event": "merge_complete",
        "timestamp": get_timestamp_str(),
        "output_file": str(output_path),
        "courses_merged": len(merged),
        "total_cluster_files": total_files,
        "failed_files": failed_files,
        "skipped_no_course": skipped_no_course
    }))

    # Concise summary to pipeline.log
    pipeline_logger.info(
        f"Merge complete: {len(merged)} courses merged, {total_files} files "
        f"({failed_files} failed, {skipped_no_course} skipped) — details in merge.log"
    )


if __name__ == "__main__":
    main()