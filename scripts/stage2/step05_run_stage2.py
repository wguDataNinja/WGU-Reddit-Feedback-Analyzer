# filename: scripts/stage2/step05_run_stage2.py
#!/usr/bin/env python3
import sys
from pathlib import Path
import time

# Fix imports for CLI
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel, ValidationError

from utils.logger import setup_logger, get_timestamp_str
from utils.jsonl_io import read_jsonl, write_jsonl
from utils.archive_ops import move_to_archive
from utils.paths import project_path

from scripts.stage2.step03_call_llm import call_llm
from scripts.stage2.step04_apply_actions import apply_actions, deduplicate_and_reindex, check_alerts
from scripts.stage2.config_stage2 import BATCH_SIZE, ALERT_THRESHOLD, STAGE1_FLAT_FILE, STAGE2_INPUT_DIR

from scripts.stage2.step01_group_by_course import group_by_course

# Setup
logger = setup_logger("run_stage2", filename="stage2.log", to_console=True)
PROJECT_ROOT = project_path
INPUT_DIR = PROJECT_ROOT / "outputs" / "stage2" / "pain_points_by_course"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "stage2" / "clusters_by_course"
ARCHIVE_DIR = PROJECT_ROOT / "outputs" / "stage2" / "archive" / "clusters_by_course"
STAGE1_ARCHIVE_DIR = PROJECT_ROOT / "outputs" / "stage2" / "archive" / "pain_points_stage1"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
STAGE1_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# Group the Stage 1 flat file before processing
group_by_course(STAGE1_FLAT_FILE, STAGE2_INPUT_DIR)

# Pydantic models
class Cluster(BaseModel):
    cluster_id: str
    title: str
    root_cause_summary: str
    pain_point_ids: List[str]
    is_potential: bool

class Alert(BaseModel):
    cluster_id: str
    summary: str
    post_count: int
    detected_on: str

class FinalOutput(BaseModel):
    course: str
    clusters: List[Cluster]
    alert_threshold: int
    alerts: List[Alert]

def load_clusters(path: Path, course: str) -> Dict:
    if not path.exists():
        return {"course": course, "clusters": [], "alerts": [], "alert_threshold": ALERT_THRESHOLD}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def save_json(obj: Dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def run_course(course: str) -> None:
    start = time.time()

    in_path = INPUT_DIR / f"{course}.jsonl"
    out_path = OUTPUT_DIR / f"{course}_clusters.json"
    logger.info(json.dumps({
        "event": "run_course_start",
        "course": course,
        "input": str(in_path.name),
        "output": str(out_path.name),
        "start_time": get_timestamp_str()
    }))

    try:
        pain_points = list(read_jsonl(in_path))
    except Exception as e:
        logger.error(json.dumps({
            "event": "read_input_error",
            "course": course,
            "error": str(e),
            "timestamp": get_timestamp_str()
        }))
        return

    state = load_clusters(out_path, course)

    for i in range(0, len(pain_points), BATCH_SIZE):
        batch = pain_points[i:i + BATCH_SIZE]
        try:
            actions = call_llm(course, state["clusters"], batch)
            apply_actions(course, state, actions)
            save_json(state, out_path)
        except Exception as e:
            logger.error(json.dumps({
                "event": "batch_processing_error",
                "course": course,
                "batch_index": i // BATCH_SIZE,
                "error": str(e),
                "timestamp": get_timestamp_str()
            }))
            continue

    deduplicate_and_reindex(course, state["clusters"])
    check_alerts(state, threshold=ALERT_THRESHOLD)

    final_output = {
        "course": course,
        "clusters": state["clusters"],
        "alert_threshold": ALERT_THRESHOLD,
        "alerts": state.get("alerts", [])
    }

    try:
        FinalOutput.parse_obj(final_output)
    except ValidationError as e:
        logger.error(json.dumps({
            "event": "validation_error",
            "course": course,
            "error": e.json(),
            "timestamp": get_timestamp_str()
        }))
        return

    save_json(final_output, out_path)

    elapsed = time.time() - start
    logger.info(json.dumps({
        "event": "run_course_complete",
        "course": course,
        "clusters": len(final_output["clusters"]),
        "alerts": len(final_output["alerts"]),
        "elapsed_seconds": round(elapsed, 1),
        "end_time": get_timestamp_str()
    }))

def run_all() -> None:
    for file in INPUT_DIR.glob("*.jsonl"):
        run_course(file.stem)

def run_subset(course_list: List[str]) -> None:
    for course in course_list:
        run_course(course)

if __name__ == "__main__":
    run_all()
