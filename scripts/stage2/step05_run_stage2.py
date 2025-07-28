#!/usr/bin/env python3

import sys
import json
import time
from pathlib import Path
from typing import List, Dict
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.logger import setup_logger, get_timestamp_str
from utils.jsonl_io import read_jsonl
from utils.paths import project_path
from scripts.stage2.step01_group_by_course import group_by_course
from scripts.stage2.config_stage2 import (
    STAGE1_FLAT_FILE,
    STAGE2_INPUT_DIR,
    STAGE2_OUTPUT_DIR,
    FULL_BATCH_TOKEN_LIMIT,
)
from utils.token_utils import count_tokens
from scripts.stage2.step03_call_llm import call_llm_full, FinalOutput

logger = setup_logger("run_stage2", filename="stage2.log", to_console=True)
INPUT_DIR = STAGE2_INPUT_DIR
OUTPUT_DIR = STAGE2_OUTPUT_DIR

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Group the Stage 1 flat file before processing
group_by_course(STAGE1_FLAT_FILE, INPUT_DIR)

def save_json(obj: Dict, path: Path) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def run_course(course: str) -> None:
    start = time.time()
    in_path = INPUT_DIR / f"{course}.jsonl"
    out_path = OUTPUT_DIR / f"{course}_clusters.json"
    logger.info(json.dumps({
        "event": "run_course_start",
        "course": course,
        "input": in_path.name,
        "output": out_path.name,
        "start_time": get_timestamp_str()
    }))
    pain_points = list(read_jsonl(in_path))
    raw_text = "\n---\n".join(f"{p['pain_point_summary']}\n{p['quoted_text']}" for p in pain_points)
    if count_tokens(raw_text) > FULL_BATCH_TOKEN_LIMIT:
        logger.error(json.dumps({
            "event": "token_limit_exceeded",
            "course": course,
            "tokens": count_tokens(raw_text),
            "limit": FULL_BATCH_TOKEN_LIMIT,
            "timestamp": get_timestamp_str()
        }))
        return
    try:
        result = call_llm_full(course, clusters=[], pain_points=pain_points, verbose=True)
    except Exception as e:
        logger.error(json.dumps({
            "event": "llm_call_failed",
            "course": course,
            "error": str(e),
            "timestamp": get_timestamp_str()
        }))
        return
    try:
        FinalOutput.model_validate(result)
    except ValidationError as e:
        logger.error(json.dumps({
            "event": "validation_error",
            "course": course,
            "error": e.json(),
            "timestamp": get_timestamp_str()
        }))
        return
    save_json(result, out_path)
    elapsed = time.time() - start
    logger.info(json.dumps({
        "event": "run_course_complete",
        "course": course,
        "clusters": len(result['clusters']),
        "elapsed_seconds": round(elapsed, 1),
        "end_time": get_timestamp_str()
    }))

def run_all() -> None:
    from scripts.stage2.config_stage2 import MODEL_NAME, MAX_RETRIES, RETRY_SLEEP_SECONDS

    start_time = time.time()
    logger.info(json.dumps({
        "event": "run_stage2_start",
        "model": MODEL_NAME,
        "token_limit": FULL_BATCH_TOKEN_LIMIT,
        "max_retries": MAX_RETRIES,
        "retry_sleep_seconds": RETRY_SLEEP_SECONDS,
        "start_time": get_timestamp_str()
    }))

    summary = []
    for file in INPUT_DIR.glob("*.jsonl"):
        result = run_course(file.stem)
        if result:
            summary.append(result)

    elapsed = round(time.time() - start_time, 1)
    logger.info(json.dumps({
        "event": "run_all_summary",
        "total_courses": len(summary),
        "total_clusters": sum(c["clusters"] for c in summary),
        "total_seconds": sum(c["seconds"] for c in summary),
        "elapsed_wallclock": elapsed,
        "end_time": get_timestamp_str(),
        "details": summary
    }))

# Filename: step05_run_stage2.py (add below existing functions)

def run_courses(course_list: List[str]) -> None:
    available_files = {file.stem for file in INPUT_DIR.glob("*.jsonl")}
    missing = [course for course in course_list if course not in available_files]
    if missing:
        raise FileNotFoundError(f"Missing input files for course(s): {', '.join(missing)}")
    for course in course_list:
        run_course(course)

if __name__ == "__main__":
    run_all()
    # run_courses(["D335"])