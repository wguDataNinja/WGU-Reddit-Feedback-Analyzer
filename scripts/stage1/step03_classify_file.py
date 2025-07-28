# scripts/stage1/step03_classify_file.py

"""Processes all Reddit posts for Stage 1 pain point classification."""

from pathlib import Path
from typing import Any
import json
import re
import time
from scripts.stage1.step02_classify_post import classify_post
from scripts.stage1.config_stage1 import INPUT_PATH, OUTPUT_PATH
from utils.logger import setup_logger, get_timestamp_str
from utils.jsonl_io import read_jsonl, write_jsonl

logger = setup_logger("stage1_file", filename="stage1.log", to_console=True, verbose=True)
def truncate(text: str, max_len: int) -> str:
    return text[:max_len] if text else ""

def get_text(post: dict[str, Any]) -> str:
    return post.get("text_clean") or post.get("text") or post.get("selftext") or ""

def normalize_text(text: str) -> str:
    """Lowercase, remove punctuation, normalize whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text)

def classify_file(limit: int | None = None) -> None:
    start_time = time.time()
    posts = list(read_jsonl(INPUT_PATH))
    if limit:
        posts = posts[:limit]

    print(f"Starting Stage 1 classification")
    print(f"Loaded {len(posts)} posts from {INPUT_PATH.name}")

    logger.info(json.dumps({
        "event": "stage1_start",
        "model": "gpt-4o-mini",
        "input": str(INPUT_PATH),
        "output": str(OUTPUT_PATH),
        "max_chars": 2000,
        "total_posts": len(posts),
        "start_time": get_timestamp_str()
    }))

    output_records = []
    success = errors = 0
    seen_texts = set()

    for i, post in enumerate(posts, 1):
        post_id = post.get("post_id", f"idx_{i}")
        courses = post.get("matched_course_codes") or []
        course = courses[0] if courses else "UNKNOWN"
        text = truncate(get_text(post), 2000)
        norm = normalize_text(text)

        if norm in seen_texts:
            print(f"[{i}] Skipped duplicate post_id={post_id}")
            logger.info(json.dumps({
                "post_id": post_id,
                "course": course,
                "skipped_reason": "duplicate_text"
            }))
            continue
        seen_texts.add(norm)

        print(f"[{i}] Classifying post_id={post_id}, course={course}")
        post_start = time.time()

        try:
            res = classify_post(post_id, course, text)
            n = res.get("num_pain_points", 0)
            pain_points = res.get("pain_points", [])
            flat = [
                {
                    "pain_point_id": f"{post_id}_{j}",
                    "post_id": post_id,
                    "course": course,
                    "pain_point_summary": p["pain_point_summary"],
                    "root_cause": p["root_cause"],
                    "quoted_text": p["quoted_text"]
                }
                for j, p in enumerate(pain_points)
            ]
            output_records.extend(flat)
            success += 1

            print(f"[{i}] Extracted {n} pain points")

            logger.info(json.dumps({
                "post_id": post_id,
                "course": course,
                "num_pain_points": n,
                "pain_point_ids": [r["pain_point_id"] for r in flat],
                "quoted_texts": [r["quoted_text"] for r in flat]
            }))

            if n == -1:
                logger.warning(json.dumps({
                    "post_id": post_id,
                    "course": course,
                    "warning": "classification failed, num_pain_points=-1"
                }))

            logger.debug(f"post_id={post_id} completed in {time.time() - post_start:.2f}s")

        except Exception as e:
            print(f"[{i}] Error on post_id={post_id}: {e}")
            errors += 1
            logger.error(json.dumps({
                "post_id": post_id,
                "error": str(e)
            }))

        if i % 25 == 0:
            logger.info(f"Processed {i}/{len(posts)} posts so far...")

    write_jsonl(output_records, OUTPUT_PATH)
    elapsed = time.time() - start_time

    print(f"Finished Stage 1. Wrote {len(output_records)} pain points to {OUTPUT_PATH.name}")
    print(f"Success: {success} | Errors: {errors}")
    print(f"Elapsed time: {elapsed:.1f} seconds")

    logger.info(json.dumps({
        "event": "stage1_complete",
        "success": success,
        "errors": errors,
        "output": str(OUTPUT_PATH),
        "elapsed_seconds": round(elapsed, 1),
        "end_time": get_timestamp_str()
    }))