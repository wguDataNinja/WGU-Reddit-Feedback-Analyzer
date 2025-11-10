#!/usr/bin/env python3
"""
Daily Update Orchestrator

Purpose:
    Coordinate the daily Reddit ingestion pipeline:
    posts, comments, and subreddit statistics.

Inputs:
    Environment variables and configuration loaded via config_loader.
    Valid Reddit API credentials.

Outputs:
    Updated local SQLite database tables for posts, comments, and subreddits.
    Log entries in logs/daily_update.log.
    Run metadata appended to the run_log table.

Usage:
    python -m wgu_reddit_analyzer.daily.daily_update

Notes:
    - Logging is configured centrally in this module.
    - This script is safe to call from launchd or cron.
    - User-level tracking remains out of scope for this pipeline.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from wgu_reddit_analyzer.fetchers.fetch_comments_daily import fetch_comments
from wgu_reddit_analyzer.fetchers.fetch_posts_daily import fetch_posts
from wgu_reddit_analyzer.fetchers.fetch_subreddits_daily import fetch_subreddits
from wgu_reddit_analyzer.utils.config_loader import (
    get_config,
    load_env,
    require_reddit_creds,
)
from wgu_reddit_analyzer.utils.db import get_db_connection

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "daily_update.log"


def setup_logger() -> logging.Logger:
    """
    Configure and return the daily update logger.

    The logger writes to both logs/daily_update.log and stdout.
    Configuration is idempotent and safe for repeated calls.

    Returns:
        Configured logger instance for daily update runs.
    """
    logger = logging.getLogger("wgu.daily_update")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logger()


def log_run(started_at: float, finished_at: float, summary: dict) -> None:
    """
    Persist a compact summary of a daily run to the database.

    The schema is kept backward compatible for any legacy consumers.

    Args:
        started_at:
            Unix timestamp marking the start of the run.
        finished_at:
            Unix timestamp marking the end of the run.
        summary:
            Aggregated run statistics for posts, comments, and subreddits.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS run_log (
          run_id            INTEGER PRIMARY KEY AUTOINCREMENT,
          started_at        REAL,
          finished_at       REAL,
          seeds_read        INTEGER,
          posts_attempted   INTEGER,
          comments_inserted INTEGER,
          failures          INTEGER
        );
        """
    )

    cur.execute(
        """
        INSERT INTO run_log (
          started_at,
          finished_at,
          seeds_read,
          posts_attempted,
          comments_inserted,
          failures
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            started_at,
            finished_at,
            0,
            summary.get("posts", {}).get("posts_fetched", 0),
            summary.get("comments", {}).get("comments_inserted", 0),
            summary.get("total_failures", 0),
        ),
    )

    conn.commit()
    conn.close()


def main() -> int:
    """
    Execute the daily update pipeline.

    Loads configuration and credentials, runs posts/comments/subreddit fetchers,
    logs failures, and records a run_log entry.

    Returns:
        Exit code 0 on success, 1 if any stage reports failures.
    """
    started_at = time.time()
    logger.info("=== Daily Update start ===")

    try:
        load_env()
        cfg = get_config()
        require_reddit_creds(cfg)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Configuration/credentials failed: %s", exc)
        return 1

    summary: dict = {}
    total_failures = 0

    try:
        posts_result = fetch_posts()
        summary["posts"] = posts_result
        total_failures += posts_result.get("failures", 0)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Posts stage failed: %s", exc)
        total_failures += 1

    try:
        comments_result = fetch_comments()
        summary["comments"] = comments_result
        total_failures += comments_result.get("failures", 0)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Comments stage failed: %s", exc)
        total_failures += 1

    try:
        subreddits_result = fetch_subreddits()
        summary["subreddits"] = subreddits_result
        total_failures += subreddits_result.get("failures", 0)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Subreddit stats stage failed: %s", exc)
        total_failures += 1

    summary["total_failures"] = total_failures

    finished_at = time.time()
    try:
        log_run(started_at, finished_at, summary)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to record run_log entry: %s", exc)

    logger.info("Failures: %s", total_failures)
    logger.info("=== Daily Update end ===")

    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())