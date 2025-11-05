# filename: scripts/run_daily_pipeline.py

import subprocess
import datetime
import argparse
import sys
import traceback
import json
import time
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.logger import get_timestamp_str
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")
def estimate_tokens(text: str) -> int:
    return len(enc.encode(text))


def run(cmd: list[str], stage_name: str, dry_run: bool, stats: Dict[str, Any]) -> None:
    print(f"\n [{stage_name}] Running: {' '.join(str(c) for c in cmd)}")
    start = time.time()
    if dry_run:
        print(" Dry run mode, skipping actual execution.")
        return
    try:
        subprocess.check_call(cmd)
        elapsed = round(time.time() - start, 1)
        stats["stages"][stage_name] = {
            "status": "success",
            "start_time": get_timestamp_str(),
            "end_time": get_timestamp_str(),
            "seconds": elapsed
        }
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        stats["stages"][stage_name] = {
            "status": "failed",
            "start_time": get_timestamp_str(),
            "end_time": get_timestamp_str(),
            "seconds": elapsed,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        raise

def collect_stats(output_dir: Path) -> Dict[str, Any]:
    stats = defaultdict(int)
    pain_point_path = output_dir / "stage1" / "pain_points_stage1.jsonl"
    cluster_dir = output_dir / "stage2_output"
    updated_courses_path = output_dir / "stage1" / "updated_courses.txt"

    # Stage 1
    if pain_point_path.exists():
        with pain_point_path.open() as f:
            lines = f.readlines()
            stats["pain_points_extracted"] = len(lines)
            post_ids = set()
            total_tokens = 0
            for line in lines:
                item = json.loads(line)
                post_ids.add(item["post_id"])
                total_tokens += estimate_tokens(item.get("quoted_text", "") + " " + item.get("pain_point_summary", ""))
            stats["posts_processed"] = len(post_ids)
            stats["pain_points_per_post"] = round(stats["pain_points_extracted"] / max(len(post_ids), 1), 2)
            stats["tokens_processed_stage1"] = total_tokens

    # Stage 2
    if updated_courses_path.exists():
        with updated_courses_path.open() as f:
            updated_courses = [line.strip() for line in f if line.strip()]
        stats["updated_courses"] = len(updated_courses)

        # check if course was new (not in cache yet)
        cache_dir = Path("old/outputs/stage2_cache/course_inputs")
        stats["new_courses"] = sum(
            1 for course in updated_courses if not (cache_dir / f"{course}.jsonl").exists()
        )

    cluster_sizes = []
    total_cluster_tokens = 0
    if cluster_dir.exists():
        for f in cluster_dir.glob("*_clusters.json"):
            with f.open() as fp:
                data = json.load(fp)
                clusters = data.get("clusters", [])
                stats["clusters_created"] += len(clusters)
                cluster_sizes.extend(len(c.get("pain_point_ids", [])) for c in clusters)
                total_cluster_tokens += sum(
                    estimate_tokens(c.get("title", "") + " " + c.get("root_cause_summary", ""))
                    for c in clusters
                )
        if cluster_sizes:
            stats["avg_cluster_size"] = round(sum(cluster_sizes) / len(cluster_sizes), 2)
        stats["tokens_processed_stage2"] = total_cluster_tokens

    return stats


def write_log(log_file: Path, stats: Dict[str, Any]) -> None:
    success_count = sum(1 for s in stats["stages"].values() if s["status"] == "success")
    total = len(stats["stages"])
    pipeline_health = (
        "healthy" if success_count == total
        else "partial" if success_count > 0
        else "failed"
    )

    final_log = {
        "pipeline_health": pipeline_health,
        "last_run_time": get_timestamp_str(),
        "total_runtime_sec": round(time.time() - stats["start_time"], 1),
        "stages": stats["stages"],
        "today_stats": stats["today_stats"],
    }

    # Include updated courses if they exist
    updated_courses_file = log_file.parent.parent / "stage1" / "updated_courses.txt"
    if updated_courses_file.exists():
        final_log["updated_courses"] = [
            c.strip() for c in updated_courses_file.read_text().splitlines() if c.strip()
        ]

    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(json.dumps(final_log, indent=2))
    print(f"\n Pipeline complete. Log saved to: {log_file}")


def main():
    today = datetime.date.today().isoformat()
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default=f"outputs/runs/{today}")
    parser.add_argument("--log_file", default=f"outputs/runs/{today}/logs/pipeline_run.log")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    out = Path(args.output_dir)
    log_file = Path(args.log_file)
    out.mkdir(parents=True, exist_ok=True)

    stats = {
        "start_time": time.time(),
        "stages": {},
        "today_stats": {}
    }

    try:
        # Stage 1
        cmd = [
            "python", "-m", "scripts.stage1.step04_run_stage1",
            "--output_dir", str(out)
        ]
        if args.limit:
            cmd += ["--limit", str(args.limit)]
        run(cmd, "stage1_classify", args.dry_run, stats)

        # Group + per-course change detection
        run([
            "python", "-m", "scripts.stage2.step01_group_by_course",
            "--input", str(out / "stage1" / "pain_points_stage1.jsonl"),
            "--cache_dir", "outputs/stage2_cache/course_inputs/",
            "--output_dir", str(out / "stage2_input"),
            "--emit_updated_list", str(out / "stage1" / "updated_courses.txt")
        ], "group_and_cache", args.dry_run, stats)

        # Only run Stage 2 if there are updated courses
        updated_courses_file = out / "stage1" / "updated_courses.txt"
        should_run_stage2 = updated_courses_file.exists() and updated_courses_file.read_text().strip()

        if should_run_stage2:
            run([
                "python", "-m", "scripts.stage2.step05_run_stage2",
                "--output_dir", str(out),
                "--courses_file", str(updated_courses_file)
            ], "cluster", args.dry_run, stats)
        else:
            print("No updated courses — skipping Stage 2 (cluster)")

        # Merge + PDFs
        run([
            "python", "-m", "scripts.merge_course_feedback",
            "--output_dir", str(out),
            "--course_csv", "data/2025_06_course_list_with_college.csv"
        ], "merge", args.dry_run, stats)

        run([
            "python", "-m", "scripts.batch_generate_pdfs",
            "--output_dir", str(out),
            "--course_csv", "data/2025_06_course_list_with_college.csv"
        ], "pdf_generation", args.dry_run, stats)

        # Optional GH release
        if not args.dry_run:
            run([
                "gh", "release", "create",
                f"feedback-{today}",
                str(out / "pdfs" / "*.pdf"),
                "--title", f"Reddit Feedback for {today}"
            ], "gh_release", args.dry_run, stats)

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}", file=sys.stderr)

    # ✅ Always run this regardless of failure
    stats["today_stats"] = collect_stats(out)
    write_log(log_file, stats)


if __name__ == "__main__":
    main()