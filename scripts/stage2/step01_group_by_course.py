# filename: scripts/stage2/step01_group_by_course.py

import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
import json


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.logger import setup_logger, get_timestamp_str
from utils.jsonl_io import read_jsonl, write_jsonl
from utils.archive_ops import move_to_archive
from utils.paths import project_path

# Paths
INPUT_PATH = project_path / "outputs" / "stage1" / "pain_points_stage1.jsonl"
OUTPUT_DIR = project_path / "outputs" / "stage2" / "pain_points_by_course"
ARCHIVE_DIR = project_path / "outputs" / "stage2" / "archive" / "pain_points_by_course"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = setup_logger("group_by_course", filename="stage2.log", to_console=True)


def group_by_course(input_path: Path, output_dir: Path) -> None:
    grouped: Dict[str, List[Dict]] = defaultdict(list)

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
        write_jsonl(records, out_path)

    logger.info(json.dumps({
        "event": "group_by_course_complete",
        "input": str(input_path.name),
        "output_dir": str(output_dir),
        "course_count": len(grouped),
        "timestamp": get_timestamp_str()
    }))


def main() -> None:
    group_by_course(INPUT_PATH, OUTPUT_DIR)


if __name__ == "__main__":
    main()
