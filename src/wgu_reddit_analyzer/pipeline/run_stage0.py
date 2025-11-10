"""
Stage 0 Runner

Purpose:
    Execute the authoritative Stage 0 dataset build and record run metadata.

Inputs:
    Local SQLite database and course list CSV.

Outputs:
    - artifacts/stage0_filtered_posts.jsonl
    - artifacts/runs/<run_id>/stage0.log
    - artifacts/runs/<run_id>/manifest.json

Usage:
    python -m wgu_reddit_analyzer.pipeline.run_stage0

Notes:
    - Honors artifacts/stage0_lock.json (status="locked") to skip rebuild.
    - Uses build_stage0_dataset as the single source of Stage 0 logic.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from wgu_reddit_analyzer.pipeline.build_stage0_dataset import (
    _artifacts_dir,
    build_stage0_dataset,
)
from wgu_reddit_analyzer.utils import filters
from wgu_reddit_analyzer.utils.logging_utils import get_logger


def _line_count(path: Path) -> int:
    """
    Count non-empty lines in a file.

    Args:
        path:
            File to inspect.

    Returns:
        Number of non-empty lines.
    """
    if not path.exists():
        return 0

    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def _get_db_path() -> str:
    """
    Return the database path derived from the repository layout.

    Returns:
        String path to db/WGU-Reddit.db.
    """
    root = _artifacts_dir().parent
    db_path = root / "db" / "WGU-Reddit.db"
    return str(db_path)


def _is_stage0_locked(artifacts_dir: Path) -> bool:
    """
    Determine whether Stage 0 is locked.

    Args:
        artifacts_dir:
            Path to the artifacts directory.

    Returns:
        True if artifacts/stage0_lock.json exists with status="locked".
    """
    lock_path = artifacts_dir / "stage0_lock.json"
    if not lock_path.exists():
        return False

    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False

    return data.get("status") == "locked"


def _setup_run_logger(run_dir: Path) -> logging.Logger:
    """
    Configure a file-backed logger for this Stage 0 run.

    Args:
        run_dir:
            Directory where stage0.log will be written.

    Returns:
        Logger instance scoped to the Stage 0 run.
    """
    logger = get_logger("stage0_run")

    log_path = run_dir / "stage0.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        ),
    )
    file_handler.setLevel(logging.INFO)

    if not any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", None) == str(log_path)
        for handler in logger.handlers
    ):
        logger.addHandler(file_handler)

    logger.info("Stage 0 run logger initialized at %s", log_path)
    return logger


def _write_manifest(run_dir: Path, output_path: Path, written: int) -> None:
    """
    Write a JSON manifest describing this Stage 0 build.

    Args:
        run_dir:
            Directory for the manifest.
        output_path:
            Path to the Stage 0 output file.
        written:
            Count of records written.
    """
    db_path = _get_db_path()
    course_csv = str(filters.COURSE_CSV) if hasattr(filters, "COURSE_CSV") else None

    manifest = {
        "stage": "stage0",
        "run_id": run_dir.name,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": "uncommitted-local",
        "script_name": "run_stage0.py",
        "inputs": {
            "db_path": db_path,
            "course_csv": course_csv,
        },
        "outputs": {
            "stage0_path": str(output_path),
            "stage0_line_count": _line_count(output_path),
        },
        "constraints": {
            "sentiment": "vader_compound < -0.2",
            "course_code": (
                "exactly one regex-verified course_code per row"
            ),
        },
        "counts": {
            "stage0_records_written": int(written),
        },
        "notes": (
            "Authoritative Stage 0 dataset build "
            "(negative-only, course-verified)."
        ),
    }

    manifest_path = run_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)


def main() -> None:
    """
    Run the Stage 0 build and record run metadata.

    Skips execution if Stage 0 is locked.
    """
    artifacts_dir = _artifacts_dir()

    if _is_stage0_locked(artifacts_dir):
        logger = get_logger("stage0_run")
        logger.info("Stage 0 is locked. Skipping rebuild.")
        return

    stage0_path = artifacts_dir / "stage0_filtered_posts.jsonl"

    run_id = "stage0_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = artifacts_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    logger = _setup_run_logger(run_dir)
    logger.info("Starting Stage 0 rebuild with run_id=%s", run_id)
    logger.info("Authoritative output: %s", stage0_path)

    written = build_stage0_dataset(stage0_path)
    logger.info("Stage 0 build completed. Records written: %d", written)

    _write_manifest(run_dir, stage0_path, written)
    logger.info("Stage 0 manifest written to %s", run_dir / "manifest.json")
    logger.info("Stage 0 run %s completed.", run_id)


if __name__ == "__main__":
    main()