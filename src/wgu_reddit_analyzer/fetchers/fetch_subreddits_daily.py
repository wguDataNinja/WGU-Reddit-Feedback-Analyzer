from __future__ import annotations

"""
Daily Subreddit Metadata Fetcher

Loads target subreddits, validates access, and updates:
- subreddits (about metadata)
- subreddit_stats (point-in-time metrics)
"""

import time
from pathlib import Path
from typing import Dict, Any, List

import prawcore

from wgu_reddit_analyzer.utils.reddit_client import make_reddit
from wgu_reddit_analyzer.utils.db import get_db_connection, get_table_columns
from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("fetch_subreddits_daily")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUBREDDIT_LIST_PATH = PROJECT_ROOT / "data" / "wgu_subreddits.txt"


def _read_subreddit_list() -> List[str]:
    if not SUBREDDIT_LIST_PATH.exists():
        raise FileNotFoundError(f"Missing subreddit list: {SUBREDDIT_LIST_PATH}")

    subs: List[str] = []
    with SUBREDDIT_LIST_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("r/"):
                line = line[2:]
            if line:
                subs.append(line)

    if not subs:
        raise RuntimeError(f"Subreddit list is empty: {SUBREDDIT_LIST_PATH}")

    return subs


def fetch_subreddits() -> Dict[str, Any]:
    start = time.time()
    reddit = make_reddit()
    subs = _read_subreddit_list()

    conn = get_db_connection()
    cur = conn.cursor()

    sub_cols = set(get_table_columns(conn, "subreddits"))
    stat_cols = set(get_table_columns(conn, "subreddit_stats"))

    if not sub_cols or not stat_cols:
        logger.error("Missing required tables: subreddits or subreddit_stats.")
        conn.close()
        return {
            "stage": "subreddits",
            "subreddit_stats_inserted": 0,
            "failures": 1,
            "duration_sec": 0.0,
        }

    ok = 0
    failures = 0

    for name in subs:
        try:
            s = reddit.subreddit(name)

            # Validate existence/access
            try:
                _ = s.id
            except prawcore.exceptions.NotFound:
                logger.warning("Skipping subreddit '%s' — not found or banned (404).", name)
                continue
            except prawcore.exceptions.Forbidden:
                logger.warning("Skipping subreddit '%s' — access forbidden/private (403).", name)
                continue
            except Exception as exc:
                failures += 1
                logger.warning(
                    "Error initializing subreddit '%s': %s: %s",
                    name,
                    type(exc).__name__,
                    exc,
                )
                continue

            about = {
                "subreddit_id": s.id,
                "name": s.display_name,
                "description": s.public_description,
                "is_nsfw": int(getattr(s, "over18", False)),
                "created_utc": float(getattr(s, "created_utc", 0.0) or 0.0),
                "rules": None,
                "sidebar_text": getattr(s, "description", None),
            }

            about_row = {k: v for k, v in about.items() if k in sub_cols}
            if about_row:
                cols = ", ".join(about_row.keys())
                qs = ", ".join(["?"] * len(about_row))
                cur.execute(
                    f"INSERT OR REPLACE INTO subreddits ({cols}) VALUES ({qs})",
                    list(about_row.values()),
                )

            stats = {
                "subreddit_id": s.id,
                "captured_at": time.time(),
                "subscriber_count": int(getattr(s, "subscribers", 0) or 0),
                "active_users": int(
                    getattr(s, "active_user_count", 0)
                    or getattr(s, "accounts_active", 0)
                    or 0
                ),
            }

            stats_row = {k: v for k, v in stats.items() if k in stat_cols}
            if stats_row:
                cols = ", ".join(stats_row.keys())
                qs = ", ".join(["?"] * len(stats_row))
                cur.execute(
                    f"INSERT INTO subreddit_stats ({cols}) VALUES ({qs})",
                    list(stats_row.values()),
                )

            ok += 1

        except Exception as exc:
            failures += 1
            logger.warning(
                "Error fetching subreddit '%s': %s: %s",
                name,
                type(exc).__name__,
                exc,
            )

    conn.commit()
    conn.close()

    duration = round(time.time() - start, 2)
    logger.info(
        "Subreddit Stats Inserted=%s Failures=%s Duration=%.2fs",
        ok,
        failures,
        duration,
    )

    return {
        "stage": "subreddits",
        "subreddit_stats_inserted": ok,
        "failures": failures,
        "duration_sec": duration,
    }


if __name__ == "__main__":
    summary = fetch_subreddits()
    logger.info("Standalone fetch_subreddits run summary: %s", summary)