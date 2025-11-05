# scripts/stage2/step01_group_by_course.py

import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.logger import setup_logger, get_timestamp_str
from utils.jsonl_io import read_jsonl, write_jsonl

# Paths
INPUT_PATH = Path("outputs/stage1/pain_points_stage1.jsonl")
OUTPUT_DIR = Path("outputs/stage2/pain_points_by_course")
CACHE_DIR = Path("outputs/stage2_cache/course_inputs")
UPDATED_LIST = Path("outputs/stage2_cache/updated_courses.txt")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

logger = setup_logger("group_by_course", filename="stage2.log", to_console=True)


def group_by_course(input_path: Path, output_dir: Path, cache_dir: Path, updated_list_path: Path) -> None:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    updated_courses = []

    for line in input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            course = entry.get("course")
            if course:
                grouped[course].append(entry)
        except json.JSONDecodeError:
            continue

    for course, records in grouped.items():
        out_path = output_dir / f"{course}.jsonl"
        cache_path = cache_dir / f"{course}.count"

        # Check if count changed
        old_count = int(cache_path.read_text()) if cache_path.exists() else -1
        new_count = len(records)
        if new_count != old_count:
            updated_courses.append(course)

        # Write updated records and update cache
        write_jsonl(records, out_path)
        cache_path.write_text(str(new_count))

    # Write updated courses list
    if updated_courses:
        updated_list_path.write_text("\n".join(updated_courses))
        logger.info(f"Updated courses: {updated_courses}")
    else:
        if updated_list_path.exists():
            updated_list_path.unlink()
        logger.info("No updated courses")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Group pain points by course and detect changes")
    parser.add_argument("--input", required=True, help="Path to pain_points_stage1.jsonl")
    parser.add_argument("--output_dir", required=True, help="Output dir for course-level pain points")
    parser.add_argument("--cache_dir", required=True, help="Cache dir for course input counts")
    parser.add_argument("--emit_updated_list", required=True, help="Path to write updated_courses.txt")
    args = parser.parse_args()

    group_by_course(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        cache_dir=Path(args.cache_dir),
        updated_list_path=Path(args.emit_updated_list),
    )